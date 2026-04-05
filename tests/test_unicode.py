"""Tests for md2linkedin._unicode — Unicode character mapping functions."""

from __future__ import annotations

import pytest

from md2linkedin._unicode import (
    apply_style,
    to_sans_bold,
    to_sans_bold_italic,
    to_sans_italic,
)


# ── to_sans_bold ───────────────────────────────────────────────────────────────


class TestToSansBold:
    def test_uppercase_letters(self):
        result = to_sans_bold("ABCXYZ")
        assert result == "𝗔𝗕𝗖𝗫𝗬𝗭"

    def test_lowercase_letters(self):
        result = to_sans_bold("abcxyz")
        assert result == "𝗮𝗯𝗰𝘅𝘆𝘇"

    def test_digits(self):
        result = to_sans_bold("0123456789")
        assert result == "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"

    def test_non_ascii_passthrough(self):
        assert to_sans_bold("café") == "𝗰𝗮𝗳é"

    def test_emoji_passthrough(self):
        assert to_sans_bold("hi 🎉") == "𝗵𝗶 🎉"

    def test_punctuation_passthrough(self):
        assert to_sans_bold("Hello, World!") == "𝗛𝗲𝗹𝗹𝗼, 𝗪𝗼𝗿𝗹𝗱!"

    def test_spaces_passthrough(self):
        assert to_sans_bold("a b") == "𝗮 𝗯"

    def test_empty_string(self):
        assert to_sans_bold("") == ""

    def test_full_sentence(self):
        result = to_sans_bold("Hello World 123")
        assert result == "𝗛𝗲𝗹𝗹𝗼 𝗪𝗼𝗿𝗹𝗱 𝟭𝟮𝟯"


# ── to_sans_italic ─────────────────────────────────────────────────────────────


class TestToSansItalic:
    def test_uppercase_letters(self):
        result = to_sans_italic("ABCXYZ")
        assert result == "𝘈𝘉𝘊𝘟𝘠𝘡"

    def test_lowercase_letters(self):
        result = to_sans_italic("abcxyz")
        assert result == "𝘢𝘣𝘤𝘹𝘺𝘻"

    def test_digits_unchanged(self):
        # No italic digits in this Unicode block
        assert to_sans_italic("123") == "123"

    def test_non_ascii_passthrough(self):
        assert to_sans_italic("café") == "𝘤𝘢𝘧é"

    def test_emoji_passthrough(self):
        assert to_sans_italic("go 🚀") == "𝘨𝘰 🚀"

    def test_punctuation_passthrough(self):
        assert to_sans_italic("Hello!") == "𝘏𝘦𝘭𝘭𝘰!"

    def test_empty_string(self):
        assert to_sans_italic("") == ""


# ── to_sans_bold_italic ────────────────────────────────────────────────────────


class TestToSansBoldItalic:
    def test_uppercase_letters(self):
        result = to_sans_bold_italic("ABCXYZ")
        assert result == "𝘼𝘽𝘾𝙓𝙔𝙕"

    def test_lowercase_letters(self):
        result = to_sans_bold_italic("abcxyz")
        assert result == "𝙖𝙗𝙘𝙭𝙮𝙯"

    def test_digits_unchanged(self):
        assert to_sans_bold_italic("123") == "123"

    def test_non_ascii_passthrough(self):
        assert to_sans_bold_italic("café") == "𝙘𝙖𝙛é"

    def test_empty_string(self):
        assert to_sans_bold_italic("") == ""

    def test_mixed(self):
        result = to_sans_bold_italic("Hello World!")
        assert result == "𝙃𝙚𝙡𝙡𝙤 𝙒𝙤𝙧𝙡𝙙!"


# ── apply_style ────────────────────────────────────────────────────────────────


class TestApplyStyle:
    def test_bold(self):
        assert apply_style("hello", "bold") == to_sans_bold("hello")

    def test_italic(self):
        assert apply_style("hello", "italic") == to_sans_italic("hello")

    def test_bold_italic(self):
        assert apply_style("hello", "bold_italic") == to_sans_bold_italic("hello")

    def test_invalid_style_raises(self):
        with pytest.raises(ValueError, match="Unknown style"):
            apply_style("hello", "underline")  # type: ignore[arg-type]

    def test_empty_string(self):
        assert apply_style("", "bold") == ""
        assert apply_style("", "italic") == ""
        assert apply_style("", "bold_italic") == ""

    def test_roundtrip_consistency(self):
        text = "Test123"
        assert apply_style(text, "bold") == to_sans_bold(text)
        assert apply_style(text, "italic") == to_sans_italic(text)
        assert apply_style(text, "bold_italic") == to_sans_bold_italic(text)
