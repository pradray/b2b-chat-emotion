# B2B Chat Application with Emotion Recognition

A conversational AI-powered B2B marketplace application featuring emotion-aware responses, voice chat capabilities, and a modern React frontend.

---

## Key Features

### Core Intelligence
- **Hybrid NLU Engine**: Combines Semantic Search (SentenceTransformers) and Fuzzy Matching for **better intent accuracy**.
- **Context-Aware Dialog**: Handles multi-turn conversations and **Topic Shifts** (e.g., switching from "Bearings" to "Actuators" preserves the pricing question).
- **Robust Guards**:
    - **Business Term Guard**: Whitelists non-product queries like "Account Manager" to prevent OOS false positives.
    - **OOS Guard**: Uses Regex + Product Entity checks to filter true out-of-scope queries.
    - **First-Mention Guard**: Prevents false context switching on the very first message.
- **Emotion Intelligence**: Detects user sentiment (Frustration, Anger, Happiness) using VADER and adjusts responses with empathy.

### Voice & Audio
- **Full Voice Chat**: Hands-free Speech-to-Text (STT) and Text-to-Speech (TTS) via Web Speech API.
- **Dynamic Voice Selection**: Automatically detects and lists all available system voices (e.g., Microsoft Zira, Google US English).
- **Audio Diagnostics**: Built-in microphone permission checks, volume visualizers, and audio testing tools.
- **Visual Feedback**: Real-time listening indicators and speaking animations.

### User Experience
- **Interactive Marketplace**: Uses modern React components for product listing, search, and filtering.
- **Persistent Settings**: Dark Mode, Voice Preferences, and Chat History saved to `localStorage`.
- **Responsive Design**: Mobile-friendly layout with glassmorphism UI effects.
- **Session Management**: Automatic 30-minute inactivity timeout to reset context.
---

## Tech Stack

| Layer | Technology | Note |
|-------|------------|------|
| **Frontend** | React 19, Vite, Vanilla CSS | Voice support via Web Speech API |
| **Backend** | Python, Flask | Lightweight wrapper for Lambda handler |
| **NLU** | `fuzzywuzzy`, `sentence-transformers` | **Hybrid Engine: Semantic Search + Fuzzy Matching** |
| **Emotion** | `vaderSentiment` | Rule-based sentiment analysis |
| **LLM** | **Groq LPU** | Intelligent fallback for unknown queries |

---

## Project Structure

```
.
├── backend/                  # Flask API + NLU Logic
│   ├── lambda_function.py   # Core v09 logic (OOS Guards, Context)
│   ├── entity_extractor.py  # Regex/Fuzzy extraction (Updated Catalog)
│   ├── semantic_nlu.py      # Semantic Search Engine
│   ├── context_manager.py   # State & Reference Resolution
│   ├── verify_nlu.py        # NLU Regression Tests
│   └── ...
├── frontend/                 # React Application
├── evaluation/               # Testing Reports
└── README.md                 # This file
```

---

## Quick Start

### 1. Backend Setup
**Prerequisites:** Python 3.8+, GROQ API Key

**Get the GROQ API Key:** This is necessary fallback mechanism for emotion detection when non-LLM procedures fail
 - Navigate to [GROQ API KEY CONSOLE](https://console.groq.com/keys)
 - Create a new Key
 - Add it against GROQ_API_KEY environment variable in `.env`

**Install Dependencies and Run Server:**

```bash
cd backend

# Create & Activate Virtual Env
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Mac/Linux: source .venv/bin/activate

# Install Dependencies
pip install -r requirements.txt

# Start Server
python server.py
```

*Server runs on port 5000, example URL: `http://127.0.0.1:5000`*

### 2. Frontend Setup

**Prerequisites:** Node.js 18+

**Edit .env** Update the VITE_API_URL=http://127.0.0.1:5000 to point to your backend server.

**Install Dependencies and Run Dev Server:**

```bash
cd frontend
npm install
npm run dev
```

*App runs at: `http://localhost:5173`*

---

## Verification & Testing 

The system includes a suite of automated verification scripts to ensure stability.

| Script | Purpose | Status |
| --- | --- | --- |
| `python verify_nlu.py` | Tests NLU intent classification accuracy. | **25/25 Pass** |
| `python verify_entities.py` | Tests extraction of Products, Quantities, Dates. | **12/12 Pass** |
| `python verify_flows.py` | Validates multi-turn dialog flows (Price -> RFQ). | **Pass** |
| `python verify_switch.py` | Tests mid-flow topic switching logic. | **Pass** |
| `python verify_robustness.py` | Tests OOS and Cancel guards. | **Pass** |

### Manual Testing Scenarios

1. **Topic Shift**: Ask "Price of bearings", then say "Actually I want actuators". The bot should show the price of actuators.
2. **OOS Guard**: Ask "What is the weather resistance of seals?". The bot should answer about seals, NOT say "I cannot help with weather".
3. **Emotion**: Say "I am frustrated". The bot should apologize and de-escalate.

---

## Chat Capabilities

| Intent | Example Phrases |
| --- | --- |
| **RFQ Status** | "Status of REQ-98211", "Where is my quote?" |
| **Lead Time** | "How long to deliver?", "When will it arrive?" |
| **Bulk Inquiry** | "I need 500 units", "Volume discount" |
| **Context** | "What is the price of *it*?", "Actually I want *pumps*" |
| **Support** | "I need help", "Having problems" |

---

## Author

BITS MTech AI/ML - Conversational AI Assignment
|Team Member               |Roll No      |
|--------------------------|-------------|
| PRADYUMNA RAY            | 2024CT05003 |
| ROHIT KUMAR DUBEY        | 2024CT05050 |
| SAMIRAN GHOSH            | 2023CT05033 |
| TUSHAR GAJANAN LOKHANDE  | 2024CT05001 | 

---

