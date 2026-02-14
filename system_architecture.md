# Application Architecture

## System Overview

The B2B Chat Application follows a modern client-server architecture with a **Hybrid NLU** engine.

```mermaid
%%{init: { "flowchart": { "nodePadding": 20 }, "themeVariables": { "fontSize": "18px" } } }%%
graph TD
    subgraph Frontend [**React Frontend**]
        UI["App.jsx<br/>Main UI"]
        Chat["ChatWidget.jsx"]
        Voice["VoiceChatWidget.jsx"]
        WebSpeech["Web Speech<br>API"]
        
        User((User)) -->|Clicks/<br>Types| UI
        User -->|Speaks| WebSpeech
        WebSpeech -->|Text| Voice
        UI --> Chat
        UI --> Voice
    end

    subgraph Backend [**Python Flask** Backend]
        API["Flask Server"]
        Lambda["Lambda Handler"]
        Chat -->|POST/chat| API
        Voice -->|POST/chat| API
        API -->|JSON| Lambda
    end

    subgraph Intelligence [**Core Intelligence** Layer]
        Lambda --> Context["Context Manager"]
        Lambda --> Dialog["Dialog Manager"]
        Lambda --> Entity["Entity Extractor"]
        
        subgraph NLU [**Hybrid NLU Engine**]
            Semantic["Semantic NLU (SentenceTransformers)"]
            Fuzzy["Fuzzy Matcher (FuzzyWuzzy)"]
            
            Lambda -->|Layer 1: Guards| Guards{"Out of Scope / Business Guards"}
            Guards -->|Pass| Semantic
            Semantic -->|Low Confidence| Fuzzy
            Fuzzy -->|No Match| Grok[("Grok LLM<br>(Fallback)")]
        end
    end

    subgraph Data [**Data Persistence**]
        Context ----> Store[(Session Store)]
        Dialog ----> Flows[(Active Flows)]
        UI ----> LocalStore[(local Storage)]
    end

    %% Data Flow Styling (Standard)
```

## Component Details

### 1. Frontend (React)
-   **App.jsx**: Manages global state (Theme, Voice Settings, Navigation).
-   **VoiceChatWidget**: Handles Microphone input, STT (Speech-to-Text), and TTS (Text-to-Speech) using the browser's **Web Speech API**.
-   **State Sync**: Voice settings are lifted up to `App.jsx` to ensure consistency.

### 2. Backend (Flask + Python)
-   **Lambda Handler**: Central orchestration logic.
-   **Hybrid NLU**:
    -   **Semantic Search**: Uses BERT embeddings (`sentence-transformers`) to understand intent meaning (e.g., "How much is it?" = Pricing).
    -   **Fuzzy Matching**: Fallback for specific keywords or typos.
    -   **Grok LLM**: Final fallback for complex queries or chit-chat that the NLU cannot handle.
-   **Context Manager**: Tracks conversation history and resolves references like "it" or "that".
