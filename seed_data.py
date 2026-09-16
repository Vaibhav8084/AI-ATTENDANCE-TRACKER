import random
import numpy as np
import database
import json

def generate_synthetic_descriptor(seed_val):
    rng = np.random.RandomState(seed_val)
    vec = rng.randn(128).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return [round(float(x), 6) for x in vec]

DEMO_STUDENTS = [
    {"net_id": "ra2211003010123", "reg_no": "RA2211003010123", "name": "Aarav Sharma", "dept": "Computer Science & Engineering", "email": "as1023@srmist.edu.in"},
    {"net_id": "ra2211003010045", "reg_no": "RA2211003010045", "name": "Elena Rostova", "dept": "Computer Science & Engineering", "email": "er5492@srmist.edu.in"},
    {"net_id": "ra2211003010088", "reg_no": "RA2211003010088", "name": "Marcus Vance", "dept": "Computer Science & Engineering", "email": "mv3041@srmist.edu.in"},
    {"net_id": "ra2211003010112", "reg_no": "RA2211003010112", "name": "Aria Takahashi", "dept": "Computer Science & Engineering", "email": "at8922@srmist.edu.in"},
    {"net_id": "ra2211003010167", "reg_no": "RA2211003010167", "name": "Devon Cole", "dept": "Computer Science & Engineering", "email": "dc1145@srmist.edu.in"},
    {"net_id": "ra2211003010190", "reg_no": "RA2211003010190", "name": "Zara Chen", "dept": "Computer Science & Engineering", "email": "zc4402@srmist.edu.in"},
    {"net_id": "ra2211003010204", "reg_no": "RA2211003010204", "name": "Priya Sundaram", "dept": "Computer Science & Engineering", "email": "ps9021@srmist.edu.in"},
    {"net_id": "ra2211003010231", "reg_no": "RA2211003010231", "name": "Lucas Silva", "dept": "Computer Science & Engineering", "email": "ls7710@srmist.edu.in"}
]

CLASSROOMS = [
    {
        "code": "SRM-DL01",
        "name": "Deep Learning & Neural Architectures",
        "course_code": "18CSC305J",
        "section": "CSE-B",
        "desc": "Official course portal for 18CSC305J. Covers CNNs, Vision Transformers, PyTorch, and Biometric Vision."
    },
    {
        "code": "SRM-OS02",
        "name": "Operating Systems & Virtualization",
        "course_code": "18CSC302J",
        "section": "CSE-B",
        "desc": "Concurrency, paging, virtual memory, scheduling algorithms and Linux kernel internals."
    },
    {
        "code": "SRM-DA03",
        "name": "Design & Analysis of Algorithms",
        "course_code": "18CSC303J",
        "section": "CSE-B",
        "desc": "Dynamic programming, greedy paradigms, graph algorithms, and NP-completeness."
    },
    {
        "code": "SRM-CN04",
        "name": "Computer Networks & Protocols",
        "course_code": "18CSC304J",
        "section": "CSE-B",
        "desc": "OSI 7 Layers, TCP congestion control, BGP routing, and network security."
    }
]

STUDENT_COURSES = [
    {"code": "18CSC305J", "name": "Deep Learning & Neural Architectures", "faculty": "Dr. Rajesh K. Sundaram", "total": 42, "att": 38, "cla1": 23.5, "cla2": 24.0, "assign": 9.5, "model": 46.0},
    {"code": "18CSC302J", "name": "Operating Systems & Virtualization", "faculty": "Dr. N. Karthikeyan", "total": 36, "att": 30, "cla1": 21.0, "cla2": 22.5, "assign": 9.0, "model": 43.5},
    {"code": "18CSC303J", "name": "Design & Analysis of Algorithms", "faculty": "Dr. V. Meenakshi", "total": 40, "att": 31, "cla1": 19.5, "cla2": 20.0, "assign": 8.5, "model": 39.0},
    {"code": "18CSC304J", "name": "Computer Networks & Protocols", "faculty": "Dr. S. Balasubramanian", "total": 38, "att": 26, "cla1": 18.0, "cla2": 19.5, "assign": 8.0, "model": 36.5},
    {"code": "18LEM101T", "name": "Constitution of India", "faculty": "Prof. R. Anitha", "total": 20, "att": 19, "cla1": 24.0, "cla2": 23.5, "assign": 10.0, "model": 48.0}
]

TIMETABLE = [
    # Day Order 1
    {"day": 1, "hour": 1, "code": "18CSC305J", "name": "Deep Learning", "room": "TP-704", "faculty": "Dr. Rajesh K. Sundaram"},
    {"day": 1, "hour": 2, "code": "18CSC302J", "name": "Operating Systems", "room": "TP-704", "faculty": "Dr. N. Karthikeyan"},
    {"day": 1, "hour": 3, "code": "18CSC303J", "name": "Algorithms", "room": "TP-704", "faculty": "Dr. V. Meenakshi"},
    {"day": 1, "hour": 4, "code": "18CSC304J", "name": "Computer Networks", "room": "TP-704", "faculty": "Dr. S. Balasubramanian"},
    {"day": 1, "hour": 5, "code": "18CSC305J", "name": "Deep Learning Lab", "room": "Tech Park Lab 3", "faculty": "Dr. Rajesh K. Sundaram"},
    {"day": 1, "hour": 6, "code": "18CSC305J", "name": "Deep Learning Lab", "room": "Tech Park Lab 3", "faculty": "Dr. Rajesh K. Sundaram"},
    
    # Day Order 2
    {"day": 2, "hour": 1, "code": "18CSC303J", "name": "Algorithms", "room": "TP-704", "faculty": "Dr. V. Meenakshi"},
    {"day": 2, "hour": 2, "code": "18CSC304J", "name": "Computer Networks", "room": "TP-704", "faculty": "Dr. S. Balasubramanian"},
    {"day": 2, "hour": 3, "code": "18CSC305J", "name": "Deep Learning", "room": "TP-704", "faculty": "Dr. Rajesh K. Sundaram"},
    {"day": 2, "hour": 4, "code": "18CSC302J", "name": "Operating Systems", "room": "TP-704", "faculty": "Dr. N. Karthikeyan"},
    {"day": 2, "hour": 5, "code": "18LEM101T", "name": "Constitution of India", "room": "TP-704", "faculty": "Prof. R. Anitha"},

    # Day Order 3
    {"day": 3, "hour": 1, "code": "18CSC302J", "name": "Operating Systems Lab", "room": "TP Lab 5", "faculty": "Dr. N. Karthikeyan"},
    {"day": 3, "hour": 2, "code": "18CSC302J", "name": "Operating Systems Lab", "room": "TP Lab 5", "faculty": "Dr. N. Karthikeyan"},
    {"day": 3, "hour": 3, "code": "18CSC305J", "name": "Deep Learning", "room": "TP-704", "faculty": "Dr. Rajesh K. Sundaram"},
    {"day": 3, "hour": 4, "code": "18CSC303J", "name": "Algorithms", "room": "TP-704", "faculty": "Dr. V. Meenakshi"},

    # Day Order 4
    {"day": 4, "hour": 1, "code": "18CSC304J", "name": "Computer Networks", "room": "TP-704", "faculty": "Dr. S. Balasubramanian"},
    {"day": 4, "hour": 2, "code": "18CSC305J", "name": "Deep Learning", "room": "TP-704", "faculty": "Dr. Rajesh K. Sundaram"},
    {"day": 4, "hour": 3, "code": "18CSC302J", "name": "Operating Systems", "room": "TP-704", "faculty": "Dr. N. Karthikeyan"},
    {"day": 4, "hour": 4, "code": "18CSC303J", "name": "Algorithms", "room": "TP-704", "faculty": "Dr. V. Meenakshi"},

    # Day Order 5
    {"day": 5, "hour": 1, "code": "18CSC303J", "name": "Algorithms Lab", "room": "TP Lab 2", "faculty": "Dr. V. Meenakshi"},
    {"day": 5, "hour": 2, "code": "18CSC303J", "name": "Algorithms Lab", "room": "TP Lab 2", "faculty": "Dr. V. Meenakshi"},
    {"day": 5, "hour": 3, "code": "18CSC304J", "name": "Computer Networks Lab", "room": "TP Lab 4", "faculty": "Dr. S. Balasubramanian"},
    {"day": 5, "hour": 4, "code": "18CSC304J", "name": "Computer Networks Lab", "room": "TP Lab 4", "faculty": "Dr. S. Balasubramanian"}
]

EXAM_SEATING = [
    {
        "code": "18CSC305J",
        "name": "Deep Learning & Neural Architectures",
        "exam": "Continuous Learning Assessment 2 (CLA-2)",
        "date": "2026-09-15",
        "session": "FN",
        "time": "10:00 AM - 11:30 AM",
        "hall": "Tech Park 704",
        "seat": "TP-704-B12"
    },
    {
        "code": "18CSC302J",
        "name": "Operating Systems & Virtualization",
        "exam": "Continuous Learning Assessment 2 (CLA-2)",
        "date": "2026-09-17",
        "session": "FN",
        "time": "10:00 AM - 11:30 AM",
        "hall": "Tech Park 704",
        "seat": "TP-704-B12"
    },
    {
        "code": "18CSC303J",
        "name": "Design & Analysis of Algorithms",
        "exam": "Continuous Learning Assessment 2 (CLA-2)",
        "date": "2026-09-19",
        "session": "FN",
        "time": "10:00 AM - 11:30 AM",
        "hall": "Tech Park 602",
        "seat": "TP-602-C05"
    },
    {
        "code": "18CSC304J",
        "name": "Computer Networks & Protocols",
        "exam": "Continuous Learning Assessment 2 (CLA-2)",
        "date": "2026-09-22",
        "session": "FN",
        "time": "10:00 AM - 11:30 AM",
        "hall": "Tech Park 602",
        "seat": "TP-602-C05"
    }
]

def seed():
    database.init_db()
    conn = database.get_connection()
    cursor = conn.cursor()

    # 1. Seed Faculty User
    faculty = database.get_user_by_net_id("faculty_srm")
    if not faculty:
        faculty_id, _ = database.create_user(
            net_id="faculty_srm",
            name="Dr. Rajesh K. Sundaram",
            password="password123",
            role="teacher",
            department="Department of Computing Technologies",
            reg_no="EMP-CT-10492",
            semester="Faculty Member",
            avatar_path="/static/img/avatar_placeholder.svg"
        )
        print(f"[SEED] Created Faculty User: Dr. Rajesh K. Sundaram (ID #{faculty_id})")
    else:
        faculty_id = faculty["id"]

    # 2. Seed Students
    student_ids = []
    for idx, s in enumerate(DEMO_STUDENTS):
        existing = database.get_user_by_net_id(s["net_id"])
        if not existing:
            desc = generate_synthetic_descriptor(200 + idx)
            sid, _ = database.create_user(
                net_id=s["net_id"],
                name=s["name"],
                password="password123",
                role="student",
                department=s["dept"],
                reg_no=s["reg_no"],
                semester="5th Semester (B.Tech CSE)",
                avatar_path="/static/img/avatar_placeholder.svg",
                face_descriptor=desc
            )
            student_ids.append(sid)
            print(f"  + Enrolled Student: {s['name']} ({s['reg_no']})")
        else:
            student_ids.append(existing["id"])

    # 3. Seed Classrooms (Google Classroom Style)
    created_classes = []
    for c in CLASSROOMS:
        existing_class = database.get_classroom_by_code(c["code"])
        if not existing_class:
            cursor.execute("""
            INSERT INTO classrooms (code, name, course_code, section, teacher_id, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (c["code"], c["name"], c["course_code"], c["section"], faculty_id, c["desc"], "2026-08-01 09:00:00"))
            conn.commit()
            cid = cursor.lastrowid
            created_classes.append(cid)
            print(f"[SEED] Created Classroom: {c['name']} [Code: {c['code']}]")
        else:
            created_classes.append(existing_class["id"])

    # 4. Enroll all demo students into the seeded classrooms
    for cid in created_classes:
        for sid in student_ids:
            try:
                cursor.execute("""
                INSERT OR IGNORE INTO classroom_members (classroom_id, student_id, joined_at)
                VALUES (?, ?, '2026-08-02 10:00:00')
                """, (cid, sid))
            except Exception:
                pass
    conn.commit()

    # 5. Add Sample Classroom Stream Posts
    if created_classes:
        dl_class_id = created_classes[0]
        cursor.execute("SELECT COUNT(*) FROM classroom_posts WHERE classroom_id = ?", (dl_class_id,))
        if cursor.fetchone()[0] == 0:
            database.add_classroom_post(
                classroom_id=dl_class_id,
                author_id=faculty_id,
                author_name="Dr. Rajesh K. Sundaram",
                author_role="Faculty",
                content="Welcome to 18CSC305J Deep Learning & Neural Architectures! Please find the semester syllabus dossier, reference textbook (Goodfellow), and PyTorch setup instructions below. Next lecture will feature live AI Face Recognition attendance sweeps!",
                media_url="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=1000&auto=format&fit=crop",
                media_type="image"
            )
            database.add_classroom_post(
                classroom_id=dl_class_id,
                author_id=faculty_id,
                author_name="Dr. Rajesh K. Sundaram",
                author_role="Faculty",
                content="📢 ANNOUNCEMENT: CLA-2 Internal Exam is scheduled for September 15th at Tech Park Hall 704. Check your Academia Exam Seating Planner tab for your allocated desk number.",
                media_url="",
                media_type="none"
            )
            print("[SEED] Created classroom announcements and media posts.")

    # 6. Seed Student Academia Data (Courses, Timetable, Exams) for Aarav Sharma
    aarav = database.get_user_by_net_id("ra2211003010123")
    if aarav:
        aarav_id = aarav["id"]

        # Student Courses & Margins
        for sc in STUDENT_COURSES:
            cursor.execute("""
            INSERT OR IGNORE INTO student_courses 
            (student_id, course_code, course_name, faculty_name, total_hours, attended_hours, cla1_marks, cla2_marks, assignment_marks, model_marks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (aarav_id, sc["code"], sc["name"], sc["faculty"], sc["total"], sc["att"], sc["cla1"], sc["cla2"], sc["assign"], sc["model"]))
        
        # Timetable
        cursor.execute("SELECT COUNT(*) FROM timetable WHERE student_id = ?", (aarav_id,))
        if cursor.fetchone()[0] == 0:
            for t in TIMETABLE:
                cursor.execute("""
                INSERT INTO timetable (student_id, day_order, hour, course_code, course_name, room_no, faculty_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (aarav_id, t["day"], t["hour"], t["code"], t["name"], t["room"], t["faculty"]))

        # Exam Seating
        cursor.execute("SELECT COUNT(*) FROM exam_seating WHERE student_id = ?", (aarav_id,))
        if cursor.fetchone()[0] == 0:
            for ex in EXAM_SEATING:
                cursor.execute("""
                INSERT INTO exam_seating (student_id, course_code, course_name, exam_name, exam_date, exam_session, exam_time, hall_no, seat_no)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (aarav_id, ex["code"], ex["name"], ex["exam"], ex["date"], ex["session"], ex["time"], ex["hall"], ex["seat"]))

        conn.commit()
        print("[SEED] Seeded SRM Academia Timetable, Course Attendance Margins, and Exam Seating for Aarav Sharma.")

    # 7. Seed Default Active Camera Session
    active_sess = database.get_active_session()
    if not active_sess and created_classes:
        sess_id = database.create_session(
            session_name="Lecture 14: Convolutional Feature Maps",
            course_code="18CSC305J",
            notes="Tech Park Room 704 - Live Rotating Camera Sweep",
            classroom_id=created_classes[0]
        )
        print(f"[SEED] Seeded default attendance camera session ID #{sess_id}")

    conn.close()
    print("[SEED] SRM Academia & Google Classroom seeding completed successfully!")
    return database.get_all_students()

if __name__ == "__main__":
    seed()
