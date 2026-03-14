---
name: pre-push-workflow
description: Run local tests, CI-style validation, and optionally visual check before pushing a PR. Use when the user asks to verify everything works, test before push, or ensure CI will pass.
---

# Pre-Push Workflow

Before pushing changes and opening a PR, run these checks to ensure CI and tests pass.

## 1. Run Python Tests

```bash
python3 -m unittest discover -s tests -v
```

All tests must pass.

## 2. Run CI Validation (index.html structure)

Mirror what `.github/workflows/test.yml` does:

```bash
grep -q '<div class="recent-list" id="recent-list">' index.html && echo "Recent Issues container OK"
grep -q 'id="recent-posts-data"' index.html && echo "Inline posts data OK"
grep -q 'recent-posts.json' index.html && echo "Dynamic fetch OK"
grep -q 'id="recent-updated"' index.html && echo "Last updated container OK"
grep -q 'id="subscribe-section"' index.html && echo "Substack email signup section OK"
grep -q 'newsletter.systemdesignlaws.xyz' index.html && echo "Substack subscribe link OK"
grep -q 'newsletter.systemdesignlaws.xyz/subscribe' index.html && echo "Subscribe CTAs use /subscribe path OK"
! grep -q 'systemdesignlaws.substack.com' index.html && echo "No old substack.com links OK"
grep -q 'guardrail-issue' index.html && echo "Frontend guardrail fallback OK"
```

## 3. Optional: Visual Check

```bash
python3 -m http.server 8080
```

Open http://localhost:8080 in a browser. Verify subscribe links, animations, no console errors.

## 4. Push and PR

Only push when 1 and 2 pass. CI will re-run on push; if local validation passed, CI should pass too.
