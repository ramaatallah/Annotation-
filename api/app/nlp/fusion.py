# -*- coding: utf-8 -*-
"""
Entity Fusion & Verification Pipeline.
Merges local BERT detections with fine-grained LLM classifications.
Performs span verification, specialization resolution, conflict marking,
eliminates BERT WordPiece fragments (e.g. ##فيري, ##نات),
and populates word-level morphological roots via CAMeL Tools.
"""

import re
from typing import List, Dict, Any, Tuple
from app.nlp.spans import verify_entity_spans, find_all_spans
from app.nlp.taxonomy import TAXONOMY, ALLOWED_SPECIALIZATIONS
from app.nlp.roots.camel_engine import CamelRootEngine

# Singleton CAMeL root engine (loaded once at module import time)
_camel_engine = CamelRootEngine()


def is_valid_entity_text(text: str) -> bool:
    """Rejects WordPiece subword fragments, hashes, and non-semantic noise."""
    if not text:
        return False
    t = text.strip()
    if "##" in t or t.startswith("#"):
        return False
    # Must contain at least two Arabic or alphanumeric characters
    chars = re.findall(r"[\u0621-\u064A\w]", t)
    return len(chars) >= 2


def fuse_entities(
    original_text: str,
    local_entities: List[Dict[str, Any]],
    llm_entities: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fuses local and LLM entities according to Section 7.5 of the Blueprint.
    Returns: (fused_entities_list, rejected_count).
    """
    rejected_by_span_check = 0
    verified_llm: List[Dict[str, Any]] = []

    # Step 1: Span Verification for LLM entities + subword rejection
    for le in llm_entities:
        ent_text = le.get("text", "")
        if not is_valid_entity_text(ent_text):
            rejected_by_span_check += 1
            continue

        verified, is_valid = verify_entity_spans(original_text, le)
        if is_valid and verified and is_valid_entity_text(verified.get("text", "")):
            verified_llm.append(verified)
        else:
            rejected_by_span_check += 1

    # Step 2: Ensure spans on local BERT entities + subword rejection
    verified_local: List[Dict[str, Any]] = []
    for be in local_entities:
        ent_text = be.get("text", "")
        if not is_valid_entity_text(ent_text):
            continue

        s = be.get("start")
        e = be.get("end")
        if s is not None and e is not None and e > s:
            # Overwrite text with exact slice from original text
            be["text"] = original_text[s:e].strip()
            if is_valid_entity_text(be["text"]):
                verified_local.append(be)
        else:
            v, is_valid = verify_entity_spans(original_text, be)
            if is_valid and v and is_valid_entity_text(v.get("text", "")):
                verified_local.append(v)

    # Step 3: Merge overlapping and matching spans
    span_map: Dict[Tuple[int, int], Dict[str, Any]] = {}

    for be in verified_local:
        s, e = be["start"], be["end"]
        span_map[(s, e)] = {
            "text": be["text"],
            "type": be["type"],
            "start": s,
            "end": e,
            "source": "bert",
            "bert_score": be.get("bert_score"),
            "llm_self_confidence": None,
            "conflict": False,
        }

    for le in verified_llm:
        s, e = le["start"], le["end"]
        llm_type = le.get("type", "CONCEPT")
        llm_conf = le.get("confidence") or le.get("llm_self_confidence")

        # Check if identical span exists in BERT
        if (s, e) in span_map:
            existing = span_map[(s, e)]
            bert_type = existing["type"]

            if bert_type == llm_type:
                existing["source"] = "both"
                existing["llm_self_confidence"] = llm_conf
                existing["type_ar"] = le.get("type_ar")
                existing["subtype_ar"] = le.get("subtype_ar")
                existing["domain"] = le.get("domain")
            elif llm_type in ALLOWED_SPECIALIZATIONS.get(bert_type, []):
                # Allowed specialization (e.g. BERT ORG -> LLM UNIVERSITY)
                existing["type"] = llm_type
                existing["type_ar"] = le.get("type_ar")
                existing["subtype_ar"] = le.get("subtype_ar")
                existing["domain"] = le.get("domain")
                existing["source"] = "both"
                existing["llm_self_confidence"] = llm_conf
                existing["conflict"] = False
            else:
                # Incompatible conflict: prefer LLM with conflict flag
                existing["type"] = llm_type
                existing["type_ar"] = le.get("type_ar")
                existing["subtype_ar"] = le.get("subtype_ar")
                existing["domain"] = le.get("domain")
                existing["source"] = "both"
                existing["llm_self_confidence"] = llm_conf
                existing["conflict"] = True
        else:
            # Check for partial span overlap -> prefer longer span
            overlapped = False
            for (os, oe), item in list(span_map.items()):
                if not (e <= os or s >= oe):  # Overlap
                    overlapped = True
                    curr_len = e - s
                    prev_len = oe - os
                    if curr_len > prev_len:
                        del span_map[(os, oe)]
                        span_map[(s, e)] = {
                            "text": le["text"],
                            "type": llm_type,
                            "type_ar": le.get("type_ar"),
                            "subtype_ar": le.get("subtype_ar"),
                            "domain": le.get("domain"),
                            "start": s,
                            "end": e,
                            "source": "llm",
                            "bert_score": item.get("bert_score"),
                            "llm_self_confidence": llm_conf,
                            "conflict": False,
                        }
                    break

            if not overlapped:
                span_map[(s, e)] = {
                    "text": le["text"],
                    "type": llm_type,
                    "type_ar": le.get("type_ar"),
                    "subtype_ar": le.get("subtype_ar"),
                    "domain": le.get("domain"),
                    "start": s,
                    "end": e,
                    "source": "llm",
                    "bert_score": None,
                    "llm_self_confidence": llm_conf,
                    "conflict": False,
                }

    fused: List[Dict[str, Any]] = [
        ent for ent in span_map.values() if is_valid_entity_text(ent.get("text", ""))
    ]

    # Step 4: Populate Taxonomy metadata & Word Roots for each entity
    for ent in fused:
        etype = ent["type"]
        if etype in TAXONOMY:
            if not ent.get("type_ar"):
                ent["type_ar"] = TAXONOMY[etype]["type_ar"]
            if not ent.get("domain"):
                ent["domain"] = TAXONOMY[etype]["default_domain"]

        # Word-level root extraction via CAMeL Tools (batch for context)
        if _camel_engine.is_available():
            entity_words = ent["text"].split()
            root_results = _camel_engine.extract_roots_batch(entity_words)
            ent["words"] = [wr.to_dict() for wr in root_results if wr is not None]
        else:
            ent["words"] = []

    # Sort entities by start offset
    fused.sort(key=lambda x: x.get("start", 0))
    print(f"[Pipeline] BERT detected: {len(local_entities)}, LLM detected: {len(llm_entities)} -> Final fused: {len(fused)}")
    return fused, rejected_by_span_check
