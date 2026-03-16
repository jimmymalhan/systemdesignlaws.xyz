#!/usr/bin/env python3
"""
Batch create/update drafts and PUBLISH (not draft-only).
If article exists (draft or published) → update it. If not → create and publish.
Runs create_draft.py then publish_draft.py for each article.
Shows overall progress bar and uses batch delay to avoid rate limits.

Usage:
  python3 newsletter/scripts/batch_create_and_publish.py
  python3 newsletter/scripts/batch_create_and_publish.py --articles scaling-reads.md,real-time-updates.md
  python3 newsletter/scripts/batch_create_and_publish.py --dry-run
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DRAFTS_DIR = SCRIPT_DIR.parent / "drafts"
REPO_ROOT = SCRIPT_DIR.parent.parent

DEFAULT_ARTICLES = [
    "real-time-updates-for-system-design-interviews.md",
    "dealing-with-contention-for-system-design-interviews.md",
    "multi-step-processes-for-system-design-interviews.md",
    "scaling-reads-for-system-design-interviews.md",
    "scaling-writes-for-system-design-interviews.md",
    "handling-large-blobs-for-system-design-interviews.md",
    "managing-long-running-tasks-for-system-design-interviews.md",
]


def progress_bar(current: int, total: int, prefix: str = "", suffix: str = ""):
    """ASCII progress bar with percentage."""
    if total <= 0:
        return
    pct = current / total * 100
    width = 40
    filled = int(width * current / total)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    print(f"\r  {prefix} |{bar}| {pct:5.1f}% ({current}/{total}) {suffix}", end="", flush=True)
    if current >= total:
        print()


def main():
    parser = argparse.ArgumentParser(description="Batch create/update and publish newsletter articles")
    parser.add_argument("--articles", help="Comma-separated draft filenames")
    parser.add_argument("--dry-run", action="store_true", help="Only create/update drafts, do not publish")
    parser.add_argument("--batch-delay", type=int, default=5, help="Seconds between articles (default: 5)")
    args = parser.parse_args()

    if args.articles:
        filenames = [f.strip() for f in args.articles.split(",") if f.strip()]
    else:
        filenames = DEFAULT_ARTICLES

    paths = []
    for fname in filenames:
        p = DRAFTS_DIR / fname
        if p.exists():
            paths.append(p)
        else:
            print(f"Warning: {fname} not found, skipping")

    if not paths:
        print("No draft files found.")
        sys.exit(1)

    total = len(paths)
    print(f"\nBatch Create & Publish — {total} articles")
    print("=" * 50)
    if args.dry_run:
        print("  [DRY-RUN] Will create/update drafts only (no publish)")
    print()

    results = []
    for idx, draft_path in enumerate(paths, start=1):
        slug = draft_path.stem
        progress_bar(idx - 1, total, "Overall", f"Processing {slug}...")
        print(f"\n[{idx}/{total}] {draft_path.name}")

        # Step 1: create_draft (creates or updates)
        try:
            r = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "create_draft.py"), "--draft", draft_path.name],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
                timeout=300,
            )
            if r.returncode != 0:
                print(f"  FAILED create_draft: {r.stderr[:200] if r.stderr else r.stdout[:200]}")
                results.append({"slug": slug, "status": "FAILED", "stage": "create_draft"})
                continue
        except subprocess.TimeoutExpired:
            print("  FAILED: create_draft timeout")
            results.append({"slug": slug, "status": "FAILED", "stage": "timeout"})
            continue

        # Step 2: publish_draft (unless dry-run)
        if not args.dry_run:
            try:
                r = subprocess.run(
                    [sys.executable, str(SCRIPT_DIR / "publish_draft.py"), "--draft", draft_path.name],
                    capture_output=True,
                    text=True,
                    cwd=str(REPO_ROOT),
                    timeout=120,
                )
                if r.returncode != 0:
                    print(f"  FAILED publish_draft: {r.stderr[:200] if r.stderr else r.stdout[:200]}")
                    results.append({"slug": slug, "status": "DRAFT_OK_PUBLISH_FAILED", "stage": "publish"})
                else:
                    results.append({"slug": slug, "status": "PUBLISHED"})
            except subprocess.TimeoutExpired:
                print("  FAILED: publish_draft timeout")
                results.append({"slug": slug, "status": "FAILED", "stage": "publish_timeout"})
        else:
            results.append({"slug": slug, "status": "DRAFT_UPDATED"})

        if idx < total:
            time.sleep(args.batch_delay)

    progress_bar(total, total, "Overall", "Done")
    print("\n" + "=" * 50)
    n_ok = sum(1 for r in results if r["status"] == "PUBLISHED" or r["status"] == "DRAFT_UPDATED")
    n_fail = len(results) - n_ok
    print(f"Complete: {n_ok} ok, {n_fail} failed")
    sys.exit(1 if n_fail > 0 else 0)


if __name__ == "__main__":
    main()
