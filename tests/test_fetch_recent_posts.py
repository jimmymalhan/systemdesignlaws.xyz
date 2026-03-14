"""Tests for fetch-recent-posts script."""
import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".github" / "scripts"))
from fetch_recent_posts import parse_rss_to_posts, strip_html

# Mock RSS XML
MOCK_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>First Post</title>
      <link>https://example.com/p/first</link>
      <description><p>First post <b>description</b> here.</p></description>
    </item>
    <item>
      <title>Second Post</title>
      <link>https://example.com/p/second</link>
      <description>Second post with a very long description that should be truncated because it exceeds the maximum allowed length for descriptions in the feed output format.</description>
    </item>
    <item>
      <title>Third Post</title>
      <link>https://example.com/p/third</link>
      <description></description>
    </item>
  </channel>
</rss>"""


class TestStripHtml(unittest.TestCase):
    def test_strips_tags(self):
        self.assertEqual(strip_html("<p>Hello <b>world</b></p>"), "Hello world")

    def test_empty(self):
        self.assertEqual(strip_html(""), "")

    def test_no_tags(self):
        self.assertEqual(strip_html("No tags"), "No tags")


class TestParseRssToPosts(unittest.TestCase):
    def test_parse_rss_to_posts(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(MOCK_RSS)
            rss_path = Path(f.name)

        try:
            posts = parse_rss_to_posts(rss_path)
            self.assertEqual(len(posts), 3)
            self.assertEqual(posts[0]["title"], "First Post")
            self.assertEqual(posts[0]["url"], "https://example.com/p/first")
            self.assertEqual(posts[0]["description"], "First post description here.")
            self.assertEqual(posts[1]["title"], "Second Post")
            self.assertLessEqual(len(posts[1]["description"]), 140)
            self.assertTrue(posts[1]["description"].endswith("..."))
            self.assertEqual(posts[2]["description"], "Read more.")
        finally:
            rss_path.unlink()

    def test_parse_rss_respects_limit(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(MOCK_RSS)
            rss_path = Path(f.name)

        try:
            posts = parse_rss_to_posts(rss_path, limit=2)
            self.assertEqual(len(posts), 2)
        finally:
            rss_path.unlink()


class TestRecentPostsJson(unittest.TestCase):
    ISO8601_REGEX = (
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})?$"
    )

    def test_recent_posts_json_schema(self):
        """Ensure recent-posts.json exists and has valid schema."""
        repo_root = Path(__file__).resolve().parent.parent
        json_path = repo_root / "recent-posts.json"
        if not json_path.exists():
            self.skipTest("recent-posts.json not found (run fetch script first)")
        data = json.loads(json_path.read_text())
        self.assertIn("posts", data)
        self.assertIsInstance(data["posts"], list)
        for post in data["posts"]:
            self.assertIn("title", post)
            self.assertIn("url", post)
            self.assertIn("description", post)

    def test_recent_posts_updated_format(self):
        """When 'updated' exists in recent-posts.json, it must be valid ISO 8601."""
        import re
        repo_root = Path(__file__).resolve().parent.parent
        json_path = repo_root / "recent-posts.json"
        if not json_path.exists():
            self.skipTest("recent-posts.json not found")
        data = json.loads(json_path.read_text())
        if "updated" not in data or not data["updated"]:
            self.skipTest("recent-posts.json has no 'updated' field")
        updated = data["updated"]
        self.assertIsInstance(updated, str, "'updated' must be a string")
        self.assertRegex(
            updated,
            self.ISO8601_REGEX,
            f"'updated' must be ISO 8601, got: {updated!r}",
        )


if __name__ == "__main__":
    unittest.main()
