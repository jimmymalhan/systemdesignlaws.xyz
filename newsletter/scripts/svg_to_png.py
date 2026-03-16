#!/usr/bin/env python3
"""
Convert SVG diagrams to PNG for Substack upload.
Uses Playwright to render SVG at 2x scale for crisp output.

Usage:
  python svg_to_png.py                          # Convert all SVGs in plots/svg/
  python svg_to_png.py composite-index           # Convert single file
"""
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PLOTS_DIR = SCRIPT_DIR.parent / "plots"
SVG_DIR = PLOTS_DIR / "svg"
PNG_DIR = PLOTS_DIR / "png"


def svg_to_png(svg_path: Path, png_path: Path, scale: int = 2) -> bool:
    """Render SVG to PNG using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install playwright: pip install playwright && playwright install chromium")
        return False

    svg_path = svg_path.resolve()
    if not svg_path.exists():
        print(f"Not found: {svg_path}")
        return False

    png_path.parent.mkdir(parents=True, exist_ok=True)

    # Read SVG: prefer width/height (display size) over viewBox (content bounds)
    content = svg_path.read_text()
    import re
    wh = re.search(r'\swidth="(\d+(?:\.\d+)?)"\s+height="(\d+(?:\.\d+)?)"', content)
    if wh:
        w, h = float(wh.group(1)), float(wh.group(2))
    else:
        vb = re.search(r'viewBox="[^"]*\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)"', content)
        if vb:
            w, h = float(vb.group(1)), float(vb.group(2))
        else:
            w, h = 960, 500
    w, h = int(w * scale), int(h * scale)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto(f"file://{svg_path}")
        page.wait_for_timeout(300)
        page.screenshot(path=str(png_path))
        browser.close()

    return True


def main():
    parser = argparse.ArgumentParser(description="Convert SVG diagrams to PNG")
    parser.add_argument("name", nargs="?", help="Single SVG stem (e.g. composite-index) or all if omitted")
    parser.add_argument("--scale", type=int, default=2, help="Scale factor (default 2)")
    args = parser.parse_args()

    if not SVG_DIR.exists():
        print(f"SVG dir not found: {SVG_DIR}")
        sys.exit(1)

    if args.name:
        svg = SVG_DIR / f"{args.name}.svg"
        if not svg.exists():
            print(f"Not found: {svg}")
            sys.exit(1)
        files = [svg]
    else:
        files = sorted(SVG_DIR.glob("*.svg"))

    count = 0
    for svg_path in files:
        stem = svg_path.stem
        png_path = PNG_DIR / f"{stem}.png"
        if svg_to_png(svg_path, png_path, args.scale):
            print(f"Converted: {stem}.svg -> {stem}.png")
            count += 1

    print(f"Done. {count} PNG(s) in {PNG_DIR}")


if __name__ == "__main__":
    main()
