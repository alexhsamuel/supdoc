import re

from   . import base

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


def get_common_indent(lines):
    """
    Extracts the common indentation for lines.

    @return
      The common indentation size, and the lines with that indentaiton removed.
    """
    indent = min( get_indent(l) for l in lines )
    return indent, tuple( l[indent :] for l in lines )


#-------------------------------------------------------------------------------

JAVADOC_ARG_TAGS = frozenset({
    "param",
    "type",
    })


def find_javadoc(lines):
    """
    Finds and separates Javadoc-style tags.
    """
    javadoc = []

    def filter():
        tag = None
        for line in lines:
            l = line.strip()
            try:
                first, rest = l.split(None, 1)
            except ValueError:
                first, rest = l, ""
            if first.startswith("@") and len(first) > 1:
                if tag is not None:
                    # Done with the previous tag.
                    javadoc.append((tag, arg, " ".join(text)))
                tag = first[1 :]
                # Some tags take an argument.
                if tag in JAVADOC_ARG_TAGS and len(rest) > 0:
                    words = rest.split(None, 1)
                    if len(words) == 1:
                        arg, = words
                        rest = ""
                    else:
                        arg, rest = words
                else:
                    arg = None
                text = [rest] if len(rest) > 0 else []
                indent = get_indent(line)
            elif tag is not None and get_indent(line) >= indent:
                text.append(l)
            else:
                yield line
        if tag is not None:
            javadoc.append((tag, arg, " ".join(text)))
    
    return list(filter()), javadoc


#-------------------------------------------------------------------------------

def parse_doc(source):
    # Split into paragraphs.
    lines = ( l.expandtabs().rstrip() for l in source.splitlines() )
    pars = join_pars(lines)

    # The first paragraph is the summary.
    summary = next(pars)
    summary = " ".join( l.lstrip() for l in summary )

    # Remove common indentation.
    pars = [ get_common_indent(p) for p in pars ]
    min_indent = 0 if len(pars) == 0 else min( i for i, _ in pars )
    pars = ( (i - min_indent, p) for i, p in pars )

    # FIXME
    if True:
        p = [ (i, ) + find_javadoc(p) for i, p in pars ]
        indents, pars, javadoc = zip(*p) if len(p) > 0 else ([], [], [])
        pars = zip(indents, pars)
        javadoc = sum(javadoc, [])
    else:
        javadoc = []

    body = []
    doctests = []

    def generate(pars):
        pars = base.QIter(pars)
        for indent, par in pars:
            # Look for underlined headers.
            if len(par) >= 2:
                line0, line1, *rest = par
                if len(line0) > 1 and len(line1) == len(line0):
                    if all( c == "=" for c in line1 ):
                        body.append("<h1>" + line0 + "</h1>")
                        par = rest
                    elif all( c == "-" for c in line1 ):
                        body.append("<h2>" + line0 + "</h2>")
                        par = rest

            # Look for doctests.
            # FIXME: Look for more indentation than the previous par.
            if indent > 0 and len(par) >= 1 and par[0].startswith(">>>"):
                doctests.append("\n".join(par))
                continue

            if len(par) > 0:
                body.append("<p>" + " ".join( p.strip() for p in par ) + "</p>")

            if len(par) > 0 and par[-1].rstrip().endswith(":"):
                text = []
                for i, p in pars:
                    if i > indent:
                        text.extend(p)
                    else:
                        pars.push((i, p))
                        break
                if len(text) > 0:
                    # FIXME: Use a better tag for this.
                    body.append('<pre class="code">' + "\n".join(text) + "</pre>")

    generate(pars)

    # # Attach Javadoc-style tags.
    # if len(javadoc) > 0:
    #     container = DL(class_="javadoc")
    #     for tag, arg, text in javadoc:
    #         element = TAG(text, tag=tag)
    #         if arg is not None:
    #             element.setAttribute("argument", arg)
    #         container.appendChild(element)
    #     body.appendChild(container)

    # find_identifiers(body)

    result = dict(
        summary =summary, 
        body    =body, 
        doctests=doctests, 
    )
    if len(javadoc) > 0:
        result["javadoc"] = javadoc
    return result
    


def enrich(jso, modules={}):
    docs = jso.get("docs", {})
    try:
        doc = docs["doc"]
    except KeyError:
        pass
    else:
        docs.update(parse_doc(doc))

    # FIXME
    for val in jso.get("dict", {}).values():
        enrich(val, modules)


def enrich_modules(modules):
    for mod in modules.values():
        if mod is not None:
            enrich(mod, modules)


