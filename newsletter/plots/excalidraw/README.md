# Excalidraw Diagrams

All newsletter diagrams are created in **Excalidraw** and exported to SVG/PNG.

## Workflow

1. **Create** diagrams at [excalidraw.com](https://excalidraw.com) (or Excalidraw desktop app).
2. **Save** as `.excalidraw` files in this folder (e.g. `indexing-btree.excalidraw`).
3. **Export** to SVG/PNG:
   ```bash
   cd newsletter/scripts
   npm run export-excalidraw
   ```
   Or:
   ```bash
   npx excalidraw-brute-export-cli -i newsletter/plots/excalidraw/indexing-btree.excalidraw -o newsletter/plots/svg/indexing-btree.svg -f svg -s 2 -b true
   ```

## Naming convention

- Source: `newsletter/plots/excalidraw/[name].excalidraw`
- SVG output: `newsletter/plots/svg/[name].svg`
- PNG output: `newsletter/plots/png/[name].png` (for Substack)

Match the draft's image references. Example: `![Indexing - B-Tree vs Full Table Scan](...indexing-btree.svg)` → create `indexing-btree.excalidraw`.

## Requirements

- Node.js 18+
- Playwright (installed via `npx playwright install firefox` for excalidraw-brute-export-cli)

## All diagrams in one Excalidraw

**File:** `newsletter/plots/excalidraw/all-diagrams.excalidraw`

Contains all 21 newsletter diagrams as embedded images in a scrollable grid:
- scaling-reads-overview, indexing-btree, composite-index, vertical-vs-horizontal
- denormalization-tradeoff, materialized-view, read-replicas-flow, replication-lag-problem
- functional-sharding, geographic-sharding, sharding-distribution
- cache-aside-flow, cache-invalidation-strategies, cdn-edge-caching
- request-coalescing, cache-stampede, cache-versioning
- caching-layers-overview, cache-aside-pattern, write-through-vs-write-behind, latency-comparison

**To open:** [excalidraw.com](https://excalidraw.com) → **File** → **Open** → select `all-diagrams.excalidraw`

## Individual diagram: Composite Index

**File:** `newsletter/plots/excalidraw/composite-index.excalidraw`

**To open:** [excalidraw.com](https://excalidraw.com) → File → Open → select this file.
