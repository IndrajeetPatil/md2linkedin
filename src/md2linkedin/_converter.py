"""Markdown-to-LinkedIn conversion pipeline.

Each step is a small, independently testable function. The top-level
:func:`convert` function wires them together in the correct order to avoid
regex conflicts (e.g. bold-italic must be processed before bold or italic).
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from ._unicode import to_sans_bold, to_sans_bold_italic, to_sans_italic

__all__ = ["convert", "convert_file"]

_NESTED_BULLET_MIN_INDENT = 2  # spaces of indentation that triggers a nested bullet (‣)

# ── Low-level pipeline steps ───────────────────────────────────────────────────


def _normalize_line_endings(text: str) -> str:
    """Normalize Windows (\\r\\n) and classic Mac (\\r) line endings to \\n."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _protect_code(text: str) -> tuple[str, dict[str, str]]:
    """Replace code spans and fenced blocks with unique placeholders.

    Code content must never be transformed by the Unicode mapping steps.
    Placeholders are UUID-based so they cannot accidentally match user text.

    Args:
        text: Markdown text.

    Returns:
        A ``(modified_text, placeholder_map)`` tuple where *placeholder_map*
        maps each placeholder back to its original code string.
    """
    placeholders: dict[str, str] = {}

    def _replace(match: re.Match[str]) -> str:
        key = f"\x00CODE{uuid.uuid4().hex}\x00"
        placeholders[key] = match.group(0)
        return key

    # Fenced code blocks (``` or ~~~, with optional language tag)
    text = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", _replace, text)
    # Inline code spans (single backtick only; triple already caught above)
    text = re.sub(r"`[^`\n]+`", _replace, text)
    return text, placeholders


def _restore_code(text: str, placeholders: dict[str, str]) -> str:
    """Restore code placeholders to their original content.

    For inline code, the surrounding backticks are stripped (the plain text
    content is kept). For fenced blocks, the entire original block is kept
    intact so structure is preserved.

    Args:
        text: Text containing placeholders.
        placeholders: Map of placeholder → original code string.

    Returns:
        Text with all placeholders replaced by their original code content.
    """
    for key, original in placeholders.items():
        if original.startswith(("```", "~~~")):
            # Keep fenced blocks as-is (no backtick stripping)
            text = text.replace(key, original)
        else:
            # Strip the surrounding backticks for inline code
            text = text.replace(key, original[1:-1])
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
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", text, flags=re.DOTALL)
    return text


def _convert_bold_italic(text: str) -> str:
    """Replace ``***text***`` (or ``___text___``) with bold-italic Unicode.

    Must run before :func:`_convert_bold` and :func:`_convert_italic` to
    prevent the triple markers from being consumed piecemeal.

    Backslash-escaped markers (``\\***``) are not matched.

    Args:
        text: Input text.

    Returns:
        Text with bold-italic markers replaced.
    """
    text = re.sub(
        r"(?<!\\)\*{3}(.+?)(?<!\\)\*{3}",
        lambda m: to_sans_bold_italic(m.group(1)),
        text,
    )
    return re.sub(
        r"(?<!\\)_{3}(.+?)(?<!\\)_{3}",
        lambda m: to_sans_bold_italic(m.group(1)),
        text,
    )


def _convert_bold(text: str) -> str:
    """Replace ``**text**`` (or ``__text__``) with bold Unicode.

    Backslash-escaped markers (``\\**``) are not matched.

    Args:
        text: Input text.

    Returns:
        Text with bold markers replaced.
    """
    text = re.sub(
        r"(?<!\\)\*{2}(.+?)(?<!\\)\*{2}",
        lambda m: to_sans_bold(m.group(1)),
        text,
    )
    return re.sub(
        r"(?<!\\)__(.+?)(?<!\\)__",
        lambda m: to_sans_bold(m.group(1)),
        text,
    )


def _convert_italic(text: str) -> str:
    """Replace ``*text*`` or ``_text_`` with italic Unicode.

    Uses negative look-around to avoid matching asterisks that are part of
    bold (``**``) or bold-italic (``***``) markers already consumed by
    earlier pipeline steps. Backslash-escaped markers (``\\*``) are also
    not matched.

    Args:
        text: Input text.

    Returns:
        Text with italic markers replaced.
    """
    # *text* — negative look-around prevents matching residual ** markers or \* escapes
    text = re.sub(
        r"(?<!\\)(?<!\*)\*(?!\*)(.+?)(?<!\\)(?<!\*)\*(?!\*)",
        lambda m: to_sans_italic(m.group(1)),
        text,
    )
    # _text_ — word-boundary anchors prevent matching inside_words; skip \_ escapes
    return re.sub(
        r"(?<!\w)(?<!\\)_(?!_)(.+?)(?<!\\)(?<!_)_(?!\w)",
        lambda m: to_sans_italic(m.group(1)),
        text,
    )


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
            title = atx.group(2).rstrip()
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
        return ("  ‣ " if len(indent) >= _NESTED_BULLET_MIN_INDENT else "• ")

    return re.sub(r"^(\s*)[-*+] ", _bullet, text, flags=re.MULTILINE)


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
    replacements = {
        "&gt;": ">",
        "&lt;": "<",
        "&amp;": "&",
        "&nbsp;": " ",
        "&quot;": '"',
        "&apos;": "'",
    }
    for entity, char in replacements.items():
        text = text.replace(entity, char)
    return text


def _clean_escaped_chars(text: str) -> str:
    """Remove Markdown backslash escapes (e.g. ``\\*`` → ``*``).

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


def convert(text: str, *, preserve_links: bool = False) -> str:
    """Convert Markdown text to LinkedIn-compatible Unicode plain text.

    Bold (``**text**`` / ``__text__``), italic (``*text*`` / ``_text_``), and
    bold-italic (``***text***`` / ``___text___``) markers are replaced with
    their Unicode Mathematical Sans-Serif equivalents so that the styling is
    preserved when pasting into LinkedIn or other plain-text rich editors.

    The following Markdown constructs are also handled:

    * **Headers** — ATX (``#``) and setext styles; H1 gets a ``━`` border.
    * **Code spans** — backticks stripped, content kept as plain text.
    * **Fenced code blocks** — preserved verbatim (no Unicode transforms).
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
    text = _restore_code(text, placeholders)
    text = _clean_entities(text)
    text = _clean_escaped_chars(text)
    return _normalize_whitespace(text)


def convert_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    preserve_links: bool = False,
) -> Path:
    """Convert a Markdown file and write the result to a ``.txt`` file.

    Args:
        input_path: Path to the Markdown source file (``.md`` or any text
            file).
        output_path: Destination path for the converted output.  Defaults to
            the input path with the extension replaced by
            ``.linkedin.txt``.
        preserve_links: Passed through to :func:`convert`.

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
        >>> os.unlink(tmp); os.unlink(str(out))
    """
    input_path = Path(input_path)
    if not input_path.exists():
        msg = f"Input file not found: {input_path}"
        raise FileNotFoundError(msg)

    if output_path is None:
        output_path = input_path.with_suffix("").with_suffix(".linkedin.txt")
    output_path = Path(output_path)

    md_text = input_path.read_text(encoding="utf-8")
    result = convert(md_text, preserve_links=preserve_links)
    output_path.write_text(result, encoding="utf-8")
    return output_path
