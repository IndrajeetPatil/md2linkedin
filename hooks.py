import os


def on_post_build(config, **kwargs):
    well_known = os.path.join(config["site_dir"], ".well-known")
    os.makedirs(well_known, exist_ok=True)
    with open(os.path.join(well_known, "llms.txt"), "w") as f:
        f.write(
            "# LLM Documentation Index for md2linkedin\n"
            "# Machine-readable documentation index for AI assistants\n"
            "# See https://llmstxt.org/ for the specification\n\n"
            "/llms.txt: Concise package overview for AI assistants\n"
            "/llms-full.txt: Complete package documentation for AI assistants\n"
        )
