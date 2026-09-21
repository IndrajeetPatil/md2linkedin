"""Public conversion behavior for Markdown and file inputs."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from md2linkedin import to_monospace, to_sans_bold
from md2linkedin._converter import convert, convert_file


@pytest.mark.parametrize(
    ("markdown", "expected"),
    [
        ("**bold**", "𝗯𝗼𝗹𝗱\n"),
        ("*italic*", "𝘪𝘵𝘢𝘭𝘪𝘤\n"),
        ("***both***", "𝙗𝙤𝙩𝙝\n"),
        ("**bold and *italic* inside**", "𝗯𝗼𝗹𝗱 𝗮𝗻𝗱 𝙞𝙩𝙖𝙡𝙞𝙘 𝗶𝗻𝘀𝗶𝗱𝗲\n"),
        ("# Hi", f"{'━' * 40}\n𝗛𝗜\n{'━' * 40}\n"),
        ("Title\n=====", f"{'━' * 40}\n𝗧𝗜𝗧𝗟𝗘\n{'━' * 40}\n"),
        ("## Sub", "𝗦𝘂𝗯\n"),
        ("- a\n  - b\n    - c", "• a\n  ‣ b\n    ◦ c\n"),
        ("1. first\n2. second", "1. first\n2. second\n"),
        ("> outer\n>> inner", "outer\ninner\n"),
        ("[name](https://example.com)", "name\n"),
        ("![logo](logo.png)", "logo\n"),
        ("[name][d]\n\n[d]: https://example.com", "name\n"),
        ("use `hello`", f"use {to_monospace('hello')}\n"),
        ("    print(1)", f"{to_monospace('print(1)')}\n"),
        ("```python\nprint(1)\n```", f"{to_monospace('print(1)')}\n"),
        ("<span>hello</span>", "hello\n"),
        ("a <br> b", "a <br> b\n"),
        ("<div>\nhello\n</div>", "<div>\nhello\n</div>\n"),
        ("<div>\n**bold**\n</div>", "<div>\n**bold**\n</div>\n"),
        ("- ", "•\n"),
        ("~~old~~", "old\n"),
        ("a &gt; b", "a > b\n"),
        (r"\*literal\*", "*literal*\n"),
        ("some_variable_name", "some_variable_name\n"),
        ("a\n\nb", "a\n\nb\n"),
        ("first  \nsecond", "first  \nsecond\n"),
        ("first\\\nsecond", "first\nsecond\n"),
        ("first  \n\nsecond", "first  \n\nsecond\n"),
        ("**first\nsecond**  \n\nthird", "𝗳𝗶𝗿𝘀𝘁\n𝘀𝗲𝗰𝗼𝗻𝗱  \n\nthird\n"),
        ("a\rb", "a\nb\n"),
        ("a\x00b", "ab\n"),
        ("a\n\n* * *\n\nb", "a\n\nb\n"),
        ("| a | b |\n| --- | --- |\n| c | d |", "a: c · b: d\n"),
        ("| a | b |\n| --- | --- |", "a · b\n"),
        (
            "| a | b |\n| --- | --- |\n| c | d |\n| e | f |",
            "a: c · b: d\na: e · b: f\n",
        ),
        ("| a | b |\n| --- | --- |\n| c \\| d | e |", "a: c | d · b: e\n"),
    ],
)
def test_convert_markdown(markdown: str, expected: str) -> None:
    assert convert(markdown) == expected


@pytest.mark.parametrize("markdown", ["", "  \n  "])
def test_empty_input(markdown: str) -> None:
    assert not convert(markdown)


def test_plain_code_option_keeps_fences_and_literal_inline_content() -> None:
    assert convert("**`raw`**", monospace_code=False) == "raw\n"
    assert convert("```python\n**raw**\n```", monospace_code=False) == (
        "```python\n**raw**\n```\n"
    )
    assert convert("    print(1)", monospace_code=False) == "print(1)\n"
    assert convert("```python\na\n````", monospace_code=False) == (
        "```python\na\n````\n"
    )
    assert convert("```python\na\n", monospace_code=False) == ("```python\na\n")


def test_excessive_blank_lines_inside_code_are_collapsed_for_linkedin() -> None:
    assert convert("```\na\n\n\n\nb\n```") == (
        f"{to_monospace('a')}\n\n{to_monospace('b')}\n"
    )


def test_links_option_preserves_link_syntax() -> None:
    assert convert("[name](https://example.com)", preserve_links=True) == (
        "[name](https://example.com)\n"
    )
    assert convert("<https://example.com>", preserve_links=True) == (
        "<https://example.com>\n"
    )
    assert convert("[name][d]\n\n[d]: https://example.com", preserve_links=True) == (
        "[name][d]\n"
    )
    assert convert("[name][]\n\n[name]: /page", preserve_links=True) == ("[name][]\n")
    assert convert("[name]\n\n[name]: /page", preserve_links=True) == ("[name]\n")
    assert convert("[name](url 'title')", preserve_links=True) == (
        "[name](url 'title')\n"
    )


def test_headings_do_not_style_code_spans() -> None:
    assert convert("# Why is `Any` bad?").splitlines()[1] == (
        f"{to_sans_bold('WHY IS ')}{to_monospace('Any')}{to_sans_bold(' BAD?')}"
    )
    assert convert("# Why is `Any` bad?", monospace_code=False).splitlines()[1] == (
        f"{to_sans_bold('WHY IS ')}Any{to_sans_bold(' BAD?')}"
    )


def test_list_marker_changes_keep_sibling_depth() -> None:
    assert convert("- outer\n    - bullet\n    2. ordered") == (
        "• outer\n  ‣ bullet\n  2. ordered\n"
    )
    assert convert("- outer\n    1. first\n   2) prose\n     - child") == (
        "• outer\n  1. first\n  2) prose\n  ‣ child\n"
    )


def test_thematic_break_inside_list_item_does_not_emit_marker() -> None:
    assert convert("- a\n    * * *\n    - b") == "• a\n  ‣ b\n"


def test_mixed_marker_widths_follow_item_content_columns() -> None:
    assert convert("- outer\n\n  10. middle\n       - child") == (
        "• outer\n\n  10. middle\n    ◦ child\n"
    )


def test_loose_nested_lists_preserve_blank_lines() -> None:
    assert convert("- role\n\n  - task\n\n    - project\n\n  - next\n\n- other") == (
        "• role\n\n  ‣ task\n\n    ◦ project\n\n  ‣ next\n\n• other\n"
    )


def test_terminal_hard_break_ignores_newline_from_html_entity() -> None:
    assert convert("a &#10; b  \n\nnext").endswith("b  \n\nnext\n")


def test_unicode_and_line_endings() -> None:
    assert convert("**café** 🎉\r\nnext") == "𝗰𝗮𝗳é 🎉\nnext\n"


def test_code_inside_emphasis_stays_code() -> None:
    assert convert("**`code`**") == f"{to_monospace('code')}\n"


# File conversion exercises the same public API and explicit UTF-8 I/O.
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
