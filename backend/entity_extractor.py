"""
Entity Extraction Module
Extracts structured entities from user input using patterns and rules.

Add to your backend folder and import in lambda_function.py:
    from entity_extractor import entity_extractor

For more advanced NER, consider:
    pip install spacy
    python -m spacy download en_core_web_sm
"""

import re
import difflib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from itertools import combinations


@dataclass
class Entity:
    """Extracted entity."""
    type: str
    value: str
    original_text: str
    start: int
    end: int
    confidence: float
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "value": self.value,
            "original_text": self.original_text,
            "confidence": self.confidence
        }


class EntityExtractor:
    """
    Extract named entities from text using patterns and rules.
    
    Supports:
    - Quantities (500 units, 1000 pieces)
    - Order numbers (PO-12345, #ABC123)
    - Prices ($450.00, 500 dollars)
    - Dates (next week, Jan 15, 2024-01-15)
    - Emails (user@domain.com)
    - Products (from catalog)
    - Companies (Acme Inc, XYZ Corp)
    """
    
    def __init__(self):
        # Product catalog - expand with your actual products
        self.products = {
            "servo motor": ["servo", "servo motor", "servomotor", "industrial servo", "servo motors", "servos", "motor", "motors"],
            "fiber optic cable": ["fiber", "fiber optic", "optical cable", "fibre optic", "fiber cable", "fiber optic cables", "fiber cables", "cable", "cables"],
            "actuator": ["actuator", "actuators", "heavy duty actuator", "linear actuator", "pneumatic actuator"],
            "controller": ["controller", "controllers", "plc", "plcs", "programmable controller", "logic controller"],
            "sensor": ["sensor", "sensors", "proximity sensor", "temperature sensor", "pressure sensor"],
            "power supply": ["power supply", "power supplies", "psu", "power unit"],
            "relay": ["relay", "relays", "solid state relay", "ssr"],
            "conveyor": ["conveyor", "conveyors", "conveyor belt", "belt system"],
            "pump": ["pump", "pumps", "hydraulic pump", "vacuum pump"],
            "valve": ["valve", "valves", "solenoid valve", "control valve"],
            "optics": ["optics", "optical components", "lens", "lenses", "mirror", "mirrors", "prism", "prisms"],
            "pneumatic cylinder": ["pneumatic cylinder", "cylinder", "air cylinder"],
            "hydraulic cylinder": ["hydraulic cylinder", "hydraulic ram"],
            "gearbox": ["gearbox", "gear box", "reducer", "gear reducer"],
            "industrial robot": ["industrial robot", "robot arm", "robot", "robotic arm"],
            "bearing": ["bearing", "bearings", "ball bearing", "roller bearing"],
            "stepper motor": ["stepper motor", "stepper", "stepping motor"],
            "3d printer": ["3d printer", "3d printing", "additive manufacturing"],
            "fastener": ["fastener", "fasteners", "screw", "bolt", "nut", "washer", "nuts and bolts"],
            "human machine interface": ["human machine interface", "hmi", "panel pc", "touch panel"],
            "wiring": ["wiring", "wire", "electrical wire", "hook up wire"],
            "resistor": ["resistor", "resistors"],
            "soldering station": ["soldering station", "soldering iron", "solder"],
            "oscilloscope": ["oscilloscope", "scope", "o-scope"],
            "multimeter": ["multimeter", "meter", "multi meter"],
            "capacitor": ["capacitor", "cap"],
            "diode": ["diode", "led", "zener"],
            "transistor": ["transistor", "mosfet", "bjt"],
            "microcontroller": ["microcontroller", "mcu", "arduino", "esp32", "stm32"],
            "development board": ["development board", "dev board", "eval board"],
            "led": ["led", "light emitting diode"],
            "lcd screen": ["lcd screen", "lcd", "display", "monitor", "screen"],
            "switch": ["switch", "switches", "toggle switch", "push button"],
            "connector": ["connector", "plug", "socket", "jack"],
            "terminal block": ["terminal block", "terminal strip"],
            "fuse": ["fuse", "circuit protection"],
            "circuit breaker": ["circuit breaker", "breaker", "mcb"],
            "contactor": ["contactor", "starter"],
            "transformer": ["transformer", "power transformer"],
            "inverter": ["inverter", "vfd", "variable frequency drive"],
            "battery": ["battery", "batteries", "cell", "li-ion", "lithium"],
            "solar panel": ["solar panel", "pv panel", "photovoltaic"],
            "wind turbine": ["wind turbine", "turbine"],
            "cable tie": ["cable tie", "zip tie", "monitor"],
            "heat shrink tubing": ["heat shrink tubing", "heat shrink", "shrink tube"],
            "enclosure": ["enclosure", "box", "cabinet", "housing"],
            "fan": ["fan", "cooling fan"],
            "heatsink": ["heatsink", "heat sink"],
            "thermal paste": ["thermal paste", "thermal compound", "grease"],
            "screw": ["screw", "screws"],
            "nut": ["nut", "nuts"],
            "bolt": ["bolt", "bolts"],
            # v09 Fix: Added 'seal' to prevent OOS false positives on "weather resistance of seals"
            "seal": ["seal", "seals", "sealing", "gasket", "o-ring", "washers"]
        }
        
        # Regex patterns for different entity types
        self.patterns = {
            "quantity": [
                # "500 units", "1,000 pieces", "50 pcs", "20k pieces"
                (r'(\d{1,7}(?:[.,]\d{1,3})*[kK]?)\s*(?:units?|pcs?|pieces?|items?|ea)', 0.95),
                # "order 500", "need 1000", "want 200", "buy 5k"
                (r'(?:order|buy|need|want|require|purchase)\s+(\d{1,7}(?:[.,]\d{1,3})*[kK]?)', 0.85),
                # "500 of them", "1000 of those"
                (r'(\d{1,7}(?:,\d{3})*)\s*(?:of\s+them|of\s+those|of\s+these)', 0.80),
                # "quantity: 500", "qty 500"
                (r'(?:quantity|qty)[:\s]+(\d{1,7}(?:,\d{3})*)', 0.95),
                # standalone number in context (lower confidence) - skipping 'k' here to avoid false positives like "talk"
                (r'\b(\d{3,6})\b(?!\s*(?:days?|weeks?|hours?|minutes?|\$|dollars?|%|percent))', 0.60),
            ],
            "order_number": [
                # "PO-12345", "PO#12345", "po 12345"
                (r'(?:PO|po|P\.O\.)[#\-\s]?(\d{4,10})', 0.95),
                # "order number 12345", "order #ABC123" - exclude REQ/RFQ
                (r'(?:order\s+(?:number|#|no\.?)|order\s+id)[:\s]*((?!REQ|RFQ)[A-Z0-9\-]{4,15})', 0.90),
                # "#ABC12345" standalone - exclude REQ/RFQ
                (r'#((?!REQ|RFQ)[A-Z]{2,4}\d{4,10})', 0.85),
                # "tracking ABC123456"
                (r'(?:tracking|shipment)[:\s#]*([A-Z0-9]{8,20})', 0.85),
            ],
            "rfq_id": [
                # "REQ-12345", "REQ-9876", "REQ 12345", "#REQ-999"
                (r'(?:#)?(REQ[-\s]?\d{3,10})', 0.95),
                (r'(?:#)?(RFQ[-\s]?\d{3,10})', 0.90),
            ],
            "price": [
                # "$450.00", "$ 1,000"
                (r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 0.95),
                # "450 dollars", "1000 usd"
                (r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:dollars?|usd|USD)', 0.90),
                # "budget 5000", "price 450"
                (r'(?:budget|price|cost|spend)[:\s]*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 0.85),
                # "around $500", "about 1000"
                (r'(?:around|about|approximately|~)\s*\$?(\d{1,3}(?:,\d{3})*)', 0.75),
            ],
            "date": [
                # "01/15/2024", "2024-01-15" - strict boundaries
                (r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b', 0.95),
                (r'\b(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})\b', 0.95),
                # "January 15", "Jan 15, 2024"
                (r'\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)\b', 0.90),
                # "next week", "next month", "next monday"
                (r'\b(next\s+(?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b', 0.85),
                # "in 5 days", "within 2 weeks"
                (r'\b((?:in|within)\s+\d+\s+(?:days?|weeks?|months?))\b', 0.85),
                # "by end of month", "by friday"
                (r'\b(by\s+(?:end\s+of\s+)?(?:week|month|(?:mon|tues|wednes|thurs|fri|satur|sun)day))\b', 0.80),
            ],
            "email": [
                (r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 0.98),
            ],
            "phone": [
                # US format: (123) 456-7890, 123-456-7890, 1234567890
                (r'(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', 0.90),
            ],
            "company": [
                # "from Acme Inc", "at XYZ Corp" - tightened to avoid "is the lead time"
                # Requires Capitalized words (2+ chars) and optional specific suffixes or context
                # Added \b to triggers and removed "for" to reduce noise
                (r'(?:\bfrom\b|\bat\b|\bcompany(?:\s+name)?[:\s]+)\s*([A-Z][a-zA-Z0-9\s&\-\.]{2,}?(?:\s+(?:Inc|LLC|Ltd|Corp|Co|Company|Industries|Manufacturing|Solutions|Systems))?)\s*(?:[,\.]|$)', 0.75),
            ],
            "percentage": [
                # "15%", "20 percent"
                (r'(\d{1,3}(?:\.\d{1,2})?)\s*(?:%|percent)', 0.95),
            ]
        }
    
    def extract_all(self, text: str) -> Dict[str, List[Entity]]:
        """
        Extract all entities from text.
        
        Args:
            text: User input text
            
        Returns:
            Dict mapping entity types to lists of extracted entities
        """
        entities = {}
        
        # Extract pattern-based entities
        for entity_type, patterns in self.patterns.items():
            matches = self._extract_pattern(text, entity_type, patterns)
            if matches:
                entities[entity_type] = matches
        
        # Extract product entities (handled separately due to fuzzy matching)
        product_matches = self._extract_products(text)
        
        # Add fuzzy matches
        fuzzy_matches = self._extract_products_fuzzy(text)
        if fuzzy_matches:
            product_matches.extend(fuzzy_matches)
            # Re-deduplicate to prefer exact matches (higher confidence) over fuzzy ones
            product_matches = self._deduplicate_entities(product_matches)
            
        if product_matches:
            entities["product"] = product_matches
            
        # Resolve overlaps across all entities (e.g. Product vs Company)
        # Flatten list
        all_list = []
        for matches in entities.values():
            all_list.extend(matches)
            
        resolved = self._resolve_overlaps(all_list)
        
        # Re-group by type
        final_entities = {}
        for entity in resolved:
            if entity.type not in final_entities:
                final_entities[entity.type] = []
            final_entities[entity.type].append(entity)
            
        return final_entities
    
    def extract_for_intent(self, text: str, intent: str) -> Dict[str, Entity]:
        """
        Extract entities relevant to a specific intent.
        Returns single best entity for each type.
        
        Args:
            text: User input text
            intent: Detected intent
            
        Returns:
            Dict mapping entity type to single best Entity
        """
        all_entities = self.extract_all(text)
        
        # Define which entities are relevant for each intent
        intent_entity_map = {
            "INFO_MOQ": ["product", "quantity"],
            "INFO_PRICE": ["product", "quantity", "price"],
            "INFO_BULK": ["product", "quantity", "price", "percentage"],
            "INFO_TRACK": ["order_number", "rfq_id"],
            "INFO_SHIPPING": ["product", "quantity", "date"],
            "INFO_LEADTIME": ["product", "quantity", "date"],
            "INFO_SAMPLE": ["product", "quantity", "email"],
            "INFO_RETURN": ["order_number", "product"],
            "NAV_RFQ": ["product", "quantity", "company", "email", "price", "rfq_id"],
            "HELP": ["product", "order_number"],
            "INFO_RFQ_STATUS": ["rfq_id", "date"],
        }
        
        relevant_types = intent_entity_map.get(intent, list(self.patterns.keys()) + ["product"])
        result = {}
        
        for entity_type in relevant_types:
            if entity_type in all_entities and all_entities[entity_type]:
                # Take highest confidence match
                best = max(all_entities[entity_type], key=lambda e: e.confidence)
                result[entity_type] = best
        
        return result
    
    def _extract_pattern(self, text: str, entity_type: str, 
                         patterns: List[Tuple[str, float]]) -> List[Entity]:
        """Extract entities matching given patterns."""
        entities = []
        
        for pattern, base_confidence in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Get the captured group (first group if exists, else full match)
                value = match.group(1) if match.lastindex else match.group(0)
                
                entities.append(Entity(
                    type=entity_type,
                    value=self._normalize_value(entity_type, value),
                    original_text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=base_confidence
                ))
        
        # Deduplicate, keeping highest confidence
        return self._deduplicate_entities(entities)
    
    def _extract_products(self, text: str) -> List[Entity]:
        """Extract product mentions from text using catalog matching."""
        entities = []
        text_lower = text.lower()
        
        for product_name, variations in self.products.items():
            for variation in sorted(variations, key=len, reverse=True):  # Longer matches first
                # Find the variation in text
                start_search = 0
                while True:
                    idx = text_lower.find(variation.lower(), start_search)
                    if idx == -1:
                        break
                        
                    # Check start boundary
                    before_ok = idx == 0 or not text_lower[idx-1].isalnum()
                    
                    # Check end boundary (allow plural 's' or 'es')
                    after_idx = idx + len(variation)
                    
                    # Check for plural suffix
                    plural_suffix = ""
                    if after_idx < len(text_lower) and text_lower[after_idx] == 's':
                        plural_suffix = "s"
                    elif after_idx + 1 < len(text_lower) and text_lower[after_idx:after_idx+2] == 'es':
                        plural_suffix = "es"
                        
                    end_idx = after_idx + len(plural_suffix)
                    after_ok = end_idx >= len(text_lower) or not text_lower[end_idx].isalnum()
                    
                    if before_ok and after_ok:
                        # Confidence based on match type
                        if variation.lower() == product_name.lower():
                            confidence = 0.95  # Exact canonical name
                        elif len(variation) > 5:
                            confidence = 0.85  # Long variation
                        else:
                            confidence = 0.70  # Short variation (might be ambiguous)
                        
                        entities.append(Entity(
                            type="product",
                            value=product_name,  # Normalized canonical name
                            original_text=text[idx:end_idx],
                            start=idx,
                            end=end_idx,
                            confidence=confidence
                        ))
                        # Don't break here, find all instances? 
                        # Actually for now let's just break for this variation to avoid overlaps, 
                        # or advance search. 
                        # But simpler logic: if we found a match for this variation, add it.
                    
                    start_search = idx + 1
                    
        return self._deduplicate_entities(entities)
    
    def _normalize_value(self, entity_type: str, value: str) -> str:
        """Normalize extracted values to standard format."""
        value = value.strip()
        
        if entity_type == "quantity":
            # Remove commas, handle 'k' suffix
            clean = value.lower().replace(",", "").replace(" ", "")
            multiplier = 1
            if clean.endswith("k"):
                multiplier = 1000
                clean = clean[:-1]
            
            try:
                # Handle float inputs like 1.5k -> 1500
                val = float(clean)
                return str(int(val * multiplier))
            except ValueError:
                return value
                
        elif entity_type == "price":
            # Remove $ and commas, keep decimals
            clean = value.replace("$", "").replace(",", "").strip()
            return clean
            
        elif entity_type == "order_number":
            # Uppercase, remove extra spaces
            return value.upper().replace(" ", "")
            
        elif entity_type == "email":
            return value.lower()
            
        elif entity_type == "phone":
            # Keep only digits and leading +
            digits = re.sub(r'[^\d+]', '', value)
            return digits
            
        elif entity_type == "percentage":
            # Just the number
            return value.replace("%", "").replace("percent", "").strip()

        elif entity_type == "rfq_id":
            # Uppercase, remove spaces, ensure standard dash
            norm = value.upper().replace(" ", "")
            if "REQ" in norm and "-" not in norm:
                norm = norm.replace("REQ", "REQ-")
            return norm
        
        return value
            
    def _resolve_overlaps(self, entities: List[Entity]) -> List[Entity]:
        """Resolve overlapping entities by keeping the longest/highest confidence match."""
        if not entities:
            return []
            
        # Sort by start position, then by length (descending)
        sorted_entities = sorted(entities, key=lambda e: (e.start, -(e.end - e.start)))
        
        result = []
        current_end = -1
        
        for entity in sorted_entities:
            # If this entity starts after the previous one ended, keep it
            if entity.start >= current_end:
                result.append(entity)
                current_end = entity.end
            else:
                # Overlap detected. 
                # Since we sorted by length descending for same start, the first one seen is optimal?
                # Not strictly true for partial overlaps like [A [B] C].
                # But simple greedy strategy works for most NER.
                
                # Check if we should replace the last one (e.g. if this one is significantly better confidence)
                # For now, just simplistic "longest non-overlapping wins" (First-Fit)
                pass
                
        # Better approach: Filter products specifically for containment
        # If "cylinder" (start 10, end 18) and "hydraulic cylinder" (start 0, end 18)
        # We want hydraulic cylinder.
        
        # Re-implementation: Check all pairs
        to_remove = set()
        for i, e1 in enumerate(entities):
            for j, e2 in enumerate(entities):
                if i == j: continue
                if j in to_remove: continue
                
                # Check overlap
                if max(e1.start, e2.start) < min(e1.end, e2.end):
                    # Overlap exists. Favor longer string, then higher confidence.
                    len1 = e1.end - e1.start
                    len2 = e2.end - e2.start
                    
                    if len1 > len2:
                        to_remove.add(j)
                    elif len2 > len1:
                        to_remove.add(i)
                    elif e1.confidence > e2.confidence:
                        to_remove.add(j)
                    else:
                        to_remove.add(i)
                        
        return [e for i, e in enumerate(entities) if i not in to_remove]

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities, keeping highest confidence."""
        seen_values = {}
        
        for entity in entities:
            key = (entity.type, entity.value.lower())
            if key not in seen_values or entity.confidence > seen_values[key].confidence:
                seen_values[key] = entity
        
        return list(seen_values.values())
    
    def add_product(self, canonical_name: str, variations: List[str]):
        """Add a new product to the catalog."""
        self.products[canonical_name.lower()] = [v.lower() for v in variations]
    
    def add_products_from_list(self, products: List[Dict]):
        """
        Add products from a list of dicts.
        
        Args:
            products: List of {"name": "...", "aliases": ["...", "..."]}
        """
        for product in products:
            name = product.get("name", "").lower()
            aliases = [a.lower() for a in product.get("aliases", [])]
            if name:
                self.products[name] = [name] + aliases

    def _extract_products_fuzzy(self, text: str) -> List[Entity]:
        """
        Extract product mentions using fuzzy matching (e.g. 'snesor' -> 'sensor').
        Computes Levenshtein-based similarity on n-grams.
        """
        entities = []
        text_lower = text.lower()
        words = text_lower.split()
        
        # Helper to get character offset from word index
        # This is approximate because split() loses whitespace info
        # But we can find the substring in the original text
        
        # Better: use regex to find words and their spans
        word_spans = []
        for match in re.finditer(r'\b\w+\b', text_lower):
            word_spans.append((match.group(0), match.start(), match.end()))
            
        if not word_spans:
            return []

        # Common words to skip for fuzzy matching (prevent "order"->"solder", "use"->"fuse")
        STOP_WORDS = {
            "order", "query", "price", "unit", "use", "which", "what", "where", 
            "how", "when", "need", "want", "find", "show", "list", "minimum",
            "maximum", "quantity", "quote", "buy", "purchase", "get", "have",
            "lead", "time", "date"
        }

        # Flatten all product variations for lookup
        all_variations = []
        for product_name, variations in self.products.items():
            for v in variations:
                all_variations.append((v, product_name))
        
        # Check n-grams (up to 3 words)
        for n in range(1, 4):
            for i in range(len(word_spans) - n + 1):
                # Construct n-gram from words
                ngram_words = [ws[0] for ws in word_spans[i:i+n]]
                ngram_text = " ".join(ngram_words)
                
                # Skip if n-gram is a stop word or too short
                if ngram_text.lower() in STOP_WORDS:
                    continue
                    
                # Skip very short words to avoid "use"->"fuse" or "fan"->"fna" noise
                # Exact matches for short words are handled by _extract_products
                if len(ngram_text) < 4:
                    continue
                
                # Get span coverage
                start_idx = word_spans[i][1]
                end_idx = word_spans[i+n-1][2]
                
                # Compare with all variations
                # Optimization: checks length diff first
                for variation, canonical_name in all_variations:
                    # Skip if length difference is too big
                    if abs(len(ngram_text) - len(variation)) > 3:
                        continue
                        
                    # Calculate similarity ratio
                    # (2 * M) / T   where M=matches, T=total length
                    ratio = difflib.SequenceMatcher(None, ngram_text, variation).ratio()
                    
                    # Threshold: 0.80 (Strict enough to reject 'order'->'solder' @ 0.72)
                    # But allows 'snesor'->'sensor' @ 0.83, 'batreies'->'batteries' @ 0.82
                    if ratio >= 0.80: 
                        entities.append(Entity(
                            type="product",
                            value=canonical_name,
                            original_text=text[start_idx:end_idx],
                            start=start_idx,
                            end=end_idx,
                            confidence=0.6 + (ratio * 0.3) # Confidence scaled by similarity
                        ))
        
        return entities


# Global instance
entity_extractor = EntityExtractor()


# Example usage and tests
if __name__ == "__main__":
    test_cases = [
        "I want to order 500 servo motors",
        "What's the price for 1,000 units of fiber optic cable?",
        "Where is my order PO-12345?",
        "Can I get a quote for actuators? My email is john@company.com",
        "Need delivery by next week for 200 sensors",
        "Budget is around $5000 for 100 controllers",
        "I'm from Acme Industries, need pricing on pumps",
        "Tracking number ABC123456789",
        "Can you do 15% discount on 500 units?",
        "Do you have seals for pneumatic cylinders?"
    ]
    
    print("Entity Extraction Tests")
    print("=" * 60)
    
    for text in test_cases:
        print(f"\nInput: {text}")
        entities = entity_extractor.extract_all(text)
        
        if entities:
            for etype, elist in entities.items():
                for e in elist:
                    print(f"  → {etype}: '{e.value}' (conf: {e.confidence:.2f}, text: '{e.original_text}')")
        else:
            print("  → No entities found")