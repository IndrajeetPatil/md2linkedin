"""Benchmark the public conversion pipeline and Unicode mapping."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from md2linkedin import convert, to_sans_bold

if TYPE_CHECKING:
    from pytest_codspeed.plugin import BenchmarkFixture

MARKDOWN = """## Release notes

**Fast** and *readable* with [documentation](https://example.com).

- First item
- Second item with `code()`

> A quoted paragraph.
"""


@pytest.mark.parametrize("repetitions", [1, 100], ids=["post", "long-document"])
def test_convert_document(benchmark: BenchmarkFixture, repetitions: int) -> None:
    text = MARKDOWN * repetitions
    result = benchmark(convert, text)
    assert result.count("𝗙𝗮𝘀𝘁") == repetitions
    assert result.count("documentation") == repetitions
    assert "**" not in result
    assert "\x00CODE" not in result


def test_preserve_links_and_plain_code(benchmark: BenchmarkFixture) -> None:
    text = MARKDOWN * 20
    result = benchmark(convert, text, preserve_links=True, monospace_code=False)
    assert result.count("[documentation](https://example.com)") == 20
    assert result.count("code()") == 20
    assert "\x00CODE" not in result


def test_unicode_mapping(benchmark: BenchmarkFixture) -> None:
    text = "Hello 123! " * 1000
    assert benchmark(to_sans_bold, text) == "𝗛𝗲𝗹𝗹𝗼 𝟭𝟮𝟯! " * 1000
