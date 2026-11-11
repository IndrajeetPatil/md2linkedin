"""Tests for md2linkedin._unicode — Unicode character mapping functions."""

from __future__ import annotations

import string
import unicodedata
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

    def test_digits_omitted_when_base_is_none(self) -> None:
        table = _build_table(0x100, 0x200)
        assert not any(ord(d) in table for d in string.digits)

    def test_ascii_maps_only_letters_and_digits(self) -> None:
        table = _build_table(0x100, 0x200, 0x300)
        mapped = {chr(cp) for cp in table if cp < 0x80}
        assert mapped == set(string.ascii_letters + string.digits)

    @pytest.mark.parametrize(
        ("char", "expected"),
        [
            pytest.param("é", "\u0204\u0301", id="acute"),
            pytest.param("Ä", "\u0100\u0308", id="uppercase-umlaut"),
            pytest.param("ǖ", "\u0214\u0308\u0304", id="stacked-marks"),
            pytest.param("ẞ", None, id="capital-sharp-s"),
            pytest.param("ł", None, id="no-decomposition"),
        ],
    )
    def test_accented_letters_map_to_styled_base_and_marks(
        self,
        char: str,
        expected: str | None,
    ) -> None:
        assert _build_table(0x100, 0x200).get(ord(char)) == expected

    def test_every_decomposable_latin_letter_is_mapped(self) -> None:
        # Guards the hard-coded Latin ranges: a letter composed of an ASCII
        # base and marks outside them would silently lose its styling.
        # Singleton decompositions, such as U+212A KELVIN SIGN to ``K``, are
        # duplicate symbols rather than accented letters and are left out.
        table = _build_table(0x100, 0x200)
        letters = set(string.ascii_letters)
        composed = {
            cp
            for cp in range(0x80, 0x110000)
            if unicodedata.normalize("NFD", chr(cp))[0] in letters
            and " " in unicodedata.decomposition(chr(cp))
        }
        assert composed <= table.keys()


class TestToSansBold:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("ABCXYZ", "𝗔𝗕𝗖𝗫𝗬𝗭", id="uppercase"),
            pytest.param("abcxyz", "𝗮𝗯𝗰𝘅𝘆𝘇", id="lowercase"),
            pytest.param(string.digits, "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵", id="digits"),
            pytest.param("café", "𝗰𝗮𝗳𝗲\u0301", id="accented"),
            pytest.param("Grüße", "𝗚𝗿𝘂\u0308ß𝗲", id="umlaut-and-sharp-s"),
            pytest.param("Ärger", "𝗔\u0308𝗿𝗴𝗲𝗿", id="uppercase-accented"),
            pytest.param("u\u0308", "𝘂\u0308", id="already-decomposed"),
            pytest.param("Hello, World 123!", "𝗛𝗲𝗹𝗹𝗼, 𝗪𝗼𝗿𝗹𝗱 𝟭𝟮𝟯!", id="sentence"),
        ],
    )
    def test_converts(self, text: str, expected: str) -> None:
        assert to_sans_bold(text) == expected


class TestToSansItalic:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("ABCXYZ", "𝘈𝘉𝘊𝘟𝘠𝘡", id="uppercase"),
            pytest.param("abcxyz", "𝘢𝘣𝘤𝘹𝘺𝘻", id="lowercase"),
            # No italic digits in this Unicode block
            pytest.param("123", "123", id="digits-unchanged"),
            pytest.param("café", "𝘤𝘢𝘧𝘦\u0301", id="accented"),
            pytest.param("Hello World!", "𝘏𝘦𝘭𝘭𝘰 𝘞𝘰𝘳𝘭𝘥!", id="sentence"),
        ],
    )
    def test_converts(self, text: str, expected: str) -> None:
        assert to_sans_italic(text) == expected


class TestToSansBoldItalic:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("ABCXYZ", "𝘼𝘽𝘾𝙓𝙔𝙕", id="uppercase"),
            pytest.param("abcxyz", "𝙖𝙗𝙘𝙭𝙮𝙯", id="lowercase"),
            pytest.param("123", "123", id="digits-unchanged"),
            pytest.param("café", "𝙘𝙖𝙛𝙚\u0301", id="accented"),
            pytest.param("Hello World!", "𝙃𝙚𝙡𝙡𝙤 𝙒𝙤𝙧𝙡𝙙!", id="sentence"),
        ],
    )
    def test_converts(self, text: str, expected: str) -> None:
        assert to_sans_bold_italic(text) == expected


class TestToMonospace:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("ABCXYZ", "𝙰𝙱𝙲𝚇𝚈𝚉", id="uppercase"),
            pytest.param("abcxyz", "𝚊𝚋𝚌𝚡𝚢𝚣", id="lowercase"),
            pytest.param(string.digits, "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿", id="digits"),
            pytest.param("café", "𝚌𝚊𝚏𝚎\u0301", id="accented"),
            pytest.param("Größe", "𝙶𝚛𝚘\u0308ß𝚎", id="umlaut-and-sharp-s"),
            pytest.param("Hello, World 123!", "𝙷𝚎𝚕𝚕𝚘, 𝚆𝚘𝚛𝚕𝚍 𝟷𝟸𝟹!", id="sentence"),
        ],
    )
    def test_converts(self, text: str, expected: str) -> None:
        assert to_monospace(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty"),
        pytest.param(" \t\n", id="whitespace"),
        pytest.param("ß ł 🎉 🚀", id="non-ascii"),
        # Hangul syllables have canonical decompositions too, but into jamo,
        # not ASCII letters, so they must stay composed.
        pytest.param("한글 Ωμέγα ё", id="non-latin-scripts"),
        # Punctuation fills the ASCII gaps around the letters and digits (``@``
        # before ``A``, ``[`` after ``Z``, ``:`` after ``9``, ...), so a table
        # that maps one character too many beside a range changes this string.
        pytest.param(string.punctuation, id="ascii-punctuation"),
    ],
)
@pytest.mark.parametrize(
    "func",
    [
        pytest.param(to_sans_bold, id="bold"),
        pytest.param(to_sans_italic, id="italic"),
        pytest.param(to_sans_bold_italic, id="bold_italic"),
        pytest.param(to_monospace, id="monospace"),
    ],
)
def test_unmapped_characters_pass_through(
    func: Callable[[str], str],
    text: str,
) -> None:
    assert func(text) == text


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
