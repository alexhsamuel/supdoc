import html
import inspect
import logging
import markdown
import re
import xml.etree.ElementTree as ET

from   .lib.itr import PeekIter
from   .lib.text import get_indent, get_common_indent, join_pars

#-------------------------------------------------------------------------------

def markup_error(description):
    logging.warning(description)


#-------------------------------------------------------------------------------

JAVADOC_ARG_TAGS = frozenset({
    "cvar",
    "ivar",
    "param",
    "raise",
    "raises",
    "type",
    "var",
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
                    text=parse_formatting("\n".join(text)),
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
        # Finish the last tag.
        javadoc.append(dict(
            tag =tag, 
            arg =arg, 
            text=parse_formatting("\n".join(text))
        ))
    
    # FIXME: Handle some aliases, for instance "returns" for "return" and
    # "raises" for "raise".

    return doc_lines, javadoc


#-------------------------------------------------------------------------------

DOUBLE_BACKTICK_REGEX   = re.compile(r"``(.+?)``")
SINGLE_BACKTICK_REGEX   = re.compile(r"`(.+?)`")

# For underscore-delimited text, require a space before the opening underscore
# but no space after it, vice versa for the closing underscore.  Also limit the
# length of the enclosed text.
UNDERSCORE_REGEX        = re.compile(r"(\s)_([^\s].{,128}[^\s])_(\s)")
# Likewise for single- and double-asterisk.
DOUBLE_ASTERISK_REGEX   = re.compile(r"(\s)\*\*([^\s].{,128}[^\s])\*\*(\s)")
ASTERISK_REGEX          = re.compile(r"(\s)\*([^\s].{,128}[^\s])\*(\s)")

def parse_formatting(text):
    # Look for ``-delimited strings.
    text = DOUBLE_BACKTICK_REGEX.sub(r'<code>\1</code>', text)
    # Look for `-delimited strings.
    text = SINGLE_BACKTICK_REGEX.sub(r'<code>\1</code>', text)

    # text = markdown.markdown(text, output_format="html5")

    text = UNDERSCORE_REGEX.sub(r'\1<i>\2</i>\3', text)
    text = DOUBLE_ASTERISK_REGEX.sub(r'\1<b>\2</b>\3', text)
    text = ASTERISK_REGEX.sub(r'\1<i>\2</i>\3', text)

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
        pars = PeekIter(pars)
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


# FIXME: This is a stop-gap.  In order to handle default values and annotations
# correctly, we need to extract the signature (from a javadoc tag or whatever)
# at the time we're first inspecting the object, and parse the signature at 
# that time.  That will allow us to provide the right context for evaluating
# the default value and annotation expressions, and to inspect the resulting
# values.

def parse_signature(name, signature):
    """
    @param name
      The expected name of the function.
    @parma signature
      A string containing the function signature.
    """
    # Write an empty function with this signature.
    fn_src = "def {}:\n  pass\n".format(signature)

    # For evaluation, use a fake globals dict.  We don't have access to 
    # the global context for the object for which this is the signature;
    class Globals(dict):
        # This is called when an annotation or default parameter value 
        # references some name.
        def __getitem__(self, name):
            return name
        # This should be called once: to add the function definition.
        def __setitem__(self, attr_name, fn):
            assert attr_name == name
            self.signature = inspect.signature(fn)

    # Now evaluate it.  
    # FIXME: This allows evaluation of arbitrary expressions.
    namespace = Globals()
    exec(fn_src, namespace)

    # Fish out the produced function, and get its signature.
    sig = namespace.signature

    # For now, return a string.  But see the FIXME above.
    def make(obj):
        return {
          "repr": str(obj),
          "type": {
            "$ref": "#/modules/builtins/dict/str",
            "type": {
              "$ref": "#/modules/builtins/dict/type"
            }
          },
          "type_name": "str"
        }

    # Exctract docs from the signature.

    def inspect_parameter(param):
        jso = {
            "name": param.name,
            "kind": str(param.kind),
        }
        if param.annotation is not param.empty:
            jso["annotation"] = make(param.annotation)  # FIXME
        if param.default is not param.empty:
            jso["default"] = make(param.default)  # FIXME
        return jso

    jso = {
        "params": [ inspect_parameter(p) for p in sig.parameters.values() ]
    }
    if sig.return_annotation != inspect.Signature.empty:
        jso["return"] = {"annotation": make(sig.return_annotation)}  # FIXME

    return jso


def attach_javadoc_to_signature(doc):
    try:
        javadoc = doc["docs"]["javadoc"]
    except KeyError:
        # No javadoc annotations.
        return

    # If this is a callable but has no signature, and there is a @signature
    # annotation, use it.
    if doc.get("callable", False) and "signature" not in doc:
        sig = [ e for e in javadoc if e["tag"] == "signature" ]
        if len(sig) > 0:
            sig = sig[0]["text"].strip()
            try:
                doc["signature"] = parse_signature(doc["name"], sig)
            except Exception as e:
                print(e)
                return

    try:
        signature = doc["signature"]
    except KeyError:
        # No signature to annotate.
        return

    params = { s["name"] : s for s in signature.get("params", ()) }

    for entry in javadoc:
        tag = entry["tag"]

        # Attach parameter annotations: @param and @type.
        if tag in {"param", "type"}:
            name = entry["arg"]
            try:
                param = params[name]
            except KeyError:
                markup_error(
                    "no matching parameter for @{} {}".format(tag, name))
            else:
                key = "doc" if tag == "param" else "doc_type"
                param[key] = entry["text"]

        # Attach return type annotations: @return and @rtype.
        if tag in {"return", "rtype"}:
            ret = signature.setdefault("return", {})
            key = "doc" if tag == "return" else "doc_type"
            # If an annotation was given more than once, we use the last.
            ret[key] = entry["text"]

        # Attach exception annotations.
        if tag in {"raise"}: 
            signature.setdefault("exceptions", []).append({
                "exc_type": entry["arg"],
                "doc": entry["text"],
            })



def attach_javadoc_to_members(doc):
    """
    Attaches javadoc annotations to the doc's dict members.
    """
    javadoc = doc.get("docs", {}).get("javadoc", {})
    for entry in javadoc:
        if entry["tag"] == "cvar":  # A class variable.
            # FIXME: Make sure this is a type.
            name = entry["arg"]
            try:
                member = doc["dict"][name]
            except KeyError:
                continue
            else:
                # FIXME: Don't replace.
                member["docs"] = parse_doc_markdown(entry["text"])


#-------------------------------------------------------------------------------

def markdown_to_et(text):
    """
    Parses as Markdown to `ElementTree`.
    """
    # Process as Markdown.
    from . import markdown_doctest
    html = markdown.markdown(
        text, output_format="html5", 
        extensions=(
            "codehilite", 
            "fenced_code", 
            markdown_doctest.Extension(),
        ))

    # Parse it back.  
    # FIXME: Teach markup to emit ElementTree directly?
    # The parser expects a single element, so wrap it.
    try:
        from lxml.etree import HTMLParser
        et = ET.fromstring('<html>' + html + '</html>', parser=HTMLParser())
    except ET.ParseError as exc:
        # FIXME: If the source includes invalid HTML, such as unclosed tags,
        # so will the output, will will lead to parse errors.  For now, just
        # report these and produce an error..
        logging.error("-" * 80 + "\n" + html + "\n" + str(exc) + "\n\n")
        return ET.fromstring('<strong>Error parsing Markdown output.</strong>')

    # Unwrap the body.
    if et.tag.lower() == "html" and len(et) == 1 and et[0].tag.lower() == "body":
        et = et[0]

    return et


def parse_doc_markdown(docstring):
    """
    Parses a docstring as Markdown.
    """
    # Remove common indentation.
    _, lines = get_common_indent(docstring.splitlines(), ignore_first=True)

    # Filter and parse Javadoc tags.
    lines, javadoc = find_javadoc(lines)

    docstring = "\n".join(lines)

    # Replace 'doc' with the de-indented version, since that's nicer.
    result = {"doc": docstring}

    et = markdown_to_et(docstring)

    tostring = lambda e: ET.tostring(e, method="html", encoding="unicode")

    def content(e):
        return (html.escape(e.text or "")) + "".join( tostring(c) for c in e )

    # If the first element is a paragraph, use that as the summary.
    if len(et) > 0 and et[0].tag.lower() == 'p':
        summary = et[0]
        et.remove(summary)
        # Get the summary contents, without the enclosing <p> element.
        result["summary"] = content(summary)

    # Reassemble the HTML source.
    result["body"] = "\n".join( tostring(e) for e in et )

    # Add javadoc.
    if len(javadoc) > 0:
        result["javadoc"] = javadoc

    return result


#-------------------------------------------------------------------------------

def enrich(odoc):
    docs = odoc.get("docs", {})
    try:
        doc = docs["doc"]
    except KeyError:
        pass
    else:
        # docs.update(parse_doc(doc))
        docs.update(parse_doc_markdown(doc))
        attach_javadoc_to_signature(odoc)
        attach_javadoc_to_members(odoc)

    # FIXME
    for val in odoc.get("dict", {}).values():
        enrich(val)


