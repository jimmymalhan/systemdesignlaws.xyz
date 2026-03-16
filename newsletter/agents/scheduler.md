# Newsletter Scheduler Agent

Pushes verified drafts to Substack and publishes immediately. No drafts left visible.

## Core Rules (ENFORCED AT EVERY STEP)

- **Never delete published articles.** Always edit. If article exists, update it. Never create duplicates.
- **Publish immediately.** Create draft then publish in one flow. No lingering Substack drafts.
- **Original content only:** Curriculum topics. No external attribution.
- **Anti-duplicate:** Always check `list_posts.py --search` before creating. Edit existing, never create duplicates.
- **Progress bars:** All batch operations must show real-time ASCII progress bars (current/total, percentage, filename).
- **Adaptive rate limiting:** Slow at 70% capacity (3x delay), 90% (5x delay), 95% (heavy pause). NEVER hit 100%. Checkpoint/resume on failure. All API calls use `api_call_with_retry()` with `AdaptiveRateLimiter`.
- **Batch image uploads:** Use `--batch-delay` (default 2s). Resume from last checkpoint on failure.

## Process

1. Receive verified draft path from Verifier/Orchestrator
2. Validate the draft passes structure tests
3. Push to Substack using `create_draft.py`
4. Report the edit URL back to Orchestrator
5. Orchestrator updates `backlog.json` status to `published`

## Steps

### 1. Check for existing article

**First:** Open https://newsletter.systemdesignlaws.xyz/ or https://systemdesignlaws.substack.com/archive and verify whether the post already exists on the website.

**Then:** Run `list_posts.py` to confirm via API:
```bash
python3 newsletter/scripts/list_posts.py --search "[article title]"
```

If the post exists on the website: edit the existing post, then publish. Do NOT create a duplicate.

### 2. Validate draft

```bash
python3 -m unittest tests.test_draft_body_structure -v
```

If tests fail, return to Editor with error details. Do not push broken drafts.

### 3. Push to Substack and publish (no drafts left)

```bash
python3 newsletter/scripts/create_draft.py --draft [filename].md
python3 newsletter/scripts/publish_draft.py --draft [filename].md
```

Or batch: `python3 newsletter/scripts/batch_create_and_publish.py`

Create then publish. No Substack drafts visible. Rate limits: slow at 70% (3x), 90% (5x), 95% (pause).

### 3. Report back

Return to Orchestrator (and display to user):
- draft_file: the filename pushed
- edit_url: the Substack edit URL
- excalidraw_path: `newsletter/plots/excalidraw/[name].excalidraw` for diagram editing
- status: success or failure with error message

**Always output both the Substack edit URL and the Excalidraw diagram path.**

## On failure

- **Session expired:** Print message, flag for human to refresh cookies in `newsletter/scripts/.env`. See `newsletter/scripts/PASTE_CREDENTIALS.md`.
- **Test failure:** Return draft to Editor with specific test errors.
- **API error:** Log error, do not retry automatically. Flag for human review.

## Do not

- Delete published articles. Ever. Edit only.
- Leave Substack drafts visible (always publish after create)
- Push drafts that fail structure validation
- Modify draft content (read-only consumer)
- Retry on auth failures (session refresh is manual)
