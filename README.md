'supdoc
=======

'supdoc is a browser for API documentation automatically extracted from Python
source code.  Docstrings are among my favorite Python features, because they
keep the documentation close to the code.  This tool aims to extract code
structure and docstrings, to parse and interpret the latter, and to present it
in a modern web UI.

Sphinx, the leading Python documentation tool, is great for hand-written
documentation, but I find that in many projects, writing manuals is just too low
a priority to get done ever.  Docstrings, however, are cheap to write, and
further can contain doctests, simple code snippets that can serve both as unit
tests and code samples.  Epydoc is the best docstring-focused documentation I
know of, but is old and no longer maintained.

Finally, in this web-focused day and age, I think an API documentation system
should be constructed in modular and service-oriented way.

1. A documentation extract library.  This may be run in batch mode, for
instance, as part of a build process, or just in time, in response to
documentation queries.

2. A library for interpreting as many types and variants of documentation markup
as possible (incuding <i>ad hoc</i> markup) and interpreting it in the context
of code.  For instance, documentation of function parameters should be
associated with the parameters themselves.

3. A JSON-based format for representing the API documentation for a code
module.  

4. A dynamic web UI for browsing the API documentation, responsible for
presentation aspects.

