"""Unit tests for newsletter create_draft script (no credentials required)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sys_path))

# Load create_draft when available (not committed on all branches)
_create_draft_path = sys_path / "newsletter" / "scripts" / "create_draft.py"
HAS_CREATE_DRAFT = _create_draft_path.exists()

if HAS_CREATE_DRAFT:
    import importlib.util
    spec = importlib.util.spec_from_file_location("create_draft", _create_draft_path)
    create_draft = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(create_draft)
    parse_draft_content = create_draft.parse_draft_content
    get_publication_from_env = create_draft.get_publication_from_env
else:
    parse_draft_content = None
    get_publication_from_env = None


@unittest.skipUnless(HAS_CREATE_DRAFT, "create_draft.py not in repo")
class TestParseDraftContent(unittest.TestCase):
    """Test draft parsing logic."""

    def test_parses_title_and_subtitle(self):
        content = """# Caching for System Design Interviews

**TL;DR** — Caching cuts latency 50x.

Body text here.
"""
        title, subtitle = parse_draft_content(content, Path("dummy.md"))
        self.assertEqual(title, "Caching for System Design Interviews")
        self.assertIn("Caching cuts latency", subtitle or "")

    def test_fallback_title_from_filename(self):
        content = "No heading here.\n\nJust body."
        title, _ = parse_draft_content(content, Path("my-article-name.md"))
        self.assertEqual(title, "My Article Name")

    def test_empty_content_returns_empty_title(self):
        title, subtitle = parse_draft_content("", Path("x.md"))
        self.assertEqual(title, "X")
        self.assertEqual(subtitle, "")

    def test_returns_title_and_subtitle_tuple(self):
        content = "# Hi\n\n**TL;DR** Short.\n\nBody"
        result = parse_draft_content(content, Path("x.md"))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "Hi")
        self.assertIn("Short", result[1])


@unittest.skipUnless(HAS_CREATE_DRAFT, "create_draft.py not in repo")
class TestGetPublicationFromEnv(unittest.TestCase):
    """Test publication URL parsing from env."""

    def test_returns_none_when_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# comment\n")
            f.flush()
            p = get_publication_from_env(Path(f.name))
        self.assertIsNone(p)

    def test_returns_publication_when_set(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SUBSTACK_PUBLICATION=https://jimmymalhan.substack.com\n")
            f.flush()
            p = get_publication_from_env(Path(f.name))
        self.assertEqual(p, "https://jimmymalhan.substack.com")


class TestDraftFileExists(unittest.TestCase):
    """Test that the expected draft file exists (sanity check)."""

    def test_caching_draft_exists(self):
        repo = Path(__file__).resolve().parent.parent
        draft = repo / "newsletter" / "drafts" / "caching-for-system-design-interviews.md"
        self.assertTrue(draft.exists(), f"Expected draft at {draft}")
        content = draft.read_text()
        self.assertIn("Caching", content)
        self.assertIn("TL;DR", content)
