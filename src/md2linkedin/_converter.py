"""Render parsed Markdown as LinkedIn-compatible Unicode text."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast, override

from mistletoe import Document
from mistletoe.base_renderer import BaseRenderer
from mistletoe.block_token import (
    BlockCode,
    CodeFence,
    Heading,
    HtmlBlock,
    List,
    ListItem,
    Paragraph,
    Quote,
    Table,
    ThematicBreak,
)
from mistletoe.span_token import (
    AutoLink,
    Emphasis,
    HtmlSpan,
    InlineCode,
    LineBreak,
    Link,
    RawText,
    Strong,
)

from ._unicode import to_monospace, to_sans_bold, to_sans_bold_italic, to_sans_italic

if TYPE_CHECKING:
    from mistletoe.token import Token

__all__ = ["convert", "convert_file"]

_ENCODING = "utf-8"
_BULLET_MARKERS = ("•", "‣", "◦", "▪")
_H1_BORDER = "━" * 40
_HARD_BREAK_SPACES = 2
_BOLD = 1
_ITALIC = 2
_BOLD_ITALIC = _BOLD | _ITALIC


def _count_line_breaks(token: Token) -> int:
    """Count parsed source line breaks, excluding decoded text newlines."""
    return sum(
        isinstance(child, LineBreak) + _count_line_breaks(child)
        for child in token.children or ()
    )


# mistletoe dispatches through public render_* methods, one per token type.
class _LinkedInRenderer(BaseRenderer):  # ruff: ignore[too-many-public-methods]
    """Turn syntax tree nodes into plain text while tracking inline and list context."""

    def __init__(
        self,
        source: str,
        *,
        preserve_links: bool,
        monospace_code: bool,
    ) -> None:
        super().__init__(HtmlBlock, HtmlSpan)
        self._source_lines = source.splitlines(keepends=True)
        self.preserve_links = preserve_links
        self.monospace_code = monospace_code
        self._style = 0
        self._heading_level = 0
        self._list_depth = 0

    @override
    def render(self, token: Token) -> str:
        """Narrow mistletoe's dynamically dispatched result to text."""
        return cast("str", super().render(token))

    @override
    def render_inner(self, token: Token) -> str:
        """Render children with explicit string and presence guarantees."""
        return "".join(self.render(child) for child in token.children or ())

    @override
    def render_document(self, token: Document) -> str:
        """Separate top-level blocks without exposing Markdown markers."""
        return "\n\n".join(
            filter(None, (self.render(child) for child in token.children or ())),
        )

    @override
    def render_paragraph(self, token: Paragraph) -> str:
        """Restore terminal hard-break spaces stripped by mistletoe's parser."""
        content = self.render_inner(token)
        start = cast("int", vars(token)["line_number"]) - 1
        source_line = self._source_lines[start + _count_line_breaks(token)].rstrip("\n")
        spaces = source_line[len(source_line.rstrip(" ")) :]
        return content + spaces if len(spaces) >= _HARD_BREAK_SPACES else content

    @override
    def render_raw_text(self, token: RawText) -> str:
        """Decode entities and apply the active Unicode text style."""
        content = html.unescape(str(token.content))
        if self._heading_level == 1:
            content = content.upper()
        style = self._style or (_BOLD if self._heading_level else 0)
        if style == _BOLD_ITALIC:
            return to_sans_bold_italic(content)
        if style == _ITALIC:
            return to_sans_italic(content)
        if style == _BOLD:
            return to_sans_bold(content)
        return content

    @override
    def render_strong(self, token: Strong) -> str:
        """Combine bold with the enclosing italic style when present."""
        previous, self._style = self._style, self._style | _BOLD
        try:
            return self.render_inner(token)
        finally:
            self._style = previous

    @override
    def render_emphasis(self, token: Emphasis) -> str:
        """Combine italic with the enclosing bold style when present."""
        previous, self._style = self._style, self._style | _ITALIC
        try:
            return self.render_inner(token)
        finally:
            self._style = previous

    @override
    def render_inline_code(self, token: InlineCode) -> str:
        """Keep code literal even when it appears inside emphasis or a heading."""
        child = next(iter(token.children or ()))
        content = str(cast("RawText", child).content)
        return to_monospace(content) if self.monospace_code else content

    @override
    def render_link(self, token: Link) -> str:
        """Show link text, optionally reconstructing the Markdown link."""
        label = self.render_inner(token)
        if not self.preserve_links:
            return label
        if token.label is not None:
            return f"[{label}][{token.label}]"
        if token.dest_type == "collapsed":
            return f"[{label}][]"
        if token.dest_type == "shortcut":
            return f"[{label}]"
        delimiter = token.title_delimiter or '"'
        closing = ")" if delimiter == "(" else delimiter
        title = f" {delimiter}{token.title}{closing}" if token.title else ""
        return f"[{label}]({token.target}{title})"

    @override
    def render_auto_link(self, token: AutoLink) -> str:
        """Show the URL or email, retaining angle brackets when requested."""
        label = self.render_inner(token)
        return f"<{label}>" if self.preserve_links else label

    @override
    def render_line_break(self, token: LineBreak) -> str:
        """Keep source spaces for hard breaks and discard backslash markers."""
        return "\n" if token.content.startswith("\\") else f"{token.content}\n"

    @override
    def render_heading(self, token: Heading) -> str:
        """Style headings and frame H1 with the existing border."""
        previous, self._heading_level = self._heading_level, token.level
        try:
            title = self.render_inner(token).strip()
        finally:
            self._heading_level = previous
        if token.level == 1:
            return f"{_H1_BORDER}\n{title}\n{_H1_BORDER}"
        return title

    @override
    def render_quote(self, token: Quote) -> str:
        """Render every nested quote level without its source prefix."""
        return "\n".join(
            filter(None, (self.render(child) for child in token.children or ())),
        )

    @override
    def render_block_code(self, token: BlockCode | CodeFence) -> str:
        """Render parsed code, retaining fences when that option is disabled."""
        if self.monospace_code:
            return to_monospace(token.content).rstrip("\n")
        if isinstance(token, CodeFence):
            # The AST does not retain the exact closing delimiter or whether
            # the fence was left open, so use its source lines for plain code.
            start = cast("int", vars(token)["line_number"]) - 1
            end = start + token.content.count("\n") + 2
            return "".join(self._source_lines[start:end]).rstrip("\n")
        return str(token.content).rstrip("\n")

    @override
    def render_list(self, token: List) -> str:
        """Use the nesting tree for markers and retain loose-list spacing."""
        self._list_depth += 1
        try:
            separator = "\n\n" if token.loose else "\n"
            return separator.join(self.render(child) for child in token.children or ())
        finally:
            self._list_depth -= 1

    @override
    def render_list_item(self, token: ListItem) -> str:
        """Keep ordered markers and convert unordered markers by tree depth."""
        depth = self._list_depth - 1
        marker = (
            f"{_BULLET_MARKERS[min(depth, len(_BULLET_MARKERS) - 1)]}"
            if len(token.leader) == 1
            else token.leader
        )
        prefix = f"{'  ' * depth}{marker}"
        if not token.children:
            return prefix
        first, *rest = token.children
        result = f"{prefix} {self.render(first)}"
        for child in rest:
            rendered = self.render(child)
            if rendered:
                separator = (
                    "\n\n" if token.loose or isinstance(child, Paragraph) else "\n"
                )
                result += separator + rendered
        return result

    @override
    def render_table(self, token: Table) -> str:
        """Render rows as labelled values that remain readable without columns."""
        headers = [self.render(cell) for cell in token.header.children or ()]
        if not token.children:
            return " · ".join(headers)
        rows: list[str] = []
        for row in token.children or ():
            values = [self.render(cell) for cell in row.children or ()]
            rows.append(
                " · ".join(
                    f"{header}: {value}" if header else value
                    for header, value in zip(headers, values, strict=False)
                ),
            )
        return "\n".join(rows)

    @override
    def render_thematic_break(self, token: ThematicBreak) -> str:
        """Drop thematic breaks as the previous converter did."""
        del token
        return ""

    @staticmethod
    def render_html_span(token: HtmlSpan) -> str:
        """Unwrap HTML spans while leaving other inline HTML unchanged."""
        content = token.content
        if content.lower().startswith(("<span", "</span")):
            return ""
        return str(content)

    @staticmethod
    def render_html_block(token: HtmlBlock) -> str:
        """Retain HTML blocks as literal text."""
        return str(token.content)


def convert(
    text: str,
    *,
    preserve_links: bool = False,
    monospace_code: bool = True,
) -> str:
    r"""Convert Markdown text to LinkedIn-compatible Unicode plain text.

    The Markdown syntax tree distinguishes nested lists, code blocks, quotes,
    link definitions, and tables before they are rendered. Bold, italic, and
    bold-italic text become Unicode Mathematical Sans-Serif characters. H1 is
    framed with a border, deeper headings are bold, lists use Unicode bullets,
    and table rows become labelled values.

    Args:
        text: The Markdown source string.
        preserve_links: Keep Markdown link syntax instead of just display text.
        monospace_code: Convert code to Unicode Mathematical Monospace. If
            false, inline code stays plain and fenced blocks keep their fences.

    Returns:
        Plain text suitable for pasting into LinkedIn, ending in a newline;
        an empty string for empty or whitespace-only input.

    Examples:
        >>> convert("**Hello**, *world*!")
        '𝗛𝗲𝗹𝗹𝗼, 𝘸𝘰𝘳𝘭𝘥!\\n'

        >>> convert("")
        ''

    """
    if not text or not text.strip():
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    with _LinkedInRenderer(
        normalized,
        preserve_links=preserve_links,
        monospace_code=monospace_code,
    ) as renderer:
        result = renderer.render(Document(normalized))
    return re.sub(r"\n{3,}", "\n\n", result).strip() + "\n"


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
