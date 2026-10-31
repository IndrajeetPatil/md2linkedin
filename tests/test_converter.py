"""Tests for md2linkedin._converter — the Markdown conversion pipeline."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from selectolax.lexbor import LexborHTMLParser

from md2linkedin._converter import Renderer, convert, convert_file

_RULE = "━" * 40


class TestConvert:
    # ── emphasis ──────────────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param("**hello**", "𝗵𝗲𝗹𝗹𝗼\n", id="bold"),
            pytest.param("__hello__", "𝗵𝗲𝗹𝗹𝗼\n", id="bold_underscores"),
            pytest.param("*hello*", "𝘩𝘦𝘭𝘭𝘰\n", id="italic"),
            pytest.param("_hello_", "𝘩𝘦𝘭𝘭𝘰\n", id="italic_underscores"),
            # Three markers are one bold-italic span, not bold wrapping italic.
            pytest.param("***hello***", "𝙝𝙚𝙡𝙡𝙤\n", id="bold_italic"),
            pytest.param(
                "**bold and *italic* inside**",
                "𝗯𝗼𝗹𝗱 𝗮𝗻𝗱 𝙞𝙩𝙖𝙡𝙞𝙘 𝗶𝗻𝘀𝗶𝗱𝗲\n",
                id="italic_nested_in_bold",
            ),
            pytest.param(
                "**bold** and *italic*",
                "𝗯𝗼𝗹𝗱 and 𝘪𝘵𝘢𝘭𝘪𝘤\n",
                id="bold_and_italic_together",
            ),
            pytest.param("**123**", "𝟭𝟮𝟯\n", id="digits_inside_bold_are_converted"),
            # Underscores inside a word are not emphasis markers.
            pytest.param(
                "some_variable_name",
                "some_variable_name\n",
                id="snake_case_is_not_italicised",
            ),
            pytest.param(
                r"\*not italic\*",
                "*not italic*\n",
                id="escaped_asterisk_is_not_emphasis",
            ),
            pytest.param(
                "price: $10 * 3",
                "price: $10 * 3\n",
                id="unmatched_marker_is_left_alone",
            ),
            # LinkedIn has no strikethrough, so the text is kept and the markers
            # go, rather than being left in the output as punctuation.
            pytest.param(
                "~~strike~~ text",
                "strike text\n",
                id="strikethrough_markers_are_dropped",
            ),
            # LinkedIn has no highlighting either, so ``==`` goes the same way.
            pytest.param(
                "==marked== text",
                "marked text\n",
                id="highlight_markers_are_dropped",
            ),
            pytest.param(
                "==a **b**==",
                "a 𝗯\n",
                id="highlight_keeps_the_styles_inside_it",
            ),
            pytest.param(
                "x == y",
                "x == y\n",
                id="spaced_double_equals_is_not_a_highlight",
            ),
        ],
    )
    def test_emphasis(self, markdown: str, expected: str) -> None:
        assert convert(markdown) == expected

    # ── headings ──────────────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param(
                "# Hello",
                f"{_RULE}\n𝗛𝗘𝗟𝗟𝗢\n{_RULE}\n",
                id="heading_h1_is_bold_upper_between_rules",
            ),
            pytest.param(
                "## Sub-section",
                "𝗦𝘂𝗯-𝘀𝗲𝗰𝘁𝗶𝗼𝗻\n",
                id="heading_h2_is_bold_without_a_rule",
            ),
            pytest.param(
                "###### Deep",
                "𝗗𝗲𝗲𝗽\n",
                id="heading_h6_is_bold_without_a_rule",
            ),
            pytest.param(
                "Title\n=====",
                f"{_RULE}\n𝗧𝗜𝗧𝗟𝗘\n{_RULE}\n",
                id="setext_h1_is_a_heading",
            ),
            pytest.param("Title\n-----", "𝗧𝗶𝘁𝗹𝗲\n", id="setext_h2_is_a_heading"),
            pytest.param(
                "## Heading\n\nbody",
                "𝗛𝗲𝗮𝗱𝗶𝗻𝗴\n\nbody\n",
                id="heading_is_separated_from_the_text_below_it",
            ),
        ],
    )
    def test_headings(self, markdown: str, expected: str) -> None:
        assert convert(markdown) == expected

    # ── code ──────────────────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param(
                "use `hello` here",
                "use 𝚑𝚎𝚕𝚕𝚘 here\n",
                id="inline_code_is_monospaced_by_default",
            ),
            pytest.param(
                "```python\nprint('hello')\n```",
                "𝚙𝚛𝚒𝚗𝚝('𝚑𝚎𝚕𝚕𝚘')\n",
                id="fenced_code_is_monospaced_by_default",
            ),
            # Four spaces open a code block, which a regex pipeline read as prose.
            pytest.param(
                "    print(1)",
                "𝚙𝚛𝚒𝚗𝚝(𝟷)\n",
                id="indented_code_block_is_a_code_block",
            ),
            # Only ASCII letters and digits are remapped, so the ``**`` survives
            # and nothing inside the span is read as emphasis.
            pytest.param(
                "use `**bold**` here",
                "use **𝚋𝚘𝚕𝚍** here\n",
                id="markdown_inside_code_is_not_converted",
            ),
        ],
    )
    def test_code(self, markdown: str, expected: str) -> None:
        assert convert(markdown) == expected

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param(
                "use `hello` here",
                "use hello here\n",
                id="inline_code_is_plain_when_monospace_is_off",
            ),
            pytest.param(
                "```python\nprint('hello')\n```",
                "print('hello')\n",
                id="fenced_code_is_plain_when_monospace_is_off",
            ),
            pytest.param(
                "use `**bold**` here",
                "use **bold** here\n",
                id="markdown_inside_plain_code_is_left_alone",
            ),
        ],
    )
    def test_code_with_monospace_off(self, markdown: str, expected: str) -> None:
        assert convert(markdown, monospace_code=False) == expected

    # ── links and images ──────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param(
                "[GitHub](https://github.com)",
                "GitHub\n",
                id="link_is_reduced_to_its_text",
            ),
            pytest.param(
                "**[bold link](https://x.com)**",
                "𝗯𝗼𝗹𝗱 𝗹𝗶𝗻𝗸\n",
                id="styled_link_text_is_converted",
            ),
            # Writing nothing must not look like writing a line without newlines,
            # or the paragraph after it would gain a blank line.
            pytest.param(
                "a\n\n[](https://example.com)\n\nb",
                "a\n\nb\n",
                id="a_link_with_no_text_leaves_the_spacing_alone",
            ),
            pytest.param(
                "<https://example.com>",
                "https://example.com\n",
                id="autolink_is_reduced_to_the_url",
            ),
            # The definition is consumed by the parser instead of being left in
            # the output as text.
            pytest.param(
                "[text][ref]\n\n[ref]: https://example.com",
                "text\n",
                id="reference_style_link_is_resolved",
            ),
            pytest.param(
                "![Logo](logo.png)",
                "Logo\n",
                id="image_is_reduced_to_its_alt_text",
            ),
            pytest.param(
                "![](logo.png)",
                "\n",
                id="image_without_alt_text_renders_nothing",
            ),
            # Markdown images always carry ``alt``; raw HTML need not.
            pytest.param(
                'a <img src="logo.png"> b',
                "a  b\n",
                id="raw_html_image_without_an_alt_attribute_renders_nothing",
            ),
        ],
    )
    def test_links_and_images(self, markdown: str, expected: str) -> None:
        assert convert(markdown) == expected

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param(
                "[GitHub](https://github.com)",
                "[GitHub](https://github.com)\n",
                id="link_is_kept_whole_when_preserved",
            ),
            pytest.param(
                '[GitHub](https://github.com "Home")',
                '[GitHub](https://github.com "Home")\n',
                id="link_title_is_kept_when_preserved",
            ),
            pytest.param(
                "[**bold** and plain](https://x.com)",
                "[𝗯𝗼𝗹𝗱 and plain](https://x.com)\n",
                id="link_text_in_several_styles_is_joined_seamlessly",
            ),
            # Only raw HTML can spell an anchor with no ``href`` at all.
            pytest.param(
                "<a>text</a>",
                "[text]()\n",
                id="a_link_without_a_url_is_preserved_with_an_empty_target",
            ),
            pytest.param(
                "<https://example.com>",
                "<https://example.com>\n",
                id="autolink_keeps_its_brackets_when_preserved",
            ),
            # The autolink extension turns a bare URL into a link, so preserving
            # links spells it as an autolink rather than as ``[url](url)``.
            pytest.param(
                "see https://example.com",
                "see <https://example.com>\n",
                id="bare_url_is_a_link",
            ),
        ],
    )
    def test_links_when_preserved(self, markdown: str, expected: str) -> None:
        assert convert(markdown, preserve_links=True) == expected

    # ── lists ─────────────────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param(
                "- item one\n- item two",
                "• item one\n• item two\n",
                id="bullet_list",
            ),
            pytest.param(
                "- a\n  - b\n    - c\n      - d",
                "• a\n  ‣ b\n    ◦ c\n      ▪ d\n",
                id="nested_bullets_get_their_own_marker_per_level",
            ),
            pytest.param(
                "- a\n  - b\n    - c\n      - d\n        - e",
                "• a\n  ‣ b\n    ◦ c\n      ▪ d\n        ▪ e\n",
                id="bullets_past_the_fourth_level_reuse_the_last_marker",
            ),
            # Depth comes from the parsed tree, not from the indentation width.
            pytest.param(
                "- a\n    - b",
                "• a\n  ‣ b\n",
                id="four_space_indentation_nests_like_two",
            ),
            # Markdown allows a top-level item up to three leading spaces.
            pytest.param(
                "- a\n - b",
                "• a\n• b\n",
                id="one_extra_space_is_not_a_nesting_level",
            ),
            pytest.param(
                "1. a\n2. b",
                "1. a\n2. b\n",
                id="ordered_list_keeps_its_numbers",
            ),
            pytest.param(
                "5. five\n6. six",
                "5. five\n6. six\n",
                id="ordered_list_starts_where_its_first_item_says",
            ),
            # The second item is numbered by the renderer's counter, not by the
            # source, so a mis-numbered list comes out in order.
            pytest.param(
                "3. three\n3. four",
                "3. three\n4. four\n",
                id="ordered_list_renumbers_from_its_start",
            ),
            pytest.param(
                "1. parent\n   - child",
                "1. parent\n   ‣ child\n",
                id="bullets_nested_under_an_ordered_item_align_under_its_text",
            ),
            pytest.param(
                "1. a\n   1. b",
                "1. a\n   1. b\n",
                id="ordered_list_nested_under_an_ordered_item",
            ),
            pytest.param(
                "- a\n\n  more",
                "• a\n\n  more\n",
                id="a_continuation_paragraph_stays_inside_its_item",
            ),
            pytest.param(
                "- first line\n  second line",
                "• first line\n  second line\n",
                id="a_wrapped_line_stays_inside_its_item",
            ),
            pytest.param(
                "- item\n\n  ```\n  a = 1\n  b = 2\n  ```",
                "• item\n\n  𝚊 = 𝟷\n  𝚋 = 𝟸\n",
                id="a_code_block_inside_an_item_stays_inside_it",
            ),
            pytest.param(
                "- a\n\n- b",
                "• a\n\n• b\n",
                id="a_loose_list_keeps_the_blank_lines_between_its_items",
            ),
            # Only the newlines an item ends in decide the gap to the next one;
            # the letters before them are content like any other.
            pytest.param(
                "- LaTeX\n\n- Typst",
                "• LaTeX\n\n• Typst\n",
                id="a_loose_item_is_spaced_by_its_newlines_not_its_last_character",
            ),
            pytest.param(
                "<ul><li><p>note </p></li><li><p>next</p></li></ul>",
                "• note\n\n• next\n",
                id="a_trailing_space_inside_an_item_does_not_widen_the_gap",
            ),
            # The marker is alone on its line, without trailing blank space.
            pytest.param(
                "-\n  - b",
                "•\n  ‣ b\n",
                id="an_item_holding_only_a_nested_list_leaves_its_marker_bare",
            ),
            pytest.param(
                "intro\n\n- a\n\nend",
                "intro\n\n• a\n\nend\n",
                id="list_is_separated_from_the_text_around_it",
            ),
            pytest.param(
                "# Heading\n\n- first\n  - sub\n- second",
                f"{_RULE}\n𝗛𝗘𝗔𝗗𝗜𝗡𝗚\n{_RULE}\n\n• first\n  ‣ sub\n• second\n",
                id="a_bullet_after_a_heading_is_a_list",
            ),
            # Indented, the block is content of the item above rather than a block
            # of its own, so the list continues and ``c`` stays ``b``'s sibling.
            pytest.param(
                "- a\n    - b\n    ```\n    code\n    ```\n    - c",
                "• a\n  ‣ b\n\n  𝚌𝚘𝚍𝚎\n\n  ‣ c\n",
                id="an_indented_fenced_block_keeps_the_list_open",
            ),
            # An inline span is ordinary paragraph content, so the paragraph it
            # sits in carries on the item above it.
            pytest.param(
                "- a\n    - b\n`code` continues\n    - c",
                "• a\n  ‣ b\n    𝚌𝚘𝚍𝚎 continues\n  ‣ c\n",
                id="inline_code_keeps_the_list_open",
            ),
            # There is no paragraph above the marker for it to interrupt, so its
            # number does not have to be one.
            pytest.param(
                "```\ncode\n```\n2. parent\n    - child",
                "𝚌𝚘𝚍𝚎\n\n2. parent\n   ‣ child\n",
                id="an_ordered_marker_after_a_fenced_block_starts_a_list",
            ),
            # Only ``1.`` may interrupt a paragraph, so ``2.`` here is text and
            # the bullet below it nests under ``outer`` instead.
            pytest.param(
                "- outer\n  `code` paragraph\n  2. prose\n    - child",
                "• outer\n  𝚌𝚘𝚍𝚎 paragraph\n  2. prose\n  ‣ child\n",
                id="an_ordered_marker_inside_a_paragraph_is_prose",
            ),
            pytest.param(
                "## Heading\n2. parent\n    - child",
                "𝗛𝗲𝗮𝗱𝗶𝗻𝗴\n\n2. parent\n   ‣ child\n",
                id="an_ordered_marker_after_a_heading_starts_a_list",
            ),
            # A marker of a different kind ends the list above it, so ``2. y`` is
            # a list of its own rather than an item or prose.
            pytest.param(
                "- x\n2. y",
                "• x\n\n2. y\n",
                id="an_ordered_marker_beside_a_bullet_starts_a_second_list",
            ),
            pytest.param(
                "1. x\n2) y",
                "1. x\n\n2. y\n",
                id="a_different_ordered_delimiter_starts_a_second_list",
            ),
        ],
    )
    def test_lists(self, markdown: str, expected: str) -> None:
        assert convert(markdown) == expected

    # ── tables ────────────────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param(
                "| Lang | Users |\n|---|---|\n| Python | 10 |\n| Rust | 5 |",
                "𝗟𝗮𝗻𝗴 | 𝗨𝘀𝗲𝗿𝘀\nPython | 10\nRust | 5\n",
                id="table_header_is_bold_and_cells_are_separated",
            ),
            pytest.param(
                "| col |\n|---|\n| cell |",
                "𝗰𝗼𝗹\ncell\n",
                id="a_single_column_table_needs_no_separator",
            ),
            pytest.param(
                "| a |\n|---|\n| `code` |",
                "𝗮\n𝚌𝚘𝚍𝚎\n",
                id="table_cells_keep_their_own_formatting",
            ),
            pytest.param(
                "intro\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nend",
                "intro\n\n𝗮 | 𝗯\n1 | 2\n\nend\n",
                id="table_is_separated_from_the_text_around_it",
            ),
            pytest.param(
                "<table>\n<tr>\n<td>a</td>\n<td>b</td>\n</tr>\n</table>",
                "a | b\n",
                id="raw_html_table_ignores_the_whitespace_between_its_cells",
            ),
        ],
    )
    def test_tables(self, markdown: str, expected: str) -> None:
        assert convert(markdown) == expected

    # ── blockquotes, breaks and raw HTML ──────────────────────────────────────

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param(
                "> quoted text",
                "quoted text\n",
                id="blockquote_loses_its_marker",
            ),
            # A regex pipeline stripped one level and left the other behind.
            pytest.param(
                ">> inner",
                "inner\n",
                id="nested_blockquote_loses_every_level",
            ),
            pytest.param(
                "before\n\n---\n\nafter",
                "before\n\nafter\n",
                id="thematic_break_is_dropped",
            ),
            # Spaced out, the line is still a break rather than a bullet holding
            # the remaining markers.
            pytest.param(
                "before\n\n* * *\n\nafter",
                "before\n\nafter\n",
                id="spaced_thematic_break_is_dropped",
            ),
            pytest.param(
                "before\n\n_ _ _\n\nafter",
                "before\n\nafter\n",
                id="spaced_underscore_break_is_dropped",
            ),
            pytest.param(
                "* * *\n\n**bold**",
                "𝗯𝗼𝗹𝗱\n",
                id="emphasis_after_a_break_still_converts",
            ),
            pytest.param(
                "Line 1  \nLine 2",
                "Line 1\nLine 2\n",
                id="hard_break_becomes_a_newline",
            ),
        ],
    )
    def test_blockquotes_and_breaks(self, markdown: str, expected: str) -> None:
        assert convert(markdown) == expected

    def test_a_document_of_nothing_but_a_break_renders_nothing(self) -> None:
        assert convert("* * *") == "\n"
        assert convert("_ _ _") == "\n"

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param(
                "line1<br>line2",
                "line1\nline2\n",
                id="html_break_becomes_a_newline",
            ),
            pytest.param(
                '<span class="x">hello</span>',
                "hello\n",
                id="html_tags_are_stripped_and_their_text_kept",
            ),
            pytest.param(
                '**<span style="color: black">Dr. Patil</span>**',
                "𝗗𝗿. 𝗣𝗮𝘁𝗶𝗹\n",
                id="html_inside_emphasis_is_stripped",
            ),
            # Raw HTML is read for its text, and a script holds none.
            pytest.param(
                "<script>alert(1)</script>ok",
                "ok\n",
                id="script_content_is_dropped",
            ),
            pytest.param(
                "<style>p{color:red}</style>ok",
                "ok\n",
                id="style_content_is_dropped",
            ),
            pytest.param(
                "text <!-- hidden --> more",
                "text  more\n",
                id="html_comment_is_dropped",
            ),
            pytest.param("a &gt; b", "a > b\n", id="html_entities_are_decoded"),
            # Without a list around it there is nothing for the item to be part
            # of, so its content gets a line rather than a marker.
            pytest.param(
                "<li>x</li>",
                "x\n",
                id="stray_html_list_item_is_not_a_bullet",
            ),
            pytest.param(
                '<ol start="oops"><li>x</li></ol>',
                "1. x\n",
                id="unreadable_html_list_start_falls_back_to_one",
            ),
            pytest.param(
                '<ol start="7"><li>x</li></ol>',
                "7. x\n",
                id="html_list_start_is_honoured",
            ),
        ],
    )
    def test_raw_html(self, markdown: str, expected: str) -> None:
        assert convert(markdown) == expected

    # ── whitespace ────────────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param("", "", id="empty_string_converts_to_nothing"),
            pytest.param("   \n  ", "", id="whitespace_only_input_converts_to_nothing"),
            pytest.param("hello", "hello\n", id="output_ends_in_exactly_one_newline"),
            pytest.param(
                "a\n\n\n\n\n\n\nb",
                "a\n\nb\n",
                id="blank_lines_between_paragraphs_are_collapsed",
            ),
            # Exactly three newlines: the block boundaries never emit more than
            # two, so raw HTML is the only source of a longer run.
            pytest.param(
                "<div>a\n\n\nb</div>",
                "a\n\nb\n",
                id="blank_lines_inside_raw_html_are_collapsed",
            ),
            pytest.param(
                "**hello**\r\n*world*",
                "𝗵𝗲𝗹𝗹𝗼\n𝘸𝘰𝘳𝘭𝘥\n",
                id="windows_line_endings_are_normalised",
            ),
        ],
    )
    def test_whitespace(self, markdown: str, expected: str) -> None:
        assert convert(markdown) == expected

    def test_no_line_ends_in_blank_space(self) -> None:
        result = convert("- a\n\n  more\n\n-\n  - b\n\n| x |\n|---|\n| y |")
        assert not re.search(r"[ \t]\n", result)

    # ── passthrough ───────────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [
            pytest.param("**Hello** 🎉", "𝗛𝗲𝗹𝗹𝗼 🎉\n", id="emoji_passes_through"),
            pytest.param(
                "**café** résumé",
                "𝗰𝗮𝗳é résumé\n",
                id="accented_characters_pass_through",
            ),
        ],
    )
    def test_passthrough(self, markdown: str, expected: str) -> None:
        assert convert(markdown) == expected


# ── Renderer ──────────────────────────────────────────────────────────────────


def _render(html: str) -> str:
    return Renderer(preserve_links=False, monospace_code=True).render(
        LexborHTMLParser(html).root,
    )


class TestRenderer:
    def test_an_absent_tree_renders_nothing(self) -> None:
        # ``LexborHTMLParser.root`` is optional, so the renderer has to cope with it.
        assert not Renderer(preserve_links=False, monospace_code=True).render(None)

    def test_a_block_is_padded_on_both_sides(self) -> None:
        # The renderer surrounds every block with blank lines and leaves the
        # document edges to ``convert``, which strips them.
        assert _render("<p>a</p>") == "\n\na\n\n"

    def test_consecutive_blocks_share_one_blank_line(self) -> None:
        assert _render("<p>a</p><p>b</p>") == "\n\na\n\nb\n\n"


# ── convert_file ──────────────────────────────────────────────────────────────


def _write_markdown(tmp_path: Path, text: str) -> Path:
    src = tmp_path / "test.md"
    src.write_text(text, encoding="utf-8")
    return src


class TestConvertFile:
    def test_basic_conversion(self, tmp_path: Path) -> None:
        src = _write_markdown(tmp_path, "**bold** text")
        out = convert_file(src)
        assert out.read_text(encoding="utf-8") == "𝗯𝗼𝗹𝗱 text\n"

    def test_default_output_path(self, tmp_path: Path) -> None:
        src = _write_markdown(tmp_path, "hello")
        out = convert_file(src)
        assert out == tmp_path / "test.linkedin.txt"

    def test_explicit_output_path(self, tmp_path: Path) -> None:
        src = _write_markdown(tmp_path, "hello")
        dst = tmp_path / "output.txt"
        out = convert_file(src, dst)
        assert out == dst
        assert dst.read_text(encoding="utf-8") == "hello\n"

    def test_preserve_links_forwarded(self, tmp_path: Path) -> None:
        src = _write_markdown(tmp_path, "[GitHub](https://github.com)")
        out = convert_file(src, preserve_links=True)
        assert out.read_text(encoding="utf-8") == "[GitHub](https://github.com)\n"

    def test_string_path_accepted(self, tmp_path: Path) -> None:
        src = _write_markdown(tmp_path, "hello")
        out = convert_file(str(src))
        assert out == tmp_path / "test.linkedin.txt"
        assert out.read_text(encoding="utf-8") == "hello\n"

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.md"
        # The error message must name the missing path so that users can
        # diagnose the failure; mutmut mutates the f-string body to `None`.
        # `re.escape` is required so Windows path separators aren't treated
        # as regex escapes.
        with pytest.raises(
            FileNotFoundError,
            match=re.escape(f"Input file not found: {missing}"),
        ):
            convert_file(missing)

    def test_default_strips_links(self, tmp_path: Path) -> None:
        # The default value of ``preserve_links`` MUST be False, i.e. links
        # are stripped to their display text unless the caller opts in.
        src = _write_markdown(tmp_path, "[GitHub](https://github.com)")
        out = convert_file(src)
        assert out.read_text(encoding="utf-8") == "GitHub\n"

    def test_output_is_utf8(self, tmp_path: Path) -> None:
        src = _write_markdown(tmp_path, "**café** résumé 🎉")
        out = convert_file(src)
        assert out.read_text(encoding="utf-8") == "𝗰𝗮𝗳é résumé 🎉\n"

    def test_monospace_code_forwarded(self, tmp_path: Path) -> None:
        src = _write_markdown(tmp_path, "use `hello` here")
        out = convert_file(src, monospace_code=False)
        assert out.read_text(encoding="utf-8") == "use hello here\n"

    def test_monospace_code_default(self, tmp_path: Path) -> None:
        src = _write_markdown(tmp_path, "use `hello` here")
        out = convert_file(src)
        assert out.read_text(encoding="utf-8") == "use 𝚑𝚎𝚕𝚕𝚘 here\n"

    def test_returns_path_object(self, tmp_path: Path) -> None:
        src = _write_markdown(tmp_path, "hello")
        result = convert_file(src)
        assert isinstance(result, Path)

    def test_read_text_called_with_utf8_encoding(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Guard against a mutation that flips ``encoding=_ENCODING`` on
        # ``input_path.read_text`` to ``encoding=None`` or drops the
        # keyword argument entirely.  Both variants are indistinguishable
        # on Linux/macOS at runtime (the default locale is already
        # UTF-8), so we assert the argument explicitly via a spy.
        src = _write_markdown(tmp_path, "hello")

        recorded: dict[str, object] = {}

        def spy_read_text(
            self: Path,
            encoding: str | None = None,
            errors: str | None = None,
            newline: str | None = None,
        ) -> str:
            if self == src:
                recorded["encoding"] = encoding
            # Bypass the patched method by using the underlying file API.
            with self.open(encoding=encoding, errors=errors, newline=newline) as f:
                return f.read()

        monkeypatch.setattr(Path, "read_text", spy_read_text)
        convert_file(src)

        # ``encoding="utf-8"`` must be passed explicitly.  Mutations to
        # ``None`` or an arg-drop (which defaults to ``None``) both fail.
        assert recorded["encoding"] == "utf-8"

    def test_write_text_called_with_utf8_encoding(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Guard against a mutation that flips ``encoding=_ENCODING`` on
        # ``output_path.write_text`` to ``encoding=None`` or drops the
        # keyword argument entirely.  Both variants are indistinguishable
        # on Linux/macOS at runtime (the default locale is already
        # UTF-8), so we assert the argument explicitly via a spy.
        src = _write_markdown(tmp_path, "hello")

        recorded: dict[str, object] = {}

        def spy_write_text(
            self: Path,
            data: str,
            encoding: str | None = None,
            errors: str | None = None,
            newline: str | None = None,
        ) -> int:
            if self != src:
                recorded["encoding"] = encoding
                recorded["data"] = data
            # Bypass the patched method by using the underlying file API.
            with self.open(
                "w",
                encoding=encoding,
                errors=errors,
                newline=newline,
            ) as f:
                return f.write(data)

        monkeypatch.setattr(Path, "write_text", spy_write_text)
        convert_file(src)

        # ``encoding="utf-8"`` must be passed explicitly.  Mutations to
        # ``None`` or an arg-drop (which defaults to ``None``) both fail.
        assert recorded["encoding"] == "utf-8"
        assert recorded["data"] == "hello\n"


@pytest.mark.skipif(
    sys.version_info < (3, 15),
    reason="lazy imports (PEP 810) need Python 3.15+",
)
def test_parser_extensions_load_on_first_conversion() -> None:
    # A fresh interpreter, since this test session has loaded them already.
    code = """
import sys
import md2linkedin
loaded = lambda: [name in sys.modules for name in ("comrak", "selectolax.lexbor")]
print(loaded())
md2linkedin.convert("**hi**")
print(loaded())
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        check=True,
        text=True,
    )
    assert result.stdout.splitlines() == ["[False, False]", "[True, True]"]
