# Talk Rules — One Pass, No Re-reading

Skim once. Act. Don't re-read.

---

## Source

- **Original content only.** All articles are original. No external attribution, no copied content.
- **Per-article topic** - Use the topic from `newsletter/curriculum.md` or `backlog.json` for that article.
- Researcher gathers context. Writer produces original standalone content.
- No external URLs in article content. No "Reference:" links, no "Source:" attributions.
- Content is standalone - no external URL references in the published article.
- **Rewrite, don't copy** - Content must be substantially rewritten in original words. Change sentence structure, use different phrasing, add original examples. Must not appear as copied content.
- **No source data in GitHub** - Draft content must NOT be committed to the public repository. Drafts stay local or go directly to Substack. Use .gitignore to exclude newsletter/drafts/ and newsletter/research/.

## Operational Rules (ALL agents)

- **Anti-duplicate:** Always check `list_posts.py --search` before creating. Edit existing, never create duplicates.
- **Progress bars:** All batch operations show real-time ASCII progress bars (current/total, percentage, filename).
- **Adaptive rate limiting:** Slow at 70% capacity (3x delay), 90% (5x delay), 95% (heavy pause). NEVER hit 100%. Checkpoint/resume on failure.
- **Batch image uploads:** Use `--batch-delay` (default 2s). Resume from last checkpoint on failure.

---

## Concept-first

- **Define before detail.** For every term (indexing, denormalization, read replica, sharding, caching, CDN), add "What is X?" and explain before going into how/when/why.
- Example: "What is indexing? An index is a data structure..." then "Without an index... With an index..."

## Tables and structure

- Use structured bullet lists for comparisons. Format: **Label** - value. Or **Term** - Pros / Cons.
- **Schema tables** - Use markdown pipe tables for schemas: | Column | Type | Purpose |
- For interview Q&A: **Question** - Answer (one per bullet).

## No raw code blocks

- **Never include raw code blocks (```) in the article body** - no SQL, Python, Mermaid, DDL, or any programming language.
- **Schema tables** - Use markdown tables: | Column | Type | Purpose |. Never show raw CREATE TABLE or DDL.
- **Query descriptions** - Write in plain English: what the query does, which fields it uses, the expected result. Never show raw SQL.
- This rule applies to all content visible in the published article.

## Diagrams (20-25 per article)

- **Use Excalidraw** - All diagrams are created in [Excalidraw](https://excalidraw.com). Save `.excalidraw` files to `newsletter/plots/excalidraw/`, then run `npm run export-excalidraw` to export to SVG/PNG.
- **No overlap** - Text must never overlap lines, arrows, or other text. Use minimum 12px spacing between elements. Route arrows around text boxes.
- **20-25 diagrams per article** - Every concept gets its own diagram. Not just one per section - every sub-concept, flow, comparison, and trade-off should have a visual.
- Every major section = multiple embedded inline diagrams explaining each concept
- **No raw Mermaid/code in newsletter body** - Readers should not see flowchart syntax
- **Embed diagrams inline** - Each concept gets an embedded diagram directly in the article text as `![Alt](url)`.
- **No links to separate diagram files** - Do not link to `newsletter/plots/*.html` files. No "Open newsletter/plots/..." text. Diagrams live in the article, not in separate files.
- **No external references** - No external URLs in the article body. Content is standalone.
- **Smaller sizing** - Diagrams must match content column width (728px render width, ~960x480 source). Do not use full-bleed/oversized images. imageSize: "normal", resizeWidth: 728.
- **Verify loading** - After publishing, verify diagrams actually load on the live website (newsletter.systemdesignlaws.xyz). Check every image URL resolves. Reject if any diagram is broken.

## Formatting

- **No "- " prefix on sub-headlines** - Sub-headlines must not start with "- ". Write complete sub-headlines. No truncation - if text is long, use "..." at the end, never cut mid-word.
- **No leading line breaks** - Article content must not begin with blank lines or line breaks. First line after the title/TL;DR is content.
- **Complete sub-headlines** - Every sub-headline must be a complete phrase. Never truncate mid-word (e.g., "- r glo..." is wrong. Use "Regional Globalization..." instead).

## Structure

- Logical H2, H3 subsection organization
- **Order matters**: Optimize within DB first, then scale horizontally, then add caching
- Use subsection titles: Indexing, Hardware Upgrades, Denormalization, Read Replicas, Sharding, Application-Level Caching, CDN
- TL;DR one liner at top
- 800-1500 words
- No external attribution links or URLs (standalone content)

## Paywall

- **Paywall at 30%** - Insert `{{PAYWALL}}` after approximately 30% of the article content. Place it before revealing the key insight or solution twist. Content above the paywall is free preview; content below requires subscription.
- The paywall marker must appear in every article draft.

## Voice

- Dense. Practical. Interview-ready.
- No filler: "So, what is the solution? Let's break it down." / "In this article" / "Let's dive in"
- Numbers when relevant (latency, throughput)
- Trade-offs, not just facts

---

## Substack compatibility (when using create_draft.py)

- **No em/en dashes** — Use `-` not `—` or `–` (editor can break on Unicode)
- **No × in body** — Use `x` (e.g. "Nx read capacity" not "N×")
- **No standalone ---** — Script converts these; avoid if possible
- **Complete paragraphs** — Every section must have body text under each header, not just headers

---

## Verifier rejection criteria

The verifier must reject any draft that contains:
- Raw code blocks (```) of any kind in the article body
- External URL references in body text (any external site)
- Links to separate diagram files (`newsletter/plots/*.html` or "Open newsletter/plots/..." text)
- Missing inline diagram references - every major section must have an embedded diagram description

## Workflow

1. Orchestrator picks from backlog
2. Researcher fetches source material
3. Writer drafts with inline diagrams (no code blocks, no external URLs)
4. Editor tightens
5. Scheduler runs `batch_create_and_publish.py` or `create_draft.py` + `publish_draft.py` - publishes (not draft-only). If article exists → edit. If not → publish.
6. URL: `newsletter.systemdesignlaws.xyz/p/[slug]`
