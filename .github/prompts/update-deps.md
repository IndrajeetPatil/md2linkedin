---
name: update-deps
description: Update dependencies and ensure the codebase is compatible with the latest versions
---

# Update Dependencies and Refactor Codebase

Run `make update-deps` to refresh `uv` dependencies and `prek` hook revisions. Then iterate
until the full local quality gate passes:

- `make check-package`

Fix any breaking API changes, type errors, lockfile drift, coverage regressions, or lint failures introduced by the upgrades.

Ensure that the minimum versions of updated dependencies in `pyproject.toml` are correctly bumped.

Ensure that all dependencies in `pyproject.toml` remain alphabetically sorted.

If the `uv` version changes, keep its hardcoded versions in sync: `required-version` and the `uv_build` bounds in `pyproject.toml`, and the minimum in `tests/benchmarks/README.md`.

`make update-deps` runs `prek update --freeze`, which refreshes each prek hook to its latest tag but records the resolved commit SHA in `rev` with a `# frozen: <tag>` comment. Ensure that versions of hooks (like `ruff`, `ty`, and `unref`) in `prek.toml` are matching their respective versions in `pyproject.toml`. Never rewrite a frozen `rev` back to a bare mutable tag.

Once the dependency update is green, review relevant changelogs and current documentation for upgraded libraries and CLIs. Apply small compatibility simplifications only when they reduce local complexity or remove a workaround, and rerun the affected checks after each change. Check whether changes in CLIs or dependencies also allow updating or simplifying artifacts relevant for agentic engineering: keep `AGENTS.md`, agentic skills (under `.agents/skills/`), and their referenced assets or instructions aligned whenever tool flags, behaviors, or capabilities change.

## Learn from mistakes

When a check fails, a reviewer raises a finding, or you notice a mistake in
your own work, fix it, then ask what led you to it. If a skill, its scripts or
templates, a prompt, or `AGENTS.md` gave missing, ambiguous, or wrong
guidance, correct that guidance in the same pull request, stating the general
rule rather than the incident. Never weaken a quality gate instead.

## Pull request

Open a ready-for-review (not draft) PR with `gh pr create`. In the PR body, summarise dependency groups changed, compatibility fixes made, validation commands that passed, and any key refactorings as list items.
