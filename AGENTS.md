# Agent Instructions

## Project Structure
- `src/`: Contains the main package code.
- `tests/`: Contains the `pytest` test suite. `tests/benchmarks/` holds the
  performance benchmarks behind the CI regression gate; see its `README.md`.
- `docs/`: Contains documentation files.
- `README.md`: Also the documentation homepage — `docs/index.md` only
  includes it via `--8<--`, so edit `README.md`, never `docs/index.md`. Its
  Python examples run in `tests/test_readme.py`, which compares each one's
  output with the fenced block after its `<!--pytest-codeblocks:expected-output-->`
  marker; update that block when a converter change alters the output.
- `CHANGELOG.md`: Also the documentation changelog page — `docs/changelog.md`
  only includes it via `--8<--`, so edit `CHANGELOG.md`, never
  `docs/changelog.md`.
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
- `make format` adds missing trailing commas (Ruff `COM812`,
  `missing-trailing-comma`, intentionally enabled despite Ruff's formatter
  warning) before `ruff format`, preserving multiline layouts.
- If `pyrefly` and `ty` conflict on any issue, `ty` should win.
- Pre-commit hooks are configured via `prek`.
- **Do not** commit code with linting errors, type warnings, or failing tests.
- Always run `make qa` to format, lint, type-check, check type coverage, and audit dependencies.
- Run `make check-package` to run the full validation suite (QA + Tests + Build).
- After changing `docs/`, `README.md`, `CHANGELOG.md`, `mkdocs.yml` or a public
  docstring, also run `make build-docs`, a strict build that fails on warnings.
- **Do not** bypass the `Makefile`; rely on its targets for standardized workflows.

## Docstrings & Comments
- The public API — `convert()`, `convert_file()`, the `_unicode` mapping
  functions, and the CLI `main()` (whose docstring *is* the `--help` text) —
  carries full Google-style docstrings with `Args:`, `Returns:`, `Raises:`,
  and `Examples:` sections. These are what `mkdocstrings` renders on the
  documentation site and what `help()` shows, so they are written for someone
  who cannot see the implementation.
- Internal functions — anything with a leading underscore, such as the
  helpers and `Renderer` methods in `_converter.py` — get a **description only**:
  a summary line, plus as many paragraphs as the behaviour genuinely warrants.
  Say what the step does and why it exists; ordering constraints, non-obvious
  algorithms and workarounds belong here and are worth spelling out.
- **Do not** give an internal function `Args:`, `Returns:`, or `Raises:`
  sections. They restate a signature the reader is already looking at, and
  they go stale. Module docstrings stay as they are.
- Step-by-step notes about individual lines stay as inline comments in the
  body rather than migrating into the docstring.
- Ruff's pydoclint rules `DOC201`, `DOC402` and `DOC501` are ignored in
  `pyproject.toml` (by name: `docstring-missing-returns`,
  `docstring-missing-yields`, `docstring-missing-exception`) because they cannot tell public from internal functions; the
  public API's sections are upheld in review. If another rule flags a
  description-only docstring, relax that rule rather than padding the docstring.

## Contribution Workflow
1. Ensure you are on a feature branch.
2. Implement your code changes within `src/` and corresponding tests within `tests/`.
3. Verify all changes by running `make check-package`.
4. Commit your changes and push to the branch to update the Pull Request.

## Release Process
To create a new release, follow `.github/prompts/create-release.md` (it covers
the code-scanning alert check).

## Agent Skills
Skills live in `.agents/skills/<name>/SKILL.md`. Load one before its task:

| Skill | Load before |
| --- | --- |
| `mutation-testing` | Running mutmut, acting on surviving mutants or the weekly mutation-test report |
