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
            par = [line]
        else:
            par.append(line)
    if par is not None:
        yield par


def get_common_indent(lines):
    """
    Extracts the common indentation for lines.

    @return
      The common indentation size, and the lines with that indentaiton removed.
    """
    indent = min( get_indent(l) for l in lines )
    return indent, tuple( l[min_indent :] for l in lines )


#-------------------------------------------------------------------------------

if __name__ == "__main__":
    lines = ( l.expandtabs().rstrip() for l in sys.stdin )
    pars = join_pars(lines)
    pars = [ get_common_indent(p) for p in pars ]
    min_indent = min( i for i, _ in pars )
    pars = [ (i - min_indent, p) for i, p in pars ]
    for i, p in pars:
        print(i)
        for l in p:
            print(l)
        print()



