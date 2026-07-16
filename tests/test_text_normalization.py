"""Unit tests for text normalization (SCENARIOS.md "Text Normalization").

Run with: python -m unittest discover tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.whisper_utils import normalize_text


class TestTextNormalization(unittest.TestCase):
    def test_lowercase(self) -> None:
        self.assertEqual(normalize_text("HELLO ROBOT"), "hello robot")

    def test_punctuation_removed(self) -> None:
        self.assertEqual(normalize_text("What is your name?!"), "what is your name")

    def test_extra_whitespace_collapsed(self) -> None:
        self.assertEqual(normalize_text("  hello    world  "), "hello world")

    def test_combined_example_from_spec(self) -> None:
        # SCENARIOS.md's own example: "What is your name?!" -> "what is your name"
        self.assertEqual(normalize_text("What is your name?!"), "what is your name")

    def test_empty_string(self) -> None:
        self.assertEqual(normalize_text(""), "")

    def test_whitespace_only(self) -> None:
        self.assertEqual(normalize_text("   "), "")

    def test_unicode_letters_preserved(self) -> None:
        # Amharic and Arabic scripts must survive normalization, not be
        # stripped as "punctuation" -- \w in Python's re is Unicode-aware.
        self.assertEqual(normalize_text("ሰላም ሮቦት!"), "ሰላም ሮቦት")
        self.assertEqual(normalize_text("مرحبا روبوت؟"), "مرحبا روبوت")

    def test_idempotent(self) -> None:
        once = normalize_text("What IS your Name?!")
        twice = normalize_text(once)
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
