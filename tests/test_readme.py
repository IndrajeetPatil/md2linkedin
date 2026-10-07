"""Check that the Python examples in README.md run and print what they claim.

README.md is the single source for the GitHub page, the PyPI description and
the documentation homepage (``docs/index.md`` includes it), so a stale example
would be wrong in all three places at once.

An example's printed output is the next fenced block, preceded by a
``<!--pytest-codeblocks:expected-output-->`` comment. When a change to the
converter alters that output, this test fails until the block is updated.
"""

from pathlib import Path

import pytest
from pytest_codeblocks import CodeBlock, extract_from_file

README = Path(__file__).parents[1] / "README.md"

# Only Python examples run here: the bash blocks install the package or write
# files, and the CLI they call is covered by ``test_cli.py``.
EXAMPLES = [block for block in extract_from_file(README) if block.syntax == "python"]


def test_readme_has_python_examples() -> None:
    assert EXAMPLES


@pytest.mark.parametrize(
    "example",
    EXAMPLES,
    ids=[f"README.md:{block.lineno}" for block in EXAMPLES],
)
def test_readme_example(example: CodeBlock, capsys: pytest.CaptureFixture[str]) -> None:
    expected = example.expected_output
    assert expected is not None, "README example has no expected-output block"
    exec(example.code, {"__name__": "__main__"})  # ruff: ignore[exec-builtin] - trusted repo file
    # ``print(convert(md))`` ends in a blank line that a fenced block cannot
    # show, so trailing newlines are not part of the comparison.
    assert capsys.readouterr().out.rstrip("\n") == expected.rstrip("\n")
