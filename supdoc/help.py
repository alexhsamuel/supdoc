import json
import sys

from   . import terminal
from   .inspector import Inspector

__all__ = (
    "dump_objdoc",
    "help", 
)

#-------------------------------------------------------------------------------

# FIXME: Use the cache directory, for installed stuff.

def dump_objdoc(obj):
    """
    Dumps JSON documentation extracted from `obj`.
    """
    inspector = Inspector()
    objdoc = inspector.inspect(obj)

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
    inspector = Inspector()
    objdoc = inspector.inspect(obj)

    print()
    terminal.print_docs(inspector, objdoc, private=private, imports=imports)


