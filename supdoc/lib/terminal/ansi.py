"""
ANSI escape codes.

See https://en.wikipedia.org/wiki/ANSI_escape_code.
"""

#-------------------------------------------------------------------------------

from   enum import Enum
import html.parser
from   math import floor
import re

#-------------------------------------------------------------------------------

ESC = "\x1b"
CSI = ESC + "["

def csi(*parts):
    return CSI + "".join( str(p) for p in parts )


def to_column(col):
    """
    Moves the cursor to (zero-indexed) `col`.
    """
    return csi(col + 1, "G")


def SGR(*codes):
    assert all( isinstance(c, int) for c in codes )
    return CSI + ";".join( str(c) for c in codes ) + "m"


RESET               = SGR(  )  # Same as NORMAL.
NORMAL              = SGR( 0)
BOLD                = SGR( 1)
LIGHT               = SGR( 2)
ITALIC              = SGR( 3)
UNDERLINE           = SGR( 4)
SLOW_BLINK          = SGR( 5)
RAPID_BLINK         = SGR( 6)
NEGATIVE            = SGR( 7)
CONCEAL             = SGR( 8)
CROSS_OUT           = SGR( 9)
PRIMARY_FONT        = SGR(10)
ALTERNATE_FONT_1    = SGR(11)
ALTERNATE_FONT_2    = SGR(12)
ALTERNATE_FONT_3    = SGR(13)
ALTERNATE_FONT_4    = SGR(14)
ALTERNATE_FONT_5    = SGR(15)
ALTERNATE_FONT_6    = SGR(16)
ALTERNATE_FONT_7    = SGR(17)
ALTERNATE_FONT_8    = SGR(18)
ALTERNATE_FONT_9    = SGR(19)
BOLD_OFF            = SGR(21)
NORMAL_INTENSITY    = SGR(22)
ITALIC_OFF          = SGR(23)
UNDERLINE_OFF       = SGR(24)
BLINK_OFF           = SGR(25)
POSITIVE            = SGR(27)
REVEAL              = SGR(28)
CROSS_OUT_OFF       = SGR(29)
BLACK_TEXT          = SGR(30)
RED_TEXT            = SGR(31)
GREEN_TEXT          = SGR(32)
YELLOW_TEXT         = SGR(33)
BLUE_TEXT           = SGR(34)
MAGENTA_TEXT        = SGR(35)
CYAN_TEXT           = SGR(36)
WHITE_TEXT          = SGR(37)
DEFAULT_TEXT        = SGR(39)
BLACK_BACKGROUND    = SGR(40)
RED_BACKGROUND      = SGR(41)
GREEN_BACKGROUND    = SGR(42)
YELLOW_BACKGROUND   = SGR(43)
BLUE_BACKGROUND     = SGR(44)
MAGENTA_BACKGROUND  = SGR(45)
CYAN_BACKGROUND     = SGR(46)
WHITE_BACKGROUND    = SGR(47)
DEFAULT_BACKGROUND  = SGR(49)

def COLORMAP_TEXT(i):
    assert 0 <= i < 256
    return SGR(38, 5, i)


def COLORMAP_BACKGROUND(i):
    assert 0 <= i < 256
    return SGR(48, 5, i)


#-------------------------------------------------------------------------------

COLOR_NAMES = dict(
    black       =  0,
    dark_red    =  1,
    dark_green  =  2,
    brown       =  3,
    dark_blue   =  4,
    purple      =  5,
    turquoise   =  6,
    light_gray  =  7,
    dark_gray   =  8,
    red         =  9,
    green       = 10,
    yellow      = 11,
    blue        = 12,
    pink        = 13,
    cyan        = 14,
    white       =231,
)


def parse_rgb_triple(triple):
    if not triple.startswith("#"):
        raise ValueError("RGB triple doesn't start with #")
    if len(triple) == 4:
        # Multiply single digits by 0x11 to repeat digits, e.g. #1a6 expands
        # to #11aa66.
        return tuple( int(x, 16) * 17 for x in triple[1 : 4] )
    elif len(triple) == 7:
        rgb = triple[1 : 3], triple[3 : 5], triple[5 : 7]
        return tuple( int(x, 16) for x in rgb )
    else:
        raise ValueError("wrong number of digits for RGB triple")


def get_color(value):
    """
    Translates `value` to a color code.

    `value` may be:

    - An integer color code between 0 and 255.
    - An 9-bit "%XYZ" RGB triple, where each digit is between 0 and 5.
    - A web-style "#XYZ" or "#XXYYZZ" RGB triple
    - A grayscale name "grayX" where X is between 0 and 100.
    - A color name for the sixteen standard colors.
    """
    if isinstance(value, int):
        if 0 <= value < 256:
            return value
        else:
            raise ValueError("color value not between 0 and 255")

    val = str(value)

    if val.startswith("#"):
        r, g, b = parse_rgb_triple(val)
        # Convert RGB value range from 0-255 to 0-5.
        return 16 + 36 * (r * 6 // 256) + 6 * (g * 6 // 256) + (b * 6 // 256)

    if val.startswith("gray"):
        try:
            gray_value = int(val[4 :])
        except ValueError:
            pass
        else:
            if 0 <= gray_value <= 100:
                # Use black (0), white (231), and 24 additional gray values in
                # the range 232-255.
                gray_value = gray_value * 26 // 101
                return (
                    0 if gray_value == 0 
                    else 231 if gray_value == 25 
                    else 231 + gray_value
                )

    if val.startswith("%") and len(val) == 4:
        r, g, b = ( int(x) for x in val[1 :] )
        return 16 + 36 * r + 6 * g + b

    try:
        return COLOR_NAMES[val]
    except KeyError:
        pass

    raise ValueError("unrecognized color: {!r}".format(value))
    


def GRAY_LEVEL(fraction):
    """
    Returns the closest color map code for a gray level between 0 and 1.
    """
    assert 0 <= fraction <= 1
    index = int(floor(fraction * 24.999999999999))
    return 231 if index == 24 else 232 + index


def sgr(*, fg=None, bg=None, bold=None, underline=None, blink=None,
        reverse=None, conceal=None):
    """
    Returns an SGR sequence to set color and text style.

    An argument value of `None` indicates that style should not be modified.

    @param fg
      Foreground color name or number, or `"default"` for the implementation's
      default. 
    @param bg
      Background color name or number, or `"default"` for the implementation's
      default. 
    @param underline
      True to enable single underlining; false to disable.
    @param blink
      True to enable blinking text; false to disable.
    @param reverse
      True to enable reverse video; false to disable.
    @param conceal
      True to conceal text; false to reveal.
    """
    codes = []

    # Avoid using codes 30-37 for foreground and 40-47 for background color,
    # since the bold setting may change the colors of these.

    if fg is None:
        pass
    elif fg == "default":
        codes.append(39)
    else:
        codes.extend((38, 5, get_color(fg)))

    if bg is None:
        pass
    elif bg == "default":
        codes.append(49)
    else:
        codes.extend((48, 5, get_color(bg)))

    if bold is not None:
        # FIXME: Might be 22 for OSX, 21 for Linux?
        codes.append(1 if bold else 22)
    if underline is not None:
        codes.append(4 if underline else 24)
    if blink is not None:
        codes.append(5 if blink else 25)
    if reverse is not None:
        codes.append(7 if reverse else 27)
    if conceal is not None:
        codes.append(8 if conceal else 28)

    return SGR(*codes) if len(codes) > 0 else ""


def inverse_sgr(*, fg=None, bg=None, bold=None, underline=None, blink=None,
                reverse=None, conceal=None):
    if fg is not None:
        fg = "default"
    if bg is not None:
        bg = "default"
    if bold is not None:
        bold = not bold
    if underline is not None:
        underline = not underline
    if blink is not None:
        blink = not blink
    if reverse is not None:
        reverse = not reverse
    if conceal is not None:
        conceal = not conceal
    return sgr(
        fg=fg, bg=bg, bold=bold, underline=underline, blink=blink,
        reverse=reverse, conceal=conceal)


# FIXME: We need a Style class.

def style(**kw_args):
    """
    Returns a function that applies graphics style to text.

    The styling function accepts a single string argument, and returns that
    string styled and followed by the inverse styling.
    """
    escape = sgr(**kw_args)
    unescape = inverse_sgr(**kw_args)
    return lambda text: escape + str(text) + unescape


# Single-style shortcuts.

def fg(color):
    return style(fg=color)


def bg(color):
    return style(bg=color)


bold        = style(bold=True)
underline   = style(underline=True)
blink       = style(blink=True)
reverse     = style(reverse=True)
concel      = style(conceal=True)

#-------------------------------------------------------------------------------

ESCAPE_REGEX = re.compile(re.escape(CSI) + r"[^@-~]*.")

# FIXME: Use extension version from fixfmt.
def length(string):
    return len(ESCAPE_REGEX.sub("", string))


# FIXME: Elsewhere.
def dict_diff(dict0, dict1):
    assert len(dict0) == len(dict1)
    return { k: dict1[k] for k in dict0 if dict1[k] != dict0[k] }


class StyleStack:
    """
    Stack of nested styles.
    """

    DEFAULT_STYLE = {
        "fg"        : "default",
        "bg"        : "default",
        "bold"      : False,
        "underline" : False,
        "blink"     : False,
        "reverse"   : False,
        "conceal"   : False,
    }


    def __init__(self, style=DEFAULT_STYLE):
        """
        @param style
          The initial style.
        """
        self.__stack = [style]


    def push(self, **styles):
        """
        Pushes a new style onto the stack.

        @return
          Escape codes to produce the new style.
        """
        bad_keys = set(styles) - set(self.DEFAULT_STYLE)
        if len(bad_keys) > 0:
            raise TypeError("unknown styles: " + ", ".join(bad_keys))

        old = self.__stack[-1]
        new = old.copy()
        new.update(styles)
        self.__stack.append(new)
        return sgr(**dict_diff(old, new))


    def pop(self):
        """
        Pops a style off the stack.

        @return
          Escape codes to revert to the previous style.
        """
        old = self.__stack.pop()
        new = self.__stack[-1]
        return sgr(**dict_diff(old, new))
                


#-------------------------------------------------------------------------------

class ParseError(Exception):
    """
    An error while parsing pseudo-HTML.
    """

    pass



class Parser(html.parser.HTMLParser):
    """
    Parses pseudo-HTML markup into text with ANSI escapes.

    Syntax:

    - `<foreground color="COLOR"> ... </foreground>` for the foreground color.
    - `<background color="COLOR"> ... </background>` for the background color.
    - `<bold> ... </bold>` for bold.
    - `<underline> ... </underline>`.
    - `<blink> ... </blink>` for blink.
    - `<reverse> ... </reverse>` for reverse.
    - `<conceal> ... </conceal>` for conceal.

    The aliases `<fg>`, `<bg>`, `<b>`, `<u>` may be used for the first four
    tags above, respectively.

    `COLOR` may be a color name, RGB triplet, or gray value like "gray50".

    Unrecognized tags are passed through.

    Usage::

        print(Parser().feed(markup).result)

    """

    # Renaming tags to SGR attributes.
    __RENAME = {
        "b"         : "bold",
        "background": "bg",
        "foreground": "fg",
        "u"         : "underline",
    }

    def __init__(self):
        super().__init__()
        self.__result = []
        # Stack of tags, for matching end tags.
        self.__tags = []
        # For colors, stacks of nested values; "default" is a sentry value.
        self.__colors = dict(fg=["default"], bg=["default"])
        # For boolean attributes, a nesting count.
        self.__attrs = dict(bold=0, underline=0, blink=0, reverse=0, conceal=0)


    def handle_starttag(self, tag, attrs):
        tag = self.__RENAME.get(tag, tag)
        self.__tags.append(tag)
        
        if tag in self.__colors:
            if len(attrs) != 1 or attrs[0][0] != "color":
                raise ParseError("{} must have attribute color".format(tag))
            color = get_color(attrs[0][1])
            stack = self.__colors[tag]
            # Set the color.
            if stack[-1] != color:
                self.__result.append(sgr(**{tag: color}))
            # Push it.
            stack.append(color)

        elif tag in self.__attrs:
            # Set the attribute, if this is the outermost tag.
            if self.__attrs[tag] == 0:
                self.__result.append(sgr(**{tag: True}))
            # Increment the nesting count.
            self.__attrs[tag] += 1

        else:
            self.__result.append(self.get_starttag_text())


    def handle_endtag(self, tag):
        tag = self.__RENAME.get(tag, tag)
        if len(self.__tags) == 0:
            raise ParseError("unmatched end tag {!r}".format(tag))
        elif tag != self.__tags.pop():
            raise ParseError("mismatched end tag {!r}".format(tag))

        if tag in self.__colors:
            stack = self.__colors[tag]
            color = stack.pop()
            # Restore the previous color.
            if stack[-1] != color:
                self.__result.append(sgr(**{tag: stack[-1]}))

        elif tag in self.__attrs:
            self.__attrs[tag] -= 1
            # Turn off the attribute, if this is the outermost tag.
            if self.__attrs[tag] == 0:
                self.__result.append(sgr(**{tag: False}))

        else:
            self.__result.append("</" + tag + ">")


    def handle_data(self, data):
        # Just append non-tag text.
        self.__result.append(data)


    def feed(self, *args, **kw_args):
        """
        @raise ParseError
          The input coudl not be parsed.
        """
        # Just make this method chainable.
        super().feed(*args, **kw_args)
        return self


    @property
    def result(self):
        """
        The parsed and converted result.
        """
        return "".join(self.__result)



def convert_markup(text):
    """
    Converts HTML-style markup into ANSI escape codes.

    @see
      `Parser` for markup syntex.
    """
    return Parser().feed(text).result


#-------------------------------------------------------------------------------
# For testing purposes.

def print_colors(print=print):
    """
    Prints color samples.
    """
    print(underline("Basic Colors"))
    for color in range(16):
        print(
            "    {:2x} ".format(color) + fg(color)("TEST") + "  ", 
            end="\n" if color % 6 == 5 else "")
    print()
    print(underline("RGB Foreground Colors"))
    for r in range(6):
        for g in range(6):
            for b in range(6):
                color = 16 + 36 * r + 6 * g + b
                print(
                    f"{r}{g}{b} {color:2x} " + fg(color)("TEST") + "  ", 
                    end="\n" if color % 6 == 3 else "")
    print(underline("RGB Background Colors"))
    for r in range(6):
        for g in range(6):
            for b in range(6):
                color = 16 + 36 * r + 6 * g + b
                print(
                    f"{r}{g}{b} {color:2x} ".format(r, g, b, color)
                    + bg(color)("TEST") + "  ", 
                    end="\n" if color % 6 == 3 else "")
    print(underline("Gray Scale"))
    for i in range(0, 101, 4):
        color = get_color("gray{}".format(i))
        name = "g{:02d}".format(i) if i < 100 else "   "
        print("{} {:2x} ".format(name, color) + fg(color)("TEST") + "  ", 
            end="\n" if i % 24 == 20 else "")
    print()


