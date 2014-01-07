import html
import functools

#-------------------------------------------------------------------------------

def terminate(terminator, strings):
    result = terminator.join(strings)
    if len(result) > 0:
        result += terminator
    return result


def format_tag(name, attrs={}, close=False):
    if len(attrs) == 0:
        attr_str = ""
    else:
        assert not close
        attr_str = " " + " ".join( 
            '{}="{}"'.format(n, html.escape(v, quote=True)) 
            for n, v in attrs.items() )
    return "<" + ("/" if close else "") + name + attr_str + ">"


class Element:

    def __init__(self, tag, *children, **attrs):
        try:
            attrs["class"] = attrs.pop("class_")
        except KeyError:
            pass

        children = tuple( 
            c if isinstance(c, Element) else str(c) for c in children )
        attrs = { str(n): str(v) for n, v in attrs.items() }

        self.__tag = tag
        self.__attrs = attrs
        self.__children = children


    def __repr__(self):
        return "{}({!r}, *{!r}, **{!r})".format(
            self.__class__.__name__, self.__tag, self.__children, self.__attrs)


    def __str__(self):
        return self.format("", "")


    @property
    def children(self):
        return self.__children


    @property
    def attrs(self):
        # FIXME: Return a read-only view.
        return self.__attrs


    def generate(self, terminator="", indent="", depth=0):
        prefix = indent * depth
        yield prefix + format_tag(self.__tag, self.__attrs) + terminator
        for child in self.__children:
            try:
                yield from child.generate(terminator, indent, depth + 1)
            except AttributeError:
                yield prefix + indent + str(child) + terminator
        yield prefix + format_tag(self.__tag, close=True) + terminator


    def format(self, terminator="\n", indent=" ", depth=0):
        return "".join(self.generate(terminator, indent, depth))



#-------------------------------------------------------------------------------

def _make_element(tag):
    def El(*children, **attrs):
        return Element(tag, *children, **attrs)

    El.__name__ = tag
    return El


_elements = tuple(
    _make_element(n)
    for n in (
        "A",
        "BODY",
        "DIV",
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
        "UL",
        )
    )

globals().update( (e.__name__, e) for e in _elements )

#-------------------------------------------------------------------------------

__all__ = (
    "Element",
    ) + tuple( e.__name__ for e in _elements )


