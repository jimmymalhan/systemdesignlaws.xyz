# SystemDesignLaws.xyz — Newsletter Agent System

## What This Is

AI-powered newsletter production system for system design interview prep. Original content based on system design curriculum. Published to Substack at `newsletter.systemdesignlaws.xyz`.

## Project Structure

```
newsletter/
├── TALK_RULES.md          # One-pass content rules (read once, act)
├── curriculum.md           # 40+ system design topics
├── backlog.json            # Topic status tracking (queued/drafting/review/published)
├── agents/                 # Agent role definitions
│   ├── orchestrator.md     # Picks topics, coordinates workflow
│   ├── researcher.md       # Researches curriculum topics
│   ├── writer.md           # Produces drafts with diagrams
│   ├── editor.md           # Tightens prose, enforces rules
│   ├── verifier.md         # Quality gate before publish
│   └── scheduler.md        # Pushes draft to Substack via API
├── drafts/                 # Ready-for-Substack markdown drafts
├── plots/                  # Interactive HTML diagrams
└── scripts/
    ├── create_draft.py     # Push markdown → Substack draft via API
    ├── markdown_to_prosemirror.py  # MD → ProseMirror JSON converter
    └── delete_drafts.py    # Utility to clear Substack drafts
```

## Content Rules (Summary)

- **Original content:** System design curriculum topics. No external attribution. Standalone articles.
- **Structure:** Clear H2/H3, lists, subsections.
- **Diagrams:** 20-25 Excalidraw diagrams per article explaining every concept. Embedded inline as `![Alt](url)`. No raw Mermaid in articles.
- **Voice:** Dense, practical, interview-ready. No filler.
- **Length:** 800-1500 words per post.
- **Substack-safe:** No em-dashes, no x, no pipe tables, ASCII only.
- **Anti-duplicate:** Always check if article exists before publishing. If exists, edit and update - never create duplicates.
- **Progress bars:** All batch operations show real-time progress bars in terminal.

## Agent Workflow

1. **Orchestrator** picks next topic from `backlog.json` (status: queued)
2. **Researcher** gathers key concepts for the topic
3. **Writer** produces draft in `newsletter/drafts/[slug].md` + diagram in `newsletter/plots/`
4. **Editor** tightens prose, cuts filler, enforces TALK_RULES
5. **Verifier** runs quality checklist (definitions, no tables, no Mermaid, Q&A section)
6. **Scheduler** runs `create_draft.py --draft [file]` to push to Substack

## Verification Commands

```bash
# Run all tests
python3 -m unittest discover -s tests -v

# Check for existing article (ALWAYS do this first)
python3 newsletter/scripts/list_posts.py --search "[title]"

# List all posts
python3 newsletter/scripts/list_posts.py

# Dry-run Substack draft creation (no credentials needed to validate)
python3 newsletter/scripts/create_draft.py --dry-run

# Create/update draft (auto-detects duplicates, retries on rate limits)
python3 newsletter/scripts/create_draft.py --draft [filename].md

# Force new draft (skip duplicate check)
python3 newsletter/scripts/create_draft.py --draft [filename].md --force-new

# Delete all Substack drafts (human-only, requires --yes)
python3 newsletter/scripts/delete_drafts.py --yes
```

## Feedback Loop (CRITICAL)

Every piece of user feedback must cascade through ALL system layers. No exceptions.

**Propagation order:**
1. Memory file (`.claude/projects/.../memory/`)
2. `newsletter/docs/FEEDBACK_LOG.md`
3. Skills (`.claude/skills/newsletter-draft/SKILL.md` + `.claude/newsletter/SKILL.md`)
4. Agents (`newsletter/agents/*.md` + `.claude/newsletter/agents/*.md`)
5. Sub-agents/verifiers (`.claude/newsletter/agents/verifiers/*.md`)
6. `.claude/newsletter/TALK_RULES.md`
7. `newsletter/docs/WORKFLOW.md` + `newsletter/docs/ARTICLE_TEMPLATE.md`
8. This file (CLAUDE.md) if project-level
9. Hooks if the feedback can be automated

**Goal:** Zero repeat corrections. The system learns permanently from every interaction.

## Main Branch Protection (CRITICAL)

- **main is protected.** Never delete the main branch. Workflows must never target main for deletion.
- Before new work or a merge, run `./.github/scripts/sync_main_ruleset.sh`.
- Ruleset: `.github/rulesets/main.json` enforces no deletions, no force pushes, PR-only merges, and required checks `test`, `e2e-website`.
- Auto-merge: When PR targets main and `test` + `e2e-website` pass, the merge job runs and merges the PR, then deletes the feature branch only (never main).

## Never Delete Posted Articles (CRITICAL)

- **Draft** vs **Posted** are distinct. Drafts = work-in-progress. Posted = published, live.
- NEVER delete posted/published articles. Create or update only.
- `delete_drafts.py` deletes Substack drafts only. Requires `--yes`. Do NOT run as part of automated workflows. Human-only.

## Anti-Duplication Rule

Before creating ANY article:
1. **Check the website:** https://newsletter.systemdesignlaws.xyz/ or https://systemdesignlaws.substack.com/archive - verify if the post already exists
2. If it exists: edit the existing post, then publish. Do NOT create a duplicate
3. Also run `list_posts.py --search "[title]"` to confirm via API

## Rate Limits and Guardrails

- All Substack API calls use `api_call_with_retry()` with `AdaptiveRateLimiter`
- **Adaptive slowdown:** 70% capacity = 3x delay, 90% = 5x delay, 95% = heavy pause. Never hit 100%.
- Batch image uploads with `--batch-delay` (default 2s between uploads)
- **Checkpoint/resume:** Progress saved after each successful upload. On failure, resume from last checkpoint.
- **Never hallucinate success** - verify every API response has valid data before reporting
- **Progress bars:** Every batch operation shows real-time ASCII progress bar (current/total, percentage, filename)
- Pipeline steps: numbered step banners [1/7], [2/7], etc.

## Key Constraints

- All drafts must pass `tests/test_draft_body_structure.py` before pushing to Substack
- ProseMirror output must have valid structure (no empty marks, all paragraph content is type=text)
- Credentials live in `newsletter/scripts/.env` and `.substack-cookies.json` (gitignored)
- Branch: `feature/newsletter-agent-system` — do not push to main without review

## PR Auto-Merge and Branch Cleanup

- **Protect main first:** Run `./.github/scripts/sync_main_ruleset.sh` before opening or merging a PR. See `.github/rulesets/main.json` and `docs/PROTECT_MAIN_BRANCH.md`.
- **Required checks:** `test` and `e2e-website` must pass before merge.
- **Branch cleanup:** The merge workflow deletes the feature branch after merge. Never delete `main`.
