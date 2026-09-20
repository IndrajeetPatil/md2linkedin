"""Unicode Mathematical Sans-Serif character mapping functions.

Converts ASCII letters and digits to their Unicode Mathematical
Sans-Serif equivalents, enabling bold, italic, and bold-italic
styling in plain-text environments like LinkedIn.
"""

from __future__ import annotations

import string
from typing import Literal

__all__ = [
    "apply_style",
    "to_monospace",
    "to_sans_bold",
    "to_sans_bold_italic",
    "to_sans_italic",
]

# ── Unicode block offsets ──────────────────────────────────────────────────────
# Reference: Unicode Mathematical Alphanumeric Symbols (U+1D400–U+1D7FF)

_SANS_BOLD_UPPER = 0x1D5D4  # 𝗔
_SANS_BOLD_LOWER = 0x1D5EE  # 𝗮
_SANS_BOLD_DIGIT = 0x1D7EC  # 𝟬

_SANS_ITALIC_UPPER = 0x1D608  # 𝘈
_SANS_ITALIC_LOWER = 0x1D622  # 𝘢

_SANS_BOLD_ITALIC_UPPER = 0x1D63C  # 𝘼
_SANS_BOLD_ITALIC_LOWER = 0x1D656  # 𝙖

_MONOSPACE_UPPER = 0x1D670  # 𝙰
_MONOSPACE_LOWER = 0x1D68A  # 𝚊
_MONOSPACE_DIGIT = 0x1D7F6  # 𝟶


# ── Translation tables ─────────────────────────────────────────────────────────


def _build_table(upper: int, lower: int, digit: int | None = None) -> dict[int, int]:
    """Build a :meth:`str.translate` table for one Unicode style block.

    The table is derived from the codepoints of the block's styled ``A``,
    ``a`` and ``0``. *digit* is ``None`` for the italic blocks, which have no
    digits. Characters absent from the table are left unchanged.
    """
    blocks = [(string.ascii_uppercase, upper), (string.ascii_lowercase, lower)]
    if digit is not None:
        blocks.append((string.digits, digit))
    return {
        ord(char): base + offset
        for chars, base in blocks
        for offset, char in enumerate(chars)
    }


_SANS_BOLD_TABLE = _build_table(_SANS_BOLD_UPPER, _SANS_BOLD_LOWER, _SANS_BOLD_DIGIT)
_SANS_ITALIC_TABLE = _build_table(_SANS_ITALIC_UPPER, _SANS_ITALIC_LOWER)
_SANS_BOLD_ITALIC_TABLE = _build_table(
    _SANS_BOLD_ITALIC_UPPER,
    _SANS_BOLD_ITALIC_LOWER,
)
_MONOSPACE_TABLE = _build_table(_MONOSPACE_UPPER, _MONOSPACE_LOWER, _MONOSPACE_DIGIT)


# ── Public mapping functions ───────────────────────────────────────────────────


def to_sans_bold(text: str) -> str:
    """Convert text to Unicode Mathematical Sans-Serif Bold.

    ASCII uppercase letters, lowercase letters, and digits are mapped to
    their bold sans-serif counterparts. All other characters (spaces,
    punctuation, non-ASCII) pass through unchanged.

    Args:
        text: The input string to convert.

    Returns:
        A new string with ASCII alphanumerics replaced by bold sans-serif
        Unicode equivalents.

    Examples:
        >>> to_sans_bold("Hello, World! 123")
        '𝗛𝗲𝗹𝗹𝗼, 𝗪𝗼𝗿𝗹𝗱! 𝟭𝟮𝟯'

        >>> to_sans_bold("café")
        '𝗰𝗮𝗳é'

        >>> to_sans_bold("")
        ''

    """
    return text.translate(_SANS_BOLD_TABLE)


def to_sans_italic(text: str) -> str:
    """Convert text to Unicode Mathematical Sans-Serif Italic.

    ASCII uppercase and lowercase letters are mapped to their italic
    sans-serif counterparts. Digits and all other characters pass through
    unchanged (there are no italic digit codepoints in this Unicode block).

    Args:
        text: The input string to convert.

    Returns:
        A new string with ASCII letters replaced by italic sans-serif
        Unicode equivalents.

    Examples:
        >>> to_sans_italic("Hello, World!")
        '𝘏𝘦𝘭𝘭𝘰, 𝘞𝘰𝘳𝘭𝘥!'

        >>> to_sans_italic("price: $42")
        '𝘱𝘳𝘪𝘤𝘦: $42'

        >>> to_sans_italic("")
        ''

    """
    return text.translate(_SANS_ITALIC_TABLE)


def to_sans_bold_italic(text: str) -> str:
    """Convert text to Unicode Mathematical Sans-Serif Bold Italic.

    ASCII uppercase and lowercase letters are mapped to their bold-italic
    sans-serif counterparts. Digits and all other characters pass through
    unchanged.

    Args:
        text: The input string to convert.

    Returns:
        A new string with ASCII letters replaced by bold-italic sans-serif
        Unicode equivalents.

    Examples:
        >>> to_sans_bold_italic("Hello, World!")
        '𝙃𝙚𝙡𝙡𝙤, 𝙒𝙤𝙧𝙡𝙙!'

        >>> to_sans_bold_italic("")
        ''

    """
    return text.translate(_SANS_BOLD_ITALIC_TABLE)


def to_monospace(text: str) -> str:
    """Convert text to Unicode Mathematical Monospace.

    ASCII uppercase letters, lowercase letters, and digits are mapped to
    their monospace counterparts. All other characters (spaces,
    punctuation, non-ASCII) pass through unchanged.

    Args:
        text: The input string to convert.

    Returns:
        A new string with ASCII alphanumerics replaced by monospace
        Unicode equivalents.

    Examples:
        >>> to_monospace("Hello, World! 123")
        '𝙷𝚎𝚕𝚕𝚘, 𝚆𝚘𝚛𝚕𝚍! 𝟷𝟸𝟹'

        >>> to_monospace("café")
        '𝚌𝚊𝚏é'

        >>> to_monospace("")
        ''

    """
    return text.translate(_MONOSPACE_TABLE)


def apply_style(text: str, style: Literal["bold", "italic", "bold_italic"]) -> str:
    """Apply a Unicode sans-serif style to text.

    A convenience dispatcher that routes to the appropriate mapping function
    based on the requested style. Useful when the style is determined
    dynamically at runtime.

    Args:
        text: The input string to convert.
        style: One of ``"bold"``, ``"italic"``, or ``"bold_italic"``.

    Returns:
        A new string with the requested Unicode style applied.

    Raises:
        ValueError: If *style* is not one of the three accepted values.

    Examples:
        >>> apply_style("hello", "bold")
        '𝗵𝗲𝗹𝗹𝗼'

        >>> apply_style("hello", "italic")
        '𝘩𝘦𝘭𝘭𝘰'

        >>> apply_style("hello", "bold_italic")
        '𝙝𝙚𝙡𝙡𝙤'

    """
    if style == "bold":
        return to_sans_bold(text)
    if style == "italic":
        return to_sans_italic(text)
    if style == "bold_italic":
        return to_sans_bold_italic(text)
    msg = f"Unknown style {style!r}. Expected 'bold', 'italic', or 'bold_italic'."
    raise ValueError(msg)
