"""Tests for md2linkedin._converter — the Markdown conversion pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from md2linkedin._converter import (
    _clean_entities,
    _clean_escaped_chars,
    _convert_bold,
    _convert_bold_italic,
    _convert_bullets,
    _convert_headers,
    _convert_italic,
    _normalize_line_endings,
    _normalize_whitespace,
    _protect_code,
    _restore_code,
    _strip_blockquotes,
    _strip_html_spans,
    _strip_images,
    _strip_links,
    convert,
    convert_file,
)

# ── _normalize_line_endings ────────────────────────────────────────────────────


class TestNormalizeLineEndings:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("a\r\nb", "a\nb"),
            ("a\rb", "a\nb"),
            ("a\nb", "a\nb"),
            ("", ""),
            ("a\r\nb\rc\nd", "a\nb\nc\nd"),
        ],
        ids=["crlf", "cr", "lf_unchanged", "empty", "mixed"],
    )
    def test_line_endings(self, text: str, expected: str) -> None:
        assert _normalize_line_endings(text) == expected


# ── _protect_code / _restore_code ─────────────────────────────────────────────


class TestProtectAndRestoreCode:
    def test_inline_code_protected(self) -> None:
        text, placeholders = _protect_code("say `hello world` here")
        assert "`hello world`" not in text
        assert len(placeholders) == 1

    def test_inline_code_content_preserved_on_restore(self) -> None:
        text, placeholders = _protect_code("say `hello world` here")
        restored = _restore_code(text, placeholders, monospace=False)
        # Backticks are stripped on restore
        assert restored == "say hello world here"

    def test_fenced_block_protected(self) -> None:
        text, placeholders = _protect_code("```python\nprint('hi')\n```")
        assert "print" not in text
        assert len(placeholders) == 1

    def test_fenced_block_restored_verbatim(self) -> None:
        original = "```python\nprint('hi')\n```"
        text, placeholders = _protect_code(original)
        restored = _restore_code(text, placeholders, monospace=False)
        assert restored == original

    def test_default_monospace_flag_is_false(self) -> None:
        # The default value of `monospace` must be False — a fenced block
        # is restored verbatim (fences intact) unless monospace=True is
        # passed explicitly.
        original = "```py\nprint('x')\n```"
        text, placeholders = _protect_code(original)
        restored = _restore_code(text, placeholders)
        assert restored == original

    def test_tilde_fenced_block(self) -> None:
        original = "~~~\nsome code\n~~~"
        text, placeholders = _protect_code(original)
        restored = _restore_code(text, placeholders, monospace=False)
        assert restored == original

    def test_code_not_transformed_by_bold(self) -> None:
        text, placeholders = _protect_code("use `**bold**` code")
        # Bold markers inside code are hidden from the converter
        assert "**bold**" not in text
        restored = _restore_code(text, placeholders, monospace=False)
        assert restored == "use **bold** code"

    def test_inline_code_monospace(self) -> None:
        text, placeholders = _protect_code("say `hello` here")
        restored = _restore_code(text, placeholders, monospace=True)
        assert restored == "say 𝚑𝚎𝚕𝚕𝚘 here"

    def test_fenced_block_monospace(self) -> None:
        text, placeholders = _protect_code("```python\nprint('hi')\n```")
        restored = _restore_code(text, placeholders, monospace=True)
        # Body only — fence stripped, language tag stripped, ASCII mapped.
        assert restored == "𝚙𝚛𝚒𝚗𝚝('𝚑𝚒')\n"

    def test_tilde_fenced_block_monospace(self) -> None:
        text, placeholders = _protect_code("~~~\nsome code\n~~~")
        restored = _restore_code(text, placeholders, monospace=True)
        # Content only; leading language tag is empty; body preserved.
        assert restored == "𝚜𝚘𝚖𝚎 𝚌𝚘𝚍𝚎\n"

    def test_fenced_block_monospace_empty_body(self) -> None:
        text, placeholders = _protect_code("``````")
        restored = _restore_code(text, placeholders, monospace=True)
        assert not restored

    def test_fenced_block_no_newline_body_monospace(self) -> None:
        # A degenerate fenced block that has no newline in its body — the
        # implementation treats it as empty content (guarding the
        # `first_nl == -1` sentinel branch).
        text, placeholders = _protect_code("```hi```")
        restored = _restore_code(text, placeholders, monospace=True)
        assert not restored

    def test_fenced_block_monospace_preserves_syntax_chars(self) -> None:
        text, placeholders = _protect_code("```\n**not bold**\n```")
        restored = _restore_code(text, placeholders, monospace=True)
        # ** should pass through unchanged (not ASCII letters/digits)
        assert restored == "**𝚗𝚘𝚝 𝚋𝚘𝚕𝚍**\n"

    def test_empty_no_placeholders(self) -> None:
        text, placeholders = _protect_code("no code here")
        assert text == "no code here"
        assert placeholders == {}


# ── _strip_html_spans ─────────────────────────────────────────────────────────


class TestStripHtmlSpans:
    def test_simple_span(self) -> None:
        assert _strip_html_spans('<span class="x">hello</span>') == "hello"

    def test_nested_spans(self) -> None:
        result = _strip_html_spans('<span><span class="inner">text</span></span>')
        assert result == "text"

    def test_no_spans_unchanged(self) -> None:
        assert _strip_html_spans("plain text") == "plain text"

    def test_span_with_style(self) -> None:
        result = _strip_html_spans('<span style="font-weight:bold">Bold</span>')
        assert result == "Bold"

    def test_multiline_span(self) -> None:
        result = _strip_html_spans("<span>\nhello\n</span>")
        assert result == "\nhello\n"

    def test_empty_string(self) -> None:
        # An empty input must still terminate the loop and return the empty
        # string (the while-true guard exits on the first iteration).
        assert not _strip_html_spans("")

    def test_text_with_no_spans_single_pass(self) -> None:
        # No spans and non-empty input — result MUST equal the exact input.
        text = "just some plain text"
        assert _strip_html_spans(text) == text


# ── _convert_bold_italic ──────────────────────────────────────────────────────


class TestConvertBoldItalic:
    def test_triple_asterisk(self) -> None:
        result = _convert_bold_italic("***hello***")
        assert result == "𝙝𝙚𝙡𝙡𝙤"

    def test_triple_underscore(self) -> None:
        # The underscore variant must produce the same bold-italic Unicode
        # output as the asterisk variant.
        assert _convert_bold_italic("___hello___") == "𝙝𝙚𝙡𝙡𝙤"

    def test_no_change_for_bold_only(self) -> None:
        text = "**hello**"
        assert _convert_bold_italic(text) == text

    def test_no_change_for_italic_only(self) -> None:
        text = "*hello*"
        assert _convert_bold_italic(text) == text

    def test_passthrough_non_ascii(self) -> None:
        assert _convert_bold_italic("***café***") == "𝙘𝙖𝙛é"


# ── _convert_bold ─────────────────────────────────────────────────────────────


class TestConvertBold:
    def test_double_asterisk(self) -> None:
        assert _convert_bold("**hello**") == "𝗵𝗲𝗹𝗹𝗼"

    def test_double_underscore(self) -> None:
        assert _convert_bold("__hello__") == "𝗵𝗲𝗹𝗹𝗼"

    def test_preserves_surrounding_text(self) -> None:
        assert _convert_bold("before **bold** after") == "before 𝗯𝗼𝗹𝗱 after"

    def test_multiple_bold_spans(self) -> None:
        assert _convert_bold("**a** and **b**") == "𝗮 and 𝗯"

    def test_no_change_for_italic(self) -> None:
        text = "*hello*"
        assert _convert_bold(text) == text


# ── _convert_italic ───────────────────────────────────────────────────────────


class TestConvertItalic:
    def test_single_asterisk(self) -> None:
        assert _convert_italic("*hello*") == "𝘩𝘦𝘭𝘭𝘰"

    def test_single_underscore(self) -> None:
        assert _convert_italic("_hello_") == "𝘩𝘦𝘭𝘭𝘰"

    def test_no_match_inside_word_underscore(self) -> None:
        # snake_case should not be affected
        text = "snake_case_var"
        assert _convert_italic(text) == text

    def test_preserves_surrounding_text(self) -> None:
        assert _convert_italic("before *italic* after") == "before 𝘪𝘵𝘢𝘭𝘪𝘤 after"

    def test_no_change_for_bold_markers(self) -> None:
        # Bold markers (**) should not be consumed by italic pattern
        text = "**bold**"
        assert _convert_italic(text) == text


# ── _convert_headers ──────────────────────────────────────────────────────────


class TestConvertHeaders:
    _SEP = "━" * 40

    def test_h1_full_output(self) -> None:
        # H1 is uppercased, wrapped in ━×40 separators, and bolded.
        expected = f"\n{self._SEP}\n𝗛𝗘𝗟𝗟𝗢\n{self._SEP}\n"
        assert _convert_headers("# Hello") == expected

    def test_h1_separator_length(self) -> None:
        # The separator MUST be exactly 40 ━ characters.
        result = _convert_headers("# X")
        sep_line = result.split("\n")[1]
        assert sep_line == self._SEP
        assert len(sep_line) == 40

    def test_h2_full_output(self) -> None:
        assert _convert_headers("## Section") == "𝗦𝗲𝗰𝘁𝗶𝗼𝗻"

    @pytest.mark.parametrize(
        ("level", "expected"),
        [(3, "𝗛𝗲𝗮𝗱𝗶𝗻𝗴"), (4, "𝗛𝗲𝗮𝗱𝗶𝗻𝗴"), (5, "𝗛𝗲𝗮𝗱𝗶𝗻𝗴"), (6, "𝗛𝗲𝗮𝗱𝗶𝗻𝗴")],
    )
    def test_h3_to_h6_bolded_no_separator(self, level: int, expected: str) -> None:
        assert _convert_headers(f"{'#' * level} Heading") == expected

    def test_setext_h1_full_output(self) -> None:
        expected = f"\n{self._SEP}\n𝗧𝗜𝗧𝗟𝗘\n{self._SEP}\n"
        assert _convert_headers("Title\n=====") == expected

    def test_setext_h1_advances_past_underline(self) -> None:
        # After consuming a setext H1 the loop MUST skip BOTH the title
        # and the ==== underline (i += 2). Otherwise the underline leaks
        # into the output as its own line.
        expected = f"\n{self._SEP}\n𝗧𝗜𝗧𝗟𝗘\n{self._SEP}\n\nnext line here"
        assert _convert_headers("Title\n=====\nnext line here") == expected

    def test_setext_h2_full_output(self) -> None:
        assert _convert_headers("Subtitle\n--------") == "𝗦𝘂𝗯𝘁𝗶𝘁𝗹𝗲"

    def test_setext_h2_advances_past_underline(self) -> None:
        assert _convert_headers("Sub\n-----\nnext line here") == "𝗦𝘂𝗯\nnext line here"

    def test_atx_advances_past_header(self) -> None:
        # An ATX header consumes exactly one line — the next line follows.
        expected = f"\n{self._SEP}\n𝗧𝗜𝗧𝗟𝗘\n{self._SEP}\n\nbody"
        assert _convert_headers("# Title\nbody") == expected

    def test_atx_advances_relative_not_absolute(self) -> None:
        # `i += 1` must be an INCREMENT, not `i = 1`. If it were absolute,
        # placing an ATX header at line index >= 2 would cause the loop to
        # reset the cursor to 1 and re-emit line 1, which we can detect.
        text = "line0\nline1\n# H\ntail"
        expected = f"line0\nline1\n\n{self._SEP}\n𝗛\n{self._SEP}\n\ntail"
        assert _convert_headers(text) == expected

    def test_setext_h1_advances_relative_not_absolute(self) -> None:
        text = "prev\nTitle\n=====\ntail"
        expected = f"prev\n\n{self._SEP}\n𝗧𝗜𝗧𝗟𝗘\n{self._SEP}\n\ntail"
        assert _convert_headers(text) == expected

    def test_setext_h2_advances_relative_not_absolute(self) -> None:
        # Place the H2 at index >= 2 so mutating `i += 2` to `i = 2` would
        # rewind the cursor (dropping the earlier lines from the output).
        assert _convert_headers("A\nB\nSub\n-----\ntail") == "A\nB\n𝗦𝘂𝗯\ntail"

    def test_horizontal_rule_advances_relative_not_absolute(self) -> None:
        # An HR at a later position must not reset the cursor to 1 — the
        # preceding lines must be preserved verbatim.
        assert _convert_headers("aaa\nbbb\n***\nccc") == "aaa\nbbb\nccc"

    def test_standalone_horizontal_rule_removed(self) -> None:
        assert not _convert_headers("---")

    def test_horizontal_rule_advances_one_line(self) -> None:
        # After stripping an HR the loop MUST advance exactly one line so
        # the line after the rule is emitted (not skipped, not repeated).
        assert _convert_headers("---\nafter") == "after"

    def test_non_header_unchanged(self) -> None:
        text = "Just a line"
        assert _convert_headers(text) == text

    def test_non_header_advances_one_line(self) -> None:
        # Plain lines must be emitted in order — mutating the line-advance
        # from `i += 1` to `i = 1` would repeat or drop lines.
        text = "line one\nline two\nline three"
        assert _convert_headers(text) == text

    def test_atx_trailing_whitespace_stripped(self) -> None:
        # rstrip on the ATX title must strip trailing (not leading) space —
        # the title has trailing spaces after "Hi" that must be removed.
        expected = f"\n{self._SEP}\n𝗛𝗜\n{self._SEP}\n"
        assert _convert_headers("# Hi   ") == expected

    def test_h2_trailing_whitespace_stripped(self) -> None:
        # rstrip on ATX title applies to H2 as well.
        assert _convert_headers("## Section   ") == "𝗦𝗲𝗰𝘁𝗶𝗼𝗻"


# ── _strip_links ──────────────────────────────────────────────────────────────


class TestStripLinks:
    def test_inline_link_stripped_to_text(self) -> None:
        assert _strip_links("[Click here](https://example.com)") == "Click here"

    def test_empty_link_removed(self) -> None:
        assert not _strip_links("[](https://example.com)")

    def test_reference_style_link(self) -> None:
        assert _strip_links("[text][ref]") == "text"

    def test_autolink(self) -> None:
        assert _strip_links("<https://example.com>") == "https://example.com"

    def test_preserve_links_flag(self) -> None:
        text = "[Click here](https://example.com)"
        assert _strip_links(text, preserve=True) == text

    def test_link_with_title(self) -> None:
        result = _strip_links('[text](https://example.com "title")')
        assert result == "text"

    def test_no_links_unchanged(self) -> None:
        assert _strip_links("plain text") == "plain text"


# ── _strip_images ─────────────────────────────────────────────────────────────


class TestStripImages:
    def test_image_replaced_by_alt(self) -> None:
        assert _strip_images("![Logo](logo.png)") == "Logo"

    def test_image_with_empty_alt_removed(self) -> None:
        assert not _strip_images("![](logo.png)")

    def test_no_images_unchanged(self) -> None:
        assert _strip_images("plain text") == "plain text"


# ── _convert_bullets ──────────────────────────────────────────────────────────


class TestConvertBullets:
    @pytest.mark.parametrize(
        "marker",
        ["-", "*", "+"],
        ids=["dash", "asterisk", "plus"],
    )
    def test_bullet_markers(self, marker: str) -> None:
        assert _convert_bullets(f"{marker} item") == "• item"

    def test_nested_bullet(self) -> None:
        result = _convert_bullets("  - nested")
        assert "‣" in result

    def test_non_list_line_unchanged(self) -> None:
        assert _convert_bullets("regular line") == "regular line"

    def test_multiline(self) -> None:
        text = "- one\n- two\n- three"
        result = _convert_bullets(text)
        assert result.count("•") == 3

    def test_bullet_after_blank_lines_not_nested(self) -> None:
        text = "some text\n\n\n- first\n  - sub\n- second"
        result = _convert_bullets(text)
        assert result.startswith("some text\n\n\n• first")
        assert "  ‣ sub" in result
        assert result.endswith("• second")


# ── _strip_blockquotes ────────────────────────────────────────────────────────


class TestStripBlockquotes:
    def test_simple_blockquote(self) -> None:
        assert _strip_blockquotes("> hello") == "hello"

    def test_blockquote_with_space(self) -> None:
        assert _strip_blockquotes("> hello") == "hello"

    def test_non_blockquote_unchanged(self) -> None:
        assert _strip_blockquotes("plain text") == "plain text"

    def test_multiline(self) -> None:
        text = "> line one\n> line two"
        result = _strip_blockquotes(text)
        assert ">" not in result


# ── _clean_entities ───────────────────────────────────────────────────────────


class TestCleanEntities:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("a &gt; b", "a > b"),
            ("a &lt; b", "a < b"),
            ("a &amp; b", "a & b"),
            ("a&nbsp;b", "a b"),
            ("&quot;text&quot;", '"text"'),
            ("it&apos;s", "it's"),
        ],
        ids=["gt", "lt", "amp", "nbsp", "quot", "apos"],
    )
    def test_entity(self, text: str, expected: str) -> None:
        assert _clean_entities(text) == expected

    def test_no_entities_unchanged(self) -> None:
        assert _clean_entities("plain text") == "plain text"


# ── _clean_escaped_chars ──────────────────────────────────────────────────────


class TestCleanEscapedChars:
    def test_escaped_asterisk(self) -> None:
        assert _clean_escaped_chars(r"\*not italic\*") == "*not italic*"

    def test_escaped_underscore(self) -> None:
        assert _clean_escaped_chars(r"\_word\_") == "_word_"

    def test_escaped_backtick(self) -> None:
        assert _clean_escaped_chars(r"\`code\`") == "`code`"

    def test_no_escapes_unchanged(self) -> None:
        assert _clean_escaped_chars("plain text") == "plain text"


# ── _normalize_whitespace ─────────────────────────────────────────────────────


class TestNormalizeWhitespace:
    def test_collapses_triple_newlines(self) -> None:
        # 3+ newlines collapse to exactly two.
        assert _normalize_whitespace("a\n\n\nb") == "a\n\nb\n"

    def test_keeps_double_newline(self) -> None:
        assert _normalize_whitespace("a\n\nb") == "a\n\nb\n"

    def test_adds_trailing_newline(self) -> None:
        assert _normalize_whitespace("text") == "text\n"

    def test_strips_leading_whitespace(self) -> None:
        assert _normalize_whitespace("\n\ntext") == "text\n"


# ── convert (integration) ─────────────────────────────────────────────────────


class TestConvert:
    def test_empty_string(self) -> None:
        assert not convert("")

    def test_whitespace_only(self) -> None:
        assert not convert("   \n  ")

    def test_bold(self) -> None:
        result = convert("**hello**")
        assert "**" not in result
        assert result.endswith("\n")

    def test_italic(self) -> None:
        result = convert("*hello*")
        assert "*" not in result

    def test_bold_italic(self) -> None:
        result = convert("***hello***")
        assert "***" not in result

    def test_bold_and_italic_together(self) -> None:
        result = convert("**bold** and *italic*")
        assert "**" not in result
        assert "*" not in result

    def test_header_h1(self) -> None:
        result = convert("# My Header")
        assert "━" in result

    def test_header_h2(self) -> None:
        result = convert("## Sub-section")
        assert "━" not in result
        assert "##" not in result

    def test_link_stripped(self) -> None:
        result = convert("[GitHub](https://github.com)")
        assert "https://github.com" not in result
        assert "GitHub" in result

    def test_link_preserved_with_flag(self) -> None:
        result = convert("[GitHub](https://github.com)", preserve_links=True)
        assert result.strip() == "[GitHub](https://github.com)"

    def test_bullet_list(self) -> None:
        result = convert("- item one\n- item two")
        assert "•" in result
        assert "- " not in result

    def test_code_not_transformed(self) -> None:
        result = convert("use `**bold**` here", monospace_code=False)
        # The **bold** inside code backticks must NOT be unicode-transformed
        assert "**bold**" in result

    def test_fenced_code_preserved(self) -> None:
        md = "```python\nprint('hello')\n```"
        result = convert(md, monospace_code=False)
        assert "print('hello')" in result

    def test_code_monospace_default(self) -> None:
        result = convert("use `hello` here")
        assert "𝚑𝚎𝚕𝚕𝚘" in result

    def test_fenced_code_monospace_default(self) -> None:
        md = "```python\nprint('hello')\n```"
        result = convert(md)
        assert "𝚙𝚛𝚒𝚗𝚝" in result
        assert "```" not in result

    def test_code_monospace_disabled(self) -> None:
        result = convert("use `hello` here", monospace_code=False)
        assert "hello" in result
        assert "𝚑𝚎𝚕𝚕𝚘" not in result

    def test_code_monospace_preserves_markdown_syntax(self) -> None:
        result = convert("use `**bold**` here")
        # ** should remain as-is (not ASCII letters), bold text gets monospaced
        assert "**" in result
        assert "𝚋𝚘𝚕𝚍" in result

    def test_image_alt_text(self) -> None:
        result = convert("![Logo](logo.png)")
        assert "Logo" in result
        assert "logo.png" not in result

    def test_html_span_stripped(self) -> None:
        result = convert('<span class="x">hello</span>')
        assert "<span" not in result
        assert "hello" in result

    def test_blockquote_stripped(self) -> None:
        result = convert("> quoted text")
        assert ">" not in result
        assert "quoted text" in result

    def test_html_entities_decoded(self) -> None:
        result = convert("a &gt; b")
        assert "&gt;" not in result
        assert ">" in result

    def test_windows_line_endings(self) -> None:
        result = convert("**hello**\r\n*world*")
        assert "\r" not in result

    def test_excessive_blank_lines_collapsed(self) -> None:
        result = convert("a\n\n\n\n\nb")
        assert "\n\n\n" not in result

    def test_non_ascii_passthrough(self) -> None:
        result = convert("**café** résumé")
        assert "é" in result
        assert "é" in result

    def test_emoji_passthrough(self) -> None:
        result = convert("**Hello** 🎉")
        assert "🎉" in result

    def test_escaped_asterisk_not_italic(self) -> None:
        result = convert(r"\*not italic\*")
        assert "*not italic*" in result

    def test_underline_italic(self) -> None:
        result = convert("_hello_")
        assert "_hello_" not in result

    def test_snake_case_not_italicized(self) -> None:
        result = convert("some_variable_name")
        assert "some_variable_name" in result

    def test_bold_italic_before_bold(self) -> None:
        # ***text*** should be bold-italic, not bold(*text*)
        result = convert("***key***")
        # Result should contain bold-italic characters, not bold + asterisks
        assert "***" not in result

    def test_setext_h1(self) -> None:
        result = convert("Title\n=====")
        assert "━" in result

    def test_trailing_newline(self) -> None:
        result = convert("hello")
        assert result.endswith("\n")

    def test_reference_style_link(self) -> None:
        result = convert("[text][ref]")
        assert "text" in result
        assert "[ref]" not in result

    def test_autolink(self) -> None:
        result = convert("<https://example.com>")
        assert result.strip() == "https://example.com"

    def test_bullet_list_after_heading(self) -> None:
        result = convert("# Heading\n\n- first\n  - sub\n- second")
        assert "• first" in result
        assert "  ‣ sub" in result
        assert "• second" in result


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
        with pytest.raises(FileNotFoundError, match=str(missing)):
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
