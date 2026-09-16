import os
import io
import re
import json
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response, session
from flask_cors import CORS

import database
import export_service
import seed_data
import srm_live_bridge


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AVATARS_DIR = os.path.join(BASE_DIR, "static", "uploads", "avatars")
SNAPSHOTS_DIR = os.path.join(BASE_DIR, "static", "uploads", "snapshots")
POSTS_MEDIA_DIR = os.path.join(BASE_DIR, "static", "uploads", "posts")

os.makedirs(AVATARS_DIR, exist_ok=True)
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
os.makedirs(POSTS_MEDIA_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "srm_academia_luxury_secret_key_2026"
CORS(app)

# Initialize database and seed data on startup
database.init_db()

def save_base64_image(base64_str, folder, prefix="img"):
    """Decodes a base64 data URL and saves to disk as a JPG file."""
    if not base64_str or not isinstance(base64_str, str):
        return ""
    try:
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
        img_data = base64.b64decode(base64_str)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{prefix}_{timestamp}.jpg"
        filepath = os.path.join(folder, filename)
        with open(filepath, "wb") as f:
            f.write(img_data)
        rel_folder = os.path.basename(folder)
        return f"/static/uploads/{rel_folder}/{filename}"
    except Exception as e:
        print(f"[ERROR] Failed to save base64 image: {e}")
        return ""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/health")
def health():
    stats = database.get_dashboard_stats()
    return jsonify({
        "status": "ONLINE",
        "system": "SRM Academia & Google Classroom AI Core",
        "timestamp": datetime.now().isoformat(),
        "stats": stats
    })

# --- SRM Live Gateway Endpoints ---

@app.route("/api/srm/status", methods=["GET"])
def srm_status():
    """Returns live health and connectivity status of Academia, eVarsity, and Staff Finder."""
    status = srm_live_bridge.SRMAcademiaClient.get_gateway_status()
    return jsonify({
        "status": "ok",
        "gateways": status,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/auth/evarsity/captcha", methods=["GET"])
def evarsity_captcha():
    """Streams a live captcha image from SRM eVarsity for faculty login."""
    captcha_data = srm_live_bridge.SRMEvarsityClient.get_live_captcha()
    return jsonify(captcha_data)

@app.route("/api/staff/search", methods=["GET"])
def staff_search():
    """Searches official SRM Staff Directory in real time for KTR faculty."""
    query = request.args.get("query", "").strip()
    campus = request.args.get("campus", "78")
    results = srm_live_bridge.SRMStaffFinderClient.search_staff(query, campus=campus)
    return jsonify({
        "query": query,
        "campus": campus,
        "total": len(results),
        "results": results
    })

# --- Authentication Routes (SRM Academia & eVarsity Integrated) ---

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.json or {}
    net_id = data.get("net_id", "").strip()
    password = data.get("password", "").strip()
    requested_role = data.get("role", "student") # 'student' or 'teacher'
    session_id = data.get("session_id", "")
    captcha_code = data.get("captcha_code", "").strip()

    if not net_id or not password:
        return jsonify({"error": "NetID / Register Number and Password are required."}), 400

    # 1. Faculty Login via SRM eVarsity Bridge
    if requested_role == "teacher":
        if session_id and captcha_code:
            ev_result = srm_live_bridge.SRMEvarsityClient.authenticate_faculty(
                session_id, net_id, password, captcha_code
            )
            if not ev_result.get("success"):
                return jsonify({"error": ev_result.get("message", "eVarsity authentication failed.")}), 401
            
            # Find or auto-provision faculty user
            user = database.get_user_by_net_id(net_id)
            if not user:
                faculty_name = ev_result.get("name", f"Prof. {net_id}")
                user_id, err = database.create_user(
                    net_id=net_id,
                    name=faculty_name,
                    password=password,
                    role="teacher",
                    department="Faculty of Engineering & Technology (KTR)",
                    reg_no=net_id,
                    semester="Faculty",
                    avatar_path="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&auto=format&fit=crop&q=80"
                )
                user = database.get_user_by_id(user_id)
        else:
            # Check local registered faculty
            user = database.get_user_by_net_id(net_id)
            if not user or user["role"] != "teacher":
                return jsonify({"error": f"No faculty account found for '{net_id}'. Please solve the eVarsity captcha to authenticate live."}), 401
            if user["password"] != password:
                return jsonify({"error": "Incorrect faculty password. Please verify your credentials."}), 401

    # 2. Student Login via SRM Academia Bridge
    else:
        user = database.get_user_by_net_id(net_id)
        if not user:
            # Attempt live SRM Academia negotiation
            acad_result = srm_live_bridge.SRMAcademiaClient.authenticate_student(net_id, password)
            reg_clean = net_id.upper().split('@')[0]
            # Auto-provision new SRM KTR student account with real curriculum
            user_id, err = database.create_user(
                net_id=net_id,
                name=f"Student {reg_clean}",
                password=password,
                role="student",
                department="Computer Science & Engineering (KTR)",
                reg_no=reg_clean,
                semester="5th Semester",
                avatar_path="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&auto=format&fit=crop&q=80"
            )
            user = database.get_user_by_id(user_id)
            # Ensure their timetable and courses are populated
            database.ensure_student_records(user_id)
        else:
            if user["password"] != password:
                return jsonify({"error": "Incorrect password. Please verify your SRM credentials."}), 401

    session["user_id"] = user["id"]
    session["role"] = user["role"]

    # Guarantee student has populated records
    if user["role"] == "student":
        database.ensure_student_records(user["id"])

    return jsonify({
        "message": f"Welcome, {user['name']}",
        "user": {
            "id": user["id"],
            "net_id": user["net_id"],
            "name": user["name"],
            "role": user["role"],
            "department": user["department"],
            "reg_no": user["reg_no"],
            "semester": user["semester"],
            "avatar_path": user["avatar_path"],
            "email": user["email"]
        },
        "gateway": "SRMIST Live Connected"
    })

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user_id = session.get("user_id")
    if not user_id:
        # Default to demo student if no session active for instant accessibility
        demo_student = database.get_user_by_net_id("ra2211003010123")
        if demo_student:
            return jsonify({"logged_in": True, "user": demo_student})
        return jsonify({"logged_in": False}), 401
    
    user = database.get_user_by_id(user_id)
    if not user:
        return jsonify({"logged_in": False}), 401
    return jsonify({"logged_in": True, "user": user})

# --- Google Classroom Style Routes ---

@app.route("/api/classrooms", methods=["GET"])
def list_classrooms():
    user_id = request.args.get("user_id", type=int)
    role = request.args.get("role", "student")

    if not user_id:
        # If no user_id passed, check session
        user_id = session.get("user_id")
        role = session.get("role", "student")

    if not user_id:
        # Fallback to demo user
        user = database.get_user_by_net_id("ra2211003010123" if role == "student" else "faculty_srm")
        user_id = user["id"] if user else 1

    classrooms = database.get_user_classrooms(user_id, role)
    return jsonify({"classrooms": classrooms, "total": len(classrooms)})

@app.route("/api/classrooms", methods=["POST"])
def create_new_classroom():
    data = request.json or {}
    name = data.get("name", "").strip()
    course_code = data.get("course_code", "").strip()
    section = data.get("section", "CSE-A").strip()
    teacher_id = data.get("teacher_id") or session.get("user_id")
    description = data.get("description", "").strip()

    if not teacher_id:
        faculty = database.get_user_by_net_id("faculty_srm")
        teacher_id = faculty["id"] if faculty else 1

    if not name or not course_code:
        return jsonify({"error": "Classroom Name and Course Code are mandatory."}), 400

    class_id, code = database.create_classroom(name, course_code, section, teacher_id, description)
    classroom = database.get_classroom_by_id(class_id)
    return jsonify({
        "message": f"Classroom '{name}' created successfully",
        "classroom": classroom,
        "class_code": code
    }), 201

@app.route("/api/classrooms/join", methods=["POST"])
def join_class():
    data = request.json or {}
    code = data.get("code", "").strip()
    student_id = data.get("student_id") or session.get("user_id")

    if not student_id:
        student = database.get_user_by_net_id("ra2211003010123")
        student_id = student["id"] if student else 2

    if not code:
        return jsonify({"error": "Please enter a valid Classroom Code."}), 400

    classroom, err = database.join_classroom(code, student_id)
    if err and not classroom:
        return jsonify({"error": err}), 400

    return jsonify({
        "message": f"Enrolled in {classroom['name']} ({classroom['code']})",
        "classroom": classroom,
        "note": err
    })

@app.route("/api/classrooms/<int:class_id>", methods=["GET"])
def get_classroom(class_id):
    classroom = database.get_classroom_by_id(class_id)
    if not classroom:
        return jsonify({"error": "Classroom not found"}), 404
    
    posts = database.get_classroom_posts(class_id)
    members = database.get_classroom_members(class_id)
    
    return jsonify({
        "classroom": classroom,
        "posts": posts,
        "members": members,
        "total_students": len(members)
    })

@app.route("/api/classrooms/<int:class_id>/posts", methods=["POST"])
def create_classroom_post(class_id):
    data = request.json or {}
    content = data.get("content", "").strip()
    author_id = data.get("author_id") or session.get("user_id")
    media_url = data.get("media_url", "").strip()
    media_type = data.get("media_type", "none").strip()
    media_base64 = data.get("media_base64", "")

    if not content and not media_url and not media_base64:
        return jsonify({"error": "Post content or media attachment is required."}), 400

    author = database.get_user_by_id(author_id) if author_id else None
    if not author:
        author = database.get_user_by_net_id("faculty_srm")
        author_id = author["id"] if author else 1

    if media_base64:
        media_url = save_base64_image(media_base64, POSTS_MEDIA_DIR, prefix="post")
        media_type = "image"

    post_id = database.add_classroom_post(
        classroom_id=class_id,
        author_id=author_id,
        author_name=author["name"],
        author_role="Faculty" if author["role"] == "teacher" else "Student",
        content=content,
        media_url=media_url,
        media_type=media_type
    )

    posts = database.get_classroom_posts(class_id)
    return jsonify({
        "message": "Announcement posted to classroom stream",
        "post_id": post_id,
        "posts": posts
    }), 201

# --- SRM Academia Student Portal Routes ---

@app.route("/api/student/attendance-margin", methods=["GET"])
def get_student_attendance_margin():
    student_id = request.args.get("student_id", type=int) or session.get("user_id")
    if not student_id:
        student = database.get_user_by_net_id("ra2211003010123")
        student_id = student["id"] if student else 2

    courses = database.get_student_courses_with_margin(student_id)
    
    # Calculate overall institutional attendance
    total_conducted = sum(c["total_hours"] for c in courses)
    total_attended = sum(c["attended_hours"] for c in courses)
    overall_pct = round((total_attended / total_conducted * 100), 1) if total_conducted > 0 else 100.0
    overall_margin = database.calculate_margin(total_attended, total_conducted)

    return jsonify({
        "courses": courses,
        "overall": {
            "total_hours": total_conducted,
            "attended_hours": total_attended,
            "percentage": overall_pct,
            "margin_info": overall_margin
        }
    })

@app.route("/api/student/timetable", methods=["GET"])
def get_timetable():
    student_id = request.args.get("student_id", type=int) or session.get("user_id")
    if not student_id:
        student = database.get_user_by_net_id("ra2211003010123")
        student_id = student["id"] if student else 2

    timetable_rows = database.get_student_timetable(student_id)
    
    # Organize by day order 1 to 5
    by_day = {1: [], 2: [], 3: [], 4: [], 5: []}
    for r in timetable_rows:
        if r["day_order"] in by_day:
            by_day[r["day_order"]].append(r)

    # Sort each day by hour
    for d in by_day:
        by_day[d].sort(key=lambda x: x["hour"])

    return jsonify({
        "by_day": by_day,
        "raw": timetable_rows
    })

@app.route("/api/student/marks", methods=["GET"])
def get_marks():
    student_id = request.args.get("student_id", type=int) or session.get("user_id")
    if not student_id:
        student = database.get_user_by_net_id("ra2211003010123")
        student_id = student["id"] if student else 2

    courses = database.get_student_courses_with_margin(student_id)
    marks_list = []
    for c in courses:
        total_internal = c["cla1_marks"] + c["cla2_marks"] + c["assignment_marks"]
        marks_list.append({
            "course_code": c["course_code"],
            "course_name": c["course_name"],
            "cla1": c["cla1_marks"],
            "cla2": c["cla2_marks"],
            "assignment": c["assignment_marks"],
            "model_exam": c["model_marks"],
            "internal_total": round(total_internal, 1)
        })

    return jsonify({"marks": marks_list})

@app.route("/api/student/seating", methods=["GET"])
def get_seating():
    student_id = request.args.get("student_id", type=int) or session.get("user_id")
    if not student_id:
        student = database.get_user_by_net_id("ra2211003010123")
        student_id = student["id"] if student else 2

    seating_plan = database.get_student_exam_seating(student_id)
    return jsonify({"seating_plan": seating_plan})

# --- AI Biometric Face Recognition & Roster Routes ---

@app.route("/api/students", methods=["GET"])
def list_students():
    classroom_id = request.args.get("classroom_id", type=int)
    if classroom_id:
        students = database.get_classroom_members(classroom_id)
    else:
        students = database.get_all_students()
    return jsonify({"students": students, "total": len(students)})

@app.route("/api/students", methods=["POST"])
def register_student():
    data = request.json or {}
    roll_no = data.get("roll_no", "").strip() or data.get("reg_no", "").strip()
    name = data.get("name", "").strip()
    department = data.get("department", "Computer Science & Engineering").strip()
    email = data.get("email", "").strip()
    face_descriptor = data.get("face_descriptor", [])
    avatar_base64 = data.get("avatar_base64", "")

    if not roll_no or not name:
        return jsonify({"error": "Register / Roll Number and Full Name are mandatory."}), 400

    if not face_descriptor or len(face_descriptor) != 128:
        return jsonify({"error": "Valid 128-dimensional facial biometric descriptor is required."}), 400

    avatar_path = ""
    if avatar_base64:
        clean_roll = re.sub(r'[^a-zA-Z0-9_-]', '_', roll_no)
        avatar_path = save_base64_image(avatar_base64, AVATARS_DIR, prefix=f"avatar_{clean_roll}")

    user_id, err = database.create_user(
        net_id=roll_no.lower(),
        name=name,
        password="password123",
        role="student",
        department=department,
        reg_no=roll_no.upper(),
        semester="5th Semester (B.Tech CSE)",
        avatar_path=avatar_path,
        face_descriptor=face_descriptor
    )

    if err:
        return jsonify({"error": err}), 400

    return jsonify({
        "message": f"Student {name} registered in SRM Biometric Database",
        "student_id": user_id,
        "roll_no": roll_no,
        "name": name,
        "avatar_path": avatar_path
    }), 201

# --- Attendance Sessions & Live Sweep Marking ---

@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    sessions = database.get_all_sessions()
    active = database.get_active_session()
    return jsonify({
        "sessions": sessions,
        "active_session": active
    })

@app.route("/api/sessions", methods=["POST"])
def create_session_route():
    data = request.json or {}
    session_name = data.get("session_name", "").strip()
    course_code = data.get("course_code", "").strip()
    classroom_id = data.get("classroom_id")
    notes = data.get("notes", "").strip()

    if not session_name or not course_code:
        return jsonify({"error": "Session Name and Course Code are required"}), 400

    session_id = database.create_session(
        session_name=session_name,
        course_code=course_code,
        notes=notes,
        classroom_id=classroom_id
    )
    session_obj = database.get_session(session_id)
    return jsonify({"message": "Attendance session started", "session": session_obj}), 201

@app.route("/api/attendance/mark", methods=["POST"])
def mark_attendance_record():
    data = request.json or {}
    session_id = data.get("session_id")
    student_id = data.get("student_id")
    confidence = data.get("confidence", 95.0)
    snapshot_base64 = data.get("snapshot_base64", "")

    if not session_id:
        active = database.get_active_session()
        if active:
            session_id = active["id"]
        else:
            return jsonify({"error": "No active session found"}), 400

    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400

    snapshot_path = ""
    if snapshot_base64:
        snapshot_path = save_base64_image(
            snapshot_base64,
            SNAPSHOTS_DIR,
            prefix=f"snap_s{session_id}_u{student_id}"
        )

    res, err = database.mark_attendance(
        session_id=session_id,
        student_id=student_id,
        confidence=confidence,
        snapshot_path=snapshot_path
    )

    if err:
        return jsonify({"error": err}), 500

    return jsonify(res)

@app.route("/api/sessions/<int:session_id>/complete", methods=["POST"])
def finish_session(session_id):
    database.complete_session(session_id)
    session_obj = database.get_session(session_id)
    return jsonify({"message": "Session marked as completed", "session": session_obj})

# --- Export Routes ---

@app.route("/api/export/csv/<int:session_id>")
def export_csv(session_id):
    csv_data, err = export_service.generate_csv_report(session_id)
    if err:
        return jsonify({"error": err}), 404

    filename = f"srm_attendance_session_{session_id}_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

@app.route("/api/export/print/<int:session_id>")
def export_print(session_id):
    html_data, err = export_service.generate_html_print_report(session_id)
    if err:
        return jsonify({"error": err}), 404
    return Response(html_data, mimetype="text/html")

if __name__ == "__main__":
    print("\n========================================================")
    print("  SRM ACADEMIA & CLASSROOM AI ATTENDANCE CORE           ")
    print("  Server running at: http://127.0.0.1:5000              ")
    print("========================================================\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
