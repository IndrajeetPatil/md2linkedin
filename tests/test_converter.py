"""Tests for md2linkedin._converter — the Markdown conversion pipeline."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from selectolax.parser import HTMLParser

from md2linkedin._converter import Renderer, convert, convert_file


class TestConvert:
    # ── emphasis ──────────────────────────────────────────────────────────────

    def test_bold(self) -> None:
        result = convert("**hello**")
        assert result == "𝗵𝗲𝗹𝗹𝗼\n"

    def test_bold_underscores(self) -> None:
        assert convert("__hello__") == "𝗵𝗲𝗹𝗹𝗼\n"

    def test_italic(self) -> None:
        assert convert("*hello*") == "𝘩𝘦𝘭𝘭𝘰\n"

    def test_italic_underscores(self) -> None:
        assert convert("_hello_") == "𝘩𝘦𝘭𝘭𝘰\n"

    def test_bold_italic(self) -> None:
        # Three markers are one bold-italic span, not bold wrapping italic.
        assert convert("***hello***") == "𝙝𝙚𝙡𝙡𝙤\n"

    def test_italic_nested_in_bold(self) -> None:
        assert convert("**bold and *italic* inside**") == "𝗯𝗼𝗹𝗱 𝗮𝗻𝗱 𝙞𝙩𝙖𝙡𝙞𝙘 𝗶𝗻𝘀𝗶𝗱𝗲\n"

    def test_bold_and_italic_together(self) -> None:
        assert convert("**bold** and *italic*") == "𝗯𝗼𝗹𝗱 and 𝘪𝘵𝘢𝘭𝘪𝘤\n"

    def test_digits_inside_bold_are_converted(self) -> None:
        assert convert("**123**") == "𝟭𝟮𝟯\n"

    def test_snake_case_is_not_italicised(self) -> None:
        # Underscores inside a word are not emphasis markers.
        assert convert("some_variable_name") == "some_variable_name\n"

    def test_escaped_asterisk_is_not_emphasis(self) -> None:
        assert convert(r"\*not italic\*") == "*not italic*\n"

    def test_unmatched_marker_is_left_alone(self) -> None:
        assert convert("price: $10 * 3") == "price: $10 * 3\n"

    def test_strikethrough_markers_are_dropped(self) -> None:
        # LinkedIn has no strikethrough, so the text is kept and the markers
        # go, rather than being left in the output as punctuation.
        assert convert("~~strike~~ text") == "strike text\n"

    # ── headings ──────────────────────────────────────────────────────────────

    def test_heading_h1_is_bold_upper_between_rules(self) -> None:
        rule = "━" * 40
        assert convert("# Hello") == f"{rule}\n𝗛𝗘𝗟𝗟𝗢\n{rule}\n"

    def test_heading_h2_is_bold_without_a_rule(self) -> None:
        assert convert("## Sub-section") == "𝗦𝘂𝗯-𝘀𝗲𝗰𝘁𝗶𝗼𝗻\n"

    def test_heading_h6_is_bold_without_a_rule(self) -> None:
        assert convert("###### Deep") == "𝗗𝗲𝗲𝗽\n"

    def test_setext_h1_is_a_heading(self) -> None:
        assert "━" in convert("Title\n=====")

    def test_setext_h2_is_a_heading(self) -> None:
        assert convert("Title\n-----") == "𝗧𝗶𝘁𝗹𝗲\n"

    def test_heading_is_separated_from_the_text_below_it(self) -> None:
        assert convert("## Heading\n\nbody") == "𝗛𝗲𝗮𝗱𝗶𝗻𝗴\n\nbody\n"

    # ── code ──────────────────────────────────────────────────────────────────

    def test_inline_code_is_monospaced_by_default(self) -> None:
        assert convert("use `hello` here") == "use 𝚑𝚎𝚕𝚕𝚘 here\n"

    def test_inline_code_is_plain_when_monospace_is_off(self) -> None:
        assert convert("use `hello` here", monospace_code=False) == "use hello here\n"

    def test_fenced_code_is_monospaced_by_default(self) -> None:
        assert convert("```python\nprint('hello')\n```") == "𝚙𝚛𝚒𝚗𝚝('𝚑𝚎𝚕𝚕𝚘')\n"

    def test_fenced_code_is_plain_when_monospace_is_off(self) -> None:
        result = convert("```python\nprint('hello')\n```", monospace_code=False)
        assert result == "print('hello')\n"

    def test_indented_code_block_is_a_code_block(self) -> None:
        # Four spaces open a code block, which a regex pipeline read as prose.
        assert convert("    print(1)") == "𝚙𝚛𝚒𝚗𝚝(𝟷)\n"

    def test_markdown_inside_code_is_not_converted(self) -> None:
        # Only ASCII letters and digits are remapped, so the ``**`` survives
        # and nothing inside the span is read as emphasis.
        assert convert("use `**bold**` here") == "use **𝚋𝚘𝚕𝚍** here\n"

    def test_markdown_inside_plain_code_is_left_alone(self) -> None:
        assert (
            convert("use `**bold**` here", monospace_code=False)
            == "use **bold** here\n"
        )

    # ── links and images ──────────────────────────────────────────────────────

    def test_link_is_reduced_to_its_text(self) -> None:
        assert convert("[GitHub](https://github.com)") == "GitHub\n"

    def test_link_is_kept_whole_when_preserved(self) -> None:
        result = convert("[GitHub](https://github.com)", preserve_links=True)
        assert result == "[GitHub](https://github.com)\n"

    def test_link_title_is_kept_when_preserved(self) -> None:
        result = convert('[GitHub](https://github.com "Home")', preserve_links=True)
        assert result == '[GitHub](https://github.com "Home")\n'

    def test_styled_link_text_is_converted(self) -> None:
        assert convert("**[bold link](https://x.com)**") == "𝗯𝗼𝗹𝗱 𝗹𝗶𝗻𝗸\n"

    def test_link_text_in_several_styles_is_joined_seamlessly(self) -> None:
        result = convert("[**bold** and plain](https://x.com)", preserve_links=True)
        assert result == "[𝗯𝗼𝗹𝗱 and plain](https://x.com)\n"

    def test_a_link_without_a_url_is_preserved_with_an_empty_target(self) -> None:
        # Only raw HTML can spell an anchor with no ``href`` at all.
        assert convert("<a>text</a>", preserve_links=True) == "[text]()\n"

    def test_a_link_with_no_text_leaves_the_spacing_alone(self) -> None:
        # Writing nothing must not look like writing a line without newlines,
        # or the paragraph after it would gain a blank line.
        assert convert("a\n\n[](https://example.com)\n\nb") == "a\n\nb\n"

    def test_autolink_is_reduced_to_the_url(self) -> None:
        assert convert("<https://example.com>") == "https://example.com\n"

    def test_autolink_keeps_its_brackets_when_preserved(self) -> None:
        result = convert("<https://example.com>", preserve_links=True)
        assert result == "<https://example.com>\n"

    def test_bare_url_is_a_link(self) -> None:
        # The autolink extension turns a bare URL into a link, so preserving
        # links spells it as an autolink rather than as ``[url](url)``.
        assert convert("see https://example.com", preserve_links=True) == (
            "see <https://example.com>\n"
        )

    def test_reference_style_link_is_resolved(self) -> None:
        # The definition is consumed by the parser instead of being left in
        # the output as text.
        assert convert("[text][ref]\n\n[ref]: https://example.com") == "text\n"

    def test_image_is_reduced_to_its_alt_text(self) -> None:
        assert convert("![Logo](logo.png)") == "Logo\n"

    def test_image_without_alt_text_renders_nothing(self) -> None:
        assert convert("![](logo.png)") == "\n"

    # ── lists ─────────────────────────────────────────────────────────────────

    def test_bullet_list(self) -> None:
        assert convert("- item one\n- item two") == "• item one\n• item two\n"

    def test_nested_bullets_get_their_own_marker_per_level(self) -> None:
        result = convert("- a\n  - b\n    - c\n      - d")
        assert result == "• a\n  ‣ b\n    ◦ c\n      ▪ d\n"

    def test_bullets_past_the_fourth_level_reuse_the_last_marker(self) -> None:
        result = convert("- a\n  - b\n    - c\n      - d\n        - e")
        assert result == "• a\n  ‣ b\n    ◦ c\n      ▪ d\n        ▪ e\n"

    def test_four_space_indentation_nests_like_two(self) -> None:
        # Depth comes from the parsed tree, not from the indentation width.
        assert convert("- a\n    - b") == "• a\n  ‣ b\n"

    def test_one_extra_space_is_not_a_nesting_level(self) -> None:
        # Markdown allows a top-level item up to three leading spaces.
        assert convert("- a\n - b") == "• a\n• b\n"

    def test_ordered_list_keeps_its_numbers(self) -> None:
        assert convert("1. a\n2. b") == "1. a\n2. b\n"

    def test_ordered_list_starts_where_its_first_item_says(self) -> None:
        assert convert("5. five\n6. six") == "5. five\n6. six\n"

    def test_ordered_list_renumbers_from_its_start(self) -> None:
        # The second item is numbered by the renderer's counter, not by the
        # source, so a mis-numbered list comes out in order.
        assert convert("3. three\n3. four") == "3. three\n4. four\n"

    def test_bullets_nested_under_an_ordered_item_align_under_its_text(self) -> None:
        assert convert("1. parent\n   - child") == "1. parent\n   ‣ child\n"

    def test_ordered_list_nested_under_an_ordered_item(self) -> None:
        assert convert("1. a\n   1. b") == "1. a\n   1. b\n"

    def test_a_continuation_paragraph_stays_inside_its_item(self) -> None:
        assert convert("- a\n\n  more") == "• a\n\n  more\n"

    def test_a_wrapped_line_stays_inside_its_item(self) -> None:
        assert convert("- first line\n  second line") == "• first line\n  second line\n"

    def test_a_code_block_inside_an_item_stays_inside_it(self) -> None:
        result = convert("- item\n\n  ```\n  a = 1\n  b = 2\n  ```")
        assert result == "• item\n\n  𝚊 = 𝟷\n  𝚋 = 𝟸\n"

    def test_a_loose_list_keeps_the_blank_lines_between_its_items(self) -> None:
        assert convert("- a\n\n- b") == "• a\n\n• b\n"

    def test_a_loose_item_is_spaced_by_its_newlines_not_its_last_character(
        self,
    ) -> None:
        # Only the newlines an item ends in decide the gap to the next one;
        # the letters before them are content like any other.
        assert convert("- LaTeX\n\n- Typst") == "• LaTeX\n\n• Typst\n"

    def test_a_trailing_space_inside_an_item_does_not_widen_the_gap(self) -> None:
        result = convert("<ul><li><p>note </p></li><li><p>next</p></li></ul>")
        assert result == "• note\n\n• next\n"

    def test_an_item_holding_only_a_nested_list_leaves_its_marker_bare(self) -> None:
        # The marker is alone on its line, without trailing blank space.
        assert convert("-\n  - b") == "•\n  ‣ b\n"

    def test_list_is_separated_from_the_text_around_it(self) -> None:
        assert convert("intro\n\n- a\n\nend") == "intro\n\n• a\n\nend\n"

    def test_a_bullet_after_a_heading_is_a_list(self) -> None:
        result = convert("# Heading\n\n- first\n  - sub\n- second")
        assert result.endswith("• first\n  ‣ sub\n• second\n")

    def test_an_indented_fenced_block_keeps_the_list_open(self) -> None:
        # Indented, the block is content of the item above rather than a block
        # of its own, so the list continues and ``c`` stays ``b``'s sibling.
        result = convert("- a\n    - b\n    ```\n    code\n    ```\n    - c")
        assert result == "• a\n  ‣ b\n\n  𝚌𝚘𝚍𝚎\n\n  ‣ c\n"

    def test_inline_code_keeps_the_list_open(self) -> None:
        # An inline span is ordinary paragraph content, so the paragraph it
        # sits in carries on the item above it.
        result = convert("- a\n    - b\n`code` continues\n    - c")
        assert result == "• a\n  ‣ b\n    𝚌𝚘𝚍𝚎 continues\n  ‣ c\n"

    def test_an_ordered_marker_after_a_fenced_block_starts_a_list(self) -> None:
        # There is no paragraph above the marker for it to interrupt, so its
        # number does not have to be one.
        result = convert("```\ncode\n```\n2. parent\n    - child")
        assert result == "𝚌𝚘𝚍𝚎\n\n2. parent\n   ‣ child\n"

    def test_an_ordered_marker_inside_a_paragraph_is_prose(self) -> None:
        # Only ``1.`` may interrupt a paragraph, so ``2.`` here is text and
        # the bullet below it nests under ``outer`` instead.
        result = convert("- outer\n  `code` paragraph\n  2. prose\n    - child")
        assert result == "• outer\n  𝚌𝚘𝚍𝚎 paragraph\n  2. prose\n  ‣ child\n"

    def test_an_ordered_marker_after_a_heading_starts_a_list(self) -> None:
        result = convert("## Heading\n2. parent\n    - child")
        assert result == "𝗛𝗲𝗮𝗱𝗶𝗻𝗴\n\n2. parent\n   ‣ child\n"

    def test_an_ordered_marker_beside_a_bullet_starts_a_second_list(self) -> None:
        # A marker of a different kind ends the list above it, so ``2. y`` is
        # a list of its own rather than an item or prose.
        assert convert("- x\n2. y") == "• x\n\n2. y\n"

    def test_a_different_ordered_delimiter_starts_a_second_list(self) -> None:
        assert convert("1. x\n2) y") == "1. x\n\n2. y\n"

    # ── tables ────────────────────────────────────────────────────────────────

    def test_table_header_is_bold_and_cells_are_separated(self) -> None:
        result = convert("| Lang | Users |\n|---|---|\n| Python | 10 |\n| Rust | 5 |")
        assert result == "𝗟𝗮𝗻𝗴 | 𝗨𝘀𝗲𝗿𝘀\nPython | 10\nRust | 5\n"

    def test_a_single_column_table_needs_no_separator(self) -> None:
        assert convert("| col |\n|---|\n| cell |") == "𝗰𝗼𝗹\ncell\n"

    def test_table_cells_keep_their_own_formatting(self) -> None:
        result = convert("| a |\n|---|\n| `code` |")
        assert result == "𝗮\n𝚌𝚘𝚍𝚎\n"

    def test_table_is_separated_from_the_text_around_it(self) -> None:
        result = convert("intro\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nend")
        assert result == "intro\n\n𝗮 | 𝗯\n1 | 2\n\nend\n"

    def test_raw_html_table_ignores_the_whitespace_between_its_cells(self) -> None:
        result = convert("<table>\n<tr>\n<td>a</td>\n<td>b</td>\n</tr>\n</table>")
        assert result == "a | b\n"

    # ── blockquotes, breaks and raw HTML ──────────────────────────────────────

    def test_blockquote_loses_its_marker(self) -> None:
        assert convert("> quoted text") == "quoted text\n"

    def test_nested_blockquote_loses_every_level(self) -> None:
        # A regex pipeline stripped one level and left the other behind.
        assert convert(">> inner") == "inner\n"

    def test_thematic_break_is_dropped(self) -> None:
        assert convert("before\n\n---\n\nafter") == "before\n\nafter\n"

    def test_spaced_thematic_break_is_dropped(self) -> None:
        # Spaced out, the line is still a break rather than a bullet holding
        # the remaining markers.
        assert convert("before\n\n* * *\n\nafter") == "before\n\nafter\n"

    def test_spaced_underscore_break_is_dropped(self) -> None:
        assert convert("before\n\n_ _ _\n\nafter") == "before\n\nafter\n"

    def test_a_document_of_nothing_but_a_break_renders_nothing(self) -> None:
        assert convert("* * *") == "\n"
        assert convert("_ _ _") == "\n"

    def test_emphasis_after_a_break_still_converts(self) -> None:
        assert convert("* * *\n\n**bold**") == "𝗯𝗼𝗹𝗱\n"

    def test_hard_break_becomes_a_newline(self) -> None:
        assert convert("Line 1  \nLine 2") == "Line 1\nLine 2\n"

    def test_html_break_becomes_a_newline(self) -> None:
        assert convert("line1<br>line2") == "line1\nline2\n"

    def test_html_tags_are_stripped_and_their_text_kept(self) -> None:
        assert convert('<span class="x">hello</span>') == "hello\n"

    def test_html_inside_emphasis_is_stripped(self) -> None:
        result = convert('**<span style="color: black">Dr. Patil</span>**')
        assert result == "𝗗𝗿. 𝗣𝗮𝘁𝗶𝗹\n"

    def test_script_content_is_dropped(self) -> None:
        # Raw HTML is read for its text, and a script holds none.
        assert convert("<script>alert(1)</script>ok") == "ok\n"

    def test_style_content_is_dropped(self) -> None:
        assert convert("<style>p{color:red}</style>ok") == "ok\n"

    def test_html_comment_is_dropped(self) -> None:
        assert convert("text <!-- hidden --> more") == "text  more\n"

    def test_html_entities_are_decoded(self) -> None:
        assert convert("a &gt; b") == "a > b\n"

    def test_stray_html_list_item_is_not_a_bullet(self) -> None:
        # Without a list around it there is nothing for the item to be part
        # of, so its content gets a line rather than a marker.
        assert convert("<li>x</li>") == "x\n"

    def test_unreadable_html_list_start_falls_back_to_one(self) -> None:
        assert convert('<ol start="oops"><li>x</li></ol>') == "1. x\n"

    def test_html_list_start_is_honoured(self) -> None:
        assert convert('<ol start="7"><li>x</li></ol>') == "7. x\n"

    # ── whitespace ────────────────────────────────────────────────────────────

    def test_empty_string_converts_to_nothing(self) -> None:
        assert not convert("")

    def test_whitespace_only_input_converts_to_nothing(self) -> None:
        assert not convert("   \n  ")

    def test_output_ends_in_exactly_one_newline(self) -> None:
        assert convert("hello") == "hello\n"

    def test_blank_lines_between_paragraphs_are_collapsed(self) -> None:
        assert convert("a\n\n\n\n\n\n\nb") == "a\n\nb\n"

    def test_blank_lines_inside_raw_html_are_collapsed(self) -> None:
        # Exactly three newlines: the block boundaries never emit more than
        # two, so raw HTML is the only source of a longer run.
        assert convert("<div>a\n\n\nb</div>") == "a\n\nb\n"

    def test_windows_line_endings_are_normalised(self) -> None:
        assert convert("**hello**\r\n*world*") == "𝗵𝗲𝗹𝗹𝗼\n𝘸𝘰𝘳𝘭𝘥\n"

    def test_no_line_ends_in_blank_space(self) -> None:
        result = convert("- a\n\n  more\n\n-\n  - b\n\n| x |\n|---|\n| y |")
        assert not re.search(r"[ \t]\n", result)

    # ── passthrough ───────────────────────────────────────────────────────────

    def test_emoji_passes_through(self) -> None:
        assert convert("**Hello** 🎉") == "𝗛𝗲𝗹𝗹𝗼 🎉\n"

    def test_accented_characters_pass_through(self) -> None:
        assert convert("**café** résumé") == "𝗰𝗮𝗳é résumé\n"


# ── Renderer ──────────────────────────────────────────────────────────────────


def _render(html: str) -> str:
    return Renderer(preserve_links=False, monospace_code=True).render(
        HTMLParser(html).root,
    )


class TestRenderer:
    def test_an_absent_tree_renders_nothing(self) -> None:
        # ``HTMLParser.root`` is optional, so the renderer has to cope with it.
        assert not Renderer(preserve_links=False, monospace_code=True).render(None)

    def test_a_block_is_padded_on_both_sides(self) -> None:
        # The renderer surrounds every block with blank lines and leaves the
        # document edges to ``convert``, which strips them.
        assert _render("<p>a</p>") == "\n\na\n\n"

    def test_consecutive_blocks_share_one_blank_line(self) -> None:
        assert _render("<p>a</p><p>b</p>") == "\n\na\n\nb\n\n"


# ── convert_file ──────────────────────────────────────────────────────────────


class TestConvertFile:
    def test_basic_conversion(self, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("**bold** text", encoding="utf-8")
        out = convert_file(src)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "**" not in content

    def test_default_output_path(self, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        out = convert_file(src)
        assert out.suffix == ".txt"
        assert "linkedin" in out.name

    def test_explicit_output_path(self, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        dst = tmp_path / "output.txt"
        src.write_text("hello", encoding="utf-8")
        out = convert_file(src, dst)
        assert out == dst
        assert dst.exists()

    def test_preserve_links_forwarded(self, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("[GitHub](https://github.com)", encoding="utf-8")
        out = convert_file(src, preserve_links=True)
        assert out.read_text(encoding="utf-8").strip() == "[GitHub](https://github.com)"

    def test_string_path_accepted(self, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        out = convert_file(str(src))
        assert out.exists()

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.md"
        # The error message must name the missing path so that users can
        # diagnose the failure; mutmut mutates the f-string body to `None`.
        # `re.escape` is required so Windows path separators aren't treated
        # as regex escapes.
        with pytest.raises(FileNotFoundError, match=re.escape(str(missing))):
            convert_file(missing)

    def test_default_strips_links(self, tmp_path: Path) -> None:
        # The default value of ``preserve_links`` MUST be False, i.e. links
        # are stripped to their display text unless the caller opts in.
        src = tmp_path / "test.md"
        src.write_text("[GitHub](https://github.com)", encoding="utf-8")
        out = convert_file(src)
        content = out.read_text(encoding="utf-8").strip()
        assert content == "GitHub"

    def test_output_is_utf8(self, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("**café** résumé 🎉", encoding="utf-8")
        out = convert_file(src)
        content = out.read_text(encoding="utf-8")
        assert "é" in content
        assert "🎉" in content

    def test_monospace_code_forwarded(self, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("use `hello` here", encoding="utf-8")
        out = convert_file(src, monospace_code=False)
        content = out.read_text(encoding="utf-8")
        assert "hello" in content
        assert "𝚑𝚎𝚕𝚕𝚘" not in content

    def test_monospace_code_default(self, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("use `hello` here", encoding="utf-8")
        out = convert_file(src)
        content = out.read_text(encoding="utf-8")
        assert "𝚑𝚎𝚕𝚕𝚘" in content

    def test_returns_path_object(self, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
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
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")

        recorded: dict[str, object] = {}

        def spy_read_text(
            self: Path,
            encoding: str | None = None,
            errors: str | None = None,
            newline: str | None = None,
        ) -> str:
            if self == src:
                recorded["encoding"] = encoding
                recorded["errors"] = errors
                recorded["newline"] = newline
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
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")

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
                recorded["errors"] = errors
                recorded["newline"] = newline
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
        assert isinstance(recorded["data"], str)
