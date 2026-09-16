import unittest
import json
import os
import database
import seed_data
from app import app

class TestSRMAcademiaHub(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        database.init_db()
        seed_data.seed()

    def test_01_student_auth(self):
        res = self.app.post('/api/auth/login', json={
            "net_id": "ra2211003010123",
            "password": "password123",
            "role": "student"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["user"]["name"], "Aarav Sharma")
        self.assertEqual(data["user"]["role"], "student")

    def test_02_faculty_auth(self):
        res = self.app.post('/api/auth/login', json={
            "net_id": "faculty_srm",
            "password": "password123",
            "role": "teacher"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("Rajesh", data["user"]["name"])
        self.assertEqual(data["user"]["role"], "teacher")

    def test_03_create_and_join_classroom(self):
        # 1. Faculty creates classroom
        faculty = database.get_user_by_net_id("faculty_srm")
        res = self.app.post('/api/classrooms', json={
            "name": "Cloud Computing & Distributed Systems",
            "course_code": "18CSC308J",
            "section": "CSE-C",
            "teacher_id": faculty["id"],
            "description": "AWS, GCP, Kubernetes and distributed consensus protocols."
        })
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        class_code = data["class_code"]
        class_id = data["classroom"]["id"]
        self.assertTrue(class_code.startswith("SRM-"))

        # 2. Student joins via class code
        student = database.get_user_by_net_id("ra2211003010123")
        join_res = self.app.post('/api/classrooms/join', json={
            "code": class_code,
            "student_id": student["id"]
        })
        self.assertEqual(join_res.status_code, 200)

        # 3. Post an announcement to classroom stream
        post_res = self.app.post(f'/api/classrooms/{class_id}/posts', json={
            "content": "Lecture 01 slides on Distributed Consensus and Paxos are uploaded.",
            "author_id": faculty["id"],
            "media_url": "https://example.com/slides.pdf",
            "media_type": "link"
        })
        self.assertEqual(post_res.status_code, 201)

        # 4. Fetch stream and verify post
        stream_res = self.app.get(f'/api/classrooms/{class_id}')
        self.assertEqual(stream_res.status_code, 200)
        stream_data = json.loads(stream_res.data)
        self.assertGreaterEqual(len(stream_data["posts"]), 1)
        self.assertGreaterEqual(len(stream_data["members"]), 1)

    def test_04_attendance_margin_calculator(self):
        student = database.get_user_by_net_id("ra2211003010123")
        res = self.app.get(f'/api/student/attendance-margin?student_id={student["id"]}')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("courses", data)
        self.assertIn("overall", data)

        # Test margin math
        for c in data["courses"]:
            self.assertIn("margin", c)
            self.assertIn("status", c)
            if c["course_code"] == "18CSC305J": # 38/42 = 90.5%
                self.assertEqual(c["status"], "safe")
                self.assertGreater(c["margin"], 0)
            elif c["course_code"] == "18CSC304J": # 26/38 = 68.4%
                self.assertEqual(c["status"], "critical")
                self.assertLess(c["margin"], 0)

    def test_05_timetable_and_exam_seating(self):
        student = database.get_user_by_net_id("ra2211003010123")
        
        # Timetable
        tt_res = self.app.get(f'/api/student/timetable?student_id={student["id"]}')
        self.assertEqual(tt_res.status_code, 200)
        tt_data = json.loads(tt_res.data)
        self.assertIn("by_day", tt_data)
        self.assertTrue("1" in tt_data["by_day"] or 1 in tt_data["by_day"])

        # Exam Seating
        seat_res = self.app.get(f'/api/student/seating?student_id={student["id"]}')
        self.assertEqual(seat_res.status_code, 200)
        seat_data = json.loads(seat_res.data)
        self.assertGreaterEqual(len(seat_data["seating_plan"]), 1)
        first_exam = seat_data["seating_plan"][0]
        self.assertEqual(first_exam["hall_no"], "Tech Park 704")
        self.assertEqual(first_exam["seat_no"], "TP-704-B12")

if __name__ == "__main__":
    unittest.main()
