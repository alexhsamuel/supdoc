import html.entities
import html.parser
import io
import logging
import re
import shutil
import sys

from   . import ansi
from   .printer import Printer, NL
from   ..text import get_common_indent
import aslib.log

log = aslib.log.get()

#-------------------------------------------------------------------------------

# FIXME: 
# - Add UPPERCASE feature
# - Elide / truncate words longer than width?
# - French spacing.

class Converter(html.parser.HTMLParser):
    """
    Prints HTML to a fixed-width ANSI terminal.

    For each HTML element, style is given by a tuple,

        `(indent, prefix, prenl, postnl, style)`

    where,

    - `indent` is text to append to the current indentation
    - `prefix` is text to prepend to the next word
    - `prenl` is amount of vertical space to precede the element; 0 for no
      break; 1 for a line break, 2 for a line break and one blank line, etc.
    - `postnl` is the amount of vertical space to follow the element.
    - `style` is a style mapping for the element
    """

    ELEMENTS = {
        # Block elements
        "div"   : ("", "", 1, 2, {}),
        "h1"    : ("", "\u272a ", 2, 1, {"bold": True, "underline": True}),
        "h2"    : ("", "\u2605 ", 2, 1, {"bold": True}),
        "h3"    : ("", "\u2734 ", 1, 1, {}),
        "ol"    : ("  ", "", 1, 1, {}), 
        "p"     : ("", "", 1, 2, {}),
        "pre"   : ("\u2503 ", "", 1, 2, {"fg": "gray20"}),
        "ul"    : ("  ", "", 1, 1, {}),

        # Inline elements
        "a"     : ("", "", 0, 0, {"fg": "#125"}),
        "b"     : ("", "", 0, 0, {"bold": True}),
        "code"  : ("", "", 0, 0, {"bold": True}),
        "em"    : ("", "", 0, 0, {"underline": True}),
        "i"     : ("", "", 0, 0, {"fg": "#600"}),
        "li"    : ("", "\u2219 ", 1, 1, {}),  # FIXME: Numbers for <ol>!
        "u"     : ("", "", 0, 0, {"underline": True}),
    }


    def __init__(self, printer):
        super().__init__(convert_charrefs=True)

        self.__printer = printer

        # True if horizontal space is required before the next word.
        self.__hspace = False
        # Number of lines of vertical space required before the next word.
        self.__vspace = 0
        # True if we are in a <pre> element.
        self.__pre = False


    def convert(self, html, style={}):
        self.reset()
        if style:
            self.__printer.style(**style)
        self.feed(html)
        self.close()
        if style:
            self.__printer.unstyle()


    def handle_starttag(self, tag, attrs):
        pr = self.__printer

        # If needed, emit a word separator before emitting the word.
        if self.__hspace and not pr.is_start:
            pr << " "
            self.__hspace = False

        try:
            indent, prefix, prenl, postnl, style = self.ELEMENTS[tag]
        except KeyError:
            log.warning("unknown tag: {}".format(tag))
        else:
            if indent:
                pr.indent(indent)
            if style:
                pr.style(**style)
            self.__vspace = max(self.__vspace, prenl)
            self.__handle_text(prefix)

        if tag == "pre":
            # Enable special handling for preformatted elements.
            self.__pre = True


    def handle_endtag(self, tag):
        if tag == "pre":
            self.__pre = False

        pr = self.__printer

        try:
            indent, prefix, prenl, postnl, style = self.ELEMENTS[tag]
        except KeyError:
            pass
        else:
            if indent:
                pr.unindent()
            if style:
                pr.unstyle()
            pr.newline(postnl - (1 if pr.is_start else 0))


    def handle_data(self, data):
        assert isinstance(data, str)
        if self.__pre:
            self.__handle_pre_text(data)
        else:
            self.__handle_text(data)


    def __handle_text(self, text):
        pr = self.__printer

        # Break into words at whitespace boundaries, keeping whitespace.
        words = [ w for w in re.split(r"(\s+)", text) if len(w) > 0 ]

        for word in words:
            length = len(word)
            if re.match(r"\s+$", word):  # FIXME
                # This is whitespace.  Don't emit it, but flag that we've 
                # seen it and require a separation for the next word.
                self.__hspace = True

            elif len(word) > 0:
                # Add vertical space if needed.  The first vspace ends the
                # current line, so credit it if we're already at the start.
                pr.newline(self.__vspace - (1 if pr.is_start else 0))
                self.__vspace = 0

                # Check if this word would take us past the terminal width.
                if (not pr.is_start
                    and (1 if self.__hspace else 0) + length > pr.remaining):
                    # On to the next line.
                    pr << NL
                    self.__hspace = False

                # Don't need a separator at the start of a line.
                if pr.is_start:
                    self.__hspace = False

                # If needed, emit a word separator before emitting the word.
                if self.__hspace:
                    pr << " "
                    self.__hspace = False

                pr << word


    def __handle_pre_text(self, text):
        """
        Emits preformatted text.
        """
        self.__printer.write(text)


    def handle_entityref(self, name):
        char = chr(html.entities.name2codepoint[name])
        self.__printer.write(char)



# FIXME: The width thing is hacky.  This method should only understand inline
# elements, not block elements, and not do any line splitting.

def convert(html, *, style={}, width=sys.maxsize, **kw_args):
    """
    Converts HTML to text with ANSI escape sequences.

    @keywords
      See `Converter.__init__()`.
    """
    buffer = io.StringIO()
    printer = Printer(buffer.write, width=width)
    converter = Converter(printer, **kw_args)
    if style:
        printer.style(**style)
    converter.feed(html)
    if style:
        printer.unstyle()
    return buffer.getvalue()


#-------------------------------------------------------------------------------

# FIXME: For testing.

if __name__ == "__main__":
    with open(sys.argv[1]) as file:
        html = file.read()
    print(convert(html))


