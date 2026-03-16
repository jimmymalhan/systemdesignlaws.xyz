# Newsletter Article Template

Use this structure for all upcoming articles. Based on `scaling-reads-for-system-design-interviews.md`.

## Required sections (in order)

1. **Title** - `# [Topic] for System Design Interviews`
2. **TL;DR** - One-liner after title: `**TL;DR** - [core insight]. [1–2 sentence takeaway].`
3. **>> Elevator pitch** (optional) - 30-second quote format
4. **The Problem** - Real-world scenario, numbers (read/write ratios, scale)
5. **>> Physics quote** (optional) - Why this isn't just a software fix
6. **Problem list** - Bold: "**N problems that use this pattern:**" + comma-separated list
7. **What You Will Learn** - Blockquote with tiered list
8. **The Solution** - Overview diagram + blockquote "What interviewers want to hear"
9. **Tier sections** - H2 per tier, H3 per concept
10. **Deep Dives** - Common interviewer follow-ups
11. **When to Use in Interviews** - Scenario-specific advice + "When NOT to use"
12. **Summary** - Bullet list of key points + blockquote
13. **{{SUBSCRIBE}}** and **{{BUTTON:Read More Articles|url}}**

## Per-concept structure (within each tier)

- **Concept intro** - "What is X?" before detail
- **Explanation** - How it works, when to use, trade-offs
- **Schema** - Structured bullet list: **column** type, purpose (no raw DDL)
- **Without/With** - Blockquote: **Without X** - desc. **With X** - desc.
- **Interview tip** - Blockquote with actionable advice
- **>> Myth-busting** (optional) - Blockquote correcting common misconceptions
- **Diagrams** - `![Alt](url)` - 20-25 per article. Every concept, flow, comparison, and trade-off gets its own diagram.

## Diagram conventions (20-25 per article)

- All diagrams in Excalidraw: `newsletter/plots/excalidraw/[name].excalidraw`
- Export to SVG: `newsletter/plots/svg/[name].svg`
- PNG for Substack: `newsletter/plots/png/[name].png`
- Image refs in draft: `![Alt](https://raw.githubusercontent.com/.../newsletter/plots/svg/[name].svg)`
- **Sizing**: All diagrams ~960x480 viewBox. Content must not clip. See `newsletter/docs/FEEDBACK_LOG.md`.

## Schema format (no raw code)

```
**Schema: users table**

- **id** integer, primary key - Unique user identifier
- **email** varchar(255), indexed - Most common lookup field
- **name** varchar(100) - Display name
- **created_at** timestamp, indexed - Account creation date
```

## Blockquote types

- `>` - Standard blockquote
- `>>` - Pull quote (emphasis)
- `> **Interview tip:**` - Actionable advice
- `> **Note:**` - Technical caveat

## File naming

- Draft: `[topic-slug]-for-system-design-interviews.md`
- Diagram: `[concept-slug].excalidraw` / `.svg` / `.png`

## Article output (always provide both)

After creating an article, always output:
1. **Substack draft edit URL**
2. **Excalidraw diagram path** (`newsletter/plots/excalidraw/[name].excalidraw`)
