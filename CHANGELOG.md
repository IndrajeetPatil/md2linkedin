# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Markdown tables are rendered: the header row in bold, cells joined by
  ` | `, one line per row. They were previously emitted as unreadable
  run-together text (fixes #70).
- `~~strikethrough~~` keeps its text and drops its markers, instead of
  leaving `~~` in the output.

### Changed

- Conversion now runs a real CommonMark parser
  ([`comrak`](https://pypi.org/project/comrak/)) and walks the resulting
  document with [`selectolax`](https://pypi.org/project/selectolax/), in
  place of the pipeline of regular expressions. Every construct is read in
  context, which resolves the whole class of fidelity gaps listed in #70 —
  four-space indented code blocks are code, `>> inner` is a doubly nested
  quote, `[ref]: url` definitions are consumed rather than printed, a
  thematic break inside a list item is a break rather than a bullet, and a
  mixed or renumbered marker starts a new list.
- Blank lines inside a code block are preserved. The old pipeline collapsed
  every run of three or more newlines anywhere in the document.
- `monospace_code=False` strips the fences from a fenced block and keeps the
  content as plain text. It previously left the ` ``` ` fences in the
  output.
- Conversion costs more than it did, because a document is now parsed
  rather than pattern-matched. A LinkedIn-sized post takes a few tens of
  microseconds longer; the parsing itself happens in Rust and C, so the
  cost stays linear in input length.
- Requires Python 3.12 or newer; support for Python 3.10 and 3.11 is discontinued.

### Fixed

- `<script>` and `<style>` in raw HTML are dropped along with their content.
  Both the tags and the code inside them used to be emitted as text.

## [0.4.0] — 2026-09-20

### Fixed

- Bullets nested three or more levels deep keep their nesting. Every item
  indented by at least two spaces was rendered as `  ‣ `, so a grandchild
  item collapsed onto its parent's level. Each level now gets its own marker
  (`•`, `‣`, `◦`, `▪`) and two spaces of indentation (fixes #68).

### Changed

- Bullet nesting depth is counted from the enclosing list items instead of
  from the raw indentation width, so a document indented by four spaces per
  level nests exactly like one indented by two. Output indentation is
  normalized to two spaces per level. Nesting takes at least two extra
  spaces, so an item indented by only one space past its predecessor stays
  its sibling, as Markdown allows a top-level item up to three leading
  spaces. Ordered markers (`1.`) are still kept verbatim, but they are
  re-indented like bullets and they now open a level for bullets nested
  under them — except in the middle of a paragraph, where Markdown only
  lets a list start at number one, so `2. prose` there is left as the prose
  it is instead of nesting what follows it one level too deep.
- A heading (ATX or setext), thematic break, blockquote or fenced code block
  at column zero ends an open list, as Markdown says it does, so an item
  after one restarts its nesting from its own indentation instead of
  continuing the list above. None of them is a paragraph either, so an
  ordered list may start under one whatever its first number is.
- A spaced thematic break (`* * *`, `- - -`) is no longer converted into a
  bullet holding the remaining markers. Markdown reads such a line as a
  break wherever a list item would also fit, so it is now dropped like the
  compact `***` form. The `*` and `_` spellings are dropped before the
  emphasis steps run, which used to pair up the first two markers of
  `* * *` and leave a stray one behind.
- A paragraph after a blank line now ends only the list levels it is not
  indented inside, instead of leaving every level open unless the paragraph
  starts at column zero. A second paragraph of an outer item therefore ends
  the list nested in that item, and the next item there nests one level deep
  rather than two.
- A numbered item only carries on a list that is itself numbered. A `2.`
  standing where a bullet item stands no longer opens a phantom level that
  pushed the items under it one level too deep; it is left as the text it
  is. CommonMark would start a second list there instead, which is a known
  gap rather than the intended reading (see #70).
- A tab may separate a list marker from its content (`-\titem`,
  `1.\titem`), as CommonMark allows. Only a space was recognised before, so
  a tab-formatted list was left unconverted and its ordered items did not
  open a level for the bullets nested under them.
- Documents holding many lines that begin with a number convert in linear
  rather than quadratic time. Deciding whether such a line interrupts a
  paragraph re-read everything above it, so a paragraph followed by 1,600
  `2. prose` lines took about 0.29 seconds and doubling the count roughly
  quadrupled that; the same document now converts in a few milliseconds.

### Documentation

- Added a `Markdown parsing fidelity` section to the documentation, and a
  matching `Limitations` entry in the README, recording the constructs a
  pipeline of regular expressions reads more loosely than a CommonMark
  parser: indented code blocks, nested blockquotes, link reference
  definitions, a thematic break indented inside a list item, tables, and
  list markers that change the kind of list. Each was checked against a
  reference parser, and #70 tracks the rework that would fix them.

## [0.3.0] — 2026-09-18

### Fixed

- Inline code spans and fenced code blocks no longer leak their internal
  protection placeholder into the output. A code span inside a header
  (`` # Heading with `code` ``) or inside emphasis markers (``**`code`**``)
  emitted a NUL control character followed by a run of bold hex digits,
  because the placeholder was built from ASCII alphanumerics that the
  Unicode mapping steps then rewrote. Placeholders now use Private Use Area
  characters, which those steps leave untouched (fixes #63).
- An inline code span that wraps a fenced block (`` ` ```x``` ` ``) no longer
  leaves an unexpanded placeholder in the output. Placeholders are now
  restored in reverse insertion order, so an outer span is expanded before
  the keys nested inside it.
- A single-line fenced run (` ```code``` `) no longer converts to nothing.
  Its body was treated as a language tag and discarded, but a language tag
  is only a language tag when a newline terminates it, so the whole body is
  content.

### Changed

- `convert()` and `convert_file()` are now deterministic. Code placeholders
  were previously derived from `uuid4()`, so any input whose placeholder
  leaked produced different output on every call.
- Documents with many code spans convert faster. Placeholders are restored in
  a single regex pass rather than one `str.replace` scan per placeholder,
  which removes the quadratic cost of that step.
- `to_sans_bold()`, `to_sans_italic()`, `to_sans_bold_italic()`, and
  `to_monospace()` are faster. They now apply precomputed `str.translate()`
  tables instead of building the mapping per character on every call.
- `click` is now required at version 8.5.0 or newer (previously 8.4.0).

## [0.2.3] — 2026-08-05

### Changed

- Updated all dependencies to their latest versions to address security
  vulnerabilities.

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
