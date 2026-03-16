#!/usr/bin/env python3
"""
Create Excalidraw source files for the 4 pattern overview diagrams.
Run: python create_pattern_excalidraw.py
Then: cd newsletter/scripts && ./export_excalidraw.sh --png
"""
import json
import random
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent
PLOTS = SCRIPT.parent / "plots"
EXCALIDRAW_DIR = PLOTS / "excalidraw"
EXCALIDRAW_DIR.mkdir(parents=True, exist_ok=True)

# Minimum spacing between elements - prevents text/line overlap in exported diagrams
MIN_SPACING = 12


def gen_id():
    return hex(random.randint(0, 2**64))[2:].zfill(16)


def rect(x, y, w, h, fill, stroke="#1e1e1e", rx=8):
    return {
        "id": gen_id(),
        "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": stroke, "backgroundColor": fill,
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roundness": {"type": 3, "value": rx}, "seed": random.randint(1, 10**9),
        "version": 1, "versionNonce": random.randint(1, 10**9), "isDeleted": False,
    }


def text_el(x, y, w, txt, size=20):
    return {
        "id": gen_id(),
        "type": "text",
        "x": x, "y": y, "width": w, "height": max(25, size + 8),
        "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roundness": None, "seed": random.randint(1, 10**9),
        "version": 1, "versionNonce": random.randint(1, 10**9), "isDeleted": False,
        "text": txt, "fontSize": size, "fontFamily": 1,
        "textAlign": "left", "verticalAlign": "top",
    }


def arrow_el(x1, y1, x2, y2, stroke="#1971c2"):
    return {
        "id": gen_id(),
        "type": "arrow",
        "x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1,
        "angle": 0, "strokeColor": stroke, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roundness": None, "seed": random.randint(1, 10**9),
        "version": 1, "versionNonce": random.randint(1, 10**9), "isDeleted": False,
        "points": [[0, 0], [x2 - x1, y2 - y1]],
        "lastCommittedPoint": None, "startArrowhead": None, "endArrowhead": "arrow",
    }


def save(name, elements):
    out = EXCALIDRAW_DIR / f"{name}.excalidraw"
    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
        "files": {},
    }
    out.write_text(json.dumps(doc, indent=2))
    print(f"Created: {out}")


def real_time_updates():
    """Hop 1: Client-Server | Hop 2: Source-Server"""
    el = []
    el.append(text_el(200, 8, 700, "Real-time Updates: Two Hops", 26))
    el.append(rect(40, 50, 420, 180, "#e3f2fd"))
    el.append(text_el(180, 60, 140, "HOP 1: Client to Server", 18))
    el.append(rect(60, 95, 170, 45, "#bbdefb"))
    el.append(text_el(75, 108, 140, "Simple Polling", 16))
    el.append(rect(60, 150, 170, 45, "#90caf9"))
    el.append(text_el(75, 163, 140, "Long Polling", 16))
    el.append(rect(250, 95, 190, 45, "#64b5f6"))
    el.append(text_el(265, 108, 160, "SSE", 16))
    el.append(rect(250, 150, 190, 45, "#42a5f5"))
    el.append(text_el(265, 163, 160, "WebSockets", 16))
    el.append(text_el(60, 210, 380, "L4 load balancers for WebSockets", 14))
    el.append(rect(520, 50, 420, 180, "#e8f5e9"))
    el.append(text_el(660, 60, 140, "HOP 2: Source to Server", 18))
    el.append(rect(540, 95, 180, 45, "#c8e6c9"))
    el.append(text_el(555, 108, 150, "Pull Polling", 16))
    el.append(rect(540, 150, 180, 45, "#a5d6a7"))
    el.append(text_el(555, 163, 150, "Consistent Hash", 16))
    el.append(rect(740, 95, 180, 45, "#81c784"))
    el.append(text_el(755, 108, 150, "Pub/Sub", 16))
    el.append(text_el(540, 210, 380, "Kafka, Redis, ZooKeeper", 14))
    el.append(rect(40, 260, 900, 50, "#fff3e0"))
    el.append(text_el(320, 278, 340, "Start simple: polling -> long poll -> SSE -> WebSocket", 16))
    save("real-time-updates-overview", el)


def dealing_with_contention():
    """Escalation: Atomicity -> Pessimistic -> Optimistic -> Distributed"""
    el = []
    el.append(text_el(180, 8, 700, "Dealing with Contention: Escalation Path", 26))
    el.append(rect(40, 55, 200, 70, "#e8f5e9"))
    el.append(text_el(70, 72, 140, "Atomicity", 18))
    el.append(text_el(55, 95, 170, "Transactions", 14))
    el.append(rect(260, 55, 200, 70, "#c8e6c9"))
    el.append(text_el(290, 72, 140, "Pessimistic", 18))
    el.append(text_el(275, 95, 170, "FOR UPDATE", 14))
    el.append(rect(480, 55, 200, 70, "#a5d6a7"))
    el.append(text_el(510, 72, 140, "Optimistic", 18))
    el.append(text_el(495, 95, 170, "Version column", 14))
    el.append(rect(700, 55, 200, 70, "#ffccbc"))
    el.append(text_el(720, 72, 160, "Distributed", 18))
    el.append(text_el(715, 95, 170, "2PC, Sagas, Locks", 14))
    el.append(rect(40, 150, 200, 60, "#e3f2fd"))
    el.append(text_el(70, 165, 140, "Single DB", 16))
    el.append(rect(260, 150, 440, 60, "#bbdefb"))
    el.append(text_el(350, 165, 260, "Multiple DBs", 16))
    el.append(rect(40, 235, 860, 55, "#fff8e1"))
    el.append(text_el(280, 255, 400, "Exhaust single-DB solutions first", 18))
    save("dealing-with-contention-overview", el)


def multi_step_processes():
    """Single Server -> Event Sourcing -> Workflows"""
    el = []
    el.append(text_el(180, 8, 700, "Multi-step Processes: From Simple to Durable", 26))
    el.append(rect(40, 55, 260, 100, "#ffebee"))
    el.append(text_el(100, 72, 140, "Single Server", 18))
    el.append(text_el(55, 100, 230, "No durability", 14))
    el.append(text_el(55, 120, 230, "Crashes = lost progress", 14))
    el.append(rect(330, 55, 260, 100, "#fff3e0"))
    el.append(text_el(390, 72, 140, "Event Sourcing", 18))
    el.append(text_el(345, 100, 230, "Kafka log", 14))
    el.append(text_el(345, 120, 230, "Workers react", 14))
    el.append(rect(620, 55, 280, 100, "#e8f5e9"))
    el.append(text_el(680, 72, 160, "Workflow Engines", 18))
    el.append(text_el(635, 100, 250, "Temporal, Step Functions", 14))
    el.append(text_el(635, 120, 250, "Durable execution", 14))
    el.append(rect(40, 185, 860, 55, "#e3f2fd"))
    el.append(text_el(280, 205, 400, "Use workflows when: partial failures, long waits, compensation", 16))
    save("multi-step-processes-overview", el)


def scaling_writes():
    """Tier 1 -> 2 -> 3 -> 4"""
    el = []
    el.append(text_el(200, 8, 700, "Scaling Writes: Four Tiers", 26))
    el.append(rect(40, 55, 200, 75, "#e8f5e9"))
    el.append(text_el(70, 72, 140, "Tier 1", 18))
    el.append(text_el(55, 95, 170, "Vertical + DB choice", 14))
    el.append(rect(260, 55, 200, 75, "#e3f2fd"))
    el.append(text_el(290, 72, 140, "Tier 2", 18))
    el.append(text_el(275, 95, 170, "Sharding", 14))
    el.append(rect(480, 55, 200, 75, "#fff3e0"))
    el.append(text_el(510, 72, 140, "Tier 3", 18))
    el.append(text_el(495, 95, 170, "Queues, Load Shed", 14))
    el.append(rect(700, 55, 200, 75, "#fce4ec"))
    el.append(text_el(730, 72, 140, "Tier 4", 18))
    el.append(text_el(715, 95, 170, "Batching", 14))
    el.append(rect(40, 160, 420, 55, "#e8eaf6"))
    el.append(text_el(180, 180, 140, "Reduce throughput per component", 16))
    el.append(rect(480, 160, 420, 55, "#f3e5f5"))
    el.append(text_el(620, 180, 160, "Cassandra, Kafka, Redis", 16))
    save("scaling-writes-overview", el)


if __name__ == "__main__":
    random.seed(42)
    real_time_updates()
    dealing_with_contention()
    multi_step_processes()
    scaling_writes()
    print("\nExport with: cd newsletter/scripts && ./export_excalidraw.sh --png")
