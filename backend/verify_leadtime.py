# Python's built-in unit testing framework
import unittest
# Used to serialize and deserialize JSON payloads
import json
# Import the Lambda function handler
from lambda_function import lambda_handler

class TestLeadtimeOverride(unittest.TestCase):
    def send(self, text):
        return lambda_handler({'body': json.dumps({'message': text, 'sessionId': 'test_leadtime'})}, None)

    def test_leadtime_override(self):
        print("\n--- Test: Leadtime Override ---")
        phrases = [
            "how long to deliver",
            "how long to deliver 500 units",
            "lead time for bearings",
            "when will it arrive"
        ]
        # Run the same intent validation for each phrase
        for phrase in phrases:
            print(f"Testing '{phrase}'...")
            # Send the phrase to the lambda handler
            resp = self.send(phrase)
            # Parse the response body
            body = json.loads(resp['body'])
            # Extract detected intent for debugging/validation
            intent = body.get('debug_intent')
            print(f"  -> Intent: {intent}")
            
            # v11 Rule: "how long to deliver" MUST be INFO_LEADTIME
            # Previously it often matched INFO_SHIPPING due to fuzzy match
            self.assertEqual(intent, "INFO_LEADTIME", f"Failed override for '{phrase}'")

if __name__ == '__main__':
    try:
        # Initialize NLU if needed (done in lambda_function global scope, but good to be safe)
        from lambda_function import semantic_nlu
    except ImportError:
        pass
        
    unittest.main()
