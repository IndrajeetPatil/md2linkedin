# ══════════════════════════════════════════════════════════════════════════════
# md2linkedin – R Implementation
# Convert Markdown to LinkedIn-friendly Unicode text
#
# Port of the Python md2linkedin package. No external dependencies (base R only).
# ══════════════════════════════════════════════════════════════════════════════

# Null-coalescing operator (define only if not already in base, i.e. R < 4.4)
if (!exists("%||%", baseenv())) `%||%` <- function(x, y) if (is.null(x)) y else x

# ── Unicode Block Offsets ─────────────────────────────────────────────────────
# Reference: Unicode Mathematical Alphanumeric Symbols (U+1D400–U+1D7FF)

.SANS_BOLD_UPPER       <- 0x1D5D4L
.SANS_BOLD_LOWER       <- 0x1D5EEL
.SANS_BOLD_DIGIT       <- 0x1D7ECL
.SANS_ITALIC_UPPER     <- 0x1D608L
.SANS_ITALIC_LOWER     <- 0x1D622L
.SANS_BI_UPPER         <- 0x1D63CL
.SANS_BI_LOWER         <- 0x1D656L
.MONO_UPPER            <- 0x1D670L
.MONO_LOWER            <- 0x1D68AL
.MONO_DIGIT            <- 0x1D7F6L
.COMBINING_UNDERLINE   <- 0x0332L
.COMBINING_STRIKETHROUGH <- 0x0336L
.NESTED_BULLET_MIN_INDENT <- 2L

# ── Unicode Mapping Functions ─────────────────────────────────────────────────

#' Map ASCII codepoints to a Unicode mathematical block.
#'
#' Shared helper used by all style functions. Replaces A-Z, a-z, and
#' optionally 0-9 with their offset equivalents. All other codepoints
#' pass through unchanged.
#'
#' @param text      Character string to convert.
#' @param upper     Codepoint base for uppercase letters.
#' @param lower     Codepoint base for lowercase letters.
#' @param digit     Codepoint base for digits, or NA to skip digits.
#' @return Converted character string.
.map_codepoints <- function(text, upper, lower, digit = NA_integer_) {
  if (!nzchar(text)) return("")
  cps <- utf8ToInt(text)
  out <- integer(length(cps))
  for (i in seq_along(cps)) {
    cp <- cps[i]
    if (cp >= 65L && cp <= 90L) {
      out[i] <- upper + cp - 65L
    } else if (cp >= 97L && cp <= 122L) {
      out[i] <- lower + cp - 97L
    } else if (!is.na(digit) && cp >= 48L && cp <= 57L) {
      out[i] <- digit + cp - 48L
    } else {
      out[i] <- cp
    }
  }
  intToUtf8(out)
}

#' Convert text to Unicode Mathematical Sans-Serif Bold.
#'
#' Maps ASCII letters and digits to bold sans-serif equivalents.
#' Non-ASCII and punctuation pass through unchanged.
#'
#' @param text Character string.
#' @return Bold-styled string.
#' @examples
#' to_sans_bold("Hello 123") # => "𝗛𝗲𝗹𝗹𝗼 𝟭𝟮𝟯"
to_sans_bold <- function(text) {
  .map_codepoints(text, .SANS_BOLD_UPPER, .SANS_BOLD_LOWER, .SANS_BOLD_DIGIT)
}

#' Convert text to Unicode Mathematical Sans-Serif Italic.
#'
#' Maps ASCII letters only (no italic digits exist in Unicode).
#'
#' @param text Character string.
#' @return Italic-styled string.
to_sans_italic <- function(text) {
  .map_codepoints(text, .SANS_ITALIC_UPPER, .SANS_ITALIC_LOWER)
}

#' Convert text to Unicode Mathematical Sans-Serif Bold Italic.
#'
#' Maps ASCII letters only.
#'
#' @param text Character string.
#' @return Bold-italic-styled string.
to_sans_bold_italic <- function(text) {
  .map_codepoints(text, .SANS_BI_UPPER, .SANS_BI_LOWER)
}

#' Convert text to Unicode Mathematical Monospace.
#'
#' Maps ASCII letters and digits to monospace equivalents.
#'
#' @param text Character string.
#' @return Monospace-styled string.
to_monospace <- function(text) {
  .map_codepoints(text, .MONO_UPPER, .MONO_LOWER, .MONO_DIGIT)
}

#' Apply combining underline (U+0332) to every character.
#'
#' @param text Character string.
#' @return Underlined string using combining characters.
to_underline <- function(text) {
  if (!nzchar(text)) return("")
  chars <- strsplit(text, "")[[1]]
  paste0(chars, intToUtf8(.COMBINING_UNDERLINE), collapse = "")
}

#' Apply combining strikethrough (U+0336) to every character.
#'
#' @param text Character string.
#' @return Strikethrough string using combining characters.
to_strikethrough <- function(text) {
  if (!nzchar(text)) return("")
  chars <- strsplit(text, "")[[1]]
  paste0(chars, intToUtf8(.COMBINING_STRIKETHROUGH), collapse = "")
}

#' Dispatch to a style function by name.
#'
#' @param text  Character string.
#' @param style One of "bold", "italic", "bold_italic".
#' @return Styled string.
apply_style <- function(text, style) {
  switch(style,
    bold        = to_sans_bold(text),
    italic      = to_sans_italic(text),
    bold_italic = to_sans_bold_italic(text),
    stop(sprintf("Unknown style '%s'. Expected 'bold', 'italic', or 'bold_italic'.", style))
  )
}


# ── Internal Helpers ──────────────────────────────────────────────────────────

#' Replace regex matches using a function (like Python's re.sub with a callable).
#'
#' Iteratively finds the first match, calls fn(full_match, capture_groups),
#' and splices the return value in by position. Repeats until no matches remain.
#'
#' @param pattern Perl-compatible regex pattern.
#' @param fn      Function(full_match, groups) -> replacement string.
#' @param text    Character string to process.
#' @return Modified string.
.gsub_fn <- function(pattern, fn, text) {
  repeat {
    m <- regexec(pattern, text, perl = TRUE)[[1L]]
    if (m[1L] == -1L) break

    ml   <- attr(m, "match.length")
    start <- m[1L]
    end   <- start + ml[1L] - 1L
    full  <- substring(text, start, end)

    groups <- character(0)
    if (length(m) > 1L) {
      for (j in 2:length(m)) {
        gs <- m[j]; gl <- ml[j]
        groups <- c(groups,
          if (gs > 0L) substring(text, gs, gs + gl - 1L) else NA_character_
        )
      }
    }

    repl   <- fn(full, groups)
    before <- if (start > 1L) substring(text, 1L, start - 1L) else ""
    after  <- if (end < nchar(text)) substring(text, end + 1L) else ""
    text   <- paste0(before, repl, after)
  }
  text
}


# ── Pipeline Steps ────────────────────────────────────────────────────────────

#' Normalize \\r\\n and \\r line endings to \\n.
.normalize_line_endings <- function(text) {
  text <- gsub("\r\n", "\n", text, fixed = TRUE)
  gsub("\r", "\n", text, fixed = TRUE)
}

#' Replace code spans and fenced blocks with unique placeholders.
#'
#' Returns list(text, placeholders) where placeholders is a named list
#' mapping placeholder keys to original code strings.
.protect_code <- function(text) {
  env <- new.env(parent = emptyenv())
  env$placeholders <- list()
  env$n <- 0L

  make_ph <- function(original) {
    env$n <- env$n + 1L
    key <- sprintf("\uFFFFCODE%06d\uFFFF", env$n)
    env$placeholders[[key]] <- original
    key
  }

  # Fenced code blocks (``` or ~~~, with optional language tag)
  text <- .gsub_fn("```[\\s\\S]*?```|~~~[\\s\\S]*?~~~", function(full, g) make_ph(full), text)
  # Inline code spans
  text <- .gsub_fn("`[^`\\n]+`", function(full, g) make_ph(full), text)

  list(text = text, placeholders = env$placeholders)
}

#' Restore code placeholders to original content.
#'
#' @param text        Text with placeholders.
#' @param placeholders Named list from .protect_code().
#' @param monospace   If TRUE, apply to_monospace() to code content.
.restore_code <- function(text, placeholders, monospace = FALSE) {
  for (key in names(placeholders)) {
    orig <- placeholders[[key]]
    is_fenced <- startsWith(orig, "```") || startsWith(orig, "~~~")

    if (is_fenced) {
      if (monospace) {
        fence <- substring(orig, 1L, 3L)
        rest  <- substring(orig, 4L)
        body  <- sub(paste0("\\Q", fence, "\\E\\s*$"), "", rest, perl = TRUE)
        first_nl <- regexpr("\n", body, fixed = TRUE)
        content  <- if (first_nl > 0L) substring(body, first_nl + 1L) else ""
        text <- gsub(key, to_monospace(content), text, fixed = TRUE)
      } else {
        text <- gsub(key, orig, text, fixed = TRUE)
      }
    } else if (monospace) {
      inner <- substring(orig, 2L, nchar(orig) - 1L)
      text  <- gsub(key, to_monospace(inner), text, fixed = TRUE)
    } else {
      inner <- substring(orig, 2L, nchar(orig) - 1L)
      text  <- gsub(key, inner, text, fixed = TRUE)
    }
  }
  text
}

#' Remove <span ...>...</span> wrappers, keeping inner text.
.strip_html_spans <- function(text) {
  prev <- NULL
  while (!identical(prev, text)) {
    prev <- text
    text <- gsub("<span[^>]*>(.*?)</span>", "\\1", text, perl = TRUE)
  }
  text
}

#' Convert <u>text</u> to underlined Unicode using combining characters.
.convert_underline <- function(text) {
  .gsub_fn("<u>(.+?)</u>", function(full, groups) {
    to_underline(groups[1])
  }, text)
}

#' Convert ~~text~~ to strikethrough Unicode using combining characters.
.convert_strikethrough <- function(text) {
  .gsub_fn("(?<!\\\\)~~(.+?)(?<!\\\\)~~", function(full, groups) {
    to_strikethrough(groups[1])
  }, text)
}

#' Replace ***text*** and ___text___ with bold-italic Unicode.
.convert_bold_italic <- function(text) {
  text <- .gsub_fn("(?<!\\\\)\\*{3}(.+?)(?<!\\\\)\\*{3}", function(f, g) to_sans_bold_italic(g[1]), text)
  .gsub_fn("(?<!\\\\)_{3}(.+?)(?<!\\\\)_{3}", function(f, g) to_sans_bold_italic(g[1]), text)
}

#' Replace **text** and __text__ with bold Unicode.
.convert_bold <- function(text) {
  text <- .gsub_fn("(?<!\\\\)\\*{2}(.+?)(?<!\\\\)\\*{2}", function(f, g) to_sans_bold(g[1]), text)
  .gsub_fn("(?<!\\\\)__(.+?)(?<!\\\\)__", function(f, g) to_sans_bold(g[1]), text)
}

#' Replace *text* and _text_ with italic Unicode.
.convert_italic <- function(text) {
  text <- .gsub_fn("(?<!\\\\)(?<!\\*)\\*(?!\\*)(.+?)(?<!\\\\)(?<!\\*)\\*(?!\\*)",
                    function(f, g) to_sans_italic(g[1]), text)
  .gsub_fn("(?<!\\w)(?<!\\\\)_(?!_)(.+?)(?<!\\\\)(?<!_)_(?!\\w)",
           function(f, g) to_sans_italic(g[1]), text)
}

#' Convert ATX and setext headers to styled plain text.
#'
#' H1 gets bold + upper-case + ━ border. H2-H6 get bold only.
.convert_headers <- function(text) {
  sep <- paste0(rep("\u2501", 40), collapse = "")
  lines <- strsplit(text, "\n", fixed = TRUE)[[1]]
  out <- character(0)
  i <- 1L
  n <- length(lines)

  while (i <= n) {
    line <- lines[i]

    # ATX headers
    atx <- regexec("^(#{1,6})\\s+(.*)", line, perl = TRUE)[[1]]
    if (atx[1] != -1L) {
      ml    <- attr(atx, "match.length")
      level <- ml[2]  # length of the # run
      title <- substring(line, atx[3], atx[3] + ml[3] - 1L)
      title <- trimws(title)
      if (level == 1L) {
        out <- c(out, paste0("\n", sep, "\n", to_sans_bold(toupper(title)), "\n", sep, "\n"))
      } else {
        out <- c(out, to_sans_bold(title))
      }
      i <- i + 1L
      next
    }

    # Setext headers
    if (i + 1L <= n) {
      next_line <- lines[i + 1L]
      if (grepl("^={3,}\\s*$", next_line, perl = TRUE)) {
        out <- c(out, paste0("\n", sep, "\n", to_sans_bold(toupper(trimws(line))), "\n", sep, "\n"))
        i <- i + 2L
        next
      }
      if (grepl("^-{3,}\\s*$", next_line, perl = TRUE) && nzchar(trimws(line))) {
        out <- c(out, to_sans_bold(trimws(line)))
        i <- i + 2L
        next
      }
    }

    # Standalone horizontal rules
    if (grepl("^(-{3,}|_{3,}|\\*{3,})\\s*$", line, perl = TRUE)) {
      i <- i + 1L
      next
    }

    out <- c(out, line)
    i <- i + 1L
  }
  paste0(out, collapse = "\n")
}

#' Handle Markdown links.
#'
#' By default strips to display text. When preserve=TRUE, keeps original syntax.
.strip_links <- function(text, preserve = FALSE) {
  if (preserve) return(text)
  text <- gsub("\\[\\]\\([^)]*\\)", "", text, perl = TRUE)
  text <- gsub("\\[([^\\]]+)\\]\\([^)]*\\)", "\\1", text, perl = TRUE)
  text <- gsub("\\[([^\\]]+)\\]\\[[^\\]]*\\]", "\\1", text, perl = TRUE)
  gsub("<(https?://[^>]+)>", "\\1", text, perl = TRUE)
}

#' Replace Markdown images with alt text.
.strip_images <- function(text) {
  gsub("!\\[([^\\]]*)\\]\\([^)]*\\)", "\\1", text, perl = TRUE)
}

#' Replace Markdown list markers with Unicode bullets.
.convert_bullets <- function(text) {
  lines <- strsplit(text, "\n", fixed = TRUE)[[1]]
  lines <- vapply(lines, function(line) {
    m <- regexec("^(\\s*)[-*+] ", line, perl = TRUE)[[1]]
    if (m[1] == -1L) return(line)
    ml <- attr(m, "match.length")
    indent_len <- ml[2]
    rest <- substring(line, m[1] + ml[1])
    bullet <- if (indent_len >= .NESTED_BULLET_MIN_INDENT) "  \u2023 " else "\u2022 "
    paste0(bullet, rest)
  }, character(1), USE.NAMES = FALSE)
  paste0(lines, collapse = "\n")
}

#' Remove leading > blockquote markers.
.strip_blockquotes <- function(text) {
  gsub("^> ?", "", text, perl = TRUE)
}

#' Decode common HTML entities to literal characters.
.clean_entities <- function(text) {
  entities <- c("&gt;" = ">", "&lt;" = "<", "&amp;" = "&",
                "&nbsp;" = " ", "&quot;" = '"', "&apos;" = "'")
  for (ent in names(entities)) {
    text <- gsub(ent, entities[[ent]], text, fixed = TRUE)
  }
  text
}

#' Remove Markdown backslash escapes (e.g. \\* -> *).
.clean_escaped_chars <- function(text) {
  gsub("\\\\([\\\\`*_{}\\[\\]()#+\\-.!~])", "\\1", text, perl = TRUE)
}

#' Collapse excessive blank lines and trim whitespace.
.normalize_whitespace <- function(text) {
  text <- gsub("\n{3,}", "\n\n", text, perl = TRUE)
  paste0(trimws(text), "\n")
}


# ── Public API ────────────────────────────────────────────────────────────────

#' Convert Markdown text to LinkedIn-compatible Unicode plain text.
#'
#' Processes bold, italic, bold-italic, underline (<u>), strikethrough (~~),
#' headers, code, links, images, bullets, blockquotes, and HTML entities.
#'
#' @param text           Markdown source string.
#' @param preserve_links If TRUE, keep link syntax unchanged.
#' @param monospace_code If TRUE (default), render code in Unicode monospace.
#' @return Plain-text string ready for LinkedIn.
#' @examples
#' convert("**Hello**, *world*!")
#' # => "𝗛𝗲𝗹𝗹𝗼, 𝘸𝘰𝘳𝘭𝘥!\n"
convert <- function(text, preserve_links = FALSE, monospace_code = TRUE) {
  if (!nzchar(trimws(text %||% ""))) return("")

  text <- .normalize_line_endings(text)
  code <- .protect_code(text)
  text <- code$text
  placeholders <- code$placeholders

  text <- .strip_html_spans(text)
  text <- .strip_images(text)
  text <- .convert_underline(text)
  text <- .convert_strikethrough(text)
  text <- .convert_bold_italic(text)
  text <- .convert_bold(text)
  text <- .convert_italic(text)
  text <- .convert_headers(text)
  text <- .strip_links(text, preserve = preserve_links)
  text <- .convert_bullets(text)
  text <- .strip_blockquotes(text)
  text <- .restore_code(text, placeholders, monospace = monospace_code)
  text <- .clean_entities(text)
  text <- .clean_escaped_chars(text)
  .normalize_whitespace(text)
}

#' Convert a Markdown file and write the result to a .txt file.
#'
#' @param input_path     Path to the .md source file.
#' @param output_path    Destination path (default: input with .linkedin.txt extension).
#' @param preserve_links Passed to convert().
#' @param monospace_code Passed to convert().
#' @return The output file path (invisibly).
convert_file <- function(input_path, output_path = NULL, preserve_links = FALSE, monospace_code = TRUE) {
  if (!file.exists(input_path)) {
    stop(sprintf("Input file not found: %s", input_path))
  }
  if (is.null(output_path)) {
    output_path <- sub("\\.[^.]+$", ".linkedin.txt", input_path)
  }
  md_text <- paste(readLines(input_path, encoding = "UTF-8", warn = FALSE), collapse = "\n")
  result  <- convert(md_text, preserve_links = preserve_links, monospace_code = monospace_code)
  writeLines(result, output_path, useBytes = TRUE)
  message(sprintf("LinkedIn-formatted text written to: %s", output_path))
  invisible(output_path)
}

