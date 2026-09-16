import unittest
from srm_live_bridge import SRMStaffFinderClient, SRMEvarsityClient, SRMAcademiaClient

class TestSRMLiveBridge(unittest.TestCase):
    def test_staff_finder_search(self):
        print("\n--- Testing Live Staff Finder ---")
        results = SRMStaffFinderClient.search_staff("Kumar", campus="78")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        first = results[0]
        print(f"Found faculty: {first['name']} | {first['designation']} | {first['department']}")
        self.assertIn('name', first)
        self.assertIn('designation', first)
        self.assertIn('campus', first)

    def test_evarsity_captcha(self):
        print("\n--- Testing Live eVarsity Captcha Stream ---")
        res = SRMEvarsityClient.get_live_captcha()
        self.assertTrue(res['success'])
        self.assertTrue('captcha_b64' in res)
        self.assertTrue('session_id' in res)
        print(f"Retrieved Captcha from: {res['source']} (Session ID: {res['session_id'][:8]}...)")

    def test_gateway_status(self):
        print("\n--- Testing SRM Gateway Status Health Check ---")
        status = SRMAcademiaClient.get_gateway_status()
        self.assertIn('academia', status)
        self.assertIn('evarsity', status)
        self.assertIn('staff_finder', status)
        for k, v in status.items():
            print(f"{k}: online={v['online']}, latency={v['latency_ms']}ms, status={v['status']}")

if __name__ == '__main__':
    unittest.main()
