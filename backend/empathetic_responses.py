"""
Empathetic Response Templates
Provides emotion-aware prefixes, suffixes, and acknowledgments for natural conversation flow.
"""

import random

# Empathetic acknowledgments by emotion
EMPATHY_PREFIXES = {
    "happy": [
        "That's wonderful to hear! ",
        "I'm glad you're having a great experience! ",
        "Fantastic! ",
        "Great to hear that! "
    ],
    "positive": [
        "I'm happy to help! ",
        "Thanks for reaching out! ",
        "Of course! "
    ],
    "neutral": [
        "",  # No prefix for neutral
        "Sure! ",
        "Certainly! "
    ],
    "negative": [
        "I understand your concern. ",
        "I hear you. ",
        "Let me help with that. "
    ],
    "sad": [
        "I'm sorry to hear that. ",
        "I understand this can be disappointing. ",
        "I apologize for any inconvenience. ",
        "I truly understand how you feel. "
    ],
    "angry": [
        "I completely understand your frustration, and I apologize. ",
        "I'm truly sorry for this experience. ",
        "I hear you, and I want to make this right. ",
        "I apologize sincerely for any inconvenience caused. "
    ],
    "frustrated": [
        "I understand this has been frustrating. ",
        "I'm sorry you've had to deal with this. ",
        "I can see this hasn't been easy. Let me help. ",
        "I apologize for the trouble you've been experiencing. "
    ],
    "anxious": [
        "I understand this is urgent for you. ",
        "Don't worry, I'm here to help. ",
        "Let's address your concern right away. ",
        "I can help you with this immediately. "
    ]
}

# Empathetic suffixes to add warmth
EMPATHY_SUFFIXES = {
    "happy": [
        " Is there anything else I can help you with today?",
        " Let me know if you need anything else!",
        ""
    ],
    "positive": [
        " Feel free to ask if you have more questions!",
        ""
    ],
    "neutral": [
        "",
        " Is there anything else you'd like to know?"
    ],
    "negative": [
        " I'm here if you need further assistance.",
        " Please don't hesitate to reach out if you need more help."
    ],
    "sad": [
        " We truly value your business and want to make things right.",
        " Please let me know how else I can assist you.",
        " We're committed to resolving this for you."
    ],
    "angry": [
        " Your satisfaction is our top priority.",
        " We take your feedback seriously and will work to improve.",
        " Please let me know if there's anything specific I can do to help."
    ],
    "frustrated": [
        " We appreciate your patience.",
        " I'll do my best to resolve this quickly.",
        " Thank you for your understanding."
    ],
    "anxious": [
        " Rest assured, we'll take care of this promptly.",
        " I'll prioritize this for you.",
        ""
    ]
}

# Context-aware acknowledgments for specific situations
SITUATION_RESPONSES = {
    "waiting": [
        "I understand the wait can be frustrating. ",
        "I apologize for the delay you've experienced. "
    ],
    "issue": [
        "I'm sorry you're experiencing this issue. ",
        "Let me help you resolve this problem. "
    ],
    "urgent": [
        "I understand this is time-sensitive. ",
        "Let me prioritize this for you right away. "
    ]
}


def enhance_response(base_response: str, emotion: str, intensity: str = "medium") -> str:
    """
    Enhance a base response with empathetic elements based on detected emotion.
    
    Args:
        base_response: The original response message
        emotion: The detected emotion category
        intensity: Emotional intensity (low/medium/high)
        
    Returns:
        Enhanced response with empathetic prefix and/or suffix
    """
    # Get appropriate prefix
    prefixes = EMPATHY_PREFIXES.get(emotion, EMPATHY_PREFIXES["neutral"])
    prefix = random.choice(prefixes) if prefixes else ""
    
    # Get appropriate suffix (only for non-neutral emotions with medium/high intensity)
    if emotion != "neutral" and intensity in ("medium", "high"):
        suffixes = EMPATHY_SUFFIXES.get(emotion, [])
        suffix = random.choice(suffixes) if suffixes else ""
    else:
        suffix = ""
    
    return f"{prefix}{base_response}{suffix}"


def get_empathy_acknowledgment(emotion: str) -> str:
    """Get a standalone empathy acknowledgment for the emotion."""
    prefixes = EMPATHY_PREFIXES.get(emotion, [])
    return random.choice(prefixes) if prefixes else ""


def detect_situation_context(text: str) -> list:
    """
    Detect specific situational context in the user's message.
    
    Returns list of detected situations that may need special handling.
    """
    text_lower = text.lower()
    detected = []
    
    waiting_keywords = ["waiting", "wait", "long", "forever", "still", "yet", "when"]
    issue_keywords = ["problem", "issue", "error", "broken", "doesn't work", "not working", "bug"]
    urgent_keywords = ["urgent", "asap", "immediately", "emergency", "deadline", "hurry"]
    
    if any(word in text_lower for word in waiting_keywords):
        detected.append("waiting")
    if any(word in text_lower for word in issue_keywords):
        detected.append("issue")
    if any(word in text_lower for word in urgent_keywords):
        detected.append("urgent")
    
    return detected
