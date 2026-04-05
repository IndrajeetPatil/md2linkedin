


# md2linkedin <img src="https://raw.githubusercontent.com/IndrajeetPatil/md2linkedin/main/docs/assets/logo.png" align="right" width="240" />

[![PyPI
version](https://img.shields.io/pypi/v/md2linkedin.png)](https://pypi.org/project/md2linkedin/)
![Python versions](https://img.shields.io/pypi/pyversions/md2linkedin.png)
[![PyPI
Downloads](https://img.shields.io/pypi/dm/md2linkedin.png)](https://pypistats.org/packages/md2linkedin)

`md2linkedin` converts Markdown text to LinkedIn-compatible plain text by
replacing bold, italic, and bold-italic markers with Unicode Mathematical
Sans-Serif characters. This preserves visual formatting when pasting into
platforms like LinkedIn that do not support Markdown natively.

## Installation

| Package Manager | Installation Command      |
|-----------------|---------------------------|
| pip             | `pip install md2linkedin` |
| uv              | `uv add md2linkedin`      |

## Usage

### Python API

``` python
# @pyodide
from md2linkedin import convert

md = """
# Exciting News

I'm thrilled to share that **we just launched** a new product!

Key highlights:

- **Performance**: *3x faster* than the previous version
- **Reliability**: ***zero downtime*** deployments
- **Developer UX**: clean, intuitive API

Check it out and let me know what you think.
"""

print(convert(md))
```

    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    𝗘𝗫𝗖𝗜𝗧𝗜𝗡𝗚 𝗡𝗘𝗪𝗦
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    𝘐'𝘮 𝘵𝘩𝘳𝘪𝘭𝘭𝘦𝘥 𝘵𝘰 𝘴𝘩𝘢𝘳𝘦 𝘵𝘩𝘢𝘵 𝗿𝗲 𝗷𝘂𝘀𝘁 𝗹𝗮𝘂𝗻𝗰𝗵𝗲𝗱 a new product!
    
    Key highlights:
    
    • 𝗣𝗲𝗿𝗳𝗼𝗿𝗺𝗮𝗻𝗰𝗲: 𝘴𝘱𝘦𝘦𝘥 is faster than the previous version
    • 𝗥𝗲𝗹𝗶𝗮𝗯𝗶𝗹𝗶𝘁𝘆: 𝙯𝙚𝙧𝙤 𝙙𝙤𝙬𝙣𝙩𝙞𝙢𝙚 deployments
    • 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿 𝗨𝗫: clean, intuitive API
    
    Check it out and let me know what you think.

### CLI

``` bash
# Convert a Markdown file (output: post.linkedin.txt)
md2linkedin post.md

# Specify output path
md2linkedin post.md -o linkedin_post.txt

# Pipe from stdin
echo "**Hello**, *world*!" | md2linkedin

# Keep link URLs in the output
md2linkedin post.md --preserve-links
```

## Key Features

- **Bold**: `**text**` or `__text__` → Unicode Sans-Serif Bold (𝗯𝗼𝗹𝗱)
- **Italic**: `*text*` or `_text_` → Unicode Sans-Serif Italic (𝘪𝘵𝘢𝘭𝘪𝘤)
- **Bold-italic**: `***text***` or `___text___` → Unicode Sans-Serif Bold
  Italic (𝙗𝙤𝙡𝙙-𝙞𝙩𝙖𝙡𝙞𝙘)
- **Headers**: `#`/`##`/etc. styled with bold Unicode; H1 gets a `━` border
- **Code spans**: backticks stripped, content kept as plain text — *never*
  Unicode-transformed
- **Fenced code blocks**: preserved verbatim
- **Links**: stripped to display text by default; `--preserve-links` retains
  URLs
- **Images**: replaced by alt text
- **Bullet lists**: `-`/`*`/`+` → `•`; nested items → `‣`
- **Blockquotes**: leading `>` stripped
- **HTML spans**: unwrapped, inner text preserved
- **HTML entities**: decoded (`&amp;` → `&`, etc.)
- **Backslash escapes**: resolved (`\*` → `*`)
- **Windows line endings**: normalised automatically
- **Emojis & non-ASCII**: pass through unchanged — no accidental corruption

For more examples, check out the package documentation at:
<https://www.indrapatil.com/md2linkedin/>

## License

This project is licensed under the MIT License.

## Code of Conduct

Please note that the md2linkedin project is released with a [Contributor
Code of
Conduct](https://www.contributor-covenant.org/version/3/0/code_of_conduct/).
By contributing to this project, you agree to abide by its terms.

## Acknowledgements

Hex sticker font is `Rubik`. Icons are sourced from
[Flaticon](https://www.flaticon.com/):

- Markdown icon by [Freepik](https://www.flaticon.com/authors/freepik)
- LinkedIn icon by [Freepik](https://www.flaticon.com/authors/freepik)
- Arrow/conversion icon by
  [Freepik](https://www.flaticon.com/authors/freepik)
