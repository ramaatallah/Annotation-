# -*- coding: utf-8 -*-
"""
Unit tests for Span Verification and Text Chunking.
"""

import os
import sys
import pytest

_curr = os.path.dirname(os.path.abspath(__file__))
_api_dir = os.path.join(os.path.dirname(_curr), "..", "api")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from app.nlp.spans import find_all_spans, verify_entity_spans
from app.nlp.chunking import split_into_chunks


def test_find_all_spans():
    text = "جامعة النجاح الوطنية في نابلس وجامعة النجاح مؤسسة عريقة."
    query = "جامعة النجاح"
    spans = find_all_spans(text, query)
    assert len(spans) == 2
    assert spans[0] == (0, 12)
    assert text[spans[0][0]:spans[0][1]] == query


def test_reject_hallucinated_entity():
    text = "كتب ابن خلدون كتابه في تونس."
    fake_entity = {"text": "جامعة هارفارد", "type": "UNIVERSITY"}
    verified, is_valid = verify_entity_spans(text, fake_entity)
    assert not is_valid
    assert verified is None


def test_chunking_preserves_sentence_boundaries():
    text = "الجملة الأولى تمثل مقدمة البحث. الجملة الثانية تناقش المنهج العلمي المستخدم في التحليل. الجملة الثالثة تستعرض النتائج بالتفصيل."
    chunks = split_into_chunks(text, max_chunk_size=60, overlap=15)
    assert len(chunks) >= 2
    for chunk_text, offset in chunks:
        assert text[offset:offset + len(chunk_text)] == chunk_text
