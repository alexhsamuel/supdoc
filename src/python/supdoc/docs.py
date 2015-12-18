import re

import logging
import markdown
import xml.etree.ElementTree as ET

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

DOUBLE_BACKTICK_REGEX = re.compile(r"``(.*?)``")
SINGLE_BACKTICK_REGEX = re.compile(r"`(.*?)`")

def parse_formatting(text):
    # Look for ``-delimited strings.
    text = DOUBLE_BACKTICK_REGEX.sub(r'<span class="code">\1</span>', text)
    # Look for `-delimited strings.
    text = SINGLE_BACKTICK_REGEX.sub(r'<span class="code">\1</span>', text)

    text = markdown.markdown(text, output_format="html5")

    return text



def parse_doc(source):
    # Split into paragraphs.
    lines = ( l.expandtabs().rstrip() for l in source.splitlines() )
    pars = join_pars(lines)

    # The first paragraph is the summary.
    try:
        summary = next(pars)
    except StopIteration:
        summary = None
    else:
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

    def generate(pars):
        pars = base.QIter(pars)
        for indent, par in pars:
            # Look for doctests.
            # FIXME: Look for more indentation than the previous par.
            if len(par) >= 1 and par[0].startswith(">>>"):
                body.append('<pre class="doctest">' + "\n".join(par) + '</pre>')
                continue

            if len(par) > 0:
                _, lines = get_common_indent(par)
                text = " ".join(lines)
                text = parse_formatting(text)
                body.append(text)

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
    )
    if len(javadoc) > 0:
        result["javadoc"] = javadoc
    return result


def markdown_to_et(text):
    """
    Parses as Markdown to `ElementTree`.
    """
    # Process as Markdown.
    html = markdown.markdown(text, output_format="html5")

    # Parse it back.  
    # FIXME: Teach markup to emit ElementTree directly?
    # The parser expects a single element, so wrap it.
    try:
        et = ET.fromstring('<html>' + html + '</html>')
    except ET.ParseError as exc:
        # FIXME: If the source includes invalid HTML, such as unclosed tags,
        # so will the output, will will lead to parse errors.  For now, just
        # report these and produce an error..
        logging.error("-" * 80 + "\n" + html + "\n" + str(exc) + "\n\n")
        return ET.fromstring('<strong>Error parsing Markdown output.</strong>')

    return et


def parse_docstring(docstring):
    """
    Parses a docstring.

    FIXME
    """
    # Remove common indentation.
    _, lines = get_common_indent(docstring.splitlines(), ignore_first=True)
    docstring = "\n".join(lines)

    # Replace 'doc' with the de-indented version, since that's nicer.
    result = {"doc": docstring}

    et = markdown_to_et(docstring)

    tostring = lambda e: ET.tostring(e, method="html", encoding="unicode")
    content = lambda e: (e.text or "") + "".join( tostring(c) for c in e )

    # If the first element is a paragraph, use that as the summary.
    if len(et) > 0 and et[0].tag.lower() == 'p':
        summary = et[0]
        et.remove(summary)
        # Get the summary contents, without the enclosing <p> element.
        result["summary"] = content(summary)

    # Reassemble the HTML source.
    result["body"] = [ tostring(e) for e in et ]

    return result


def enrich(jso, modules={}):
    docs = jso.get("docs", {})
    try:
        doc = docs["doc"]
    except KeyError:
        pass
    else:
        docs.update(parse_docstring(doc))

    # FIXME
    for val in jso.get("dict", {}).values():
        enrich(val, modules)


def enrich_modules(modules):
    for mod in modules.values():
        if mod is not None:
            enrich(mod, modules)

