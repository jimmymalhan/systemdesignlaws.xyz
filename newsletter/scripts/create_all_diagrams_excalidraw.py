#!/usr/bin/env python3
"""
Create one Excalidraw file with ALL newsletter diagrams embedded as images.
Layout: grid of 4 columns. Uses existing PNGs from newsletter/plots/png/.

Output: newsletter/plots/excalidraw/all-diagrams.excalidraw

Open at excalidraw.com: File > Open > all-diagrams.excalidraw
"""
import base64
import json
import random
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PLOTS_DIR = SCRIPT_DIR.parent / "plots"
PNG_DIR = PLOTS_DIR / "png"
EXCALIDRAW_DIR = PLOTS_DIR / "excalidraw"
OUT = EXCALIDRAW_DIR / "all-diagrams.excalidraw"

# Diagram order (scaling-reads + caching + extras)
DIAGRAMS = [
    "scaling-reads-overview",
    "indexing-btree",
    "composite-index",
    "vertical-vs-horizontal",
    "denormalization-tradeoff",
    "materialized-view",
    "read-replicas-flow",
    "replication-lag-problem",
    "functional-sharding",
    "geographic-sharding",
    "sharding-distribution",
    "cache-aside-flow",
    "cache-invalidation-strategies",
    "cdn-edge-caching",
    "request-coalescing",
    "cache-stampede",
    "cache-versioning",
    "caching-layers-overview",
    "cache-aside-pattern",
    "write-through-vs-write-behind",
    "latency-comparison",
]

CELL_W = 480
CELL_H = 320
GAP = 40
COLS = 4


def gen_id():
    return hex(random.randint(0, 2**64))[2:].zfill(16)


def main():
    EXCALIDRAW_DIR.mkdir(parents=True, exist_ok=True)

    elements = []
    files = {}
    ts = int(time.time() * 1000)

    for i, name in enumerate(DIAGRAMS):
        png_path = PNG_DIR / f"{name}.png"
        if not png_path.exists():
            print(f"Skip (no PNG): {name}")
            continue

        data = png_path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        file_id = gen_id()
        files[file_id] = {
            "id": file_id,
            "mimeType": "image/png",
            "dataURL": f"data:image/png;base64,{b64}",
            "created": ts,
            "lastRetrieved": ts,
        }

        row, col = divmod(i, COLS)
        x = col * (CELL_W + GAP)
        y = row * (CELL_H + GAP)

        # Label
        label_id = gen_id()
        elements.append({
            "id": label_id,
            "type": "text",
            "x": x,
            "y": y - 28,
            "width": CELL_W,
            "height": 24,
            "angle": 0,
            "strokeColor": "#1e1e1e",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roundness": None,
            "seed": random.randint(1, 10**9),
            "version": 1,
            "versionNonce": random.randint(1, 10**9),
            "isDeleted": False,
            "text": name.replace("-", " ").title(),
            "fontSize": 18,
            "fontFamily": 1,
            "textAlign": "left",
            "verticalAlign": "top",
        })

        # Image
        img_id = gen_id()
        elements.append({
            "id": img_id,
            "type": "image",
            "x": x,
            "y": y,
            "width": CELL_W,
            "height": CELL_H,
            "angle": 0,
            "strokeColor": "#1e1e1e",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roundness": {"type": 3, "value": 4},
            "seed": random.randint(1, 10**9),
            "version": 1,
            "versionNonce": random.randint(1, 10**9),
            "isDeleted": False,
            "fileId": file_id,
            "scale": [1, 1],
        })

        print(f"Added: {name}")

    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {
            "viewBackgroundColor": "#ffffff",
            "gridSize": None,
            "scrollX": 0,
            "scrollY": 0,
            "zoom": {"value": 1},
        },
        "files": files,
    }

    OUT.write_text(json.dumps(doc, indent=2))
    print(f"\nCreated: {OUT}")
    print(f"Diagrams: {len([e for e in elements if e['type'] == 'image'])}")


if __name__ == "__main__":
    main()
