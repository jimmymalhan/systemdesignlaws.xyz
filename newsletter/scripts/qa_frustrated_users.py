#!/usr/bin/env python3
"""
QA Skill: Simulate 100 frustrated/upset users reviewing the newsletter draft.
Generates a list of realistic complaints from different reader personas,
then checks the draft against each complaint to surface real issues.

Usage:
  python qa_frustrated_users.py --draft scaling-reads-for-system-design-interviews.md
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

# 100 frustrated user complaints organized by category
COMPLAINTS = {
    "Missing Content": [
        "Where's the actual code? I can't learn without seeing real SQL queries.",
        "You mention B-tree but don't explain what a B-tree actually IS.",
        "No mention of connection pooling? That's the first thing I'd do.",
        "What about read-through caching? You only cover cache-aside.",
        "Missing: how do you actually SET UP a read replica in Postgres?",
        "Where are the benchmarks? Show me actual throughput numbers.",
        "You don't explain WAL at all, just name-drop it.",
        "No mention of materialized views as a caching strategy.",
        "What about query optimization beyond indexing? EXPLAIN plans?",
        "Missing section on monitoring - how do I know reads are the bottleneck?",
    ],
    "Diagrams & Visuals": [
        "The diagrams look like they were made in MS Paint.",
        "I can't read the text in the diagram - it's too small.",
        "Text overlaps in the sharding diagram.",
        "Where's the diagram for cache-aside flow? That's the most important pattern.",
        "No diagram for denormalization? Show me the before/after tables.",
        "The arrows don't clearly show data flow direction.",
        "These diagrams would fail in an actual interview whiteboard.",
        "Add a comparison diagram - replicas vs sharding vs caching side by side.",
        "The CDN diagram doesn't show cache invalidation flow.",
        "No watermark or branding on diagrams - anyone could steal these.",
    ],
    "Too Vague / Not Practical": [
        "You say 'index columns you query often' but don't explain HOW to decide.",
        "What does '50,000-100,000 reads per second' actually mean in practice?",
        "Cache-aside sounds great but what happens in a distributed system with 20 servers?",
        "You mention TTL but don't say what happens when TTL is wrong.",
        "The sharding section is too theoretical. Show me a real shard key decision.",
        "How do I actually implement request coalescing? This is hand-wavy.",
        "Your cache stampede solutions are listed but not explained.",
        "What monitoring tools detect these read bottlenecks?",
        "How do I decide WHEN to move from Tier 1 to Tier 2?",
        "The 'when not to use' section is too brief. Give me anti-pattern examples.",
    ],
    "Formatting & Readability": [
        "This reads like a textbook, not a newsletter. Where's the personality?",
        "Wall of text. I stopped reading after the indexing section.",
        "Too many bullet points. Mix it up with different formatting.",
        "The schema sections are hard to scan. Use a visual table, not bullets.",
        "Section headers don't tell me what I'll learn. 'Indexing' is boring.",
        "No callout boxes for key takeaways. I want to skim and still learn.",
        "The summary just repeats what you already said. Add something new.",
        "Where's the TL;DR for each section? I don't have time to read everything.",
        "The article flow is jerky - no transitions between sections.",
        "Font size in email is too small for the data-heavy sections.",
    ],
    "Interview Relevance": [
        "This doesn't tell me WHAT WORDS to say in an interview.",
        "No example of how to structure a 5-minute scaling reads answer.",
        "Missing: common mistakes candidates make when discussing caching.",
        "How does this apply to a specific system? Design Twitter's feed.",
        "You list Ticketmaster but don't show HOW to apply scaling reads to it.",
        "What's the interviewer actually looking for when they ask about scaling reads?",
        "No decision tree: given X requirements, choose Y technique.",
        "The deep dive questions are listed but the answers are too short.",
        "Missing: how to handle follow-up questions about consistency.",
        "Where's the 30-second elevator pitch for scaling reads?",
    ],
    "Technical Accuracy": [
        "B-tree index doesn't always have 4 levels. Depends on data and page size.",
        "Your TTL guidelines are arbitrary. Source?",
        "Redis is not always 1ms. Network latency varies.",
        "Cache-aside doesn't 'only store requested data' - pre-warming exists.",
        "Sharding by user_id isn't always even. Zipf distribution?",
        "You ignore the coordinator overhead in scatter-gather queries.",
        "Write-ahead log doesn't 'stream' - it's pulled by replicas in most DBs.",
        "CDN latency of 20-40ms is only for cached content. First request is slow.",
        "The 50x cache improvement assumes cache hit rate of >95%.",
        "Denormalization doesn't always give 10x improvement. Depends on join complexity.",
    ],
    "Comparison with Other Resources": [
        "Other resources explain this better with interactive diagrams.",
        "ByteByteGo covers this in one diagram. Why do I need 2000 words?",
        "System Design Primer has more practical examples.",
        "Your article is too long. DDIA covers this in a more structured way.",
        "Where's the practice problem? Other resources have exercises.",
        "No video walkthrough? Other newsletters have YouTube companions.",
        "The numbering system is confusing. Just use clear headers.",
        "Other newsletters use code examples. Where are yours?",
        "This feels like a wiki article, not expert instruction.",
        "No community discussion or comments section linked.",
    ],
    "Substack-Specific Issues": [
        "Images don't load in my email client (Gmail).",
        "The subscribe button looks broken.",
        "Links open in a weird way on mobile.",
        "Can't share a specific section of this article.",
        "The article is too long for email. Split into a series.",
        "No table of contents at the top.",
        "The diagrams are blurry on my retina display.",
        "Dark mode makes the diagrams unreadable.",
        "No bookmark/save feature for sections I want to revisit.",
        "The 'Next: Scaling Writes' teaser gives no timeline.",
    ],
    "Emotional / Trust": [
        "Who wrote this? What's your background in distributed systems?",
        "These numbers feel made up. Cite your sources.",
        "This covers basics I already know. Where's the advanced content?",
        "I paid for this? It reads like a free blog post.",
        "No testimonials from people who passed interviews using this.",
        "The advice contradicts what my senior engineer told me.",
        "Too much jargon without definitions. Not beginner-friendly.",
        "Not enough jargon. Too dumbed down for senior engineers.",
        "The article promises 'interview-ready' but I still don't feel ready.",
        "No follow-up support if I have questions. Just a wall of text.",
    ],
    "Specific Technical Gaps": [
        "No mention of CQRS pattern for read/write separation.",
        "Missing: event sourcing as an alternative to read replicas.",
        "Where's the discussion of read-your-own-writes consistency?",
        "No mention of bloom filters for cache optimization.",
        "Missing: leader election when primary fails.",
        "What about multi-region replication?",
        "No discussion of hot partition mitigation beyond key fanout.",
        "Where's the analysis of consistent hashing for sharding?",
        "Missing: write-behind caching as an alternative pattern.",
        "No mention of database connection pooling (PgBouncer, etc.).",
    ],
}


def run_qa(draft_path: Path) -> list[dict]:
    """Run all 100 user complaints against the draft. Returns list of {complaint, category, status, note}."""
    content = draft_path.read_text().lower()
    results = []

    for category, complaints in COMPLAINTS.items():
        for complaint in complaints:
            # Simple keyword-based check
            status = "addressed"
            note = ""

            # Check if the complaint topic is covered in the article
            keywords = _extract_keywords(complaint)
            found = sum(1 for kw in keywords if kw in content)
            coverage = found / len(keywords) if keywords else 0

            if coverage < 0.3:
                status = "NOT_ADDRESSED"
                note = f"Missing keywords: {[kw for kw in keywords if kw not in content][:3]}"
            elif coverage < 0.6:
                status = "PARTIALLY_ADDRESSED"
                note = f"Partially covered ({found}/{len(keywords)} keywords)"
            else:
                status = "ADDRESSED"

            results.append({
                "category": category,
                "complaint": complaint,
                "status": status,
                "note": note,
            })

    return results


def _extract_keywords(complaint: str) -> list[str]:
    """Extract meaningful keywords from a complaint."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "but", "and", "or",
        "not", "no", "nor", "so", "too", "very", "just", "don't", "doesn't",
        "i", "you", "me", "my", "your", "it", "this", "that", "these", "those",
        "what", "where", "when", "how", "why", "which", "who", "whom",
        "about", "than", "then", "there", "here", "also", "only",
    }
    words = complaint.lower().replace("?", "").replace(".", "").replace("'", "").split()
    return [w for w in words if w not in stop_words and len(w) > 2]


def print_report(results: list[dict]):
    """Print a summary report of the QA results."""
    total = len(results)
    addressed = sum(1 for r in results if r["status"] == "ADDRESSED")
    partial = sum(1 for r in results if r["status"] == "PARTIALLY_ADDRESSED")
    missing = sum(1 for r in results if r["status"] == "NOT_ADDRESSED")

    print(f"\n{'='*70}")
    print(f"QA REPORT: 100 Frustrated Users Review")
    print(f"{'='*70}")
    print(f"  ADDRESSED:           {addressed}/{total}")
    print(f"  PARTIALLY ADDRESSED: {partial}/{total}")
    print(f"  NOT ADDRESSED:       {missing}/{total}")
    print(f"{'='*70}")

    if missing > 0:
        print(f"\nTOP UNADDRESSED COMPLAINTS:")
        print(f"{'-'*70}")
        for r in results:
            if r["status"] == "NOT_ADDRESSED":
                print(f"  [{r['category']}] {r['complaint']}")
                if r["note"]:
                    print(f"    -> {r['note']}")

    if partial > 0:
        print(f"\nPARTIALLY ADDRESSED (could improve):")
        print(f"{'-'*70}")
        for r in results:
            if r["status"] == "PARTIALLY_ADDRESSED":
                print(f"  [{r['category']}] {r['complaint']}")

    print(f"\n{'='*70}")
    score = (addressed * 1.0 + partial * 0.5) / total * 100
    print(f"OVERALL SCORE: {score:.0f}/100")
    if score >= 80:
        print("VERDICT: READY TO PUBLISH")
    elif score >= 60:
        print("VERDICT: NEEDS MINOR FIXES")
    else:
        print("VERDICT: NEEDS MAJOR REVISION")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="QA: 100 Frustrated Users Review")
    parser.add_argument("--draft", type=str, required=True, help="Draft filename")
    args = parser.parse_args()

    drafts_dir = REPO / "newsletter" / "drafts"
    draft_path = drafts_dir / args.draft
    if not draft_path.exists():
        print(f"Draft not found: {draft_path}")
        sys.exit(1)

    results = run_qa(draft_path)
    print_report(results)
