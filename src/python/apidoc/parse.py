import re
import sys

#-------------------------------------------------------------------------------

_SPACES = re.compile(" *")

def get_indent(line):
    match = _SPACES.match(line)
    return 0 if match is None else match.span()[1]


def get_common_indent(lines):
    return min( get_indent(l) for l in lines if l.strip() != "" )


def remove_indent(lines):
    lines = list(lines)
    indent = get_common_indent(lines)
    return ( l if l.strip() == "" else l[indent :] for l in lines )


# FIXME: Gather indent on a paragraph basis.

def join_pars(lines):
    par = None
    for line in lines:
        if line.strip() == "":
            if par is not None:
                yield par
            par = None
        elif par is None:
            par = [line.rstrip()]
        else:
            par.append(line.rstrip())
    if par is not None:
        yield par


#-------------------------------------------------------------------------------

if __name__ == "__main__":
    lines = ( l.expandtabs().rstrip() for l in sys.stdin )
    for par in join_pars(remove_indent(lines)):
        print(par)


