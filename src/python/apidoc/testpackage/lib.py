import os
import sys
from   urllib.request import urlopen
from   urllib.request import urlopen as urlopen_renamed

__all__ = (
    "LibClass",
    "lib_function",
    "LIB_CONSTANT",
    "LIB_STRING_CONSTANT",
    )


class LibClass:
    """
    A library class.

    This class doesn't do anything much at all.  However, its documentation
    rambles on and on for no paticular reason.  There's really no justification
    in writing all of this, or of reading it, but that didn't stop anyone from
    composing it anyway.  It is, however, occasionally helpful to have a very
    long docstring for testing purposes, no matter how irrelevant and tiresome
    its content may be.
    """

    pass



def lib_function(x, y):
    """
    Returns the adjusted sum of two distinct numbers.

    The adjusted some is twice the first number plus the second number.

    @param x
      A value.
    @param y
      Another value, which must be different.
    @raise ValueError
      The values are the same.
    """
    if x == y:
        raise ValueError("values are the same")
    else:
        return 2 * x + y


def _internal_function(x):
    """
    Doubles the value.

    @note
      This function is for internal use only.
    """
    return 2 * x


LIB_CONSTANT = 42

LIB_STRING_CONSTANT = "Hello, world."

LIB_INTERNAL_CONSTANT = 17

_LIB_INTERNAL_CONSTANT = 18

