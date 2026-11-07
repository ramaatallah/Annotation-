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
                # Sub-span containment check: if candidate is completely inside last (e.g. 'فلسطين' inside 'بنك فلسطين')
                if candidate["start_char"] >= last["start_char"] and candidate["end_char"] <= last["end_char"]:
                    continue

                # If candidate completely encompasses last (e.g. 'جامعة النجاح الوطنية' vs 'جامعة النجاح')
                if candidate["start_char"] <= last["start_char"] and candidate["end_char"] >= last["end_char"]:
                    merged[-1] = candidate
                    merged[-1]["confidence"] = min(1.0, round(candidate["confidence"] + 0.03, 4))
                    continue

                cand_len = candidate["end_char"] - candidate["start_char"]
                last_len = last["end_char"] - last["start_char"]

                # If candidate is significantly longer, prefer the longer unbroken entity
                if cand_len > last_len:
                    merged[-1] = candidate
                    merged[-1]["confidence"] = min(1.0, round(candidate["confidence"] + 0.03, 4))
                elif CATEGORY_PRIORITY.get(candidate["category"], 0) > CATEGORY_PRIORITY.get(last["category"], 0) + 20:
                    merged[-1] = candidate
                continue

            # Case C: No overlap -> Append cleanly
            merged.append(candidate)

        # Post-pass: Stitch adjacent fragments (e.g., "محمود" + "درويش", "رام" + "الله")
        merged = self._stitch_adjacent_entities(original_text, merged)

        # Attach trilateral roots to each constituent word in the entity
        # Only include resolved roots (word + root), skip unresolved to reduce noise
        for entity in merged:
            entity_text = entity["text"]
            roots_data = root_engine.extract_phrase_roots(entity_text)
            entity["roots"] = [
                {"word": r["word"], "root": r["root"]}
                for r in roots_data
                if r.get("root") and r.get("status") == "analyzed"
            ]

        return merged

    def _stitch_adjacent_entities(
        self, original_text: str, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Stitches adjacent entities that belong to the same multi-word entity (e.g. compound names)."""
        if len(entities) < 2:
            return entities

        stitched: List[Dict[str, Any]] = []
        for ent in entities:
            if not stitched:
                stitched.append(ent)
                continue

            prev = stitched[-1]
            gap = original_text[prev["end_char"]:ent["start_char"]]

            # Sub-token split without space (e.g. HuggingFace token cut: "والقد" + "س" -> "والقدس")
            if gap == "" and prev["category"] == ent["category"]:
                prev["text"] = original_text[prev["start_char"]:ent["end_char"]]
                prev["end_char"] = ent["end_char"]
                prev["confidence"] = max(prev["confidence"], ent["confidence"])
                continue

            # Check if next word begins with coordinating conjunction 'و' -> separate entity!
            if ent["text"].startswith("و") and len(ent["text"]) > 2:
                stitched.append(ent)
                continue

            should_stitch = False
            if gap in (" ", "-"):
                # Compound personal names (e.g. "محمود" + "درويش")
                if prev["category"] == "PERSON" and ent["category"] == "PERSON":
                    should_stitch = True
                # Compound educational / organization terms
                elif {prev["category"], ent["category"]} <= {"UNIVERSITY", "ORGANIZATION"}:
                    should_stitch = True
                # Compound locations starting with known prefix
                elif prev["category"] == "LOCATION" and ent["category"] == "LOCATION":
                    first_word = prev["text"].split()[-1]
                    if first_word in {"رام", "بيت", "دير", "كفر", "عين", "تل", "شرم", "بئر", "أبو", "أم", "وادي", "رأس", "بور", "سان", "نيو"}:
                        should_stitch = True

            if should_stitch:
                combined_text = original_text[prev["start_char"]:ent["end_char"]].strip()
                prev["text"] = combined_text
                prev["end_char"] = ent["end_char"]
                prev["confidence"] = max(prev["confidence"], ent["confidence"])
                if prev["category"] != ent["category"]:
                    if CATEGORY_PRIORITY.get(ent["category"], 0) > CATEGORY_PRIORITY.get(prev["category"], 0):
                        prev["category"] = ent["category"]
            else:
                stitched.append(ent)

        return stitched

    def _sanitize_entity(self, original_text: str, ent: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures text bounds and indices are valid and match original text."""
        text_val = ent.get("text", "").strip(" ،,.:؟!؛\t\n")
        if not text_val or len(text_val) < 2:
            return None

        # Filter out common interrogative/stop phrases that are not true entities
        STOP_PHRASES = {"ما هي", "ما هو", "ماذا", "لماذا", "كيف", "متى", "أين", "هل", "من هو", "من هي", "عن ماذا", "فيما يلي"}
        if text_val in STOP_PHRASES:
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

        clean_ent = {
            "text": text_val,
            "category": category,
            "confidence": round(float(ent.get("confidence", 0.90)), 4),
            "source": ent.get("source", "Hybrid"),
            "start_char": start,
            "end_char": end,
        }

        candidate = self._clean_and_expand_candidate(original_text, clean_ent)
        if not candidate:
            return None

        cleaned_text = candidate["text"].strip(" ،,.:؟!؛\t\n")
        STOP_WORDS = {
            "ما هي", "ما هو", "ماذا", "لماذا", "كيف", "متى", "أين", "هل", "من هو", "من هي",
            "عن ماذا", "فيما يلي", "بشكل عام", "على سبيل المثال", "إلى جانب ذلك", "التي", "الذي",
            "الذين", "اللواتي", "هذا", "هذه", "هؤلاء", "ذلك", "تلك", "هناك", "هنالك"
        }
        if cleaned_text in STOP_WORDS or len(cleaned_text) < 2:
            return None

        return candidate

    def _clean_and_expand_candidate(self, text: str, ent: Dict[str, Any]) -> Dict[str, Any]:
        """Cleans proclitics and expands compound named entities to avoid fragmented spans."""
        import re

        start = ent["start_char"]
        end = ent["end_char"]
        val = ent["text"]
        cat = ent["category"]

        # Strip leading 'و' or 'ف' conjunction if glued to entity
        if val.startswith(("و", "ف")) and len(val) > 3 and val not in {"واشنطن", "وادي", "ورقلة", "ويلز", "ولايات", "فلسطين", "فيينا"}:
            start += 1
            val = text[start:end]

        # Expand backward if preceded by compound name prefix (e.g. 'عبد الله', 'صلاح الدين', 'ابن سينا')
        before_text = text[:start].rstrip()
        for prefix in ["عبد", "ابن", "بن", "أبو", "ابو", "أم", "ام", "آل", "سيف", "نور", "صلاح", "علاء", "بهاء", "جمال"]:
            if before_text.endswith(prefix) and (len(before_text) == len(prefix) or before_text[-len(prefix) - 1] == " "):
                p_start = before_text.rfind(prefix)
                start = p_start
                val = text[start:end]
                break

        # Expand forward for compound organizations / universities (e.g. الوطنية, الأمريكية, الإسلامية)
        if cat in ("ORGANIZATION", "UNIVERSITY"):
            after_text = text[end:].lstrip()
            for suffix in ["الوطنية", "الإسلامية", "الأمريكية", "العربية", "الدولية", "المفتوحة", "التخصصي", "العالمية", "المتحدة"]:
                if after_text.startswith(suffix) and (len(after_text) == len(suffix) or after_text[len(suffix)] in " ،.؟!\n\t"):
                    end = text.find(suffix, end) + len(suffix)
                    val = text[start:end]
                    break

        # Expand forward for compound places (e.g. رام الله, بيت لحم, شرم الشيخ, كفر الشيخ)
        # ONLY expand if it's currently a single word!
        if cat == "LOCATION":
            words = val.split()
            if len(words) == 1 and words[0] in {"رام", "بيت", "دير", "كفر", "عين", "شرم", "بئر", "أبو", "أم", "وادي", "رأس", "بور"}:
                after_text = text[end:].lstrip()
                next_word_m = re.match(r"^([\u0600-\u06FF]+)", after_text)
                if next_word_m:
                    nw = next_word_m.group(1)
                    # Make sure the next word is not a conjunction like 'والقدس' or 'وعمان'
                    if not nw.startswith("و"):
                        end = text.find(nw, end) + len(nw)
                        val = text[start:end]

        ent["start_char"] = start
        ent["end_char"] = end
        ent["text"] = text[start:end].strip()
        return ent


fusion_engine = EntityFusionEngine()
