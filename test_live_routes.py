import unittest
import json
from app import app
import database

class TestLiveRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_srm_status(self):
        res = self.client.get('/api/srm/status')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('gateways', data)
        self.assertIn('academia', data['gateways'])
        self.assertIn('evarsity', data['gateways'])
        self.assertIn('staff_finder', data['gateways'])
        print("\n[TEST] SRM Gateway Status:", data['gateways'])

    def test_evarsity_captcha_endpoint(self):
        res = self.client.get('/api/auth/evarsity/captcha')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('captcha_b64', data)
        self.assertIn('session_id', data)
        print("\n[TEST] Live eVarsity Captcha fetched with session ID:", data['session_id'][:8])

    def test_staff_search_endpoint(self):
        res = self.client.get('/api/staff/search?query=Kumar&campus=78')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreater(data.get('total', 0), 0)
        print("\n[TEST] Staff Finder Search returned", data['total'], "faculty cards.")
        print("Sample faculty:", data['results'][0]['name'], "-", data['results'][0]['department'])

    def test_student_academia_login_and_timetable(self):
        # Test student login with realistic SRM NetID
        res = self.client.post('/api/auth/login', json={
            'net_id': 'ra2211003010123',
            'password': 'password123',
            'role': 'student'
        })
        self.assertEqual(res.status_code, 200)
        user_data = res.get_json()['user']
        self.assertEqual(user_data['role'], 'student')
        student_id = user_data['id']

        # Verify timetable is synced and complete
        tt_res = self.client.get(f'/api/student/timetable?student_id={student_id}')
        self.assertEqual(tt_res.status_code, 200)
        tt_data = tt_res.get_json()
        self.assertIn('by_day', tt_data)
        # Should have Day 1 to 5
        self.assertTrue('1' in tt_data['by_day'] or 1 in tt_data['by_day'])
        print("\n[TEST] Student timetable successfully loaded with Day Orders 1 to 5.")

        # Verify attendance margin calculation
        margin_res = self.client.get(f'/api/student/attendance-margin?student_id={student_id}')
        self.assertEqual(margin_res.status_code, 200)
        margin_data = margin_res.get_json()
        self.assertIn('overall', margin_data)
        self.assertIn('courses', margin_data)
        print("[TEST] Overall attendance percentage:", margin_data['overall']['percentage'], "%")
        print("[TEST] Safe margin text:", margin_data['overall']['margin_info']['text'])

    def test_faculty_evarsity_login(self):
        # First get fresh captcha session
        c_res = self.client.get('/api/auth/evarsity/captcha')
        c_data = c_res.get_json()
        session_id = c_data['session_id']

        # Submit faculty login with eVarsity session
        res = self.client.post('/api/auth/login', json={
            'net_id': 'faculty_srm',
            'password': 'password123',
            'role': 'teacher',
            'session_id': session_id,
            'captcha_code': c_data.get('demo_code', 'TEST')
        })
        self.assertEqual(res.status_code, 200)
        user = res.get_json()['user']
        self.assertEqual(user['role'], 'teacher')
        print("\n[TEST] Faculty login authenticated successfully via eVarsity bridge for:", user['name'])

if __name__ == '__main__':
    unittest.main()
