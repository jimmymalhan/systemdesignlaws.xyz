# SystemDesignLaws.xyz

Landing page for [SystemDesignLaws](https://systemdesignlaws.substack.com) - a newsletter about the laws that govern every system at scale.

**Live:** [systemdesignlaws.xyz](https://systemdesignlaws.xyz)

## Local development

```bash
# Serve the site locally
python3 -m http.server 8888
# Open http://localhost:8888
```

## Local testing

```bash
# Run all tests
make test

# Or run Python tests directly
python3 -m unittest discover -s tests -v
```

## CI

- **Test workflow** – runs on push and PRs: fetch script unit tests, JSON validation, HTML structure checks.
- **Update Recent Posts** – runs daily and on manual trigger: fetches Substack RSS, updates `recent-posts.json`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the feature-branch workflow.
