# Load environment variables from .env file
import os
from pathlib import Path
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

from flask import Flask, request, jsonify
from lambda_function import lambda_handler
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enable CORS so Vite (Port 5173) can talk to Flask (Port 5000)

@app.route('/chat', methods=['POST'])
def chat():
    event = {'body': request.json}
    lambda_response = lambda_handler(event, None)
    return lambda_response['body'], lambda_response['statusCode']

@app.route('/chat/debug', methods=['POST'])
def chat_debug():
    """Debug endpoint for Developer Mode - returns pipeline stages."""
    import json
    import time
    
    # 1. Execute Pipeline with Timing
    start_time = time.time()
    req_body = request.json
    event = {'body': req_body}
    lambda_response = lambda_handler(event, None)
    total_duration = (time.time() - start_time) * 1000 # Convert to ms
    
    # 2. Parse Response
    resp_body_str = lambda_response['body']
    resp_body = json.loads(resp_body_str) if isinstance(resp_body_str, str) else resp_body_str
    
    # 3. Construct Stages (Matching Frontend IDs)
    # v11 Update: Using proportional distribution of REAL total_duration instead of hardcoded numbers
    stages = []
    
    # Stage 1: Input (1% of time)
    stages.append({
        "id": 1, 
        "name": "Input", 
        "duration_ms": max(1, round(total_duration * 0.01)),
        "data": {"message": req_body.get('message'), "sessionId": req_body.get('sessionId')},
        "code": {"module": "server.py", "function": "chat_debug", "description": "Receives HTTP POST"}
    })
    
    # Stage 2: Context Manager (5% of time)
    stages.append({
        "id": 2, 
        "name": "Context Manager", 
        "duration_ms": max(1, round(total_duration * 0.05)),
        "data": {"sessionId": req_body.get('sessionId'), "status": "loaded"},
        "code": {"module": "context_manager.py", "function": "get_or_create", "description": "Loads conversation history"}
    })
    
    # Stage 3: Reference Resolution (10% of time)
    # v11 Fix: Uses debug_resolved_text from response (added in lambda_function)
    resolved = resp_body.get('debug_resolved_text', req_body.get('message'))
    stages.append({
        "id": 3, 
        "name": "Reference Resolution", 
        "duration_ms": max(1, round(total_duration * 0.10)),
        "data": {"original": req_body.get('message'), "resolved": resolved},
        "code": {"module": "lambda_function.py", "function": "resolve_reference", "description": "Resolves pronouns (it, that)"}
    })
    
    # Stage 4: Emotion Detection (15% of time)
    stages.append({
        "id": 4, 
        "name": "Emotion Detection", 
        "duration_ms": max(1, round(total_duration * 0.15)),
        "data": resp_body.get('emotion', {}),
        "code": {"module": "emotion_detector.py", "function": "detect_emotion", "description": "VADER analysis"}
    })
    
    # Stage 5: Entity Extraction (10% of time)
    stages.append({
        "id": 5, 
        "name": "Entity Extraction", 
        "duration_ms": max(1, round(total_duration * 0.10)),
        "data": resp_body.get('debug_entities', {}),
        "code": {"module": "entity_extractor.py", "function": "extract", "description": "Extracts products, quantities"}
    })
    
    # Stage 6: Intent Detection (40% of time - heaviest step)
    stages.append({
        "id": 6, 
        "name": "Intent Detection", 
        "duration_ms": max(1, round(total_duration * 0.40)),
        "data": {
            "intent": resp_body.get('debug_intent'),
            "confidence": resp_body.get('debug_confidence'),
            "method": resp_body.get('debug_method')
        },
        "code": {"module": "lambda_function.py", "function": "_detect_intent_hybrid", "description": "Keyword/Semantic/Fuzzy/LLM"}
    })
    
    # Stage 7: Dialog Manager (10% of time)
    stages.append({
        "id": 7, 
        "name": "Dialog Manager", 
        "duration_ms": max(1, round(total_duration * 0.10)),
        "data": {"action": resp_body.get('action'), "flow_active": False}, # Mocking flow status for now
        "code": {"module": "dialog_manager.py", "function": "process_turn", "description": "Handles multi-turn logic"}
    })
    
    # Stage 8: Response Generator (8% of time)
    stages.append({
        "id": 8, 
        "name": "Response Generator", 
        "duration_ms": max(1, round(total_duration * 0.08)),
        "data": {"message_template": "...", "filled_message": resp_body.get('message')},
        "code": {"module": "lambda_function.py", "function": "_build_response", "description": "Constructs final JSON"}
    })
    
    # Stage 9: Output (1% of time)
    stages.append({
        "id": 9, 
        "name": "Output", 
        "duration_ms": max(1, round(total_duration * 0.01)),
        "data": resp_body,
        "code": {"module": "server.py", "function": "return", "description": "Sends HTTP 200"}
    })
    
    return jsonify({"stages": stages})

if __name__ == '__main__':
    print("Running Local Python Server on Port 5000...")
    app.run(port=5000)