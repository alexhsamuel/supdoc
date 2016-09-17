import argparse
from   html import escape

import pygments
import pygments.lexers
import pygments.formatters

from   .tags import *
from   .. import inspector, modules, path
from   .. import terminal  # FIXME
from   ..objdoc import *
from   ..path import Path
from   aslib import if_none
from   aslib import itr, log, memo, py
import aslib.json

#-------------------------------------------------------------------------------

def format_modname(modname):
    return CODE(modname, cls="module")


def make_url(path):
    return "/{}/{}".format(path.modname, path.qualname or "")


# find_modules = memo.memoize(lambda: list(modules.find_modules_in_path))
find_modules = modules.find_modules_in_path

def format_module_list():
    module_list = UL()
    module_list.append(DIV("Modules", cls="heading"))
    for modname in find_modules():
        if "." in modname:
            # For submodules, show only the last component, but indented.
            name = (
                "&nbsp;" * (2 * modname.count("."))
                + "." + modname.rsplit(".", 1)[1]
            )
        else:
            name = modname

        el = CODE(name, cls="modname identifier")
        el = A(el, href=make_url(Path(modname)))
        module_list.append(LI(el))
    return DIV(module_list, cls="module-list")


def format_name(path, *, name=None, relative_to=None):
    modname, qualname = path
    if name is not None:
        qualname = (
            qualname.rsplit(".", 1)[0] + "." + name 
            if qualname is not None and "." in qualname
            else name
        )
    
    if relative_to is None:
        pass
    elif relative_to.modname != modname:
        # In a different module.
        pass
    elif qualname is None:
        # It's the module itself; show it fully.
        pass
    elif relative_to.qualname is None:
        # Relative to the module: show qualname only.
        modname = None
    elif qualname.startswith(relative_to.qualname + "."):
        # Sub-qualname; omit the common prefix.
        modname = None
        qualname = qualname[len(relative_to.qualname) + 1 :]

    if modname == "builtins":
        modname = None

    if modname is None:
        element = CODE(qualname, cls="qualname")
    elif qualname is None:
        element = CODE(modname, cls="modname")
    else:
        element = CODE(
            CODE(modname, cls="modname"), ".",
            CODE(qualname, cls="qualname"),
        )

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
    div = DIV(cls="docs")

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
            *( format_name(get_path(base), relative_to=Path(modname))
               for base in bases )))
    if mro is not None:
        mro_div = DIV("MRO: ")
        for first, mro_type in aslib.itr.first(mro):
            if not first:
                mro_div.append(" \u2192 ")
            mro_div.append(
                format_name(get_path(mro_type), relative_to=Path(modname)))
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


def format_signature_summary(docsrc, objdoc):
    div = DIV(
        H2("Signature"), 
        CODE(objdoc["name"]), format_signature(docsrc, objdoc), 
        cls="signature")
    signature = get_signature(objdoc)

    if signature is None:
        div.append(DIV("no parameter information available", cls="missing"))

    else:
        def format_param(param):
            name        = param["name"]
            default     = param.get("default")
            doc_type    = param.get("doc_type")
            doc         = param.get("doc")

            li = LI()
            li.append(CODE(name, cls="identifier"))
            if default is not None:
                li.extend((" = ", CODE(escape(default["repr"]))))
            if doc_type is not None:
                li.append(DIV("type: ", CODE(doc_type)))
            if doc is not None:
                li.append(DIV(doc))
            return li

        div.append(UL(*( format_param(p) for p in signature["params"] )))

        # Show the return type type and documentation.
        ret = signature.get("return")
        if ret is not None:
            doc         = ret.get("doc")
            doc_type    = ret.get("doc_type")

            div.append(H3("Return type"))
            if doc_type is not None:
                div.append(DIV(doc_type))
            if doc is not None:
                div.append(doc)

    return div


# FIXME: WTF is this signature anyway?
def format_member(docsrc, objdoc, lookup_path, *, context_path=None, 
                  show_type=True):
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
        except (LookupError, QualnameError):
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

    dt = DT(
        format_name(lookup_path, relative_to=context_path, name=unmangled_name))
    if is_function_like(objdoc):
        dt.append(format_signature(docsrc, objdoc))
        
    if show_type:
        nice_type = terminal.format_nice_type_name(objdoc, lookup_path)
        if nice_type is None:
            nice_type = type_name
        dt.extend((" &mdash;&mdash; ", CODE(nice_type, cls="type")))

    dd = DD(cls="rest")

    # Show where this was imported from.
    if import_path is not None:
        path = format_name(import_path, relative_to=lookup_path)
        dd.append(DIV("import \u21d2 ", path))

    if show_repr and repr is not None:
        dd.append(DIV("= ", CODE(escape(repr))))

    if summary is not None:
        docs = DIV(summary)
        if body:
            # Don't print the body, but indicate that there are more docs.
            docs.append("\u2026")
        dd.append(docs)

    return dt, dd


def format_members(docsrc, dict, parent_path, show_type=True, imports=True):
    div = DL(cls="members")
    for name in sorted(dict):
        objdoc = dict[name]
        if imports or not is_ref(objdoc):
            # FIXME: Even if parent_path is None, we need to pass the local
            # name, in case the object doesn't know its own name.
            lookup_path = None if parent_path is None else parent_path / name
            div.extend(format_member(
                docsrc, objdoc, lookup_path, 
                context_path=parent_path, show_type=show_type))
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
        # div.append(PRE(source_text, cls="source"))
        lexer = pygments.lexers.get_lexer_by_name("python")
        formatter = pygments.formatters.get_formatter_by_name(
            "html", cssclass="source")
        div.append(pygments.highlight(source_text, lexer, formatter))

    return div


def generate(docsrc, objdoc, lookup_path):
    # If this is a ref, follow it.
    from_path   = lookup_path or get_path(objdoc)
    while is_ref(objdoc):
        path = parse_ref(objdoc)
        # FIXME: pr << format_path(from_path) << IMPORT_ARROW << NL
        objdoc = docsrc.resolve(objdoc)
        from_path = path

    path            = get_path(objdoc) or lookup_path
    name            = objdoc.get("name")
    qualname        = objdoc.get("qualname")
    mangled_name    = objdoc.get("mangled_name")
    display_name = (
             qualname if qualname is not None
        else name
    )
    type            = objdoc.get("type")
    type_name       = objdoc.get("type_name")
    type_path       = get_path(type)
    
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
    body_content = DIV(id="content")
    body.append(body_content)

    module_list = format_module_list()
    module_list["id"] = "module-sidebar"
    body_content.append(module_list)

    doc = DIV(id="main")
    body_content.append(doc)

    details = DIV(cls="details box")

    # Show its type.
    instance_of = (
        "instance of ", 
        format_name(type_path, relative_to=Path(lookup_modname)),
    )
    nice_type_name = terminal.format_nice_type_name(objdoc, lookup_path)
    if nice_type_name is not None:
        instance_of = (nice_type_name, " (", *instance_of, ")")
    details.append(DIV(*instance_of))

    # Show the module name.
    if type_name != "module" and module is not None:
        details.append(
            DIV("in module ", format_name(Path(parse_ref(module)[0]))))

    # Show the mangled name.
    if mangled_name is not None:
        details.append(DIV(
            "external name ", CODE(mangled_name, cls="identifier")))

    # FIXME: Use a better icon.
    details.append(DIV(A(
        SPAN("JSON", cls="mini-icon"), 
        href=make_url(lookup_path) + "?format=json"),
        style="margin: 8px 0; "
    ))

    doc.append(details)

    main = DIV(cls="main box")

    main.append(DIV(CODE(display_name, cls="identifier"), cls="name"))

    # Show documentation.
    docs = objdoc.get("docs")
    if docs is not None:
        main.append(format_docs(docs))

    # Summarize type.
    if type_name == "type":
        main.append(format_type_summary(objdoc, modname))

    # Summarize property.
    if type_name == "property":
        main.append(format_property(objdoc))

    if is_function_like(objdoc):
        main.append(format_signature_summary(docsrc, objdoc))

    doc.append(main)

    # doc.append(DIV(cls="clear"))

    #----------------------------------------
    # Summarize contents.

    # FIXME
    private = True
    imports = True

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

    doc.append(contents)

    #----------------------------------------

    # Summarize the source.
    source = objdoc.get("source")
    if source is not None:
        doc.append(format_source(source))

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

