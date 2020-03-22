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
from   xml.dom import minidom  # FIXME

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
TAG             = make_element("TAG")

#-------------------------------------------------------------------------------

def replace_children(node, fn, filter=lambda n: True):
    """
    Replaces child nodes recursively.

    @param node
      The node whose children to replace.
    @param fn
      The replacement function.  Takes a node, and returns `None`, a single 
      node, or a sequence of nodes.
    @param filter
      A filter function.  Takes a node and returns true if it should be 
      replaced.
    """
    for child in tuple(node.childNodes):
        replace_children(child, fn, filter)
        if filter(child):
            replacement = fn(child)
            if replacement is None:
                node.removeChild(child)
            elif isinstance(replacement, minidom.Node):
                node.replaceChild(child, replacement)
            else:
                for r in replacement:
                    node.insertBefore(r, child)
                node.removeChild(child)


is_text_node = lambda n: isinstance(n, minidom.Text)


def find_identifiers(node):
    """
    Finds identifiers recursively and puts them into `IDENTIFIER` elements.

    Looks for identifiers indicated in back quotes.
    """
    def to_id(name):
        if name.endswith("()"):
            name = name[: -2]
        return OBJ(name)

    def replacement(node):
        return [
            to_id(p.strip("`")) if p.startswith("`") and p.endswith("`")
            else make_text(p)
            for p in re.split(r"(``?[^`]*``?)", node.data)
            ]

    replace_children(node, replacement, is_text_node)


JAVADOC_ARG_TAGS = frozenset({
    "param",
    "type",
    })


def find_javadoc(lines):
    """
    Finds and separates Javadoc-style tags.
    """
    javadoc = []

    def filter():
        tag = None
        for line in lines:
            l = line.strip()
            try:
                first, rest = l.split(None, 1)
            except ValueError:
                first, rest = l, ""
            if first.startswith("@") and len(first) > 1:
                if tag is not None:
                    # Done with the previous tag.
                    javadoc.append((tag, arg, " ".join(text)))
                tag = first[1 :]
                # Some tags take an argument.
                if tag in JAVADOC_ARG_TAGS and len(rest) > 0:
                    words = rest.split(None, 1)
                    if len(words) == 1:
                        arg, = words
                        rest = ""
                    else:
                        arg, rest = words
                else:
                    arg = None
                text = [rest] if len(rest) > 0 else []
                indent = get_indent(line)
            elif tag is not None and get_indent(line) >= indent:
                text.append(l)
            else:
                yield line
        if tag is not None:
            javadoc.append((tag, arg, " ".join(text)))
    
    return list(filter()), javadoc


def parse_doc(source):
    # Split into paragraphs.
    lines = ( l.expandtabs().rstrip() for l in source.splitlines() )
    pars = join_pars(lines)

    # The first paragraph is the summary.
    summary = next(pars)
    summary = SPAN(" ".join( l.lstrip() for l in summary ))

    # Remove common indentation.
    pars = [ get_common_indent(p) for p in pars ]
    min_indent = 0 if len(pars) == 0 else min( i for i, _ in pars )
    pars = ( (i - min_indent, p) for i, p in pars )

    # FIXME
    if False:
        p = [ (i, ) + find_javadoc(p) for i, p in pars ]
        indents, pars, javadoc = zip(*p) if len(p) > 0 else ([], [], [])
        pars = zip(indents, pars)
        javadoc = sum(javadoc, [])
    else:
        javadoc = []

    def generate(pars):
        pars = base.QIter(pars)
        while True:
            indent, par = next(pars)

            # Look for underlined headers.
            if len(par) >= 2:
                line0, line1, *rest = par
                if len(line0) > 1 and len(line1) == len(line0):
                    if all( c == "=" for c in line1 ):
                        yield H1(line0)
                        par = rest
                    elif all( c == "-" for c in line1 ):
                        yield H2(line0)
                        par = rest

            # Look for doctests.
            # FIXME: Look for more indentation than the previous par.
            if indent > 0 and len(par) >= 1 and par[0].startswith(">>>"):
                yield DOCTEST("\n".join(par))
                continue

            if len(par) > 0:
                yield P(" ".join( p.strip() for p in par ))

            if par[-1].rstrip().endswith(":"):
                text = []
                for i, p in pars:
                    print("SUBPAR", i, indent)
                    if i > indent:
                        text.extend(p)
                    else:
                        pars.push((i, p))
                        break
                if len(text) > 0:
                    # FIXME: Use a better tag for this.
                    yield PRE("\n".join(text), class_="code")

    body = DIV(*generate(pars))

    # Attach Javadoc-style tags.
    if len(javadoc) > 0:
        container = DL(class_="javadoc")
        for tag, arg, text in javadoc:
            element = TAG(text, tag=tag)
            if arg is not None:
                element.setAttribute("argument", arg)
            container.appendChild(element)
        body.appendChild(container)

    find_identifiers(body)

    return summary, body


def open_arg(name):
    if name == "-":
        return sys.stdin
    else:
        return open(name)


#-------------------------------------------------------------------------------

def main(argv):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", metavar="FILE", default="-",
        help="input file; - for stdin")
    args = parser.parse_args(argv[1 :])

    with open_arg(args.input) as file:
        source = file.read()
    print(source)
    print()
    summary, doc = parse_doc(source)
    print(summary.toprettyxml(" "))
    print(doc.toprettyxml(" "))


if __name__ == "__main__":
    main(sys.argv)


