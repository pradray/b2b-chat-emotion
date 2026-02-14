# Backend API Service

## Overview
This folder contains a lightweight Flask backend that wraps a Lambda-style handler and exposes a `/chat` endpoint used by the frontend.

## Prerequisites
- **Python:** Python 3.8 or newer installed.
- **Tools:** `git` and a POSIX shell (macOS/Linux) or PowerShell on Windows.

## Setup

### Update GROQ API Key
**Get the GROQ API Key:** This is necessary fallback mechanism for emotion detection when non-LLM procedures fail
 - Navigate to [GROQ API KEY CONSOLE](https://console.groq.com/keys)
 - Create a new Key
 - Add it against GROQ_API_KEY environment variable in `.env`

### Create Virtual Environment

**macOS / Linux / zsh:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install Requirements
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Run the Server
Start the Flask server (default port 5000):
```bash
python server.py
```
The server exposes `POST /chat` which the frontend calls. The request/response format is JSON.

### Quick Test (curl)
```bash
curl -X POST http://127.0.0.1:5000/chat \
	-H "Content-Type: application/json" \
	-d '{"message":"Hello"}'
```

## Files

### Core Modules
- **`server.py`**: Flask entrypoint — defines the `/chat` route and starts the local server.
- **`lambda_function.py`**: Core business logic and `lambda_handler` used by `server.py`.
- **`semantic_nlu.py`**: Hybrid NLU engine using `SentenceTransformers` and fuzzy matching.
- **`dialog_manager.py`**: Manages conversation state, flows (RFQ, Pricing), and context.
- **`entity_extractor.py`**: Regex and fuzzy-based extraction for products, dates, and quantities.
- **`empathetic_responses.py`**: Generates emotion-aware responses based on detected sentiment.
- **`emotion_detector.py`**: Analyzes text sentiment using VADER.
- **`context_manager.py`**: Handles conversation memory, topic tracking, and reference resolution.
- **`llm_fallback.py`**: Fallback logic using Groq API when NLU confidence is low.
- **`debug_nlu.py`**: Standalone script for debugging NLU intent classification.

### Verification & Testing
- **`verify_nlu.py`**: Regression testing script for NLU accuracy (`SentenceTransformers`).
- **`verify_entities.py`**: Tests for entity extraction (regex/fuzzy) accuracy.
- **`verify_flows.py`**: Verifies multi-turn dialog flows (RFQ, Pricing).
- **`verify_robustness.py`**: Tests keyword short-circuiting for Cancel and OOS intents.
- **`verify_switch.py`**: Verifies mid-flow topic switching and context updates.
- **`test_emotion_detector.py`**: Unit tests for emotion detection logic.

### Configuration
- **`requirements.txt`**: Python dependencies required by the backend.

## Troubleshooting

- **Port in use:** If port 5000 is already in use, stop the other process or change the port in `app.run(...)` inside `server.py`.
- **Missing packages:** Ensure the virtual environment is activated and run `pip install -r requirements.txt`.
- **CORS issues:** CORS is enabled in `server.py` so the Vite frontend (default port 5173) can call the backend; if you still see CORS errors, verify the frontend origin and the backend configuration.

## Notes
The backend implements a thin wrapper around the local Lambda-style handler in `lambda_function.py`. The frontend expects a JSON response with `message` (and optional `action`) fields.

When sharing or deploying, remember to secure any secrets and follow environment-specific deployment practices.

