import html
import logging
import re
import sys
import xml.etree.ElementTree as ET

import markdown

import pln.itr
from   pln.text import get_indent, get_common_indent, join_pars

#-------------------------------------------------------------------------------

def markup_error(description):
    logging.warning(description)


#-------------------------------------------------------------------------------

JAVADOC_ARG_TAGS = frozenset({
    "param",
    "type",
})


def find_javadoc(lines):
    """
    Finds and separates Javadoc-style tags.

    @param lines
      Iterable of docstring lines.
    @return
      `doc_lines, javadoc`, where `doc_lines` is a sequence of the filtered
      non-Javadoc lines, and `javadoc` is a sequence of extracted Javadoc tags.
    """
    doc_lines = []
    javadoc = []

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
                javadoc.append(dict(
                    tag =tag, 
                    arg =arg, 
                    text=parse_formatting(" ".join(text)),
                ))
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
            doc_lines.append(line)
    if tag is not None:
        javadoc.append(dict(
            tag =tag, 
            arg =arg, 
            text=" ".join(text)
        ))
    
    return doc_lines, javadoc


#-------------------------------------------------------------------------------

DOUBLE_BACKTICK_REGEX   = re.compile(r"``(.+?)``")
SINGLE_BACKTICK_REGEX   = re.compile(r"`(.+?)`")

ITALIC_REGEX            = re.compile(r"_(.+?)_")
BOLD_REGEX              = re.compile(r"\*(.+?)\*")

def parse_formatting(text):
    # Look for ``-delimited strings.
    text = DOUBLE_BACKTICK_REGEX.sub(r'<code>\1</code>', text)
    # Look for `-delimited strings.
    text = SINGLE_BACKTICK_REGEX.sub(r'<code>\1</code>', text)

    # text = markdown.markdown(text, output_format="html5")

    # FIXME: These are too lenient.
    # text = ITALIC_REGEX.sub(r'<i>\1</i>', text)
    # text = BOLD_REGEX.sub(r'<b>\1</b>', text)

    return text



def parse_doc(source):
    # Split into lines.
    lines = ( l.expandtabs().rstrip() for l in source.split("\n") )

    # Filter and parse Javadoc tags.
    lines, javadoc = find_javadoc(lines)

    # Combine lines into paragraphs.
    pars = join_pars(lines)

    # The first paragraph is the summary.
    try:
        summary = next(pars)
    except StopIteration:
        summary = None
    else:
        summary = " ".join( l.lstrip() for l in summary )
        summary = parse_formatting(html.escape(summary))

    # Remove common indentation.
    pars = [ get_common_indent(p) for p in pars ] 
    min_indent = min(( i for i, _ in pars ), default=0)
    pars = [ (i - min_indent, p) for i, p in pars ]

    def generate(pars):
        pars = pln.itr.PeekIter(pars)
        for indent, par in pars:
            # Look for doctests.
            # FIXME: Look for more indentation than the previous par.
            if len(par) >= 1 and par[0].startswith(">>>"):
                yield '<pre class="doctest">' + "\n".join(par) + '</pre>'
                continue

            if len(par) > 0:
                _, lines = get_common_indent(par)
                text = " ".join(lines)
                text = parse_formatting(html.escape(text))
                yield '<p>' + text + '</p>'

            if len(par) > 0 and par[-1].rstrip().endswith(":"):
                text = []
                for i, p in pars:
                    if i > indent:
                        text.extend(p)
                        # FIXME: This is wrong.  It adds a single space between
                        # "paragraphs" of preformatted text, regardless of how
                        # many were there originally.  To get this write, we
                        # should split paragraphs incrementally, so we don't
                        # have to split at all for preformatted elements.
                        text.append("")
                    else:
                        pars.push((i, p))
                        break
                if len(text) > 0:
                    text = html.escape("\n".join(text))
                    yield '<pre class="code">' + text + "</pre>"

    body = "\n".join(generate(pars))

    # find_identifiers(body)

    result = dict(
        summary =summary, 
        body    =body, 
    )
    if len(javadoc) > 0:
        result["javadoc"] = javadoc
    return result


def attach_epydoc_to_signature(doc):
    try:
        signature   = doc["signature"]
        javadoc     = doc["docs"]["javadoc"]
    except KeyError:
        return

    params = { s["name"] : s for s in signature.get("params", ()) }

    for entry in javadoc:
        tag = entry["tag"]
        if tag in {"param", "type"}:
            name = entry["arg"]
            try:
                param = params[name]
            except KeyError:
                markup_error(
                    "no matching parameter for @{} {}".format(tag, name))
            else:
                param["doc" if tag == "param" else "doc_type"] = entry["text"]


#-------------------------------------------------------------------------------

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


def parse_doc_markdown(docstring):
    """
    Parses a docstring as Markdown.

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
    result["body"] = "\n".join( tostring(e) for e in et )

    return result


#-------------------------------------------------------------------------------

def enrich(odoc, modules={}):
    docs = odoc.get("docs", {})
    try:
        doc = docs["doc"]
    except KeyError:
        pass
    else:
        # docs.update(parse_doc_markdown(doc))
        docs.update(parse_doc(doc))
        attach_epydoc_to_signature(odoc)

    # FIXME
    for val in odoc.get("dict", {}).values():
        enrich(val, modules)


def enrich_modules(modules):
    for mod in modules.values():
        if mod is not None:
            enrich(mod, modules)


