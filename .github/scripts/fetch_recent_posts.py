#!/usr/bin/env python3
"""Fetch latest 3 posts from Substack RSS and write recent-posts.json."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import xml.etree.ElementTree as ET

RSS_PATH = Path("feed.xml")
OUTPUT_PATH = Path("recent-posts.json")
LIMIT = 3
DESC_MAX_LEN = 140


def strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def get_text(element) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def parse_rss_to_posts(rss_path: Path, limit: int = LIMIT, desc_max: int = DESC_MAX_LEN) -> list:
    """Parse RSS XML and return list of post dicts (title, url, description)."""
    tree = ET.parse(rss_path)
    root = tree.getroot()
    items = root.findall(".//item")[:limit]
    posts = []
    for item in items:
        title = get_text(item.find("title"))
        link_el = item.find("link")
        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        desc_raw = get_text(item.find("description"))
        desc = strip_html(desc_raw)
        if len(desc) > desc_max:
            desc = desc[: desc_max - 3].rsplit(" ", 1)[0] + "..."
        if title and link:
            url = link.replace("systemdesignlaws.substack.com", "newsletter.systemdesignlaws.xyz")
            posts.append({"title": title, "url": url, "description": desc or "Read more."})
    return posts


def main():
    posts = parse_rss_to_posts(RSS_PATH)
    output = {
        "posts": posts,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote {len(posts)} posts to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
