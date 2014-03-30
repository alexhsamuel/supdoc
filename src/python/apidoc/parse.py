import re
import sys

from   . import htmlgen
from   .htmlgen import *

#-------------------------------------------------------------------------------

_SPACES = re.compile(" *")

def get_indent(line):
    match = _SPACES.match(line)
    return 0 if match is None else match.span()[1]


def get_common_indent(lines):
    return min( get_indent(l) for l in lines if l.strip() != "" )


def remove_indent(lines):
    lines = list(lines)
    indent = get_common_indent(lines)
    return ( l if l.strip() == "" else l[indent :] for l in lines )


# FIXME: Gather indent on a paragraph basis.

def join_pars(lines):
    par = None
    for line in lines:
        if line.strip() == "":
            if par is not None:
                yield par
            par = None
        elif par is None:
            par = [line]
        else:
            par.append(line)
    if par is not None:
        yield par


def get_common_indent(lines):
    """
    Extracts the common indentation for lines.

    @return
      The common indentation size, and the lines with that indentaiton removed.
    """
    indent = min( get_indent(l) for l in lines )
    return indent, tuple( l[indent :] for l in lines )


#-------------------------------------------------------------------------------

DOCTEST = htmlgen._make_element("doctest")

def parse_doc(lines):
    # Split into paragraphs.
    lines = ( l.expandtabs().rstrip() for l in lines )
    pars = join_pars(lines)

    pars = list(pars)
    summary = " ".join( l.strip() for l in pars.pop(0) )

    # Remove overall indentation.
    pars = [ get_common_indent(p) for p in pars ]
    min_indent = min( i for i, _ in pars )
    pars = [ (i - min_indent, p) for i, p in pars ]

    def to_html(indent, par):
        if len(par) == 2 and len(par[1]) > 1 and all( c == "=" for c in par[1] ):
            return H1(par[0])
        elif len(par) == 2 and len(par[1]) > 1 and all( c == "-" for c in par[1] ):
            return H2(par[0])
        elif indent > 0 and par[0].startswith(">>>"):
            return DOCTEST(*par)
        else:
            return P(*par)
    
    doc = "".join( 
        to_html(i, p).format(indent="", terminator="\n") 
        for i, p in pars 
    )
    return summary, doc


if __name__ == "__main__":
    summary, doc = parse_doc(sys.stdin)
    print("summary: " + summary)
    print
    print(doc)


