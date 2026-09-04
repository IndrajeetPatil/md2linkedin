"""Tests for md2linkedin._unicode — Unicode character mapping functions."""

from __future__ import annotations

import string
from typing import TYPE_CHECKING, Any, Literal, cast

import pytest

from md2linkedin._unicode import (
    apply_style,
    to_monospace,
    to_sans_bold,
    to_sans_bold_italic,
    to_sans_italic,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# ── to_sans_bold ───────────────────────────────────────────────────────────────


class TestToSansBold:
    def test_uppercase_letters(self) -> None:
        result = to_sans_bold("ABCXYZ")
        assert result == "𝗔𝗕𝗖𝗫𝗬𝗭"

    def test_lowercase_letters(self) -> None:
        result = to_sans_bold("abcxyz")
        assert result == "𝗮𝗯𝗰𝘅𝘆𝘇"

    def test_digits(self) -> None:
        result = to_sans_bold(string.digits)
        assert result == "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"

    def test_non_ascii_passthrough(self) -> None:
        assert to_sans_bold("café") == "𝗰𝗮𝗳é"

    def test_emoji_passthrough(self) -> None:
        assert to_sans_bold("hi 🎉") == "𝗵𝗶 🎉"

    def test_punctuation_passthrough(self) -> None:
        assert to_sans_bold("Hello, World!") == "𝗛𝗲𝗹𝗹𝗼, 𝗪𝗼𝗿𝗹𝗱!"

    def test_spaces_passthrough(self) -> None:
        assert to_sans_bold("a b") == "𝗮 𝗯"

    def test_empty_string(self) -> None:
        assert not to_sans_bold("")

    def test_full_sentence(self) -> None:
        result = to_sans_bold("Hello World 123")
        assert result == "𝗛𝗲𝗹𝗹𝗼 𝗪𝗼𝗿𝗹𝗱 𝟭𝟮𝟯"

    @pytest.mark.parametrize(
        ("char", "expected"),
        [("A", "𝗔"), ("Z", "𝗭"), ("a", "𝗮"), ("z", "𝘇"), ("0", "𝟬"), ("9", "𝟵")],
        ids=["A", "Z", "a", "z", "0", "9"],
    )
    def test_boundary_characters_mapped(self, char: str, expected: str) -> None:
        # Guard against boundary mutations (e.g. "A" <= c <= "z", "0" <= c <= "9").
        assert to_sans_bold(char) == expected

    @pytest.mark.parametrize(
        "char",
        ["[", "\\", "]", "^", "_", "`", "{", "|", "}", "~", ":", ";", "?", "@"],
    )
    def test_between_ascii_ranges_passthrough(self, char: str) -> None:
        # Chars in ASCII gaps like Z<x<a or 9<x<A must pass through unchanged.
        assert to_sans_bold(char) == char


# ── to_sans_italic ─────────────────────────────────────────────────────────────


class TestToSansItalic:
    def test_uppercase_letters(self) -> None:
        result = to_sans_italic("ABCXYZ")
        assert result == "𝘈𝘉𝘊𝘟𝘠𝘡"

    def test_lowercase_letters(self) -> None:
        result = to_sans_italic("abcxyz")
        assert result == "𝘢𝘣𝘤𝘹𝘺𝘻"

    def test_digits_unchanged(self) -> None:
        # No italic digits in this Unicode block
        assert to_sans_italic("123") == "123"

    def test_non_ascii_passthrough(self) -> None:
        assert to_sans_italic("café") == "𝘤𝘢𝘧é"

    def test_emoji_passthrough(self) -> None:
        assert to_sans_italic("go 🚀") == "𝘨𝘰 🚀"

    def test_punctuation_passthrough(self) -> None:
        assert to_sans_italic("Hello!") == "𝘏𝘦𝘭𝘭𝘰!"

    def test_empty_string(self) -> None:
        assert not to_sans_italic("")

    @pytest.mark.parametrize(
        ("char", "expected"),
        [("A", "𝘈"), ("Z", "𝘡"), ("a", "𝘢"), ("z", "𝘻")],
        ids=["A", "Z", "a", "z"],
    )
    def test_boundary_characters_mapped(self, char: str, expected: str) -> None:
        # Guard against boundary mutations in the "a" <= c <= "z" comparison.
        assert to_sans_italic(char) == expected

    @pytest.mark.parametrize("char", ["[", "\\", "]", "^", "_", "`"])
    def test_between_ranges_passthrough(self, char: str) -> None:
        assert to_sans_italic(char) == char


# ── to_sans_bold_italic ────────────────────────────────────────────────────────


class TestToSansBoldItalic:
    def test_uppercase_letters(self) -> None:
        result = to_sans_bold_italic("ABCXYZ")
        assert result == "𝘼𝘽𝘾𝙓𝙔𝙕"

    def test_lowercase_letters(self) -> None:
        result = to_sans_bold_italic("abcxyz")
        assert result == "𝙖𝙗𝙘𝙭𝙮𝙯"

    def test_digits_unchanged(self) -> None:
        assert to_sans_bold_italic("123") == "123"

    def test_non_ascii_passthrough(self) -> None:
        assert to_sans_bold_italic("café") == "𝙘𝙖𝙛é"

    def test_empty_string(self) -> None:
        assert not to_sans_bold_italic("")

    def test_mixed(self) -> None:
        result = to_sans_bold_italic("Hello World!")
        assert result == "𝙃𝙚𝙡𝙡𝙤 𝙒𝙤𝙧𝙡𝙙!"

    @pytest.mark.parametrize(
        ("char", "expected"),
        [("A", "𝘼"), ("Z", "𝙕"), ("a", "𝙖"), ("z", "𝙯")],
        ids=["A", "Z", "a", "z"],
    )
    def test_boundary_characters_mapped(self, char: str, expected: str) -> None:
        assert to_sans_bold_italic(char) == expected

    @pytest.mark.parametrize("char", ["[", "\\", "]", "^", "_", "`"])
    def test_between_ranges_passthrough(self, char: str) -> None:
        assert to_sans_bold_italic(char) == char


# ── to_monospace ──────────────────────────────────────────────────────────────


class TestToMonospace:
    def test_uppercase_letters(self) -> None:
        result = to_monospace("ABCXYZ")
        assert result == "𝙰𝙱𝙲𝚇𝚈𝚉"

    def test_lowercase_letters(self) -> None:
        result = to_monospace("abcxyz")
        assert result == "𝚊𝚋𝚌𝚡𝚢𝚣"

    def test_digits(self) -> None:
        result = to_monospace(string.digits)
        assert result == "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"

    def test_non_ascii_passthrough(self) -> None:
        assert to_monospace("café") == "𝚌𝚊𝚏é"

    def test_emoji_passthrough(self) -> None:
        assert to_monospace("hi 🎉") == "𝚑𝚒 🎉"

    def test_punctuation_passthrough(self) -> None:
        assert to_monospace("Hello, World!") == "𝙷𝚎𝚕𝚕𝚘, 𝚆𝚘𝚛𝚕𝚍!"

    def test_spaces_passthrough(self) -> None:
        assert to_monospace("a b") == "𝚊 𝚋"

    def test_empty_string(self) -> None:
        assert not to_monospace("")

    def test_full_sentence(self) -> None:
        result = to_monospace("Hello World 123")
        assert result == "𝙷𝚎𝚕𝚕𝚘 𝚆𝚘𝚛𝚕𝚍 𝟷𝟸𝟹"

    @pytest.mark.parametrize(
        ("char", "expected"),
        [("A", "𝙰"), ("Z", "𝚉"), ("a", "𝚊"), ("z", "𝚣"), ("0", "𝟶"), ("9", "𝟿")],
        ids=["A", "Z", "a", "z", "0", "9"],
    )
    def test_boundary_characters_mapped(self, char: str, expected: str) -> None:
        assert to_monospace(char) == expected

    @pytest.mark.parametrize("char", ["[", "\\", "]", "^", "_", "`", ":", "@"])
    def test_between_ranges_passthrough(self, char: str) -> None:
        assert to_monospace(char) == char


# ── apply_style ────────────────────────────────────────────────────────────────


class TestApplyStyle:
    def test_bold(self) -> None:
        assert apply_style("hello", "bold") == to_sans_bold("hello")

    def test_italic(self) -> None:
        assert apply_style("hello", "italic") == to_sans_italic("hello")

    def test_bold_italic(self) -> None:
        assert apply_style("hello", "bold_italic") == to_sans_bold_italic("hello")

    def test_invalid_style_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown style"):
            apply_style("hello", cast("Any", "underline"))

    @pytest.mark.parametrize("style", ["bold", "italic", "bold_italic"])
    def test_empty_string(
        self,
        style: Literal["bold", "italic", "bold_italic"],
    ) -> None:
        assert not apply_style("", style)

    @pytest.mark.parametrize(
        ("style", "func"),
        [
            ("bold", to_sans_bold),
            ("italic", to_sans_italic),
            ("bold_italic", to_sans_bold_italic),
        ],
    )
    def test_roundtrip_consistency(
        self,
        style: Literal["bold", "italic", "bold_italic"],
        func: Callable[[str], str],
    ) -> None:
        assert apply_style("Test123", style) == func("Test123")
