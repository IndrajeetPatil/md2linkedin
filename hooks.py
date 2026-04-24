from pathlib import Path
from typing import Any


def on_post_build(config: dict[str, Any]) -> None:
    well_known = Path(config["site_dir"]) / ".well-known"
    well_known.mkdir(exist_ok=True)
    (well_known / "llms.txt").write_text(
        "# LLM Documentation Index for md2linkedin\n"
        "# Machine-readable documentation index for AI assistants\n"
        "# See https://llmstxt.org/ for the specification\n\n"
        "/llms.txt: Concise package overview for AI assistants\n"
        "/llms-full.txt: Complete package documentation for AI assistants\n",
        encoding="utf-8",
    )
