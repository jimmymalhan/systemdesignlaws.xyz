#!/usr/bin/env python3
"""
Update a Substack draft with SEO/tags metadata, then publish.

Usage:
  python publish_draft.py --draft scaling-reads-for-system-design-interviews.md [--no-publish]
  python publish_draft.py --draft-id 190979284 [--no-publish]

With --no-publish: only update draft metadata; do not publish.
"""
import argparse
import json
import sys
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def load_session():
    """Load session from .env or persisted cookies."""
    env_path = Path(__file__).parent / ".env"
    cookies_path = Path(__file__).parent / ".substack-cookies.json"
    if cookies_path.exists():
        return {"cookies_path": str(cookies_path)}
    if not env_path.exists():
        print("No session. Create newsletter/scripts/.env with SUBSTACK_COOKIES")
        sys.exit(1)
    env = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    cookies_str = env.get("SUBSTACK_COOKIES")
    if not cookies_str and env.get("SUBSTACK_SID") and env.get("CONNECT_SID"):
        cookies_str = f"substack.sid={env['SUBSTACK_SID']}; connect.sid={env['CONNECT_SID']}"
    if not cookies_str:
        print("Missing SUBSTACK_COOKIES or SUBSTACK_SID+CONNECT_SID in .env")
        sys.exit(1)
    return {"cookies_string": cookies_str}


def load_article_metadata(slug: str) -> dict:
    """Load metadata from newsletter/docs/article_metadata.json."""
    meta_path = Path(__file__).resolve().parent.parent / "docs" / "article_metadata.json"
    if not meta_path.exists():
        return {}
    data = json.loads(meta_path.read_text())
    return data.get(slug, {})


def main():
    parser = argparse.ArgumentParser(description="Update draft metadata and publish")
    parser.add_argument("--draft", type=str, help="Draft filename (e.g. scaling-reads-for-system-design-interviews.md)")
    parser.add_argument("--draft-id", type=int, help="Substack draft ID (e.g. 190979284)")
    parser.add_argument("--no-publish", action="store_true", help="Only update metadata, do not publish")
    args = parser.parse_args()

    try:
        from substack import Api
    except ImportError:
        print("Install: pip install python-substack")
        sys.exit(1)

    session = load_session()
    publication = None
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "SUBSTACK_PUBLICATION" in line and "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    if k.strip() == "SUBSTACK_PUBLICATION" and v.strip():
                        publication = v.strip().strip('"').strip("'")
                        break

    api = Api(**session) if publication is None else Api(publication_url=publication, **session)

    try:
        api.get_user_id()
    except Exception as e:
        print("Session expired. Paste fresh cookies into newsletter/scripts/.env")
        sys.exit(1)

    # Resolve draft_id
    draft_id = args.draft_id
    slug = None
    if draft_id is None and args.draft:
        slug = Path(args.draft).stem
        published_dir = Path(__file__).resolve().parent.parent / "published"
        pub_file = published_dir / f"{slug}.json"
        if pub_file.exists():
            data = json.loads(pub_file.read_text())
            draft_id = data.get("draft_id")
        else:
            print(f"No published/{slug}.json. Run create_draft.py first or pass --draft-id")
            sys.exit(1)
    elif draft_id is None:
        print("Provide --draft or --draft-id")
        sys.exit(1)

    if slug is None and args.draft:
        slug = Path(args.draft).stem
    elif slug is None:
        slug = str(draft_id)

    meta = load_article_metadata(slug)
    seo = meta.get("seo", {})
    share = meta.get("share", {})

    # Update draft with SEO metadata (Substack PUT accepts partial updates)
    update_payload = {}
    if seo.get("title"):
        update_payload["search_engine_title"] = seo["title"]
    if seo.get("description"):
        update_payload["search_engine_description"] = seo["description"]

    if update_payload:
        try:
            api.put_draft(draft_id, **update_payload)
            print(f"Updated draft {draft_id} with SEO metadata")
            for k, v in update_payload.items():
                print(f"  {k}: {v[:60]}..." if len(str(v)) > 60 else f"  {k}: {v}")
        except Exception as e:
            print(f"Warning: Could not update draft metadata: {e}")
            print("  (SEO can be set manually in Substack editor)")
    else:
        print("No SEO metadata in article_metadata.json for this slug")

    # Tags: Substack API may not expose tags for drafts. Print manual steps.
    tags = meta.get("tags", [])
    if tags:
        print("\nTags (add manually in Substack editor):")
        for t in tags:
            print(f"  - {t}")
        print("  Edit: Settings sidebar > Tags > Add tags")

    base = str(publication or getattr(api, "publication_url", "https://jimmymalhan.substack.com")).replace("https://", "").replace("http://", "").split("/")[0]
    edit_url = f"https://{base}/publish/post/{draft_id}"
    print(f"\nEdit URL: {edit_url}")

    if args.no_publish:
        print("\nSkipped publish (--no-publish). Open edit URL to add tags and publish manually.")
        return

    send = share.get("send_email", True)
    share_auto = share.get("share_automatically", False)
    print(f"\nPublishing (send_email={send}, share_automatically={share_auto})...")
    try:
        result = api.publish_draft(draft_id, send=send, share_automatically=share_auto)
        print("Published successfully!")
        if isinstance(result, dict) and result.get("slug"):
            pub_slug = result["slug"]
            pub_url = f"https://{base}/p/{pub_slug}"
            print(f"Post URL: {pub_url}")
    except Exception as e:
        print(f"Publish failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
