---
name: change-checklist
description: Enforces branching, full test and CI validation before merging. Use when the user asks for a new change, feature, or fix. Always create a branch first; ensure tests pass locally and in CI before push/PR.
---

# Change Checklist

Whenever the user asks for changes, follow this checklist. **Always create a new branch first.** Do not merge until every item passes.

## 0. Create a Branch (Always First)

- Run: `git checkout main && git pull` (if needed), then `git checkout -b feature/<name>` (or `fix/`, `update/`)
- Use descriptive names: `feature/subscribe-links`, `fix/animations`, `update/hero-section`
- **Never edit directly on main** — only on a feature branch

## 1. Update All Tests

- Add or update unit tests in `tests/` for new behavior
- Add schema/validation tests for new data shapes (JSON, HTML)
- Add structure checks (grep patterns) for new HTML elements or IDs
- Ensure existing tests still pass and are not broken by the change

## 2. Pass Locally

- Run: `make test` or `python3 -m unittest discover -s tests -v`
- All tests must pass
- If tests fail: fix the code or tests before proceeding

## 3. Update CI

- Update `.github/workflows/test.yml` if new checks are needed
- Add grep validations for new HTML/JSON structure
- Ensure workflow triggers on relevant branches (`main`, `feature/**`, `fix/**`)

## 4. CI Must Pass

- Push branch, create PR
- Wait for CI to complete with 100% pass
- Do not merge until CI is green

## 5. Check Frontend and Backend Errors

- **Frontend**: Verify no console errors, broken links, or "refused to connect" issues (e.g. iframes, third-party embeds)
- **Backend**: If applicable, verify scripts (e.g. `fetch_recent_posts.py`) run without errors
- **Surface issues**: Add guardrails (fallbacks, error messages) so users see when things fail

## 6. Fix Any Issues Found

- Address linter errors
- Fix test failures
- Resolve frontend/backend errors before merge

## Quick Reference

```
0. git checkout -b feature/<name>   (always branch first)
1. Implement change
2. Update tests → python3 -m unittest discover -s tests -v (must pass)
3. Update CI workflow if needed
4. Run CI validation greps locally (see test.yml)
5. Push → PR → wait for CI green
6. Optional: python3 -m http.server 8080 for visual check
7. Fix any issues → merge only when all green
```
