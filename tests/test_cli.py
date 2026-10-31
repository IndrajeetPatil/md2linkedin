"""Tests for md2linkedin._cli — Click-based command-line interface."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from click.testing import CliRunner

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
        assert "LinkedIn-formatted" in result.output

    def test_default_output_filename(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "post.md"
        src.write_text("hello", encoding="utf-8")
        runner.invoke(main, [str(src)])
        expected = tmp_path / "post.linkedin.txt"
        assert expected.exists()

    def test_explicit_output_path(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "post.md"
        dst = tmp_path / "out.txt"
        src.write_text("hello", encoding="utf-8")
        result = runner.invoke(main, [str(src), "-o", str(dst)])
        assert result.exit_code == 0
        assert dst.exists()

    def test_preserve_links_flag(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "post.md"
        src.write_text("[GitHub](https://github.com)", encoding="utf-8")
        dst = tmp_path / "out.txt"
        runner.invoke(main, [str(src), "-o", str(dst), "--preserve-links"])
        assert dst.read_text(encoding="utf-8").strip() == "[GitHub](https://github.com)"

    def test_output_path_printed(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        result = runner.invoke(main, [str(src)])
        assert str(tmp_path) in result.output

    def test_nonexistent_file_error(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(main, [str(tmp_path / "missing.md")])
        assert result.exit_code != 0


class TestCliStdin:
    @pytest.mark.parametrize("is_tty", [True, False])
    def test_detects_terminal(self, *, is_tty: bool) -> None:
        with patch("md2linkedin._cli.sys.stdin.isatty", return_value=is_tty):
            assert _stdin_is_tty() is is_tty

    @pytest.mark.parametrize(
        ("markdown", "marker"),
        [("**hello** world", "**"), ("*italic*", "*")],
        ids=["bold", "italic"],
    )
    def test_reads_from_stdin(
        self,
        runner: CliRunner,
        markdown: str,
        marker: str,
    ) -> None:
        result = runner.invoke(main, [], input=markdown)
        assert result.exit_code == 0
        assert marker not in result.output

    def test_stdin_empty(self, runner: CliRunner) -> None:
        result = runner.invoke(main, [], input="")
        assert result.exit_code == 0

    def test_tty_stdin_no_file_error(self, runner: CliRunner) -> None:
        with patch("md2linkedin._cli._stdin_is_tty", return_value=True):
            result = runner.invoke(main, [])
        assert result.exit_code != 0


class TestCliNoMonospaceCode:
    def test_no_monospace_code_flag_file(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        src = tmp_path / "post.md"
        src.write_text("use `hello` here", encoding="utf-8")
        dst = tmp_path / "out.txt"
        runner.invoke(main, [str(src), "-o", str(dst), "--no-monospace-code"])
        content = dst.read_text(encoding="utf-8")
        assert "hello" in content
        assert "𝚑𝚎𝚕𝚕𝚘" not in content

    def test_monospace_code_default_on(self, runner: CliRunner, tmp_path: Path) -> None:
        src = tmp_path / "post.md"
        src.write_text("use `hello` here", encoding="utf-8")
        dst = tmp_path / "out.txt"
        runner.invoke(main, [str(src), "-o", str(dst)])
        content = dst.read_text(encoding="utf-8")
        assert "𝚑𝚎𝚕𝚕𝚘" in content

    def test_no_monospace_code_stdin(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--no-monospace-code"], input="use `hello` here")
        assert result.exit_code == 0
        assert "hello" in result.output
        assert "𝚑𝚎𝚕𝚕𝚘" not in result.output


class TestCliFlags:
    @pytest.mark.parametrize("flag", ["--version", "-V"])
    def test_version_flag(self, runner: CliRunner, flag: str) -> None:
        result = runner.invoke(main, [flag])
        assert result.exit_code == 0
        assert "." in result.output  # version number contains dots

    @pytest.mark.parametrize("flag", ["--help", "-h"])
    def test_help_flag(self, runner: CliRunner, flag: str) -> None:
        result = runner.invoke(main, [flag])
        assert result.exit_code == 0
        assert "Markdown" in result.output
