# Newsletter Agent System - Plan

> Branch: `feature/newsletter-agent-system`
> Status: Active development

---

## 1. Content Source

- **Curriculum topics only** - Topics from `newsletter/curriculum.md` and `newsletter/backlog.json`
- Researcher gathers context for each topic
- Writer produces original standalone content
- No external attribution or copied content in published articles

---

## 2. Structure

- **Introduction** - What are system design interviews, types, assessment, prep, delivery
- **Core Concepts** - Networking, API Design, Data Modeling, Caching, Sharding, Consistent Hashing, CAP, Database Indexing, Numbers to Know
- **Key Technologies** - Redis, Elasticsearch, Kafka, API Gateway, Cassandra, DynamoDB, PostgreSQL, Flink, ZooKeeper
- **Question Breakdowns** - Bit.ly, Dropbox, Uber, WhatsApp, Instagram, Rate Limiter, etc.
- **Patterns** - Real-time Updates, Contention, Multi-step, Scaling Reads/Writes, Blobs, Long-running Tasks
- **Advanced Topics** - Time Series DBs, Data Structures for Big Data, Vector DBs

Full mapping in `newsletter/curriculum.md`. Status tracked in `newsletter/backlog.json`.

**Template and feedback:**
- **Article structure:** `newsletter/docs/ARTICLE_TEMPLATE.md` (based on scaling-reads)
- **Persisted feedback:** `newsletter/docs/FEEDBACK_LOG.md` – diagram conventions, schema format, Substack tips
- **Full pipeline:** `newsletter/docs/WORKFLOW.md`
- When feedback is received: add to FEEDBACK_LOG, then update agents, SKILL, and WORKFLOW

---

## 3. Diagrams

**All diagrams are created in Excalidraw.** Store source files in `newsletter/plots/excalidraw/` as `.excalidraw` files. Export to SVG/PNG via `npm run export-excalidraw` in `newsletter/scripts/`.

- One diagram per major section
- Create at [excalidraw.com](https://excalidraw.com), save as `.excalidraw`, export to `newsletter/plots/svg/`
- **Sizing:** ~960x480 viewBox, no clipping. See `newsletter/docs/FEEDBACK_LOG.md`
- No raw Mermaid or code blocks visible to readers
- Diagrams embedded inline in drafts; no links to separate files

---

## 4. Agent Architecture

Six agents forming a pipeline:

| Agent | Role | Definition |
|-------|------|------------|
| **Orchestrator** | Pick topic from backlog, coordinate pipeline, track status | `agents/orchestrator.md` |
| **Researcher** | Gather context for curriculum topic | `agents/researcher.md` |
| **Writer** | Produce draft with structure, diagrams, prose | `agents/writer.md` |
| **Editor** | Tighten prose, enforce TALK_RULES, cut filler | `agents/editor.md` |
| **Verifier** | Quality gate checklist before publish | `agents/verifier.md` |
| **Scheduler** | Validate tests, push to Substack, publish immediately | `agents/scheduler.md` |

Pipeline: `Orchestrator → Researcher → Writer → Editor → Verifier → Scheduler`

Status flow in backlog.json: `queued → drafting → review → published`

---

## 5. Talk Rules (One-pass, No Re-reading)

**File:** `newsletter/TALK_RULES.md`

- **Source:** Curriculum topics only
- **Concept-first:** Define every term before detail
- **Diagrams:** Excalidraw in `newsletter/plots/excalidraw/`. Export to SVG. No raw code. Sizing: ~960x480 viewBox, no clipping (see FEEDBACK_LOG.md).
- **Structure:** Clear H2/H3, lists
- **Voice:** Dense, practical, interview-ready. No filler.
- **Comparisons:** Bullet lists, not pipe tables
- **Substack-safe:** ASCII only (no em-dashes, no multiplication signs)
- **Length:** 800-1500 words per post

---

## 6. Template and feedback loop

- **Article template:** `newsletter/docs/ARTICLE_TEMPLATE.md` - structure from scaling-reads for all upcoming articles
- **Feedback log:** `newsletter/docs/FEEDBACK_LOG.md` - persisted conventions (Excalidraw, diagram sizing, schema format)
- **On feedback:** Update FEEDBACK_LOG.md first, then propagate to SKILL.md, agents, and WORKFLOW.md

---

## 7. File Layout

```
CLAUDE.md                        # Project context for agent teams
newsletter/
├── docs/                        # Article template, feedback log, workflow
│   ├── ARTICLE_TEMPLATE.md      # Structure for all articles (from scaling-reads)
│   ├── FEEDBACK_LOG.md          # Persisted learnings (diagrams, schema, Substack)
│   └── WORKFLOW.md              # End-to-end pipeline
├── TALK_RULES.md                # One-pass content rules
├── README.md                    # Publishing instructions
├── curriculum.md                # Topic list
├── backlog.json                 # Status per topic (queued/drafting/review/published)
├── agents/                      # Agent role definitions
│   ├── orchestrator.md          # Topic selection + coordination
│   ├── researcher.md            # Curriculum context gathering
│   ├── writer.md                # Draft production
│   ├── editor.md                # Prose tightening + rule enforcement
│   ├── verifier.md              # Quality checklist gate
│   └── scheduler.md             # Substack API push + publish
├── drafts/                      # Ready-for-Substack markdown drafts
├── plots/                       # Excalidraw source + exported SVG/PNG
│   ├── excalidraw/              # .excalidraw source files
│   ├── svg/                     # Exported SVGs (from Excalidraw)
│   └── png/                     # Exported PNGs (for Substack)
└── scripts/
    ├── create_draft.py          # Push markdown → Substack
    ├── publish_draft.py         # Publish draft (no draft-only)
    ├── markdown_to_prosemirror.py  # MD → ProseMirror JSON
    ├── delete_drafts.py         # Human-only; never touch published
    ├── .env                     # Credentials (gitignored)
    └── .substack-cookies.json   # Session (gitignored)
tests/
├── test_draft_body_structure.py # ProseMirror structure validation
├── test_newsletter_create_draft.py  # Draft parsing + env tests
└── test_fetch_recent_posts.py   # Landing page tests
```

---

## 8. Substack Publishing Pipeline

1. Scheduler validates draft passes `test_draft_body_structure.py`
2. Scheduler runs `create_draft.py` then `publish_draft.py` - **publish immediately, no drafts left**
3. **Never delete published articles** - edit only. If article exists, update it.
4. URL: `https://newsletter.systemdesignlaws.xyz/p/[slug]`
5. Orchestrator updates `backlog.json` status to `published`

Credentials: cookie-based session in `.env` / `.substack-cookies.json` (see `PASTE_CREDENTIALS.md`).

---

## 9. Customization Levers

| Lever | File | Effect |
|-------|------|--------|
| Topic order | `backlog.json` | What gets written next |
| Content rules | `TALK_RULES.md` | One-pass behavior for all agents |
| Voice/tone | `agents/writer.md` | Density, structure, style |
| Quality bar | `agents/verifier.md` | Pass/reject criteria |
| Editing rules | `agents/editor.md` | What gets cut or changed |
| Curriculum | `curriculum.md` | Full topic list |
| Article structure | `docs/ARTICLE_TEMPLATE.md` | Required sections, schema format |
| Feedback/learnings | `docs/FEEDBACK_LOG.md` | Diagram conventions, schema, Substack |

---

## 10. What Exists (This Branch)

- [x] Plan (this file)
- [x] `CLAUDE.md` - project context for agent teams
- [x] `newsletter/TALK_RULES.md` - one-pass content rules
- [x] `newsletter/curriculum.md` - 40+ topics
- [x] `newsletter/backlog.json` - topic status tracking
- [x] `newsletter/agents/` - all 6 agents defined
- [x] `newsletter/drafts/` - draft articles
- [x] `newsletter/plots/` - diagrams
- [x] `newsletter/scripts/create_draft.py` - Substack API integration
- [x] `newsletter/scripts/publish_draft.py` - publish flow
- [x] `newsletter/scripts/markdown_to_prosemirror.py` - MD → ProseMirror converter
- [x] `newsletter/scripts/delete_drafts.py` - draft cleanup (human-only, never published)
- [x] Tests - structure validation, parsing, landing page
- [x] CI - GitHub Actions with dry-run validation
