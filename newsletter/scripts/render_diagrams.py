#!/usr/bin/env python3
"""
Render diagram panels from HTML to PNG images using Playwright.
Uploads rendered images to Substack and returns URLs for embedding.

Usage:
  python render_diagrams.py newsletter/plots/scaling-reads.html
  python render_diagrams.py newsletter/plots/scaling-reads.html --panels 0,1,2,3,4,5,6,7,8
  python render_diagrams.py newsletter/plots/scaling-reads.html --upload
"""
import argparse
import json
import sys
from pathlib import Path


def render_panels(html_path: str, panel_indices: list = None, output_dir: str = None) -> list:
    """Render each panel from a tabbed HTML diagram to separate PNG images."""
    from playwright.sync_api import sync_playwright

    html_path = Path(html_path).resolve()
    if not html_path.exists():
        print(f"Error: {html_path} not found")
        sys.exit(1)

    if output_dir is None:
        output_dir = html_path.parent / "rendered"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    stem = html_path.stem
    images = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(1000)  # Let animations start

        # Count panels
        panel_count = page.evaluate("document.querySelectorAll('.panel').length")
        if panel_count == 0:
            # No panels - screenshot the whole page
            out = output_dir / f"{stem}.png"
            page.screenshot(path=str(out), full_page=True)
            images.append(str(out))
            print(f"Rendered: {out}")
        else:
            indices = panel_indices or list(range(panel_count))
            for i in indices:
                if i >= panel_count:
                    continue
                # Click the tab to show the panel
                page.evaluate(f"showPanel({i})")
                page.wait_for_timeout(500)  # Let animations settle

                # Get panel element and screenshot just that region
                panel = page.query_selector(f"#p{i}")
                if panel:
                    out = output_dir / f"{stem}-{i}.png"
                    # Screenshot the content area (panel + some padding)
                    panel.screenshot(path=str(out))
                    images.append(str(out))
                    print(f"Rendered panel {i}: {out}")

        browser.close()

    return images


def upload_to_substack(image_paths: list) -> list:
    """Upload images to Substack, return hosted URLs."""
    sys.path.insert(0, str(Path(__file__).parent))
    from create_draft import load_session, get_publication_from_env
    from substack import Api

    session = load_session()
    env_path = Path(__file__).parent / ".env"
    pub = get_publication_from_env(env_path) if env_path.exists() else None
    api = Api(publication_url=pub, **session) if pub else Api(**session)

    urls = []
    for img_path in image_paths:
        try:
            result = api.get_image(img_path)
            url = result.get("url", result) if isinstance(result, dict) else str(result)
            urls.append(url)
            print(f"Uploaded: {Path(img_path).name} -> {url}")
        except Exception as e:
            print(f"Upload failed for {img_path}: {e}")
            urls.append(None)
    return urls


def main():
    parser = argparse.ArgumentParser(description="Render HTML diagram panels to PNG")
    parser.add_argument("html", help="Path to HTML diagram file")
    parser.add_argument("--panels", help="Comma-separated panel indices (default: all)")
    parser.add_argument("--output", help="Output directory for PNGs")
    parser.add_argument("--upload", action="store_true", help="Upload to Substack")
    args = parser.parse_args()

    panels = [int(x) for x in args.panels.split(",")] if args.panels else None
    images = render_panels(args.html, panels, args.output)

    if args.upload and images:
        urls = upload_to_substack(images)
        # Write manifest
        manifest = []
        for img, url in zip(images, urls):
            manifest.append({"file": img, "url": url})
        manifest_path = Path(images[0]).parent / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"\nManifest: {manifest_path}")
    elif images:
        print(f"\n{len(images)} images rendered. Use --upload to push to Substack.")


if __name__ == "__main__":
    main()
