"""
Custom markdown-to-ProseMirror converter for Substack drafts.
Uses Substack document format: https://github.com/can3p/substack-api-notes/blob/master/doc_format.md

Supports: headings, paragraphs, images (captionedImage), blockquotes, pullquotes,
horizontal rules, subscribe widgets, buttons, bold, italic, links.
"""
import re
from typing import Any


def _tokens_to_inline(tokens: list[dict]) -> list[dict]:
    """Convert parse_inline tokens to ProseMirror inline nodes. Each node needs type+text."""
    result = []
    for t in tokens:
        text = t.get("content") or t.get("text") or ""
        if not text:
            continue
        node = {"type": "text", "text": text}
        marks = t.get("marks")
        if marks:
            pm_marks = []
            for m in marks:
                pm = {"type": m.get("type", "strong")}
                if pm["type"] == "link":
                    href = m.get("href") or (m.get("attrs") or {}).get("href")
                    if href:
                        pm["attrs"] = {"href": href}
                pm_marks.append(pm)
            if pm_marks:
                node["marks"] = pm_marks
        result.append(node)
    return result


def _parse_inline(text: str) -> list[dict]:
    """Parse **bold**, *italic*, [link](url) into tokens. Returns list of {content, marks?}."""
    if not text:
        return []
    tokens = []
    link_pat = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    bold_pat = re.compile(r"\*\*([^*]+)\*\*")
    italic_pat = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")

    matches = []
    for m in link_pat.finditer(text):
        if m.start() == 0 or (m.start() > 0 and text[m.start() - 1 : m.start() + 1] != "!["):
            matches.append((m.start(), m.end(), "link", m.group(1), m.group(2)))
    for m in bold_pat.finditer(text):
        if not any(s <= m.start() < e for s, e, *_ in matches):
            matches.append((m.start(), m.end(), "bold", m.group(1), None))
    for m in italic_pat.finditer(text):
        if not any(s <= m.start() < e for s, e, *_ in matches):
            matches.append((m.start(), m.end(), "italic", m.group(1), None))

    matches.sort(key=lambda x: x[0])
    last = 0
    for start, end, kind, content, url in matches:
        if start > last:
            tokens.append({"content": text[last:start]})
        if kind == "link":
            tokens.append({"content": content, "marks": [{"type": "link", "attrs": {"href": url}}]})
        elif kind == "bold":
            tokens.append({"content": content, "marks": [{"type": "strong"}]})
        elif kind == "italic":
            tokens.append({"content": content, "marks": [{"type": "em"}]})
        last = end
    if last < len(text):
        tokens.append({"content": text[last:]})
    return [t for t in tokens if t.get("content")]


def _make_image_node(src_url: str, alt_text: str) -> dict:
    """Create a Substack captionedImage ProseMirror node. Uses full width, correct aspect ratio."""
    return {
        "type": "captionedImage",
        "content": [
            {
                "type": "image2",
                "attrs": {
                    "src": src_url,
                    "fullscreen": False,
                    "imageSize": "full",
                    "height": 747,
                    "width": 1456,
                    "resizeWidth": 1456,
                    "alt": alt_text,
                    "title": "",
                    "type": "captionedImage",
                    "belowTheFold": False,
                },
            }
        ],
    }


def _make_paragraph(text: str) -> dict:
    """Create a paragraph node with inline parsing."""
    inline = _tokens_to_inline(_parse_inline(text))
    return {
        "type": "paragraph",
        "content": inline or [{"type": "text", "text": text}],
    }


def markdown_to_prosemirror(md: str) -> dict:
    """
    Convert markdown to Substack ProseMirror doc. Returns {"type": "doc", "content": [...]}.

    Special markers:
      > text         -> blockquote
      >> text        -> pullquote
      ---            -> horizontal_rule
      {{SUBSCRIBE}}  -> subscribeWidget
      {{BUTTON:text|url}} -> button
      ![alt](url)    -> captionedImage
    """
    lines = md.strip().split("\n")
    blocks = []
    current = []
    in_code = False
    code_lang = None

    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                if current:
                    blocks.append({"type": "code", "language": code_lang, "content": "\n".join(current)})
                current = []
                in_code = False
            else:
                if current:
                    blocks.append({"type": "text", "content": "\n".join(current)})
                    current = []
                code_lang = line.strip()[3:].strip() or None
                in_code = True
            continue

        if in_code:
            current.append(line)
        elif line.strip() == "":
            if current:
                blocks.append({"type": "text", "content": "\n".join(current)})
                current = []
        else:
            current.append(line)

    if current:
        if in_code:
            blocks.append({"type": "code", "language": code_lang, "content": "\n".join(current)})
        else:
            blocks.append({"type": "text", "content": "\n".join(current)})

    content = []
    for block in blocks:
        if block["type"] == "code":
            code = block.get("content", "").strip()
            if code:
                node = {"type": "codeBlock", "content": [{"type": "text", "text": code}]}
                if block.get("language"):
                    node["attrs"] = {"language": block.get("language")}
                content.append(node)
            continue

        text = block.get("content", "").strip()
        if not text:
            continue

        # --- Horizontal rule
        if text == "---":
            content.append({"type": "horizontal_rule"})

        # # Headings
        elif text.startswith("#"):
            level = len(text) - len(text.lstrip("#"))
            level = min(max(level, 1), 6)
            heading_text = text.lstrip("#").strip()
            if heading_text:
                inline = _tokens_to_inline(_parse_inline(heading_text))
                content.append({
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": inline or [{"type": "text", "text": heading_text}],
                })

        # ![alt](url) Images
        elif text.startswith("!["):
            img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", text)
            if img_match:
                content.append(_make_image_node(img_match.group(2), img_match.group(1)))

        # {{SUBSCRIBE}} widget
        elif text.strip() == "{{SUBSCRIBE}}":
            content.append({
                "type": "subscribeWidget",
                "attrs": {
                    "url": "%%checkout_url%%",
                    "text": "Subscribe",
                    "language": "en",
                },
                "content": [
                    {
                        "type": "ctaCaption",
                        "content": [
                            {
                                "type": "text",
                                "text": "Subscribe for free to receive new posts.",
                            }
                        ],
                    }
                ],
            })

        # {{BUTTON:text|url}} button
        elif text.strip().startswith("{{BUTTON:"):
            btn_match = re.match(r"\{\{BUTTON:([^|]+)\|([^}]+)\}\}", text.strip())
            if btn_match:
                content.append({
                    "type": "button",
                    "attrs": {"url": btn_match.group(2).strip(), "action": "navigate"},
                    "content": [{"type": "text", "text": btn_match.group(1).strip()}],
                })

        # Multi-line blocks (lists, blockquotes, pullquotes, mixed content)
        elif "\n" in text:
            raw_lines = [l.strip() for l in text.split("\n") if l.strip()]

            # Check if all lines are blockquote (> prefix)
            all_blockquote = all(l.startswith("> ") for l in raw_lines)
            all_pullquote = all(l.startswith(">> ") for l in raw_lines)

            if all_pullquote:
                inner = [_make_paragraph(l[3:].strip()) for l in raw_lines]
                content.append({"type": "pullquote", "content": inner})
            elif all_blockquote:
                inner = [_make_paragraph(l[2:].strip()) for l in raw_lines]
                content.append({"type": "blockquote", "content": inner})
            else:
                # Markdown table: lines contain | and at least one is a separator (---)
                is_table = raw_lines and all("|" in l for l in raw_lines)
                sep = re.compile(r"^\|[\s\-:]+\|")
                if is_table:
                    for raw_line in raw_lines:
                        if sep.match(raw_line):
                            continue
                        cells = [c.strip() for c in raw_line.split("|") if c.strip()]
                        if cells:
                            bullet_text = " | ".join(cells)
                            content.append(_make_paragraph(bullet_text))
                else:
                    for raw_line in raw_lines:
                        line = raw_line.strip()
                        # Image in multi-line block
                        img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
                        if img_match:
                            content.append(_make_image_node(img_match.group(2), img_match.group(1)))
                            continue
                        # Blockquote line
                        if line.startswith(">> "):
                            content.append({
                                "type": "pullquote",
                                "content": [_make_paragraph(line[3:].strip())],
                            })
                            continue
                        if line.startswith("> "):
                            content.append({
                                "type": "blockquote",
                                "content": [_make_paragraph(line[2:].strip())],
                            })
                            continue
                        # Bullet or plain text
                        bullet_text = None
                        if line.startswith("- "):
                            bullet_text = line[2:].strip()
                        elif line.startswith("* ") or (line.startswith("*") and not line.startswith("**")):
                            bullet_text = (line[2:] if line.startswith("* ") else line[1:]).strip()
                        else:
                            bullet_text = line
                        if bullet_text:
                            content.append(_make_paragraph(bullet_text))

        # Single-line: blockquote or pullquote
        elif text.startswith(">> "):
            content.append({
                "type": "pullquote",
                "content": [_make_paragraph(text[3:].strip())],
            })
        elif text.startswith("> "):
            content.append({
                "type": "blockquote",
                "content": [_make_paragraph(text[2:].strip())],
            })

        # Plain paragraph
        else:
            content.append(_make_paragraph(text))

    return {"type": "doc", "content": content}
