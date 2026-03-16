#!/usr/bin/env python3
"""Delete all Substack drafts. Uses same session as create_draft.py.

CRITICAL: This deletes DRAFTS only. NEVER delete posted/published articles.
Requires --yes to confirm. Do NOT run as part of automated workflows.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from create_draft import load_session, get_publication_from_env


def main():
    parser = argparse.ArgumentParser(description="Delete Substack drafts only (never posted articles)")
    parser.add_argument("--yes", action="store_true", help="Confirm deletion (required)")
    args = parser.parse_args()

    if not args.yes:
        print("Refusing to run without --yes. This deletes drafts only, never posted articles.")
        sys.exit(1)
    try:
        from substack import Api
    except ImportError:
        print("Install: pip install python-substack")
        sys.exit(1)

    try:
        session = load_session()
    except SystemExit:
        raise

    env_path = Path(__file__).parent / ".env"
    publication = get_publication_from_env(env_path) if env_path.exists() else None

    api = Api(**session) if not publication else Api(publication_url=publication, **session)

    drafts = api.get_drafts()
    count = len(drafts) if isinstance(drafts, list) else 0

    if count == 0:
        print("No drafts to delete.")
        return

    for d in drafts:
        did = d.get("id")
        title = d.get("title", "untitled")
        api.delete_draft(did)
        print(f"Deleted: {title} (id={did})")

    print(f"Deleted {count} draft(s).")


if __name__ == "__main__":
    main()
