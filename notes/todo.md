- [x] remove actual source from `_get_source`
- [x] recast `Docsrc` → cached `Inspector`
- [x] clean up `.format`
- [x] make `--no-source` work
- [x] fix `supdoc supdoc.test.C`
- [ ] fix `supdoc pandas.DataFrame.align`
- [ ] cache on `id(obj)`
- [ ] remove `supdoc-inspect`
- [ ] add + document CLI for precaching objdocs
- [ ] improve on `_get_source`, particularly `inspect.getsourcelines`
- [ ] don't parse/convert doc text when inspecting, but rather later


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


