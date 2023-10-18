- only classes may have methods; other types have attributes only
- sort members better: special, then regular, then private
- inspect bound methods
- show umnagled name only if parent name in MRO?
- better support for inspecting objects
- handle `__future__` annotations
- pager support
- moving unmangling into inspector?
- color themes (dark & light)
- cache stuff under `sys.prefix` for `help()`
- cache on `id(obj)`
- remove `supdoc-inspect`
- add + document CLI for precaching objdocs
- improve on `_get_source`, particularly `inspect.getsourcelines`
- don't parse/convert doc text when inspecting, but rather later


# Transforming docstrings

The current design is that we convert markdown to HTML, including processing
embedded source with pygments.  For terminal output, we have special logic to
(attempt to) render HTML approximately with ANSI escapes.  HTML is effectively
th interchange format.

Alternate designs:

- Leave Markdown as the interchange format.  Convert Markdown to HTML (including
  syntax highlighting) in the web browser.  Convert Markdown to ANSI in the
  terminal output code.
  
- Convert Markdown to HTML in the objdoc in the web service (or HTML generation)
  code before sending (or writing).
  
Keep in mind we want to support ReST and potentially other formats as well as
Markdown.


