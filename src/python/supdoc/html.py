import argparse

from   . import inspector, path
from   . import terminal  # FIXME
from   .htmlgen import *
from   .objdoc import *
import aslib.json

#-------------------------------------------------------------------------------

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
    if path.qualname is None or path.modname not in ("builtins", modname):
        yield SPAN(path.modname, cls="module")
        if path.qualname is not None:
            yield "."
    if path.qualname is not None:
        yield SPAN(path.qualname, cls="identifier")


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
        result = SPAN(prefix, param.name, cls="parameter")
        yield result


def format_signature(docsrc, objdoc):
    sig = get_signature(objdoc)
    span = SPAN("(", cls="signature")
    if sig is None:
        span.append(SPAN("??", cls="missing"))
    else:
        sig = signature_from_jso(sig, docsrc)
        span.extend(format_parameters(sig.parameters))
    span.append(")")
    return span


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
    body.append(H1(SPAN(display_name, signature, cls="identifier")))
    
    # Show its type.
    type            = objdoc.get("type")
    type_name       = objdoc.get("type_name")
    type_path       = get_path(type)
    instance_of = ("instance of ", *format_path(type_path, modname=lookup_modname))
    nice_type_name = terminal.format_nice_type_name(objdoc, lookup_path)
    if nice_type_name is not None:
        instance_of = (nice_type_name, " (", *instance_of, ")")
    body.append(DIV(*instance_of))

    # Show the module name.
    if type_name != "module" and module is not None:
        body.append(DIV(
            "in module ",
            *format_path(Path(parse_ref(module)[0], None))
        ))

    # # Show the mangled name.
    # if mangled_name is not None:
    #     pr << "external name "
    #     with pr(**STYLES["mangled_name"]):
    #         pr << mangled_name << NL 
    #     pr << NL

    # # Summarize the source.
    # if source is not None:
    #     loc         = source.get("source_file") or source.get("file")
    #     source_text = source.get("source")

    #     if loc is not None or source_text is not None:
    #         header("Source")

    #     if loc is not None:
    #         with pr(**STYLES["path"]):
    #             pr << loc
    #         lines = source.get("lines")
    #         if lines is not None:
    #             start, end = lines
    #             pr >> " lines {}-{}".format(start + 1, end + 1)
    #         pr << NL << NL

    #     if source_text is not None:
    #         with pr(indent="\u2506 ", **STYLES["source"]):
    #             pr.elide(source_text)
    #         pr << NL << NL

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

