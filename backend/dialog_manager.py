"""
Dialog State Manager
Handles multi-turn conversations with slot filling.

Add to your backend folder and import in lambda_function.py:
    from dialog_manager import dialog_manager
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re


class DialogStatus(Enum):
    """Status of a dialog flow."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Slot:
    """A slot to be filled in a dialog."""
    name: str
    prompt: str  # Question to ask user
    required: bool = True
    value: Optional[str] = None
    entity_type: Optional[str] = None  # For auto-extraction
    validator: Optional[Callable[[str], bool]] = None
    normalizer: Optional[Callable[[str], str]] = None
    error_message: str = "I didn't understand that. Could you try again?"
    reprompt_message: Optional[str] = None  # Alternative prompt on retry
    max_attempts: int = 3
    attempts: int = 0
    
    def validate(self, value: str) -> bool:
        """Validate the slot value."""
        if self.validator:
            return self.validator(value)
        return bool(value and value.strip())
    
    def normalize(self, value: str) -> str:
        """Normalize the slot value."""
        if self.normalizer:
            return self.normalizer(value)
        return value.strip()
    
    def reset(self):
        """Reset slot to initial state."""
        self.value = None
        self.attempts = 0


@dataclass
class DialogFlow:
    """Definition of a multi-turn dialog flow."""
    name: str
    trigger_intents: List[str]
    slots: List[Slot]
    completion_message: str
    confirmation_prompt: Optional[str] = None  # Ask for confirmation before completing
    on_complete: Optional[Callable[[Dict], Any]] = None  # Callback with filled slots
    cancel_intents: List[str] = field(default_factory=lambda: ["cancel", "stop", "nevermind"])
    status: DialogStatus = DialogStatus.NOT_STARTED
    started_at: Optional[datetime] = None
    
    def get_next_empty_slot(self) -> Optional[Slot]:
        """Get the next required slot that needs filling."""
        for slot in self.slots:
            if slot.required and slot.value is None:
                return slot
        # Check optional slots too
        for slot in self.slots:
            if not slot.required and slot.value is None:
                return slot
        return None
    
    def get_next_required_empty_slot(self) -> Optional[Slot]:
        """Get the next required slot that needs filling."""
        for slot in self.slots:
            if slot.required and slot.value is None:
                return slot
        return None
    
    def fill_slot(self, slot_name: str, value: str) -> bool:
        """
        Fill a slot with a value.
        
        Returns:
            True if value was valid and slot was filled
        """
        for slot in self.slots:
            if slot.name == slot_name:
                slot.attempts += 1
                
                # Normalize first
                normalized = slot.normalize(value)
                
                # Then validate
                if slot.validate(normalized):
                    slot.value = normalized
                    return True
                return False
        return False
    
    def fill_slot_direct(self, slot_name: str, value: str):
        """Fill a slot directly without validation (for entity extraction)."""
        for slot in self.slots:
            if slot.name == slot_name:
                slot.value = value
                return
    
    def get_filled_slots(self) -> Dict[str, str]:
        """Get all filled slot values."""
        return {s.name: s.value for s in self.slots if s.value is not None}
    
    def get_slot(self, slot_name: str) -> Optional[Slot]:
        """Get a slot by name."""
        for slot in self.slots:
            if slot.name == slot_name:
                return slot
        return None
    
    def is_complete(self) -> bool:
        """Check if all required slots are filled."""
        return all(s.value is not None for s in self.slots if s.required)
    
    def reset(self):
        """Reset all slots and status."""
        for slot in self.slots:
            slot.reset()
        self.status = DialogStatus.NOT_STARTED
        self.started_at = None
    
    def get_summary(self) -> str:
        """Get a summary of filled slots."""
        filled = self.get_filled_slots()
        if not filled:
            return "No information collected yet."
        
        lines = ["Here's what I have so far:"]
        for name, value in filled.items():
            # Make slot name more readable
            display_name = name.replace("_", " ").title()
            lines.append(f"  • {display_name}: {value}")
        return "\n".join(lines)


class DialogManager:
    """
    Manages dialog flows and slot filling.
    
    Usage:
        dm = DialogManager()
        
        # Check if intent triggers a flow
        flow = dm.get_flow_for_intent("NAV_RFQ")
        
        # Process a turn
        result = dm.process_turn(intent, entities, user_text, session_id)
        if result:
            return result["response"]
    """
    
    def __init__(self):
        self.flows: Dict[str, DialogFlow] = {}
        self.active_flows: Dict[str, str] = {}  # session_id -> flow_name
        self._register_default_flows()
    
    def _register_default_flows(self):
        """Register built-in dialog flows for B2B scenarios."""
        
        # RFQ (Request for Quote) Flow
        self.register_flow(DialogFlow(
            name="rfq_flow",
            trigger_intents=["NAV_RFQ", "request_quote"],
            slots=[
                Slot(
                    name="product",
                    prompt="Which product are you interested in getting a quote for?",
                    entity_type="product",
                    error_message="I couldn't identify that product. Could you specify the product name? (e.g., servo motors, actuators)"
                ),
                Slot(
                    name="quantity",
                    prompt="How many units do you need?",
                    entity_type="quantity",
                    validator=lambda x: x.isdigit() and int(x) > 0,
                    normalizer=lambda x: re.sub(r'[^\d]', '', x),
                    error_message="Please enter a valid number of units (e.g., 500)."
                ),
                Slot(
                    name="company",
                    prompt="What's your company name?",
                    entity_type="company",
                    validator=lambda x: len(x) >= 2,
                    error_message="Please provide your company name (at least 2 characters)."
                ),
                Slot(
                    name="email",
                    prompt="What email should I send the quote to?",
                    entity_type="email",
                    validator=lambda x: "@" in x and "." in x.split("@")[-1],
                    normalizer=lambda x: x.lower().strip(),
                    error_message="Please enter a valid email address (e.g., orders@company.com)."
                ),
                Slot(
                    name="timeline",
                    prompt="When do you need this delivered by? (optional - type 'skip' to skip)",
                    required=False,
                    entity_type="date"
                )
            ],
            completion_message=(
                "✅ Perfect! I've submitted your RFQ:\n\n"
                "  • Product: {product}\n"
                "  • Quantity: {quantity} units\n"
                "  • Company: {company}\n"
                "  • Email: {email}\n\n"
                "Our sales team will send a detailed quote to {email} within 24 hours. "
                "Is there anything else I can help with?"
            ),
            confirmation_prompt=(
                "Just to confirm, you'd like a quote for:\n"
                "  • {quantity} x {product}\n"
                "  • For: {company}\n"
                "  • Send to: {email}\n\n"
                "Is this correct? (yes/no)"
            )
        ))
        
        # Order Tracking Flow
        self.register_flow(DialogFlow(
            name="tracking_flow",
            trigger_intents=["INFO_TRACK", "track_order", "order_status"],
            slots=[
                Slot(
                    name="order_number",
                    prompt="What's your order or PO number?",
                    entity_type="order_number",
                    validator=lambda x: len(x) >= 4 and any(c.isdigit() for c in x),
                    normalizer=lambda x: x.upper().replace(" ", ""),
                    error_message="Order numbers are usually 4+ characters with some digits. Please check and try again (e.g., PO-12345)."
                )
            ],
            completion_message=(
                "📦 Looking up order **{order_number}**...\n\n"
                "Your order is currently **In Transit** and expected to arrive in 3-5 business days.\n"
                "For real-time tracking, I can send updates to your email. Would you like that?"
            )
        ))
        
        # Bulk Discount Inquiry Flow
        self.register_flow(DialogFlow(
            name="bulk_discount_flow",
            trigger_intents=["INFO_BULK", "volume_discount", "bulk_pricing"],
            slots=[
                Slot(
                    name="product",
                    prompt="Which product are you considering for bulk order?",
                    entity_type="product"
                ),
                Slot(
                    name="quantity",
                    prompt="Approximately how many units are you thinking?",
                    entity_type="quantity",
                    validator=lambda x: x.isdigit() and int(x) >= 100,
                    error_message="For bulk discounts, minimum quantity is 100 units. How many do you need?"
                )
            ],
            completion_message=(
                "💰 Great news! For **{quantity} {product}**, here are your discount tiers:\n\n"
                "  • 100-499 units: 5% off\n"
                "  • 500-999 units: 10% off\n"
                "  • 1000+ units: 15% off + free shipping\n\n"
                "Would you like me to prepare a formal quote with exact pricing?"
            )
        ))
        
        # Sample Request Flow
        self.register_flow(DialogFlow(
            name="sample_flow",
            trigger_intents=["INFO_SAMPLE", "request_sample"],
            slots=[
                Slot(
                    name="product",
                    prompt="Which product would you like to sample?",
                    entity_type="product"
                ),
                Slot(
                    name="company",
                    prompt="What company are you with?",
                    entity_type="company"
                ),
                Slot(
                    name="email",
                    prompt="Where should we send the sample confirmation?",
                    entity_type="email",
                    validator=lambda x: "@" in x and "." in x.split("@")[-1]
                )
            ],
            completion_message=(
                "📬 Sample request submitted!\n\n"
                "  • Product: {product}\n"
                "  • Company: {company}\n\n"
                "We'll send sample details and pricing to {email}. "
                "Note: Sample cost is credited toward bulk orders over 500 units."
            )
        ))
        
        
        # Pricing Inquiry Flow
        self.register_flow(DialogFlow(
            name="pricing_flow",
            trigger_intents=["INFO_PRICE", "price_check"],
            slots=[
                Slot(
                    name="product",
                    prompt="Which product would you like pricing for?",
                    entity_type="product",
                    error_message="I didn't catch the product name. We have servo motors, specialized cables, and actuators."
                ),
                Slot(
                    name="large_order_check",
                    prompt="Asking... (dynamic prompt needed)", 
                    # Prompt is dynamic based on price lookup, mocked below in confirm step
                    # We use a dummy validation here because this is a YES/NO confirmation flow
                    entity_type="confirmation",
                    required=True, 
                    # Slot is filled via confirmation logic or manual "Yes/No"
                )
            ],
            completion_message="Checking custom pricing options...",
            confirmation_prompt=None  # Removed to prevent looping (Prompt handled by dynamic slot)
        ))
        
        # Product Inquiry Flow (Fallback for MOQ/Availability only)
        self.register_flow(DialogFlow(
            name="product_inquiry_flow",
            trigger_intents=["INFO_MOQ"], # INFO_PRICE moved to pricing_flow
            slots=[
                Slot(
                    name="product",
                    prompt="Which product would you like information about?",
                    entity_type="product"
                )
            ],
            completion_message=None  # Handled by main response logic
        ))
    
    def register_flow(self, flow: DialogFlow):
        """Register a new dialog flow."""
        self.flows[flow.name] = flow
    
    def get_flow_for_intent(self, intent: str) -> Optional[DialogFlow]:
        """Get a dialog flow triggered by the given intent."""
        for flow in self.flows.values():
            if intent in flow.trigger_intents:
                return flow
        return None
    
    def has_active_flow(self, session_id: str = "default") -> bool:
        """Check if there's an active dialog flow for this session."""
        return session_id in self.active_flows
    
    def get_active_flow(self, session_id: str = "default") -> Optional[DialogFlow]:
        """Get the active flow for a session."""
        if session_id in self.active_flows:
            flow_name = self.active_flows[session_id]
            return self.flows.get(flow_name)
        return None
    
    def clear_flow(self, session_id: str = "default"):
        """Force clear any active flow for a session."""
        self._end_flow(session_id)
    
    def process_turn(self, intent: Optional[str], entities: Dict, 
                     user_text: str, session_id: str = "default") -> Optional[Dict]:
        """
        Process a conversation turn.
        
        Args:
            intent: Detected intent (can be None if in active flow)
            entities: Extracted entities {type: Entity or value}
            user_text: Raw user input
            session_id: Session identifier
            
        Returns:
            Dict with response info, or None if no flow handling needed
            {
                "response": str,
                "flow_status": DialogStatus,
                "filled_slots": Dict,
                "action": Optional[str],
                "flow_name": str
            }
        """
        # Check if there's an active flow
        if self.has_active_flow(session_id):
            flow = self.get_active_flow(session_id)
            return self._continue_flow(flow, entities, user_text, session_id)
        
        # Check if intent triggers a new flow
        if intent:
            flow = self.get_flow_for_intent(intent)
            if flow:
                return self._start_flow(flow, entities, session_id)
        
        # No flow handling needed
        return None
    
    def _start_flow(self, flow: DialogFlow, entities: Dict, 
                    session_id: str) -> Dict:
        """Start a new dialog flow."""
        flow.reset()
        flow.status = DialogStatus.IN_PROGRESS
        flow.started_at = datetime.now()
        self.active_flows[session_id] = flow.name
        
        # Pre-fill slots from extracted entities
        for slot in flow.slots:
            if slot.entity_type and slot.entity_type in entities:
                entity_list = entities[slot.entity_type]
                # Handle list of entities (from extract_all) or single entity
                if isinstance(entity_list, list) and len(entity_list) > 0:
                    entity = entity_list[0]
                    value = entity.value if hasattr(entity, 'value') else str(entity)
                elif hasattr(entity_list, 'value'):
                    value = entity_list.value
                else:
                    value = str(entity_list)
                if slot.validate(value):
                    slot.value = slot.normalize(value)
        
        # Get next prompt or complete
        return self._get_next_prompt(flow, session_id)
    
    def _continue_flow(self, flow: DialogFlow, entities: Dict, 
                       user_text: str, session_id: str) -> Dict:
        """Continue an existing dialog flow."""
        
        # Check for cancellation
        cancel_phrases = ["cancel", "stop", "never mind", "nevermind", "forget it", "quit", "exit"]
        if any(phrase in user_text.lower() for phrase in cancel_phrases):
            return self._cancel_flow(flow, session_id)
        
        # Check for "skip" on optional slots
        current_slot = flow.get_next_empty_slot()
        if current_slot and not current_slot.required:
            if user_text.lower().strip() in ["skip", "no", "none", "n/a"]:
                current_slot.value = "N/A"
                return self._get_next_prompt(flow, session_id)
        
        # Check for confirmation response
        if flow.status == DialogStatus.AWAITING_CONFIRMATION:
            return self._handle_confirmation(flow, user_text, session_id)
        
        # Try to fill the current slot
        if current_slot:
            # First try entity extraction
            value = None
            if current_slot.entity_type and current_slot.entity_type in entities:
                entity_list = entities[current_slot.entity_type]
                # Handle list of entities (from extract_all) or single entity
                if isinstance(entity_list, list) and len(entity_list) > 0:
                    entity = entity_list[0]
                    value = entity.value if hasattr(entity, 'value') else str(entity)
                elif hasattr(entity_list, 'value'):
                    value = entity_list.value
                else:
                    value = str(entity_list)
            
            # Fall back to raw text
            if not value:
                value = user_text.strip()
            
            # Validate and fill
            if flow.fill_slot(current_slot.name, value):
                return self._get_next_prompt(flow, session_id)
            else:
                # Validation failed
                return self._get_error_response(flow, current_slot, session_id)
        
        return self._get_next_prompt(flow, session_id)
    
    
    def _get_next_prompt(self, flow: DialogFlow, session_id: str) -> Dict:
        """Get the next prompt or completion message."""
        next_slot = flow.get_next_required_empty_slot()
        
        if next_slot:
            # More required slots to fill
            prompt = next_slot.prompt
            
            # --- CUSTOM LOGIC: Dynamic Pricing Prompt ---
            if flow.name == "pricing_flow" and next_slot.name == "large_order_check":
                product_val = flow.get_filled_slots().get("product", "").lower()
                price = "$TBD"
                
                # Mock DB lookup
                mock_prices = {
                    "servo": "$450.00", "motor": "$450.00",
                    "fiber": "$120.00",  # Prioritize 'fiber' over 'cable'
                    "cable": "$12.00/m", 
                    "actuator": "$85.00",
                    "sensor": "$45.00",
                    "valve": "$60.00"
                }
                
                for k, v in mock_prices.items():
                    if k in product_val:
                        price = v
                        break
                
                prompt = (f"The standard price for **{product_val.title()}** is **{price}** (per unit).\n"
                          f"However, we offer custom quotes for large orders. \n\n"
                          f"Would you like to proceed with a custom quote request?")

            # Use reprompt if this is a retry
            elif next_slot.attempts > 0 and next_slot.reprompt_message:
                prompt = next_slot.reprompt_message
            
            return {
                "response": prompt,
                "flow_status": DialogStatus.IN_PROGRESS,
                "filled_slots": flow.get_filled_slots(),
                "action": None,
                "flow_name": flow.name,
                "current_slot": next_slot.name
            }
        
        # Check for optional slots
        optional_slot = flow.get_next_empty_slot()
        if optional_slot:
            return {
                "response": optional_slot.prompt,
                "flow_status": DialogStatus.IN_PROGRESS,
                "filled_slots": flow.get_filled_slots(),
                "action": None,
                "flow_name": flow.name,
                "current_slot": optional_slot.name
            }
        
        # All slots filled - check if confirmation needed
        if flow.confirmation_prompt and flow.status != DialogStatus.AWAITING_CONFIRMATION:
            flow.status = DialogStatus.AWAITING_CONFIRMATION
            filled = flow.get_filled_slots()
            confirmation = flow.confirmation_prompt.format(**filled)
            
            return {
                "response": confirmation,
                "flow_status": DialogStatus.AWAITING_CONFIRMATION,
                "filled_slots": filled,
                "action": None,
                "flow_name": flow.name
            }
        
        # Complete the flow
        return self._complete_flow(flow, session_id)
    
    def _get_error_response(self, flow: DialogFlow, slot: Slot, 
                           session_id: str) -> Dict:
        """Get error response when slot validation fails."""
        # Check if max attempts reached
        if slot.attempts >= slot.max_attempts:
            return self._cancel_flow(flow, session_id, 
                reason="Too many invalid attempts. Let's start over when you're ready.")
        
        error_msg = slot.error_message
        
        return {
            "response": error_msg,
            "flow_status": DialogStatus.IN_PROGRESS,
            "filled_slots": flow.get_filled_slots(),
            "action": None,
            "flow_name": flow.name,
            "current_slot": slot.name,
            "error": True
        }
    
    def _handle_confirmation(self, flow: DialogFlow, user_text: str, 
                            session_id: str) -> Dict:
        """Handle confirmation response."""
        text_lower = user_text.lower().strip()
        
        if text_lower in ["yes", "y", "correct", "confirm", "that's right", "yep", "yeah"]:
            return self._complete_flow(flow, session_id)
        elif text_lower in ["no", "n", "wrong", "incorrect", "change", "edit"]:
            # Let user modify - ask what to change
            return {
                "response": "What would you like to change? You can say things like 'change quantity to 1000' or 'different email'.",
                "flow_status": DialogStatus.IN_PROGRESS,
                "filled_slots": flow.get_filled_slots(),
                "action": None,
                "flow_name": flow.name
            }
        else:
            return {
                "response": "Please confirm with 'yes' or 'no'. " + flow.confirmation_prompt.format(**flow.get_filled_slots()),
                "flow_status": DialogStatus.AWAITING_CONFIRMATION,
                "filled_slots": flow.get_filled_slots(),
                "action": None,
                "flow_name": flow.name
            }
    
    def _complete_flow(self, flow: DialogFlow, session_id: str) -> Dict:
        """Complete the dialog flow."""
        filled = flow.get_filled_slots()
        
        # Format completion message
        if flow.completion_message:
            response = flow.completion_message.format(**filled)
        else:
            response = None  # Let caller handle
        
        # Call completion callback if defined
        if flow.on_complete:
            try:
                flow.on_complete(filled)
            except Exception as e:
                print(f"Flow completion callback error: {e}")
        
        # Clean up
        flow.status = DialogStatus.COMPLETED
        self._end_flow(session_id)
        
        return {
            "response": response,
            "flow_status": DialogStatus.COMPLETED,
            "filled_slots": filled,
            "action": None,
            "flow_name": flow.name
        }
    
    def _cancel_flow(self, flow: DialogFlow, session_id: str, 
                     reason: str = None) -> Dict:
        """Cancel the current flow."""
        flow.status = DialogStatus.CANCELLED
        self._end_flow(session_id)
        
        message = reason or "No problem, I've cancelled that. How else can I help you?"
        
        return {
            "response": message,
            "flow_status": DialogStatus.CANCELLED,
            "filled_slots": {},
            "action": None,
            "flow_name": flow.name
        }
    
    def _end_flow(self, session_id: str):
        """End the current flow for a session."""
        if session_id in self.active_flows:
            flow_name = self.active_flows[session_id]
            if flow_name in self.flows:
                self.flows[flow_name].reset()
            del self.active_flows[session_id]


# Global instance
dialog_manager = DialogManager()


# Example usage
if __name__ == "__main__":
    print("Dialog Manager Test")
    print("=" * 60)
    
    # Simulate RFQ conversation
    session = "test_session"
    
    # Turn 1: Trigger the flow
    print("\nUser: I want a quote")
    result = dialog_manager.process_turn(
        intent="NAV_RFQ",
        entities={},
        user_text="I want a quote",
        session_id=session
    )
    print(f"Bot: {result['response']}")
    
    # Turn 2: Provide product
    print("\nUser: servo motors")
    result = dialog_manager.process_turn(
        intent=None,
        entities={"product": type('Entity', (), {'value': 'servo motor'})()},
        user_text="servo motors",
        session_id=session
    )
    print(f"Bot: {result['response']}")
    
    # Turn 3: Provide quantity
    print("\nUser: 500")
    result = dialog_manager.process_turn(
        intent=None,
        entities={"quantity": type('Entity', (), {'value': '500'})()},
        user_text="500",
        session_id=session
    )
    print(f"Bot: {result['response']}")
    
    # Turn 4: Provide company
    print("\nUser: Acme Industries")
    result = dialog_manager.process_turn(
        intent=None,
        entities={},
        user_text="Acme Industries",
        session_id=session
    )
    print(f"Bot: {result['response']}")
    
    # Turn 5: Provide email
    print("\nUser: orders@acme.com")
    result = dialog_manager.process_turn(
        intent=None,
        entities={"email": type('Entity', (), {'value': 'orders@acme.com'})()},
        user_text="orders@acme.com",
        session_id=session
    )
    print(f"Bot: {result['response']}")
    print(f"\nFlow Status: {result['flow_status']}")
    print(f"Filled Slots: {result['filled_slots']}")
