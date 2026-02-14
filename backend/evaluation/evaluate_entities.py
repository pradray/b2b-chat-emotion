
import json
import sys
import os
from collections import defaultdict

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from entity_extractor import EntityExtractor
except ImportError:
    print("Error: Could not import backend modules. Run this script from backend/evaluation/")
    sys.exit(1)

def load_test_data(filepath: str) -> list:
    with open(filepath, 'r') as f:
        return json.load(f)

def run_evaluation():
    print("Loading Entity Extractor...")
    extractor = EntityExtractor()
    
    data_path = os.path.join(os.path.dirname(__file__), 'entity_test_data.json')
    try:
        test_data = load_test_data(data_path)
    except FileNotFoundError:
        print("entity_test_data.json not found.")
        return

    print(f"Evaluating {len(test_data)} entity samples...")
    print("-" * 60)
    
    total = len(test_data)
    exact_matches = 0
    partial_matches = 0
    failures = 0
    
    # Per-entity type stats
    stats = {
        "product": {"total": 0, "correct": 0},
        "quantity": {"total": 0, "correct": 0}
    }

    for item in test_data:
        text = item['text']
        expected = item.get('entities', {})
        
        extracted = extractor.extract_all(text)
        
        # Convert extracted entities to dict for comparison {type: value}
        # EntityExtractor.extract_all returns Dict[str, List[Entity]]
        predicted_map = {}
        
        # We only care about product and quantity for this test
        for etype in ["product", "quantity"]:
            if etype in extracted:
                # Take the first/best match for comparison
                # In a real scenario we might match all, but for this benchmark we assume 1 per type
                entity = extracted[etype][0]
                predicted_map[entity.type] = str(entity.value).lower()
            
        # Compare
        is_exact = True
        match_count = 0
        
        # Check Expected vs Predicted
        for key, val in expected.items():
            stats[key]["total"] += 1
            pred_val = predicted_map.get(key)
            
            # Flexible match for singular/plural/canonical
            # Check if predicted is same, or singular of expected, or expected is singular of predicted
            p_val = pred_val
            e_val = str(val).lower()
            
            match = False
            if p_val:
                if p_val == e_val:
                    match = True
                elif p_val + 's' == e_val or p_val + 'es' == e_val:
                    match = True
                elif e_val + 's' == p_val or e_val + 'es' == p_val:
                    match = True
                # Handle y -> ies pluralization (battery -> batteries)
                elif p_val.endswith('y') and p_val[:-1] + 'ies' == e_val:
                    match = True
                elif e_val.endswith('y') and e_val[:-1] + 'ies' == p_val:
                    match = True
                # elif p_val in e_val or e_val in p_val: # Fallback substring match (disabled for strictness)
                #     match = True
            
            if match:
                stats[key]["correct"] += 1
                match_count += 1
            else:
                is_exact = False
                # Debug print for mismatch (limit to first few or just print)
                if match_count == 0 and key == "product":
                     print(f"Mismatch: Exp='{val}' vs Pred='{pred_val}'")
                
        # Check for hallucinations (Predicted has extra keys)
        if len(predicted_map) > len(expected):
            is_exact = False
            
        if is_exact:
            exact_matches += 1
        elif match_count > 0:
            partial_matches += 1
        else:
            failures += 1
            
    # Report
    print(f"Total Samples: {total}")
    print(f"Exact Matches: {exact_matches} ({exact_matches/total:.2%})")
    print(f"Partial Matches: {partial_matches} ({partial_matches/total:.2%})")
    print(f"Failures: {failures} ({failures/total:.2%})")
    
    print("\nPer-Entity Accuracy:")
    for entity_type, data in stats.items():
        if data["total"] > 0:
            acc = data["correct"] / data["total"]
            print(f"  {entity_type.capitalize()}: {acc:.2%} ({data['correct']}/{data['total']})")
        else:
             print(f"  {entity_type.capitalize()}: N/A (0 samples)")

if __name__ == "__main__":
    run_evaluation()
