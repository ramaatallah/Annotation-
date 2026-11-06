"""Entity Fusion and Validation Engine.

Combines entities extracted from BERT and Groq LLM:
1. Resolves overlapping and nested spans (longest and highest priority win).
2. Merges duplicate entities with confidence score reinforcement.
3. Attaches high-precision trilateral roots to all words within each entity.
4. Validates boundary offsets against original text.
"""

import logging
from typing import List, Dict, Any
from app.services.nlp.root_engine import root_engine

logger = logging.getLogger(__name__)

# Priority order for entity categorization (more specific types take precedence)
CATEGORY_PRIORITY = {
    "UNIVERSITY": 100,
    "DISEASE": 95,
    "MEDICAL_TERM": 90,
    "TECHNOLOGY": 85,
    "FIELD": 80,
    "CONCEPT": 75,
    "PERSON": 70,
    "LOCATION": 65,
    "ORGANIZATION": 60,
    "DATE": 50,
    "MISC": 10,
}


class EntityFusionEngine:
    """Intelligently merges BERT and LLM entity spans and binds morphological roots."""

    def merge_entities(
        self,
        original_text: str,
        bert_entities: List[Dict[str, Any]],
        llm_entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Merges two entity streams into a cohesive, non-overlapping entity list."""
        all_candidates = []

        # Tag and validate BERT candidates
        for ent in bert_entities:
            clean_ent = self._sanitize_entity(original_text, ent)
            if clean_ent:
                all_candidates.append(clean_ent)

        # Tag and validate LLM candidates
        for ent in llm_entities:
            clean_ent = self._sanitize_entity(original_text, ent)
            if clean_ent:
                all_candidates.append(clean_ent)

        if not all_candidates:
            return []

        # Sort primarily by starting position, secondarily by length descending (longest span first)
        all_candidates.sort(
            key=lambda x: (x["start_char"], -(x["end_char"] - x["start_char"]), -CATEGORY_PRIORITY.get(x["category"], 0))
        )

        merged: List[Dict[str, Any]] = []

        for candidate in all_candidates:
            if not merged:
                merged.append(candidate)
                continue

            last = merged[-1]

            # Case A: Exact match in span or text -> Merge & boost confidence
            if candidate["start_char"] == last["start_char"] and candidate["end_char"] == last["end_char"]:
                # Prefer more specific category
                if CATEGORY_PRIORITY.get(candidate["category"], 0) > CATEGORY_PRIORITY.get(last["category"], 0):
                    last["category"] = candidate["category"]
                # Boost confidence for agreement
                last["confidence"] = min(1.0, round(max(last["confidence"], candidate["confidence"]) + 0.05, 4))
                last["source"] = "Hybrid"
                continue

            # Case B: Overlap detected
            if candidate["start_char"] < last["end_char"]:
                cand_len = candidate["end_char"] - candidate["start_char"]
                last_len = last["end_char"] - last["start_char"]

                # If candidate is significantly longer (e.g., "جامعة النجاح الوطنية" vs "جامعة النجاح")
                if cand_len > last_len:
                    merged[-1] = candidate
                    merged[-1]["confidence"] = min(1.0, round(candidate["confidence"] + 0.03, 4))
                elif CATEGORY_PRIORITY.get(candidate["category"], 0) > CATEGORY_PRIORITY.get(last["category"], 0) + 20:
                    # Specific concept over generic organization
                    merged[-1] = candidate
                # Otherwise, keep existing earlier/longer entity
                continue

            # Case C: No overlap -> Append cleanly
            merged.append(candidate)

        # Attach trilateral roots to each constituent word in the entity
        for entity in merged:
            entity_text = entity["text"]
            roots_data = root_engine.extract_phrase_roots(entity_text)
            entity["roots"] = roots_data

        return merged

    def _sanitize_entity(self, original_text: str, ent: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures text bounds and indices are valid and match original text."""
        text_val = ent.get("text", "").strip()
        if not text_val:
            return None

        start = ent.get("start_char", 0)
        end = ent.get("end_char", start + len(text_val))

        # Boundary checks
        if start < 0 or start >= len(original_text):
            # Recalculate using find
            found_idx = original_text.find(text_val)
            if found_idx != -1:
                start = found_idx
                end = start + len(text_val)
            else:
                return None

        # Verify substring matches
        actual_sub = original_text[start:end]
        if actual_sub != text_val:
            # Minor index shift adjustment
            found_idx = original_text.find(text_val)
            if found_idx != -1:
                start = found_idx
                end = start + len(text_val)
            else:
                text_val = actual_sub.strip()

        category = ent.get("category", "CONCEPT").upper()

        return {
            "text": text_val,
            "category": category,
            "confidence": round(float(ent.get("confidence", 0.90)), 4),
            "source": ent.get("source", "Hybrid"),
            "start_char": start,
            "end_char": end,
        }


fusion_engine = EntityFusionEngine()
