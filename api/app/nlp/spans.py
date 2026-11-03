# -*- coding: utf-8 -*-
"""
Span Verification & Offset Mapping.
Finds exact character offsets (start, end) in the original document.
Rejects any hallucinated entity not present in the text.
"""

import re
from typing import List, Tuple, Optional
from app.nlp.normalize import normalize_for_matching


def find_all_spans(original_text: str, entity_text: str) -> List[Tuple[int, int]]:
    """
    Locates all occurrences of entity_text in original_text.
    Returns list of (start_char, end_char) tuples.
    """
    if not original_text or not entity_text:
        return []

    ent = entity_text.strip()
    spans: List[Tuple[int, int]] = []

    # 1. Exact string search
    start = 0
    while True:
        pos = original_text.find(ent, start)
        if pos == -1:
            break
        spans.append((pos, pos + len(ent)))
        start = pos + len(ent)

    if spans:
        return spans

    # 2. Tolerant regex matching with flexible diacritics, alif/yaa/taa forms
    tashkeel_pat = r"[\u064B-\u065F\u0670\u0640]*"
    # Remove existing tashkeel from entity for pattern generation
    clean_ent = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", ent)
    if not clean_ent.strip():
        return []

    char_patterns = []
    for ch in clean_ent:
        if ch in ("ا", "أ", "إ", "آ", "ٱ"):
            char_patterns.append(r"[اأإآٱ]" + tashkeel_pat)
        elif ch in ("ي", "ى"):
            char_patterns.append(r"[يى]" + tashkeel_pat)
        elif ch in ("ة", "ه"):
            char_patterns.append(r"[ةه]" + tashkeel_pat)
        elif ch.isspace():
            char_patterns.append(r"\s+")
        else:
            char_patterns.append(re.escape(ch) + tashkeel_pat)

    try:
        pattern = re.compile("".join(char_patterns), re.IGNORECASE)
        for match in pattern.finditer(original_text):
            spans.append((match.start(), match.end()))
    except Exception:
        pass

    return spans


def verify_entity_spans(
    original_text: str, entity_dict: dict
) -> Tuple[Optional[dict], bool]:
    """
    Verifies that entity_dict['text'] exists in original_text.
    Populates 'start', 'end', and 'occurrences'.
    Returns (updated_entity_dict, is_valid).
    """
    raw_text = entity_dict.get("text", "")
    spans = find_all_spans(original_text, raw_text)
    if not spans:
        return None, False

    first_start, first_end = spans[0]
    verified = dict(entity_dict)
    verified["start"] = first_start
    verified["end"] = first_end
    verified["occurrences"] = len(spans)
    # Ensure text matches exact slice from original text
    verified["text"] = original_text[first_start:first_end]
    return verified, True
