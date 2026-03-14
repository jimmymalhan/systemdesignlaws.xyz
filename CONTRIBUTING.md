# Contributing

All changes must go through a feature branch. Do not commit directly to `main`.

## Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-change-name
   ```

2. **Make your changes** and commit
   ```bash
   git add .
   git commit -m "Your message"
   ```

3. **Push and open a PR**
   ```bash
   git push -u origin feature/your-change-name
   ```

4. **Merge to main** after review (or squash-merge via GitHub).

## Branch naming

Use descriptive prefixes:
- `feature/` — new features or content
- `fix/` — bug fixes
- `docs/` — documentation only

Examples: `feature/landing-page`, `fix/redirect-url`, `docs/readme`.
