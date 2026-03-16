# Newsletter Workflow

End-to-end workflow for producing and publishing articles. Use scaling-reads as the template.

## 0. Protect main before new work

Before starting a new branch or merging a PR, sync the checked-in GitHub ruleset:

```bash
./.github/scripts/sync_main_ruleset.sh
```

- Ruleset file: `.github/rulesets/main.json`
- Required checks: `test`, `e2e-website`
- Protection: no deletion, no force pushes, PR-only merges on `main`

## 1. Source and structure

- **Source**: Curriculum topics only (original content)
- **Template**: `newsletter/docs/ARTICLE_TEMPLATE.md`
- **Curriculum**: `newsletter/curriculum.md`, status in `newsletter/backlog.json`

## 2. Draft creation

1. Orchestrator picks topic from backlog (status: queued)
2. Researcher gathers context for the topic (from curriculum)
3. Writer produces draft in `newsletter/drafts/[slug]-for-system-design-interviews.md`
4. Follow structure: The Problem, What You Will Learn, The Solution, Tier sections, Deep Dives, When to Use, Summary

## 3. Diagrams (20-25 per article)

Every article must have 20-25 diagrams explaining every concept visually.

1. **Create** at [excalidraw.com](https://excalidraw.com) - one diagram per concept, flow, comparison, and trade-off
2. **Save** as `newsletter/plots/excalidraw/[name].excalidraw`
3. **Export**:
   - Option A: `npm run export-excalidraw` in `newsletter/scripts` (Excalidraw to SVG, needs Playwright Firefox)
   - Option B: Use SVG source in `newsletter/plots/svg/`, then `python newsletter/scripts/svg_to_png.py [name]` for PNG
4. **Sizing**: ~960x480 viewBox, no clipping. See `newsletter/docs/FEEDBACK_LOG.md`
5. **Reference in draft**: `![Alt](https://raw.githubusercontent.com/.../newsletter/plots/svg/[name].svg)`
6. **Minimum**: 20 diagrams. Target: 25. Reject if fewer than 20.

## 4. Edit and verify

1. Editor tightens prose, enforces `newsletter/TALK_RULES.md`
2. Verifier runs checklist (concept-first, no raw code, diagrams inline, Substack-safe)
3. Run: `python3 -m unittest tests.test_draft_body_structure -v`

## 5. Publish to Substack

**Step 5a: Check for existing article first**
```bash
python3 newsletter/scripts/list_posts.py --search "[article title]"
```
If match found, the article already exists. Update it instead of creating a duplicate.

**Step 5b: Create or update draft**
```bash
# Auto-detects duplicates and updates if found
python3 newsletter/scripts/create_draft.py --draft [filename].md

# Force new (skip duplicate check)
python3 newsletter/scripts/create_draft.py --draft [filename].md --force-new

# Explicit update
python3 newsletter/scripts/create_draft.py --draft [filename].md --update
```
Script uploads PNGs from `newsletter/plots/png/` to Substack CDN. Rate limits handled with auto-retry.

**Always provide both to user:**
- Substack draft edit URL
- Excalidraw diagram path (`newsletter/plots/excalidraw/[name].excalidraw`)

**Step 5b: Create/update + publish (no draft-only)**
- If article exists (draft or published) → update it. If not → create and publish.
- Batch (all pattern articles): `python3 newsletter/scripts/batch_create_and_publish.py`
- Single article: `create_draft.py` then `publish_draft.py`:
```bash
python3 newsletter/scripts/create_draft.py --draft [filename].md
python3 newsletter/scripts/publish_draft.py --draft [filename].md
```
- Add article metadata to `newsletter/docs/article_metadata.json` (tags, SEO, share options) before publish.
- Publishes (not draft-only). Updates draft with SEO, publishes, optionally sends email + auto-shares.
- Tags: Add manually in Substack editor (Settings sidebar > Tags)

With `publish_draft.py --no-publish`: only updates metadata, does not publish.

## 6. Post-publish

- Update `newsletter/backlog.json` status to `published`
- Update landing page if needed

## 7. Feedback loop (ALWAYS when feedback received)

Every piece of user feedback triggers a full propagation cascade. No exceptions.

### Propagation order

1. **Memory** - Save/update feedback memory in `.claude/projects/.../memory/`
2. **FEEDBACK_LOG** - Add to `newsletter/docs/FEEDBACK_LOG.md`
3. **Skills** - Update `.claude/skills/newsletter-draft/SKILL.md` AND `.claude/newsletter/SKILL.md`
4. **Agents** - Update relevant agents in `newsletter/agents/*.md` AND `.claude/newsletter/agents/*.md`
5. **Sub-agents (verifiers)** - Update `.claude/newsletter/agents/verifiers/*.md`
6. **TALK_RULES** - Update `.claude/newsletter/TALK_RULES.md`
7. **WORKFLOW** - Update this file (`newsletter/docs/WORKFLOW.md`) and `docs/PROTECT_MAIN_BRANCH.md` if the change affects merge/protection workflow
8. **ARTICLE_TEMPLATE** - Update `newsletter/docs/ARTICLE_TEMPLATE.md`
9. **CLAUDE.md** - Update if it affects project-level rules
10. **Hooks** - Add/update hooks if the feedback can be automated

### Execution

- Propagate to all files in parallel (use agents per file)
- Then verify the fix end-to-end
- Goal: zero repeat corrections across conversations

## Quick commands

```bash
# Check for existing article before creating
python3 newsletter/scripts/list_posts.py --search "Scaling Reads"

# List all posts (drafts + published)
python3 newsletter/scripts/list_posts.py

# Dry-run (validate without pushing)
python3 newsletter/scripts/create_draft.py --dry-run

# Create/update draft (auto-detects duplicates)
python3 newsletter/scripts/create_draft.py --draft scaling-reads-for-system-design-interviews.md

# Force new draft (skip duplicate check)
python3 newsletter/scripts/create_draft.py --draft [file].md --force-new

# Regenerate PNG from SVG
python3 newsletter/scripts/svg_to_png.py composite-index

# Export all Excalidraw files (needs npx playwright install)
cd newsletter/scripts && npm run export-excalidraw
```
