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
    p_color = "#1A1A1A",
    p_family = google_font_name,
    p_size = 40,
    p_x = 1,
    p_y = 1.3,
    s_x = 1,
    s_y = 0.85,
    s_width = 1.35,
    s_height = 1.1,
    h_color = "#2D2D2D",
    filename = "docs/assets/logo.png",
    h_fill = "white",
    url = "https://www.indrapatil.com/md2linkedin/",
    u_x = 0.95,
    u_size = 8,
    u_color = "grey",
    dpi = 600
)
