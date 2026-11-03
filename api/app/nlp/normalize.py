# -*- coding: utf-8 -*-
"""
Arabic Text Normalization & Hashing utilities.
Used strictly for index key generation and flexible span matching.
The original text is always preserved for offset calculations.
"""

import hashlib
import re

_TASHKEEL_REGEX = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_ALIF_REGEX = re.compile(r"[أإآٱ]")
_YAA_REGEX = re.compile(r"[ىي]")
_TAA_MARBUTA_REGEX = re.compile(r"[ةه]")


def normalize_for_matching(text: str) -> str:
    """
    Normalizes Arabic string strictly for flexible lookup and comparison:
    - Removes diacritics (tashkeel) and elongation (tatweel/kashida).
    - Unifies Alef forms (أ, إ, آ, ٱ -> ا).
    - Unifies Yaa forms (ى -> ي).
    - Collapses multiple whitespace.
    """
    if not text:
        return ""
    t = _TASHKEEL_REGEX.sub("", str(text))
    t = _ALIF_REGEX.sub("ا", t)
    t = _YAA_REGEX.sub("ي", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def clean_arabic_token(word: str) -> str:
    """Cleans a single token: removes punctuation, digits, tashkeel."""
    if not word:
        return ""
    t = _TASHKEEL_REGEX.sub("", str(word).strip())
    # Keep only Arabic characters and basic latin/digits if needed
    t = re.sub(r"[^\w\s\u0621-\u064A]", "", t)
    return t.strip()


def compute_sha256(text: str) -> str:
    """Computes SHA-256 hash of the input text for run reproducibility."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()
