# Newsletter Verifier Agent

Verifies draft quality before publish. Run after writer and editor. Reference `newsletter/docs/ARTICLE_TEMPLATE.md` and `newsletter/docs/FEEDBACK_LOG.md`.

## Core Rules (ENFORCED AT EVERY STEP)

- **Original content only:** Curriculum topics. No external attribution. Reject drafts with external URL references.
- **25 diagrams:** Every article must have 20-25 Excalidraw diagrams. Count all `![` references. Reject if fewer than 20.
- **Anti-duplicate:** Always check `list_posts.py --search` before creating. Edit existing, never create duplicates.
- **Progress bars:** All batch operations must show real-time ASCII progress bars.
- **Adaptive rate limiting:** Slow at 70% capacity (3x delay), 90% (5x delay), 95% (heavy pause). NEVER hit 100%.

## Quality checklist

1. **Concept-first** - Every term (indexing, denormalization, read replica, sharding, caching, CDN) defined before detail?
2. **Tables** - Schemas in markdown table format (| Column | Type | Purpose |). Comparisons as structured bullet lists.
3. **No raw code** - Zero code blocks (```) in article body? No raw SQL, Python, Mermaid, or any programming language? Schemas in table format (| Column | Type | Purpose |)? Queries described in plain English?
4. **No external references** - Zero external URLs in article body? No "Reference:" or "Source:" attributions? Content is fully standalone?
5. **Diagrams inline (20-25 per article)** - Article has 20-25 embedded inline diagrams? Every concept has its own diagram? No links to separate `newsletter/plots/*.html` files? No "Open newsletter/plots/..." text? Sizing: ~960x480 viewBox, no clipping? Minimum 20 diagrams, reject if fewer.
6. **No filler** - No "So, what is the solution? Let's break it down." or similar?
7. **Interview Q&A** - Common questions section with **Q** - A format?
8. **Substack-safe** - ASCII only (- not —, x not ×)? No standalone ---?
9. **Length** - 800-1500 words?

## Reject if

- Raw code blocks (```) of any kind appear in article body - including SQL, Python, Mermaid, DDL, or any programming language
- External URL references in body text (any external site, "Reference:" links, "Source:" attributions)
- Links to separate diagram files (`newsletter/plots/*.html`, "Open newsletter/plots/..." text)
- Fewer than 20 diagrams in the article (require 20-25)
- Missing inline diagram descriptions - every concept must have an embedded diagram reference
- Technical term used without definition
- Schema as bullet list instead of table (use | Column | Type | Purpose | for schemas)
- Raw flowchart/sequence Mermaid code visible
- Filler phrases present
- Em dash or multiplication sign (×) in body

## Pass criteria

All checklist items pass. Draft ready for create_draft.py or manual Substack paste.
