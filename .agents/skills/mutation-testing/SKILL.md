---
name: mutation-testing
description: >
  Run and act on mutmut mutation testing: the local run, how to kill or
  justify surviving mutants, and the weekly CI job. Use when asked to run
  mutation tests, when the scheduled mutation-test workflow reports
  survivors, or when strengthening tests beyond line coverage.
---

# Mutation testing

[`mutmut`](https://mutmut.readthedocs.io/) checks whether the test suite
catches semantic changes to the source, not just line coverage.

- Configuration lives in the `[tool.mutmut]` section of `pyproject.toml`.
- Run `make mutation-test` to execute the full run and print the results
  table.
- Every surviving mutant MUST be either killed by a new test or explicitly
  justified as equivalent via `do_not_mutate_patterns` in `pyproject.toml`
  (with a comment explaining why).
- Investigate a single survivor with `uv run mutmut show <mutant-id>` and rerun
  just that mutant with `uv run mutmut run <mutant-id>` after strengthening the
  tests.
- CI runs mutation testing weekly and on `workflow_dispatch`
  (`.github/workflows/mutation-test.yml`). It is intentionally not gated on
  every PR because full runs are slow.
