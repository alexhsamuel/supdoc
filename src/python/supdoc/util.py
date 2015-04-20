OMIT_ATTRS = set(dir(object))
OMIT_ATTRS.remove("__class__")

OMIT_ATTRS = {}

import ngrid.terminal
from   six import print_


def print_attrs(obj):
    width = ngrid.terminal.get_terminal_width()

    names = [ n for n in dir(obj) if n not in OMIT_ATTRS ]
    length = 0 if len(names) == 0 else max( len(n) for n in names )
    name_fmt = "{}s".format(length)
    val_length = width - length - 1

    for name in sorted(names):
        val = getattr(obj, name)
        val = repr(val)[: val_length]
        print_("{} {}".format(format(name, name_fmt), val))


