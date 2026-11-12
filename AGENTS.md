# Agent Instructions

## Single-source docs
- `README.md` is also the documentation homepage: `docs/index.md` only
  includes it via `--8<--`, so edit `README.md`, never `docs/index.md`. Its
  Python examples run in `tests/test_readme.py`, which compares each one's
  output with the fenced block after its `<!--pytest-codeblocks:expected-output-->`
  marker; update that block when a converter change alters the output.
- `CHANGELOG.md` is also the documentation changelog page: `docs/changelog.md`
  only includes it via `--8<--`, so edit `CHANGELOG.md`, never
  `docs/changelog.md`. Separate two changelog entries with a blank line, so
  each bullet stands apart from the next.

## Tooling
- Use `uv` for environments and dependencies, not `pip`, `pipenv` or `poetry`,
  and never edit `uv.lock` by hand.
- Use the `Makefile` targets rather than calling the tools directly. `make
  format` applies Ruff's `missing-trailing-comma` fix before `ruff format`,
  so a bare `ruff format` collapses intentional multiline layouts.
- To upgrade dependencies and hooks, follow `.github/prompts/update-deps.md`.
- If `pyrefly` and `ty` disagree on an issue, `ty` wins.

## Checks
- `make check-package` (tests with 100% coverage, QA, build) and
  `make hooks` (`prek` hooks from `prek.toml`) must pass before committing.
- After changing `docs/`, `README.md`, `CHANGELOG.md`, `mkdocs.yml` or a public
  docstring, also run `make build-docs`, a strict build that fails on warnings.
- The benchmarks in `tests/benchmarks/` back a CI regression gate; see its
  `README.md`.

## Docstrings & Comments
- The public API — `convert()`, `convert_file()`, the `_unicode` mapping
  functions, and the CLI `main()` (whose docstring *is* the `--help` text) —
  carries full Google-style docstrings with `Args:`, `Returns:`, `Raises:`,
  and `Examples:` sections. These are what `mkdocstrings` renders on the
  documentation site and what `help()` shows, so they are written for someone
  who cannot see the implementation.
- Internal functions — anything with a leading underscore, such as the
  helpers and `Renderer` methods in `_converter.py` — get a description only:
  a summary line, plus as many paragraphs as the behaviour genuinely warrants.
  Say what the step does and why it exists; ordering constraints, non-obvious
  algorithms and workarounds belong here and are worth spelling out.
- Do not give an internal function `Args:`, `Returns:`, or `Raises:`
  sections. They restate a signature the reader is already looking at, and
  they go stale. Module docstrings stay as they are.
- Step-by-step notes about individual lines stay as inline comments in the
  body rather than migrating into the docstring.
- Ruff's `docstring-missing-returns`, `docstring-missing-yields` and
  `docstring-missing-exception` rules are ignored in `pyproject.toml` because
  they cannot tell public from internal functions; the public API's sections
  are upheld in review. If another rule flags a description-only docstring,
  relax that rule rather than padding the docstring.

## Release Process
To create a new release, follow `.github/prompts/create-release.md` (it covers
the code-scanning alert check).

## Agent Skills
Skills live in `.agents/skills/<name>/SKILL.md`. Load one before its task:

| Skill | Load before |
| --- | --- |
| `mutation-testing` | Running mutmut, acting on surviving mutants or the weekly mutation-test report |
