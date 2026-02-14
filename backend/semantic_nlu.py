
"""
Semantic NLU Engine
Uses SentenceTransformers (BERT) to create vector embeddings for intents
and performs cosine similarity search for deep semantic understanding.
"""

import logging
import os
import json
from typing import Dict, List, Optional, NamedTuple, Any

# Configure logging
logger = logging.getLogger(__name__)

# Define match result structure
class IntentMatch(NamedTuple):
    intent: str
    confidence: float

class SemanticNLU:
    def __init__(self):
        self.model = None
        self.intent_embeddings = None
        self.corpus_phrases = [] # List of (intent, phrase) tuples
        self.is_ready = False
        
    def initialize(self, intent_map: Dict[str, List[str]]):
        """
        Load the model and pre-compute embeddings for all intents.
        This runs once at startup.
        """
        try:
            # Lazy import to avoid crashing if library is missing
            from sentence_transformers import SentenceTransformer, util
            import torch
            
            logger.info("Loading Semantic NLU model (all-MiniLM-L6-v2)...")
            # Downloads ~80MB on first run, then uses cache
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # 1. Flatten the Intent Map
            self.corpus_phrases = [] # Reset
            corpus_text = []
            
            for intent, phrases in intent_map.items():
                # Skip structural intents that don't need semantic search
                if intent in ["CONTROL_CANCEL", "OUT_OF_SCOPE", "SYSTEM_RFQ_SUBMITTED"]:
                    continue
                    
                for phrase in phrases:
                    self.corpus_phrases.append(intent)
                    corpus_text.append(phrase)
            
            # 2. Generate Embeddings (Fast batch operation)
            # convert_to_tensor=True allows fast GPU/CPU operations
            self.intent_embeddings = self.model.encode(corpus_text, convert_to_tensor=True)
            
            self.is_ready = True
            logger.info(f"Semantic NLU initialized with {len(corpus_text)} phrases.")
            
        except ImportError:
            logger.warning("Semantic NLU: sentence-transformers not installed. Falling back to fuzzy match.")
            self.is_ready = False
        except Exception as e:
            logger.error(f"Semantic NLU Initialization Failed: {e}")
            self.is_ready = False

    def match_intent(self, text: str, threshold: float = 0.45) -> Optional[IntentMatch]:
        """
        Find the best semantic match for the user's text.
        Returns None if confidence is below threshold.
        """
        if not self.is_ready or not text.strip():
            return None
            
        try:
            from sentence_transformers import util
            import torch
            
            # 1. Encode the user query
            user_embedding = self.model.encode(text, convert_to_tensor=True)
            
            # 2. Compute Cosine Similarity against all intent phrases
            # Returns a list of scores [0.1, 0.8, 0.3, ...]
            cosine_scores = util.cos_sim(user_embedding, self.intent_embeddings)[0]
            
            # 3. Find the best match
            best_score = torch.max(cosine_scores)
            best_idx = torch.argmax(cosine_scores).item()
            
            confidence = float(best_score)
            
            # 4. Return result if it meets threshold
            if confidence >= threshold:
                best_intent = self.corpus_phrases[best_idx]
                return IntentMatch(intent=best_intent, confidence=confidence)
                
            return None
            
        except Exception as e:
            logger.error(f"Semantic Search Error: {e}")
            return None

# Global Instance
semantic_nlu = SemanticNLU()