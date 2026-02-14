"""
LLM Fallback Module - Groq Integration
Uses Groq API for intelligent fallback when rule-based system fails.

Installation:
    pip install groq

Environment:
    export GROQ_API_KEY=your-api-key

Add to your backend folder and import:
    from llm_fallback import llm_fallback
"""

import os
from typing import Optional, Dict
import json
from dotenv import load_dotenv

load_dotenv()

# Try to import Groq client
try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    print("Note: groq not installed. Install with: pip install groq")
    print("LLM fallback will use simple responses.")


class LLMFallback:
    """
    Provides LLM-powered fallback responses when rule-based NLU fails.
    
    Features:
    - Context-aware responses using conversation history
    - Emotion-aware tone adjustment
    - Business domain knowledge injection
    - Graceful degradation when API unavailable
    
    Usage:
        fallback = LLMFallback()
        response = fallback.generate_response(
            user_message="Can you help me find something?",
            context="User asked about servo motors earlier",
            detected_emotion="frustrated"
        )
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-8b-instant"):
        """
        Initialize the LLM fallback.
        
        Args:
            api_key: Groq API key (or set GROQ_API_KEY env var)
            model: Model to use for responses
                - "llama-3.1-8b-instant": Fast, good quality (recommended)
                - "llama-3.1-70b-versatile": Higher quality, slower
                - "mixtral-8x7b-32768": Good alternative
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.client = None
        self.is_ready = False
        
        if HAS_GROQ and self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                self.is_ready = True
            except Exception as e:
                print(f"Error initializing Groq client: {e}")
        
        # Business knowledge to inject
        self.business_context = """
        You are a helpful B2B support assistant for an industrial parts marketplace.
        
        Key Business Information:
        - MOQ (Minimum Order Quantity): Typically 50-500 units depending on product
        - Lead time: 14-21 days for most standard items
        - Shipping: FOB and EXW options via Maersk, DHL, FedEx
        - Bulk discounts: 5% (100-499 units), 10% (500-999), 15% (1000+)
        - Payment: Net-30, Wire Transfer, Letter of Credit
        - Warranty: 1 year manufacturer warranty on industrial parts
        - Returns: RMA within 14 days of delivery
        
        Product Categories:
        - Motors & Drives (servo motors, stepper motors)
        - Cables & Connectors (fiber optic, industrial ethernet)
        - Actuators & Automation
        - Sensors & Controllers
        - Power Supplies & Relays
        
        Navigation Options:
        - Marketplace: Browse all products
        - Suppliers: View verified manufacturers
        - RFQ: Submit request for quote
        - Login: Access partner account
        """
    
    def generate_response(self, 
                          user_message: str, 
                          context: str = "",
                          detected_emotion: str = "neutral",
                          conversation_history: list = None,
                          max_tokens: int = 250) -> str:
        """
        Generate a response using Groq.
        
        Args:
            user_message: The user's current message
            context: Previous conversation context string
            detected_emotion: Detected user emotion
            conversation_history: List of {"role": "user/assistant", "content": "..."}
            max_tokens: Maximum response length
            
        Returns:
            Generated response string
        """
        if not self.is_ready:
            return self._simple_fallback(user_message, detected_emotion)
        
        system_prompt = self._build_system_prompt(detected_emotion)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 3 turns
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add context and current message
        if context and not conversation_history:
            user_content = f"Previous context:\n{context}\n\nCurrent message: {user_message}"
        else:
            user_content = user_message
        
        messages.append({"role": "user", "content": user_content})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq API error: {e}")
            return self._simple_fallback(user_message, detected_emotion)
    
    def _build_system_prompt(self, emotion: str) -> str:
        """Build system prompt with emotion-aware guidance."""
        
        emotion_guidance = {
            "happy": "The user seems positive and engaged. Match their enthusiasm while being helpful.",
            "positive": "The user has a positive tone. Be friendly and efficient.",
            "frustrated": "The user seems frustrated. Be extra patient, empathetic, and solution-focused. Acknowledge their frustration.",
            "angry": "The user seems upset. Apologize sincerely, stay calm, and focus on resolving their issue quickly.",
            "sad": "The user seems disappointed. Be supportive, understanding, and offer constructive help.",
            "anxious": "The user seems worried or rushed. Provide clear, reassuring guidance. Be concise and action-oriented.",
            "neutral": "Respond in a friendly, professional manner.",
            "negative": "The user may be having a difficult experience. Be empathetic and helpful."
        }
        
        tone_instruction = emotion_guidance.get(emotion, emotion_guidance["neutral"])
        
        return f"""{self.business_context}

Response Guidelines:
- Be concise: 2-3 sentences max unless more detail is needed
- Be helpful: Guide users to solutions or next steps
- Be honest: If you don't know specific details, offer to connect them with sales
- {tone_instruction}

Important:
- Never make up specific prices, inventory numbers, or delivery dates
- Suggest relevant actions: "You can browse the Marketplace" or "Would you like to submit an RFQ?"
- If the request is unclear, ask a clarifying question
- If you can't help, offer alternatives (contact sales, browse FAQ, etc.)
"""
    
    def _simple_fallback(self, user_message: str, emotion: str) -> str:
        """
        Simple fallback responses when LLM is unavailable.
        Returns helpful response based on emotion and keywords.
        """
        msg_lower = user_message.lower()
        
        # Domain-specific keyword matching
        if any(w in msg_lower for w in ["track", "ship", "delivery", "arrive", "where"]):
            return ("I can help with shipping or tracking. "
                    "Please provide your PO number (e.g., PO-12345) to check status.")
                    
        if any(w in msg_lower for w in ["price", "cost", "quote", "how much", "expensive"]):
            return ("For pricing, you can ask about specific products or request a formal quote. "
                    "For example: 'price of servo motors' or 'start RFQ'.")
                    
        if any(w in msg_lower for w in ["return", "refund", "exchang", "broken", "damage"]):
            return ("I can assist with returns. Please provide your Order Number and a brief reason "
                    "so I can start the RMA process.")
                    
        if any(w in msg_lower for w in ["stock", "inventory", "available", "carry"]):
            return ("To check stock, please name the specific product you're looking for, "
                    "like 'stepper motors' or 'sensors'.")

        # Emotion-aware fallbacks (if no specific domain detected)
        if emotion in ["frustrated", "angry"]:
            responses = [
                "I apologize that I couldn't fully understand your request. "
                "For immediate assistance, please contact our sales team at sales@b2bhub.com "
                "or call 1-800-B2B-HELP. I want to make sure you get the help you need.",
                
                "I'm sorry for any confusion. Let me help you better. "
                "You can try asking about specific topics like MOQ, pricing, shipping, "
                "or I can connect you with our support team.",
            ]
        elif emotion in ["anxious"]:
            responses = [
                "I understand you need quick assistance. Here's how I can help right away:\n"
                "• For order status: provide your PO number\n"
                "• For urgent quotes: say 'RFQ' to start\n"
                "• For immediate support: contact sales@b2bhub.com",
            ]
        elif emotion in ["sad", "negative"]:
            responses = [
                "I'm sorry things aren't going as expected. "
                "I'd like to help make this right. Could you tell me more about what you need? "
                "I can assist with orders, shipping, returns, or connect you with our team.",
            ]
        else:
            responses = [
                "I'd be happy to help you! I can assist with:\n"
                "• Product information and MOQ\n"
                "• Pricing and bulk discounts\n"
                "• Shipping and delivery\n"
                "• Order tracking\n"
                "What would you like to know more about?",
                
                "I'm not quite sure what you're looking for. "
                "Try asking about products, pricing, shipping, or say 'Marketplace' to browse. "
                "I'm here to help!",
                
                "Could you tell me a bit more about what you need? "
                "I can help with product inquiries, quotes, shipping info, and more.",
            ]
        
        import random
        return random.choice(responses)
    
    def generate_clarification(self, user_message: str, 
                               possible_intents: list) -> str:
        """
        Generate a clarification question for ambiguous input.
        
        Args:
            user_message: The ambiguous user message
            possible_intents: List of possible intent matches
            
        Returns:
            Clarification question
        """
        intent_descriptions = {
            "INFO_MOQ": "minimum order quantities",
            "INFO_PRICE": "pricing and costs",
            "INFO_SHIPPING": "shipping and delivery",
            "INFO_LEADTIME": "production and delivery times",
            "INFO_BULK": "bulk order discounts",
            "INFO_TRACK": "order tracking",
            "NAV_MARKETPLACE": "browsing products",
            "NAV_SUPPLIER": "viewing suppliers",
            "NAV_RFQ": "requesting a quote",
            "HELP": "general assistance"
        }
        
        options = []
        for intent in possible_intents[:3]:
            intent_name = intent["intent"] if isinstance(intent, dict) else intent
            if intent_name in intent_descriptions:
                options.append(intent_descriptions[intent_name])
        
        if not options:
            return "Could you tell me more about what you need? I want to make sure I help you correctly."
        
        if len(options) == 1:
            return f"Are you asking about {options[0]}?"
        
        options_str = ", ".join(options[:-1]) + f", or {options[-1]}"
        return f"I want to make sure I understand. Are you asking about {options_str}?"
    
    def enhance_response(self, base_response: str, 
                         user_message: str,
                         emotion: str = "neutral") -> str:
        """
        Enhance a template response using LLM for more natural flow.
        
        This is useful when you have a factual response but want to make it
        sound more natural and contextually appropriate.
        """
        if not self.is_ready:
            return base_response
        
        prompt = f"""The user said: "{user_message}"
The user's emotional state appears to be: {emotion}

Here's the factual response to give: "{base_response}"

Please rephrase this response to be more natural, conversational, and appropriate 
for the user's emotional state. Keep the same factual information but make it 
sound more human. Keep it concise (1-2 sentences).

Respond with just the rephrased message, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that rephrases responses to be more natural."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception:
            return base_response


# Global instance
llm_fallback = LLMFallback()


# Example usage
if __name__ == "__main__":
    print("LLM Fallback Test (Groq)")
    print("=" * 60)
    
    if not llm_fallback.is_ready:
        print("\nLLM not available. Testing simple fallback...")
        print("\nTest 1: Neutral emotion")
        print(llm_fallback._simple_fallback("help me", "neutral"))
        
        print("\nTest 2: Frustrated emotion")
        print(llm_fallback._simple_fallback("help me", "frustrated"))
        
        print("\nTest 3: Anxious emotion")
        print(llm_fallback._simple_fallback("help me", "anxious"))
    else:
        print("\nGroq LLM available. Testing full responses...")
        
        test_cases = [
            {
                "message": "I've been waiting for my order for weeks!",
                "emotion": "frustrated",
                "context": "User ordered servo motors"
            },
            {
                "message": "Can you help me find something for my factory?",
                "emotion": "neutral",
                "context": ""
            },
            {
                "message": "This is urgent, I need parts by Friday!",
                "emotion": "anxious",
                "context": ""
            }
        ]
        
        for test in test_cases:
            print(f"\nUser ({test['emotion']}): {test['message']}")
            response = llm_fallback.generate_response(
                test["message"],
                test["context"],
                test["emotion"]
            )
            print(f"Bot: {response}")
