"""
Python API documentation extraction and browsing.

This package extracts information about objects in Python source code, such
as classes and functions.  This information is represented as a JSON
document, which can be served to a web API for browsing.

Finding modules
---------------

Use `apidoc.modules` to obtain information about modules in a package
hierarchy.  

  >>> import apidoc.modules
  >>> names = apidoc.modules.find_modules(path)

The `find_modules()` function generates the list of /fully-qualified module
names/ below `path`, which is assumed to be at the top level of the
`PYTHONPATH`.

"""
