"""
Convenience class for formatting to a fixed-width ANSI terminal.

`Printer` is not a good example of OO design; rather, it is a convenience class
that pulls together various loosely-coupled pieces of functionality that 
together make it easy to produce formatted terminal output.  The class includes
a number of dubious bits of syntactic sugar to make the formatting code concise.

For example,

    from supdoc.lib.terminal.printer import Printer, NL
    printer = Printer()

    # Print a message.
    printer << "Hello, world!" << NL

    # Print a message with some ANSI terminal styles applied.
    with printer(fg="green", bold=True):
        printer << "This is quite important!" << NL << NL

    # Render some HTML, with indentation on each line.
    with printer(indent=">> "):
        printer.html(html_source)

    # Print a right-justified message.
    printer >> "Bye!"

Note that `NL` is just an alias for `"\\n"`; you may include newlines directly.
"""

#-------------------------------------------------------------------------------

import sys

from   supdoc.lib import itr
from   . import get_width
from   .ansi import length, StyleStack

#-------------------------------------------------------------------------------

NL = "\n"

class Printer:
    """
    Manages formatted printing to a fixed-width ANSI terminal.

    - Tracks the current column position relative to the (fixed) width.  Use
      `column`, `remaining`, and `fits()`.

    - Manages indentation.  Keeps a stack of indentation, each a suffix if the
      previous.  Use `indent()` and `unindent()` to push and pop.

    - Manages style with a stack of nested styles, per `ansi.style()`.  Use
      `style()` and `unstyle()` to push and pop.

    - Can write strings right-justified (`write_right()`) or elided (`elide()`).

    - Can render HTML; use `html()`.

    - Provides a `write()` method for use as a file-like object.

    - Provides syntactic sugar with `__lshift__` and `__rshift__`.

    - Provides a context manager for styles and indents, with `__call__()`.

    """

    def __init__(self, write=None, *, width=None, indent="", 
                 style=StyleStack.DEFAULT_STYLE):
        """
        @param write
          The method to write characters to the terminal.  If `None`, uses,
          `sys.stdout.write`.
        @param width
          The fixed terminal width.  If `None`, calls `get_width()`.
        @param indent
          The initial indentation.
        @prefix style
          The initial style.
        """
        if write is None:
            write = sys.stdout.write
        if width is None:
            width = get_width()

        self.__width = width
        self.__col = None
        self.__indent = [indent]
        self.__style = StyleStack(style)
        self._write = write


    @property
    def width(self):
        """
        The terminal width.
        """
        return self.__width


    @property
    def column(self):
        """
        The current column number.

        The width of the current indentation is not included.
        """
        return length(self.__indent[-1]) if self.__col is None else self.__col


    @property
    def remaining(self):
        """
        The number of characters remaining on the line.
        """
        return self.__width - self.column


    @property
    def is_start(self):
        """
        True if printing is at the start of a new line.
        """
        return self.__col is None


    def fits(self, string):
        """
        Returns true if `string` fits on the current line.
        """
        return self.column + length(string) <= self.width


    def newline(self, count=1):
        """
        Advances to the next line.

        @param count
          The number of newlines to advance.  
        """
        if count < 1:
            return
        if self.is_start:
            self._write(self.__indent[-1])
        self._write("\n")
        if count > 1:
            self._write((self.__indent[-1] + "\n") * (count - 1))
        self.__col = None


    @property
    def indentation(self):
        """
        The indentation that will be used for the next line.
        """
        return self.__indent[-1]


    def indent(self, indent):
        """
        Appends `intent` to the current `indentation`.
        """
        self.__indent.append(self.__indent[-1] + indent)


    def unindent(self):
        """
        Removes the most recently appended indentation.

        Undoes the last call to `indent()`.
        """
        self.__indent.pop()


    def style(self, **style):
        """
        Sets style.

        @keyword style
          See `ansi.style()`.
        """
        self._write(self.__style.push(**style))


    def unstyle(self):
        """
        Removes the most recently set style.

        Undoes the last call to `style()`.
        """
        self._write(self.__style.pop())


    def _start_line(self):
        """
        Starts the current line, if necessary.
        """
        if self.__col is None:
            # FIXME: Hacky.  What's the style policy for indentation?
            with self(**StyleStack.DEFAULT_STYLE):
                self._write(self.indentation)
            self.__col = length(self.indentation)


    def write(self, string):
        *lines, last = string.split("\n")
        for line in lines:
            self._start_line()
            self._write(line)
            self.newline()
        if len(last) > 0:
            self._start_line()
            self._write(last)
            self.__col += length(last)


    def elide(self, string, *, ellipsis="\u2026"):
        """
        Prints text elided to the width.

        Prints each line of `string`, eliding it if it doesn't fit the current
        line.  The string is elided by truncating sufficient characters and
        appending `ellipsis`.  
        """
        lel = length(ellipsis)
        for last, line in itr.last(string.split("\n")):
            self._start_line()
            if length(line) > self.remaining:
                line = line[: self.remaining - lel] + ellipsis
            self._write(line)
            if not last:
                self.newline()


    def write_right(self, string):
        """
        Prints right-justified.

        Prints `string` at the end of the current line, if it fits, on the end
        of the next line otherwise.  Does not end the line; `column` is at
        `width` on return.
        """
        self._start_line()
        pad = self.remaining - length(string)
        if pad < 0:
            self.newline()
        else:
            self._write(pad * " ")
        self._write(string)
        self.__col = self.width


    def __lshift__(self, string):
        """
        Prints `string`.

        @return
          `self`
        @see
          `write()`.
        """
        self.write(str(string))
        return self


    def __rshift__(self, string):
        """
        Prints `string` right-justified.

        @return
          `self`
        @see
          `write_right()`.
        """
        self.write_right(str(string))
        return self


    def html(self, html):
        """
        Renders HTML `html` to the printer.
        """
        from .html import Converter
        Converter(self).convert(html)
        return self


    class _StyleContext:
        """
        Used by `__call__()`.
        """

        def __init__(self, printer, *, indent=None, **style):
            self.__printer = printer
            self.__indent = indent
            self.__style = style


        def __enter__(self):
            if self.__indent:
                self.__printer.indent(self.__indent)
            if self.__style:
                self.__printer.style(**self.__style)


        def __exit__(self, *exc_info):
            if self.__style:
                self.__printer.unstyle()
            if self.__indent:
                self.__printer.unindent()
                


    def __call__(self, *, indent=None, **style):
        """
        Returns a context manager that sets style and/or indent.

        The indentation and style last for the context of the context manager.

        @param indent
          If not `None`, the indentation to append.
        @param style
          Style variables.  See `ansi.style()`.
        """
        return self._StyleContext(self, indent=indent, **style)



