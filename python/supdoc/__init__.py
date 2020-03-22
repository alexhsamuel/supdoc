import sys

from   . import inspector
from   . import terminal
import aslib.json
from   aslib.memo import memoize
import aslib.terminal
from   aslib.terminal.printer import Printer

__all__ = (
    "dump_objdoc",
    "help", 
    )

#-------------------------------------------------------------------------------

@memoize
def _get_docsrc():
    return inspector.DocSource()


def dump_objdoc(obj):
    """
    Dumps JSON documentation extracted from `obj`.
    """
    docsrc = _get_docsrc()
    # FIXME: For shame.
    objdoc = docsrc._DocSource__inspector._inspect(obj)

    aslib.json.pprint(objdoc)
    print()


def help(obj, *, private=False, imports=False):
    """
    Prints documentation for `obj`.

    Inspects `obj` for documentation and formats it for the terminal.  

    @param private
      If true, includes private/internal names.
    @param imports
      If true, includes imported names.
    """
    docsrc = _get_docsrc()
    # FIXME: For shame.
    objdoc = docsrc._DocSource__inspector._inspect(obj)

    print()
    terminal.print_docs(docsrc, objdoc, private=private, imports=imports)

