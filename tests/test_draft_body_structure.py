"""
Validate draft body structure for Substack compatibility.
Ensures we never produce invalid ProseMirror that breaks the Substack editor.
"""
import json
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
ALLOWED_ARTICLE_URL_HOSTS = {
    "newsletter.systemdesignlaws.xyz",
    "raw.githubusercontent.com",
    "systemdesignlaws.substack.com",
    "systemdesignlaws.xyz",
}
sys.path.insert(0, str(REPO / "newsletter" / "scripts"))
from markdown_to_prosemirror import markdown_to_prosemirror

try:
    from create_draft import prepare_body_markdown, clean_draft_body, parse_draft_content
    HAS_CREATE_DRAFT = True
except (ModuleNotFoundError, ImportError):
    HAS_CREATE_DRAFT = False
    prepare_body_markdown = clean_draft_body = parse_draft_content = None


def _validate_node(node, path=""):
    """Recurse through doc, assert valid structure. Returns list of errors."""
    errors = []

    if isinstance(node, dict):
        # Only validate nodes that have both 'type' and 'content' (actual ProseMirror nodes)
        # Skip attrs dicts that happen to have a 'type' field
        is_pm_node = "type" in node and ("content" in node or "text" in node or node.get("type") == "text")
        if is_pm_node:
            if node.get("type") == "paragraph":
                content = node.get("content", [])
                for i, c in enumerate(content):
                    if c.get("type") != "text":
                        errors.append(f"{path}.content[{i}] must be type=text, got {c.get('type')}")
                    elif "text" not in c:
                        errors.append(f"{path}.content[{i}] must have 'text' field")
                    if c.get("marks") == []:
                        errors.append(f"{path}.content[{i}] has empty marks (omit when empty)")
            elif node.get("type") == "heading":
                if "attrs" not in node or "level" not in node.get("attrs", {}):
                    errors.append(f"{path} heading must have attrs.level")
                content = node.get("content", [])
                for i, c in enumerate(content):
                    if c.get("type") != "text":
                        errors.append(f"{path}.content[{i}] must be type=text")
            elif node.get("type") == "captionedImage":
                children = node.get("content", [])
                image2_nodes = [c for c in children if c.get("type") == "image2"]
                if len(image2_nodes) != 1:
                    errors.append(f"{path} captionedImage must have exactly one image2 child")
                for img in image2_nodes:
                    attrs = img.get("attrs", {})
                    if "src" not in attrs:
                        errors.append(f"{path} image2 node must have src attr")
                    if "alt" not in attrs:
                        errors.append(f"{path} image2 node must have alt attr")
            elif node.get("type") == "text":
                if "text" not in node:
                    errors.append(f"{path} text node must have 'text' field")
        # Only recurse into content arrays, not attrs
        for k, v in node.items():
            if k == "attrs":
                continue  # Skip attrs dicts - they aren't ProseMirror nodes
            if isinstance(v, (dict, list)):
                errors.extend(_validate_node(v, f"{path}.{k}"))
    elif isinstance(node, list):
        for i, x in enumerate(node):
            errors.extend(_validate_node(x, f"{path}[{i}]"))

    return errors


class TestDraftBodyStructure(unittest.TestCase):
    """Validate ProseMirror doc structure for Substack compatibility."""

    def test_minimal_doc_structure(self):
        """Minimal doc must have type=doc and content array."""
        md = "Hello world"
        doc = markdown_to_prosemirror(md)
        self.assertEqual(doc.get("type"), "doc")
        self.assertIsInstance(doc.get("content"), list)
        self.assertGreaterEqual(len(doc["content"]), 1)
        para = doc["content"][0]
        self.assertEqual(para.get("type"), "paragraph")
        self.assertGreaterEqual(len(para.get("content", [])), 1)
        text = para["content"][0]
        self.assertEqual(text.get("type"), "text")
        self.assertIn("text", text)

    def test_paragraph_inline_nodes_have_type_text(self):
        """Every paragraph content item must be {type: text, text: ...}."""
        md = "Consider an Instagram feed. **Bold** and [link](https://x.com)."
        doc = markdown_to_prosemirror(md)
        errors = _validate_node(doc)
        self.assertEqual(errors, [], f"Validation errors: {errors}")

    @unittest.skipUnless(HAS_CREATE_DRAFT, "create_draft.py not in repo")
    def test_no_empty_marks(self):
        """Clean should remove empty marks."""
        doc = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x", "marks": []}]}]}
        clean_draft_body(doc)
        para = doc["content"][0]
        text = para["content"][0]
        self.assertTrue("marks" not in text or text.get("marks"))

    @unittest.skipUnless(HAS_CREATE_DRAFT, "create_draft.py not in repo")
    def test_scaling_reads_draft_produces_valid_structure(self):
        """Full Scaling Reads draft must pass validation."""
        draft_path = REPO / "newsletter" / "drafts" / "scaling-reads-for-system-design-interviews.md"
        self.assertTrue(draft_path.exists(), f"Expected draft at {draft_path}")
        content = draft_path.read_text()
        title, _ = parse_draft_content(content, draft_path)
        body_md = prepare_body_markdown(content, title)
        doc = markdown_to_prosemirror(body_md)
        clean_draft_body(doc)
        errors = _validate_node(doc)
        self.assertEqual(errors, [], f"Scaling Reads draft has invalid structure: {errors}")
        content_list = doc.get("content", [])
        paras = [n for n in content_list if n.get("type") == "paragraph"]
        headings = [n for n in content_list if n.get("type") == "heading"]
        self.assertGreaterEqual(len(paras), 5, "Draft should have many paragraphs")
        self.assertGreaterEqual(len(headings), 3, "Draft should have multiple headings")


@unittest.skipUnless(HAS_CREATE_DRAFT, "create_draft.py not in repo")
class TestDraftDiagramsEmbedded(unittest.TestCase):
    """Verify diagrams are embedded as Substack-compatible images in every draft."""

    def _load_draft(self, filename):
        draft_path = REPO / "newsletter" / "drafts" / filename
        if not draft_path.exists():
            return None, None, None
        content = draft_path.read_text()
        title, _ = parse_draft_content(content, draft_path)
        body_md = prepare_body_markdown(content, title)
        doc = markdown_to_prosemirror(body_md)
        clean_draft_body(doc)
        return content, doc, draft_path

    def test_scaling_reads_has_embedded_diagrams(self):
        """Scaling Reads draft must have 20+ embedded Substack images."""
        content, doc, path = self._load_draft("scaling-reads-for-system-design-interviews.md")
        if content is None:
            self.skipTest("Draft not found")

        nodes = doc.get("content", [])
        images = [n for n in nodes if n.get("type") == "captionedImage"]
        self.assertGreaterEqual(len(images), 20, f"Draft must have at least 20 embedded diagrams (target 25), found {len(images)}")

        for i, img in enumerate(images):
            children = img.get("content", [])
            image2_nodes = [c for c in children if c.get("type") == "image2"]
            self.assertEqual(len(image2_nodes), 1, f"Image {i} must have exactly one image2 child node")
            attrs = image2_nodes[0].get("attrs", {})
            self.assertIn("src", attrs, f"Image {i} image2 node must have src attr")
            self.assertTrue(attrs["src"].startswith("https://"), f"Image {i} src must be a full URL: {attrs['src']}")
            self.assertIn("alt", attrs, f"Image {i} image2 node must have alt attr")

    def test_caching_has_embedded_diagrams(self):
        """Caching draft must have embedded Substack images (needs upgrade to 20+)."""
        content, doc, path = self._load_draft("caching-for-system-design-interviews.md")
        if content is None:
            self.skipTest("Draft not found")

        nodes = doc.get("content", [])
        images = [n for n in nodes if n.get("type") == "captionedImage"]
        # Caching currently has 5 - needs upgrade. Min 4 until upgraded.
        self.assertGreaterEqual(len(images), 4, f"Caching draft must have at least 4 embedded diagrams, found {len(images)}")

        for i, img in enumerate(images):
            children = img.get("content", [])
            image2_nodes = [c for c in children if c.get("type") == "image2"]
            self.assertEqual(len(image2_nodes), 1, f"Image {i} must have exactly one image2 child node")
            attrs = image2_nodes[0].get("attrs", {})
            self.assertIn("src", attrs, f"Image {i} image2 node must have src attr")
            self.assertTrue(attrs["src"].startswith("https://"), f"Image {i} src must be a full URL: {attrs['src']}")

    def test_all_drafts_minimum_20_diagrams(self):
        """All drafts (except caching and real-time-updates which need upgrade) must have 20+ diagrams."""
        # These drafts are known to need diagram upgrades
        UPGRADE_NEEDED = {
            "caching-for-system-design-interviews.md",
            "real-time-updates-for-system-design-interviews.md",
        }
        drafts_dir = REPO / "newsletter" / "drafts"
        for draft_path in drafts_dir.glob("*.md"):
            if draft_path.name in UPGRADE_NEEDED:
                continue
            content, doc, path = self._load_draft(draft_path.name)
            if content is None:
                continue
            nodes = doc.get("content", [])
            images = [n for n in nodes if n.get("type") == "captionedImage"]
            self.assertGreaterEqual(len(images), 20,
                f"{draft_path.name} must have at least 20 diagrams (target 25), found {len(images)}")

    def test_no_ascii_diagram_blocks(self):
        """Drafts must not contain ASCII diagram blocks (DIAGRAM: marker)."""
        drafts_dir = REPO / "newsletter" / "drafts"
        for draft_path in drafts_dir.glob("*.md"):
            content = draft_path.read_text()
            self.assertNotIn("DIAGRAM:", content,
                f"{draft_path.name} contains ASCII DIAGRAM: block - must use embedded images")

    def test_no_external_references(self):
        """Drafts must not contain external source attribution (content must be standalone)."""
        drafts_dir = REPO / "newsletter" / "drafts"
        for draft_path in drafts_dir.glob("*.md"):
            content = draft_path.read_text()
            self.assertNotIn("Reference:", content,
                f"{draft_path.name} contains Reference: attribution - must be standalone")
            self.assertNotIn("Source:", content,
                f"{draft_path.name} contains Source: attribution - must be standalone")

            urls = re.findall(r"https?://[^\s)>\"]+", content)
            external_urls = []
            for url in urls:
                host = urlparse(url).hostname or ""
                if host not in ALLOWED_ARTICLE_URL_HOSTS:
                    external_urls.append(url)

            self.assertEqual(
                external_urls,
                [],
                f"{draft_path.name} contains non-project URLs: {external_urls}",
            )

    def test_no_separate_plot_file_links(self):
        """Scaling reads draft must not link to local plot files (GitHub raw URLs are OK)."""
        draft_path = REPO / "newsletter" / "drafts" / "scaling-reads-for-system-design-interviews.md"
        if not draft_path.exists():
            self.skipTest("Draft not found")
        content = draft_path.read_text()
        for line in content.split("\n"):
            if "newsletter/plots/" in line and "raw.githubusercontent.com" not in line:
                self.fail(f"scaling-reads draft links to local plot file - must use hosted image URLs")

    def test_image_markdown_converts_to_captionedImage(self):
        """![alt](url) markdown must produce captionedImage with image2 child matching Substack format."""
        md = "![Test diagram](https://example.com/test.jpg)"
        doc = markdown_to_prosemirror(md)
        nodes = doc.get("content", [])
        images = [n for n in nodes if n.get("type") == "captionedImage"]
        self.assertEqual(len(images), 1, "Should produce one captionedImage node")
        children = images[0].get("content", [])
        image2 = [c for c in children if c.get("type") == "image2"]
        self.assertEqual(len(image2), 1, "captionedImage must contain image2 child")
        attrs = image2[0]["attrs"]
        self.assertEqual(attrs["src"], "https://example.com/test.jpg")
        self.assertEqual(attrs["alt"], "Test diagram")
        self.assertEqual(attrs["type"], "captionedImage", "image2 attrs.type must be 'captionedImage'")
        self.assertEqual(attrs["imageSize"], "full")
        self.assertIn("width", attrs)
        self.assertIn("height", attrs)

    def test_no_pipe_tables(self):
        """Scaling reads draft must not contain markdown pipe tables."""
        import re
        draft_path = REPO / "newsletter" / "drafts" / "scaling-reads-for-system-design-interviews.md"
        if not draft_path.exists():
            self.skipTest("Draft not found")
        content = draft_path.read_text()
        pipe_table = re.compile(r"^\|.*\|.*\|", re.MULTILINE)
        self.assertIsNone(pipe_table.search(content),
            "scaling-reads draft contains pipe table - must use bullet lists")

    def test_no_raw_code_blocks(self):
        """Drafts must not contain raw code blocks (``` markers) except for image/link syntax."""
        drafts_dir = REPO / "newsletter" / "drafts"
        for draft_path in drafts_dir.glob("*.md"):
            content = draft_path.read_text()
            self.assertNotIn("```", content,
                f"{draft_path.name} contains raw code block - must describe schemas as bullet lists")

    def test_no_em_dashes(self):
        """Drafts must use ASCII dashes, not em/en dashes."""
        drafts_dir = REPO / "newsletter" / "drafts"
        for draft_path in drafts_dir.glob("*.md"):
            content = draft_path.read_text()
            self.assertNotIn("\u2014", content,
                f"{draft_path.name} contains em dash - use ASCII hyphen instead")
            self.assertNotIn("\u2013", content,
                f"{draft_path.name} contains en dash - use ASCII hyphen instead")

    def test_draft_push_produces_nonempty_body(self):
        """The full scaling-reads draft must produce a ProseMirror body with substantial content."""
        content, doc, path = self._load_draft("scaling-reads-for-system-design-interviews.md")
        if content is None:
            self.skipTest("Draft not found")
        import json
        body_json = json.dumps(doc)
        self.assertGreater(len(body_json), 1000,
            f"Draft body JSON too small ({len(body_json)} chars) - likely empty or broken")


@unittest.skipUnless(HAS_CREATE_DRAFT, "create_draft.py not in repo")
class TestSubstackCompatibility(unittest.TestCase):
    """Validate ProseMirror JSON won't cause Substack 'Something went wrong' errors."""

    ALLOWED_NODE_TYPES = {
        "doc", "paragraph", "heading", "codeBlock", "captionedImage",
        "image2", "text", "subscribeWidget", "ctaCaption", "button",
        "horizontal_rule", "blockquote", "bullet_list", "list_item",
        "ordered_list",
    }

    def _load_and_convert(self, filename):
        draft_path = REPO / "newsletter" / "drafts" / filename
        if not draft_path.exists():
            return None
        content = draft_path.read_text()
        title, _ = parse_draft_content(content, draft_path)
        body_md = prepare_body_markdown(content, title)
        doc = markdown_to_prosemirror(body_md)
        clean_draft_body(doc)
        return doc

    def _collect_all_nodes(self, node, nodes=None):
        """Recursively collect all nodes from a ProseMirror doc."""
        if nodes is None:
            nodes = []
        if isinstance(node, dict):
            if "type" in node:
                nodes.append(node)
            for v in node.values():
                if isinstance(v, (dict, list)):
                    self._collect_all_nodes(v, nodes)
        elif isinstance(node, list):
            for item in node:
                self._collect_all_nodes(item, nodes)
        return nodes

    def test_no_null_values_in_attrs(self):
        """Substack rejects null values in attrs - clean_draft_body must strip them."""
        for draft_file in (REPO / "newsletter" / "drafts").glob("*.md"):
            doc = self._load_and_convert(draft_file.name)
            if doc is None:
                continue
            all_nodes = self._collect_all_nodes(doc)
            for node in all_nodes:
                attrs = node.get("attrs", {})
                for key, val in attrs.items():
                    self.assertIsNotNone(val,
                        f"{draft_file.name}: node type={node.get('type')} has null attr '{key}' - Substack rejects nulls")

    def test_captionedImage_has_required_attrs(self):
        """captionedImage image2 nodes must have src, imageSize, width, height."""
        for draft_file in (REPO / "newsletter" / "drafts").glob("*.md"):
            doc = self._load_and_convert(draft_file.name)
            if doc is None:
                continue
            all_nodes = self._collect_all_nodes(doc)
            for node in all_nodes:
                if node.get("type") == "image2":
                    attrs = node.get("attrs", {})
                    self.assertIn("src", attrs, f"{draft_file.name}: image2 missing src")
                    self.assertIn("imageSize", attrs, f"{draft_file.name}: image2 missing imageSize")
                    self.assertIn("width", attrs, f"{draft_file.name}: image2 missing width")
                    self.assertIn("height", attrs, f"{draft_file.name}: image2 missing height")

    def test_subscribeWidget_has_correct_format(self):
        """subscribeWidget must have url=%%checkout_url%%, language, and ctaCaption content."""
        md = "{{SUBSCRIBE}}"
        doc = markdown_to_prosemirror(md)
        clean_draft_body(doc)
        widgets = [n for n in doc.get("content", []) if n.get("type") == "subscribeWidget"]
        if not widgets:
            return  # No subscribe widget in this test
        w = widgets[0]
        attrs = w.get("attrs", {})
        self.assertEqual(attrs.get("url"), "%%checkout_url%%",
            "subscribeWidget url must be %%checkout_url%%")
        self.assertEqual(attrs.get("language"), "en",
            "subscribeWidget must have language=en")
        content = w.get("content", [])
        self.assertTrue(len(content) >= 1, "subscribeWidget must have content")
        self.assertEqual(content[0].get("type"), "ctaCaption",
            "subscribeWidget content[0] must be ctaCaption, not raw text")

    def test_no_empty_content_arrays(self):
        """Nodes with content must have at least one child."""
        for draft_file in (REPO / "newsletter" / "drafts").glob("*.md"):
            doc = self._load_and_convert(draft_file.name)
            if doc is None:
                continue
            all_nodes = self._collect_all_nodes(doc)
            for node in all_nodes:
                if "content" in node and node.get("type") not in ("doc",):
                    self.assertTrue(len(node["content"]) > 0,
                        f"{draft_file.name}: node type={node.get('type')} has empty content array")

    def test_images_use_full_width(self):
        """Images must use imageSize=full to prevent clipping."""
        for draft_file in (REPO / "newsletter" / "drafts").glob("*.md"):
            doc = self._load_and_convert(draft_file.name)
            if doc is None:
                continue
            all_nodes = self._collect_all_nodes(doc)
            for node in all_nodes:
                if node.get("type") == "image2":
                    attrs = node.get("attrs", {})
                    self.assertEqual(attrs.get("imageSize"), "full",
                        f"{draft_file.name}: image must use imageSize=full to prevent clipping")
                    # Width should be > height (landscape, not square)
                    w = attrs.get("width", 0)
                    h = attrs.get("height", 0)
                    self.assertGreater(w, h,
                        f"{draft_file.name}: image dimensions {w}x{h} look wrong (should be landscape)")

    def test_png_files_not_square(self):
        """PNG diagrams must not be square (indicates qlmanage padding bug)."""
        import struct
        png_dir = REPO / "newsletter" / "plots" / "png"
        if not png_dir.exists():
            self.skipTest("No PNG directory")
        for png in png_dir.glob("*.png"):
            with open(png, "rb") as f:
                f.read(16)
                w = struct.unpack(">I", f.read(4))[0]
                h = struct.unpack(">I", f.read(4))[0]
            self.assertNotEqual(w, h,
                f"{png.name}: PNG is {w}x{h} (square) - has dead space padding, needs cropping")

    def test_svg_valid_xml(self):
        """All SVG diagrams must be valid XML (no double-hyphens in comments, unclosed tags)."""
        import xml.etree.ElementTree as ET
        svg_dir = REPO / "newsletter" / "plots" / "svg"
        for svg_file in svg_dir.glob("*.svg"):
            try:
                ET.parse(str(svg_file))
            except ET.ParseError as e:
                self.fail(f"{svg_file.name}: invalid XML - {e}")

    def test_text_nodes_have_text_field(self):
        """Every text node in the doc must have a non-empty text field."""
        for draft_file in (REPO / "newsletter" / "drafts").glob("*.md"):
            doc = self._load_and_convert(draft_file.name)
            if doc is None:
                continue
            all_nodes = self._collect_all_nodes(doc)
            for node in all_nodes:
                if node.get("type") == "text":
                    self.assertIn("text", node,
                        f"{draft_file.name}: text node missing 'text' field")
                    self.assertTrue(len(node["text"]) > 0,
                        f"{draft_file.name}: text node has empty text")


if __name__ == "__main__":
    unittest.main()
