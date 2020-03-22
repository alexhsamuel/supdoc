"""
Tools for generating HTML.
"""

#-------------------------------------------------------------------------------

from   html import escape
import functools
from   xml.dom import minidom

#-------------------------------------------------------------------------------

_DOC = minidom.getDOMImplementation().createDocument(None, "apidoc", None)

def make_element(tag):
    def make_element(*children, **attrs):
        element = _DOC.createElement(tag)
        for child in children:
            if isinstance(child, str):
                child = make_text(child)
            assert isinstance(child, minidom.Node)
            element.appendChild(child)
        for name, value in attrs.items():
            if name == "class_":
                name = "class"
            element.setAttribute(name, value)
        return element

    make_element.__name__ = tag
    return make_element


def make_text(text):
    element = minidom.Text()
    element.data = str(text)
    return element


_ELEMENT_NAMES = (
    "A",
    "BODY",
    "DD",
    "DIV",
    "DL",
    "DT",
    "EM",
    "HEAD",
    "HTML",
    "IMG",
    "LI",
    "LINK",
    "OL",
    "P",
    "PRE",
    "SCRIPT",
    "SPAN",
    "STYLE",
    "TITLE",
    "TT",
    "UL",
    ) + tuple( "H{}".format(i) for i in range(1, 10) )

globals().update({ n: make_element(n) for n in _ELEMENT_NAMES })


#-------------------------------------------------------------------------------

__all__ = _ELEMENT_NAMES + (
    "make_element", 
    "make_text",
    )


