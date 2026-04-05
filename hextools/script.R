library(hexSticker)
library(magick)
library(showtext)

google_font_name <- "Rubik"
font_add_google(google_font_name)

showtext_auto()

img <- image_read("hextools/data.jpeg")

sticker(
    img,
    package = "md2linkedin",
    p_color = "#545452",
    p_family = google_font_name,
    p_size = 40,
    p_x = 1,
    p_y = 1.55,
    s_x = 1,
    s_y = 0.9,
    s_width = 1,
    s_height = 0.9,
    h_color = "grey",
    filename = "docs/assets/logo.png",
    h_fill = "white",
    url = "https://www.indrapatil.com/md2linkedin/",
    u_size = 8,
    u_color = "grey",
    dpi = 600
)

fs:::dir_create("man/figures")
fs::file_copy("docs/assets/logo.png", "man/figures/logo.png", overwrite = TRUE)
pkgdown::build_favicons()
fs::dir_copy("pkgdown/favicon", "docs/favicon", overwrite = TRUE)
fs::dir_delete("pkgdown")
fs::dir_delete("man")
fs::file_delete("DESCRIPTION")
