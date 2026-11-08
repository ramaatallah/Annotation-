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
    "SPECIES": 96,
    "PHENOMENON": 95,
    "CHEMICAL": 94,
    "ANATOMY": 93,
    "DISEASE": 92,
    "MEDICAL_TERM": 90,
    "TECHNOLOGY": 88,
    "WORK": 86,
    "EVENT": 84,
    "LAW_RULE": 82,
    "ASTRONOMY": 80,
    "FIELD": 78,
    "PERIOD": 76,
    "ARTIFACT": 74,
    "CONCEPT": 72,
    "PERSON": 70,
    "LOCATION": 65,
    "ORGANIZATION": 60,
    "DATE": 50,
    "OTHER": 30,
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
        # 1. Sanitize and accept all LLM entities as primary ground truth
        clean_llm: List[Dict[str, Any]] = []
        for ent in llm_entities:
            clean = self._sanitize_entity(original_text, ent)
            if clean:
                clean["source"] = "Groq"
                clean_llm.append(clean)

        # 2. Add BERT entities ONLY as gap-fillers for unmentioned entities, NEVER overriding or corrupting LLM entities
        clean_bert: List[Dict[str, Any]] = []
        for ent in bert_entities:
            clean = self._sanitize_entity(original_text, ent)
            if not clean:
                continue
            clean["source"] = "BERT"
            # Discard BERT entity if it overlaps in position or text with any high-confidence LLM entity
            overlaps_llm = any(
                (clean["start_char"] < g["end_char"] and clean["end_char"] > g["start_char"]) or
                (clean["text"] == g["text"]) or
                (clean["text"] in g["text"] and len(clean["text"]) >= 3) or
                (g["text"] in clean["text"] and len(g["text"]) >= 3)
                for g in clean_llm
            )
            if not overlaps_llm:
                clean_bert.append(clean)

        all_candidates = clean_llm + clean_bert
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
                if candidate.get("source") == "Groq":
                    last["category"] = candidate["category"]
                    last["label_ar"] = candidate.get("label_ar")
                elif last.get("source") != "Groq" and CATEGORY_PRIORITY.get(candidate["category"], 0) > CATEGORY_PRIORITY.get(last["category"], 0):
                    last["category"] = candidate["category"]
                    last["label_ar"] = candidate.get("label_ar")
                # Boost confidence for agreement
                last["confidence"] = min(1.0, round(max(last["confidence"], candidate["confidence"]) + 0.05, 4))
                last["source"] = "Hybrid"
                continue

            # Case B: Overlap detected
            if candidate["start_char"] < last["end_char"]:
                # Groq LLM has superior semantic boundaries and context over legacy BERT
                if candidate.get("source") == "Groq" and last.get("source") == "BERT":
                    merged[-1] = candidate
                    continue
                if last.get("source") == "Groq" and candidate.get("source") == "BERT":
                    continue

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

        # Deduplicate identical entity texts to keep cards and annotations clean
        unique_entities: List[Dict[str, Any]] = []
        seen_texts = set()
        for ent in merged:
            norm_text = ent["text"].strip()
            if norm_text not in seen_texts:
                seen_texts.add(norm_text)
                unique_entities.append(ent)
            else:
                # Upgrade category if a higher-priority one was found
                for u in unique_entities:
                    if u["text"] == norm_text and CATEGORY_PRIORITY.get(ent["category"], 0) > CATEGORY_PRIORITY.get(u["category"], 0):
                        u["category"] = ent["category"]
                        u["label_ar"] = ent.get("label_ar") or u.get("label_ar")
                        break
        merged = unique_entities

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

        # Universal Arabic Particle & Preposition Normalization:
        # Entities are substantive noun phrases; they must never start or end with grammatical particles
        ARABIC_PARTICLES = {
            "عن", "في", "من", "على", "إلى", "مع", "لـ", "بـ", "كـ", "أو", "و", "فـ", "ثم",
            "حتى", "منذ", "بين", "نحو", "لدى", "ضد", "حول", "دون", "غير", "سوى", "إذ", "إذا",
            "أن", "إن", "لكن", "لعل", "ليت", "قد", "لقد", "حيث", "بما", "كما", "لما", "كي", "لكي",
            "ال", "الـ", "الإ", "وال", "بال", "كال", "لل"
        }

        raw_words = text_val.split()
        if not raw_words:
            return None

        # Strip trailing prepositions/particles (e.g. 'لنحاس عن' -> 'لنحاس')
        while raw_words and raw_words[-1] in ARABIC_PARTICLES:
            raw_words.pop()

        # Strip leading prepositions/particles (e.g. 'في روما' -> 'روما')
        while raw_words and raw_words[0] in ARABIC_PARTICLES:
            raw_words.pop(0)

        if not raw_words:
            return None

        text_val = " ".join(raw_words).strip()
        if len(text_val) < 2:
            return None

        # Universal Verb & Negation Rejection:
        # Rejects any entity starting with Arabic negation or jussive particles (e.g. 'لم تحصل', 'لن يكون')
        NEGATION_VERB_PREFIXES = ("لم ", "لن ", "لا ", "ما ", "ليس ", "ليست ", "كي ", "لكي ", "حتى ", "قد ")
        if text_val.startswith(NEGATION_VERB_PREFIXES):
            return None

        # Universal Standalone Quantifier / Determiner Rejection:
        STANDALONE_QUANTIFIERS = {"بضع", "بضعة", "عدة", "بعض", "كثير", "قليل", "جميع", "كل", "أحد", "إحدى"}
        if text_val in STANDALONE_QUANTIFIERS:
            return None

        # Universal Proclitic Normalization:
        # Normalize attached prepositions (لـ / بـ / كـ) on defined nouns (e.g. 'للنحاس' -> 'النحاس')
        if len(text_val) > 4:
            if text_val.startswith("لل") and not text_val.startswith(("الله", "اللهم", "الليل", "الليث")):
                text_val = "ال" + text_val[2:]
            elif text_val.startswith(("بال", "فال", "كال", "وال")):
                text_val = "ال" + text_val[3:]

        # Recalculate true span in original text
        found_pos = original_text.find(text_val)
        if found_pos != -1:
            start = found_pos
            end = start + len(text_val)

        category = ent.get("category", "CONCEPT").upper()

        # Universal Morphological Rule: Non-person semantic anchors can never be categorized as PERSON
        PERIOD_MARKERS = {"عصر", "حقبة", "تاريخ", "فترة", "قرن", "حضارة", "سنة", "ألفية", "إمبراطورية"}
        LOCATION_MARKERS = {"مدينة", "جزيرة", "دولة", "مملكة", "عاصمة", "جبل", "بحر", "نهر", "وادي", "خليج", "قارة", "روما"}
        if category == "PERSON":
            if any(pm in text_val for pm in PERIOD_MARKERS):
                category = "PERIOD"
            elif any(lm in text_val for lm in LOCATION_MARKERS):
                category = "LOCATION"

        clean_ent = {
            "text": text_val,
            "category": category,
            "label_ar": ent.get("label_ar"),
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
