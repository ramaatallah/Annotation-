# -*- coding: utf-8 -*-
"""
Intelligent Text Chunking.
Splits long documents at sentence and paragraph boundaries without silent truncation.
Preserves global character offsets across chunk boundaries.
"""

import re
from typing import List, Tuple

_SENTENCE_SPLIT_REGEX = re.compile(r"([.!؟؛\n]+)")


def split_into_chunks(
    text: str, max_chunk_size: int = 1200, overlap: int = 100
) -> List[Tuple[str, int]]:
    """
    Splits text into overlapping chunks if longer than max_chunk_size.
    Returns list of tuples: (chunk_text, start_offset_in_original_text).
    """
    if not text or len(text) <= max_chunk_size:
        return [(text, 0)]

    chunks: List[Tuple[str, int]] = []
    n = len(text)
    start = 0

    while start < n:
        end = min(start + max_chunk_size, n)

        # If not at the end of document, find nearest sentence break
        if end < n:
            # Look backwards from end for sentence break
            search_window = text[max(start, end - 200) : end]
            matches = list(_SENTENCE_SPLIT_REGEX.finditer(search_window))
            if matches:
                last_match = matches[-1]
                end = max(start, end - 200) + last_match.end()
            else:
                # Fallback to nearest whitespace
                space_pos = text.rfind(" ", max(start, end - 100), end)
                if space_pos > start:
                    end = space_pos + 1

        chunk_text = text[start:end]
        chunks.append((chunk_text, start))

        if end >= n:
            break

        # Advance with overlap
        start = max(start + 1, end - overlap)

    return chunks
