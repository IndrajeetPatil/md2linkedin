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
        assert "hello world" in restored
        assert "`" not in restored

    def test_fenced_block_protected(self) -> None:
        text, placeholders = _protect_code("```python\nprint('hi')\n```")
        assert "print" not in text
        assert len(placeholders) == 1

    def test_fenced_block_restored_verbatim(self) -> None:
        original = "```python\nprint('hi')\n```"
        text, placeholders = _protect_code(original)
        restored = _restore_code(text, placeholders, monospace=False)
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
        assert "**bold**" in restored

    def test_inline_code_monospace(self) -> None:
        text, placeholders = _protect_code("say `hello` here")
        restored = _restore_code(text, placeholders, monospace=True)
        assert "𝚑𝚎𝚕𝚕𝚘" in restored
        assert "`" not in restored

    def test_fenced_block_monospace(self) -> None:
        text, placeholders = _protect_code("```python\nprint('hi')\n```")
        restored = _restore_code(text, placeholders, monospace=True)
        assert "𝚙𝚛𝚒𝚗𝚝" in restored
        assert "```" not in restored
        assert "python" not in restored

    def test_tilde_fenced_block_monospace(self) -> None:
        text, placeholders = _protect_code("~~~\nsome code\n~~~")
        restored = _restore_code(text, placeholders, monospace=True)
        assert "𝚜𝚘𝚖𝚎 𝚌𝚘𝚍𝚎" in restored
        assert "~~~" not in restored

    def test_fenced_block_monospace_empty_body(self) -> None:
        text, placeholders = _protect_code("``````")
        restored = _restore_code(text, placeholders, monospace=True)
        assert "```" not in restored
        assert restored == ""

    def test_fenced_block_monospace_preserves_syntax_chars(self) -> None:
        text, placeholders = _protect_code("```\n**not bold**\n```")
        restored = _restore_code(text, placeholders, monospace=True)
        # ** should pass through unchanged (not ASCII letters/digits)
        assert "**" in restored

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


# ── _convert_bold_italic ──────────────────────────────────────────────────────


class TestConvertBoldItalic:
    def test_triple_asterisk(self) -> None:
        result = _convert_bold_italic("***hello***")
        assert "***" not in result
        assert "hello" not in result  # letters replaced

    def test_triple_underscore(self) -> None:
        result = _convert_bold_italic("___hello___")
        assert "___" not in result

    def test_no_change_for_bold_only(self) -> None:
        text = "**hello**"
        assert _convert_bold_italic(text) == text

    def test_no_change_for_italic_only(self) -> None:
        text = "*hello*"
        assert _convert_bold_italic(text) == text

    def test_passthrough_non_ascii(self) -> None:
        result = _convert_bold_italic("***café***")
        assert "é" in result


# ── _convert_bold ─────────────────────────────────────────────────────────────


class TestConvertBold:
    def test_double_asterisk(self) -> None:
        result = _convert_bold("**hello**")
        assert "**" not in result

    def test_double_underscore(self) -> None:
        result = _convert_bold("__hello__")
        assert "__" not in result

    def test_preserves_surrounding_text(self) -> None:
        result = _convert_bold("before **bold** after")
        assert result.startswith("before ")
        assert result.endswith(" after")

    def test_multiple_bold_spans(self) -> None:
        result = _convert_bold("**a** and **b**")
        assert "**" not in result

    def test_no_change_for_italic(self) -> None:
        text = "*hello*"
        assert _convert_bold(text) == text


# ── _convert_italic ───────────────────────────────────────────────────────────


class TestConvertItalic:
    def test_single_asterisk(self) -> None:
        result = _convert_italic("*hello*")
        assert "*" not in result

    def test_single_underscore(self) -> None:
        result = _convert_italic("_hello_")
        assert "_hello_" not in result

    def test_no_match_inside_word_underscore(self) -> None:
        # snake_case should not be affected
        text = "snake_case_var"
        assert _convert_italic(text) == text

    def test_preserves_surrounding_text(self) -> None:
        result = _convert_italic("before *italic* after")
        assert result.startswith("before ")
        assert result.endswith(" after")

    def test_no_change_for_bold_markers(self) -> None:
        # Bold markers (**) should not be consumed by italic pattern
        text = "**bold**"
        assert _convert_italic(text) == text


# ── _convert_headers ──────────────────────────────────────────────────────────


class TestConvertHeaders:
    def test_h1_has_separator(self) -> None:
        result = _convert_headers("# Hello")
        assert "━" in result

    def test_h1_uppercase(self) -> None:
        result = _convert_headers("# Hello")
        # The title is uppercased and bolded
        assert "HELLO" not in result  # replaced with Unicode bold

    def test_h2_no_separator(self) -> None:
        result = _convert_headers("## Section")
        assert "━" not in result
        assert "##" not in result

    @pytest.mark.parametrize("level", [3, 4, 5, 6])
    def test_h3_to_h6_no_separator(self, level: int) -> None:
        result = _convert_headers(f"{'#' * level} Heading")
        assert "━" not in result
        assert "#" not in result

    def test_setext_h1(self) -> None:
        result = _convert_headers("Title\n=====")
        assert "━" in result

    def test_setext_h2(self) -> None:
        result = _convert_headers("Subtitle\n--------")
        assert "━" not in result
        assert "---" not in result

    def test_standalone_horizontal_rule_removed(self) -> None:
        result = _convert_headers("---")
        assert not result.strip()

    def test_non_header_unchanged(self) -> None:
        text = "Just a line"
        assert _convert_headers(text) == text


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
        assert _strip_images("![](logo.png)") == ""

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
        result = _normalize_whitespace("a\n\n\nb")
        assert "\n\n\n" not in result

    def test_keeps_double_newline(self) -> None:
        result = _normalize_whitespace("a\n\nb")
        assert "\n\n" in result

    def test_adds_trailing_newline(self) -> None:
        result = _normalize_whitespace("text")
        assert result.endswith("\n")

    def test_strips_leading_whitespace(self) -> None:
        result = _normalize_whitespace("\n\ntext")
        assert not result.startswith("\n")


# ── convert (integration) ─────────────────────────────────────────────────────


class TestConvert:
    def test_empty_string(self) -> None:
        assert convert("") == ""

    def test_whitespace_only(self) -> None:
        assert convert("   \n  ") == ""

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
        assert "https://github.com" in result

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
        assert "<" not in result
        assert "https://example.com" in result


# ── convert_file ──────────────────────────────────────────────────────────────


class TestConvertFile:
    def test_basic_conversion(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        src.write_text("**bold** text", encoding="utf-8")
        out = convert_file(src)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "**" not in content

    def test_default_output_path(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        out = convert_file(src)
        assert out.suffix == ".txt"
        assert "linkedin" in out.name

    def test_explicit_output_path(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        dst = tmp_path / "output.txt"
        src.write_text("hello", encoding="utf-8")
        out = convert_file(src, dst)
        assert out == dst
        assert dst.exists()

    def test_preserve_links_forwarded(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        src.write_text("[GitHub](https://github.com)", encoding="utf-8")
        out = convert_file(src, preserve_links=True)
        assert "https://github.com" in out.read_text(encoding="utf-8")

    def test_string_path_accepted(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        out = convert_file(str(src))
        assert out.exists()

    def test_file_not_found_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            convert_file(tmp_path / "nonexistent.md")

    def test_output_is_utf8(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        src.write_text("**café** résumé 🎉", encoding="utf-8")
        out = convert_file(src)
        content = out.read_text(encoding="utf-8")
        assert "é" in content
        assert "🎉" in content

    def test_monospace_code_forwarded(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        src.write_text("use `hello` here", encoding="utf-8")
        out = convert_file(src, monospace_code=False)
        content = out.read_text(encoding="utf-8")
        assert "hello" in content
        assert "𝚑𝚎𝚕𝚕𝚘" not in content

    def test_monospace_code_default(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        src.write_text("use `hello` here", encoding="utf-8")
        out = convert_file(src)
        content = out.read_text(encoding="utf-8")
        assert "𝚑𝚎𝚕𝚕𝚘" in content

    def test_returns_path_object(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        result = convert_file(src)
        assert isinstance(result, Path)
