import argparse

import pygments
import pygments.lexers
import pygments.formatters

from   .tags import *
from   .. import inspector, path
from   .. import terminal  # FIXME
from   ..objdoc import *
from   ..path import Path
from   aslib import if_none
from   aslib import itr, py
import aslib.json

#-------------------------------------------------------------------------------

def format_modname(modname):
    return CODE(modname, cls="module")


def make_url(path):
    return "/{}/{}".format(path.modname, path.qualname or "")


def format_identifier(path, *, full="auto", context=None):
    """
    Formats an identifier.

    @type path
      `Path`
    @param context
      The module name of the current context.
    """
    modname, name = path

    if path.qualname is None:
        element = CODE(path.modname, cls="module")
    elif (   modname == "builtins"
        or not full
        or (    full == "auto" 
            and context is not None and context.modname != path.modname)):
        element = CODE(path.qualname)
    else:
        element = SPAN(
            CODE(path.modname, cls="module"),
            ".",
            CODE(path.qualname))

    return A(element, href=make_url(path), cls="identifier")
    
    
# FIXME: Remove.
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


def format_type_summary(objdoc, modname=None):
    div = DIV(H2("Type"))

    bases   = objdoc.get("bases")
    mro     = objdoc.get("mro")

    if bases is not None:
        div.append(DIV(
            "Base types: ", 
            *( format_identifier(get_path(base), context=Path(modname))
               for base in bases )))
    if mro is not None:
        mro_div = DIV("MRO: ")
        for first, mro_type in aslib.itr.first(mro):
            if not first:
                mro_div.append(" \u2192 ")
            mro_div.append(
                format_identifier(get_path(mro_type), context=Path(modname)))
        div.append(mro_div)

    return div


def format_property_summary(docsrc, objdoc):
    div = DIV(H2("Property"))

    for accessor_name in ("get", "set", "del"):
        accessor = objdoc.get(accessor_name)
        accessor = None if accessor is None else docsrc.resolve(accessor)
        div.append(DIV(
            accessor_name + ": ",
            "none" if accessor is None 
            else _print_member(docsrc, accessor, None)))

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


# FIXME: WTF is this signature anyway?
def format_member(docsrc, objdoc, lookup_path, show_type=True):
    if lookup_path is None:
        lookup_name     = None
        parent_name     = None
    else:
        lookup_parts    = lookup_path.qualname.split(".")
        lookup_name     = lookup_parts[-1]
        parent_name     = None if len(lookup_parts) == 1 else lookup_parts[-2] 

    if is_ref(objdoc):
        # Find the full name from which this was imported.
        import_path = get_path(objdoc)
        # Read through the ref.
        try:
            resolved = docsrc.resolve(objdoc)
        except LookupError:
            pass
        else:
            if resolved is not None:
                objdoc = resolved
    else:
        import_path = None

    name            = objdoc.get("name")
    module          = objdoc.get("module")
    modname         = None if module is None else parse_ref(module)[0]
    unmangled_name  = if_none(terminal.unmangle(lookup_name, parent_name), name)
    type_name       = objdoc.get("type_name")
    type_           = objdoc.get("type")
    repr            = objdoc.get("repr")
    callable        = is_callable(objdoc)
    signature       = get_signature(objdoc)
    docs            = objdoc.get("docs", {})
    summary         = docs.get("summary")
    body            = docs.get("body")

    # Show the repr if this is not a callable or one of several other
    # types with uninteresting reprs.
    show_repr = (
            repr is not None 
        and signature is None 
        and type_name not in ("module", "property", "type", )
    )

    div = DIV(CODE(unmangled_name, cls="identifier"))
    if is_function_like(objdoc):
        div.append(format_signature(docsrc, objdoc))
        
    # If this is a mangled name, we showed the unmangled name earlier.  Now
    # show the mangled name too.
    if unmangled_name != lookup_name and lookup_name is not None:
        div.append(" \u224b ")
        div.append(CODE(lookup_name, cls="identifier"))

    if show_type:
        nice_type = terminal.format_nice_type_name(objdoc, lookup_path)
        if nice_type is None:
            nice_type = type_name
        div.append(DIV(CODE(nice_type, cls="type")))

    # Show where this was imported from.
    if import_path is not None:
        path = format_idenifier(
            import_path, 
            context=None if lookup_path is None else lookup_path)
        div.append(DIV("import \u21d2 ", path))

    if show_repr:
        div.append(DIV("= ", CODE(repr)))

    if summary is not None:
        docs = DIV(summary, cls="docs")
        if body:
            # Don't print the body, but indicate that there are more docs.
            docs.append("\u2026")
        div.append(docs)

    return div


def format_members(docsrc, dict, parent_path, show_type=True, imports=True):
    ul = UL()
    for name in sorted(dict):
        objdoc = dict[name]
        if imports or not is_ref(objdoc):
            # FIXME: Even if parent_path is None, we need to pass the local
            # name, in case the object doesn't know its own name.
            lookup_path = None if parent_path is None else parent_path / name
            ul.append(LI(
                format_member(docsrc, objdoc, lookup_path, show_type)))
    return ul


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
        # div.append(PRE(source_text, cls="source"))
        lexer = pygments.lexers.get_lexer_by_name("python")
        formatter = pygments.formatters.get_formatter_by_name(
            "html", cssclass="source")
        div.append(pygments.highlight(source_text, lexer, formatter))

    return div


def generate(docsrc, objdoc, lookup_path):
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

    head = HEAD(LINK(
        rel="stylesheet", type="text/css", href="/static/supdoc.css"))
    body = BODY()

    signature = \
        format_signature(docsrc, objdoc) if is_function_like(objdoc) else ""
    body.append(
        DIV(CODE(display_name, signature, cls="identifier"), cls="name"))
    
    details = DIV(cls="details")

    # Show its type.
    type            = objdoc.get("type")
    type_name       = objdoc.get("type_name")
    type_path       = get_path(type)
    instance_of = \
        ("instance of ", format_identifier(type_path, context=Path(lookup_modname)))
    nice_type_name = terminal.format_nice_type_name(objdoc, lookup_path)
    if nice_type_name is not None:
        instance_of = (nice_type_name, " (", *instance_of, ")")
    details.append(DIV(*instance_of))

    # Show the module name.
    if type_name != "module" and module is not None:
        details.append(DIV(
            "in module ",
            format_identifier(Path(parse_ref(module)[0], None))
        ))

    # Show the mangled name.
    if mangled_name is not None:
        details.append(DIV(
            "external name ", CODE(mangled_name, cls="identifier")))

    body.append(details)

    # Show documentation.
    docs = objdoc.get("docs")
    if docs is not None:
        body.append(format_docs(docs))

    # Summarize type.
    if type_name == "type":
        body.append(format_type_summary(objdoc, modname))

    # Summarize property.
    if type_name == "property":
        body.append(format_property(objdoc))

    signature = get_signature(objdoc)
    if signature is not None and len(signature) > 0:
        body.append(format_parameter_docs(signature))

    #----------------------------------------
    # Summarize contents.

    # FIXME
    private = False
    imports = False

    partitions = terminal._partition_members(terminal.get_dict(objdoc, private) or {})

    contents = DIV(cls="contents")

    partition = partitions.pop("modules", {})
    if len(partition) > 0:
        contents.extend((
            H2("Modules"),
            format_members(docsrc, partition, path, False, imports=imports)
        ))

    partition = partitions.pop("types", {})
    if len(partition) > 0:
        contents.extend((
            H2("Types" if type_name == "module" else "Member Types"),
            format_members(docsrc, partition, path, False, imports=imports)
        ))

    partition = partitions.pop("properties", {})
    if len(partition) > 0:
        contents.extend((
            H2("Properties"),
            format_members(docsrc, partition, path, True, imports=imports)
        ))

    partition = partitions.pop("functions", {})
    if len(partition) > 0:
        contents.extend((
            H2("Functions" if type_name == "module" else "Methods"),
            format_members(docsrc, partition, path, True, imports=imports)
        ))

    partition = partitions.pop("attributes", {})
    if len(partition) > 0:
        contents.extend((
            H2("Attributes"),
            format_members(docsrc, partition, path, True)
        ))

    body.append(contents)

    #----------------------------------------

    # Summarize the source.
    source = objdoc.get("source")
    if source is not None:
        body.append(format_source(source))

    # yield from HTML(head, body).format()
    return HTML(head, body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", metavar="PATH", 
        help="FIXME")
    args = parser.parse_args()

    lookup_path, _ = path.split(args.path)

    docsrc = inspector.DocSource(source=True)
    objdoc = docsrc.get(lookup_path)

    print("<!DOCTYPE html>")
    print(generate(docsrc, objdoc, lookup_path))


if __name__ == "__main__":
    main()

