import json as _json
import sys

from   . import inspector
from   . import terminal
from   pln.memo import memoize
import pln.terminal
from   pln.terminal.printer import Printer

__all__ = (
    "supdoc", 
    )

#-------------------------------------------------------------------------------

@memoize
def _get_docsrc():
    return inspector.DocSource()


def supdoc(obj, *, json=False):
    """
    Prints documentation for `obj`.

    Inspects `obj` for documentation and formats it for the terminal.  If 
    `json` is true, dumps the JSON representation of the documentation instead.
    """
    docsrc = _get_docsrc()
    # FIXME: For shame.
    objdoc = docsrc._DocSource__inspector._inspect(obj)

    if json:
        _json.dump(objdoc, sys.stdout, indent=2)
        print()
    else:
        terminal.print_docs(docsrc, objdoc)



