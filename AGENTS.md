# Agent Instructions

This is a Python package repository following standard development practices.

## Project Structure
- `src/`: Contains the main package code.
- `tests/`: Contains the `pytest` test suite.
- `docs/`: Contains documentation files.
- `pyproject.toml`: The primary configuration file for metadata and tools.
- `uv.lock`: Lockfile ensuring reproducible environments.

## Setup & Dependencies
- We use [`uv`](https://github.com/astral-sh/uv) for fast package and environment management.
- **Do not** use `pip`, `pipenv`, or `poetry` directly.
- **Do not** manually edit `uv.lock`.
- To reproduce the locked environment, run `uv sync`.
- To explicitly upgrade dependencies and pre-commit hooks, run `make update-deps`.

## Code Quality & Testing
- Code formatting and linting are handled by `ruff`, and type checking by `ty`. We use `pyrefly` to enforce 100% type coverage.
- If `pyrefly` and `ty` conflict on any issue, `ty` should win.
- Pre-commit hooks are configured via `prek`.
- **Do not** commit code with linting errors, type warnings, or failing tests.
- Always run `make qa` to format, lint, type-check, and audit dependencies.
- Run `make check-package` to run the full validation suite (QA + Tests + Build).
- **Do not** bypass the `Makefile`; rely on its targets for standardized workflows.

## Docstrings & Comments
- Only the public API carries docstrings: `convert()`, `convert_file()`, the
  `_unicode` mapping functions, the CLI `main()` (its docstring *is* the
  `--help` text), and the module docstrings that orient a reader entering a
  file. These are what `mkdocstrings` renders and what `help()` shows.
- **Do not** write docstrings for internal functions — anything with a leading
  underscore, such as `_has_indented_line()` or `_strip_images()`. Their
  `Args:`/`Returns:` sections only restate the signature and go stale.
- When an internal function *does* need explaining (an ordering constraint, a
  non-obvious algorithm, a workaround and its reason), put a short comment
  immediately above the `def`, and keep step-by-step notes as inline comments
  in the body. Explain *why*, not *what*.
- Ruff's `pydocstyle` rules only demand docstrings on public names, so this
  convention needs no ignores in `pyproject.toml`. If a future rule does flag
  an undocumented internal function, relax that rule rather than reinstating
  the docstring.

## Mutation Testing
- We use [`mutmut`](https://mutmut.readthedocs.io/) to check whether the test
  suite actually catches semantic changes to the source, not just line coverage.
- Configuration lives in the `[tool.mutmut]` section of `pyproject.toml`.
- Run `make mutation-test` locally to execute the full mutation run and print
  the results table. All surviving mutants MUST be either killed by a new test
  or explicitly justified as equivalent via `do_not_mutate_patterns` in
  `pyproject.toml` (with a comment explaining why).
- CI runs mutation testing on a weekly schedule and on `workflow_dispatch`;
  see `.github/workflows/mutation-test.yml`. It is intentionally NOT gated on
  every PR because full runs are slow.
- Investigate a single surviving mutant with `uv run mutmut show <mutant-id>`
  and rerun just that mutant with `uv run mutmut run <mutant-id>` after
  strengthening the tests.

## Contribution Workflow
1. Ensure you are on a feature branch.
2. Implement your code changes within `src/` and corresponding tests within `tests/`.
3. Verify all changes by running `make check-package`.
4. Commit your changes and push to the branch to update the Pull Request.



## Security
- **Code Scanning Alerts**: During the release process, code scanning alerts should be checked via the GitHub API (`gh api repos/IndrajeetPatil/md2linkedin/code-scanning/alerts`).
- If alerts are false positives or occur in tests, they should be dismissed using `gh api -X PATCH repos/IndrajeetPatil/md2linkedin/code-scanning/alerts/{number} -f state=dismissed -f dismissed_reason="..."` (valid reasons: "false positive", "won't fix", "used in tests").

## Release Process
To create a new release, use the prompt defined in `.github/prompts/create-release.md`. That prompt will direct you on how to proceed.
