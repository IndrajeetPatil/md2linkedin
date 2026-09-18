---
name: update-deps
description: Update dependencies and ensure the codebase is compatible with the latest versions
---

# Update Dependencies and Refactor Codebase

Run `make update-deps` to refresh backend `uv` dependencies and `prek` hook revisions. Then iterate
until the full local quality gate passes:

- `make check-package`

Fix any breaking API changes, type errors, lockfile drift, coverage regressions, or lint failures introduced by the upgrades.

Ensure that the minimum versions of updated dependencies in `pyproject.toml` are correctly bumped.

Ensure that all dependencies in `pyproject.toml` remain alphabetically sorted.

If the `uv` version changes, ensure any hardcoded versions are kept in sync.

`make update-deps` runs `prek update`, which refreshes each prek hook to its latest tag. 
Ensure that versions of hooks (like `ruff` and `ty`) in `prek.toml` are matching their respective versions in `pyproject.toml`.

Once the dependency update is green, review relevant changelogs and current documentation for upgraded libraries. Apply small compatibility simplifications only when they reduce local complexity or remove a workaround, and rerun the affected checks after each change.

Make a draft PR using the `gh` CLI. In the PR body, summarise dependency groups changed, compatibility fixes made, validation commands that passed, and any key refactorings as list items.
