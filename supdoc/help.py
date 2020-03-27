import json
import sys

from   . import terminal
from   .inspector import get_docsrc

__all__ = (
    "dump_objdoc",
    "help", 
)

#-------------------------------------------------------------------------------

def dump_objdoc(obj):
    """
    Dumps JSON documentation extracted from `obj`.
    """
    docsrc = get_docsrc()
    # FIXME: For shame.
    objdoc = docsrc._DocSource__inspector._inspect(obj)

    json.dump(objdoc, sys.stdout, indent=1, sort_keys=True)
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
    docsrc = get_docsrc()
    # FIXME: For shame.
    objdoc = docsrc._DocSource__inspector._inspect(obj)

    print()
    terminal.print_docs(docsrc, objdoc, private=private, imports=imports)


