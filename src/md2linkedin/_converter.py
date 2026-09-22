import re
from dataclasses import dataclass
from pathlib import Path

import comrak
from selectolax.parser import HTMLParser, Node

from md2linkedin._unicode import (
    to_monospace,
    to_sans_bold,
    to_sans_bold_italic,
    to_sans_italic,
)

_ENCODING = "utf-8"

# selectolax spells a text node's tag this way.
_TEXT_TAG = "-text"

_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
# Tags that render as their own paragraph, separated by a blank line.
_BLOCK_TAGS = frozenset({"p", "pre", "blockquote", "table"})
# Tags that only switch a style on for the text they wrap.
_STYLE_TAGS = {"strong": "bold", "b": "bold", "em": "italic", "i": "italic"}
_LIST_TAGS = frozenset({"ul", "ol"})
_CELL_TAGS = frozenset({"th", "td"})
# Tags whose children are rows and cells rather than prose, so the whitespace
# between them is layout rather than content.
_TABLE_TAGS = frozenset({"table", "thead", "tbody", "tfoot", "tr"})
# Raw HTML whose content is meant for the browser, not for the reader.
_SKIPPED_TAGS = frozenset({"script", "style"})

_BULLETS = ("•", "‣", "◦", "▪")
_HEADING_RULE = "━" * 40
_CELL_SEPARATOR = " | "
_TRAILING_SPACE = re.compile(r"[ \t]+(?=\n)")


@dataclass
class _Link:
    """An open ``<a>`` element and the styled text collected inside it."""

    url: str
    title: str
    text: list[str]


@dataclass
class _ListLevel:
    """An open ``<ul>``/``<ol>`` element and the next number to hand out."""

    ordered: bool
    number: int


def _list_start(node: Node) -> int:
    """Read the first number of an ordered list, defaulting to one."""
    start = node.attributes.get("start")
    if start is None:
        return 1
    try:
        return int(start)
    except ValueError:
        # Empty or not a number: raw HTML can spell it any way it likes.
        return 1


def _leads_a_list_item(node: Node) -> bool:
    """Report whether the node is the first block inside a list item."""
    parent = node.parent
    return parent is not None and parent.tag == "li" and node.prev is None


def _follows_a_cell(node: Node) -> bool:
    """Report whether another cell precedes the node in its row."""
    sibling = node.prev
    while sibling is not None:
        if sibling.tag in _CELL_TAGS:
            return True
        sibling = sibling.prev
    return False


class Renderer:
    """Renders a parsed HTML tree as LinkedIn-ready styled plain text."""

    def __init__(self, *, preserve_links: bool, monospace_code: bool) -> None:
        self.preserve_links: bool = preserve_links
        self.monospace_code: bool = monospace_code
        self.out: list[str] = []
        # Newlines at the end of ``out``, tracked so that block separation
        # does not have to re-join everything rendered so far.
        self.trailing: int = 0
        self.styles: list[str] = []
        self.lists: list[_ListLevel] = []
        self.links: list[_Link] = []

    def render(self, root: Node | None) -> str:
        """Render the tree under ``root`` and return the text."""
        if root is not None:
            self.visit(root)
        return "".join(self.out)

    def visit(self, node: Node) -> None:
        """Recursively render a node and its children."""
        tag = node.tag
        if tag == _TEXT_TAG:
            self._visit_text(node)
            return
        if tag in _SKIPPED_TAGS:
            return
        if tag == "li":
            # An item renders its own children, because everything it holds
            # has to line up under the marker.
            self._visit_item(node)
            return

        self._enter(node)
        self._visit_children(node)
        self._exit(tag)

    def _visit_children(self, node: Node) -> None:
        child = node.child
        while child is not None:
            self.visit(child)
            child = child.next

    # ── output ────────────────────────────────────────────────────────────────

    def _append(self, text: str) -> None:
        """Write rendered text, keeping the trailing-newline count in step."""
        if not text:
            return
        self.out.append(text)
        self.trailing = len(text) - len(text.rstrip("\n"))

    def _write(self, text: str) -> None:
        """Write styled text to the innermost open link, or to the output."""
        if self.links:
            self.links[-1].text.append(text)
        else:
            self._append(text)

    def _emit_newlines(self, count: int) -> None:
        """Pad the output so that it ends in at least ``count`` newlines."""
        padding = "\n" * (count - self.trailing)
        if padding:
            self.out.append(padding)
            self.trailing = count

    def _emit_text(self, text: str) -> None:
        """Write text with the styles of the enclosing tags applied."""
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

        self._write(styled)

    # ── tags ──────────────────────────────────────────────────────────────────

    def _visit_text(self, node: Node) -> None:
        # ``text()`` rather than ``text_content``: a text node always has text,
        # and this spelling says so without an unreachable fallback.
        data = node.text()
        parent = node.parent
        if parent is not None and parent.tag in _TABLE_TAGS and not data.strip():
            return
        self._emit_text(data)

    def _enter(self, node: Node) -> None:
        tag = node.tag
        if tag in _BLOCK_TAGS:
            self._start_block(node)
        elif tag in _HEADING_TAGS:
            self._start_heading(node, tag)
        elif tag in _LIST_TAGS:
            self._start_list(node, tag)
        elif tag in _CELL_TAGS:
            self._start_cell(node, tag)
        elif tag == "tr":
            self._emit_newlines(1)
        else:
            self._enter_inline(node, tag)

    def _enter_inline(self, node: Node, tag: str) -> None:
        style = _STYLE_TAGS.get(tag)
        if style is not None:
            self.styles.append(style)
        elif tag == "code":
            if self.monospace_code:
                self.styles.append("monospace")
        elif tag == "a":
            self._start_link(node)
        elif tag == "img":
            self._emit_text(node.attributes.get("alt") or "")
        elif tag == "br":
            self._emit_newlines(1)

    def _exit(self, tag: str) -> None:
        if tag in _BLOCK_TAGS:
            self._emit_newlines(2)
        elif tag in _HEADING_TAGS:
            self._end_heading(tag)
        elif tag in _LIST_TAGS:
            self._end_list()
        elif tag == "th":
            # ``_start_cell`` turns a header cell bold; nothing else in a
            # table changes the style stack.
            self.styles.remove("bold")
        else:
            self._exit_inline(tag)

    def _exit_inline(self, tag: str) -> None:
        style = _STYLE_TAGS.get(tag)
        if style is not None:
            self.styles.remove(style)
        elif tag == "code":
            if self.monospace_code:
                self.styles.remove("monospace")
        elif tag == "a":
            self._end_link()

    def _start_block(self, node: Node) -> None:
        # The first block of a list item continues the line the marker opened;
        # every other block starts after a blank line. Leading newlines are
        # stripped from the finished document, so the first block is not a
        # special case here.
        if not _leads_a_list_item(node):
            self._emit_newlines(2)

    def _start_heading(self, node: Node, tag: str) -> None:
        self._start_block(node)
        self.styles.append("bold")
        if tag == "h1":
            self.styles.append("upper")
            self._append(_HEADING_RULE)
            self._emit_newlines(1)

    def _end_heading(self, tag: str) -> None:
        self.styles.remove("bold")
        if tag == "h1":
            self.styles.remove("upper")
            self._emit_newlines(1)
            self._append(_HEADING_RULE)
        self._emit_newlines(2)

    def _start_list(self, node: Node, tag: str) -> None:
        # A nested list carries on the line its parent item started, so it
        # only needs a line break rather than a blank line.
        if self.lists:
            self._emit_newlines(1)
        else:
            self._start_block(node)
        self.lists.append(_ListLevel(ordered=tag == "ol", number=_list_start(node)))

    def _end_list(self) -> None:
        self.lists.pop()
        if not self.lists:
            self._emit_newlines(2)

    def _visit_item(self, node: Node) -> None:
        self._emit_newlines(1)
        marker = self._item_marker()
        body, gap = self._render_apart(node)
        # Everything after the first line of an item is indented to the
        # column the marker opened, so nested lists, continuation paragraphs
        # and wrapped lines all sit inside the item.
        self._append(marker + body.replace("\n", "\n" + " " * len(marker)))
        # A loose item ends in a blank line, which separates it from the next.
        self._emit_newlines(gap)

    def _item_marker(self) -> str:
        if not self.lists:
            # A stray ``<li>`` in raw HTML is not an item of anything, so it
            # gets a line of its own and no marker.
            return ""
        level = self.lists[-1]
        if level.ordered:
            # The numbers already convey the order, so they are kept verbatim.
            marker = f"{level.number}. "
            level.number += 1
            return marker
        depth = len(self.lists) - 1
        return _BULLETS[min(depth, len(_BULLETS) - 1)] + " "

    def _render_apart(self, node: Node) -> tuple[str, int]:
        """Render the children of a node on their own, away from the output.

        Returns the rendered text and the number of newlines it ends in.
        """
        held_out, held_trailing = self.out, self.trailing
        self.out = []
        self.trailing = 0
        self._visit_children(node)
        rendered = "".join(self.out)
        self.out, self.trailing = held_out, held_trailing
        body = rendered.rstrip("\n")
        return body, len(rendered) - len(body)

    def _start_cell(self, node: Node, tag: str) -> None:
        if _follows_a_cell(node):
            self._append(_CELL_SEPARATOR)
        if tag == "th":
            self.styles.append("bold")

    def _start_link(self, node: Node) -> None:
        attrs = node.attributes
        self.links.append(
            _Link(
                url=attrs.get("href") or "",
                title=attrs.get("title") or "",
                text=[],
            ),
        )

    def _end_link(self) -> None:
        link = self.links.pop()
        text = "".join(link.text)
        if not self.preserve_links:
            self._write(text)
        elif text == link.url:
            # An autolink: the URL is its own display text.
            self._write(f"<{text}>")
        else:
            title = f' "{link.title}"' if link.title else ""
            self._write(f"[{text}]({link.url}{title})")


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
            When ``False``, code is kept as plain text, with the backticks
            and fences stripped.

    Returns:
        A plain-text string suitable for pasting into LinkedIn.

    """
    if not text or not text.strip():
        return ""

    render_options = comrak.RenderOptions()
    render_options.compact_html = True
    # Raw HTML is passed through to the parser below, which reads the text out
    # of it. Nothing is ever rendered as HTML, so nothing can be injected.
    render_options.unsafe_ = True

    extensions = comrak.ExtensionOptions()
    extensions.strikethrough = True
    extensions.table = True
    extensions.autolink = True

    html = comrak.render_markdown(
        text,
        extension_options=extensions,
        render_options=render_options,
    )

    tree = HTMLParser(html)
    renderer = Renderer(
        preserve_links=preserve_links,
        monospace_code=monospace_code,
    )
    out = renderer.render(tree.root)
    # An item that holds nothing but a nested list leaves its marker alone on
    # a line; no line is meant to end in blank space.
    return _TRAILING_SPACE.sub("", out).strip() + "\n"


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
