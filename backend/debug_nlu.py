
import sys
import os
import json
import traceback

# Add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lambda_function import lambda_handler

def main():
    print("\n--- B2B Chat Pipeline Debugger (v11) ---")
    
    # Get text from args or default
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = input("Enter query: ")
    
    print(f"Input: '{text}'")
    
    try:
        # Simulate Lambda Event
        event = {"body": json.dumps({"message": text, "sessionId": "debug-session"})}
        
        # Invoke Handler
        response = lambda_handler(event, None)
        
        # Parse Body
        body_str = response.get("body", "{}")
        body = json.loads(body_str)
        
        # Extract Debug Info
        intent = body.get("debug_intent", "UNKNOWN")
        conf = body.get("debug_confidence", 0.0)
        method = body.get("debug_method", "unknown")
        entities = body.get("entities", {})
        product = entities.get("product", [None])[0]
        product_val = product if isinstance(product, str) else (product.get("value") if product else "None")
        
        # Visualizing the Pipeline
        print("\n[Pipeline Trace]")
        
        # Layer 1: Entities
        print(f"1. Entity Extraction   : {'[OK] ' + str(product_val) if product_val != 'None' else '[NO] No Product'}")
        
        # Layer 2: Guards / Layers
        layer = "Unknown"
        if method == "system_signal":
            layer = "Layer 0: System Signal"
        elif method == "keyword_short_circuit":
             if intent == "OUT_OF_SCOPE":
                 layer = "Layer 1: OOS Guard (Regex/Keyword)"
             else:
                 layer = "Layer 1: Control Guard (Cancel/Stop)"
        elif method == "topic_shift_correction":
            layer = "Layer 1.5: Context Switch (Topic Shift)"
        elif method == "semantic":
            layer = "Layer 2: Semantic NLU (SentenceTransformers)"
        elif method == "fuzzy":
            layer = "Layer 3: Fuzzy Matching (Levenshtein)"
        elif method == "llm_fallback":
            layer = "Layer 4: LLM Fallback (Groq/Llama3)"
        elif method == "keyword_correction":
            layer = "Layer 1.5: Deterministic Override"
            
        print(f"2. Resolution Layer    : {layer}")
        print(f"3. Matched Intent      : {intent} ({conf:.1%})")
        print(f"4. Response Message    : {body.get('message', '')[:100]}...")
        
        print("\n[Full JSON Dump]")
        print(json.dumps(body, indent=2))

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    main()
