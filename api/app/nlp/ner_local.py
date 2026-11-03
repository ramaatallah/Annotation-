# -*- coding: utf-8 -*-
"""
Local BERT Named Entity Recognition.
Wraps 'hatmimoha/arabic-ner' (or Wojood) with graceful initialization fallback.
Detects core academic entities: PERSON, LOCATION, ORGANIZATION, DATE, QUANTITY.
Includes subword stitching to eliminate BERT WordPiece artifacts (e.g. '##فيري', '##نات').
"""

import re
from typing import List, Dict, Any, Optional

_LOCAL_PIPELINE = None
_LOCAL_LOADED = False
_LOCAL_ERROR = None


def init_local_ner(model_name: str = "hatmimoha/arabic-ner") -> bool:
    """Initializes local transformers pipeline once during application startup."""
    global _LOCAL_PIPELINE, _LOCAL_LOADED, _LOCAL_ERROR
    if _LOCAL_LOADED:
        return True

    try:
        from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        _LOCAL_PIPELINE = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",
        )
        _LOCAL_LOADED = True
        return True
    except Exception as exc:
        _LOCAL_ERROR = str(exc)
        _LOCAL_LOADED = False
        return False


def is_local_ner_available() -> bool:
    return _LOCAL_LOADED and _LOCAL_PIPELINE is not None


def extract_local_entities(text: str) -> List[Dict[str, Any]]:
    """Runs local BERT token classification on text with strict subword cleaning."""
    if not is_local_ner_available():
        init_local_ner()
    if not is_local_ner_available() or not text.strip():
        return []

    try:
        raw_results = _LOCAL_PIPELINE(text)
        entities: List[Dict[str, Any]] = []

        tag_map = {
            "PER": "PERSON",
            "LOC": "LOCATION",
            "ORG": "ORGANIZATION",
            "DATE": "DATE",
            "MISC": "CONCEPT",
        }

        for r in raw_results:
            ent_group = r.get("entity_group", "")
            ent_type = tag_map.get(ent_group, ent_group)
            raw_word = str(r.get("word", "")).strip()
            score = float(r.get("score", 0.0))
            s = r.get("start")
            e = r.get("end")

            # 1. Handle BERT subwords (starting with ##)
            if raw_word.startswith("##"):
                # If continuous with previous entity, merge and extend span
                if entities and s is not None and entities[-1]["end"] == s:
                    entities[-1]["end"] = e
                    entities[-1]["text"] = text[entities[-1]["start"]:e].strip()
                    entities[-1]["bert_score"] = min(entities[-1]["bert_score"], round(score, 3))
                # Discard standalone orphan subwords
                continue

            # 2. Extract verbatim text slice from original text using exact offsets
            if s is not None and e is not None and e > s:
                actual_text = text[s:e].strip()
            else:
                actual_text = raw_word.replace("##", "").strip()

            # 3. Clean and validate: never accept subwords or single punctuation
            if not actual_text or "##" in actual_text or actual_text.startswith("#"):
                continue

            # Must contain at least two Arabic or alphanumeric characters
            alphanumeric = re.findall(r"[\u0621-\u064A\w]", actual_text)
            if len(alphanumeric) < 2:
                continue

            entities.append({
                "text": actual_text,
                "type": ent_type,
                "source": "bert",
                "bert_score": round(score, 3),
                "start": s,
                "end": e,
            })

        return entities
    except Exception:
        return []
