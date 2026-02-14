
import json
import sys
import os
from typing import Dict, List, Tuple
from collections import defaultdict

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from semantic_nlu import SemanticNLU, ENHANCED_INTENT_MAP
except ImportError:
    print("Error: Could not import backend modules. Run this script from backend/evaluation/")
    sys.exit(1)

def load_test_data(filepath: str) -> List[Dict]:
    """Load test data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def calculate_metrics(predictions: List[Tuple[str, str]]) -> Dict:
    """
    Calculate Precision, Recall, and F1 for each intent and overall.
    predictions: List of (actual, predicted) tuples
    """
    metrics = {}
    intents = set([p[0] for p in predictions] + [p[1] for p in predictions])
    
    # Per-intent metrics
    total_correct = 0
    
    for intent in intents:
        true_pos = sum(1 for act, pred in predictions if act == intent and pred == intent)
        false_pos = sum(1 for act, pred in predictions if act != intent and pred == intent)
        false_neg = sum(1 for act, pred in predictions if act == intent and pred != intent)
        
        precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0
        recall = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        metrics[intent] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "count": sum(1 for act, _ in predictions if act == intent)
        }
        total_correct += true_pos
        
    # Overall Accuracy
    metrics["overall"] = {
        "accuracy": total_correct / len(predictions) if predictions else 0,
        "total_samples": len(predictions)
    }
    
    return metrics

def generate_confusion_matrix(predictions: List[Tuple[str, str]]) -> Dict[str, Dict[str, int]]:
    """Generate confusion matrix dictionary."""
    matrix = defaultdict(lambda: defaultdict(int))
    for actual, predicted in predictions:
        matrix[actual][predicted] += 1
    return matrix

def print_report(metrics: Dict, confusion_matrix: Dict):
    """Print formatted evaluation report."""
    print("\n" + "="*60)
    print("NLU EVALUATION REPORT")
    print("="*60)
    
    overall = metrics.pop("overall")
    print(f"\nOverall Accuracy: {overall['accuracy']:.2%}")
    print(f"Total Samples:    {overall['total_samples']}")
    
    print("\n" + "-"*60)
    print(f"{'INTENT':<25} | {'PREC':<8} | {'REC':<8} | {'F1':<8} | {'COUNT':<5}")
    print("-" * 60)
    
    # Sort by Intent Name
    for intent in sorted(metrics.keys()):
        m = metrics[intent]
        print(f"{intent:<25} | {m['precision']:.2f}     | {m['recall']:.2f}     | {m['f1']:.2f}     | {m['count']}")
        
    print("-" * 60)
    
    print("\nCONFUSION MATRIX (Actual row, Predicted col)")
    # Identify intents with errors
    error_intents = set()
    for act, preds in confusion_matrix.items():
        for pred, count in preds.items():
            if act != pred:
                error_intents.add(act)
                
    if not error_intents:
        print("Perfect prediction! No confusion matrix needed.")
    else:
        # Simple list of confusions
        print("\nMajor Confusions (>0):")
        for actual in sorted(confusion_matrix.keys()):
            for predicted, count in confusion_matrix[actual].items():
                if actual != predicted:
                     print(f"  {actual:<20} -> Disclassified as {predicted:<20} ({count} times)")

def main():
    print("Loading Semantic NLU Model...")
    nlu = SemanticNLU()
    if not nlu.is_ready:
        print("Model failed to load.")
        return
        
    print("Registering Intents...")
    nlu.register_intents(ENHANCED_INTENT_MAP)
    
    print("Loading Test Data...")
    try:
        data = load_test_data(os.path.join(os.path.dirname(__file__), 'nlu_test_data.json'))
    except FileNotFoundError:
        print("nlu_test_data.json not found.")
        return
        
    print(f"Running evaluation on {len(data)} samples...")
    predictions = []
    
    for item in data:
        text = item['text']
        actual = item['intent']
        
        match = nlu.match_intent(text)
        predicted = match.intent if match else "NO_MATCH"
        
        predictions.append((actual, predicted))
        
    metrics = calculate_metrics(predictions)
    cm = generate_confusion_matrix(predictions)
    
    print_report(metrics, cm)

if __name__ == "__main__":
    main()
