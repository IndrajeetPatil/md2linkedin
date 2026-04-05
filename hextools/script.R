library(hexSticker)
library(magick)
library(showtext)

# ── Font ──────────────────────────────────────────────────────────────────────

google_font_name <- "Rubik"
font_add_google(google_font_name)
showtext_auto()

# ── Compose icon: Markdown → Arrow → LinkedIn ─────────────────────────────────
# Download icon_md.png, icon_arrow.png, and icon_linkedin.png from Flaticon
# and place them in this hextools/ directory before running this script.
# See README.md for acknowledgements.

icon_md <- image_read("hextools/icon_md.png")
icon_arrow <- image_read("hextools/icon_arrow.png")
icon_linkedin <- image_read("hextools/icon_linkedin.png")

# Resize all icons to the same height
icon_md <- image_resize(icon_md, "150x150!")
icon_arrow <- image_resize(icon_arrow, "80x80!")
icon_linkedin <- image_resize(icon_linkedin, "150x150!")

# Compose horizontally with padding
padding <- image_blank(20, 150, color = "white")
composite <- image_append(
  c(icon_md, padding, icon_arrow, padding, icon_linkedin),
  stack = FALSE
)

# Write composed image to a temp file
composed_path <- tempfile(fileext = ".png")
image_write(composite, composed_path)

# ── Generate hex sticker ──────────────────────────────────────────────────────

sticker(
    composed_path,
    package = "md2linkedin",
    p_color = "#0A66C2",       # LinkedIn blue
    p_family = google_font_name,
    p_size = 28,
    p_x = 1,
    p_y = 1.55,
    s_x = 1,
    s_y = 0.88,
    s_width = 1.1,
    s_height = 0.7,
    h_color = "#0A66C2",
    h_fill = "white",
    filename = "docs/assets/logo.png",
    url = "https://www.indrapatil.com/md2linkedin/",
    u_size = 7,
    u_color = "#0A66C2",
    dpi = 600
)

# Copy to man/figures for pkgdown compatibility then clean up
fs:::dir_create("man/figures")
fs::file_copy("docs/assets/logo.png", "man/figures/logo.png", overwrite = TRUE)
pkgdown::build_favicons()
fs::dir_copy("pkgdown/favicon", "docs/favicon", overwrite = TRUE)
fs::dir_delete("pkgdown")
fs::dir_delete("man")
fs::file_delete("DESCRIPTION")

# Clean up temp file
unlink(composed_path)
