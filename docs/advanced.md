# Advanced Usage

## Programmatic Use

### Converting Strings in Memory

The simplest entry point is `convert()`, which accepts a Markdown string and
returns a plain-text string ready for LinkedIn:

```python
from md2linkedin import convert

result = convert("**Hello**, *world*!")
print(result)  # 𝗛𝗲𝗹𝗹𝗼, 𝘸𝘰𝘳𝘭𝘥!
```

### Converting Files

Use `convert_file()` to read a `.md` file and write the output to a `.txt`
file. The function returns the `Path` of the written file so you can chain
further operations:

```python
from md2linkedin import convert_file

out = convert_file("post.md")
print(f"Written to: {out}")  # post.linkedin.txt

# Override the output path
out = convert_file("post.md", "my_post.txt")
```

### Preserving Links

By default, Markdown link syntax is stripped to display text only
(`[GitHub](https://github.com)` → `GitHub`). Pass `preserve_links=True` to
retain the full link syntax:

```python
result = convert("[GitHub](https://github.com)", preserve_links=True)
# [GitHub](https://github.com)

result = convert_file("post.md", preserve_links=True)
```

### Direct Unicode Mapping

The Unicode mapping functions are public and useful for applying a specific
style to a plain string programmatically:

```python
from md2linkedin import (
    to_sans_bold,
    to_sans_italic,
    to_sans_bold_italic,
    to_monospace,
    apply_style,
)

to_sans_bold("Open to Work")  # 𝗢𝗽𝗲𝗻 𝘁𝗼 𝗪𝗼𝗿𝗸
to_sans_italic("3 years of exp")  # 3 𝘺𝘦𝘢𝘳𝘴 𝘰𝘧 𝘦𝘹𝘱
to_sans_bold_italic("Key insight")  # 𝙆𝙚𝙮 𝙞𝙣𝙨𝙞𝙜𝙝𝙩
to_monospace("print('hi')")  # 𝚙𝚛𝚒𝚗𝚝('𝚑𝚒')

# Dynamic dispatch
apply_style("Hiring!", "bold")
```

---

## What Gets Transformed (and What Doesn't)

| Markdown construct | Output |
|--------------------|--------|
| `**bold**` / `__bold__` | Unicode 𝗯𝗼𝗹𝗱 |
| `*italic*` / `_italic_` | Unicode 𝘪𝘵𝘢𝘭𝘪𝘤 |
| `***bold-italic***` / `___bold-italic___` | Unicode 𝙗𝙤𝙡𝙙-𝙞𝙩𝙖𝙡𝙞𝙘 |
| `` `inline code` `` | Unicode 𝚖𝚘𝚗𝚘𝚜𝚙𝚊𝚌𝚎 (backticks stripped) |
| ` ```fenced block``` ` | Unicode 𝚖𝚘𝚗𝚘𝚜𝚙𝚊𝚌𝚎 (fences stripped) |
| `# H1` | Bold Unicode + `━` border |
| `## H2`–`###### H6` | Bold Unicode, no border |
| `[text](url)` | `text` (URL discarded) |
| `![alt](url)` | `alt` text (URL discarded) |
| `- item` | `• item` |
| `  - nested` | `  ‣ nested` |
| `> blockquote` | `> ` prefix removed |
| `<span>...</span>` | Tags removed, text kept |
| `&amp;` / `&gt;` etc. | Decoded to `&` / `>` |
| `\*` backslash escapes | Resolved to literal `*` |
| Emojis, accented chars | Passed through unchanged |
| Digits inside bold | Also converted (`**123**` → `𝟭𝟮𝟯`) |
| `_snake_case_` in middle of word | **Not** italicised |

---

## Handling Edge Cases

### Nested Formatting

`md2linkedin` handles nesting by processing bold-italic (`***`) first,
ensuring it is not accidentally consumed piecemeal:

```python
convert("***very important***")  # → bold-italic Unicode
convert("**bold and *italic* inside**")  # → bold wrapping italic
```

### Code Is Rendered in Monospace

By default, inline code and fenced code blocks are converted to Unicode
Mathematical Monospace characters. Only ASCII letters and digits are mapped;
all other characters (including Markdown syntax like `**`) pass through
unchanged — no nested processing is performed:

```python
convert("Use `**bold**` in Markdown")
# → Use **𝚋𝚘𝚕𝚍** in Markdown   (backticks stripped, letters monospaced, ** kept)

convert("```\nprint('hi')\n```")
# → 𝚙𝚛𝚒𝚗𝚝('𝚑𝚒')   (fences stripped, content monospaced)
```

To disable monospace rendering and restore the previous plain-text behavior:

```python
convert("Use `**bold**` in Markdown", monospace_code=False)
# → Use **bold** in Markdown   (backticks stripped, content as plain text)

convert("```\n**not bold**\n```", monospace_code=False)
# → ```\n**not bold**\n```     (fenced block fully preserved)
```

### Underscore Italic vs. Snake Case

Single underscores are italicised only when they sit at word boundaries:

```python
convert("_italic_")  # → italic Unicode
convert("snake_case_variable")  # → unchanged
```

### Unmatched / Orphaned Markers

Unmatched asterisks or underscores are left untouched — `md2linkedin` never
crashes on malformed input:

```python
convert("price: $10 * 3")  # → price: $10 * 3 (no crash)
convert("under_score alone")  # → unchanged
```

### Large Documents

`convert()` is a pure-Python, single-pass function with no I/O. It scales
linearly with input length and is safe to call in hot paths or on large files:

```python
big_md = Path("quarterly_report.md").read_text()
result = convert(big_md)
```

### Emojis and Non-ASCII Characters

Emojis and accented characters pass through unchanged — only ASCII letters
and digits are remapped to Unicode Mathematical variants:

```python
from md2linkedin import convert

result = convert("**Excited to share** 🎉 *check this out*!")
print(result)  # 𝗘𝘅𝗰𝗶𝘁𝗲𝗱 𝘁𝗼 𝘀𝗵𝗮𝗿𝗲 🎉 𝘤𝘩𝘦𝘤𝘬 𝘵𝘩𝘪𝘴 𝘰𝘂𝘵!
```

---

## Running Without Installing (uvx)

If you only need `md2linkedin` occasionally, you can run it directly with
[`uvx`](https://docs.astral.sh/uv/guides/tools/) without a permanent
installation:

```bash
# Convert a Markdown file (output: post.linkedin.txt)
uvx md2linkedin post.md

# Pipe from stdin
echo "**bold** and *italic*" | uvx md2linkedin

# Preserve link syntax
uvx md2linkedin --preserve-links post.md

# Explicit output path
uvx md2linkedin post.md -o linkedin_post.txt

# Disable monospace code rendering
uvx md2linkedin --no-monospace-code post.md
```

`uvx` downloads and caches the package in an isolated environment, so
subsequent runs are fast.

---

## Integration with Pandoc (LaTeX → LinkedIn)

If you write in LaTeX (e.g. a résumé), you can pipe through `pandoc` first:

```bash
pandoc --from=latex --to=markdown_strict --wrap=none resume.tex | md2linkedin
```

Or in Python:

```python
import subprocess
from md2linkedin import convert

result = subprocess.run(
    ["pandoc", "--from=latex", "--to=markdown_strict", "--wrap=none"],
    input=Path("resume.tex").read_text(),
    capture_output=True,
    text=True,
    check=True,
)
linkedin_text = convert(result.stdout)
```

---

## CLI Reference

```
Usage: md2linkedin [OPTIONS] [INPUT_FILE]

  Convert Markdown to LinkedIn-friendly Unicode text.

Options:
  -o, --output PATH    Output file path.
  --preserve-links     Keep link syntax in output.
  --no-monospace-code  Disable monospace Unicode rendering for code.
  -V, --version        Show the version and exit.
  -h, --help           Show this message and exit.
```
