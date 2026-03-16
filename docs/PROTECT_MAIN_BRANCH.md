# Protect Main Branch

Keep `main` protected with the checked-in GitHub ruleset before starting new work or merging a PR.

## Apply the ruleset

```bash
./.github/scripts/sync_main_ruleset.sh
```

The script creates or updates the `Protect main` ruleset from `.github/rulesets/main.json`.

## What the ruleset enforces

- Block branch deletion
- Block force pushes
- Require pull requests before merge
- Require `test` and `e2e-website` to pass

## Verify on GitHub

```bash
gh api repos/jimmymalhan/systemdesignlaws.xyz/rulesets --jq '.[] | {name: .name, enforcement: .enforcement}'
```

You should see an active ruleset named `Protect main`.
