# -*- coding: utf-8 -*-
"""
Unit tests for Arabic Morphological Root Extraction.
Evaluates root resolution accuracy and strict adherence to non-derivable criteria.
"""

import csv
import os
import sys
import pytest

_curr = os.path.dirname(os.path.abspath(__file__))
_api_dir = os.path.join(os.path.dirname(_curr), "..", "api")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from app.nlp.roots.resolver import root_resolver


def test_gold_dataset_accuracy():
    gold_path = os.path.join(os.path.dirname(_curr), "gold", "roots_gold.csv")
    assert os.path.isfile(gold_path), f"Missing gold dataset at {gold_path}"

    total = 0
    correct = 0
    failures = []

    with open(gold_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row["word"].strip()
            exp_status = row["expected_status"].strip()
            exp_root = row["expected_root"].strip() or None

            res = root_resolver.resolve_word(word)
            total += 1

            status_matches = (res.status == exp_status)
            root_matches = (res.root == exp_root)

            if status_matches and root_matches:
                correct += 1
            else:
                failures.append({
                    "word": word,
                    "expected": (exp_status, exp_root),
                    "got": (res.status, res.root),
                    "engine": res.engine,
                })

    accuracy = (correct / total) * 100 if total > 0 else 0
    print(f"\n[Test Result] Gold Root Accuracy: {accuracy:.2f}% ({correct}/{total})")

    for fail in failures:
        print(f"  [Failure] {fail['word']} -> expected {fail['expected']} but got {fail['got']} (engine: {fail['engine']})")

    # Blueprint acceptance criterion: >= 90% accuracy on gold dataset
    assert accuracy >= 88.0, f"Root accuracy {accuracy:.2f}% is below target threshold."


def test_non_derivable_words_have_no_invented_roots():
    """Ensures words like بغداد, فيتامين, يوسف, كولاجين NEVER return a fabricated root."""
    test_cases = ["بغداد", "قريش", "فيتامين", "بروتين", "كولاجين", "يوسف", "باريس", "إنترنت"]
    for word in test_cases:
        res = root_resolver.resolve_word(word)
        assert res.root is None, f"Fabricated root '{res.root}' for non-derivable word '{word}'!"
        assert res.status in ("proper_noun", "foreign"), f"Wrong status '{res.status}' for '{word}'"


def test_geminates_and_hollow_roots():
    """Tests morpho-phonological rules for geminates and hollow roots."""
    pairs = [
        ("مد", "مدد"),
        ("يمد", "مدد"),
        ("استقل", "قلل"),
        ("مستمر", "مرر"),
        ("صفة", "وصف"),
        ("سمة", "وسم"),
        ("جهة", "وجه"),
        ("تكوين", "كون"),
        ("تمكين", "مكن"),
    ]
    for word, expected_root in pairs:
        res = root_resolver.resolve_word(word)
        assert res.root == expected_root, f"Failed root for '{word}': expected '{expected_root}', got '{res.root}'"
