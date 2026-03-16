#!/usr/bin/env python3
"""
Browser-based E2E tests for systemdesignlaws.xyz.

Uses Playwright to visit the live website and verify all incorporated feedback:
subscribe section, recent posts, newsletter links, guardrail fallback,
no iframe embed. Mirrors and extends test_fetch_recent_posts.py assertions.

Run: python -m unittest tests.e2e_website_test -v
"""
import json
import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Playwright check - skip if not installed
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# E2E_BASE_URL for local serve; default to production
BASE_URL = os.environ.get("E2E_BASE_URL", "https://systemdesignlaws.xyz").rstrip("/")


@unittest.skipIf(not HAS_PLAYWRIGHT, "Playwright not installed: pip install playwright && playwright install chromium")
class TestE2EWebsite(unittest.TestCase):
    """Real browser E2E: live site structure matches QA expectations and user feedback."""

    def test_subscribe_section_visible(self):
        """Subscribe section must be present and visible (QA: has_subscribe_section)."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(BASE_URL, wait_until="networkidle")
            el = page.locator("#subscribe-section")
            self.assertTrue(el.count() > 0, "Must have #subscribe-section")
            self.assertTrue(el.is_visible(), "#subscribe-section must be visible")
            browser.close()

    def test_recent_list_exists_and_has_posts(self):
        """Recent list must exist and render posts (inline data or fetch)."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(BASE_URL, wait_until="networkidle")
            page.wait_for_selector(".recent-item", timeout=10000)
            list_el = page.locator("#recent-list")
            self.assertTrue(list_el.count() > 0, "Must have #recent-list")
            items = page.locator(".recent-item")
            self.assertGreater(items.count(), 0, "Must render at least one recent post")
            browser.close()

    def test_subscribe_links_use_newsletter_subdomain(self):
        """All subscribe CTAs must point to newsletter.systemdesignlaws.xyz (QA: all_subscribe_links)."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(BASE_URL, wait_until="networkidle")
            links = page.locator('a[href*="newsletter.systemdesignlaws.xyz"]')
            self.assertGreater(links.count(), 0, "At least one subscribe link must use newsletter subdomain")
            iframe = page.locator('iframe[src*="substack.com/embed"]')
            self.assertEqual(iframe.count(), 0, "No substack iframe embed - causes refused to connect")
            browser.close()

    def test_guardrail_fallback_capability(self):
        """Page must have guardrail markup for fetch failure (QA: has_guardrail_fallback)."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(BASE_URL, wait_until="networkidle")
            html = page.content()
            self.assertIn("guardrail-issue", html, "Page must have guardrail fallback capability")
            browser.close()

    def test_recent_posts_schema_in_page(self):
        """Inline recent-posts data must match schema (title, url, description)."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(BASE_URL, wait_until="networkidle")
            json_el = page.locator("#recent-posts-data")
            self.assertEqual(json_el.count(), 1, "Must have inline recent-posts-data")
            data = json.loads(json_el.text_content())
            self.assertIn("posts", data)
            for post in data["posts"]:
                self.assertIn("title", post)
                self.assertIn("url", post)
                self.assertIn("description", post)
            browser.close()

    def test_main_branch_protection_never_delete(self):
        """Safeguard: checked-in main ruleset blocks deletion, force-pushes, and direct merges."""
        ruleset_path = REPO / ".github" / "rulesets" / "main.json"
        self.assertTrue(ruleset_path.exists(), "main ruleset file must exist")
        data = json.loads(ruleset_path.read_text())
        self.assertEqual(data.get("target"), "branch")
        self.assertEqual(data.get("enforcement"), "active")
        self.assertEqual(
            data.get("conditions", {}).get("ref_name", {}).get("include"),
            ["refs/heads/main"],
            "ruleset must target refs/heads/main",
        )

        rules_by_type = {rule["type"]: rule for rule in data.get("rules", [])}
        self.assertIn("deletion", rules_by_type, "main ruleset must block deletions")
        self.assertIn("non_fast_forward", rules_by_type, "main ruleset must block force pushes")
        self.assertIn("pull_request", rules_by_type, "main ruleset must require pull requests")
        self.assertIn(
            "required_status_checks",
            rules_by_type,
            "main ruleset must require passing checks",
        )

        required_checks = [
            check["context"]
            for check in rules_by_type["required_status_checks"]["parameters"]["required_status_checks"]
        ]
        self.assertEqual(required_checks, ["test", "e2e-website"])


if __name__ == "__main__":
    unittest.main()
