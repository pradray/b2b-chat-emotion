# System utilities and testing framework
import sys
import unittest
# Import the Lambda handler to test NLU behavior
from lambda_function import lambda_handler

class TestNLURobustness(unittest.TestCase):
    def setUp(self):
        self.session_id = "test_robustness_session"

    def send(self, text):
        event = {'body': {'message': text, 'sessionId': self.session_id}}
        return lambda_handler(event, None)

    def test_cancel_short_circuit(self):
        print("\n--- Test: Cancel Short-Circuit ---")
        import json
        # Common ways users may try to cancel a flow
        keywords = ["cancel", "stop", "abort", "terminate", "exit"]
        for word in keywords:
            print(f"Testing '{word}'...")
            resp = self.send(word)
            body = json.loads(resp['body'])
            self.assertIn("debug_intent", body)
            self.assertEqual(body["debug_intent"], "CONTROL_CANCEL", f"Failed for '{word}'")

    def test_oos_short_circuit(self):
        print("\n--- Test: OOS Short-Circuit ---")
        import json
        # 1. True OOS Phrases
        oos_phrases = [
            ("tell me a joke", "OUT_OF_SCOPE"),
            ("what is the weather", "OUT_OF_SCOPE"),
            ("who is the president", "OUT_OF_SCOPE"),
            ("i hate politics", "OUT_OF_SCOPE"),
            ("give me a recipe for cake", "OUT_OF_SCOPE")
        ]
        for phrase, expected in oos_phrases:
             print(f"Testing OOS '{phrase}'...")
             resp = self.send(phrase)
             body = json.loads(resp['body'])
             self.assertEqual(body["debug_intent"], "OUT_OF_SCOPE", f"Failed for '{phrase}'")
             # Loose check for OOS response
             self.assertTrue(
                 "assist with industrial parts" in body["message"] or
                 "focused on B2B" in body["message"],
                 f"Unexpected OOS message: {body['message']}"
             )

        # 2. Business Whitelist (Should NOT be OOS)
        biz_phrases = [
            ("I need a sales rep", ["HELP", "PRODUCT_INQUIRY", "NAV_SUPPLIER"]),
            ("speak to an agent", ["HELP", "PRODUCT_INQUIRY"])
        ]
        for phrase, allowed_intents in biz_phrases:
             print(f"Testing Whitelist '{phrase}'...")
             resp = self.send(phrase)
             body = json.loads(resp['body'])
             debug_intent = body.get('debug_intent', 'LLM_FALLBACK')
             print(f"  -> Got: {debug_intent}")
             self.assertNotEqual(debug_intent, "OUT_OF_SCOPE", f"Whitelist failed for '{phrase}'")

if __name__ == '__main__':
    unittest.main()
