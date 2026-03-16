# Newsletter Content System

System design interview prep. Original content. Diagrams. Dense, interview-ready.

## Quick Rules

See `TALK_RULES.md` - read once, no re-reading.

## Diagrams (Excalidraw)

All diagrams are created in [Excalidraw](https://excalidraw.com). Source files go in `plots/excalidraw/` as `.excalidraw`. Export to SVG/PNG:

```bash
cd newsletter/scripts && npm run export-excalidraw
# Or with PNG output for Substack: npm run export-excalidraw-png
```

See `plots/excalidraw/README.md` for full workflow.

## Agent Pipeline

```
Orchestrator → Researcher → Writer → Editor → Verifier → Scheduler
```

Agent definitions in `agents/`. See `../docs/NEWSLETTER_AGENT_PLAN.md` for full architecture.

## Publishing a Draft

### Automated (via script)

```bash
# Dry-run (validate without pushing)
python3 newsletter/scripts/create_draft.py --dry-run

# Push a specific draft to Substack
python3 newsletter/scripts/create_draft.py --draft [filename].md
```

### Manual (paste into Substack)

1. Open `newsletter/drafts/[slug].md`
2. Copy the full content
3. Go to [Substack Dashboard](https://substack.com) → New post
4. Paste. Diagrams are embedded via SVG URLs; run `npm run export-excalidraw` in `newsletter/scripts` to regenerate from Excalidraw sources if needed.
5. Publish or schedule
6. Update `backlog.json` status to `published`

## Substack URL After Publishing

```
https://newsletter.systemdesignlaws.xyz/p/[slug-from-title]
```

## Drafts Ready for Substack

| Draft | Status |
|-------|--------|
| `caching-for-system-design-interviews.md` | Pushed to Substack |
| `scaling-reads-for-system-design-interviews.md` | Pushed to Substack |

## Backlog

See `backlog.json` for full topic status tracking. 40+ topics in curriculum.

## Credentials Setup

See `scripts/PASTE_CREDENTIALS.md` for Substack cookie setup. Credentials are gitignored.
