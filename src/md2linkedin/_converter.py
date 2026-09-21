"""Markdown-to-LinkedIn conversion pipeline using comrak."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, Any

import comrak

from ._unicode import to_monospace, to_sans_bold, to_sans_bold_italic, to_sans_italic

if TYPE_CHECKING:
    from typing import override
else:

    def override(x: Any) -> Any:  # ruff: ignore[any-type]
        return x


__all__ = ["convert", "convert_file"]

_ENCODING = "utf-8"


class LinkedInHTMLParser(HTMLParser):
    """HTML Parser that translates HTML tags to LinkedIn styled text."""

    def __init__(self, *, preserve_links: bool, monospace_code: bool) -> None:
        super().__init__()
        self.preserve_links: bool = preserve_links
        self.monospace_code: bool = monospace_code
        self.out: list[str] = []
        self.styles: list[str] = []
        self.lists: list[dict[str, int | str]] = []
        self.in_link: bool = False
        self.link_text: list[str] = []
        self.link_url: str = ""
        self.link_title: str = ""
        self.after_li: bool = False

    def _emit_newlines(self, n: int) -> None:
        text = "".join(self.out)
        trailing = len(text) - len(text.rstrip("\n"))
        if trailing < n:
            self.out.append("\n" * (n - trailing))

    def _emit_text(self, text: str) -> None:
        styled = text
        if "upper" in self.styles:
            styled = styled.upper()
        if "bold" in self.styles and "italic" in self.styles:
            styled = to_sans_bold_italic(styled)
        elif "bold" in self.styles:
            styled = to_sans_bold(styled)
        elif "italic" in self.styles:
            styled = to_sans_italic(styled)

        if "monospace" in self.styles:
            styled = to_monospace(styled)

        if self.in_link:
            self.link_text.append(styled)
        else:
            self.out.append(styled)

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # ruff: ignore[complex-structure, too-many-branches, too-many-statements]
        attrs_dict = dict(attrs)
        if tag in {"p", "pre", "blockquote"}:
            if self.out and not getattr(self, "after_li", False):
                self._emit_newlines(2)
            self.after_li = False
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            if self.out and not getattr(self, "after_li", False):
                self._emit_newlines(2)
            self.after_li = False
            self.styles.append("bold")
            if tag == "h1":
                self.styles.append("upper")
            if tag == "h1":
                self.out.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        elif tag in {"strong", "b"}:
            self.styles.append("bold")
        elif tag in {"em", "i"}:
            self.styles.append("italic")
        elif tag == "code":
            if self.monospace_code:
                self.styles.append("monospace")
        elif tag in {"ul", "ol"}:
            if self.lists:
                self._emit_newlines(1)
            elif self.out and not getattr(self, "after_li", False):
                self._emit_newlines(2)
            self.after_li = False
            start = int(attrs_dict.get("start") or 1)
            self.lists.append({"type": tag, "count": start})
        elif tag == "li":
            self._emit_newlines(1)
            depth = len(self.lists) - 1
            indent = "  " * depth
            list_info = self.lists[-1]
            if list_info["type"] == "ul":
                marker = ["•", "‣", "◦", "▪"][min(depth, 3)] + " "
            else:
                marker = f"{list_info['count']}. "
                list_info["count"] = int(list_info["count"]) + 1
            self.out.append(indent + marker)
            self.after_li = True
        elif tag == "a":
            self.in_link = True
            self.link_url = attrs_dict.get("href", "") or ""
            self.link_title = attrs_dict.get("title", "") or ""
            self.link_text = []
        elif tag == "img":
            alt = attrs_dict.get("alt", "") or ""
            self._emit_text(alt)
        elif tag == "br":
            self._emit_newlines(1)

    @override
    def handle_endtag(self, tag: str) -> None:  # ruff: ignore[complex-structure, too-many-branches]
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.styles.remove("bold")
            if tag == "h1":
                self.styles.remove("upper")
            if tag == "h1":
                self.out.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            self._emit_newlines(2)
        elif tag in {"p", "pre", "blockquote"}:
            self._emit_newlines(2)
        elif tag in {"strong", "b"}:
            self.styles.remove("bold")
        elif tag in {"em", "i"}:
            self.styles.remove("italic")
        elif tag == "code":
            if self.monospace_code:
                self.styles.remove("monospace")
        elif tag in {"ul", "ol"}:
            self.lists.pop()
            if not self.lists:
                self._emit_newlines(2)
        elif tag == "a":
            self.in_link: bool = False
            text = "".join(self.link_text)
            if self.preserve_links:
                if text == self.link_url:
                    self.out.append(f"<{text}>")
                else:
                    title_part = f' "{self.link_title}"' if self.link_title else ""
                    self.out.append(f"[{text}]({self.link_url}{title_part})")
            else:
                self.out.append(text)

    @override
    def handle_data(self, data: str) -> None:
        if data.strip():
            self.after_li = False
        self._emit_text(data)


def convert(
    text: str,
    *,
    preserve_links: bool = False,
    monospace_code: bool = True,
) -> str:
    r"""Convert Markdown text to LinkedIn-compatible Unicode plain text.

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

    """
    if not text or not text.strip():
        return ""

    opts = comrak.RenderOptions()
    opts.compact_html = True
    opts.unsafe_ = True  # Allows raw HTML rendering so we can parse it

    exts = comrak.ExtensionOptions()
    exts.strikethrough = True
    exts.table = True
    exts.autolink = True

    html = comrak.render_markdown(text, extension_options=exts, render_options=opts)

    parser = LinkedInHTMLParser(
        preserve_links=preserve_links,
        monospace_code=monospace_code,
    )
    parser.feed(html)

    out = "".join(parser.out)
    return re.sub(r"\n{3,}", "\n\n", out).strip() + "\n"


def convert_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    preserve_links: bool = False,
    monospace_code: bool = True,
) -> Path:
    r"""Convert a Markdown file and write the result to a ``.txt`` file.

    Args:
        input_path: Path to the Markdown source file.
        output_path: Destination path for the converted output.
        preserve_links: Passed through to :func:`convert`.
        monospace_code: Passed through to :func:`convert`.

    Returns:
        The resolved path of the written output file.

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
