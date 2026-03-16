#!/usr/bin/env python3
"""
Fetch curriculum content using session cookies.
Returns full page content as clean text for researcher/writer agents.

Usage:
  python fetch_curriculum.py --path patterns/scaling-reads
  python fetch_curriculum.py --path in-a-hurry/introduction --save research/out.txt

Requires CURRICULUM_BASE_URL in .env (e.g. https://example.com/learn/system-design).
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

COOKIES_PATH = Path(__file__).parent / ".curriculum-cookies.json"
BACKLOG_PATH = Path(__file__).parent.parent / "backlog.json"


def _load_env() -> dict:
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return {}
    out = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def build_url(path: str) -> str:
    """Build full URL from curriculum_path. Base from env."""
    env = _load_env()
    base = env.get("CURRICULUM_BASE_URL", "").rstrip("/")
    if not base:
        print("Error: CURRICULUM_BASE_URL not set in .env", file=sys.stderr)
        sys.exit(1)
    return f"{base}/{path.lstrip('/')}"


def load_cookies() -> dict:
    """Load cookies from JSON file."""
    if not COOKIES_PATH.exists():
        print(f"Error: Cookies file not found at {COOKIES_PATH}", file=sys.stderr)
        print("Add session cookies to this file.", file=sys.stderr)
        sys.exit(1)
    with open(COOKIES_PATH) as f:
        return json.load(f)


def cookies_to_header(cookies: dict) -> str:
    parts = []
    for k, v in cookies.items():
        parts.append(f"{k}={v}")
    return "; ".join(parts)


def fetch_page(url: str) -> str:
    import urllib.request

    cookies = load_cookies()
    cookie_header = cookies_to_header(cookies)
    env = _load_env()
    base = env.get("CURRICULUM_BASE_URL", "").rstrip("/")
    referer = base + "/" if base else ""

    req = urllib.request.Request(url)
    req.add_header("Cookie", cookie_header)
    req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    req.add_header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    if referer:
        req.add_header("Referer", referer)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        if e.code in (401, 403):
            print("Session may be expired. Update cookies in .curriculum-cookies.json", file=sys.stderr)
        sys.exit(1)


def html_to_text(html: str) -> str:
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<header[^>]*>.*?</header>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<h4[^>]*>(.*?)</h4>", r"\n#### \1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<blockquote[^>]*>(.*?)</blockquote>", r"\n> \1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", html)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ").replace("&#x27;", "'")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_article_content(text: str) -> str:
    markers = ["# How to scale", "# What is", "# Introduction", "## The Problem", "## Overview"]
    for marker in markers:
        idx = text.find(marker)
        if idx != -1:
            end_markers = ["Purchase Premium", "Sign up for free", "Ready to practice?", "Mock Interview", "Start practicing", "Common Patterns"]
            end_idx = len(text)
            for em in end_markers:
                eidx = text.find(em, idx + 100)
                if eidx != -1 and eidx < end_idx:
                    end_idx = eidx
            return text[idx:end_idx].strip()
    return text


def main():
    parser = argparse.ArgumentParser(description="Fetch curriculum content by path")
    parser.add_argument("--path", required=True, help="Curriculum path (e.g. patterns/scaling-reads)")
    parser.add_argument("--raw", action="store_true", help="Output raw HTML")
    parser.add_argument("--save", help="Save output to file")
    args = parser.parse_args()

    url = build_url(args.path)
    print(f"Fetching: {url}", file=sys.stderr)
    html = fetch_page(url)

    if args.raw:
        output = html
    else:
        text = html_to_text(html)
        output = extract_article_content(text)

    if args.save:
        Path(args.save).write_text(output)
        print(f"Saved to {args.save}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
