"""Tests for md2linkedin._unicode — Unicode character mapping functions."""

from __future__ import annotations

import string
from typing import TYPE_CHECKING, Any, Literal, cast

import pytest

from md2linkedin._unicode import (
    _build_table,
    apply_style,
    to_monospace,
    to_sans_bold,
    to_sans_bold_italic,
    to_sans_italic,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# ── _build_table ──────────────────────────────────────────────────────────────


class TestBuildTable:
    """Direct tests for the table builder.

    The public mapping functions only exercise it indirectly, via tables built
    once at import, so an error in the offset arithmetic could otherwise hide
    behind whichever styles happen to be asserted elsewhere.
    """

    def test_letters_map_to_consecutive_codepoints(self) -> None:
        table = _build_table(0x100, 0x200)
        assert [table[ord(c)] for c in "ABC"] == [0x100, 0x101, 0x102]
        assert [table[ord(c)] for c in "abc"] == [0x200, 0x201, 0x202]
        assert table[ord("Z")] == 0x100 + 25
        assert table[ord("z")] == 0x200 + 25

    def test_digits_included_when_base_given(self) -> None:
        table = _build_table(0x100, 0x200, 0x300)
        assert [table[ord(d)] for d in "09"] == [0x300, 0x309]
        assert len(table) == len(string.ascii_letters) + len(string.digits)

    def test_digits_omitted_when_base_is_none(self) -> None:
        table = _build_table(0x100, 0x200)
        assert not any(ord(d) in table for d in string.digits)
        assert len(table) == len(string.ascii_letters)


# ── to_sans_bold ───────────────────────────────────────────────────────────────


class TestToSansBold:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("ABCXYZ", "𝗔𝗕𝗖𝗫𝗬𝗭", id="uppercase"),
            pytest.param("abcxyz", "𝗮𝗯𝗰𝘅𝘆𝘇", id="lowercase"),
            pytest.param(string.digits, "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵", id="digits"),
            pytest.param("café", "𝗰𝗮𝗳é", id="non-ascii"),
            pytest.param("hi 🎉", "𝗵𝗶 🎉", id="emoji"),
            pytest.param("Hello, World!", "𝗛𝗲𝗹𝗹𝗼, 𝗪𝗼𝗿𝗹𝗱!", id="punctuation"),
            pytest.param("a b", "𝗮 𝗯", id="spaces"),
            pytest.param("", "", id="empty"),
            pytest.param("Hello World 123", "𝗛𝗲𝗹𝗹𝗼 𝗪𝗼𝗿𝗹𝗱 𝟭𝟮𝟯", id="sentence"),
        ],
    )
    def test_converts(self, text: str, expected: str) -> None:
        assert to_sans_bold(text) == expected


# ── to_sans_italic ─────────────────────────────────────────────────────────────


class TestToSansItalic:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("ABCXYZ", "𝘈𝘉𝘊𝘟𝘠𝘡", id="uppercase"),
            pytest.param("abcxyz", "𝘢𝘣𝘤𝘹𝘺𝘻", id="lowercase"),
            # No italic digits in this Unicode block
            pytest.param("123", "123", id="digits-unchanged"),
            pytest.param("café", "𝘤𝘢𝘧é", id="non-ascii"),
            pytest.param("go 🚀", "𝘨𝘰 🚀", id="emoji"),
            pytest.param("Hello!", "𝘏𝘦𝘭𝘭𝘰!", id="punctuation"),
            pytest.param("", "", id="empty"),
        ],
    )
    def test_converts(self, text: str, expected: str) -> None:
        assert to_sans_italic(text) == expected


# ── to_sans_bold_italic ────────────────────────────────────────────────────────


class TestToSansBoldItalic:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("ABCXYZ", "𝘼𝘽𝘾𝙓𝙔𝙕", id="uppercase"),
            pytest.param("abcxyz", "𝙖𝙗𝙘𝙭𝙮𝙯", id="lowercase"),
            pytest.param("123", "123", id="digits-unchanged"),
            pytest.param("café", "𝙘𝙖𝙛é", id="non-ascii"),
            pytest.param("", "", id="empty"),
            pytest.param("Hello World!", "𝙃𝙚𝙡𝙡𝙤 𝙒𝙤𝙧𝙡𝙙!", id="mixed"),
        ],
    )
    def test_converts(self, text: str, expected: str) -> None:
        assert to_sans_bold_italic(text) == expected


# ── to_monospace ──────────────────────────────────────────────────────────────


class TestToMonospace:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("ABCXYZ", "𝙰𝙱𝙲𝚇𝚈𝚉", id="uppercase"),
            pytest.param("abcxyz", "𝚊𝚋𝚌𝚡𝚢𝚣", id="lowercase"),
            pytest.param(string.digits, "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿", id="digits"),
            pytest.param("café", "𝚌𝚊𝚏é", id="non-ascii"),
            pytest.param("hi 🎉", "𝚑𝚒 🎉", id="emoji"),
            pytest.param("Hello, World!", "𝙷𝚎𝚕𝚕𝚘, 𝚆𝚘𝚛𝚕𝚍!", id="punctuation"),
            pytest.param("a b", "𝚊 𝚋", id="spaces"),
            pytest.param("", "", id="empty"),
            pytest.param("Hello World 123", "𝙷𝚎𝚕𝚕𝚘 𝚆𝚘𝚛𝚕𝚍 𝟷𝟸𝟹", id="sentence"),
        ],
    )
    def test_converts(self, text: str, expected: str) -> None:
        assert to_monospace(text) == expected


# ── unmapped characters ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "func",
    [
        pytest.param(to_sans_bold, id="bold"),
        pytest.param(to_sans_italic, id="italic"),
        pytest.param(to_sans_bold_italic, id="bold_italic"),
        pytest.param(to_monospace, id="monospace"),
    ],
)
def test_ascii_punctuation_passes_through(func: Callable[[str], str]) -> None:
    # Punctuation fills the ASCII gaps around the letters and digits (``@``
    # before ``A``, ``[`` after ``Z``, ``:`` after ``9``, ...), so a table
    # that maps one character too many beside a range changes this string.
    assert func(string.punctuation) == string.punctuation


# ── apply_style ────────────────────────────────────────────────────────────────


class TestApplyStyle:
    @pytest.mark.parametrize("text", ["", "hello", "Test123"])
    @pytest.mark.parametrize(
        ("style", "func"),
        [
            ("bold", to_sans_bold),
            ("italic", to_sans_italic),
            ("bold_italic", to_sans_bold_italic),
        ],
    )
    def test_dispatches_to_the_style_function(
        self,
        style: Literal["bold", "italic", "bold_italic"],
        func: Callable[[str], str],
        text: str,
    ) -> None:
        assert apply_style(text, style) == func(text)

    def test_invalid_style_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown style"):
            apply_style("hello", cast("Any", "underline"))
