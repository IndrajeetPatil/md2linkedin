# hextools

This folder contains the R script used to generate the `md2linkedin` hex
sticker logo.

## Generating the logo

The sticker artwork is `data.jpeg`, a composition of three Flaticon icons
(Markdown, LinkedIn and an arrow, all by Freepik). To regenerate the logo:

1. **Install R dependencies**:

   ```r
   install.packages(c("hexSticker", "magick", "showtext"))
   ```

2. **Run the script** from the repository root:

   ```bash
   Rscript hextools/script.R
   ```

   The generated logo is written to `docs/assets/logo.png`.

## Icon credits

Icons are sourced from [Flaticon](https://www.flaticon.com/) and made by
[Freepik](https://www.flaticon.com/authors/freepik). Please review and comply
with Flaticon's [license terms](https://www.flaticon.com/license) before
redistributing the icons.
