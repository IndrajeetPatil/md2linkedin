"""Markdown-to-LinkedIn conversion pipeline.

Each step is a small, independently testable function. The top-level
:func:`convert` function wires them together in the correct order to avoid
regex conflicts (e.g. bold-italic must be processed before bold or italic).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from ._unicode import to_monospace, to_sans_bold, to_sans_bold_italic, to_sans_italic

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["convert", "convert_file"]

_ENCODING = "utf-8"

_HTML_ENTITIES = {
    "&gt;": ">",
    "&lt;": "<",
    "&amp;": "&",
    "&nbsp;": " ",
    "&quot;": '"',
    "&apos;": "'",
}

# ── Low-level pipeline steps ───────────────────────────────────────────────────


def _normalize_line_endings(text: str) -> str:
    r"""Normalize Windows (``\r\n``) and classic Mac (``\r``) endings to ``\n``."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


# Placeholder bodies are drawn from the Private Use Area (U+E000+). A
# placeholder has to survive every step between _protect_code and
# _restore_code untouched, and those steps rewrite ASCII alphanumerics
# (to_sans_*) or apply .upper(). PUA codepoints are immune to both, whereas an
# ASCII body gets mangled and the placeholder then leaks into the output (#63).
_PLACEHOLDER_BASE = 0xE000
# Matches any key built above. Restoring via one regex pass beats a str.replace
# per key: the keys are only three characters, and CPython's substring search
# skips much less on a short needle, so repeated scans of a long document
# dominated the conversion.
_PLACEHOLDER_RE = re.compile(r"\x00.\x00", re.DOTALL)


def _protect_code(text: str) -> tuple[str, dict[str, str]]:
    r"""Swap every code span and fenced block for a placeholder.

    Code content must never be transformed by the Unicode mapping steps, so
    it is set aside here and restored once they have run. Each placeholder is
    a Private Use Area character delimited by ``\x00``, chosen so that no
    later pipeline step can alter it; see :data:`_PLACEHOLDER_BASE`. Any
    ``\x00`` already in the text is dropped first, which is what keeps the
    sequentially numbered keys from colliding with content.
    """
    text = text.replace("\x00", "")
    placeholders: dict[str, str] = {}

    def _replace(match: re.Match[str]) -> str:
        key = f"\x00{chr(_PLACEHOLDER_BASE + len(placeholders))}\x00"
        placeholders[key] = match.group(0)
        return key

    # Fenced code blocks (``` or ~~~, with optional language tag)
    text = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", _replace, text)
    # Inline code spans (single backtick only; triple already caught above)
    text = re.sub(r"`[^`\n]+`", _replace, text)
    return text, placeholders


def _restore_code(
    text: str,
    placeholders: dict[str, str],
    *,
    monospace: bool = False,
) -> str:
    """Restore code placeholders to their original content.

    Inline code keeps its content without the surrounding backticks; a fenced
    block is kept whole so its structure survives. Under *monospace*, code is
    mapped to Unicode Mathematical Monospace: only ASCII letters and digits
    are mapped and everything else (including Markdown syntax) passes through,
    so no nested processing is needed.

    Placeholders are expanded one pass at a time until the text stops
    changing. :func:`_protect_code` matches fenced blocks before inline spans,
    so an inline span wrapping a fenced run swallowed the fenced key into its
    own stored value; expanding the outer span reintroduces that inner key for
    the next pass to resolve.
    """

    def _expand(match: re.Match[str]) -> str:
        original = placeholders[match.group(0)]
        if original.startswith(("```", "~~~")):
            if monospace:
                # Strip fences and optional language tag, convert content
                fence = original[:3]
                rest = original[3:]
                # Remove closing fence
                closing_fence = rest.rfind(fence)
                body = rest[:closing_fence]
                # Strip the optional language tag, which is only a language tag
                # when a newline terminates it. A single-line run (```hi```) has
                # no tag, so find returns -1 and the slice keeps the whole body.
                content = body[body.find("\n") + 1 :]
                return to_monospace(content)
            # Keep fenced blocks as-is (no backtick stripping)
            return original
        if monospace:
            # Strip backticks and apply monospace for inline code
            return to_monospace(original[1:-1])
        # Strip the surrounding backticks for inline code
        return original[1:-1]

    while placeholders:
        new_text = _PLACEHOLDER_RE.sub(_expand, text)
        if new_text == text:
            break
        text = new_text
    return text


def _strip_html_spans(text: str) -> str:
    """Remove ``<span ...>...</span>`` wrappers, keeping inner text.

    Iterates until no span tags remain, so that arbitrarily nested spans are
    fully unwrapped.
    """
    while True:
        new_text = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", text, flags=re.DOTALL)
        if new_text == text:
            return text
        text = new_text


# Emphasis markers. Each style has an asterisk variant and an underscore
# variant, applied in that order; ``(?<!\\)`` skips backslash-escaped markers.
_BOLD_ITALIC_PATTERNS = (
    r"(?<!\\)\*{3}(.+?)(?<!\\)\*{3}",
    r"(?<!\\)_{3}(.+?)(?<!\\)_{3}",
)
_BOLD_PATTERNS = (
    r"(?<!\\)\*{2}(.+?)(?<!\\)\*{2}",
    r"(?<!\\)__(.+?)(?<!\\)__",
)
# Italic also needs negative look-around, so that residual ** markers are never
# matched, and word-boundary anchors, so that inside_words is left alone.
_ITALIC_PATTERNS = (
    r"(?<!\\)(?<!\*)\*(?!\*)(.+?)(?<!\\)(?<!\*)\*(?!\*)",
    r"(?<!\w)(?<!\\)_(?!_)(.+?)(?<!\\)(?<!_)_(?!\w)",
)


def _style_markers(
    text: str,
    patterns: tuple[str, ...],
    style: Callable[[str], str],
) -> str:
    """Apply *style* to the text captured by each emphasis pattern in turn."""
    for pattern in patterns:
        text = re.sub(pattern, lambda m: style(m.group(1)), text)
    return text


def _convert_bold_italic(text: str) -> str:
    r"""Replace ``***text***`` (or ``___text___``) with bold-italic Unicode.

    Must run before :func:`_convert_bold` and :func:`_convert_italic`, or the
    triple markers are consumed piecemeal by them. Backslash-escaped markers
    (``\***``) are not matched.
    """
    return _style_markers(text, _BOLD_ITALIC_PATTERNS, to_sans_bold_italic)


def _convert_bold(text: str) -> str:
    r"""Replace ``**text**`` (or ``__text__``) with bold Unicode."""
    return _style_markers(text, _BOLD_PATTERNS, to_sans_bold)


def _convert_italic(text: str) -> str:
    r"""Replace ``*text*`` or ``_text_`` with italic Unicode.

    Negative look-around keeps the asterisks of bold (``**``) and bold-italic
    (``***``) markers, already consumed by earlier steps, from matching here.
    """
    return _style_markers(text, _ITALIC_PATTERNS, to_sans_italic)


def _convert_headers(text: str) -> str:
    """Convert ATX (``# Heading``) and setext headers to styled text.

    H1 gets bold Unicode framed by a ``━`` border; H2–H6 get the bold mapping
    alone. Standalone horizontal rules are dropped.
    """
    separator = "━" * 40

    def _fmt_h1(title: str) -> str:
        clean = title.strip()
        return f"\n{separator}\n{to_sans_bold(clean.upper())}\n{separator}\n"

    def _fmt_h2(title: str) -> str:
        return to_sans_bold(title.strip())

    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # ATX headers
        atx = re.match(r"^(#{1,6})\s+(.*)", line)
        if atx:
            level = len(atx.group(1))
            title = atx.group(2)
            if level == 1:
                out.append(_fmt_h1(title))
            else:
                out.append(_fmt_h2(title))
            i += 1
            continue
        # Setext headers: next line is === or ---
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if re.match(r"^={3,}\s*$", next_line):
                out.append(_fmt_h1(line))
                i += 2
                continue
            if re.match(r"^-{3,}\s*$", next_line) and line.strip():
                out.append(_fmt_h2(line))
                i += 2
                continue
        # Standalone horizontal rules (---, ___, ***)
        if re.match(r"^(-{3,}|_{3,}|\*{3,})\s*$", line):
            i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def _strip_links(text: str, *, preserve: bool = False) -> str:
    """Reduce Markdown links to their display text.

    Inline, reference-style and autolink syntax all lose their URL. An empty
    link (``[](url)``) is dropped entirely. Under *preserve*, the link syntax
    is left exactly as it was.
    """
    if preserve:
        return text
    # Remove empty links [](url)
    text = re.sub(r"\[\]\([^)]*\)", "", text)
    # Inline links [text](url "optional title") → text
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # Reference-style links [text][ref] → text
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", text)
    # Autolinks <https://example.com> → https://example.com
    return re.sub(r"<(https?://[^>]+)>", r"\1", text)


def _strip_images(text: str) -> str:
    """Replace Markdown images with their alt text (or nothing if empty)."""
    # ![alt](url) → alt  (empty alt → removed)
    return re.sub(
        r"!\[([^\]]*)\]\([^)]*\)",
        lambda m: m.group(1) or "",
        text,
    )


# One marker per nesting level, outermost first. Depths beyond the last entry
# reuse it; their indentation keeps conveying how deep they are.
_BULLET_MARKERS = ("•", "‣", "◦", "▪")
_INDENT_UNIT = 2  # spaces emitted per nesting level
_TAB_WIDTH = 4  # spaces a tab stands for when measuring source indentation
# Bullet (``-``/``*``/``+``) and ordered (``1.``/``1)``) list items. An ordered
# marker is kept verbatim in the output and is matched only so that it can open
# a level for the bullets nested underneath it; its number is captured all the
# same, because CommonMark lets a number other than ``1`` start a list only
# where no paragraph is being interrupted. The number is spelled out as one to
# nine ASCII digits, as CommonMark defines it, so that a line of prose
# beginning with a longer number or with non-ASCII digits (``\d`` matches those
# too) cannot push a phantom level onto the nesting stack. Either a space or a
# tab may separate the marker from the content, as CommonMark allows.
_LIST_ITEM_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?:(?P<bullet>[-*+])|(?P<number>[0-9]{1,9})[.)])[ \t]",
    re.MULTILINE,
)
# A block construct at column zero: an ATX heading, a blockquote or a thematic
# break. None of them can be the lazy continuation of a list item's paragraph,
# so each one both ends an open list and rules out the paragraph an ordered
# marker below it would otherwise be interrupting. Indented ones belong to the
# item they sit under, which is why matches are anchored to column zero.
_BLOCK_START = r"#{1,6}(?:[ \t]|$)|>|(?:[-_*][ \t]*){3,}$"
_BLOCK_START_RE = re.compile(_BLOCK_START)
# Where an open list ends. Either a blank line followed by a paragraph at
# column zero, or one of the block constructs above. Neither half of the first
# alternative is enough on its own: a blank line alone only makes the list
# loose, and a column-zero line that follows an item directly is a lazy
# continuation of that item's paragraph. Indented lines are continuation
# paragraphs and never end the list.
_LIST_BREAK_RE = re.compile(rf"\n[ \t]*\n\S|\n(?:{_BLOCK_START})", re.MULTILINE)
_TOP_LEVEL_BULLET_RE = re.compile(r"^[-*+][ \t]", re.MULTILINE)


def _has_indented_line(text: str) -> bool:
    """Report whether any line of *text* starts with a space or a tab."""
    return text.startswith((" ", "\t")) or "\n " in text or "\n\t" in text


def _interrupts_paragraph(text: str, start: int) -> bool:
    """Report whether the line beginning at *start* cuts into a paragraph.

    It does when the line above holds prose, and Markdown only lets an ordered
    item do that when its number is ``1``. A blank line, a block construct
    such as a heading, and the top of the document are all paragraph-free, so
    a list may start under any of them whatever its first number is.
    """
    # ``start`` sits at the beginning of a line, so the text before it ends
    # with the preceding line — unless there is no preceding line at all.
    preceding_lines = text[:start].splitlines()
    if not preceding_lines:
        return False
    previous = preceding_lines[-1]
    return bool(previous.strip()) and not _BLOCK_START_RE.match(previous)


def _convert_bullets(text: str) -> str:
    """Replace Markdown list markers with Unicode bullet characters.

    Nesting depth is counted from the enclosing list items rather than from
    the raw indentation, so a document indented by four spaces per level
    nests exactly like one indented by two (fixes #68): ``- `` → ``• ``, then
    ``  ‣ ``, ``    ◦ ``, and ``      ▪ `` two further spaces per level beyond
    that. Output indentation is therefore normalized to two spaces per level.

    Nesting takes at least two extra spaces, because Markdown allows a
    top-level item up to three leading spaces; a smaller increase makes the
    item a sibling of its predecessor. A list whose first item is already
    indented has no enclosing item to count from, so its depth comes from
    that indentation instead.

    Ordered markers (``1. ``) are kept verbatim, since the numbers already
    convey order, but they are re-indented like bullets and they open a level
    for the bullets nested under them. One that would start a list in the
    middle of a paragraph opens nothing unless it is numbered ``1``, which is
    the only number Markdown lets interrupt a paragraph; anything else there
    is prose that happens to begin with a number.
    """
    if not _has_indented_line(text):
        # Nothing is indented, so no item can be nested and one constant
        # substitution does the whole job.
        return _TOP_LEVEL_BULLET_RE.sub(f"{_BULLET_MARKERS[0]} ", text)

    # (source indent width, output depth) for each currently open list level.
    levels: list[tuple[int, int]] = []
    out: list[str] = []
    pos = 0

    for match in _LIST_ITEM_RE.finditer(text):
        # Everything since the previous item: the tail of its line, plus any
        # lines in between. A blank line and then a paragraph at column zero
        # in there closes the list.
        gap = text[pos : match.start()]
        if _LIST_BREAK_RE.search(gap):
            levels.clear()

        # Close every level this item is not nested inside, its own included,
        # then reopen its level one deeper than whatever still encloses it.
        # Nesting under a level takes a full indent unit: Markdown permits up
        # to three leading spaces on a top-level item, so a smaller increase
        # marks a sibling rather than a child.
        width = len(match.group("indent").expandtabs(_TAB_WIDTH))
        depth = width // _INDENT_UNIT
        closed: int | None = None
        while levels and width < levels[-1][0] + _INDENT_UNIT:
            closed = levels.pop()[1]

        number = match.group("number")
        if (
            closed is None
            and number is not None
            and int(number) != 1
            and _interrupts_paragraph(text, match.start())
        ):
            # An ordered marker numbered something other than one may not open
            # a list in the middle of a paragraph, so this is prose. Closing no
            # level above means nothing was popped, so the stack is untouched
            # and the line can simply be left to the next item's gap.
            continue

        if levels:
            depth = levels[-1][1] + 1
        elif closed is not None:
            # Nothing encloses this item, but it is a sibling of the level it
            # just closed, so it cannot sit deeper than that level did. Its
            # own indentation still caps it, which is what pulls a dedent back
            # out (``    - deep`` followed by ``- top``).
            depth = min(depth, closed)
        levels.append((width, depth))

        indent = " " * (_INDENT_UNIT * depth)
        bullet = match.group("bullet")
        if bullet is None:
            # Ordered: keep ``1. `` verbatim, drop only its indentation.
            marker = text[match.end("indent") : match.end()]
        else:
            marker = f"{_BULLET_MARKERS[min(depth, len(_BULLET_MARKERS) - 1)]} "
        out.extend((gap, indent + marker))
        pos = match.end()

    out.append(text[pos:])
    return "".join(out)


def _strip_blockquotes(text: str) -> str:
    """Remove leading ``>`` blockquote markers."""
    return re.sub(r"^> ?", "", text, flags=re.MULTILINE)


def _clean_entities(text: str) -> str:
    """Decode common HTML entities to their literal characters."""
    for entity, char in _HTML_ENTITIES.items():
        text = text.replace(entity, char)
    return text


def _clean_escaped_chars(text: str) -> str:
    r"""Resolve Markdown backslash escapes (``\*`` → ``*``)."""
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!])", r"\1", text)


def _normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines and trim the edges.

    LinkedIn renders at most two consecutive blank lines meaningfully, so
    longer runs are collapsed and the result ends in a single newline.
    """
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


# ── Public API ─────────────────────────────────────────────────────────────────


def convert(
    text: str,
    *,
    preserve_links: bool = False,
    monospace_code: bool = True,
) -> str:
    r"""Convert Markdown text to LinkedIn-compatible Unicode plain text.

    Bold (``**text**`` / ``__text__``), italic (``*text*`` / ``_text_``), and
    bold-italic (``***text***`` / ``___text___``) markers are replaced with
    their Unicode Mathematical Sans-Serif equivalents so that the styling is
    preserved when pasting into LinkedIn or other plain-text rich editors.

    The following Markdown constructs are also handled:

    * **Headers** — ATX (``#``) and setext styles; H1 gets a ``━`` border.
    * **Code spans** — backticks stripped; content converted to Unicode
      Monospace by default (see *monospace_code*).
    * **Fenced code blocks** — fences stripped and content converted to
      Unicode Monospace by default (see *monospace_code*).
    * **Links** — stripped to display text by default (see *preserve_links*).
    * **Images** — replaced by alt text.
    * **Bullet lists** — ``-`` / ``*`` / ``+`` → ``•``, with one marker per
      nesting level (``‣``, ``◦``, ``▪``) and two spaces of indent per level.
    * **Blockquotes** — leading ``>`` stripped.
    * **HTML spans** — unwrapped, inner text kept.
    * **HTML entities** — decoded to literal characters.
    * **Backslash escapes** — resolved (``\\*`` → ``*``).
    * **Windows line endings** — normalised to ``\\n``.

    Args:
        text: The Markdown source string.
        preserve_links: When ``True``, link syntax (``[text](url)``) is left
            unchanged in the output instead of being reduced to display text.
        monospace_code: When ``True`` (the default), inline code spans and
            fenced code blocks are rendered in Unicode Mathematical Monospace.
            When ``False``, inline code is kept as plain text and fenced
            blocks are preserved verbatim.

    Returns:
        A plain-text string suitable for pasting into LinkedIn.

    Examples:
        >>> convert("**Hello**, *world*!")
        '𝗛𝗲𝗹𝗹𝗼, 𝘸𝘰𝘳𝘭𝘥!\\n'

        >>> convert("")
        ''

    """
    if not text or not text.strip():
        return ""

    text = _normalize_line_endings(text)
    text, placeholders = _protect_code(text)
    text = _strip_html_spans(text)
    text = _strip_images(text)
    # Before the headers are styled: list nesting reads the headings, thematic
    # breaks and blockquotes around a list to know where it ends, and header
    # conversion replaces that syntax with plain styled text.
    text = _convert_bullets(text)
    text = _convert_bold_italic(text)
    text = _convert_bold(text)
    text = _convert_italic(text)
    text = _convert_headers(text)
    text = _strip_links(text, preserve=preserve_links)
    text = _strip_blockquotes(text)
    text = _restore_code(text, placeholders, monospace=monospace_code)
    text = _clean_entities(text)
    text = _clean_escaped_chars(text)
    return _normalize_whitespace(text)


def convert_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    preserve_links: bool = False,
    monospace_code: bool = True,
) -> Path:
    r"""Convert a Markdown file and write the result to a ``.txt`` file.

    Args:
        input_path: Path to the Markdown source file (``.md`` or any text
            file).
        output_path: Destination path for the converted output.  Defaults to
            the input path with the extension replaced by
            ``.linkedin.txt``.
        preserve_links: Passed through to :func:`convert`.
        monospace_code: Passed through to :func:`convert`.

    Returns:
        The resolved path of the written output file.

    Raises:
        FileNotFoundError: If *input_path* does not exist.

    Examples:
        >>> from pathlib import Path
        >>> import tempfile, os
        >>> with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        ...     _ = f.write("**bold** and *italic*")
        ...     tmp = f.name
        >>> out = convert_file(tmp)
        >>> out.read_text(encoding="utf-8")
        '𝗯𝗼𝗹𝗱 and 𝘪𝘵𝘢𝘭𝘪𝘤\\n'
        >>> os.unlink(tmp)
        ... os.unlink(str(out))

    """
    input_path = Path(input_path)
    if not input_path.exists():
        msg = f"Input file not found: {input_path}"
        raise FileNotFoundError(msg)

    if output_path is None:
        output_path = input_path.with_suffix("").with_suffix(".linkedin.txt")
    output_path = Path(output_path)

    md_text = input_path.read_text(encoding=_ENCODING)
    result = convert(
        md_text,
        preserve_links=preserve_links,
        monospace_code=monospace_code,
    )
    output_path.write_text(result, encoding=_ENCODING)
    return output_path
