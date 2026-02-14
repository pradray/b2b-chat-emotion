"""
Conversation Context Manager
Maintains conversation history and provides context for NLU/response generation.

Add to your backend folder and import in lambda_function.py:
    from context_manager import context_store
"""

from collections import deque
from datetime import datetime
from typing import List, Dict, Optional

# Used for serialization
import json


class ConversationContext:
    """Manages conversation state and history."""
    
    
    def __init__(self, max_turns: int = 10, context_window: int = 5, expiry_minutes: int = 30):
        """
        Args:
            max_turns: Maximum conversation turns to store
            context_window: Number of recent turns to use for context
            expiry_minutes: Minutes of inactivity before context reset
        """
        self.max_turns = max_turns
        self.context_window = context_window
        self.expiry_minutes = expiry_minutes
        
        # Stores recent conversation turns 
        self.history: deque = deque(maxlen=max_turns)
        self.session_id: Optional[str] = None
        self.user_profile: Dict = {}
        self.current_intent: Optional[str] = None
        self.entities: Dict = {}
        self.dialog_state: Dict = {}
        self.created_at: datetime = datetime.now()
        self.last_activity: datetime = datetime.now()

    def _check_expiry(self):
        """Check if context has expired due to inactivity."""
        elapsed = (datetime.now() - self.last_activity).total_seconds() / 60
        if elapsed > self.expiry_minutes:
            # Expired: Clear volatile context
            self.history.clear()
            self.entities = {}
            self.dialog_state = {}
            # Keep user profile/session_id
            print(f"Context expired for session {self.session_id} after {elapsed:.1f} mins inactivity.")
    
    def add_turn(self, user_message: str, bot_response: str, 
                 intent: str = None, entities: Dict = None, 
                 emotion: str = None):
        """Add a conversation turn to history."""
        self._check_expiry()
        
        # Topic Shift Detection
        if entities and "product" in entities:
            new_product = entities["product"]
            old_product = self.entities.get("product")
            
            # If product changed, clear conflicting attributes from old context
            # We normalize to lower string to be safe
            p_new = str(new_product).lower()
            p_old = str(old_product).lower() if old_product else ""
            
            if old_product and p_new != p_old:
                # Topic Shift detected!
                # Keep the new product, but clear specifics of old product (qty, price, specs)
                # We retain 'email' or 'company' as those are user attributes, not product attributes.
                attributes_to_clear = ["quantity", "price", "specs", "date", "order_number"]
                for attr in attributes_to_clear:
                    if attr in self.entities:
                        del self.entities[attr]
        
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "bot": bot_response,
            "intent": intent,
            "entities": entities or {},
            "emotion": emotion
        }
        self.history.append(turn)
        self.last_activity = datetime.now()
        
        # Update accumulated entities
        if entities:
            self.entities.update(entities)
    
    def get_context_window(self) -> List[Dict]:
        """Get recent conversation turns for context."""
        self._check_expiry()
        return list(self.history)[-self.context_window:]
    
    def get_context_string(self) -> str:
        """Format context as string for LLM consumption."""
        self._check_expiry()
        context_turns = self.get_context_window()
        if not context_turns:
            return ""
        
        lines = ["Recent conversation:"]
        for turn in context_turns:
            lines.append(f"User: {turn['user']}")
            lines.append(f"Bot: {turn['bot']}")
        return "\n".join(lines)
    
    def get_last_intent(self) -> Optional[str]:
        """Get the intent from the last turn."""
        self._check_expiry()
        if self.history:
            return self.history[-1].get("intent")
        return None
    
    def get_last_entities(self) -> Dict:
        """Get entities from the last turn."""
        self._check_expiry()
        if self.history:
            return self.history[-1].get("entities", {})
        return {}
    
    def get_entity(self, entity_type: str) -> Optional[str]:
        """Get a specific entity from accumulated context."""
        self._check_expiry()
        return self.entities.get(entity_type)
    
    def resolve_reference(self, text: str) -> str:
        """
        Resolve pronouns and references using context.
        E.g., "What's the price of it?" -> "What's the price of servo motor?"
        """
        import re
        self._check_expiry()
        
        reference_words = {
            "it": ["product", "item"],
            "that": ["product", "item"],
            "this": ["product", "item"],
            "the product": ["product"],
            "the item": ["product", "item"],
            "them": ["product"],
            "those": ["product"],
            "the order": ["order_number"],
            "my order": ["order_number"]
        }
        
        text_lower = text.lower()
        resolved_text = text
        
        for ref_word, entity_types in reference_words.items():
            # Use regex to match whole words only to avoid substring replacements
            # e.g. "submit" vs "it"
            pattern = r'\b' + re.escape(ref_word) + r'\b'
            
            if re.search(pattern, text_lower):
                # Try to find a matching entity
                for entity_type in entity_types:
                    if entity_type in self.entities:
                        entity_value = self.entities[entity_type]
                        
                        # Don't replace if the entity value is already in the text!
                        # This avoids redundancy "servo motor servo motor"
                        if entity_value.lower() in text_lower:
                            break
                            
                        # Replace all occurrences (case-insensitive flag handles variants)
                        # We use a lambda to restore casing if needed, but for simplicity
                        # we replace with the entity value string directly.
                        resolved_text = re.sub(pattern, entity_value, resolved_text, flags=re.IGNORECASE)
                        
                        # Update text_lower for subsequent checks
                        text_lower = resolved_text.lower()
                        break
        
        return resolved_text
    
    def set_dialog_state(self, state_key: str, value):
        """Set a dialog state variable."""
        self.dialog_state[state_key] = value
    
    def get_dialog_state(self, state_key: str, default=None):
        """Get a dialog state variable."""
        return self.dialog_state.get(state_key, default)
    
    def clear_dialog_state(self):
        """Clear current dialog state (e.g., after completing a flow)."""
        self.dialog_state = {}
    
    def to_dict(self) -> Dict:
        """Serialize context for storage."""
        return {
            "session_id": self.session_id,
            "history": list(self.history),
            "user_profile": self.user_profile,
            "entities": self.entities,
            "dialog_state": self.dialog_state,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationContext':
        """Deserialize context from storage."""
        ctx = cls()
        ctx.session_id = data.get("session_id")
        ctx.history = deque(data.get("history", []), maxlen=ctx.max_turns)
        ctx.user_profile = data.get("user_profile", {})
        ctx.entities = data.get("entities", {})
        ctx.dialog_state = data.get("dialog_state", {})
        return ctx


class ContextStore:
    """
    In-memory store for conversation contexts.
    
    For production, replace with Redis:
        pip install redis
        
    class RedisContextStore:
        def __init__(self, redis_url="redis://localhost:6379"):
            self.redis = redis.from_url(redis_url)
            self.ttl = 3600  # 1 hour expiry
        
        def get_or_create(self, session_id: str) -> ConversationContext:
            data = self.redis.get(f"ctx:{session_id}")
            if data:
                return ConversationContext.from_dict(json.loads(data))
            ctx = ConversationContext()
            ctx.session_id = session_id
            return ctx
        
        def save(self, session_id: str, context: ConversationContext):
            self.redis.setex(f"ctx:{session_id}", self.ttl, json.dumps(context.to_dict()))
    """
    
    def __init__(self):
        self._contexts: Dict[str, ConversationContext] = {}
        self._max_contexts = 1000  # Limit memory usage
    
    def get_or_create(self, session_id: str) -> ConversationContext:
        """Get existing context or create new one."""
        if session_id not in self._contexts:
            # Clean up old contexts if at limit
            if len(self._contexts) >= self._max_contexts:
                self._cleanup_old_contexts()
            
            ctx = ConversationContext()
            ctx.session_id = session_id
            self._contexts[session_id] = ctx
        
        return self._contexts[session_id]
    
    def save(self, session_id: str, context: ConversationContext):
        """Save context."""
        self._contexts[session_id] = context
    
    def delete(self, session_id: str):
        """Delete a context."""
        if session_id in self._contexts:
            del self._contexts[session_id]
    
    def _cleanup_old_contexts(self):
        """Remove oldest contexts when at capacity."""
        if not self._contexts:
            return
        
        # Sort by last activity and remove oldest 10%
        sorted_sessions = sorted(
            self._contexts.items(),
            key=lambda x: x[1].last_activity
        )
        
        to_remove = len(sorted_sessions) // 10 or 1
        for session_id, _ in sorted_sessions[:to_remove]:
            del self._contexts[session_id]


# Global context store instance
context_store = ContextStore()


# Example usage
if __name__ == "__main__":
    # Simulate a conversation
    ctx = context_store.get_or_create("test_session_123")
    
    # First turn
    ctx.add_turn(
        user_message="What's the price of servo motors?",
        bot_response="Login to see Tier-1 wholesale pricing.",
        intent="INFO_PRICE",
        entities={"product": "servo motors"},
        emotion="neutral"
    )
    
    # Second turn - uses reference
    user_msg = "What's the MOQ for it?"
    resolved = ctx.resolve_reference(user_msg)
    print(f"Original: {user_msg}")
    print(f"Resolved: {resolved}")  # "What's the MOQ for servo motors?"
    
    # Check context
    print(f"\nContext window: {ctx.get_context_window()}")
    print(f"\nAccumulated entities: {ctx.entities}")
