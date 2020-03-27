import re

#-------------------------------------------------------------------------------

_SPACES = re.compile(" *")

def get_indent(line):
    match = _SPACES.match(line)
    return 0 if match is None else match.span()[1]


def remove_indent(lines):
    lines = list(lines)
    indent = min( get_indent(l) for l in lines if l.strip() != "" )
    return ( l if l.strip() == "" else l[indent :] for l in lines )


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


def get_common_indent(lines, ignore_first=False):
    """
    Extracts the common indentation for lines.

    Lines that are empty or contain only whitespace are not used for determining
    common indentation.

    @param ignore_first
      If true, ignore the indentation of the first line when determining the
      common indentation.  This is useful for Python multiline strings, where
      the first line is often indented differently.
    @return
      The common indentation size, and the lines with that indentation removed.
    """
    if ignore_first and len(lines) > 1:
        i, rest = get_common_indent(lines[1 :])
        lines = (lines[0][min(i, get_indent(lines[0])) :], ) + rest
        return i, lines

    indent = ( get_indent(l) for l in lines if l.strip() != "" )
    try:
        indent = min(indent)
    except ValueError:
        indent = 0
    return indent, tuple( l[indent :] for l in lines )


