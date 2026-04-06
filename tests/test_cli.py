"""Tests for md2linkedin._cli — Click-based command-line interface."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from md2linkedin._cli import main


class TestCliFileInput:
    def test_converts_file(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        src.write_text("**bold** text", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, [str(src)])
        assert result.exit_code == 0
        assert "LinkedIn-formatted" in result.output

    def test_default_output_filename(self, tmp_path) -> None:
        src = tmp_path / "post.md"
        src.write_text("hello", encoding="utf-8")
        runner = CliRunner()
        runner.invoke(main, [str(src)])
        expected = tmp_path / "post.linkedin.txt"
        assert expected.exists()

    def test_explicit_output_path(self, tmp_path) -> None:
        src = tmp_path / "post.md"
        dst = tmp_path / "out.txt"
        src.write_text("hello", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, [str(src), "-o", str(dst)])
        assert result.exit_code == 0
        assert dst.exists()

    def test_preserve_links_flag(self, tmp_path) -> None:
        src = tmp_path / "post.md"
        src.write_text("[GitHub](https://github.com)", encoding="utf-8")
        dst = tmp_path / "out.txt"
        runner = CliRunner()
        runner.invoke(main, [str(src), "-o", str(dst), "--preserve-links"])
        assert "https://github.com" in dst.read_text(encoding="utf-8")

    def test_output_path_printed(self, tmp_path) -> None:
        src = tmp_path / "test.md"
        src.write_text("hello", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, [str(src)])
        assert str(tmp_path) in result.output

    def test_nonexistent_file_error(self, tmp_path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_path / "missing.md")])
        assert result.exit_code != 0


class TestCliStdin:
    def test_reads_from_stdin(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, [], input="**hello** world")
        assert result.exit_code == 0
        assert "**" not in result.output

    def test_stdin_italic(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, [], input="*italic*")
        assert result.exit_code == 0
        assert "*" not in result.output

    def test_stdin_empty(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, [], input="")
        assert result.exit_code == 0

    def test_tty_stdin_no_file_error(self) -> None:
        runner = CliRunner()
        with patch("md2linkedin._cli._stdin_is_tty", return_value=True):
            result = runner.invoke(main, [])
        assert result.exit_code != 0


class TestCliNoMonospaceCode:
    def test_no_monospace_code_flag_file(self, tmp_path) -> None:
        src = tmp_path / "post.md"
        src.write_text("use `hello` here", encoding="utf-8")
        dst = tmp_path / "out.txt"
        runner = CliRunner()
        runner.invoke(main, [str(src), "-o", str(dst), "--no-monospace-code"])
        content = dst.read_text(encoding="utf-8")
        assert "hello" in content
        assert "𝚑𝚎𝚕𝚕𝚘" not in content

    def test_monospace_code_default_on(self, tmp_path) -> None:
        src = tmp_path / "post.md"
        src.write_text("use `hello` here", encoding="utf-8")
        dst = tmp_path / "out.txt"
        runner = CliRunner()
        runner.invoke(main, [str(src), "-o", str(dst)])
        content = dst.read_text(encoding="utf-8")
        assert "𝚑𝚎𝚕𝚕𝚘" in content

    def test_no_monospace_code_stdin(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--no-monospace-code"], input="use `hello` here")
        assert result.exit_code == 0
        assert "hello" in result.output
        assert "𝚑𝚎𝚕𝚕𝚘" not in result.output


class TestCliFlags:
    def test_version_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "." in result.output  # version number contains dots

    def test_version_short_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["-V"])
        assert result.exit_code == 0

    def test_help_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Markdown" in result.output

    def test_help_short_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["-h"])
        assert result.exit_code == 0
