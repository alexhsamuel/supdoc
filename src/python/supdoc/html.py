import argparse

from   . import inspector, path
from   . import terminal  # FIXME
from   .htmlgen import *
from   .objdoc import *
from   aslib import itr
import aslib.json

#-------------------------------------------------------------------------------

def format_modname(modname):
    return CODE(modname, cls="module")


def format_path(path, *, modname=None):
    """
    Formats a fully-qualified path.

    Prints the path, including modname and qualname.  If the modname matches
    the context `modname`, it is not shown.  Also, if the modname is "builtins",
    it is not shown.

    @type path
      `Path`.
    @param modname
      The context module name. 
    """
    span = CODE()
    if path.qualname is None or path.modname not in ("builtins", modname):
        span.append(format_modname(path.modname))
        if path.qualname is not None:
            span.append(".")
    if path.qualname is not None:
        span.append(CODE(path.qualname, cls="identifier"))
    return span


def format_parameters(parameters):
    star = False
    for param in parameters.values():
        prefix = None
        if param.kind is Parameter.KEYWORD_ONLY and not star:
            yield "*"
            star = True
        elif param.kind is Parameter.VAR_POSITIONAL:
            prefix = "*"
            star = True
        elif param.kind is Parameter.VAR_KEYWORD:
            prefix = "**"
            star = True
        result = CODE(prefix, param.name, cls="parameter")
        yield result


def format_signature(docsrc, objdoc):
    sig = get_signature(objdoc)
    span = CODE("(", cls="signature")
    if sig is None:
        span.append(SPAN("??", cls="missing"))
    else:
        sig = signature_from_jso(sig, docsrc)
        for first, param in itr.first(format_parameters(sig.parameters)):
            if not first:
                span.append(", ")
            span.append(param)
    span.append(")")
    return span


def format_docs(docs):
    div = DIV(H2("Documentation"), cls="docs")

    summary = docs.get("summary", "")
    body    = docs.get("body", "")

    # Show the doc summary.
    if summary:
        div.append(DIV(summary, cls="summary"))
    # Show the doc body.
    if body:
        div.append(DIV(body))

    return div


def format_parameter_docs(signature):
    div = DIV(H2("Parameters"), cls="parameters")
    ul = UL()
    for param in signature["params"]:
        name        = param["name"]
        default     = param.get("default")
        doc_type    = param.get("doc_type")
        doc         = param.get("doc")

        li = LI()
        li.append(CODE(name, cls="identifier"))
        if default is not None:
            li.extend((" = ", CODE(default["repr"])))

        if doc_type is not None:
            li.append(DIV("type: ", CODE(doc_type)))

        if doc is not None:
            li.append(DIV(doc))

        ul.append(li)
    div.append(ul)

    # Show the return type type and documentation.
    ret = signature.get("return")
    if ret is not None:
        doc         = ret.get("doc")
        doc_type    = ret.get("doc_type")

        div.append(H2("Return type"))
        if doc_type is not None:
            div.append(DIV(doc_type))
        if doc is not None:
            div.append(doc)

    return div


def format_source(source):
    div = DIV(H2("Source"))

    loc         = source.get("source_file") or source.get("file")
    source_text = source.get("source")

    if loc is not None:
        div.append(SPAN(loc, cls="path"))
        lines = source.get("lines")
        if lines is not None:
            start, end = lines
            div.append(" lines {}-{}".format(start + 1, end + 1))

    if source_text is not None:
        div.append(PRE(source_text, cls="source"))

    return div


def generate(docsrc, objdoc, lookup_path):
    yield "<!DOCTYPE html>"
    
    path            = get_path(objdoc) or lookup_path
    name            = objdoc.get("name")
    qualname        = objdoc.get("qualname")
    mangled_name    = objdoc.get("mangled_name")
    display_name = (
             qualname if qualname is not None
        else lookup_path.qualname if lookup_path is not None
        else name
    )
    
    module          = objdoc.get("module")
    modname         = (
             parse_ref(module)[0] if module is not None
        else lookup_path.modname if lookup_path is not None
        else None
    )
    lookup_modname  = None if lookup_path is None else lookup_path.modname

    head = HEAD(LINK(rel="stylesheet", type="text/css", href="supdoc.css"))
    body = BODY()

    signature = format_signature(docsrc, objdoc) if is_function_like(objdoc) else ""
    body.append(H1(CODE(display_name, signature, cls="identifier")))
    
    # Show its type.
    type            = objdoc.get("type")
    type_name       = objdoc.get("type_name")
    type_path       = get_path(type)
    instance_of = ("instance of ", format_path(type_path, modname=lookup_modname))
    nice_type_name = terminal.format_nice_type_name(objdoc, lookup_path)
    if nice_type_name is not None:
        instance_of = (nice_type_name, " (", *instance_of, ")")
    body.append(DIV(*instance_of))

    # Show the module name.
    if type_name != "module" and module is not None:
        body.append(DIV(
            "in module ",
            format_path(Path(parse_ref(module)[0], None))
        ))

    # Show the mangled name.
    if mangled_name is not None:
        body.append(DIV(
            "external name ", CODE(mangled_name, cls="identifier")))

    # Show documentation.
    docs = objdoc.get("docs")
    if docs is not None:
        body.append(format_docs(docs))

    signature = get_signature(objdoc)
    if signature is not None and len(signature) > 0:
        body.append(format_parameter_docs(signature))

    # Summarize the source.
    source = objdoc.get("source")
    if source is not None:
        body.append(format_source(source))

    # yield from HTML(head, body).format()
    yield HTML(head, body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", metavar="PATH", 
        help="FIXME")
    args = parser.parse_args()

    lookup_path, _ = path.split(args.path)

    docsrc = inspector.DocSource(source=True)
    objdoc = docsrc.get(lookup_path)
    # aslib.json.pprint(objdoc)  # FIXME

    for line in generate(docsrc, objdoc, lookup_path):
        print(line)


if __name__ == "__main__":
    main()

