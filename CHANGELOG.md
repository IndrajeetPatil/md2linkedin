# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
