"""
Unit tests for emotion detection module.
Run with: python -m pytest test_emotion_detector.py -v
"""

import pytest
from emotion_detector import detect_emotion, get_emotion_emoji, needs_empathy


class TestEmotionDetection:
    """Test cases for the detect_emotion function."""

    def test_happy_text(self):
        """Test detection of happy emotions."""
        test_cases = [
            "Great! Thank you so much!",
            "I love this product, it's amazing!",
            "Wonderful experience, highly appreciate it!",
            "This is fantastic news!",
        ]
        for text in test_cases:
            result = detect_emotion(text)
            assert result["emotion"] in ["happy", "positive"], f"Expected happy/positive for: {text}"
            assert result["confidence"] > 0.3

    def test_sad_text(self):
        """Test detection of sad emotions."""
        test_cases = [
            "This is really disappointing...",
            "I'm sorry but this doesn't work",
            "Unfortunately, I'm very unhappy with the result",
        ]
        for text in test_cases:
            result = detect_emotion(text)
            assert result["emotion"] in ["sad", "negative"], f"Expected sad/negative for: {text}"

    def test_angry_text(self):
        """Test detection of angry emotions."""
        test_cases = [
            "This is completely unacceptable!",
            "I hate this terrible service!",
            "This is the worst experience ever!",
            "I'm so angry about this!",
        ]
        for text in test_cases:
            result = detect_emotion(text)
            assert result["emotion"] in ["angry", "negative"], f"Expected angry/negative for: {text}"

    def test_frustrated_text(self):
        """Test detection of frustrated emotions."""
        test_cases = [
            "I've been waiting forever for this!",
            "This is so frustrating, nothing works!",
            "I'm stuck and can't proceed again",
        ]
        for text in test_cases:
            result = detect_emotion(text)
            assert result["emotion"] in ["frustrated", "negative", "angry"], f"Expected frustrated for: {text}"

    def test_neutral_text(self):
        """Test detection of neutral emotions."""
        test_cases = [
            "What is the MOQ?",
            "Can you tell me about shipping?",
            "I need information about bulk orders",
            "What are the payment options?",
        ]
        for text in test_cases:
            result = detect_emotion(text)
            assert result["emotion"] in ["neutral", "positive"], f"Expected neutral for: {text}"
            assert result["confidence"] > 0.5

    def test_empty_text(self):
        """Test handling of empty input."""
        result = detect_emotion("")
        assert result["emotion"] == "neutral"
        assert result["confidence"] == 1.0

    def test_none_text(self):
        """Test handling of None input."""
        result = detect_emotion(None)
        assert result["emotion"] == "neutral"

    def test_emotion_intensity(self):
        """Test that intensity is correctly categorized."""
        # Strong emotion should have high intensity
        result = detect_emotion("I absolutely LOVE this! It's AMAZING!")
        assert result["intensity"] in ["medium", "high"]
        
        # Mild text should have low intensity
        result = detect_emotion("Okay")
        assert result["intensity"] == "low"

    def test_return_structure(self):
        """Test that return structure is correct."""
        result = detect_emotion("Hello there!")
        assert "emotion" in result
        assert "confidence" in result
        assert "scores" in result
        assert "intensity" in result
        assert isinstance(result["confidence"], float)
        assert 0 <= result["confidence"] <= 1


class TestEmotionEmoji:
    """Test cases for the get_emotion_emoji function."""

    def test_emoji_mapping(self):
        """Test that emojis are returned for all emotions."""
        emotions = ["happy", "positive", "neutral", "negative", "sad", "angry", "frustrated", "anxious"]
        for emotion in emotions:
            emoji = get_emotion_emoji(emotion)
            assert emoji is not None
            assert len(emoji) > 0

    def test_default_emoji(self):
        """Test default emoji for unknown emotion."""
        emoji = get_emotion_emoji("unknown_emotion")
        assert emoji == "😐"


class TestNeedsEmpathy:
    """Test cases for the needs_empathy function."""

    def test_empathy_emotions(self):
        """Test emotions that need empathy."""
        empathy_required = ["sad", "angry", "frustrated", "anxious", "negative"]
        for emotion in empathy_required:
            assert needs_empathy(emotion) == True

    def test_non_empathy_emotions(self):
        """Test emotions that don't need empathy."""
        no_empathy = ["happy", "positive", "neutral"]
        for emotion in no_empathy:
            assert needs_empathy(emotion) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
