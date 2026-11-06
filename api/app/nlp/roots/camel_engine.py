# -*- coding: utf-8 -*-
"""
CAMeL Tools Root Extractor – MLEDisambiguator Edition.
Uses context-aware disambiguation (CALIMA + MLE) for accurate Arabic root extraction.
Falls back to basic Analyzer if the disambiguator model is not installed.
"""

import re
from typing import Optional, List
from app.nlp.roots.base import BaseRootEngine, WordRoot

try:
    from camel_tools.utils.charmap import CharMapper
    _CHARMAP_AVAILABLE = True
except Exception:
    _CHARMAP_AVAILABLE = False


def _clean_token(token: str) -> str:
    """Strips leading/trailing punctuation and non-word characters from token."""
    if not token:
        return ""
    return re.sub(r"^[^\w\u0621-\u064A]+|[^\w\u0621-\u064A]+$", "", str(token)).strip()

# Try loading MLEDisambiguator (preferred, context-aware)
_MLE_AVAILABLE = False
_MLE = None
try:
    from camel_tools.disambig.mle import MLEDisambiguator
    _MLE = MLEDisambiguator.pretrained("calima-msa-r13")
    _MLE_AVAILABLE = True
except Exception:
    pass

# Fallback: basic Analyzer (no context)
_ANALYZER_AVAILABLE = False
_ANALYZER = None
if not _MLE_AVAILABLE:
    try:
        from camel_tools.morphology.analyzer import Analyzer
        _ANALYZER = Analyzer.builtin_analyzer()
        _ANALYZER_AVAILABLE = True
    except Exception:
        pass

# Buckwalter → Arabic mapper
_BW2AR = None
if _CHARMAP_AVAILABLE:
    try:
        _BW2AR = CharMapper.builtin_mapper("bw2ar")
    except Exception:
        pass


def _bw_to_arabic(bw_root: str) -> str:
    """Converts a Buckwalter root string (e.g. 'k.t.b') to Arabic ('كتب')."""
    clean = bw_root.replace(".", "").strip()
    if _BW2AR and clean:
        return _BW2AR(clean)
    return clean


class CamelRootEngine(BaseRootEngine):
    name: str = "camel_mle" if _MLE_AVAILABLE else "camel_analyzer"
    version: str = "1.5.0"

    def __init__(self):
        pass  # Models are loaded at module level (singletons)

    def is_available(self) -> bool:
        return _MLE_AVAILABLE or _ANALYZER_AVAILABLE

    def extract_root(self, word: str, sentence: str = "") -> Optional[WordRoot]:
        """Extracts the morphological root for a single word."""
        if not self.is_available():
            return None

        clean_word = _clean_token(word)
        if not clean_word:
            return None

        try:
            if _MLE_AVAILABLE:
                return self._extract_via_mle(clean_word)
            else:
                return self._extract_via_analyzer(clean_word)
        except Exception:
            return None

    def extract_roots_batch(self, words: List[str]) -> List[Optional[WordRoot]]:
        """
        Batch extraction – disambiguates all words together for context.
        Only MLEDisambiguator benefits from batching; Analyzer does word-by-word.
        """
        if not self.is_available():
            return [None] * len(words)

        cleaned_words = [_clean_token(w) or w for w in words]

        if _MLE_AVAILABLE:
            return self._batch_via_mle(cleaned_words)
        else:
            return [self._extract_via_analyzer(w) for w in cleaned_words]

    # ----- MLEDisambiguator (preferred) -----

    def _extract_via_mle(self, word: str) -> Optional[WordRoot]:
        results = _MLE.disambiguate([word])
        if not results or not results[0].analyses:
            return None
        return self._parse_mle_result(word, results[0])

    def _batch_via_mle(self, words: List[str]) -> List[Optional[WordRoot]]:
        results = _MLE.disambiguate(words)
        out = []
        for word, res in zip(words, results):
            if not res.analyses:
                out.append(None)
            else:
                out.append(self._parse_mle_result(word, res))
        return out

    def _parse_mle_result(self, word: str, disambig_result) -> Optional[WordRoot]:
        """Parses a single MLEDisambiguator result into a WordRoot."""
        analysis = disambig_result.analyses[0].analysis
        raw_root = analysis.get("root", "")

        if not raw_root or raw_root in ("NO_ROOT", "NTWS", "DEFAULT"):
            return WordRoot(
                word=word, root=None, root_len=None,
                status="not_found", engine=self.name,
                engine_version=self.version, needs_review=False, candidates=[],
            )

        primary = _bw_to_arabic(raw_root)
        if not primary:
            return None

        # Collect alternative candidates from all analyses
        candidates = [primary]
        for a in disambig_result.analyses[1:5]:  # Top 5
            r = a.analysis.get("root", "")
            if r and r not in ("NO_ROOT", "NTWS", "DEFAULT"):
                c = _bw_to_arabic(r)
                if c and c not in candidates:
                    candidates.append(c)

        root_len = len(primary)
        status = "found" if root_len == 3 else ("quadrilateral" if root_len == 4 else "found")

        return WordRoot(
            word=word, root=primary, root_len=root_len,
            status=status, engine=self.name,
            engine_version=self.version, needs_review=(len(candidates) > 2),
            candidates=candidates,
        )

    # ----- Basic Analyzer (fallback) -----

    def _extract_via_analyzer(self, word: str) -> Optional[WordRoot]:
        analyses = _ANALYZER.analyze(word)
        if not analyses:
            return None

        candidates = []
        for a in analyses:
            raw_root = a.get("root")
            if raw_root and raw_root != "NO_ROOT":
                clean = _bw_to_arabic(raw_root)
                if clean and clean not in candidates:
                    candidates.append(clean)

        if not candidates:
            return None

        primary = candidates[0]
        root_len = len(primary)
        status = "found" if root_len == 3 else ("quadrilateral" if root_len == 4 else "found")

        return WordRoot(
            word=word, root=primary, root_len=root_len,
            status=status, engine="camel_analyzer",
            engine_version=self.version, needs_review=False,
            candidates=candidates,
        )
