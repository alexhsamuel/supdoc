"""
Documentation parsing.

This module attempts to support various docstring markup formats as leniently as
possible.  Even from docstrings with /ad hoc/ markup we attempt to extract as
much information as possible.
"""

#-------------------------------------------------------------------------------

import html
import re
import sys
import xml.dom

from   . import base
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

DOCTEST         = make_element("DOCTEST")
IDENTIFIER      = make_element("IDENTIFIER")
OBJ             = make_element("OBJ")
PARAMETER       = make_element("PARAMETER")

def default_format_identifier(name):
    return IDENTIFIER(name)


#-------------------------------------------------------------------------------

# FIXME: Split this up.  Identifier handling elsewhere.
def parse_doc(doc, format_identifier=default_format_identifier):
    if isinstance(doc, str):
        doc = doc.splitlines()

    # Split into paragraphs.
    lines = ( l.expandtabs().rstrip() for l in doc )
    pars = join_pars(lines)

    pars = list(pars)
    summary = " ".join( l.strip() for l in pars.pop(0) )

    # Remove common indentation.
    pars = [ get_common_indent(p) for p in pars ]
    min_indent = 0 if len(pars) == 0 else min( i for i, _ in pars )
    pars = [ (i - min_indent, p) for i, p in pars ]

    # FIXME: Replace this with real identifier resolution.  That probably
    # involves parsing docs in a second pass, once the entire symbol table has
    # been discovered.
    def fix_identifiers(par):
        def to_id(name):
            if name.endswith("()"):
                name = name[: -2]
            return format_identifier(name)

        parts = re.split(r"`([^`]*)`", par)
        parts = [ make_text(p) if i % 2 == 0 else to_id(p) for i, p in enumerate(parts) ]
        return parts

    def to_html(indent, par):
        if len(par) == 2 and len(par[1]) > 1 and all( c == "=" for c in par[1] ):
            return H1(par[0])
        elif len(par) == 2 and len(par[1]) > 1 and all( c == "-" for c in par[1] ):
            return H2(par[0])
        elif indent > 0 and par[0].startswith(">>>"):
            return DOCTEST(*( l + "\n" for l in par ))
        else:
            return P(*fix_identifiers(" ".join(par)))
    
    summary = SPAN(*fix_identifiers(summary)).toxml()
    doc = "".join( 
        to_html(i, p).toxml()
        for i, p in pars 
    )
    return summary, doc


def main(argv):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", metavar="FILE", default="-",
        help="input file; - for stdin")
    args = parser.parse_args(argv[1 :])

    if args.input == "-":
        file = sys.stdin
    else:
        file = open(args.input)
    lines = list(file)
    print("".join(lines))
    print()
    with file:
        summary, doc = parse_doc(lines)
    print("summary: " + summary.toxml())
    print()
    print(doc)


if __name__ == "__main__":
    main(sys.argv)


