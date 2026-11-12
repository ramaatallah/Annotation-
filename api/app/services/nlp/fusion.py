"""Entity Fusion and Validation Engine.

Combines entities extracted from BERT and Groq LLM:
1. Resolves overlapping and nested spans (longest and highest priority win).
2. Merges duplicate entities with confidence score reinforcement.
3. Attaches high-precision trilateral roots to all words within each entity.
4. Validates boundary offsets against original text.
5. Snaps clipped or partial words to natural Arabic word boundaries.
"""

import re
import logging
from typing import List, Dict, Any
from app.services.nlp.root_engine import root_engine

logger = logging.getLogger(__name__)

# Priority order for entity categorization (more specific types take precedence)
CATEGORY_PRIORITY = {
    "UNIVERSITY": 100,
    "SPECIES": 96,
    "GEOLOGY": 95,
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
        cached_entities: List[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Merges cached, LLM, and BERT entity streams into a cohesive, non-overlapping entity list."""
        # 0. Sanitize cached entities as highest-fidelity verified knowledge
        clean_cached: List[Dict[str, Any]] = []
        if cached_entities:
            for ent in cached_entities:
                clean = self._sanitize_entity(original_text, ent)
                if clean:
                    clean["source"] = "KnowledgeCache"
                    clean["confidence"] = 0.99
                    clean_cached.append(clean)

        # 1. Sanitize and accept all LLM entities as primary ground truth
        clean_llm: List[Dict[str, Any]] = []
        for ent in llm_entities:
            clean = self._sanitize_entity(original_text, ent)
            if clean:
                clean["source"] = "Groq"
                clean_llm.append(clean)

        # 2. Add BERT entities ONLY as gap-fillers for unmentioned entities, NEVER overriding or corrupting LLM/Cache entities
        clean_bert: List[Dict[str, Any]] = []
        for ent in bert_entities:
            clean = self._sanitize_entity(original_text, ent)
            if not clean:
                continue
            clean["source"] = "BERT"
            # Discard BERT entity if it overlaps in position or text with any high-confidence LLM or Cache entity
            overlaps = any(
                (clean["start_char"] < g["end_char"] and clean["end_char"] > g["start_char"]) or
                (clean["text"] == g["text"]) or
                (clean["text"] in g["text"] and len(clean["text"]) >= 3) or
                (g["text"] in clean["text"] and len(g["text"]) >= 3)
                for g in (clean_cached + clean_llm)
            )
            if not overlaps:
                clean_bert.append(clean)

        all_candidates = clean_cached + clean_llm + clean_bert
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
                if candidate.get("source") == "KnowledgeCache":
                    last["category"] = candidate["category"]
                    last["label_ar"] = candidate.get("label_ar") or last.get("label_ar")
                    last["source"] = "KnowledgeCache"
                elif last.get("source") == "KnowledgeCache":
                    pass  # Keep verified KnowledgeCache intact
                elif candidate.get("source") == "Groq":
                    last["category"] = candidate["category"]
                    last["label_ar"] = candidate.get("label_ar")
                elif last.get("source") != "Groq" and CATEGORY_PRIORITY.get(candidate["category"], 0) > CATEGORY_PRIORITY.get(last["category"], 0):
                    last["category"] = candidate["category"]
                    last["label_ar"] = candidate.get("label_ar")
                # Boost confidence for agreement
                last["confidence"] = min(1.0, round(max(last["confidence"], candidate["confidence"]) + 0.05, 4))
                if last.get("source") != "KnowledgeCache":
                    last["source"] = "Hybrid"
                continue

            # Case B: Overlap detected
            if candidate["start_char"] < last["end_char"]:
                # KnowledgeCache has top precedence
                if candidate.get("source") == "KnowledgeCache":
                    merged[-1] = candidate
                    continue
                if last.get("source") == "KnowledgeCache":
                    continue

                # Groq LLM has superior semantic boundaries and context over legacy BERT
                if candidate.get("source") == "Groq" and last.get("source") == "BERT":
                    merged[-1] = candidate
                    continue
                if last.get("source") == "Groq" and candidate.get("source") == "BERT":
                    continue

                # Sub-span containment check
                if candidate["start_char"] >= last["start_char"] and candidate["end_char"] <= last["end_char"]:
                    continue

                # Encompassing span check
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

        # Post-pass: Stitch adjacent compound entities
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

            # Sub-token split without space
            if gap == "" and prev["category"] == ent["category"]:
                prev["text"] = original_text[prev["start_char"]:ent["end_char"]]
                prev["end_char"] = ent["end_char"]
                prev["confidence"] = max(prev["confidence"], ent["confidence"])
                continue

            # Separate entity if word begins with conjunction
            if ent["text"].startswith("و") and len(ent["text"]) > 2:
                stitched.append(ent)
                continue

            should_stitch = False
            if gap in (" ", "-"):
                # Compound personal names
                if prev["category"] == "PERSON" and ent["category"] == "PERSON":
                    should_stitch = True
                # Compound educational or organization terms
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

    @staticmethod
    def _snap_to_word_boundaries(text: str, start: int, end: int) -> tuple:
        """Expands start and end outward to natural Arabic word boundaries.
        Guarantees that no entity span starts or ends in the middle of a word.
        """
        if not text or start < 0 or end > len(text) or start >= end:
            return start, end, text[start:end] if text else ""

        # Characters considered part of an Arabic or alphanumeric word
        word_char_pattern = re.compile(r"[\u0600-\u06FFa-zA-Z0-9]")

        # Expand start backward if it cuts inside a word
        while start > 0 and word_char_pattern.match(text[start - 1]):
            start -= 1

        # Expand end forward if it cuts inside a word
        while end < len(text) and word_char_pattern.match(text[end]):
            end += 1

        val = text[start:end].strip(" ،,.:؟!؛\t\n\"'()[]{}«»")
        return start, end, val

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
            found_idx = original_text.find(text_val)
            if found_idx != -1:
                start = found_idx
                end = start + len(text_val)
            else:
                return None

        # Verify substring matches
        actual_sub = original_text[start:end]
        if actual_sub != text_val:
            found_idx = original_text.find(text_val)
            if found_idx != -1:
                start = found_idx
                end = start + len(text_val)
            else:
                text_val = actual_sub.strip()

        # Snap any clipped sub-word to its full natural bounds in original_text
        start, end, text_val = self._snap_to_word_boundaries(original_text, start, end)
        if not text_val or len(text_val) < 2:
            return None

        # Normalize particles and prepositions
        ARABIC_PARTICLES = {
            "عن", "في", "من", "على", "إلى", "مع", "لـ", "بـ", "كـ", "أو", "و", "فـ", "ثم",
            "حتى", "منذ", "بين", "نحو", "لدى", "ضد", "حول", "دون", "غير", "سوى", "إذ", "إذا",
            "أن", "إن", "لكن", "لعل", "ليت", "قد", "لقد", "حيث", "بما", "كما", "لما", "كي", "لكي",
            "ال", "الـ", "الإ", "وال", "بال", "كال", "لل"
        }

        raw_words = text_val.split()
        if not raw_words:
            return None

        # Strip trailing prepositions/particles
        while raw_words and raw_words[-1] in ARABIC_PARTICLES:
            raw_words.pop()

        # Strip leading prepositions/particles
        while raw_words and raw_words[0] in ARABIC_PARTICLES:
            raw_words.pop(0)

        # Strip common leading verbs if accidentally glued
        COMMON_VERB_PREFIXES = {"عرف", "عَرَف", "وجد", "وُجد", "قام", "يبدأ", "تبدأ", "أدى", "أدت", "تؤدي", "يؤدي", "كان", "كانت"}
        if len(raw_words) > 1 and raw_words[0] in COMMON_VERB_PREFIXES:
            raw_words.pop(0)

        if not raw_words:
            return None

        text_val = " ".join(raw_words).strip()
        if len(text_val) < 2:
            return None

        # Reject any entity starting with negation or jussive particles
        NEGATION_VERB_PREFIXES = ("لم ", "لن ", "لا ", "ما ", "ليس ", "ليست ", "كي ", "لكي ", "حتى ", "قد ")
        if text_val.startswith(NEGATION_VERB_PREFIXES):
            return None

        # Clean unclosed Wikipedia/citation brackets and language annotations (e.g. "السرطان (الإنجليزية" -> "السرطان")
        if "(" in text_val and ")" not in text_val:
            text_val = text_val.split("(")[0].strip()
        if "[" in text_val and "]" not in text_val:
            text_val = text_val.split("[")[0].strip()
        text_val = re.sub(r"\s*\(\s*(?:بال)?(?:إنجليزية|عربية|لاتينية|يونانية)?[^)]*$", "", text_val).strip()
        text_val = text_val.strip(" ،,.:؟!؛\t\n\"'()[]{}«»")
        if not text_val or len(text_val) < 2:
            return None

        # Reject standalone quantifiers and determiners
        STANDALONE_QUANTIFIERS = {"بضع", "بضعة", "عدة", "بعض", "كثير", "قليل", "جميع", "كل", "أحد", "إحدى"}
        if text_val in STANDALONE_QUANTIFIERS:
            return None

        # Reject standalone generic geographical common nouns unless part of a specific named place
        STANDALONE_GENERIC_LOCS = {"مدينة", "قرية", "بلدة", "نهر", "النهر", "بحيرة", "البحيرة", "شاطئ", "الشاطئ", "شواطئ", "الشواطئ", "بحر", "البحر", "بحار", "البحار"}
        if text_val in STANDALONE_GENERIC_LOCS and ent.get("category") == "LOCATION":
            return None

        # Normalize attached proclitics on defined nouns and proper names
        if len(text_val) > 3:
            if text_val.startswith("لل") and not text_val.startswith(("الله", "اللهم", "الليل", "الليث")):
                text_val = "ال" + text_val[2:]
            elif text_val.startswith(("بال", "فال", "كال", "وال")):
                text_val = "ال" + text_val[3:]
            elif text_val.startswith(("بأ", "بإ", "بآ", "كأ", "كإ", "لأ", "لإ")):
                text_val = text_val[1:]
            elif (
                len(text_val) > 4
                and text_val[0] in ("ب", "ك", "ل")
                and (
                    any(loc in text_val[1:] for loc in ["أمريكا", "أفريقيا", "أوروبا", "آسيا", "فلسطين", "باريس", "لندن", "مصر", "الأردن", "العراق", "سوريا", "لبنان"])
                    or ent.get("category") == "LOCATION"
                )
            ):
                text_val = text_val[1:]

        # Recalculate true span in original text
        found_pos = original_text.find(text_val)
        if found_pos != -1:
            start = found_pos
            end = start + len(text_val)

        category = ent.get("category", "CONCEPT").upper()

        # Specific-First Hierarchy Recovery & Contextual Corrections:
        GEOLOGY_TERMS = {
            "قشرة الأرض", "قشرة الكواكب", "القشرة الأرضية", "قشرة كوكب", "غرف الصهارة",
            "غرفة الصهارة", "الصهارة", "الوشاح", "النواة الأرضية", "بركان", "البراكين",
            "براكين", "الحمم البركانية", "الرماد البركاني", "التلال المخروطية", "الجبال البركانية",
            "تلال مخروطية", "جبال بركانية", "صفائح تكتونية", "فوهة بركانية"
        }

        # Rule 1: Never classify geological structures or planet layers as biological anatomy
        if category == "ANATOMY":
            if any(term in text_val for term in ["قشرة", "صهارة", "وشاح", "نواة الأرض", "طبقة صخرية", "أرضية"]):
                category = "GEOLOGY"
                if not ent.get("label_ar"):
                    ent["label_ar"] = "طبقة صخرية / بنية كوكبية" if "قشرة" in text_val else "تراكيب جيولوجية باطنية"

        # Rule 2: Never classify natural volcanoes or landforms as human-made artifacts
        if category == "ARTIFACT":
            if any(term in text_val for term in ["بركان", "براكين", "زلزال", "تلال", "جبال", "فوهة", "صخور"]):
                category = "GEOLOGY"
                if not ent.get("label_ar"):
                    ent["label_ar"] = "معالم وتضاريس بركانية"

        # Rule 3: Upgrade general landforms and soil layers from LOCATION/CONCEPT to GEOLOGY
        if category in ("LOCATION", "CONCEPT"):
            if any(term in text_val for term in ["التلال المخروطية", "الجبال البركانية", "تلال مخروطية", "جبال بركانية", "الطبقة العليا للتربة", "طبقة التربة", "طبقات التربة", "التربة"]):
                category = "GEOLOGY"
                if not ent.get("label_ar"):
                    ent["label_ar"] = "طبقة جيولوجية / تربة سطحية" if "تربة" in text_val else "تضاريس ومعالم جيولوجية"

        # Rule 4: Upgrade CONCEPT to specific categories when clear markers are present
        if category == "CONCEPT":
            CHEM_MARKERS = {
                "أكسيد", "كربون", "هيدروجين", "نيتروجين", "أكسجين", "كبريت", "كالسيوم", "صوديوم",
                "بوتاسيوم", "مغنيسيوم", "حديد", "نحاس", "قصدير", "برونز", "ذهب", "فضة", "زئبق",
                "بترول", "نفط", "فحم", "غاز طبيعي", "حمض", "كلوريد", "فلز", "سبيكة"
            }
            PHENOM_MARKERS = {
                "احتباس حراري", "مد وجزر", "رياح", "عاصفة", "زلزال", "كسوف", "خسوف",
                "حركة أمواج", "أمواج", "تمثيل ضوئي", "تبخر", "تكاثف", "إشعاع", "جاذبية"
            }
            GEO_MARKERS = {
                "دول العالم", "العالم", "الشرق الأوسط", "شمال أفريقيا", "الوطن العربي"
            }
            ASTRON_MARKERS = {
                "الشمس", "القمر", "كوكب", "مجرة", "سديم"
            }

            if any(term in text_val for term in GEOLOGY_TERMS):
                category = "GEOLOGY"
                if not ent.get("label_ar"):
                    ent["label_ar"] = "تضاريس ومعالم جيولوجية"
            elif any(term in text_val for term in CHEM_MARKERS):
                category = "CHEMICAL"
                if not ent.get("label_ar"):
                    ent["label_ar"] = "مركب كيميائي / مادة"
            elif any(term in text_val for term in PHENOM_MARKERS):
                category = "PHENOMENON"
                if not ent.get("label_ar"):
                    ent["label_ar"] = "ظاهرة علمية / بيئية"
            elif any(term in text_val for term in GEO_MARKERS):
                category = "LOCATION"
                if not ent.get("label_ar"):
                    ent["label_ar"] = "نطاق جغرافي / تجمع دول"
            elif any(term in text_val for term in ASTRON_MARKERS):
                category = "ASTRONOMY"
                if not ent.get("label_ar"):
                    ent["label_ar"] = "جرم فلكي"

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
        start = ent["start_char"]
        end = ent["end_char"]
        val = ent["text"]
        cat = ent["category"]

        # Strip leading conjunction if glued to entity
        if val.startswith(("و", "ف")) and len(val) > 3 and val not in {"واشنطن", "وادي", "ورقلة", "ويلز", "ولايات", "فلسطين", "فيينا"}:
            start += 1
            val = text[start:end]

        # Expand backward if preceded by compound name prefix
        before_text = text[:start].rstrip()
        for prefix in ["عبد", "ابن", "بن", "أبو", "ابو", "أم", "ام", "آل", "سيف", "نور", "صلاح", "علاء", "بهاء", "جمال"]:
            if before_text.endswith(prefix) and (len(before_text) == len(prefix) or before_text[-len(prefix) - 1] == " "):
                p_start = before_text.rfind(prefix)
                start = p_start
                val = text[start:end]
                break

        # Expand forward for compound organizations and universities
        if cat in ("ORGANIZATION", "UNIVERSITY"):
            after_text = text[end:].lstrip()
            for suffix in ["الوطنية", "الإسلامية", "الأمريكية", "العربية", "الدولية", "المفتوحة", "التخصصي", "العالمية", "المتحدة"]:
                if after_text.startswith(suffix) and (len(after_text) == len(suffix) or after_text[len(suffix)] in " ،.؟!\n\t"):
                    end = text.find(suffix, end) + len(suffix)
                    val = text[start:end]
                    break

        # Expand forward for compound locations
        if cat == "LOCATION":
            words = val.split()
            if len(words) == 1 and words[0] in {"رام", "بيت", "دير", "كفر", "عين", "شرم", "بئر", "أبو", "أم", "وادي", "رأس", "بور"}:
                after_text = text[end:].lstrip()
                next_word_m = re.match(r"^([\u0600-\u06FF]+)", after_text)
                if next_word_m:
                    nw = next_word_m.group(1)
                    # Verify next word is not a conjunction
                    if not nw.startswith("و"):
                        end = text.find(nw, end) + len(nw)
                        val = text[start:end]

        ent["start_char"] = start
        ent["end_char"] = end
        ent["text"] = text[start:end].strip()
        return ent


fusion_engine = EntityFusionEngine()
