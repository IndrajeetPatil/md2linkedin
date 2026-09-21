"""Tests for md2linkedin._converter — the Markdown conversion pipeline."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from md2linkedin._converter import convert, convert_file


class TestConvert:
    def test_br_hard_break(self) -> None:
        result = convert("Line 1  \nLine 2")
        assert "Line 1\nLine 2" in result

    def test_bold_italic_unicode(self) -> None:
        assert "***bold italic***" not in convert("***bold italic***")
        assert "𝙗𝙤𝙡𝙙" in convert("***bold italic***")

    def test_heading_h1(self) -> None:
        assert "━" in convert("# Hello")
        assert "𝗛𝗘𝗟𝗟𝗢" in convert("# Hello")

    def test_nested_list(self) -> None:
        res = convert("- a\n  - b")
        assert "• a" in res
        assert "‣ b" in res

    def test_ordered_list(self) -> None:
        res = convert("1. a\n2. b")
        assert "1. a" in res
        assert "2. b" in res

    def test_images(self) -> None:
        res = convert("![alt text](img.png)")
        assert "alt text" in res

    def test_preserve_autolink(self) -> None:
        res = convert("<https://example.com>", preserve_links=True)
        assert "<https://example.com>" in res

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

    def test_spaced_asterisk_rule_is_dropped(self) -> None:
        # End to end, because the rule has to survive the list step, which
        # reads it as a boundary, and go before the emphasis steps, which
        # would pair up its first two asterisks and leave the third behind.
        assert convert("before\n\n* * *\n\nafter") == "before\n\nafter\n"

    def test_spaced_underscore_rule_is_dropped(self) -> None:
        assert convert("before\n\n_ _ _\n\nafter") == "before\n\nafter\n"

    def test_lone_spaced_rule_converts_to_nothing(self) -> None:
        assert convert("* * *") == "\n"
        assert convert("_ _ _") == "\n"

    def test_emphasis_after_a_rule_still_converts(self) -> None:
        # Dropping the rule must not disturb the emphasis around it.
        assert convert("* * *\n\n**bold**") == "𝗯𝗼𝗹𝗱\n"

    def test_indented_fenced_block_keeps_the_list_open(self) -> None:
        # Indented, the block is content of the item above rather than a block
        # of its own, so the list continues and ``c`` stays ``b``'s sibling.
        result = convert("- a\n    - b\n    ```\n    code\n    ```\n    - c")
        assert "  ‣ c" in result

    def test_inline_code_keeps_the_list_open(self) -> None:
        # An inline span leaves the same kind of placeholder as a fenced block
        # but is ordinary prose, so it must not close the list.
        result = convert("- a\n    - b\n`code` continues\n    - c")
        assert "  ‣ c" in result

    def test_ordered_list_after_a_fenced_block_opens_a_level(self) -> None:
        # No paragraph above the marker, so its number does not matter.
        result = convert("```\ncode\n```\n2. parent\n    - child")
        assert "2. parent" in result
        assert "  ‣ child" in result

    def test_non_one_ordered_marker_after_inline_code_is_prose(self) -> None:
        # Here the placeholder sits inside a paragraph, which the marker may
        # not interrupt, so it opens no level for ``child``.
        result = convert("- outer\n  `code` paragraph\n  2. prose\n    - child")
        assert "  ‣ child" in result

    def test_ordered_list_after_a_heading_opens_a_level(self) -> None:
        # Same ordering: with the heading already styled, ``2.`` would look
        # like a marker interrupting a paragraph and would open no level.
        result = convert("## Heading\n2. parent\n    - child")
        assert "2. parent" in result
        assert "  ‣ child" in result

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
        result = convert("[text][ref]\n\n[ref]: https://example.com")
        assert "text" in result
        assert "[ref]" not in result

    def test_autolink(self) -> None:
        result = convert("<https://example.com>")
        assert result.strip() == "https://example.com"

    def test_third_level_bullet_stays_nested(self) -> None:
        result = convert("- Role\n  - Applications\n    - AI Launchpad\n")
        assert result == "• Role\n  ‣ Applications\n    ◦ AI Launchpad\n"

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
