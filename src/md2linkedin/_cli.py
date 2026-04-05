"""Command-line interface for md2linkedin."""

from __future__ import annotations

import sys

import click

from . import __version__
from ._converter import convert, convert_file


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version")
@click.argument(
    "input_file",
    required=False,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "-o",
    "--output",
    "output_file",
    default=None,
    type=click.Path(dir_okay=False),
    help=(
        "Output file path. Defaults to INPUT_FILE with a '.linkedin.txt' extension. "
        "Ignored when reading from stdin."
    ),
)
@click.option(
    "--preserve-links",
    is_flag=True,
    default=False,
    help=(
        "Keep Markdown link syntax ([text](url)) in the output"
        " instead of stripping URLs."
    ),
)
def main(
    input_file: str | None,
    output_file: str | None,
    *,
    preserve_links: bool,
) -> None:
    """Convert Markdown to LinkedIn-friendly Unicode text.

    Reads from INPUT_FILE (or stdin when INPUT_FILE is omitted) and writes
    LinkedIn-compatible plain text in which bold and italic formatting is
    preserved using Unicode Mathematical Sans-Serif characters.

    \b
    Examples:

      # Convert a file (output written to README.linkedin.txt)
      md2linkedin README.md

      # Specify the output path explicitly
      md2linkedin README.md -o post.txt

      # Pipe from stdin
      echo "**Hello**, *world*!" | md2linkedin

      # Keep link URLs in the output
      md2linkedin README.md --preserve-links
    """
    if input_file is not None:
        out_path = convert_file(input_file, output_file, preserve_links=preserve_links)
        click.echo(f"LinkedIn-formatted text written to: {out_path}")
    else:
        # Read from stdin
        if _stdin_is_tty():
            msg = (
                "No input file provided and stdin is a terminal. "
                "Provide a file path or pipe content via stdin."
            )
            raise click.UsageError(
                msg
            )
        md_text = sys.stdin.read()
        result = convert(md_text, preserve_links=preserve_links)
        click.echo(result, nl=False)


def _stdin_is_tty() -> bool:
    """Return True when stdin is an interactive terminal.

    Extracted into its own function so tests can mock it cleanly without
    fighting Click's own stdin-swapping inside ``CliRunner.invoke``.
    """
    return sys.stdin.isatty()
