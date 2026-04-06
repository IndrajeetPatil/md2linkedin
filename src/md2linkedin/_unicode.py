"""Unicode Mathematical Sans-Serif character mapping functions.

Converts ASCII letters and digits to their Unicode Mathematical
Sans-Serif equivalents, enabling bold, italic, and bold-italic
styling in plain-text environments like LinkedIn.
"""

from __future__ import annotations

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
    out: list[str] = []
    for c in text:
        if "A" <= c <= "Z":
            out.append(chr(_SANS_BOLD_UPPER + ord(c) - ord("A")))
        elif "a" <= c <= "z":
            out.append(chr(_SANS_BOLD_LOWER + ord(c) - ord("a")))
        elif "0" <= c <= "9":
            out.append(chr(_SANS_BOLD_DIGIT + ord(c) - ord("0")))
        else:
            out.append(c)
    return "".join(out)


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
    out: list[str] = []
    for c in text:
        if "A" <= c <= "Z":
            out.append(chr(_SANS_ITALIC_UPPER + ord(c) - ord("A")))
        elif "a" <= c <= "z":
            out.append(chr(_SANS_ITALIC_LOWER + ord(c) - ord("a")))
        else:
            out.append(c)
    return "".join(out)


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
        '𝘼𝙡𝙡𝙤, 𝙒𝙤𝙧𝙡𝙙!'

        >>> to_sans_bold_italic("")
        ''
    """
    out: list[str] = []
    for c in text:
        if "A" <= c <= "Z":
            out.append(chr(_SANS_BOLD_ITALIC_UPPER + ord(c) - ord("A")))
        elif "a" <= c <= "z":
            out.append(chr(_SANS_BOLD_ITALIC_LOWER + ord(c) - ord("a")))
        else:
            out.append(c)
    return "".join(out)


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
    out: list[str] = []
    for c in text:
        if "A" <= c <= "Z":
            out.append(chr(_MONOSPACE_UPPER + ord(c) - ord("A")))
        elif "a" <= c <= "z":
            out.append(chr(_MONOSPACE_LOWER + ord(c) - ord("a")))
        elif "0" <= c <= "9":
            out.append(chr(_MONOSPACE_DIGIT + ord(c) - ord("0")))
        else:
            out.append(c)
    return "".join(out)


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
