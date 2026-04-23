# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] — 2026-04-23

### Fixed

- First list item after a heading was misclassified as a sub-item (`‣` instead
  of `•`) because the bullet-nesting regex matched newlines as indentation
  (fixes #10).

### Changed

- Updated all dependencies to their latest versions to address security
  vulnerabilities.

## [0.2.1] — 2026-04-07

### Documentation

- Added a `Limitations` section to the README documenting known trade-offs of
  Unicode Mathematical Alphanumeric Symbols: visual alignment issues in code
  blocks and tables, reduced accessibility for screen readers, and reduced
  searchability on LinkedIn.

## [0.2.0] — 2026-04-06

### Added

- Code spans and fenced code blocks are now rendered in Unicode Mathematical
  Monospace font by default, making code visually distinct in LinkedIn posts.
- New `monospace_code` parameter for `convert()` and `convert_file()` (default:
  `True`). Set to `False` to restore the previous plain-text behavior.
- New `--no-monospace-code` CLI flag to disable monospace code rendering.
- New `to_monospace()` Unicode mapping function for programmatic use.

## [0.1.1] — 2026-04-06

### Fixed

- Fixed logo not appearing on PyPI page.

## [0.1.0] — 2026-04-05

### Added

- Initial release of `md2linkedin`.
- `convert()` function for converting Markdown strings to LinkedIn-compatible
  Unicode plain text.
- `convert_file()` function for file-based conversion with automatic
  `.linkedin.txt` output naming.
- Unicode mapping functions: `to_sans_bold()`, `to_sans_italic()`,
  `to_sans_bold_italic()`, and `apply_style()`.
- Support for: bold (`**`/`__`), italic (`*`/`_`), bold-italic (`***`/`___`),
  ATX headers (`#`–`######`), setext headers, fenced code blocks, inline code,
  links, images, bullet lists, blockquotes, HTML spans, HTML entities, and
  backslash escapes.
- `--preserve-links` flag to retain Markdown link syntax in output.
- `md2linkedin` CLI entry point with stdin support.
- Full test suite with 100% code coverage.
