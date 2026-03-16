#!/usr/bin/env python3
"""
Create a minimal Substack draft (title + one paragraph) to verify API and format.
Run: python test_minimal_draft.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_draft import load_session

# Minimal payload from Substack/can3p docs - known to work
MINIMAL_BODY = {
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "This is a minimal test. If you see this paragraph, the draft format works."}],
        }
    ],
}


def main():
    from substack import Api

    session = load_session()
    env_path = Path(__file__).parent / ".env"
    publication = None
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "SUBSTACK_PUBLICATION" in line and "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    if k.strip() == "SUBSTACK_PUBLICATION" and v.strip():
                        publication = v.strip().strip('"').strip("'")
                        break

    api = Api(**session) if not publication else Api(publication_url=publication, **session)
    user_id = api.get_user_id()

    payload = {
        "draft_title": "Minimal Test Draft",
        "draft_subtitle": "Verification that Substack API accepts our format.",
        "draft_body": json.dumps(MINIMAL_BODY),
        "draft_bylines": [{"id": int(user_id), "is_guest": False}],
        "audience": "everyone",
        "section_chosen": True,
        "draft_section_id": None,
        "type": "newsletter",
    }

    draft = api.post_draft(payload)
    draft_id = draft.get("id")
    base = str(publication or api.publication_url or "").replace("https://", "").replace("http://", "").split("/")[0]
    edit_url = f"https://{base}/publish/post/{draft_id}"

    print("Minimal draft created.")
    print(f"Edit: {edit_url}")
    print("Open in browser - you should see the paragraph text. If you do, the format works.")


if __name__ == "__main__":
    main()
