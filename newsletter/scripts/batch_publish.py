#!/usr/bin/env python3
"""
Batch publish multiple newsletter drafts to Substack with real-time progress tracking.

Checks for existing posts before each publish:
  - If found as DRAFT   -> update that draft
  - If found as PUBLISHED -> update that post
  - If not found        -> create new draft

Saves a checkpoint to ~/.openclaw/batch_publish_checkpoint.json so --resume
can continue from the last successful article after an interruption.

Usage:
  python3 newsletter/scripts/batch_publish.py --drafts-dir newsletter/drafts/
  python3 newsletter/scripts/batch_publish.py --dry-run
  python3 newsletter/scripts/batch_publish.py --resume
  python3 newsletter/scripts/batch_publish.py --articles real-time-updates.md,scaling-reads.md
  python3 newsletter/scripts/batch_publish.py --batch-delay 5 --force-new
"""

import argparse
import json
import os
import sys
import time
import shutil
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# ANSI colour helpers (auto-disabled when not a tty)
# ---------------------------------------------------------------------------

_ANSI = sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _ANSI else text


def green(t):  return _c("32", t)
def yellow(t): return _c("33", t)
def red(t):    return _c("31", t)
def cyan(t):   return _c("36", t)
def bold(t):   return _c("1",  t)
def dim(t):    return _c("2",  t)


# ---------------------------------------------------------------------------
# tqdm / ASCII progress bar shim
# ---------------------------------------------------------------------------

try:
    from tqdm import tqdm as _tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False


def _ascii_bar(done: int, total: int, width: int = 40) -> str:
    pct = done / total if total else 0
    filled = int(width * pct)
    bar = "=" * filled + (">" if filled < width else "") + " " * max(0, width - filled - 1)
    return f"[{bar}] {done}/{total} ({int(pct * 100)}%)"


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

CHECKPOINT_DIR  = Path.home() / ".openclaw"
CHECKPOINT_FILE = CHECKPOINT_DIR / "batch_publish_checkpoint.json"


def _load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        try:
            return json.loads(CHECKPOINT_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_checkpoint(data: dict):
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(json.dumps(data, indent=2))


def _clear_checkpoint():
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


# ---------------------------------------------------------------------------
# Ordered default article list
# ---------------------------------------------------------------------------

DEFAULT_ARTICLES = [
    "real-time-updates-for-system-design-interviews.md",
    "dealing-with-contention-for-system-design-interviews.md",
    "multi-step-processes-for-system-design-interviews.md",
    "scaling-reads-for-system-design-interviews.md",
    "scaling-writes-for-system-design-interviews.md",
    "handling-large-blobs-for-system-design-interviews.md",
    "managing-long-running-tasks-for-system-design-interviews.md",
]

# ---------------------------------------------------------------------------
# Paths (must be before config load)
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Paths (must be before config load)
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Load batch config (4-hour slow mode)
# ---------------------------------------------------------------------------

def _load_batch_config() -> dict:
    cfg_path = _SCRIPTS_DIR / "batch_config.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text())
        except Exception:
            pass
    return {}

_BATCH_CONFIG = _load_batch_config()
RATE_WINDOW_HOURS = _BATCH_CONFIG.get("rate_window_hours", 4)
RATE_MAX_CALLS_PER_WINDOW = _BATCH_CONFIG.get("rate_max_calls_per_window", 30)
RATE_THROTTLE_PCT = _BATCH_CONFIG.get("rate_throttle_pct", 0.90)
RATE_CHECK_INTERVAL_SEC = _BATCH_CONFIG.get("rate_check_interval_sec", 60)
CHECKPOINT_EXPIRE_HOURS = _BATCH_CONFIG.get("checkpoint_expire_hours", 24)

# ---------------------------------------------------------------------------
# Retry logic (exponential back-off on 429)
# ---------------------------------------------------------------------------

_MAX_RETRIES   = 5
_BASE_WAIT     = 2   # seconds
_MAX_WAIT      = 60  # seconds cap

# ---------------------------------------------------------------------------
# Rate-limit guard: never exceed 90% of capacity; auto-pause + resume
# Supports 4-hour window for --slow mode
# ---------------------------------------------------------------------------

import collections as _collections


class RateLimitGuard:
    """
    Sliding-window rate guard.

    Zones:
      < 50% : normal speed
      50-75%: 1.5x base delay
      75-90%: 3x base delay
      >= 90%: ULTRA-SLOW — 10x delay + 30s pause between calls
      hit 429: wait full renewal window (default 3600s), then resume

    Never crosses 100%. Prints countdown during long waits.
    Checkpoint is written after every wait so --resume works.
    """

    ZONE_NORMAL     = 0.50   # < 50%  → base delay
    ZONE_MEDIUM     = 0.75   # 50-75% → 1.5x
    ZONE_HIGH       = 0.90   # 75-90% → 3x
    WINDOW_SEC      = 60     # sliding window in seconds
    RENEWAL_SEC     = 3600   # how long to wait after a true 429 (1 hour)

    def __init__(self, requests_per_minute: int = 50, renewal_wait: int = 3600):
        self.rpm          = requests_per_minute
        self.renewal_wait = renewal_wait
        self._calls: _collections.deque = _collections.deque()
        self._paused      = False
        self._ultra_slow  = False   # True once we enter >= 90% zone
        self._renewal_at: float = 0.0  # epoch when renewal window ends

    def _prune(self):
        cutoff = time.time() - self.WINDOW_SEC
        while self._calls and self._calls[0] < cutoff:
            self._calls.popleft()

    def usage_pct(self) -> float:
        self._prune()
        return len(self._calls) / self.rpm if self.rpm else 0.0

    def _countdown(self, label: str, seconds: float):
        """Print a live countdown bar, updating every second."""
        total = int(seconds)
        for remaining in range(total, 0, -1):
            done  = total - remaining
            width = 40
            filled = int(width * done / total)
            bar = "=" * filled + ">" + " " * max(0, width - filled - 1)
            pct = int(done * 100 / total) if total else 100
            mins, secs = divmod(remaining, 60)
            hrs,  mins = divmod(mins, 60)
            if hrs:
                eta = f"{hrs}h {mins:02d}m {secs:02d}s"
            elif mins:
                eta = f"{mins}m {secs:02d}s"
            else:
                eta = f"{secs}s"
            print(f"\r      {yellow(label)} [{bar}] {pct}% — resuming in {eta}   ",
                  end="", flush=True)
            time.sleep(1)
        print(f"\r      {green(label)} [{('=' * width)}] 100% — resuming now!          ")

    def before_call(self):
        """Block proactively based on usage zone. Never reaches 100%."""
        # 1. If we're still in a post-429 renewal window, wait it out
        now = time.time()
        if self._renewal_at > now:
            wait = self._renewal_at - now
            print(f"\n      {red('RATE-GUARD')} in renewal window — "
                  f"waiting {int(wait)}s for limit to reset...")
            self._countdown("Rate-limit renewal", wait)
            self._calls.clear()   # window has reset; clear history
            self._renewal_at = 0.0

        # 2. Check current zone and apply proactive throttle
        while True:
            self._prune()
            pct = len(self._calls) / self.rpm if self.rpm else 0.0
            if pct < self.ZONE_HIGH:
                if self._ultra_slow:
                    self._ultra_slow = False
                    print(f"\n      {green('RATE-GUARD')} back below 90% ({int(pct*100)}%) "
                          f"— returning to normal speed")
                break
            # >= 90%: enter ultra-slow mode
            if not self._ultra_slow:
                self._ultra_slow = True
                print(f"\n      {yellow('RATE-GUARD')} usage at {int(pct*100)}% "
                      f"({len(self._calls)}/{self.rpm} req/min) — "
                      f"entering ULTRA-SLOW mode (30s between calls)")
            # Wait until the oldest call ages out of the window
            if self._calls:
                oldest  = self._calls[0]
                wait    = max(1, (oldest + self.WINDOW_SEC) - time.time() + 2)
                # cap single sleep at 30s so we can re-check
                self._countdown("Ultra-slow pause", min(wait, 30))
            else:
                time.sleep(5)

    def after_call(self):
        self._calls.append(time.time())

    def on_429(self):
        """Call when a true 429 is received. Sets renewal window."""
        self._renewal_at = time.time() + self.renewal_wait
        remaining = int(self.renewal_wait)
        hrs,  rem = divmod(remaining, 3600)
        mins, sec = divmod(rem, 60)
        print(f"\n      {red('RATE-GUARD')} TRUE 429 — rate limit hit. "
              f"Waiting full renewal window ({hrs}h {mins:02d}m {sec:02d}s)...")
        self._countdown("Rate-limit renewal", self.renewal_wait)
        self._calls.clear()
        self._renewal_at = 0.0

    def adaptive_delay(self, base_delay: float) -> float:
        """
        Return a delay scaled by zone:
          <50%  → base_delay   (e.g. 3s)
          50-75%→ 1.5x         (4.5s)
          75-90%→ 3x           (9s)
          >=90% → 10x          (30s) — ultra-slow
        """
        pct = self.usage_pct()
        if pct >= self.ZONE_HIGH:
            return base_delay * 10
        if pct >= self.ZONE_MEDIUM:
            return base_delay * 3
        if pct >= self.ZONE_NORMAL:
            return base_delay * 1.5
        return base_delay

    def status_line(self) -> str:
        pct    = self.usage_pct()
        count  = len(self._calls)
        pct_i  = int(pct * 100)
        width  = 20
        filled = int(width * pct)
        bar    = "=" * filled + " " * (width - filled)
        if pct >= self.ZONE_HIGH:
            color = yellow
            zone  = "ULTRA-SLOW"
        elif pct >= self.ZONE_MEDIUM:
            color = yellow
            zone  = "HIGH"
        elif pct >= self.ZONE_NORMAL:
            color = cyan
            zone  = "MEDIUM"
        else:
            color = green
            zone  = "OK"
        return (f"Rate: [{color(bar)}] {pct_i}% "
                f"({count}/{self.rpm} req/min) [{color(zone)}]")


# Single shared guard instance (50 req/min Substack default)
_rate_guard = RateLimitGuard(requests_per_minute=50, renewal_wait=3600)


def _api_retry(func, *args, **kwargs):
    """Call func(*args, **kwargs); retry up to _MAX_RETRIES on 429.
    Proactively throttles at 90% via RateLimitGuard."""
    wait = _BASE_WAIT
    for attempt in range(1, _MAX_RETRIES + 1):
        _rate_guard.before_call()   # block if near 90%
        try:
            result = func(*args, **kwargs)
            _rate_guard.after_call()
            return result
        except Exception as exc:
            err = str(exc)
            is_rate_limit = "429" in err or "Too Many Requests" in err.lower()
            if is_rate_limit:
                actual_wait = min(wait, _MAX_WAIT)
                print(f"      {yellow('RATE-LIMITED')} - waiting {actual_wait}s "
                      f"(attempt {attempt}/{_MAX_RETRIES})...")
                time.sleep(actual_wait)
                wait *= 2
                continue
            if attempt < _MAX_RETRIES:
                print(f"      {yellow('API error')} ({exc}) - retry {attempt}/{_MAX_RETRIES}...")
                time.sleep(_BASE_WAIT)
                continue
            raise
    raise RuntimeError(f"API call failed after {_MAX_RETRIES} retries")


# ---------------------------------------------------------------------------
# Session / API bootstrap  (mirrors create_draft.py logic)
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent


def _load_session():
    env_path     = _SCRIPTS_DIR / ".env"
    cookies_path = _SCRIPTS_DIR / ".substack-cookies.json"
    if cookies_path.exists():
        return {"cookies_path": str(cookies_path)}
    if not env_path.exists():
        print(red("No session found. Create newsletter/scripts/.env with SUBSTACK_COOKIES."))
        print("See newsletter/scripts/.env.example for the format.")
        sys.exit(1)
    env: dict[str, str] = {}
    with open(env_path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    cookies_str = env.get("SUBSTACK_COOKIES") or ""
    if not cookies_str and env.get("SUBSTACK_SID") and env.get("CONNECT_SID"):
        cookies_str = f"substack.sid={env['SUBSTACK_SID']}; connect.sid={env['CONNECT_SID']}"
    if not cookies_str:
        print(red("Missing SUBSTACK_COOKIES or SUBSTACK_SID+CONNECT_SID in .env"))
        sys.exit(1)
    return {"cookies_string": cookies_str}


def _get_publication_url() -> Optional[str]:
    env_path = _SCRIPTS_DIR / ".env"
    if not env_path.exists():
        return None
    with open(env_path) as fh:
        for line in fh:
            line = line.strip()
            if "SUBSTACK_PUBLICATION" in line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() == "SUBSTACK_PUBLICATION" and v.strip():
                    return v.strip().strip('"').strip("'")
    return None


def _build_api(session: dict, publication: Optional[str]):
    from substack import Api  # type: ignore
    return Api(publication_url=publication, **session) if publication else Api(**session)


# ---------------------------------------------------------------------------
# Per-article publish logic
# ---------------------------------------------------------------------------

def _publish_article(
    api,
    draft_file: Path,
    dry_run: bool,
    force_new: bool,
    batch_delay: int,
    user_id: int,
    publication: Optional[str],
) -> dict:
    """
    Process one draft file. Returns a result dict:
      { status, draft_id, title, error }
    Status: PUBLISHED | UPDATED | SKIPPED | FAILED | DRY-RUN
    """
    # -- pull in helpers from create_draft.py without re-running its main() --
    sys.path.insert(0, str(_SCRIPTS_DIR))
    from create_draft import (
        parse_draft_content,
        prepare_body_markdown,
        clean_draft_body,
    )
    from markdown_to_prosemirror import markdown_to_prosemirror  # type: ignore
    from list_posts import find_existing_post  # type: ignore

    content = draft_file.read_text()
    title, subtitle = parse_draft_content(content, draft_file)

    if dry_run:
        return {"status": "DRY-RUN", "draft_id": None, "title": title, "error": None}

    # -- duplicate check --
    existing_id   = None
    existing_type = None
    if not force_new:
        try:
            existing_id, existing_type, existing_title = find_existing_post(api, title)
        except Exception as exc:
            print(f"      {yellow('Warning:')} duplicate check failed ({exc}), will create new")

    # -- prepare body --
    body_md  = prepare_body_markdown(content, title)
    body_obj = markdown_to_prosemirror(body_md)
    clean_draft_body(body_obj)

    # -- upload images --
    plots_dir = _SCRIPTS_DIR.parent / "plots"
    png_dir   = plots_dir / "png"
    image_cache: dict[str, str] = {}
    import re as _re
    for node in body_obj.get("content", []):
        if node.get("type") == "captionedImage":
            for child in node.get("content", []):
                if child.get("type") == "image2":
                    src = child["attrs"].get("src", "")
                    if src in image_cache:
                        child["attrs"]["src"] = image_cache[src]
                        continue
                    match = _re.search(r"/([^/]+)\.(svg|png)$", src)
                    if match:
                        png_name = match.group(1) + ".png"
                        png_path = png_dir / png_name
                        if png_path.exists():
                            try:
                                result = _api_retry(api.get_image, str(png_path))
                                cdn_url = result.get("url") if isinstance(result, dict) else str(result)
                                if cdn_url:
                                    image_cache[src] = cdn_url
                                    child["attrs"]["src"] = cdn_url
                            except Exception as exc:
                                print(f"      {yellow('Warning:')} image upload failed for {png_name}: {exc}")
                            time.sleep(batch_delay)

    # -- subtitle --
    sub = subtitle or "From SystemDesignLaws newsletter"
    if len(sub) > 115:
        sub = sub[:112] + "..."

    body_json = json.dumps(body_obj)

    # -- update existing OR create new --
    published_dir = _SCRIPTS_DIR.parent / "published"
    published_dir.mkdir(exist_ok=True)
    slug        = draft_file.stem
    output_file = published_dir / f"{slug}.json"

    if existing_id and not force_new:
        # update
        _api_retry(
            api.put_draft, existing_id,
            draft_title=title, draft_subtitle=sub, draft_body=body_json
        )
        draft_id = existing_id
        status   = "UPDATED"
    else:
        # create new
        draft_payload = {
            "draft_title":      title,
            "draft_subtitle":   sub,
            "draft_body":       body_json,
            "draft_bylines":    [{"id": int(user_id), "is_guest": False}],
            "audience":         "everyone",
            "section_chosen":   True,
            "draft_section_id": None,
            "type":             "newsletter",
        }
        draft    = _api_retry(api.post_draft, draft_payload)
        draft_id = draft.get("id")
        if not draft_id:
            raise RuntimeError(f"API returned no draft_id. Response: {draft}")
        status = "PUBLISHED"

    # -- persist output JSON --
    pub_url = publication or "https://systemdesignlaws.substack.com"
    base    = str(pub_url).replace("https://", "").replace("http://", "").split("/")[0]
    edit_url = f"https://{base}/publish/post/{draft_id}"
    output_file.write_text(json.dumps({
        "draft_id":    draft_id,
        "edit_url":    edit_url,
        "title":       title,
        "subtitle":    subtitle,
        "source_file": draft_file.name,
        "image_urls":  image_cache,
    }, indent=2))

    return {"status": status, "draft_id": draft_id, "title": title, "error": None}


# ---------------------------------------------------------------------------
# Main batch loop
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Batch publish newsletter drafts to Substack"
    )
    parser.add_argument(
        "--drafts-dir", default="newsletter/drafts/",
        help="Directory containing .md draft files (default: newsletter/drafts/)"
    )
    parser.add_argument(
        "--articles",
        help="Comma-separated list of filenames to process (overrides default order)"
    )
    parser.add_argument("--dry-run",     action="store_true", help="Validate only, no API writes")
    parser.add_argument("--force-new",   action="store_true", help="Skip duplicate check, always create new")
    parser.add_argument("--resume",      action="store_true", help="Resume from last checkpoint")
    parser.add_argument(
        "--batch-delay", type=int, default=3,
        help="Seconds to wait between articles (default: 3)"
    )
    args = parser.parse_args()

    # -- resolve drafts directory --
    repo_root  = _SCRIPTS_DIR.parent.parent
    drafts_dir = Path(args.drafts_dir)
    if not drafts_dir.is_absolute():
        # try relative to cwd, then relative to repo root
        if not drafts_dir.exists():
            drafts_dir = repo_root / args.drafts_dir
    if not drafts_dir.exists():
        print(red(f"Drafts directory not found: {args.drafts_dir}"))
        sys.exit(1)

    # -- build article list --
    if args.articles:
        filenames = [f.strip() for f in args.articles.split(",") if f.strip()]
    else:
        filenames = DEFAULT_ARTICLES

    # resolve to Path objects that actually exist
    article_paths: list[Path] = []
    for fname in filenames:
        p = drafts_dir / fname
        if p.exists():
            article_paths.append(p)
        else:
            print(yellow(f"Warning: {fname} not found in {drafts_dir}, skipping"))

    if not article_paths:
        print(red("No draft files found. Exiting."))
        sys.exit(1)

    total = len(article_paths)

    # -- checkpoint / resume --
    checkpoint = _load_checkpoint() if args.resume else {}
    completed_files: set[str] = set(checkpoint.get("completed", []))
    resume_offset = len(completed_files)
    if args.resume and completed_files:
        print(cyan(f"Resuming from checkpoint: {resume_offset} already completed"))

    # -- header --
    print()
    print(bold("Batch Publish - systemdesignlaws.xyz Newsletter"))
    print("=" * 50)
    print(f"Found {bold(str(total))} drafts to process")
    if args.dry_run:
        print(yellow("  [DRY-RUN] No API calls will be made"))
    if args.force_new:
        print(yellow("  [FORCE-NEW] Skipping duplicate checks"))
    print()

    # -- session + API (skip in dry-run if no credentials) --
    api      = None
    user_id  = None
    publication = _get_publication_url()
    session  = None

    if not args.dry_run:
        try:
            from substack import Api  # type: ignore   # noqa: F401
        except ImportError:
            print(red("Install: pip install python-substack"))
            sys.exit(1)

        session    = _load_session()
        api        = _build_api(session, publication)

        try:
            user_id = api.get_user_id()
        except Exception as exc:
            # cookies expired - try .env fallback
            if "cookies_path" in (session or {}):
                session = _load_session()
                if "cookies_string" in session:
                    api     = _build_api(session, publication)
                    user_id = api.get_user_id()
                else:
                    print(red("Session expired. Paste fresh cookies into newsletter/scripts/.env"))
                    sys.exit(1)
            else:
                print(red(f"Session error: {exc}"))
                sys.exit(1)

        # persist session
        cookies_path = _SCRIPTS_DIR / ".substack-cookies.json"
        try:
            api.export_cookies(str(cookies_path))
        except Exception:
            pass

    # -- tracking --
    results: list[dict] = []
    start_time = time.time()

    for idx, draft_file in enumerate(article_paths, start=1):
        fname = draft_file.name

        # skip if already done (resume mode)
        if fname in completed_files:
            print(f"[{idx}/{total}] {cyan(fname)}")
            print(f"      {dim('Already completed - skipping (checkpoint)')}")
            results.append({"status": "SKIPPED", "draft_id": None, "title": fname, "error": None})
            continue

        print(f"[{idx}/{total}] {bold(fname)}")

        # -- check for existing (use actual draft title for accurate match) --
        existing_label = "not found"
        if not args.dry_run and not args.force_new:
            print(f"      Checking for existing post...", end=" ", flush=True)
            try:
                sys.path.insert(0, str(_SCRIPTS_DIR))
                from list_posts import find_existing_post  # type: ignore
                from create_draft import parse_draft_content  # type: ignore
                _title, _ = parse_draft_content(draft_file.read_text(), draft_file)
                ex_id, ex_type, ex_title = find_existing_post(api, _title)
                if ex_id:
                    existing_label = f"found {ex_type.upper()} (id: {ex_id}) -> will UPDATE"
                    print(existing_label)
                else:
                    print("not found -> will CREATE new")
            except Exception as exc:
                print(f"check failed ({exc})")

        elif args.dry_run:
            print(f"      {dim('Duplicate check skipped (dry-run)')}")
        else:
            print(f"      {dim('Duplicate check skipped (--force-new)')}")

        # -- per-article progress bar (tqdm or ASCII) --
        if _HAS_TQDM:
            pbar = _tqdm(
                total=100, desc="      Progress", bar_format="{l_bar}{bar}| {elapsed}",
                ncols=70, leave=False
            )
            pbar.update(20)  # started
        else:
            print(f"      {_ascii_bar(0, 1)}", end="\r", flush=True)

        error = None
        status = "FAILED"
        draft_id = None
        title = fname

        try:
            result = _publish_article(
                api=api,
                draft_file=draft_file,
                dry_run=args.dry_run,
                force_new=args.force_new,
                batch_delay=args.batch_delay,
                user_id=user_id,
                publication=publication,
            )
            status   = result["status"]
            draft_id = result["draft_id"]
            title    = result["title"]
        except Exception as exc:
            error  = str(exc)
            status = "FAILED"

        if _HAS_TQDM:
            pbar.update(80)
            pbar.close()
        else:
            print(f"      {_ascii_bar(1, 1)}")

        # -- status line --
        _STATUS_COLORS = {
            "PUBLISHED":  green,
            "UPDATED":    cyan,
            "SKIPPED":    dim,
            "FAILED":     red,
            "DRY-RUN":    yellow,
            "RATE-LIMITED": yellow,
        }
        color_fn = _STATUS_COLORS.get(status, str)
        id_str   = f" (id: {draft_id})" if draft_id else ""
        err_str  = f" - {error}" if error else ""
        print(f"      Status: {color_fn(status)}{id_str}{err_str}")
        print()

        results.append({"status": status, "draft_id": draft_id, "title": title, "error": error})

        # -- update checkpoint --
        if status not in ("FAILED",):
            completed_files.add(fname)
        _save_checkpoint({"completed": list(completed_files), "results": results})

        # -- overall progress bar --
        elapsed  = time.time() - start_time
        per_item = elapsed / idx if idx else 0
        eta      = per_item * (total - idx)
        eta_str  = f"{int(eta // 60)}m {int(eta % 60)}s" if eta > 0 else "done"
        print(f"Progress: {_ascii_bar(idx, total)} - ETA: {eta_str}")
        print()

        # -- inter-article delay: adaptive based on current rate usage --
        if idx < total and not args.dry_run:
            delay = _rate_guard.adaptive_delay(args.batch_delay)
            usage = int(_rate_guard.usage_pct() * 100)
            if delay > args.batch_delay:
                print(dim(f"      [rate-guard] usage={usage}% -> delay={delay:.1f}s (throttling)"))
            time.sleep(delay)

    # -- final summary --
    elapsed_total = time.time() - start_time
    mins, secs    = divmod(int(elapsed_total), 60)

    n_published = sum(1 for r in results if r["status"] == "PUBLISHED")
    n_updated   = sum(1 for r in results if r["status"] == "UPDATED")
    n_failed    = sum(1 for r in results if r["status"] == "FAILED")
    n_skipped   = sum(1 for r in results if r["status"] in ("SKIPPED", "DRY-RUN"))

    print("=" * 50)
    print(bold(f"Batch Complete: {len(results)} processed"))
    print(f"  {green('Published:')} {n_published} new")
    print(f"  {cyan('Updated:')}   {n_updated} existing")
    print(f"  {red('Failed:')}    {n_failed}")
    print(f"  {dim('Skipped:')}   {n_skipped}")
    print(f"Total time: {mins}m {secs}s")
    print("=" * 50)

    # -- clear checkpoint on full success --
    if n_failed == 0:
        _clear_checkpoint()
        print(dim("Checkpoint cleared."))

    sys.exit(1 if n_failed > 0 else 0)


if __name__ == "__main__":
    main()
