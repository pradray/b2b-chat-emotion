"""
Emotion Detection Module
Uses VADER (Valence Aware Dictionary for Sentiment Reasoning) for text sentiment analysis
and maps results to emotion categories for empathetic response generation.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize VADER analyzer
analyzer = SentimentIntensityAnalyzer()

# Emotion-specific keyword boosters
EMOTION_KEYWORDS = {
    "angry": ["angry", "furious", "mad", "outraged", "annoyed", "irritated", "hate", "terrible", "awful", "worst", "unacceptable"],
    "frustrated": ["frustrated", "frustrating", "stuck", "waiting", "forever", "still", "again", "keeps", "always", "never works", "issue", "problem"],
    "sad": ["sad", "disappointed", "unhappy", "sorry", "unfortunate", "depressed", "hopeless", "regret", "miss"],
    "happy": ["happy", "great", "excellent", "wonderful", "amazing", "love", "thank", "thanks", "appreciate", "awesome", "fantastic", "perfect"],
    "anxious": ["worried", "anxious", "nervous", "concern", "urgent", "asap", "hurry", "deadline", "emergency"]
}


def detect_emotion(text: str) -> dict:
    """
    Detect emotion from text input.
    
    Args:
        text: The user's input text
        
    Returns:
        dict with keys:
            - emotion: The detected emotion category
            - confidence: Confidence score (0-1)
            - scores: Raw VADER sentiment scores
            - intensity: Emotional intensity level (low/medium/high)
    """
    if not text or not text.strip():
        return {
            "emotion": "neutral",
            "confidence": 1.0,
            "scores": {"neg": 0, "neu": 1, "pos": 0, "compound": 0},
            "intensity": "low"
        }
    
    text_lower = text.lower()
    
    # Get VADER sentiment scores
    scores = analyzer.polarity_scores(text)
    compound = scores["compound"]
    
    # Check for keyword-based emotion detection first
    keyword_emotion = _detect_keyword_emotion(text_lower)
    
    # Determine emotion from compound score
    if keyword_emotion:
        emotion = keyword_emotion
        confidence = 0.85  # High confidence for keyword matches
    elif compound >= 0.5:
        emotion = "happy"
        confidence = min(abs(compound), 1.0)
    elif compound >= 0.1:
        emotion = "positive"
        confidence = min(abs(compound) * 1.5, 1.0)
    elif compound <= -0.5:
        # Distinguish between angry and sad based on keywords
        if any(word in text_lower for word in EMOTION_KEYWORDS["angry"]):
            emotion = "angry"
        elif any(word in text_lower for word in EMOTION_KEYWORDS["frustrated"]):
            emotion = "frustrated"
        else:
            emotion = "sad"
        confidence = min(abs(compound), 1.0)
    elif compound <= -0.1:
        emotion = "negative"
        confidence = min(abs(compound) * 1.5, 1.0)
    else:
        emotion = "neutral"
        confidence = 1.0 - abs(compound)  # More neutral = higher confidence
    
    # Determine intensity
    abs_compound = abs(compound)
    if abs_compound >= 0.6:
        intensity = "high"
    elif abs_compound >= 0.3:
        intensity = "medium"
    else:
        intensity = "low"
    
    return {
        "emotion": emotion,
        "confidence": round(confidence, 2),
        "scores": scores,
        "intensity": intensity
    }


def _detect_keyword_emotion(text: str) -> str | None:
    """
    Check for explicit emotion keywords in text.
    Returns emotion if strong keyword match found, None otherwise.
    """
    keyword_counts = {}
    
    for emotion, keywords in EMOTION_KEYWORDS.items():
        count = sum(1 for keyword in keywords if keyword in text)
        if count > 0:
            keyword_counts[emotion] = count
    
    if keyword_counts:
        # Return emotion with most keyword matches
        return max(keyword_counts, key=keyword_counts.get)
    
    return None


def get_emotion_emoji(emotion: str) -> str:
    """Get an emoji representation for the detected emotion."""
    emoji_map = {
        "happy": "😊",
        "positive": "🙂",
        "neutral": "😐",
        "negative": "😕",
        "sad": "😢",
        "angry": "😠",
        "frustrated": "😤",
        "anxious": "😰"
    }
    return emoji_map.get(emotion, "😐")


def needs_empathy(emotion: str) -> bool:
    """Determine if the emotion requires an empathetic response."""
    empathy_emotions = {"sad", "angry", "frustrated", "anxious", "negative"}
    return emotion in empathy_emotions
