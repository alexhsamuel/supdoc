"""
Low-level TTY query methods.
"""

#-------------------------------------------------------------------------------

import ctypes
import os
import sys

from   ..py import export

#-------------------------------------------------------------------------------

if sys.platform == "darwin":

    class ttyent(ctypes.Structure):
        _fields_ = [
            ("ty_name"      , ctypes.c_char_p  ),
            ("ty_getty"     , ctypes.c_char_p  ),
            ("ty_type"      , ctypes.c_char_p  ),
            ("ty_status"    , ctypes.c_int     ),
            ("ty_window"    , ctypes.c_char_p  ),
            ("ty_comment"   , ctypes.c_char_p  ),
        ]

    libc = ctypes.CDLL("libc.dylib")

    # int ttyslot(void)
    _ttyslot = libc.ttyslot
    _ttyslot.argtypes = []
    _ttyslot.restype = ctypes.c_int

    # FIXME: This doesn't seem to work if none of stdin, stdout, stderr are
    # connected.

    @export
    def ttyslot():
        """
        Returns the slot number of the connected TTY.
        """
        result = _ttyslot()
        if result == 0:
            raise OSError(os.strerror(ctypes.get_errno()))
        else:
            return result

    # struct ttyent* getttyent(void)
    _getttyent = libc.getttyent
    _getttyent.argtypes = []
    _getttyent.restype = ctypes.POINTER(ttyent)

    @export
    def getttyent():
        """
        Returns the next entry from the TTY file.

        The first call to this function returns the first entry; subsequent
        calls return subsequent entries.  Call `endttyent()` when done.

        @rtype
          `ttyent`.
        @see
          Invoke `man 5 ttys` and `man getttyent` for details.
        """
        result = _getttyent()
        if result == 0:
            raise OSError(os.strerror(ctypes.get_errno()))
        else:
            return result[0]

    # int endttyent(void)
    _endttyent = libc.endttyent
    _endttyent.argtypes = []
    _endttyent.restype = ctypes.c_int

    @export
    def endttyent():
        """
        Ends enumeration of the TTY file.

        @see
          `getttyent()`.
        """
        if _endttyent() != 1:
            raise OSError(os.strerror(ctypes.get_errno()))


    @export
    def get_name():
        """
        Returns the name of the TTY attached to the process.
        """
        try:
            for _ in range(ttyslot()):
                tty = getttyent()
            return tty.ty_name.decode()
        finally:
            endttyent()


    @export
    def get_path(name):
        """
        Returns the device path for TTY named `name`.
        """
        return os.path.join("/dev", name)


