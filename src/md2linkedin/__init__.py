"""md2linkedin — Convert Markdown to LinkedIn-friendly Unicode text.

The package exposes two main entry points:

* :func:`convert` — convert a Markdown *string* in memory.
* :func:`convert_file` — read a ``.md`` file, convert it, and write a
  ``.linkedin.txt`` output file.

Lower-level Unicode mapping utilities (:func:`to_sans_bold`,
:func:`to_sans_italic`, :func:`to_sans_bold_italic`, :func:`apply_style`)
are also public for programmatic use.
"""

from __future__ import annotations

from importlib.metadata import version

from ._converter import convert, convert_file
from ._unicode import (
    apply_style,
    to_monospace,
    to_sans_bold,
    to_sans_bold_italic,
    to_sans_italic,
)

__version__ = version("md2linkedin")

__all__ = [
    "__version__",
    "apply_style",
    "convert",
    "convert_file",
    "to_monospace",
    "to_sans_bold",
    "to_sans_bold_italic",
    "to_sans_italic",
]
