# -*- coding: utf-8 -*-
"""
Base classes and data structures for Arabic morphological root extraction.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WordRoot:
    """
    Morphological analysis result for a single word token.
    Follows Section 8.2 of the Annotation Blueprint.
    """
    word: str
    root: Optional[str] = None
    root_len: Optional[int] = None
    status: str = "unknown"  # 'found', 'quadrilateral', 'proper_noun', 'foreign', 'ambiguous', 'stopword', 'not_applicable', 'unknown'
    engine: Optional[str] = None
    engine_version: Optional[str] = None
    needs_review: bool = False
    candidates: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "root": self.root,
            "root_len": self.root_len,
            "status": self.status,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "needs_review": self.needs_review,
            "candidates": self.candidates,
        }


class BaseRootEngine(ABC):
    """Abstract interface for morphological root analyzers."""

    name: str = "base"
    version: str = "1.0.0"

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the underlying library and data packages are loaded."""
        pass

    @abstractmethod
    def extract_root(self, word: str, sentence: str = "") -> Optional[WordRoot]:
        """Extracts trilateral or quadrilateral root for a single token."""
        pass
