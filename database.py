import sqlite3
import json
import os
import random
import string
import math
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Users Table (Students & Faculty)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        net_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT DEFAULT '',
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'teacher')),
        department TEXT DEFAULT 'Computer Science & Engineering',
        reg_no TEXT DEFAULT '',
        semester TEXT DEFAULT '5th Semester',
        avatar_path TEXT DEFAULT '',
        face_descriptor TEXT DEFAULT '[]',
        created_at TEXT NOT NULL
    );
    """)

    # 2. Classrooms Table (Google Classroom style)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS classrooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        course_code TEXT NOT NULL,
        section TEXT DEFAULT 'CSE-A',
        teacher_id INTEGER NOT NULL,
        description TEXT DEFAULT '',
        theme_color TEXT DEFAULT 'bronze',
        created_at TEXT NOT NULL,
        FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 3. Classroom Memberships (Students joined via class code)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS classroom_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        classroom_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        joined_at TEXT NOT NULL,
        FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(classroom_id, student_id)
    );
    """)

    # 4. Classroom Stream Posts (Announcements, media, links)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS classroom_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        classroom_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        author_name TEXT NOT NULL,
        author_role TEXT NOT NULL,
        content TEXT NOT NULL,
        media_url TEXT DEFAULT '',
        media_type TEXT DEFAULT 'none' CHECK(media_type IN ('none', 'image', 'video', 'link', 'file')),
        created_at TEXT NOT NULL,
        FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE,
        FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 5. Course Attendance & Margin Table (SRM Academia style)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_code TEXT NOT NULL,
        course_name TEXT NOT NULL,
        course_type TEXT DEFAULT 'Theory + Practical',
        faculty_name TEXT NOT NULL,
        total_hours INTEGER DEFAULT 40,
        attended_hours INTEGER DEFAULT 34,
        cla1_marks REAL DEFAULT 0.0,
        cla2_marks REAL DEFAULT 0.0,
        assignment_marks REAL DEFAULT 0.0,
        model_marks REAL DEFAULT 0.0,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(student_id, course_code)
    );
    """)

    # 6. SRM Timetable Table (Day Order 1-5, Hours 1-8)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        day_order INTEGER NOT NULL,
        hour INTEGER NOT NULL,
        course_code TEXT NOT NULL,
        course_name TEXT NOT NULL,
        room_no TEXT NOT NULL,
        faculty_name TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 7. Exam Seating Planner Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_seating (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_code TEXT NOT NULL,
        course_name TEXT NOT NULL,
        exam_name TEXT NOT NULL,
        exam_date TEXT NOT NULL,
        exam_session TEXT NOT NULL,
        exam_time TEXT NOT NULL,
        hall_no TEXT NOT NULL,
        seat_no TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 8. Attendance Sessions (Linked to Classrooms)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        classroom_id INTEGER DEFAULT NULL,
        session_name TEXT NOT NULL,
        course_code TEXT NOT NULL,
        date_time TEXT NOT NULL,
        total_enrolled INTEGER DEFAULT 0,
        total_present INTEGER DEFAULT 0,
        status TEXT DEFAULT 'ACTIVE',
        notes TEXT DEFAULT '',
        FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE SET NULL
    );
    """)

    # 9. Attendance Records (Student Biometric Proofs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        confidence REAL NOT NULL,
        snapshot_path TEXT DEFAULT '',
        status TEXT DEFAULT 'PRESENT',
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(session_id, student_id)
    );
    """)

    # Migration: Ensure classroom_id exists in sessions table
    try:
        cursor.execute("ALTER TABLE sessions ADD COLUMN classroom_id INTEGER DEFAULT NULL")
    except Exception:
        pass

    conn.commit()
    conn.close()
    print("[DB] SRM Academia & Google Classroom Database schema initialized.")

# --- Helper Functions ---

def generate_class_code(length=6):
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(chars, k=length))

def calculate_margin(attended, total, target_pct=75.0):
    """
    SRM Academia Margin Calculator:
    - If percentage >= 75%: Margin = floor((attended - 0.75 * total) / 0.75) -> can skip N classes!
    - If percentage < 75%: Deficit = ceil((0.75 * total - attended) / 0.25) -> must attend N classes!
    """
    if total <= 0:
        return {"percentage": 100.0, "status": "safe", "margin": 0, "text": "0 classes conducted"}
    
    pct = round((attended / total) * 100, 1)
    target = target_pct / 100.0

    if pct >= target_pct:
        # Number of classes student can safely skip while staying >= 75%
        safe_skips = math.floor((attended - target * total) / target)
        safe_skips = max(0, safe_skips)
        return {
            "percentage": pct,
            "status": "safe",
            "margin": safe_skips,
            "text": f"+{safe_skips} classes can be safely missed" if safe_skips > 0 else "On the border (attend next class)"
        }
    else:
        # Number of consecutive classes student must attend to recover to >= 75%
        deficit = math.ceil((target * total - attended) / (1.0 - target))
        deficit = max(1, deficit)
        return {
            "percentage": pct,
            "status": "critical",
            "margin": -deficit,
            "text": f"Must attend next {deficit} consecutive classes to reach 75%"
        }

# --- User & Auth Operations ---

def get_user_by_net_id(net_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(net_id) = LOWER(?) OR LOWER(reg_no) = LOWER(?)", (net_id.strip(), net_id.strip()))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    user = dict(row)
    try:
        user["face_descriptor"] = json.loads(user["face_descriptor"])
    except Exception:
        user["face_descriptor"] = []
    return user

def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    user = dict(row)
    try:
        user["face_descriptor"] = json.loads(user["face_descriptor"])
    except Exception:
        user["face_descriptor"] = []
    return user

def create_user(net_id, name, password, role='student', department='Computer Science & Engineering', reg_no='', semester='5th Semester', avatar_path='', face_descriptor=None):
    if face_descriptor is None:
        face_descriptor = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO users (net_id, name, password, role, department, reg_no, semester, avatar_path, face_descriptor, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (net_id.strip(), name.strip(), password, role, department, reg_no.strip(), semester, avatar_path, json.dumps(face_descriptor), now_str))
        conn.commit()
        return cursor.lastrowid, None
    except sqlite3.IntegrityError:
        return None, f"User with ID '{net_id}' already exists."
    finally:
        conn.close()

def get_all_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role = 'student' ORDER BY name ASC")
    rows = cursor.fetchall()
    students = []
    for r in rows:
        item = dict(r)
        try:
            item["face_descriptor"] = json.loads(item["face_descriptor"])
        except Exception:
            item["face_descriptor"] = []
        students.append(item)
    conn.close()
    return students

# --- Classroom Operations (Google Classroom style) ---

def create_classroom(name, course_code, section, teacher_id, description=''):
    conn = get_connection()
    cursor = conn.cursor()
    code = f"SRM-{generate_class_code(4)}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO classrooms (code, name, course_code, section, teacher_id, description, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (code, name, course_code, section, teacher_id, description, now_str))
    conn.commit()
    class_id = cursor.lastrowid
    conn.close()
    return class_id, code

def get_classroom_by_id(classroom_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT c.*, u.name as teacher_name, u.email as teacher_email
    FROM classrooms c
    JOIN users u ON c.teacher_id = u.id
    WHERE c.id = ?
    """, (classroom_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_classroom_by_code(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classrooms WHERE UPPER(code) = UPPER(?)", (code.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def join_classroom(classroom_code, student_id):
    classroom = get_classroom_by_code(classroom_code)
    if not classroom:
        return None, "Invalid Class Code. Please check the code provided by your faculty."
    
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("""
        INSERT INTO classroom_members (classroom_id, student_id, joined_at)
        VALUES (?, ?, ?)
        """, (classroom["id"], student_id, now_str))
        conn.commit()
        return classroom, None
    except sqlite3.IntegrityError:
        return classroom, "You are already enrolled in this classroom."
    finally:
        conn.close()

def get_user_classrooms(user_id, role):
    conn = get_connection()
    cursor = conn.cursor()
    if role == 'teacher':
        cursor.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM classroom_members WHERE classroom_id = c.id) as student_count,
               u.name as teacher_name
        FROM classrooms c
        JOIN users u ON c.teacher_id = u.id
        WHERE c.teacher_id = ?
        ORDER BY c.id DESC
        """, (user_id,))
    else:
        cursor.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM classroom_members WHERE classroom_id = c.id) as student_count,
               u.name as teacher_name
        FROM classrooms c
        JOIN classroom_members m ON c.id = m.classroom_id
        JOIN users u ON c.teacher_id = u.id
        WHERE m.student_id = ?
        ORDER BY c.id DESC
        """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_classroom_members(classroom_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT u.id, u.name, u.reg_no, u.net_id, u.email, u.department, u.avatar_path, u.face_descriptor, m.joined_at
    FROM users u
    JOIN classroom_members m ON u.id = m.student_id
    WHERE m.classroom_id = ?
    ORDER BY u.name ASC
    """, (classroom_id,))
    rows = cursor.fetchall()
    students = []
    for r in rows:
        item = dict(r)
        try:
            item["face_descriptor"] = json.loads(item["face_descriptor"])
        except Exception:
            item["face_descriptor"] = []
        students.append(item)
    conn.close()
    return students

# --- Classroom Stream Posts ---

def add_classroom_post(classroom_id, author_id, author_name, author_role, content, media_url='', media_type='none'):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO classroom_posts (classroom_id, author_id, author_name, author_role, content, media_url, media_type, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (classroom_id, author_id, author_name, author_role, content, media_url, media_type, now_str))
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return post_id

def get_classroom_posts(classroom_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, u.avatar_path as author_avatar
    FROM classroom_posts p
    JOIN users u ON p.author_id = u.id
    WHERE p.classroom_id = ?
    ORDER BY p.id DESC
    """, (classroom_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Student Academia Data (Attendance, Margins, Timetable, Exams) ---

def ensure_student_records(student_id):
    """Ensures a student has complete SRM KTR courses, day-order timetable, and exam seating."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if courses already exist
    cursor.execute("SELECT COUNT(*) FROM student_courses WHERE student_id = ?", (student_id,))
    if cursor.fetchone()[0] == 0:
        default_courses = [
            ("21CSC201J", "Data Structures and Algorithms", "Theory + Practical", "Dr. C. Lakshmi", 42, 38, 24.0, 23.5, 9.5, 47.0),
            ("21CSC202J", "Operating Systems & Virtualization", "Theory + Practical", "Dr. E. Poovammal", 38, 32, 22.0, 21.5, 9.0, 44.0),
            ("21CSC203J", "Design and Analysis of Algorithms", "Theory + Practical", "Dr. B. Amutha", 40, 31, 20.0, 20.5, 8.5, 40.5),
            ("21CSC204J", "Computer Organization and Architecture", "Theory + Practical", "Dr. S. S. Sridhar", 36, 26, 18.5, 19.0, 8.0, 37.0),
            ("21MTH201B", "Probability & Statistics", "Theory", "Dr. K. Vijayakumar", 30, 28, 23.0, 24.0, 9.5, 48.0)
        ]
        for code, name, c_type, fac, tot, att, c1, c2, ass, mdl in default_courses:
            cursor.execute("""
            INSERT OR IGNORE INTO student_courses 
            (student_id, course_code, course_name, course_type, faculty_name, total_hours, attended_hours, cla1_marks, cla2_marks, assignment_marks, model_marks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (student_id, code, name, c_type, fac, tot, att, c1, c2, ass, mdl))

    # Check if timetable already exists
    cursor.execute("SELECT COUNT(*) FROM timetable WHERE student_id = ?", (student_id,))
    if cursor.fetchone()[0] == 0:
        default_tt = [
            (1, 1, "21CSC201J", "Data Structures & Algorithms", "TP-704", "Dr. C. Lakshmi"),
            (1, 2, "21CSC202J", "Operating Systems", "TP-704", "Dr. E. Poovammal"),
            (1, 3, "21CSC203J", "Algorithms Design", "TP-704", "Dr. B. Amutha"),
            (1, 4, "21CSC204J", "Computer Architecture", "TP-704", "Dr. S. S. Sridhar"),
            (1, 5, "21CSC201J", "DSA Programming Lab", "Tech Park Lab 3", "Dr. C. Lakshmi"),
            (1, 6, "21CSC201J", "DSA Programming Lab", "Tech Park Lab 3", "Dr. C. Lakshmi"),
            (2, 1, "21CSC203J", "Algorithms Design", "TP-704", "Dr. B. Amutha"),
            (2, 2, "21CSC204J", "Computer Architecture", "TP-704", "Dr. S. S. Sridhar"),
            (2, 3, "21CSC201J", "Data Structures & Algorithms", "TP-704", "Dr. C. Lakshmi"),
            (2, 4, "21CSC202J", "Operating Systems", "TP-704", "Dr. E. Poovammal"),
            (2, 5, "21MTH201B", "Probability & Statistics", "UB-602", "Dr. K. Vijayakumar"),
            (3, 1, "21CSC202J", "OS Internals Lab", "Tech Park Lab 5", "Dr. E. Poovammal"),
            (3, 2, "21CSC202J", "OS Internals Lab", "Tech Park Lab 5", "Dr. E. Poovammal"),
            (3, 3, "21CSC201J", "Data Structures & Algorithms", "TP-704", "Dr. C. Lakshmi"),
            (3, 4, "21CSC203J", "Algorithms Design", "TP-704", "Dr. B. Amutha"),
            (4, 1, "21CSC204J", "Computer Architecture", "TP-704", "Dr. S. S. Sridhar"),
            (4, 2, "21CSC201J", "Data Structures & Algorithms", "TP-704", "Dr. C. Lakshmi"),
            (4, 3, "21CSC202J", "Operating Systems", "TP-704", "Dr. E. Poovammal"),
            (4, 4, "21CSC203J", "Algorithms Design", "TP-704", "Dr. B. Amutha"),
            (5, 1, "21CSC203J", "Algorithms Practical Lab", "Tech Park Lab 2", "Dr. B. Amutha"),
            (5, 2, "21CSC203J", "Algorithms Practical Lab", "Tech Park Lab 2", "Dr. B. Amutha"),
            (5, 3, "21CSC204J", "Architecture Simulator Lab", "Tech Park Lab 4", "Dr. S. S. Sridhar"),
            (5, 4, "21CSC204J", "Architecture Simulator Lab", "Tech Park Lab 4", "Dr. S. S. Sridhar")
        ]
        for day, hr, code, name, room, fac in default_tt:
            cursor.execute("""
            INSERT INTO timetable (student_id, day_order, hour, course_code, course_name, room_no, faculty_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (student_id, day, hr, code, name, room, fac))

    # Check if exam seating exists
    cursor.execute("SELECT COUNT(*) FROM exam_seating WHERE student_id = ?", (student_id,))
    if cursor.fetchone()[0] == 0:
        default_exams = [
            ("21CSC201J", "Data Structures and Algorithms", "Continuous Learning Assessment 2", "2026-10-14", "FN", "10:00 AM - 11:45 AM", "TP-401 (Tech Park 4th Floor)", "R-14"),
            ("21CSC202J", "Operating Systems & Virtualization", "Continuous Learning Assessment 2", "2026-10-16", "FN", "10:00 AM - 11:45 AM", "TP-401 (Tech Park 4th Floor)", "R-14"),
            ("21CSC203J", "Design and Analysis of Algorithms", "Continuous Learning Assessment 2", "2026-10-18", "FN", "10:00 AM - 11:45 AM", "TP-502 (Tech Park 5th Floor)", "S-08"),
            ("21CSC204J", "Computer Organization and Architecture", "Continuous Learning Assessment 2", "2026-10-21", "FN", "10:00 AM - 11:45 AM", "UB-702 (University Building)", "A-22"),
            ("21MTH201B", "Probability & Statistics", "Continuous Learning Assessment 2", "2026-10-23", "FN", "10:00 AM - 11:45 AM", "UB-702 (University Building)", "A-22")
        ]
        for c_code, c_name, ex_name, ex_date, ex_sess, ex_time, hall, seat in default_exams:
            cursor.execute("""
            INSERT INTO exam_seating (student_id, course_code, course_name, exam_name, exam_date, exam_session, exam_time, hall_no, seat_no)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (student_id, c_code, c_name, ex_name, ex_date, ex_sess, ex_time, hall, seat))

    # Auto-enroll in existing classrooms
    cursor.execute("SELECT id FROM classrooms")
    for row in cursor.fetchall():
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT OR IGNORE INTO classroom_members (classroom_id, student_id, joined_at) VALUES (?, ?, ?)", (row[0], student_id, now_str))
        except Exception:
            pass

    conn.commit()
    conn.close()

def get_student_courses_with_margin(student_id):
    ensure_student_records(student_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_courses WHERE student_id = ? ORDER BY course_code ASC", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    
    courses = []
    for r in rows:
        c = dict(r)
        margin_info = calculate_margin(c["attended_hours"], c["total_hours"])
        c.update(margin_info)
        courses.append(c)
    return courses

def get_student_timetable(student_id):
    ensure_student_records(student_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM timetable WHERE student_id = ? ORDER BY day_order ASC, hour ASC", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_student_exam_seating(student_id):
    ensure_student_records(student_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exam_seating WHERE student_id = ? ORDER BY exam_date ASC", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Attendance Sessions & Biometric Marks ---

def create_session(session_name, course_code, notes='', classroom_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if classroom_id:
        cursor.execute("SELECT COUNT(*) FROM classroom_members WHERE classroom_id = ?", (classroom_id,))
        total_enrolled = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
        total_enrolled = cursor.fetchone()[0]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO sessions (classroom_id, session_name, course_code, date_time, total_enrolled, total_present, status, notes)
    VALUES (?, ?, ?, ?, ?, 0, 'ACTIVE', ?)
    """, (classroom_id, session_name, course_code, now_str, total_enrolled, notes))
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return session_id

def get_session(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_active_session():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_sessions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def complete_session(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT student_id) FROM attendance_records WHERE session_id = ?", (session_id,))
    present_count = cursor.fetchone()[0]
    cursor.execute("UPDATE sessions SET status = 'COMPLETED', total_present = ? WHERE id = ?", (present_count, session_id))
    conn.commit()
    conn.close()
    return True

def mark_attendance(session_id, student_id, confidence, snapshot_path=''):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute("""
        INSERT INTO attendance_records (session_id, student_id, timestamp, confidence, snapshot_path, status)
        VALUES (?, ?, ?, ?, ?, 'PRESENT')
        """, (session_id, student_id, now_str, round(float(confidence), 2), snapshot_path))
        
        cursor.execute("SELECT COUNT(DISTINCT student_id) FROM attendance_records WHERE session_id = ?", (session_id,))
        present_count = cursor.fetchone()[0]
        cursor.execute("UPDATE sessions SET total_present = ? WHERE id = ?", (present_count, session_id))
        
        # Also increment attended hours in student_courses if session matches course_code!
        cursor.execute("SELECT course_code FROM sessions WHERE id = ?", (session_id,))
        sess_row = cursor.fetchone()
        if sess_row and sess_row["course_code"]:
            cursor.execute("""
            UPDATE student_courses 
            SET attended_hours = attended_hours + 1, total_hours = total_hours + 1
            WHERE student_id = ? AND course_code = ?
            """, (student_id, sess_row["course_code"]))
        
        conn.commit()
        record_id = cursor.lastrowid
        
        cursor.execute("SELECT reg_no, name, department, avatar_path FROM users WHERE id = ?", (student_id,))
        stu = cursor.fetchone()
        
        return {
            "success": True,
            "record_id": record_id,
            "session_id": session_id,
            "student_id": student_id,
            "student_name": stu["name"] if stu else "Unknown",
            "roll_no": stu["reg_no"] if stu else "",
            "department": stu["department"] if stu else "",
            "avatar_path": stu["avatar_path"] if stu else "",
            "timestamp": now_str,
            "confidence": round(float(confidence), 2),
            "snapshot_path": snapshot_path,
            "total_present": present_count,
            "already_marked": False
        }, None
    except sqlite3.IntegrityError:
        cursor.execute("SELECT * FROM attendance_records WHERE session_id = ? AND student_id = ?", (session_id, student_id))
        existing = cursor.fetchone()
        cursor.execute("SELECT reg_no, name, department, avatar_path FROM users WHERE id = ?", (student_id,))
        stu = cursor.fetchone()
        return {
            "success": True,
            "record_id": existing["id"],
            "session_id": session_id,
            "student_id": student_id,
            "student_name": stu["name"] if stu else "Unknown",
            "roll_no": stu["reg_no"] if stu else "",
            "department": stu["department"] if stu else "",
            "avatar_path": stu["avatar_path"] if stu else "",
            "timestamp": existing["timestamp"],
            "confidence": existing["confidence"],
            "snapshot_path": existing["snapshot_path"],
            "already_marked": True
        }, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

def get_session_attendance(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        u.id as student_id,
        u.reg_no as roll_no,
        u.name,
        u.department,
        u.email,
        u.avatar_path,
        r.id as record_id,
        r.timestamp,
        r.confidence,
        r.snapshot_path,
        CASE WHEN r.id IS NOT NULL THEN 'PRESENT' ELSE 'ABSENT' END as attendance_status
    FROM users u
    LEFT JOIN attendance_records r ON u.id = r.student_id AND r.session_id = ?
    WHERE u.role = 'student'
    ORDER BY u.name ASC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_dashboard_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM classrooms")
    total_classrooms = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sessions")
    total_sessions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance_records")
    total_attendances = cursor.fetchone()[0]

    conn.close()
    return {
        "total_students": total_students,
        "total_classrooms": total_classrooms,
        "total_sessions": total_sessions,
        "total_attendances": total_attendances
    }
