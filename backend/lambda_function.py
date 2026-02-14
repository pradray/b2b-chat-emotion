"""
Enhanced Lambda Function v11
Integrates all conversational AI improvements:
- Context Management
- Semantic NLU (Active Layer 2)
- Entity Extraction
- Dialog State Management
- Disambiguation
- LLM Fallback
- Robust OOS & Topic Shift Detection
- Business Term Whitelist & Deterministic Overrides
"""

import json
import random
import re
import logging
from typing import Dict, Tuple, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Original imports
from fuzzywuzzy import fuzz, process

# Existing modules
from emotion_detector import detect_emotion, get_emotion_emoji, needs_empathy
from empathetic_responses import enhance_response

# New improvement modules
from context_manager import context_store
from entity_extractor import entity_extractor, Entity
from dialog_manager import dialog_manager, DialogStatus
from llm_fallback import llm_fallback

# Import Semantic NLU (Initialized at bottom of file)
try:
    from semantic_nlu import semantic_nlu
except ImportError:
    semantic_nlu = None


# ============================================================================
# INTENT AND RESPONSE DEFINITIONS
# ============================================================================

# Intent map (keeping original for fuzzy fallback, enhanced for semantic)
INTENT_MAP = {
    # Navigation
    "NAV_MARKETPLACE": ["marketplace", "market", "browse", "products", "items", "catalog"],
    "NAV_SUPPLIER":    ["supplier", "suppliers", "vendor", "manufacturer", "factory"],
    "NAV_RFQ":         ["request for quote", "bulk quote", "estimate", "get quote", "request quote", "custom pricing"],
    "NAV_QUOTE":       ["quote", "pricing", "cost estimation"],
    "NAV_LOGIN":       ["login", "sign in", "log in", "credentials"],
    "NAV_REGISTER":    ["register", "signup", "sign up", "join", "create account"],

    # Business Logic
    "INFO_MOQ":        ["moq", "minimum order", "min qty", "smallest order", "minimum quantity"],
    "INFO_PRICE":      ["price of product", "item cost", "rates", "pricing", "how much is this", "unit price", "cost per unit"],
    "INFO_BULK":       ["bulk", "volume discount", "large order", "wholesale", "bulk discount", "buy units", "purchase units", "buy 500", "need 1000", "need 500 units"],
    "INFO_SHIPPING":   ["shipping", "freight", "transport", "logistics", "ship to", "ship to India", "shipping to usa", "deliver to", "shipping method", "shipping cost", "cost of shipping", "freight cost", "delivery price"],
    "INFO_TRACK":      ["track", "tracking", "status", "shipment", "where is my order", "status of rfq", "rfq status", "order status"],
    "INFO_INVOICE":    ["invoice", "bill", "receipt", "commercial invoice"],
    "INFO_PAYMENT":    ["payment", "pay", "bank details", "wire transfer"],
    "INFO_CREDIT":     ["credit", "payment terms", "net 30", "credit line"],
    "INFO_CATALOG":    ["catalog", "brochure", "pdf", "product list"],
    "INFO_RETURN":     ["return", "refund", "rma", "exchange", "damaged"],
    "INFO_LEADTIME":   ["lead time", "how long", "turnaround", "wait time", "delivery time", "when will it arrive", "estimated delivery", "how long to deliver", "delivery date", "when can i get it"],
    "INFO_SAMPLE":     ["sample", "prototype", "test unit"],
    "INFO_STOCK":      ["stock", "inventory", "available", "quantity on hand"],
    "INFO_WARRANTY":   ["warranty", "guarantee", "repair"],
    "INFO_CUSTOMS":    ["customs", "customs duty", "import duty", "import tax", "tariffs"],
    "INFO_CONTEXT":    ["which product", "what was i asking", "what are we talking about", "current product"],
    "INFO_RFQ_STATUS": ["rfq status", "quote status", "status of rfq", "where is my quote"],

    # Greetings & Help
    "GREETING":        ["hello", "hi", "hey", "greetings", "good morning", "good afternoon"],
    "HELP":            ["help", "support", "assist", "stuck", "what can you do"],

    # Emotional expressions (kept for direct matching)
    "EMOTION_THANKS":  ["thank you", "thanks", "appreciate", "grateful"],
    "EMOTION_HAPPY":   ["happy", "love it", "amazing", "wonderful", "fantastic"],
    "EMOTION_FRUSTRATED": ["frustrated", "annoyed", "irritated", "fed up"],
    "EMOTION_ANGRY":   ["angry", "furious", "outraged", "unacceptable", "terrible"],
    
    # Farewell
    "FAREWELL":        ["bye", "goodbye", "see you", "later", "take care"],
    "CONTROL_RESTART": ["restart", "start over", "reset", "clear session", "new session"],
    
    # Product Inquiry (do you have X, looking for X)
    "PRODUCT_INQUIRY": ["do you have", "do you sell", "looking for", "need", "want to buy", "interested in", "available", "in stock", "tell me about", "details on", "info on", "heavy duty"]
}

# Response templates
RESPONSE_MAP = {
    # Navigation
    "NAV_MARKETPLACE": {"msg": "Opening the Wholesale Marketplace...", "act": "marketplace"},
    "NAV_SUPPLIER":    {"msg": "Here is our list of verified manufacturers.", "act": "suppliers"},
    "NAV_RFQ":         {"msg": "I'll help you submit a Request for Quote.", "act": None},
    "NAV_QUOTE":       {"msg": "Please fill out the RFQ form for custom pricing.", "act": "rfq"},
    "NAV_LOGIN":       {"msg": "Redirecting to Partner Login...", "act": "login"},
    "NAV_REGISTER":    {"msg": "New partners can register via the Login page.", "act": "login"},

    # Business Logic
    "INFO_MOQ":        {"msg": "Standard MOQ is 50 units. Custom runs require 500 units.", "act": None},
    "INFO_PRICE":      {"msg": "Login to see Tier-1 wholesale pricing.", "act": "login"},
    "INFO_BULK":       {"msg": "Orders >1000 units get a 15% volume discount.", "act": None},
    "INFO_SHIPPING":   {"msg": "We ship FOB and EXW via Maersk or DHL.", "act": None},
    "INFO_TRACK":      {"msg": "Enter your PO Number to track your order.", "act": None},
    "INFO_INVOICE":    {"msg": "Invoices are emailed automatically upon dispatch.", "act": None},
    "INFO_PAYMENT":    {"msg": "We accept Net-30, LC, and TT.", "act": None},
    "INFO_CREDIT":     {"msg": "Apply for a credit line in your dashboard.", "act": None},
    "INFO_CATALOG":    {"msg": "The Q4 Catalog is available in the 'Resources' tab.", "act": None},
    "INFO_RETURN":     {"msg": "RMA requests are valid for 14 days post-delivery.", "act": None},
    "INFO_LEADTIME":   {"msg": "Current manufacturing lead time is 14 days.", "act": None},
    "INFO_SAMPLE":     {"msg": "Paid samples are available. Contact sales.", "act": None},
    "INFO_STOCK":      {"msg": "Live inventory is updated every 4 hours.", "act": None},
    "INFO_WARRANTY":   {"msg": "Industrial parts carry a 1-year manufacturer warranty.", "act": None},
    "INFO_CUSTOMS":    {"msg": "Buyer is responsible for import duties.", "act": None},
    "INFO_CONTEXT":    {"msg": "We were discussing {product}.", "act": None},
    
    # System Signal (Invisible Frontend Event)
    "SYSTEM_RFQ_SUBMITTED": {"msg": "Thank you! We've received your RFQ. Reference #REQ-{random_id}. I'm opening the Marketplace for you to browse more products.", "act": "marketplace"},

    # Greetings & Help
    "GREETING":        {"msg": "Welcome to B2B Hub! How can I assist you today?", "act": None},
    "HELP":            {"msg": "I can help with product info, pricing, shipping, orders, and more. What do you need?", "act": None},

    # Farewell
    "FAREWELL":        {"msg": "Goodbye! It was great helping you today. Come back anytime!", "act": None},
    
    # Product Inquiry
    "PRODUCT_INQUIRY": {"msg": "Yes, we carry that product! Would you like to know about pricing, MOQ, or availability? You can also browse our Marketplace.", "act": None},
    
    # Process Control
    "CONTROL_CANCEL":  {"msg": "I've cancelled the current request. How else can I help you?", "act": "reset"},
    "CONTROL_RESTART": {"msg": "I've reset the conversation. How can I help you?", "act": "reset"},
    "OUT_OF_SCOPE":    {"msg": "I apologize, but I can only assist with industrial parts, orders, and shipping. I cannot help with general topics.", "act": None},
    
    # RFQ Status (Dynamic response tailored in code)
    "INFO_RFQ_STATUS": {"msg": "Our Sales team is urgently working on the RFQ, you will hear from them shortly.", "act": None}
}

# Emotional response variants
EMOTIONAL_RESPONSES = {
    "EMOTION_THANKS": [
        "You're very welcome! 😊 Is there anything else I can help with?",
        "Happy to help! Let me know if you need anything else.",
        "My pleasure! What else can I do for you today?",
    ],
    "EMOTION_HAPPY": [
        "That's wonderful to hear! 🎉 How else can I assist you?",
        "I'm thrilled you're having a great experience! What's next?",
        "Fantastic! Let me know what else you need.",
    ],
    "EMOTION_FRUSTRATED": [
        "I completely understand your frustration, and I'm sorry you're experiencing this. 😔 Let me help make things right. What's the main issue?",
        "I hear you, and your frustration is valid. Let's work through this together. Can you tell me more?",
    ],
    "EMOTION_ANGRY": [
        "I sincerely apologize for this experience. 😞 Let me help resolve this immediately. What happened?",
        "I'm truly sorry. This isn't the experience we want for you. How can I make this right?",
    ]
}


# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================

HIGH_CONFIDENCE = 0.75      # Use template directly
MEDIUM_CONFIDENCE = 0.55    # Use template but may need clarification
LOW_CONFIDENCE = 0.40       # Consider disambiguation
FALLBACK_THRESHOLD = 0.35   # Use LLM fallback


# ============================================================================
# MAIN HANDLER
# ============================================================================

def lambda_handler(event, context):
    """
    Enhanced lambda handler with full conversational AI capabilities.
    """
    
    # 1. Parse Input
    body = event.get('body', {})
    if isinstance(body, str):
        body = json.loads(body)
    
    user_text = body.get('message', '')
    original_text = user_text
    session_id = body.get('sessionId', 'default')
    
    # 2. Get/Create Conversation Context
    conv_context = context_store.get_or_create(session_id)
    
    # 3. Reference Resolution (e.g., "it", "that", "them")
    # Skip for System Commands or short inputs
    if not user_text.startswith("SYSTEM_") and not user_text.startswith("TRACER:"):
        resolved_text = conv_context.resolve_reference(user_text)
    else:
        resolved_text = user_text
    
    if resolved_text != user_text:
        logger.info(f"Resolved reference: '{user_text}' -> '{resolved_text}'")
    
    # 4. Detect Emotion
    emotion_data = detect_emotion(resolved_text)
    detected_emotion = emotion_data["emotion"]
    emotion_intensity = emotion_data["intensity"]
    
    # ---------------------------------------------------------
    # 5. Extract Entities EARLY (Needed for Guards)
    # ---------------------------------------------------------
    entities = entity_extractor.extract_all(original_text)
    detected_product = None
    if "product" in entities and entities["product"]:
        detected_product = entities["product"][0].value

    # ---------------------------------------------------------
    # 6. INTENT DETECTION with v11 GUARDS
    # ---------------------------------------------------------
    
    detected_intent = None
    confidence = 0.0
    match_method = None
    
    # 6a. SYSTEM SIGNALS
    if original_text.strip() == "SYSTEM_RFQ_SUBMITTED":
        detected_intent = "SYSTEM_RFQ_SUBMITTED"
        confidence = 1.0
        match_method = "system_signal"
    
    # 6b. KEYWORD SHORT-CIRCUIT (Robustness for Cancel/OOS)
    elif any(w in resolved_text.lower().split() for w in ["cancel", "stop", "abort", "terminate", "exit", "quit"]):
        detected_intent = "CONTROL_CANCEL"
        confidence = 1.0
        match_method = "keyword_short_circuit"
        
    # 6c. OUT_OF_SCOPE GUARD (v10 FIX: Business Whitelist + Regex + Product Guard)
    elif not detected_product: 
        # v10 FIX: Allow business terms even if no product is found (Account Manager, Sales Rep)
        business_terms = ["account manager", "sales rep", "representative", "support", "human", "agent"]
        is_business_query = any(term in resolved_text.lower() for term in business_terms)
        
        if not is_business_query:
            oos_phrases = ["joke", "weather", "president", "politics", "recipe", "capital of", "who is", "game", "movie"]
            # Use \b to match whole words only (prevents "weather resistance" -> OOS)
            is_oos = any(re.search(rf'\b{p}\b', resolved_text.lower()) for p in oos_phrases)
            
            if is_oos:
                detected_intent = "OUT_OF_SCOPE"
                confidence = 1.0
                match_method = "keyword_short_circuit"
            
    # 6d. Standard hybrid detection (Now includes Semantic Check!)
    if not detected_intent:
        detected_intent, confidence, match_method = _detect_intent_hybrid(resolved_text)

    # ---------------------------------------------------------
    # 7. MID-FLOW CONTEXT SWITCH (Topic Shift)
    # ---------------------------------------------------------
    current_product = conv_context.get_entity("product")
    
    # Only trigger shift if we HAVE a current product AND the new one is different.
    if current_product and detected_product and detected_product.lower() != current_product.lower():
        logger.info(f"TOPIC SHIFT DETECTED: {current_product} -> {detected_product}")
        
        # Update context immediately
        conv_context.entities["product"] = detected_product
        
        # 1. Force Clear any active Dialog Flow
        dialog_manager.clear_flow(session_id)
        
        # 2. Re-run intent detection on the new input
        # We re-run because the context shift might change how we interpret the intent
        # For simplicity in v11, we trust the Semantic/Fuzzy result from above unless confidence is low
        
        match_method = "topic_shift_correction"
        
        # Default fallback
        if confidence < 0.6:
            detected_intent = "PRODUCT_INQUIRY"
            confidence = 1.0
        
        # If price was mentioned, upgrade to Pricing Flow
        if "price" in resolved_text.lower() or "pricing" in resolved_text.lower():
             detected_intent = "INFO_PRICE"
             confidence = 1.0
        
        # If it looks like a bulk inquiry, upgrade to Bulk Flow
        if "bulk" in resolved_text.lower() or "volume" in resolved_text.lower():
            detected_intent = "INFO_BULK"
            confidence = 1.0

    # ---------------------------------------------------------
    # 8. INTENT CORRECTIONS
    # ---------------------------------------------------------

    # v10 FIX: Force "how long to deliver" to LEADTIME (overrides fuzzy SHIPPING match)
    if "how long" in resolved_text.lower() and "deliver" in resolved_text.lower():
        detected_intent = "INFO_LEADTIME"
        confidence = 1.0
        match_method = "keyword_correction"

    # CORRECTION: "What about fiber optic?" -> Product Inquiry
    if detected_intent == "INFO_CONTEXT" and detected_product:
        detected_intent = "PRODUCT_INQUIRY"
        confidence = 1.0
        match_method = "entity_correction"
        
    # CORRECTION: "Pricing please" -> INFO_PRICE
    if detected_intent in ["NAV_QUOTE", "NAV_RFQ"] and ("price" in resolved_text.lower() or "pricing" in resolved_text.lower()):
        detected_intent = "INFO_PRICE"
        confidence = 1.0
        match_method = "keyword_correction"

    # CORRECTION: RFQ Status check by ID
    if "rfq_id" in entities:
        detected_intent = "INFO_RFQ_STATUS"
        confidence = 1.0
        match_method = "entity_correction"

    # CORRECTION: "rfq status" check (Generic)
    if "rfq" in resolved_text.lower() and "status" in resolved_text.lower():
        detected_intent = "INFO_RFQ_STATUS"
        confidence = 1.0
        match_method = "keyword_correction"

    # CORRECTION: "What is status of RFQ..." -> INFO_TRACK
    status_keywords = ["status", "track", "tracking", "where is", "update on", "check on"]
    if detected_intent in ["NAV_QUOTE", "NAV_RFQ"] and any(kw in resolved_text.lower() for kw in status_keywords):
        detected_intent = "INFO_TRACK"
        confidence = 1.0
        match_method = "keyword_correction"

    # CORRECTION: "price of X" -> INFO_PRICE
    if "price of" in resolved_text.lower():
        detected_intent = "INFO_PRICE"
        confidence = 1.0
        match_method = "keyword_correction"

    entities_for_intent = {}
    
    # ---------------------------------------------------------
    # 9. DIALOG FLOW EXECUTION
    # ---------------------------------------------------------
    if dialog_manager.has_active_flow(session_id):
        dialog_result = dialog_manager.process_turn(
            intent=None,
            entities=entities,
            user_text=resolved_text,
            session_id=session_id
        )
        
        if dialog_result and dialog_result.get("response"):
            response_msg = dialog_result["response"]
            
            # Handler for {random_id} if present in flow response
            if "{random_id}" in response_msg:
                random_id = random.randint(10000, 99999)
                response_msg = response_msg.replace("{random_id}", str(random_id))
            elif dialog_result["flow_status"] == DialogStatus.COMPLETED:
                response_msg = enhance_response(response_msg, detected_emotion, emotion_intensity)
                
            action = dialog_result.get("action")
            
            # Pricing Flow specific logic
            if dialog_result.get("flow_name") == "pricing_flow" and \
               dialog_result.get("flow_status").value == "completed":
                slots = dialog_result.get("filled_slots", {})
                check_val = slots.get("large_order_check", "").lower()
                if check_val in ["yes", "y", "sure", "ok", "yeah", "yes please", "yes, please"]:
                    action = "rfq"
                    response_msg += " Opening the bulk RFQ form now."
                else:
                    response_msg += " Let me know if you need anything else!"
            
            return _build_response(
                message=response_msg,
                action=action,
                emotion_data=emotion_data,
                intent=dialog_result.get("flow_name"),
                entities=dialog_result.get("filled_slots", {}),
                conv_context=conv_context,
                original_text=original_text,
                resolved_text=resolved_text
            )
    
    
    if detected_intent:
        entities_for_intent = entity_extractor.extract_for_intent(resolved_text, detected_intent)
    
    # ---------------------------------------------------------
    # 10. EMOTIONAL EXPRESSION HANDLER
    # ---------------------------------------------------------
    emotional_intent = _check_emotional_expression(resolved_text.lower())
    if emotional_intent and emotional_intent in EMOTIONAL_RESPONSES:
        response_msg = random.choice(EMOTIONAL_RESPONSES[emotional_intent])
        
        return _build_response(
            message=response_msg,
            action=None,
            emotion_data=emotion_data,
            intent=emotional_intent,
            entities={},
            conv_context=conv_context,
            original_text=original_text,
            resolved_text=resolved_text
        )
        
    # ---------------------------------------------------------
    # 11. SPECIAL INTENT HANDLERS (RFQ Status, Cancel, OOS)
    # ---------------------------------------------------------
    if detected_intent == "INFO_RFQ_STATUS":
        rfq_response = RESPONSE_MAP["INFO_RFQ_STATUS"]["msg"]
        
        time_keywords = ["when", "date", "time", "how long", "deadline", "by"]
        if any(w in resolved_text.lower() for w in time_keywords):
            rfq_response = "Our SLA is 1 week, however, we have always beaten our SLAs, so you will hear from us soon."
            
        anger_keywords = ["angry", "upset", "frustrated", "taking too long", "weeks", "late", "slow", "holding up"]
        if detected_emotion in ["EMOTION_ANGRY", "EMOTION_FRUSTRATED"] or emotion_intensity == "high" or any(w in resolved_text.lower() for w in anger_keywords):
            rfq_response = "Sorry for the inconvenience, there must be something that is holding up our team's response. Our Sales Rep will call you today to provide you with the details."
            
        return _build_response(
            message=rfq_response,
            action=None,
            emotion_data=emotion_data,
            intent="INFO_RFQ_STATUS",
            entities={k: [e.value for e in v] if isinstance(v, list) else v for k, v in entities.items()},
            conv_context=conv_context,
            original_text=original_text,
            resolved_text=resolved_text
        )

    if detected_intent == "CONTROL_CANCEL":
        dialog_manager.active_flows.pop(session_id, None)
        conv_context.current_entities = {}
        return _build_response(
            message=RESPONSE_MAP["CONTROL_CANCEL"]["msg"],
            action="reset",
            emotion_data=emotion_data,
            intent="CONTROL_CANCEL",
            entities={},
            conv_context=conv_context,
            original_text=original_text,
            method=match_method,
            resolved_text=resolved_text
        )

    if detected_intent == "OUT_OF_SCOPE":
        return _build_response(
            message=RESPONSE_MAP["OUT_OF_SCOPE"]["msg"],
            action=None,
            emotion_data=emotion_data,
            intent="OUT_OF_SCOPE",
            entities={},
            conv_context=conv_context,
            original_text=original_text,
            resolved_text=resolved_text
        )
    
    # ---------------------------------------------------------
    # 12. RESPONSE GENERATION (Template vs Dialog vs Fallback)
    # ---------------------------------------------------------
    
    # HIGH CONFIDENCE: Check if intent triggers a dialog flow
    if detected_intent and confidence >= HIGH_CONFIDENCE:
        flow = dialog_manager.get_flow_for_intent(detected_intent)
        if flow:
            # Inject context entity if product missing in current turn
            if "product" not in entities and conv_context.entities.get("product"):
                 prod_val = conv_context.entities["product"]
                 synthetic_entity = Entity(
                     type="product", 
                     value=prod_val, 
                     original_text=prod_val, 
                     start=0, end=0, confidence=1.0
                 )
                 entities["product"] = [synthetic_entity]

            dialog_result = dialog_manager.process_turn(
                intent=detected_intent,
                entities=entities,
                user_text=resolved_text,
                session_id=session_id
            )
            if dialog_result and dialog_result.get("response"):
                action = dialog_result.get("action")
                message = dialog_result.get("response", "")

                if dialog_result.get("flow_name") == "pricing_flow" and \
                   dialog_result.get("flow_status").value == "completed":
                    slots = dialog_result.get("filled_slots", {})
                    check_val = slots.get("large_order_check", "").lower()
                    if check_val in ["yes", "y", "sure", "ok", "yeah"]:
                        action = "rfq"
                        message += " Opening the bulk RFQ form now."
                    else:
                        message += " Let me know if you need anything else!"

                return _build_response(
                    message=message,
                    action=action,
                    emotion_data=emotion_data,
                    intent=detected_intent,
                    entities=dialog_result.get("filled_slots", {}),
                    conv_context=conv_context,
                    original_text=original_text,
                    confidence=confidence,
                    method=match_method,
                    resolved_text=resolved_text
                )
        
        # Use template response
        response_data = _generate_template_response(
            detected_intent, 
            detected_emotion, 
            emotion_intensity,
            entities_for_intent,
            context_entities=conv_context.entities
        )
        
        return _build_response(
            message=response_data["message"],
            action=response_data.get("action"),
            emotion_data=emotion_data,
            intent=detected_intent,
            entities={k: v.value if hasattr(v, 'value') else v for k, v in entities_for_intent.items()},
            conv_context=conv_context,
            original_text=original_text,
            confidence=confidence,
            method=match_method,
            resolved_text=resolved_text
        )
    
    # MEDIUM CONFIDENCE
    elif detected_intent and confidence >= MEDIUM_CONFIDENCE:
        response_data = _generate_template_response(
            detected_intent,
            detected_emotion,
            emotion_intensity,
            entities_for_intent,
            context_entities=conv_context.entities
        )
        
        prefix = ""
        if detected_intent not in ["PRODUCT_INQUIRY", "GREETING", "FAREWELL"] and \
           not detected_intent.startswith("INFO_") and \
           not detected_intent.startswith("NAV_"):
            prefix = random.choice([
                "I think you're asking about this: ",
                "If I understand correctly: ",
                "It sounds like you want to know: "
            ])
        
        return _build_response(
            message=prefix + response_data["message"],
            action=response_data.get("action"),
            emotion_data=emotion_data,
            intent=detected_intent,
            entities={k: v.value if hasattr(v, 'value') else v for k, v in entities_for_intent.items()},
            conv_context=conv_context,
            original_text=original_text,
            confidence=confidence,
            method=match_method,
            resolved_text=resolved_text
        )
    
    # LOW CONFIDENCE (Fallback)
    else:
        current_entities = {}
        if entities:
            for etype, elist in entities.items():
                if elist:
                    best_entity = elist[0]
                    val = best_entity.value if hasattr(best_entity, 'value') else best_entity
                    current_entities[etype] = val
        
        if not current_entities:
            current_entities = conv_context.entities.copy()
        
        context_string = conv_context.get_context_string()
        
        fallback_response = llm_fallback.generate_response(
            user_message=original_text,
            context=context_string,
            detected_emotion=detected_emotion
        )
        
        fallback_response = enhance_response(fallback_response, detected_emotion, emotion_intensity)
        
        return _build_response(
            message=fallback_response,
            action=None,
            emotion_data=emotion_data,
            intent=None,
            entities=current_entities,
            conv_context=conv_context,
            original_text=original_text,
            confidence=confidence,
            method="llm_fallback",
            resolved_text=resolved_text
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _detect_intent_hybrid(text: str) -> Tuple[Optional[str], float, str]:
    """Hybrid intent detection using semantic embeddings (Layer 2) + fuzzy matching (Layer 3)."""
    
    semantic_result = None
    fuzzy_result = None
    
    text_lower = text.lower().strip()
    
    # Continuity words check
    if text_lower in ["yes", "no", "yep", "yeah", "nope", "ok", "okay", "sure", "alright", "correct"]:
        return (None, 0.0, "continuity_word")
        
    # Category question check
    category_patterns = ["what types", "what kinds", "which types", "what options", 
                         "what products", "list of", "show me all", "what do you have",
                         "what are the", "categories", "variety", "types of", "kinds of",
                         "type of", "kind of", "sort of", "sorts of"]
    if any(pattern in text_lower for pattern in category_patterns):
        return (None, 0.0, "category_question")
    
    # --- LAYER 2: SEMANTIC NLU ---
    # Check if the global semantic_nlu instance is ready
    if semantic_nlu and semantic_nlu.is_ready:
        semantic_match = semantic_nlu.match_intent(text, threshold=0.45) # Lower threshold for semantic
        if semantic_match:
            semantic_result = (semantic_match.intent, semantic_match.confidence, "semantic")
            
            # Optimization: If semantic confidence is very high, return immediately
            if semantic_match.confidence > 0.85:
                return semantic_result

    # --- LAYER 3: FUZZY MATCHING ---
    best_fuzzy_intent = None
    best_fuzzy_score = 0
    
    for intent, phrases in INTENT_MAP.items():
        if intent.startswith("EMOTION_"): continue
        match, score = process.extractOne(text, phrases, scorer=fuzz.token_set_ratio)
        if score > best_fuzzy_score:
            best_fuzzy_score = score
            best_fuzzy_intent = intent
    
    fuzzy_confidence = best_fuzzy_score / 100.0
    if fuzzy_confidence >= 0.5:
        fuzzy_result = (best_fuzzy_intent, fuzzy_confidence, "fuzzy")
    
    # --- ARBITRATION LOGIC ---
    if semantic_result and fuzzy_result:
        # If semantic is confident, trust it more than fuzzy
        # This fixes "how long to deliver" (Fuzzy: Shipping, Semantic: LeadTime)
        if semantic_result[1] >= 0.60:
            return semantic_result
        # Otherwise trust the higher score
        elif semantic_result[1] >= fuzzy_result[1]:
            return semantic_result
        else:
            return fuzzy_result
    elif semantic_result:
        return semantic_result
    elif fuzzy_result:
        return fuzzy_result
    else:
        return (None, max(fuzzy_confidence, 0), "none")


def check_product_availability(product_name: str) -> Tuple[bool, str]:
    """Check if a product is actually carried in inventory."""
    out_of_stock = {
        "optics", "lens", "lenses", "mirror", "mirrors", "prism", "prisms", 
        "optical components", "agricultural", "farming", "food"
    }
    prod_lower = str(product_name).lower()
    for item in out_of_stock:
        if item in prod_lower:
            return False, f"We currently do not stock {product_name} in our inventory."
    return True, "Available"


def _check_emotional_expression(text: str) -> Optional[str]:
    """Check for direct emotional expressions."""
    emotional_keywords = {
        "EMOTION_THANKS": ["thank you", "thanks", "appreciate it", "grateful"],
        "EMOTION_HAPPY": ["love it", "amazing", "wonderful", "fantastic", "excellent"],
        "EMOTION_FRUSTRATED": ["so frustrated", "fed up", "sick of", "tired of this"],
        "EMOTION_ANGRY": ["furious", "outraged", "unacceptable", "this is terrible"]
    }
    farewell_keywords = ["bye", "goodbye", "see you", "later"]
    if any(w in text.lower() for w in farewell_keywords):
        return None
    
    for intent, keywords in emotional_keywords.items():
        for keyword in keywords:
            if keyword in text.lower():
                return intent
    return None


def _generate_template_response(intent: str, emotion: str, 
                                 intensity: str, entities: Dict,
                                 context_entities: Dict = None) -> Dict:
    """Generate response from templates with entity substitution."""
    
    if intent not in RESPONSE_MAP:
        return {
            "message": "I'm not sure how to help with that. Try asking about products, pricing, or shipping.",
            "action": None
        }
    
    data = RESPONSE_MAP[intent]
    message = data["msg"]
    
    has_product = entities and "product" in entities
    use_context = intent != "PRODUCT_INQUIRY"
    
    if use_context and not has_product and context_entities and "product" in context_entities:
        has_product = True
        product_val = context_entities["product"]
    elif has_product:
        product = entities["product"]
        product_val = product.value if hasattr(product, 'value') else str(product)
    else:
        product_val = None
    
    if has_product and product_val:
        if intent == "INFO_MOQ":
            message = f"For {product_val}, standard MOQ is 50 units. Custom runs require 500 units."
        elif intent == "INFO_LEADTIME":
            message = f"Lead time for {product_val} is typically 14-21 days."
        elif intent == "INFO_STOCK":
            is_available, avail_msg = check_product_availability(product_val)
            if is_available:
                message = f"Yes, {product_val} is currently in stock and ready to ship!"
            else:
                message = avail_msg
        elif intent == "PRODUCT_INQUIRY":
            is_available, avail_msg = check_product_availability(product_val)
            if is_available:
                message = f"Yes, we have {product_val}! Would you like to know about pricing, MOQ, or availability? You can also browse our Marketplace to see all options."
            else:
                message = avail_msg
        elif intent == "INFO_CONTEXT":
            message = f"We were discussing {product_val}. Would you like to know about its pricing, MOQ, or availability?"
        elif intent == "INFO_PRICE":
            is_available, avail_msg = check_product_availability(product_val)
            if is_available:
                message = f"Login to see Tier-1 wholesale pricing for {product_val}."
            else:
                message = avail_msg
    elif intent == "PRODUCT_INQUIRY":
        message = "I'm not sure if we carry that specific product, but you can browse our Marketplace to see all available industrial products. Would you like me to help you search, or would you prefer to submit an RFQ for a custom inquiry?"
    elif intent == "INFO_CONTEXT":
        message = "We haven't started discussing a specific product yet. You can browse our Marketplace to see what we offer!"
    elif intent == "SYSTEM_RFQ_SUBMITTED":
        random_id = random.randint(10000, 99999)
        message = message.replace("{random_id}", str(random_id))
    
    if entities and "quantity" in entities:
        quantity = entities["quantity"]
        qty_val = quantity.value if hasattr(quantity, 'value') else str(quantity)
        
        if intent == "INFO_BULK":
            try:
                qty_int = int(qty_val)
                if qty_int >= 1000:
                    message = f"Great news! For {qty_val} units, you qualify for our 15% bulk discount plus free shipping!"
                elif qty_int >= 500:
                    message = f"For {qty_val} units, you qualify for a 10% volume discount."
                elif qty_int >= 100:
                    message = f"For {qty_val} units, you qualify for a 5% volume discount."
            except ValueError:
                pass
    
    if intent != "SYSTEM_RFQ_SUBMITTED":
        enhanced_message = enhance_response(message, emotion, intensity)
    else:
        enhanced_message = message
    
    return {
        "message": enhanced_message,
        "action": data.get("act")
    }


def _build_response(message: str, action: Optional[str], 
                    emotion_data: Dict, intent: Optional[str],
                    entities: Dict, conv_context: Any,
                    original_text: str, confidence: float = None,
                    method: str = None, resolved_text: str = None) -> Dict:
    """Build the final response object and save conversation turn."""
    
    if message and "{random_id}" in message:
         random_id = random.randint(10000, 99999)
         message = message.replace("{random_id}", str(random_id))
         
    conv_context.add_turn(
        user_message=original_text,
        bot_response=message,
        intent=intent,
        entities=entities,
        emotion=emotion_data.get("emotion")
    )
    
    if intent == "SYSTEM_RFQ_SUBMITTED" or (message and "#REQ-" in message):
        emotion_data["emotion"] = "happy"
        emotion_data["intensity"] = "high"

    response_body = {
        "message": message,
        "action": action,
        "emotion": {
            "detected": emotion_data.get("emotion"),
            "confidence": emotion_data.get("confidence", 0),
            "intensity": emotion_data.get("intensity", "low"),
            "emoji": get_emotion_emoji(emotion_data.get("emotion", "neutral"))
        }
    }
    
    if intent:
        response_body["debug_intent"] = intent
    if confidence is not None:
        response_body["debug_confidence"] = round(confidence, 3)
    if method:
        response_body["debug_method"] = method
    if entities:
        response_body["debug_entities"] = entities
    
    # v11 Fix: Added debug_resolved_text to response for frontend debugger
    if resolved_text:
        response_body["debug_resolved_text"] = resolved_text
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
        'body': json.dumps(response_body)
    }

# ============================================================================
# INITIALIZATION (The Critical Link)
# ============================================================================
if semantic_nlu:
    # This triggers the model download (~80MB) and vector caching
    semantic_nlu.initialize(INTENT_MAP)