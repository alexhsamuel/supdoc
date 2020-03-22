from   contextlib import closing
import os
import shutil
import sys

#-------------------------------------------------------------------------------

def _determine_size():
    """
    Determines the attached terminal size through operating system calls.

    Tries to determine the size of the controlling terminal.  If none is 
    available, tries the connected standard streams to see if any is a terminal.

    @see
      `get_size()`.
    @rtype
      `os.terminal_size`.
    @raise RuntimeError
      The terminal size could not be determined.
    """
    # Try to get the terminal size from the controlling terminal.
    try:
        tty = open("/dev/tty")
    except OSError:
        pass
    else:
        with closing(tty):
            return os.get_terminal_size(tty.fileno())

    # No controlling terminal.  Try each of stdin/stdout/stderr in succession.
    for file in sys.stdin, sys.stdout, sys.stderr:
        try:
            return os.get_terminal_size(file.fileno())
        except OSError:
            pass

    # Give up.
    raise RuntimeError("can't determine terminal size")


def get_size():
    """
    Returns the terminal size.

    Like `shutil.get_terminal_size()`, but works better.  Honors the COLUMNS and
    LINES environment variables, if set.  Otherwise, uses `_determine_size()`.
    """
    try:
        columns = int(os.environ['COLUMNS'])
    except (KeyError, ValueError):
        columns = 0

    try:
        lines = int(os.environ['LINES'])
    except (KeyError, ValueError):
        lines = 0

    if columns <= 0 or lines <= 0:
        try:
            size = _determine_size()
        except (NameError, OSError):
            size = os.terminal_size(fallback)
        if columns <= 0:
            columns = size.columns
        if lines <= 0:
            lines = size.lines

    return os.terminal_size((columns, lines))


def get_width():
    """
    Returns the width in columns.
    """
    return get_size().columns


