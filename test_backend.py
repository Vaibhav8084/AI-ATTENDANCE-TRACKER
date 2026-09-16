import unittest
import json
import os
import database
import export_service
import seed_data
from app import app

class TestAuraAttendanceCore(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        database.init_db()

    def test_01_health(self):
        response = self.app.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "ONLINE")
        self.assertIn("SRM Academia", data["system"])

    def test_02_seed_students(self):
        students = seed_data.seed()
        self.assertGreaterEqual(len(students), 8)
        first = students[0]
        self.assertIn("reg_no", first)
        self.assertIn("face_descriptor", first)
        self.assertEqual(len(first["face_descriptor"]), 128)

    def test_03_create_session_and_attendance(self):
        # 1. Create session
        res = self.app.post('/api/sessions', json={
            "course_code": "CS-999",
            "session_name": "Test Sweeper Session",
            "notes": "Automated verification test"
        })
        self.assertEqual(res.status_code, 201)
        sess_data = json.loads(res.data)["session"]
        session_id = sess_data["id"]

        # 2. Get a student to mark
        students = database.get_all_students()
        student = students[0]

        # 3. Mark attendance
        mark_res = self.app.post('/api/attendance/mark', json={
            "session_id": session_id,
            "student_id": student["id"],
            "confidence": 98.4
        })
        self.assertEqual(mark_res.status_code, 200)
        mark_data = json.loads(mark_res.data)
        self.assertTrue(mark_data["success"])
        self.assertEqual(mark_data["already_marked"], False)
        self.assertEqual(mark_data["student_id"], student["id"])

        # 4. Duplicate mark test (Anti-duplicate lock verification)
        dup_res = self.app.post('/api/attendance/mark', json={
            "session_id": session_id,
            "student_id": student["id"],
            "confidence": 99.1
        })
        self.assertEqual(dup_res.status_code, 200)
        dup_data = json.loads(dup_res.data)
        self.assertTrue(dup_data["success"])
        self.assertEqual(dup_data["already_marked"], True)

        # 5. Export CSV test
        csv_res = self.app.get(f'/api/export/csv/{session_id}')
        self.assertEqual(csv_res.status_code, 200)
        csv_text = csv_res.data.decode('utf-8')
        self.assertIn("AURA-SCAN 360", csv_text)
        self.assertIn(student["name"], csv_text)
        self.assertIn("PRESENT", csv_text)

        # 6. Complete session test
        comp_res = self.app.post(f'/api/sessions/{session_id}/complete')
        self.assertEqual(comp_res.status_code, 200)
        comp_data = json.loads(comp_res.data)["session"]
        self.assertEqual(comp_data["status"], "COMPLETED")
        self.assertEqual(comp_data["total_present"], 1)

if __name__ == "__main__":
    unittest.main()
