# Standard system and utility imports
import sys
import os
import json
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from lambda_function import lambda_handler

# Test Dataset (Subset of original for speed, covering all intents)
TEST_DATA = [
    # GREETING / FAREWELL
    ("Hello", "GREETING"),
    ("Hi there", "GREETING"),
    ("Goodbye", "FAREWELL"),
    ("Thanks, bye", "FAREWELL"),
    
    # PRODUCT_INQUIRY
    ("I need servo motors", "PRODUCT_INQUIRY"),
    ("Do you have pumps?", "PRODUCT_INQUIRY"),
    ("price of sensor", "INFO_PRICE"), # Often confused, let's see logic
    
    # INFO_PRICE
    ("How much is it?", "INFO_PRICE"),
    ("pricing list", "INFO_PRICE"),
    
    # INFO_MOQ
    ("What is the moq?", "INFO_MOQ"),
    ("minimum order quantity", "INFO_MOQ"),
    
    # INFO_LEADTIME
    ("When will it arrive?", "INFO_LEADTIME"),
    ("delivery time", "INFO_LEADTIME"),
    
    # INFO_SHIPPING
    ("Do you ship to India?", "INFO_SHIPPING"),
    ("shipping cost", "INFO_SHIPPING"),
    
    # RFQ / BULK
    ("I want to buy 500 units", "INFO_BULK"), # Maps to RFQ logic
    ("bulk order discount", "INFO_BULK"),
    
    # RFQ STATUS
    ("Status of RFQ REQ-12345", "INFO_RFQ_STATUS"),
    ("where is my order", "INFO_TRACK"),
    
    # NAVIGATION
    ("show me the marketplace", "NAV_MARKETPLACE"),
    ("go to supplier list", "NAV_SUPPLIER"),
    
    # OUT OF SCOPE
    ("tell me a joke", "OUT_OF_SCOPE"),
    ("what is the weather", "OUT_OF_SCOPE"),
    
    # CONTROL
    ("cancel", "CONTROL_CANCEL"),
    ("restart", "CONTROL_RESTART")
]

def run_tests():
    print("Running NLU Verification...")
    correct = 0
    total = len(TEST_DATA)
    details = []
    
    for i, (text, expected_intent) in enumerate(TEST_DATA):
        event = {"body": {"message": text, "sessionId": f"test-nlu-{i}"}}
        response = lambda_handler(event, None)
        body = response.get("body", {})
        if isinstance(body, str):
            body = json.loads(body)
            
        # The lambda handler returns 'debug_intent' in the body for verification
        detected = body.get("debug_intent", "UNKNOWN")
        
        # Mapping checks (some runtimes remap intents)
        # e.g. "Request for Quote" from lambda might be "PRODUCT_INQUIRY" + "request_quote" action
        # For simplicity, we check if detected matches expected OR if expected is a key part of response
        
        match = False
        if detected == expected_intent:
            match = True
        elif expected_intent == "Request for Quote" and body.get("action") == "rfq_form":
            match = True
        
        if match:
            correct += 1
        else:
            details.append(f"FAIL: '{text}' -> Got {detected}, Expected {expected_intent}")

    accuracy = (correct / total) * 100
    print(f"\nNLU Accuracy: {accuracy:.2f}% ({correct}/{total})")
    for d in details:
        print(d)
        
    return accuracy

if __name__ == "__main__":
    run_tests()
