
import sys
import os
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from entity_extractor import entity_extractor

TEST_DATA = [
    # Quantities
    ("I need 500 units", {"quantity": 500}),
    ("buy 10", {"quantity": 10}),
    ("20k pieces", {"quantity": 20000}),
    
    # Products
    ("price of servo motor", {"product": "servo motor"}),
    ("do you have pumps", {"product": "pump"}),
    ("quote for hydraulic cylinder", {"product": "hydraulic cylinder"}),
    
    # Dates
    ("need it by next friday", {"date": "next friday"}),
    ("delivery on 2024-12-01", {"date": "2024-12-01"}),
    
    # RFQ IDs
    ("status of REQ-123456", {"rfq_id": "REQ-123456"}),
    ("check order #REQ-999", {"rfq_id": "REQ-999"}),
    
    # Negatives
    ("min order quantity", {}), # Should NOT match "quantity" as entity
    ("what is the lead time", {})
]

if __name__ == "__main__":
    print("Running Entity Verification...")
    correct = 0
    total = len(TEST_DATA)
    
    for text, expected in TEST_DATA:
        # Expected is Dict[str, str|int]
        # Extracted is Dict[str, List[Entity]]
        
        extracted_dict = entity_extractor.extract_all(text)
        
        # Helper to simplify extracted dict for comparison
        simple_extracted = {}
        for key, entity_list in extracted_dict.items():
            if entity_list:
                # Take the first entity's value
                val = entity_list[0].value
                # Try to convert to int if it looks like one, for comparison
                try:
                    if isinstance(val, str) and val.replace(',','').isdigit():
                        # Don't convert yet, keep as is but handle comparison below
                        pass
                except:
                    pass
                simple_extracted[key] = val
        
        print(f"Input: '{text}'")
        print(f"  Expected: {expected}")
        print(f"  Got:      {simple_extracted}")
        
        # Check correctness
        match = True
        for key, exp_val in expected.items():
            if key not in simple_extracted:
                print(f"  FAIL: Missing key '{key}'")
                match = False
            else:
                got_val = simple_extracted[key]
                
                # Normalize for comparison (remove commas, handle string vs int)
                str_got = str(got_val).replace(',', '').lower()
                str_exp = str(exp_val).replace(',', '').lower()
                
                if str_got != str_exp:
                     print(f"  FAIL: Value mismatch for '{key}': expected '{exp_val}', got '{got_val}'")
                     match = False
        
        # Check for unexpected extra entities (false positives)
        if not expected and simple_extracted:
             print(f"  FAIL: Expected empty, got {simple_extracted}")
             match = False
             
        if match:
            print("  PASS")
            correct += 1
        else:
            print("  FAIL")
            
    score = (correct / total) * 100
    print(f"\nEntity Verification Score: {score:.2f}% ({correct}/{total})")
