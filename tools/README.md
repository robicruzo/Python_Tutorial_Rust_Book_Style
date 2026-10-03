# Rebuilding the tutorial chapters

The tutorial chapters in `src/` (everything except the Fluent Python chapters)
were generated from the official reStructuredText sources of the Python 3.15
tutorial (`Doc/tutorial/*.rst` in the CPython repository):

1. `sphinx-build -b markdown` with `sphinx_conf.py` as `conf.py`
   (needs `pip install sphinx sphinx-markdown-builder`), which resolves
   cross-references and links the rest of the Python docs to docs.python.org;
2. `python3 convert_tutorial.py <sphinx-md-out> <rst-dir> ../src`, which removes the
   `>>>`/`...` prompts, turns interpreter output into `#` comments, and picks the
   language for syntax highlighting.

The Fluent Python chapters are hand-written Markdown and are not touched by
these scripts. Build the book with `mdbook build` (output goes to `book/`) or
preview it live with `mdbook serve --open`.
