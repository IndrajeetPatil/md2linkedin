# hextools

This folder contains the R script used to generate the `md2linkedin` hex
sticker logo.

## Generating the logo

1. **Download icons** from [Flaticon](https://www.flaticon.com/) and place
   them in this directory:
   - `icon_md.png` — Markdown icon
     (search: "markdown" on flaticon.com; e.g. by Freepik)
   - `icon_linkedin.png` — LinkedIn icon
     (search: "linkedin" on flaticon.com; e.g. by Freepik)
   - `icon_arrow.png` — Arrow/conversion icon
     (search: "arrow convert" on flaticon.com; e.g. by Freepik)

2. **Install R dependencies**:

   ```r
   install.packages(c("hexSticker", "magick", "showtext"))
   ```

3. **Run the script** from the repository root:

   ```bash
   Rscript hextools/script.R
   ```

   The generated logo is written to `docs/assets/logo.png`.

## Icon credits

Icons are sourced from [Flaticon](https://www.flaticon.com/) and made by
[Freepik](https://www.flaticon.com/authors/freepik). Please review and comply
with Flaticon's [license terms](https://www.flaticon.com/license) before
redistributing the icons.
