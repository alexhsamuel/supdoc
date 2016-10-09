"""
Tools for generating HTML.
"""

#-------------------------------------------------------------------------------

from   html import escape
import functools

from   aslib import py

#-------------------------------------------------------------------------------

class Element:

    def __init__(self, name, *children, **attrs):
        self.__name = name
        self.__children = []
        self.__attrs = {}
        self.extend(children)
        self.update(attrs)


    @property
    def tag(self):
        if len(self.__attrs) > 0:
            attrs = " " + " ".join( 
                a if v is None else '{}="{}"'.format(a, v) 
                for a, v in self.__attrs.items() 
            )
        else:
            attrs = ""
        return "<{}{}>".format(self.__name, attrs), "</{}>".format(self.__name)


    def __str__(self):
        begin, end = self.tag
        return begin + "".join( str(c) for c in self.__children ) + end


    def format(self, indent=0):
        begin, end = self.tag
        yield " " * indent + begin
        for child in self.__children:
            if isinstance(child, Element):
                yield from child.format(indent + 1)
                space = True
            else:
                yield " " * (indent + 1) + child
        yield " " * indent + end


    def __setitem__(self, name, value):
        if name == "cls":
            name = "class"
        if name == "fr":
            name = "for"

        if name == "class":
            value = " ".join( str(c) for c in py.tupleize(value) )

        self.__attrs[name] = value


    def update(self, attrs={}, **kw_attrs):
        for name, value in attrs.items():
            self[name] = value
        for name, value in kw_attrs.items():
            self[name] = value


    def append(self, child):
        if child is not None:
            self.__children.append(child)
        return child


    def extend(self, children):
        for child in children:
            self.append(child)


    # Why not __iadd__?  We want to use an expression operator, rather than 
    # an assignment statement, so that we can return the (rightmost) child.
    # This enables code like,
    #
    #   child = parent << DIV(...)
    #
    __lshift__ = append

    # FIXME: Sugar for extend too?




def make_element(tag):
    def make_element(*children, **attrs):
        return Element(tag, *children, **attrs)

    make_element.__name__ = tag
    return make_element


_ELEMENT_NAMES = (
    "a",
    "body",
    "button",
    "code",
    "dd",
    "div",
    "dl",
    "dt",
    "em",
    "head",
    "html",
    "img",
    "input",
    "label",
    "li",
    "link",
    "ol",
    "p",
    "pre",
    "script",
    "span",
    "style",
    "title",
    "tt",
    "ul",
) + tuple( "h{}".format(i) for i in range(1, 10) )

_ELEMENTS = { n.upper(): make_element(n) for n in _ELEMENT_NAMES }
globals().update(_ELEMENTS)


#-------------------------------------------------------------------------------

__all__ = tuple(_ELEMENTS.keys()) + (
    )


