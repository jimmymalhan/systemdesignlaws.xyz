#!/usr/bin/env python3
"""
Generate composite-index.excalidraw with Composite Index: Leftmost Prefix Rule diagram.
Run this, then export with: npx excalidraw-brute-export-cli -i ... -o ... -f png -s 3 -b true
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).parent.parent / "plots" / "excalidraw" / "composite-index.excalidraw"

def gen_id():
    return hex(random.randint(0, 2**64))[2:].zfill(16)

def rect(x, y, w, h, fill, stroke="#1e1e1e", rx=8):
    return {
        "id": gen_id(),
        "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": stroke, "backgroundColor": fill,
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roundness": {"type": 3, "value": rx}, "seed": random.randint(1, 1e9),
        "version": 1, "versionNonce": random.randint(1, 1e9), "isDeleted": False,
    }

def text_el(x, y, w, txt, size=20):
    return {
        "id": gen_id(),
        "type": "text",
        "x": x, "y": y, "width": w, "height": max(25, size + 8),
        "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roundness": None, "seed": random.randint(1, 1e9),
        "version": 1, "versionNonce": random.randint(1, 1e9), "isDeleted": False,
        "text": txt, "fontSize": size, "fontFamily": 1,
        "textAlign": "left", "verticalAlign": "top",
    }

elements = []
# Title
elements.append(text_el(180, 10, 600, "Composite Index: Leftmost Prefix Rule", 28))
# Index box
elements.append(rect(100, 55, 760, 45, "#e8f4fd"))
elements.append(text_el(280, 68, 400, "INDEX ON (status, created_at)", 22))
# Headers
elements.append(text_el(130, 118, 80, "QUERY", 16))
elements.append(text_el(440, 118, 100, "CLAUSE", 16))
elements.append(text_el(750, 118, 80, "RESULT", 16))
# Query 1
elements.append(rect(40, 165, 880, 85, "#e8f5e9"))
elements.append(text_el(60, 185, 100, "Query 1", 22))
elements.append(text_el(320, 185, 60, "WHERE", 18))
elements.append(rect(400, 178, 230, 38, "#c8e6c9", "#2e7d32"))
elements.append(text_el(415, 188, 200, "status = 'active'", 18))
elements.append(rect(840, 188, 50, 50, "#4caf50"))  # checkmark circle
elements.append(text_el(450, 235, 400, "Uses index (matches leftmost column)", 16))
# Query 2
elements.append(rect(40, 262, 880, 85, "#e8f5e9"))
elements.append(text_el(60, 282, 100, "Query 2", 22))
elements.append(text_el(220, 282, 60, "WHERE", 18))
elements.append(rect(295, 275, 200, 38, "#c8e6c9", "#2e7d32"))
elements.append(text_el(310, 285, 170, "status = 'active'", 18))
elements.append(text_el(510, 282, 40, "AND", 18))
elements.append(rect(555, 275, 230, 38, "#c8e6c9", "#2e7d32"))
elements.append(text_el(570, 285, 200, "created_at > '2024'", 18))
elements.append(rect(840, 285, 50, 50, "#4caf50"))
elements.append(text_el(380, 332, 400, "Uses index (both columns, left to right)", 16))
# Query 3
elements.append(rect(40, 359, 880, 85, "#ffebee"))
elements.append(text_el(60, 379, 100, "Query 3", 22))
elements.append(text_el(280, 379, 60, "WHERE", 18))
elements.append(rect(355, 372, 340, 38, "#ffcdd2", "#c62828"))
elements.append(text_el(370, 382, 310, "created_at > '2024-01-01'", 18))
elements.append(rect(840, 379, 50, 50, "#e53935"))  # X circle
elements.append(text_el(310, 432, 450, "Cannot use index (skipped leftmost column!)", 16))
# Phone book
elements.append(rect(80, 465, 800, 55, "#e8f4fd"))
elements.append(text_el(110, 482, 40, "📚", 24))
elements.append(text_el(160, 478, 600, "Think: phone book sorted by Last Name, then First Name", 18))

doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {
        "viewBackgroundColor": "#ffffff",
        "gridSize": None,
    },
    "files": {},
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, indent=2))
print(f"Created: {OUT}")
print("Export with zoom: npx excalidraw-brute-export-cli -i", OUT, "-o newsletter/plots/png/composite-index.png -f png -s 3 -b true")
