import sys

from   . import inspector
from   . import text

#-------------------------------------------------------------------------------

def supdoc(obj):
    docsrc = inspector.DocSource()
    objdoc = docsrc._DocSource__inspector._inspect(obj)
    import json
    json.dump(objdoc, sys.stderr, indent=2)
    print(file=sys.stderr)
    text.print_docs(docsrc, objdoc)



