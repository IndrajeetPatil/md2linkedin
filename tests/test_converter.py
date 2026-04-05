"""Tests for md2linkedin._converter — the Markdown conversion pipeline."""

from __future__ import annotations

import os
import tempfile
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
    def test_crlf_to_lf(self):
        assert _normalize_line_endings("a\r\nb") == "a\nb"

    def test_cr_to_lf(self):
        assert _normalize_line_endings("a\rb") == "a\nb"

    def test_lf_unchanged(self):
        assert _normalize_line_endings("a\nb") == "a\nb"

    def test_empty(self):
        assert _normalize_line_endings("") == ""

    def test_mixed(self):
        assert _normalize_line_endings("a\r\nb\rc\nd") == "a\nb\nc\nd"


# ── _protect_code / _restore_code ─────────────────────────────────────────────


class TestProtectAndRestoreCode:
    def test_inline_code_protected(self):
        text, placeholders = _protect_code("say `hello world` here")
        assert "`hello world`" not in text
        assert len(placeholders) == 1

    def test_inline_code_content_preserved_on_restore(self):
        text, placeholders = _protect_code("say `hello world` here")
        restored = _restore_code(text, placeholders)
        # Backticks are stripped on restore
        assert "hello world" in restored
        assert "`" not in restored

    def test_fenced_block_protected(self):
        text, placeholders = _protect_code("```python\nprint('hi')\n```")
        assert "print" not in text
        assert len(placeholders) == 1

    def test_fenced_block_restored_verbatim(self):
        original = "```python\nprint('hi')\n```"
        text, placeholders = _protect_code(original)
        restored = _restore_code(text, placeholders)
        assert restored == original

    def test_tilde_fenced_block(self):
        original = "~~~\nsome code\n~~~"
        text, placeholders = _protect_code(original)
        restored = _restore_code(text, placeholders)
        assert restored == original

    def test_code_not_transformed_by_bold(self):
        text, placeholders = _protect_code("use `**bold**` code")
        # Bold markers inside code are hidden from the converter
        assert "**bold**" not in text
        restored = _restore_code(text, placeholders)
        assert "**bold**" in restored

    def test_empty_no_placeholders(self):
        text, placeholders = _protect_code("no code here")
        assert text == "no code here"
        assert placeholders == {}


# ── _strip_html_spans ─────────────────────────────────────────────────────────


class TestStripHtmlSpans:
    def test_simple_span(self):
        assert _strip_html_spans('<span class="x">hello</span>') == "hello"

    def test_nested_spans(self):
        result = _strip_html_spans('<span><span class="inner">text</span></span>')
        assert result == "text"

    def test_no_spans_unchanged(self):
        assert _strip_html_spans("plain text") == "plain text"

    def test_span_with_style(self):
        result = _strip_html_spans('<span style="font-weight:bold">Bold</span>')
        assert result == "Bold"

    def test_multiline_span(self):
        result = _strip_html_spans("<span>\nhello\n</span>")
        assert result == "\nhello\n"


# ── _convert_bold_italic ──────────────────────────────────────────────────────


class TestConvertBoldItalic:
    def test_triple_asterisk(self):
        result = _convert_bold_italic("***hello***")
        assert "***" not in result
        assert "hello" not in result  # letters replaced

    def test_triple_underscore(self):
        result = _convert_bold_italic("___hello___")
        assert "___" not in result

    def test_no_change_for_bold_only(self):
        text = "**hello**"
        assert _convert_bold_italic(text) == text

    def test_no_change_for_italic_only(self):
        text = "*hello*"
        assert _convert_bold_italic(text) == text

    def test_passthrough_non_ascii(self):
        result = _convert_bold_italic("***café***")
        assert "é" in result


# ── _convert_bold ─────────────────────────────────────────────────────────────


class TestConvertBold:
    def test_double_asterisk(self):
        result = _convert_bold("**hello**")
        assert "**" not in result

    def test_double_underscore(self):
        result = _convert_bold("__hello__")
        assert "__" not in result

    def test_preserves_surrounding_text(self):
        result = _convert_bold("before **bold** after")
        assert result.startswith("before ")
        assert result.endswith(" after")

    def test_multiple_bold_spans(self):
        result = _convert_bold("**a** and **b**")
        assert "**" not in result

    def test_no_change_for_italic(self):
        text = "*hello*"
        assert _convert_bold(text) == text


# ── _convert_italic ───────────────────────────────────────────────────────────


class TestConvertItalic:
    def test_single_asterisk(self):
        result = _convert_italic("*hello*")
        assert "*" not in result

    def test_single_underscore(self):
        result = _convert_italic("_hello_")
        assert "_hello_" not in result

    def test_no_match_inside_word_underscore(self):
        # snake_case should not be affected
        text = "snake_case_var"
        assert _convert_italic(text) == text

    def test_preserves_surrounding_text(self):
        result = _convert_italic("before *italic* after")
        assert result.startswith("before ")
        assert result.endswith(" after")

    def test_no_change_for_bold_markers(self):
        # Bold markers (**) should not be consumed by italic pattern
        text = "**bold**"
        assert _convert_italic(text) == text


# ── _convert_headers ──────────────────────────────────────────────────────────


class TestConvertHeaders:
    def test_h1_has_separator(self):
        result = _convert_headers("# Hello")
        assert "━" in result

    def test_h1_uppercase(self):
        result = _convert_headers("# Hello")
        # The title is uppercased and bolded
        assert "HELLO" not in result  # replaced with Unicode bold

    def test_h2_no_separator(self):
        result = _convert_headers("## Section")
        assert "━" not in result
        assert "##" not in result

    def test_h3_to_h6_no_separator(self):
        for level in range(3, 7):
            result = _convert_headers(f"{'#' * level} Heading")
            assert "━" not in result
            assert "#" not in result

    def test_setext_h1(self):
        result = _convert_headers("Title\n=====")
        assert "━" in result

    def test_setext_h2(self):
        result = _convert_headers("Subtitle\n--------")
        assert "━" not in result
        assert "---" not in result

    def test_standalone_horizontal_rule_removed(self):
        result = _convert_headers("---")
        assert result.strip() == ""

    def test_non_header_unchanged(self):
        text = "Just a line"
        assert _convert_headers(text) == text


# ── _strip_links ──────────────────────────────────────────────────────────────


class TestStripLinks:
    def test_inline_link_stripped_to_text(self):
        assert _strip_links("[Click here](https://example.com)") == "Click here"

    def test_empty_link_removed(self):
        assert _strip_links("[](https://example.com)") == ""

    def test_reference_style_link(self):
        assert _strip_links("[text][ref]") == "text"

    def test_autolink(self):
        assert _strip_links("<https://example.com>") == "https://example.com"

    def test_preserve_links_flag(self):
        text = "[Click here](https://example.com)"
        assert _strip_links(text, preserve=True) == text

    def test_link_with_title(self):
        result = _strip_links('[text](https://example.com "title")')
        assert result == "text"

    def test_no_links_unchanged(self):
        assert _strip_links("plain text") == "plain text"


# ── _strip_images ─────────────────────────────────────────────────────────────


class TestStripImages:
    def test_image_replaced_by_alt(self):
        assert _strip_images("![Logo](logo.png)") == "Logo"

    def test_image_with_empty_alt_removed(self):
        assert _strip_images("![](logo.png)") == ""

    def test_no_images_unchanged(self):
        assert _strip_images("plain text") == "plain text"


# ── _convert_bullets ──────────────────────────────────────────────────────────


class TestConvertBullets:
    def test_dash_bullet(self):
        assert _convert_bullets("- item") == "• item"

    def test_asterisk_bullet(self):
        assert _convert_bullets("* item") == "• item"

    def test_plus_bullet(self):
        assert _convert_bullets("+ item") == "• item"

    def test_nested_bullet(self):
        result = _convert_bullets("  - nested")
        assert "‣" in result

    def test_non_list_line_unchanged(self):
        assert _convert_bullets("regular line") == "regular line"

    def test_multiline(self):
        text = "- one\n- two\n- three"
        result = _convert_bullets(text)
        assert result.count("•") == 3


# ── _strip_blockquotes ────────────────────────────────────────────────────────


class TestStripBlockquotes:
    def test_simple_blockquote(self):
        assert _strip_blockquotes("> hello") == "hello"

    def test_blockquote_with_space(self):
        assert _strip_blockquotes("> hello") == "hello"

    def test_non_blockquote_unchanged(self):
        assert _strip_blockquotes("plain text") == "plain text"

    def test_multiline(self):
        text = "> line one\n> line two"
        result = _strip_blockquotes(text)
        assert ">" not in result


# ── _clean_entities ───────────────────────────────────────────────────────────


class TestCleanEntities:
    def test_gt(self):
        assert _clean_entities("a &gt; b") == "a > b"

    def test_lt(self):
        assert _clean_entities("a &lt; b") == "a < b"

    def test_amp(self):
        assert _clean_entities("a &amp; b") == "a & b"

    def test_nbsp(self):
        assert _clean_entities("a&nbsp;b") == "a b"

    def test_quot(self):
        assert _clean_entities("&quot;text&quot;") == '"text"'

    def test_apos(self):
        assert _clean_entities("it&apos;s") == "it's"

    def test_no_entities_unchanged(self):
        assert _clean_entities("plain text") == "plain text"


# ── _clean_escaped_chars ──────────────────────────────────────────────────────


class TestCleanEscapedChars:
    def test_escaped_asterisk(self):
        assert _clean_escaped_chars(r"\*not italic\*") == "*not italic*"

    def test_escaped_underscore(self):
        assert _clean_escaped_chars(r"\_word\_") == "_word_"

    def test_escaped_backtick(self):
        assert _clean_escaped_chars(r"\`code\`") == "`code`"

    def test_no_escapes_unchanged(self):
        assert _clean_escaped_chars("plain text") == "plain text"


# ── _normalize_whitespace ─────────────────────────────────────────────────────


class TestNormalizeWhitespace:
    def test_collapses_triple_newlines(self):
        result = _normalize_whitespace("a\n\n\nb")
        assert "\n\n\n" not in result

    def test_keeps_double_newline(self):
        result = _normalize_whitespace("a\n\nb")
        assert "\n\n" in result

    def test_adds_trailing_newline(self):
        result = _normalize_whitespace("text")
        assert result.endswith("\n")

    def test_strips_leading_whitespace(self):
        result = _normalize_whitespace("\n\ntext")
        assert not result.startswith("\n")


# ── convert (integration) ─────────────────────────────────────────────────────


class TestConvert:
    def test_empty_string(self):
        assert convert("") == ""

    def test_whitespace_only(self):
        assert convert("   \n  ") == ""

    def test_bold(self):
        result = convert("**hello**")
        assert "**" not in result
        assert result.endswith("\n")

    def test_italic(self):
        result = convert("*hello*")
        assert "*" not in result

    def test_bold_italic(self):
        result = convert("***hello***")
        assert "***" not in result

    def test_bold_and_italic_together(self):
        result = convert("**bold** and *italic*")
        assert "**" not in result
        assert "*" not in result

    def test_header_h1(self):
        result = convert("# My Header")
        assert "━" in result

    def test_header_h2(self):
        result = convert("## Sub-section")
        assert "━" not in result
        assert "##" not in result

    def test_link_stripped(self):
        result = convert("[GitHub](https://github.com)")
        assert "https://github.com" not in result
        assert "GitHub" in result

    def test_link_preserved_with_flag(self):
        result = convert("[GitHub](https://github.com)", preserve_links=True)
        assert "https://github.com" in result

    def test_bullet_list(self):
        result = convert("- item one\n- item two")
        assert "•" in result
        assert "- " not in result

    def test_code_not_transformed(self):
        result = convert("use `**bold**` here")
        # The **bold** inside code backticks must NOT be unicode-transformed
        assert "**bold**" in result

    def test_fenced_code_preserved(self):
        md = "```python\nprint('hello')\n```"
        result = convert(md)
        assert "print('hello')" in result

    def test_image_alt_text(self):
        result = convert("![Logo](logo.png)")
        assert "Logo" in result
        assert "logo.png" not in result

    def test_html_span_stripped(self):
        result = convert('<span class="x">hello</span>')
        assert "<span" not in result
        assert "hello" in result

    def test_blockquote_stripped(self):
        result = convert("> quoted text")
        assert ">" not in result
        assert "quoted text" in result

    def test_html_entities_decoded(self):
        result = convert("a &gt; b")
        assert "&gt;" not in result
        assert ">" in result

    def test_windows_line_endings(self):
        result = convert("**hello**\r\n*world*")
        assert "\r" not in result

    def test_excessive_blank_lines_collapsed(self):
        result = convert("a\n\n\n\n\nb")
        assert "\n\n\n" not in result

    def test_non_ascii_passthrough(self):
        result = convert("**café** résumé")
        assert "é" in result
        assert "é" in result

    def test_emoji_passthrough(self):
        result = convert("**Hello** 🎉")
        assert "🎉" in result

    def test_escaped_asterisk_not_italic(self):
        result = convert(r"\*not italic\*")
        assert "*not italic*" in result

    def test_underline_italic(self):
        result = convert("_hello_")
        assert "_hello_" not in result

    def test_snake_case_not_italicized(self):
        result = convert("some_variable_name")
        assert "some_variable_name" in result

    def test_bold_italic_before_bold(self):
        # ***text*** should be bold-italic, not bold(*text*)
        result = convert("***key***")
        # Result should contain bold-italic characters, not bold + asterisks
        assert "***" not in result

    def test_setext_h1(self):
        result = convert("Title\n=====")
        assert "━" in result

    def test_trailing_newline(self):
        result = convert("hello")
        assert result.endswith("\n")

    def test_reference_style_link(self):
        result = convert("[text][ref]")
        assert "text" in result
        assert "[ref]" not in result

    def test_autolink(self):
        result = convert("<https://example.com>")
        assert "<" not in result
        assert "https://example.com" in result


# ── convert_file ──────────────────────────────────────────────────────────────


class TestConvertFile:
    def test_basic_conversion(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("**bold** text", encoding="utf-8")
        out = convert_file(src)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "**" not in content

    def test_default_output_path(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        out = convert_file(src)
        assert out.suffix == ".txt"
        assert "linkedin" in out.name

    def test_explicit_output_path(self, tmp_path):
        src = tmp_path / "test.md"
        dst = tmp_path / "output.txt"
        src.write_text("hello", encoding="utf-8")
        out = convert_file(src, dst)
        assert out == dst
        assert dst.exists()

    def test_preserve_links_forwarded(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("[GitHub](https://github.com)", encoding="utf-8")
        out = convert_file(src, preserve_links=True)
        assert "https://github.com" in out.read_text(encoding="utf-8")

    def test_string_path_accepted(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        out = convert_file(str(src))
        assert out.exists()

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            convert_file(tmp_path / "nonexistent.md")

    def test_output_is_utf8(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("**café** résumé 🎉", encoding="utf-8")
        out = convert_file(src)
        content = out.read_text(encoding="utf-8")
        assert "é" in content
        assert "🎉" in content

    def test_returns_path_object(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        result = convert_file(src)
        assert isinstance(result, Path)
