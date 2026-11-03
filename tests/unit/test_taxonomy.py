# -*- coding: utf-8 -*-
"""
Unit tests for Entity Taxonomy and Domain mappings.
"""

import os
import sys

_curr = os.path.dirname(os.path.abspath(__file__))
_api_dir = os.path.join(os.path.dirname(_curr), "..", "api")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from app.nlp.taxonomy import TAXONOMY, DOMAINS, ALLOWED_SPECIALIZATIONS


def test_taxonomy_integrity():
    expected_core = [
        "PERSON", "NORP", "ORGANIZATION", "UNIVERSITY", "LOCATION", "FACILITY",
        "EVENT", "DATE", "LAW", "WORK", "TITLE", "TECHNOLOGY", "PRODUCT",
        "SUBSTANCE", "DISEASE", "ANATOMY", "ORGANISM", "CONCEPT", "METHOD",
        "FIELD", "QUANTITY", "LANGUAGE", "OTHER",
    ]
    for cat in expected_core:
        assert cat in TAXONOMY, f"Missing category {cat} in taxonomy"
        item = TAXONOMY[cat]
        assert "type_ar" in item
        assert "description" in item
        assert item["default_domain"] in DOMAINS


def test_allowed_specializations():
    assert "ORGANIZATION" in ALLOWED_SPECIALIZATIONS
    assert "UNIVERSITY" in ALLOWED_SPECIALIZATIONS["ORGANIZATION"]
    assert "FACILITY" in ALLOWED_SPECIALIZATIONS["ORGANIZATION"]
