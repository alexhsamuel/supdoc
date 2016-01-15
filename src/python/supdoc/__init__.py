import json as _json
import sys

from   . import inspector
from   . import text
import pln.terminal
import pln.terminal.printer

#-------------------------------------------------------------------------------

def supdoc(obj, *, json=False):
    docsrc = inspector.DocSource()
    objdoc = docsrc._DocSource__inspector._inspect(obj)

    if json:
        _json.dump(objdoc, sys.stdout, indent=2)
        print()
    else:
        width = pln.terminal.get_width() - 1 
        printer = pln.terminal.printer.Printer(indent=" ", width=width)
        text.print_docs(docsrc, objdoc, printer=printer)



