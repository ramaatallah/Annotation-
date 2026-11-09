"""Unit tests for CAMeL Tools Morphological Root Extraction Engine."""

import pytest
from app.services.nlp.root_engine import root_engine


def test_camel_tools_academic_roots():
    """Validates roots for core academic and grammatical terms."""
    test_cases = {
        "جامعة": "جمع",
        "النجاح": "نجح",
        "الوطنية": "وطن",
        "تقع": "وقع",
        "مدينة": "مدن",
        "المسافرون": "سفر",
        "بالتعاون": "عون",
        "الصحة": "صحح",
        "الطلاب": "طلب",
        "يدرسون": "درس",
        "المناعة": "منع",
        "الطب": "طبب",
        "أبحاث": "بحث",
        "مستشفى": "شفي",
        "الأمراض": "مرض",
        "تقنية": "تقن",
    }

    for word, expected_root in test_cases.items():
        res = root_engine.extract_word_root(word)
        assert res["root"] == expected_root, f"Failed for {word}: expected {expected_root}, got {res['root']}"
        assert res["status"] == "analyzed"
        assert res["is_trilateral"] is True
        assert res["source"] == "camel_tools"
        assert res["lemma"] is not None


def test_unresolved_no_guessing():
    """Validates that proper nouns or unresolvable words return status 'unresolved' without guessing."""
    unresolved_words = ["نابلس", "فأسقيناكموه"]

    for word in unresolved_words:
        res = root_engine.extract_word_root(word)
        assert res["root"] is None, f"Expected no root for {word}, got {res['root']}"
        assert res["status"] == "unresolved"
        assert res["is_trilateral"] is False


def test_quadrilateral_roots():
    """Validates quadrilateral (4-letter) roots without forcing trilateral structure."""
    quad_words = {
        "برمجة": "برمج",
        "ترجمة": "ترجم",
        "هندسة": "هندس",
        "زلزال": "زلزل",
    }

    for word, expected_root in quad_words.items():
        res = root_engine.extract_word_root(word)
        assert res["root"] == expected_root, f"Failed for {word}: expected {expected_root}, got {res['root']}"
        assert res["status"] == "analyzed"
        assert res["is_trilateral"] is False


def test_phrase_contextual_roots():
    """Validates contextual disambiguation across an entire Arabic sentence."""
    phrase = "جامعة النجاح الوطنية تقع في مدينة نابلس وتعمل بالتعاون مع المسافرون"
    roots_list = root_engine.extract_phrase_roots(phrase)

    words = [r["word"] for r in roots_list]
    # Stopwords like 'في' and 'مع' should be skipped
    assert "في" not in words
    assert "مع" not in words

    root_dict = {r["word"]: r for r in roots_list}
    assert root_dict["جامعة"]["root"] == "جمع"
    assert root_dict["النجاح"]["root"] == "نجح"
    assert root_dict["الوطنية"]["root"] == "وطن"
    assert root_dict["مدينة"]["root"] == "مدن"
    assert root_dict["المسافرون"]["root"] == "سفر"
    assert root_dict["المسافرون"]["lemma"] == "مسافر"
    assert root_dict["المسافرون"]["status"] == "analyzed"
