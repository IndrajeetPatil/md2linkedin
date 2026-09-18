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

_NESTED_BULLET_MIN_INDENT = 2  # spaces of indentation that triggers a nested bullet (‣)
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
    r"""Normalize Windows (\\r\\n) and classic Mac (\\r) line endings to \\n.

    Returns:
        Text containing only Unix-style line endings.

    """
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
    r"""Replace code spans and fenced blocks with unique placeholders.

    Code content must never be transformed by the Unicode mapping steps.

    Each placeholder is a Private Use Area character delimited by ``\x00``,
    chosen so that no later pipeline step can alter it; see
    :data:`_PLACEHOLDER_BASE`. Any ``\x00`` already in *text* is dropped,
    which is what keeps the sequentially numbered keys from colliding with
    content that happens to contain Private Use Area characters.

    Args:
        text: Markdown text.

    Returns:
        A ``(modified_text, placeholder_map)`` tuple where *placeholder_map*
        maps each placeholder back to its original code string.

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

    For inline code, the surrounding backticks are stripped (the plain text
    content is kept). For fenced blocks, the entire original block is kept
    intact so structure is preserved.

    When *monospace* is ``True``, code content is converted to Unicode
    Mathematical Monospace characters. Only ASCII letters and digits are
    mapped; all other characters (including Markdown syntax) pass through
    unchanged, so no nested processing is needed.

    All placeholders are expanded in a single pass, repeated until the text
    stops changing. :func:`_protect_code` matches fenced blocks before inline
    spans, so an inline span that wraps a fenced run swallows the fenced
    placeholder into its own stored value; expanding the outer span
    reintroduces the inner key, which the next pass resolves.

    Args:
        text: Text containing placeholders.
        placeholders: Map of placeholder → original code string.
        monospace: When ``True``, apply monospace Unicode mapping to code.

    Returns:
        Text with all placeholders replaced by their original code content.

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
                # Strip optional language tag (first line of body)
                first_nl = body.find("\n")
                content = body[first_nl + 1 :] if first_nl != -1 else ""
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

    Iterates until no more span tags remain so that arbitrarily nested
    spans are fully unwrapped.

    Args:
        text: Input text that may contain HTML span elements.

    Returns:
        Text with all span elements removed and their inner content preserved.

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
    """Apply *style* to the text captured by each emphasis pattern in turn.

    Args:
        text: Input text.
        patterns: Regexes whose first capture group is the text to style.
        style: Unicode mapping function applied to each captured group.

    Returns:
        Text with every matched marker pair replaced by styled Unicode.

    """
    for pattern in patterns:
        text = re.sub(pattern, lambda m: style(m.group(1)), text)
    return text


def _convert_bold_italic(text: str) -> str:
    r"""Replace ``***text***`` (or ``___text___``) with bold-italic Unicode.

    Must run before :func:`_convert_bold` and :func:`_convert_italic` to
    prevent the triple markers from being consumed piecemeal.

    Backslash-escaped markers (``\\***``) are not matched.

    Args:
        text: Input text.

    Returns:
        Text with bold-italic markers replaced.

    """
    return _style_markers(text, _BOLD_ITALIC_PATTERNS, to_sans_bold_italic)


def _convert_bold(text: str) -> str:
    r"""Replace ``**text**`` (or ``__text__``) with bold Unicode.

    Backslash-escaped markers (``\\**``) are not matched.

    Args:
        text: Input text.

    Returns:
        Text with bold markers replaced.

    """
    return _style_markers(text, _BOLD_PATTERNS, to_sans_bold)


def _convert_italic(text: str) -> str:
    r"""Replace ``*text*`` or ``_text_`` with italic Unicode.

    Uses negative look-around to avoid matching asterisks that are part of
    bold (``**``) or bold-italic (``***``) markers already consumed by
    earlier pipeline steps. Backslash-escaped markers (``\\*``) are also
    not matched.

    Args:
        text: Input text.

    Returns:
        Text with italic markers replaced.

    """
    return _style_markers(text, _ITALIC_PATTERNS, to_sans_italic)


def _convert_headers(text: str) -> str:
    """Convert ATX headers (``# Heading``) and setext headers to styled text.

    * H1 (``#`` or setext ``===``): bold Unicode + ``━`` border.
    * H2–H6 (``##``–``######`` or setext ``---``): bold Unicode, no border.

    Args:
        text: Input text with Markdown headers.

    Returns:
        Text with headers replaced by styled plain text.

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
    """Handle Markdown links.

    By default, links are stripped to their display text only (URLs are
    discarded). Empty links ``[](url)`` are removed entirely. Reference-style
    links ``[text][ref]`` are reduced to their display text.

    When *preserve* is ``True`` the full link syntax is retained as-is.

    Args:
        text: Input text.
        preserve: When ``True``, leave link syntax unchanged.

    Returns:
        Text with links handled according to *preserve*.

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
    """Replace Markdown images with their alt text (or nothing if empty).

    Args:
        text: Input text.

    Returns:
        Text with image syntax replaced by alt text.

    """
    # ![alt](url) → alt  (empty alt → removed)
    return re.sub(
        r"!\[([^\]]*)\]\([^)]*\)",
        lambda m: m.group(1) or "",
        text,
    )


def _convert_bullets(text: str) -> str:
    """Replace Markdown list markers with Unicode bullet characters.

    * First-level ``- `` → ``• ``
    * Second-level ``  - `` (2+ leading spaces) → ``  ‣ ``
    * Ordered list markers (``1. ``) are left as-is (numbers already convey order).

    Args:
        text: Input text.

    Returns:
        Text with list markers replaced.

    """

    def _bullet(m: re.Match[str]) -> str:
        indent = m.group(1)
        return "  ‣ " if len(indent) >= _NESTED_BULLET_MIN_INDENT else "• "

    return re.sub(r"^([ \t]*)[-*+] ", _bullet, text, flags=re.MULTILINE)


def _strip_blockquotes(text: str) -> str:
    """Remove leading ``>`` blockquote markers.

    Args:
        text: Input text.

    Returns:
        Text with blockquote markers stripped from line beginnings.

    """
    return re.sub(r"^> ?", "", text, flags=re.MULTILINE)


def _clean_entities(text: str) -> str:
    """Decode common HTML entities to their literal characters.

    Args:
        text: Input text.

    Returns:
        Text with ``&gt;``, ``&lt;``, ``&amp;``, ``&nbsp;``, ``&quot;``
        replaced by their literal equivalents.

    """
    for entity, char in _HTML_ENTITIES.items():
        text = text.replace(entity, char)
    return text


def _clean_escaped_chars(text: str) -> str:
    r"""Remove Markdown backslash escapes (e.g. ``\\*`` → ``*``).

    Args:
        text: Input text.

    Returns:
        Text with backslash escapes resolved.

    """
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!])", r"\1", text)


def _normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines and strip leading/trailing whitespace.

    LinkedIn renders at most two consecutive blank lines meaningfully, so
    three or more consecutive newlines are collapsed to two.

    Args:
        text: Input text.

    Returns:
        Normalized text with a single trailing newline.

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
    * **Bullet lists** — ``-`` / ``*`` / ``+`` → ``•`` / ``‣`` (nested).
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
    text = _convert_bold_italic(text)
    text = _convert_bold(text)
    text = _convert_italic(text)
    text = _convert_headers(text)
    text = _strip_links(text, preserve=preserve_links)
    text = _convert_bullets(text)
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
