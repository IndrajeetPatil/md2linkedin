"""Tests for md2linkedin._cli — Click-based command-line interface."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from md2linkedin import __version__
from md2linkedin._cli import _stdin_is_tty, main

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestCliFileInput:
    def test_converts_file(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("**bold** text", encoding="utf-8")
        result = runner.invoke(main, [str(src)])
        assert result.exit_code == 0
        assert (tmp_path / "test.linkedin.txt").read_text(encoding="utf-8") == (
            "𝗯𝗼𝗹𝗱 text\n"
        )

    def test_default_output_filename(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "post.md"
        src.write_text("hello", encoding="utf-8")
        result = runner.invoke(main, [str(src)])
        assert result.exit_code == 0
        expected = tmp_path / "post.linkedin.txt"
        assert expected.read_text(encoding="utf-8") == "hello\n"

    def test_explicit_output_path(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "post.md"
        dst = tmp_path / "out.txt"
        src.write_text("hello", encoding="utf-8")
        result = runner.invoke(main, [str(src), "-o", str(dst)])
        assert result.exit_code == 0
        assert dst.read_text(encoding="utf-8") == "hello\n"

    def test_preserve_links_flag(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "post.md"
        src.write_text("[GitHub](https://github.com)", encoding="utf-8")
        dst = tmp_path / "out.txt"
        result = runner.invoke(main, [str(src), "-o", str(dst), "--preserve-links"])
        assert result.exit_code == 0
        assert dst.read_text(encoding="utf-8") == "[GitHub](https://github.com)\n"

    def test_output_path_printed(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        result = runner.invoke(main, [str(src)])
        assert result.output == (
            f"LinkedIn-formatted text written to: {tmp_path / 'test.linkedin.txt'}\n"
        )

    def test_nonexistent_file_error(self, runner: CliRunner, tmp_path: Path) -> None:
        missing = tmp_path / "missing.md"
        result = runner.invoke(main, [str(missing)])
        # Click rejects the path itself, as a usage error, before converting.
        assert result.exit_code == 2
        # Click quotes the path with repr(), which doubles Windows backslashes.
        assert f"File {str(missing)!r} does not exist." in result.output


class TestCliStdin:
    @pytest.mark.parametrize("is_tty", [True, False])
    def test_detects_terminal(self, *, is_tty: bool) -> None:
        with patch("md2linkedin._cli.sys.stdin.isatty", return_value=is_tty):
            assert _stdin_is_tty() is is_tty

    @pytest.mark.parametrize(
        ("markdown", "expected"),
        [("**hello** world", "𝗵𝗲𝗹𝗹𝗼 world\n"), ("*italic*", "𝘪𝘵𝘢𝘭𝘪𝘤\n")],
        ids=["bold", "italic"],
    )
    def test_reads_from_stdin(
        self,
        runner: CliRunner,
        markdown: str,
        expected: str,
    ) -> None:
        result = runner.invoke(main, [], input=markdown)
        assert result.exit_code == 0
        assert result.output == expected

    def test_stdin_empty(self, runner: CliRunner) -> None:
        result = runner.invoke(main, [], input="")
        assert result.exit_code == 0
        assert not result.output

    def test_tty_stdin_no_file_error(self, runner: CliRunner) -> None:
        with patch("md2linkedin._cli._stdin_is_tty", return_value=True):
            result = runner.invoke(main, [])
        assert result.exit_code == 2
        assert "No input file provided and stdin is a terminal." in result.output


class TestCliNoMonospaceCode:
    def test_no_monospace_code_flag_file(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        src = tmp_path / "post.md"
        src.write_text("use `hello` here", encoding="utf-8")
        dst = tmp_path / "out.txt"
        result = runner.invoke(
            main,
            [str(src), "-o", str(dst), "--no-monospace-code"],
        )
        assert result.exit_code == 0
        assert dst.read_text(encoding="utf-8") == "use hello here\n"

    def test_monospace_code_default_on(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "post.md"
        src.write_text("use `hello` here", encoding="utf-8")
        dst = tmp_path / "out.txt"
        result = runner.invoke(main, [str(src), "-o", str(dst)])
        assert result.exit_code == 0
        assert dst.read_text(encoding="utf-8") == "use 𝚑𝚎𝚕𝚕𝚘 here\n"

    def test_no_monospace_code_stdin(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--no-monospace-code"], input="use `hello` here")
        assert result.exit_code == 0
        assert result.output == "use hello here\n"


class TestCliFlags:
    @pytest.mark.parametrize("flag", ["--version", "-V"])
    def test_version_flag(self, runner: CliRunner, flag: str) -> None:
        result = runner.invoke(main, [flag])
        assert result.exit_code == 0
        assert result.output == f"main, version {__version__}\n"

    @pytest.mark.parametrize("flag", ["--help", "-h"])
    def test_help_flag(self, runner: CliRunner, flag: str) -> None:
        result = runner.invoke(main, [flag])
        assert result.exit_code == 0
        # Usage first, then the docstring's summary line.
        assert result.output.startswith(
            "Usage: main [OPTIONS] [INPUT_FILE]\n\n"
            "  Convert Markdown to LinkedIn-friendly Unicode text.\n",
        )

    def test_help_keeps_examples_unwrapped(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert "\n    md2linkedin README.md -o post.txt\n" in result.output
        assert "\\b" not in result.output
        assert "Raises:" not in result.output
