# Newsletter Feedback Log

Persisted feedback from article production. **Every entry here must be propagated to ALL system layers.**

## Propagation checklist (on every new entry)

- [ ] Memory file saved/updated
- [ ] Skills updated (`.claude/skills/newsletter-draft/SKILL.md`, `.claude/newsletter/SKILL.md`)
- [ ] Agents updated (`newsletter/agents/*.md`, `.claude/newsletter/agents/*.md`)
- [ ] Sub-agents/verifiers updated (`.claude/newsletter/agents/verifiers/*.md`)
- [ ] TALK_RULES updated (`.claude/newsletter/TALK_RULES.md`)
- [ ] WORKFLOW updated (`newsletter/docs/WORKFLOW.md`)
- [ ] ARTICLE_TEMPLATE updated (`newsletter/docs/ARTICLE_TEMPLATE.md`)
- [ ] Hooks added/updated if automatable

---

## Source of truth for existing posts (CRITICAL)

**Before creating or publishing any article:** Check the website to see if the post already exists.
- **Check:** https://newsletter.systemdesignlaws.xyz/ and https://systemdesignlaws.substack.com/archive
- **If the post is already published:** Edit the existing post, then publish. Do NOT create a duplicate.
- **If the post does not exist:** Create new, then publish.
- One thing at a time: verify on website, then edit/create, then publish. Then move on.

---

## Article Output Requirements

### Always provide Excalidraw link with draft

When creating a new article, always output both:
1. **Substack draft edit URL** (from create_draft.py)
2. **Excalidraw link/path** for the article's diagrams (`newsletter/plots/excalidraw/[name].excalidraw`)

User wants to review/edit diagrams immediately after article creation.

---

## Diagrams

### Use Excalidraw (not raw SVG or HTML)

- **Source**: All diagrams created in [Excalidraw](https://excalidraw.com)
- **Storage**: `newsletter/plots/excalidraw/[name].excalidraw`
- **Export**: SVG via `npm run export-excalidraw` (or `svg_to_png.py` for PNG from SVG)
- **All-in-one**: `all-diagrams.excalidraw` contains every diagram as embedded images. Open at excalidraw.com → File → Open

### Sizing and layout

- **No clipping** - Content must not be cut off. Expand viewBox if needed.
- **Consistent size** - Target viewBox ~960x480 (match indexing-btree, scaling-reads-overview).
- **Readable** - Text must be legible. If too small, scale content or use larger fonts.
- **Avoid scale(0.x) hacks** - Prefer natural layout. Wrapping in transform can cause XML/parsing issues.
- **Close tags** - Ensure all `<g>` and other elements are properly closed (causes "Opening and end" parse errors).

### Query/comparison diagrams (e.g. composite-index)

- Use table-like layout: QUERY | CLAUSE | RESULT columns
- Rows: Query 1 (green check), Query 2 (green check), Query 3 (red X)
- Include analogy: "Think: phone book sorted by Last Name, then First Name"
- Match row heights across queries; enough padding for italic captions

### Export pipeline

- **SVG → PNG**: `python newsletter/scripts/svg_to_png.py [name]`
- **Excalidraw → SVG/PNG**: `npx excalidraw-brute-export-cli` (requires Playwright + Firefox: `npx playwright install`)
- **create_draft** uses PNGs from `newsletter/plots/png/` for Substack upload

---

## Schema and indexing content

### Users table example

```
**Schema: users table**

- **id** integer, primary key - Unique user identifier
- **email** varchar(255), indexed - Most common lookup field
- **name** varchar(100) - Display name
- **created_at** timestamp, indexed - Account creation date
```

### Without/with index

```
> **Without index** - Full table scan of 10M rows. Cost: ~412,000 units. Time: 100-500ms. The database reads every row checking if email matches.
> **With index on email** - Index scan. Cost: ~8 units. Time: 1-5ms. Jumps directly to the matching row.
```

### What to index

Columns you filter on, join on, or sort by. If users search posts by hashtag, index the hashtag column. If you sort products by price, index price.

### Composite indexes

Composite indexes cover multiple columns. Column order matters - leftmost prefix rule. An index on (status, created_at) helps WHERE status = 'active', and WHERE status = 'active' AND created_at > X, but NOT WHERE created_at > X alone.

---

## Substack and publishing

### No duplicate articles - check existing first

- **Before creating any draft**, run `list_posts.py --search "[title]"` to check if a similar article already exists
- If match found: **UPDATE** the existing post (`create_draft.py --update`), never create a duplicate
- `create_draft.py` now auto-detects duplicates unless `--force-new` is passed
- Check both drafts AND published posts

### Rate limits and batching

- **429 Too Many Requests** - `create_draft.py` now has built-in retry with exponential backoff (30s, 60s, 90s)
- **Batch delay** - `--batch-delay N` adds N seconds between image uploads (default: 2s)
- **Auto-resume** - On rate limit, script waits and retries automatically (up to 3 times)
- **Verify responses** - Every API call checks for valid response. No hallucinated success.

### Guardrails

- Never report success without verifying API response contains a valid draft_id
- If API returns empty/invalid response, error out immediately
- All API calls wrapped in `api_call_with_retry()` for consistent error handling

### Other

- **Post URL** - Output published URL only: `https://...substack.com/p/[slug]` (not draft edit URL)
- **Credentials** - Cookie-based session in `newsletter/scripts/.env` or `.substack-cookies.json`
- **Publish script** - `publish_draft.py` updates SEO via `put_draft`, then `publish_draft`. Add tags manually in Substack editor (Settings sidebar > Tags).
- **Article metadata** - `newsletter/docs/article_metadata.json` stores per-article: tags, SEO (title, description), share options (send_email, share_automatically).
- **List posts** - `list_posts.py` shows all existing drafts and published posts. Use `--search "title"` to check for duplicates.

---

## Diagram Requirements

### 20-25 diagrams per article (minimum 20)

Every article must have 20-25 diagrams explaining every concept visually:
- Every concept, flow, comparison, and trade-off gets its own diagram
- Minimum 20 diagrams per article - reject if fewer
- Target 25 diagrams per article
- Embed inline as `![Alt](url)` - no separate file links
- Original content only (no external source attribution)

### Articles needing diagram updates
- `caching-for-system-design-interviews.md` - Currently 5 diagrams, needs 15-20 more
- `real-time-updates-for-system-design-interviews.md` - Currently 1 diagram, needs 19-24 more

---

## Batch Processing and Rate Limits

### Progress bars for all batch operations

Every batch process must show real-time ASCII progress bars:
- Image uploads: show current/total, percentage, filename
- Pipeline steps: numbered step banners [1/7], [2/7], etc.
- Rate limit aware: slow down at 90% capacity, never hit 100%
- Checkpoint/resume: track progress, resume from last success on failure

### Adaptive rate limiting

- When approaching rate limit (90%+): increase batch delay automatically
- Never hit 100% rate limit - preemptive slowdown
- On pause/failure: save checkpoint, resume from where left off
- All progress visible in terminal in real time

---

## Template reference

- **Article structure**: `newsletter/docs/ARTICLE_TEMPLATE.md`
- **Workflow**: `newsletter/docs/WORKFLOW.md`
- **Talk rules**: `newsletter/TALK_RULES.md`
