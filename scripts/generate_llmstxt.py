"""Generate llms.txt and llms-full.txt from mkdocs.yml.

This script acts as a replacement for the mkdocs-llmstxt plugin
since zensical does not execute MkDocs plugins.
"""

from pathlib import Path
from typing import Any

import yaml


def _get_llmstxt_config(config: dict[str, Any]) -> dict[str, Any] | None:
    for plugin in config.get("plugins", []):
        if isinstance(plugin, dict) and "llmstxt" in plugin:
            return plugin["llmstxt"]
    return None


def _write_section(
    content: list[str], section_name: str, patterns: list[str], *, is_full: bool
) -> None:
    content.extend((f"## {section_name}", ""))
    for pattern in patterns:
        for p in sorted(Path("docs").glob(pattern)):
            if not p.is_file():
                continue
            if is_full:
                content.extend((f"### {p.stem}", "", p.read_text(encoding="utf-8"), ""))
            else:
                rel_path = p.parent.relative_to("docs").as_posix()
                url = f"https://www.indrapatil.com/md2linkedin/{rel_path}/{p.stem}/"
                url = url.replace("/./", "/")
                content.append(f"- [{p.stem}]({url})")
    content.append("")


def main() -> None:
    """Generate llms.txt files from mkdocs.yml config."""
    mkdocs_file = Path("mkdocs.yml")
    if not mkdocs_file.exists():
        return

    with mkdocs_file.open(encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.BaseLoader)

    llmstxt_config = _get_llmstxt_config(config)
    if not llmstxt_config or not llmstxt_config.get("enabled", True):
        return

    description = llmstxt_config.get("markdown_description", "")
    sections = llmstxt_config.get("sections", {})
    output_files = [("llms.txt", False)]
    if llmstxt_config.get("full_output"):
        output_files.append((llmstxt_config["full_output"], True))

    for out_name, is_full in output_files:
        content = []
        if description:
            content.extend((description, ""))

        for section_name, patterns in sections.items():
            _write_section(content, section_name, patterns, is_full=is_full)

        out_path = Path("docs") / out_name
        out_path.write_text("\n".join(content), encoding="utf-8")


if __name__ == "__main__":
    main()
