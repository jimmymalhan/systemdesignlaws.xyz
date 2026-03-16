"""Tests for create_draft.py - run without credentials for unit tests."""
import os
import tempfile
import unittest
from pathlib import Path

# Import the module (no API calls in parse_draft_content)
sys_path_insert = Path(__file__).resolve().parent.parent.parent
import sys
if str(sys_path_insert) not in sys.path:
    sys.path.insert(0, str(sys_path_insert))

from create_draft import parse_draft_content, get_publication_from_env, _parse_env_file


class TestParseDraftContent(unittest.TestCase):
    """Test draft parsing without API or credentials."""

    def test_parses_title_from_h1(self):
        content = "# My Article Title\n\nBody here."
        title, subtitle, body = parse_draft_content(content, "test.md")
        self.assertEqual(title, "My Article Title")
        self.assertEqual(body, content)

    def test_parses_tldr_as_subtitle(self):
        content = "# Caching\n\n**TL;DR** — One line summary here.\n\nBody."
        _, subtitle, _ = parse_draft_content(content, "caching.md")
        self.assertIn("One line summary", subtitle)

    def test_fallback_title_from_filename(self):
        content = "No heading here.\n\nJust body."
        title, _, _ = parse_draft_content(content, "my-great-post.md")
        self.assertEqual(title, "My Great Post")

    def test_empty_content_raises(self):
        with self.assertRaises(ValueError):
            parse_draft_content("", "x.md")


class TestParseEnvFile(unittest.TestCase):
    """Test .env parsing."""

    def test_parses_key_value(self):
        env = _parse_env_file('SUBSTACK_COOKIES=abc=123; x=y\n')
        self.assertEqual(env.get("SUBSTACK_COOKIES"), "abc=123; x=y")

    def test_ignores_comments(self):
        env = _parse_env_file('# comment\nKEY=val\n')
        self.assertEqual(env.get("KEY"), "val")
        self.assertNotIn("#", env)

    def test_strips_quotes(self):
        env = _parse_env_file('PUB="https://x.substack.com"\n')
        self.assertEqual(env.get("PUB"), "https://x.substack.com")


class TestGetPublicationFromEnv(unittest.TestCase):
    """Test publication URL parsing from env dict."""

    def test_returns_value_when_set(self):
        env = {"SUBSTACK_PUBLICATION": "https://jimmymalhan.substack.com"}
        self.assertEqual(get_publication_from_env(env), "https://jimmymalhan.substack.com")

    def test_returns_none_when_empty(self):
        self.assertIsNone(get_publication_from_env({}))
        self.assertIsNone(get_publication_from_env({"SUBSTACK_PUBLICATION": ""}))


if __name__ == "__main__":
    unittest.main()
