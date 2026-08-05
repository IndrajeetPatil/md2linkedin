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
- Code formatting and linting are handled by `ruff`, and type checking by `ty`.
- Pre-commit hooks are configured via `prek`.
- **Do not** commit code with linting errors, type warnings, or failing tests.
- Always run `make qa` to format, lint, type-check, and audit dependencies.
- Run `make check-package` to run the full validation suite (QA + Tests + Build).
- **Do not** bypass the `Makefile`; rely on its targets for standardized workflows.

## Contribution Workflow
1. Ensure you are on a feature branch.
2. Implement your code changes within `src/` and corresponding tests within `tests/`.
3. Verify all changes by running `make check-package`.
4. Commit your changes and push to the branch to update the Pull Request.

## Release Process
To release a new version of this package on PyPI and GitHub:
1. Ensure all tests and QA checks pass (`make check-package`).
2. Verify that the version in `pyproject.toml` is correctly bumped.
3. Build the package distribution files (sdist and wheel) by running `make build`.
4. Publish the package to PyPI using `uv publish`.
5. Create a new release on GitHub using the GitHub CLI: `gh release create v<new_version> --title "v<new_version>" --generate-notes`.
6. **Release Notes Formatting**: The GitHub release body/notes must perfectly match the formatting of the newly added entry in `CHANGELOG.md` to maintain stylistic consistency with past releases. Do not rely entirely on the auto-generated release notes (which just list PRs); you should manually provide or edit the release notes (e.g. `gh release edit <tag> --notes-file ...`) to match the CHANGELOG.

## Security
- **Code Scanning Alerts**: During the release process, code scanning alerts should be checked via the GitHub API (`gh api repos/IndrajeetPatil/md2linkedin/code-scanning/alerts`).
- If alerts are false positives or occur in tests, they should be dismissed using `gh api -X PATCH repos/IndrajeetPatil/md2linkedin/code-scanning/alerts/{number} -f state=dismissed -f dismissed_reason="..."` (valid reasons: "false positive", "won't fix", "used in tests").
