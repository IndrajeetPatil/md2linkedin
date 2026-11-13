---
name: mutation-testing
description: >
  Run and act on mutmut mutation testing: the local run, how to kill
  surviving mutants, and the weekly CI job. Use when asked to run
  mutation tests, when the scheduled mutation-test workflow reports
  survivors, or when strengthening tests beyond line coverage.
---

# Mutation testing

[`mutmut`](https://mutmut.readthedocs.io/) checks whether the test suite
catches semantic changes to the source, not just line coverage.

- Configuration lives in the `[tool.mutmut]` section of `pyproject.toml`.
- Run `make mutation-test` to execute the full run and print the results
  table.
- Kill every surviving mutant with a new test, or restructure the source so
  it cannot express the mutation. `pyproject.toml` deliberately excludes
  nothing from mutation.
- Investigate a single survivor with `uv run mutmut show <mutant-id>` and rerun
  just that mutant with `uv run mutmut run <mutant-id>` after strengthening the
  tests.
- CI runs mutation testing weekly, on `workflow_dispatch`, and on pull
  requests that change `pyproject.toml`, `Makefile`, `uv.lock` or the workflow
  itself (`.github/workflows/mutation-test.yml`). It is intentionally not gated
  on every PR because full runs are slow.
