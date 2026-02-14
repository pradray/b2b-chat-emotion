
# Standard library imports
import sys
import os
import json
import time

# Add the current file directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Import the AWS Lambda handler 
from lambda_function import lambda_handler

class DialogTester:
    def __init__(self, session_id):
              # Unique session ID to maintain conversation context
        self.session_id = session_id
        
    def send(self, text, expected_action=None, expected_text_phrases=[]):
        print(f"\nUSER: {text}")
        event = {"body": {"message": text, "sessionId": self.session_id}}
         # Invoke the lambda handler
        response = lambda_handler(event, None)
        # Extract response body
        body = response.get("body", {})
        if isinstance(body, str):
            body = json.loads(body)
            
        bot_msg = body.get("message", "")
        action = body.get("action")
        # Display bot output
        print(f"BOT: {bot_msg} (Action: {action})")
        
        passed = True
        if expected_action and action != expected_action:
            print(f"FAIL: Expected action '{expected_action}', got '{action}'")
            passed = False
            
        for phrase in expected_text_phrases:
            if phrase.lower() not in bot_msg.lower():
                print(f"FAIL: Expected phrase '{phrase}' in response")
                passed = False
                
        return passed

def run_flow_test():
    tester = DialogTester("flow_test_pricing_rfq")
    all_passed = True
    
    print("--- Testing Flow: Pricing -> RFQ ---")
    
    # 1. Ask for price
    if not tester.send("price of sensors", expected_text_phrases=["price", "quote"]):
        all_passed = False
        
    # 2. Confirm RFQ (The flow asks "Would you like to proceed with a custom quote?")
    if not tester.send("yes please", expected_action="rfq"):
        all_passed = False
        
    print(f"\n--- Flow Test Result: {'PASS' if all_passed else 'FAIL'} ---")
    return all_passed

def run_context_test():
    tester = DialogTester("flow_test_context")
    all_passed = True
    
    print("\n--- Testing Flow: Contextual Resolution ---")
    
    # 1. Establish context
    tester.send("do you have servo motors")
    
    # 2. Refer to "it"
    # Should resolve "it" to "servo motor" and give pricing/moq info
    if not tester.send("what is the price of it", expected_text_phrases=["servo motor"]):
        all_passed = False

    # 2b. Cancel flow to test topic shift cleanup
    tester.send("cancel")
        
    # 3. Topic Shift
    # "Actually I want pumps"
    if not tester.send("Actually I want pumps", expected_text_phrases=["pump"]):
        all_passed = False
        
    print(f"\n--- Context Test Result: {'PASS' if all_passed else 'FAIL'} ---")
    return all_passed

if __name__ == "__main__":
    p1 = run_flow_test()
    p2 = run_context_test()
    
    # Final consolidated test result
    if p1 and p2:
        print("\nALL FLOW TESTS PASSED")
    else:
        print("\nFLOW TESTS FAILED")
