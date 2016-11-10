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


def format_objdoc(objdoc, relative_to=None):
    if is_ref(objdoc):
        path = parse_ref(objdoc)
        return format_name(parse_ref(objdoc), relative_to=relative_to)
    else:
        return CODE(objdoc["repr"])


def icon(name):
    # <svg class="icon-twitter">
    #   <use xlink:href="/images/icons.svg#icon-twitter"></use>
    # </svg>
    name = "icon-" + str(name)
    url = "/static/icons.svg#" + name
    return SVG(
        USE(**{"xlink:href": url}),
        cls=name)


def make_list(items, tag=UL, start=None, cls=None):
    list = tag(*( LI(i) for i in items ))
    if cls is not None:
        list["cls"] = cls
    if start is not None:
        list["start"] = start
    return list


def format_modname(modname):
    return CODE(modname, cls="module")


def make_url(path):
    return "/{}/{}".format(path.modname, path.qualname or "")


# find_modules = memo.memoize(lambda: list(modules.find_modules_in_path))
find_modules = modules.find_modules_in_path

def format_module_list():
    module_list = UL(DIV("Modules", cls="heading"))
    for modname in find_modules():
        if "." in modname:
            # For submodules, show only the last component, but indented.
            name = (
                "&nbsp;" * (2 * modname.count("."))
                + "." + modname.rsplit(".", 1)[1]
            )
        else:
            name = modname
        module_list << LI(A(
            CODE(name, cls="modname identifier"), 
            href=make_url(Path(modname))
        ))
    return DIV(module_list, cls="module-list")


def format_parameters(params):
    star = False
    for param in params:
        prefix = None
        kind = param["kind"]
        if kind == "KEYWORD_ONLY" and not star:
            yield "*"
            star = True
        elif kind == "VAR_POSITIONAL":
            prefix = "*"
            star = True
        elif kind == "VAR_KEYWORD":
            prefix = "**"
            star = True
        yield CODE(prefix, param["name"], cls="parameter")


def format_signature(docsrc, objdoc):
    sig = get_signature(objdoc)
    span = CODE("(", cls="signature")
    if sig is None:
        span << SPAN("??", cls="missing")
    else:
        for first, param in itr.first(format_parameters(sig["params"])):
            if not first:
                span << ", "
            span << param
    span << ")"
    return span


def format_docs(docs):
    div = DIV(cls="docs")
    # Show the doc summary.
    summary = docs.get("summary", "")
    if summary:
        div << DIV(summary, cls="summary")
    # Show the doc body.
    body = docs.get("body", "")
    if body:
        div << DIV(body, cls="body")
    return div


def format_property_summary(docsrc, objdoc, lookup_path):
    div = DIV(H2("Property"))

    for accessor_name in ("get", "set", "del"):
        accessor = objdoc.get(accessor_name)
        accessor = None if accessor is None else docsrc.resolve(accessor)
        div << DIV(
            accessor_name + ": ",
            "none" if accessor is None 
            else format_member(docsrc, accessor, lookup_path))

    return div


def format_signature_summary(docsrc, objdoc):
    div = DIV(cls="signature")
    signature = get_signature(objdoc)

    if signature is None:
        div << DIV("no parameter information available", cls="missing")

    else:
        ul = div << UL(cls="params")  # FIXME: cls="signature"

        def format_param(param):
            name        = param["name"]
            kind        = param["kind"]
            default     = param.get("default")
            doc_type    = param.get("doc_type")
            doc         = param.get("doc")
            annotation  = param.get("annotation")

            icon_name = {
                "POSITIONAL_OR_KEYWORD" : "right-circled",
                "POSITIONAL_ONLY"       : "cc-zero",
                "KEYWORD_ONLY"          : "cc-nd",
                "VAR_POSITIONAL"        : "star",
                "VAR_KEYWORD"           : "star-empty",
            }[kind]

            li = LI(
                DIV(icon(icon_name), cls="bullet"),
                SPAN("parameter ", cls="light"),
                CODE(name, cls="identifier"))
            if default is not None:
                li << " = "
                li << format_objdoc(default)
            if doc_type is not None:
                li << DIV("type: ", CODE(doc_type))
            if annotation is not None:
                li << DIV("annotation: ", format_objdoc(annotation))
            if doc is not None:
                li << DIV(doc)
            return li

        ul.extend( format_param(p) for p in signature["params"] )

        def format_exception(exc):
            type    = exc["exc_type"]
            doc     = exc["doc"]
            return LI(
                DIV(icon("alert"), cls="bullet"),
                SPAN("raises ", cls="light"),
                CODE(type, cls="identifier"),
                None if doc is None else DIV(doc))
            
        ul.extend(
            format_exception(e) for e in signature.get("exceptions", ()) )

        # Show the return type type and documentation.
        ret = signature.get("return")
        if ret is not None:
            doc_type = ret.get("doc_type")
            doc = ret.get("doc")
            ul << LI(
                DIV(icon("right-thin"), cls="bullet"),
                SPAN("returns ", cls="light"),
                None if doc_type is None else CODE(doc_type),
                None if doc is None else DIV(doc))

    return div


# Names of types of which objects' reprs are not interesting.
# FIXME: Share with terminal docs.
SUPPRESS_REPR_TYPES = {
    "classmethod_descriptor", 
    "getset_descriptor", 
    "module", 
    "property", 
    "type", 
}

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

    cls = ("member", "clearfix", )
    if import_path is not None:
        cls += ("imported-name", )
    # FIXME: Not quite right: name may be None.
    if name is not None and name.startswith("_"):
        cls += ("private-name", )
    url = make_url(lookup_path)
    result = DIV(cls=cls, onclick="window.location='{}';".format(url))

    head = result << DIV(cls="head")

    title = head << DIV(cls="title identifier")
    title << format_name(
        lookup_path, relative_to=context_path, name=unmangled_name)
    if is_function_like(objdoc):
        title << format_signature(docsrc, objdoc)
        
    # Show the repr if this is not a callable or one of several other
    # types with uninteresting reprs.
    if (
            repr is not None 
        and signature is None 
        and type_name not in SUPPRESS_REPR_TYPES
    ):
        head << DIV(SPAN("="), CODE(escape(repr)), cls="repr")

    if show_type:
        head << CODE(
            py.if_none(
                terminal.format_nice_type_name(objdoc, lookup_path), type_name),
            cls="type")

    # Show where this was imported from.
    if import_path is not None:
        head << DIV(
            "\u21d2 ", 
            format_name(import_path, relative_to=lookup_path), 
            cls="import")

    if summary is not None:
        rest = result << DIV(cls=("rest", "docs"))
        docs = rest << DIV(summary)
        if body:
            # Don't print the body, but indicate that there are more docs.
            docs << SPAN("more...", cls="more")

    return result


def format_members(docsrc, dict, parent_path, show_type=True, imports=True):
    div = DIV(cls="members")
    for name in sorted(dict):
        objdoc = dict[name]
        if imports or not is_ref(objdoc):
            # FIXME: Even if parent_path is None, we need to pass the local
            # name, in case the object doesn't know its own name.
            lookup_path = None if parent_path is None else parent_path / name
            div << format_member(
                docsrc, objdoc, lookup_path, 
                context_path=parent_path, show_type=show_type)
    return div


def format_source(source):
    div = DIV(H2("Source"))

    loc         = source.get("source_file") or source.get("file")
    source_text = source.get("source")

    if loc is not None:
        div << SPAN(loc, cls="path")
        lines = source.get("lines")
        if lines is not None:
            start, end = lines
            div << " lines {}-{}".format(start + 1, end + 1)

    if source_text is not None:
        lexer = pygments.lexers.get_lexer_by_name("python")
        formatter = pygments.formatters.get_formatter_by_name(
            "html", cssclass="source")
        div << pygments.highlight(source_text, lexer, formatter)

    return div


def generate(docsrc, objdoc, lookup_path):
    # If this is a ref, follow it.
    from_path   = lookup_path or get_path(objdoc)
    while is_ref(objdoc):
        path = parse_ref(objdoc)
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
    type_path       = None if type is None else get_path(type)
    
    module          = objdoc.get("module")
    modname         = (
             parse_ref(module)[0] if module is not None
        else lookup_path.modname if lookup_path is not None
        else None
    )
    lookup_modname  = None if lookup_path is None else lookup_path.modname

    html = HTML()

    head = html << HEAD(
        LINK(rel="stylesheet", type="text/css", href="/static/supdoc.css"),
        # Use jQuery.
        SCRIPT(src="/static/jquery.min.js"),
    )

    body = html << BODY() << DIV(id="content")

    module_list = body << format_module_list()
    module_list["id"] = "module-sidebar"

    doc = body << DIV(id="main")
    details = doc << DIV(cls="details box")

    # Show its type.
    if type is not None:
        instance_of = (
            "instance of ", 
            format_name(type_path, relative_to=Path(lookup_modname)),
        )
        nice_type_name = terminal.format_nice_type_name(objdoc, lookup_path)
        if nice_type_name is not None:
            instance_of = (nice_type_name, " (", *instance_of, ")")
        details << DIV(*instance_of)

    # Show the module name.
    if type_name != "module" and module is not None:
        details << DIV("in module ", format_name(Path(parse_ref(module)[0])))

    # Show the mangled name.
    if mangled_name is not None:
        details << DIV("external name ", CODE(mangled_name, cls="identifier"))

    bases = objdoc.get("bases")
    if bases is not None:
        bases_div = details << DIV("base types:")
        bases_div << make_list(
            ( 
                SPAN(format_name(get_path(base), relative_to=Path(modname)))
                for base in bases
            ),
            tag=OL, start=0, cls="base-type-list",
        )

    mro = objdoc.get("mro")
    if mro is not None:
        mro_div = details << DIV("MRO: ")
        for first, mro_type in aslib.itr.first(mro):
            if not first:
                mro_div << " \u2192 "
            mro_div << format_name(
                get_path(mro_type), relative_to=Path(modname))


    # FIXME: Use a better icon.
    details << DIV(A(
        CODE("{}", cls="mini-icon"), 
        href=make_url(lookup_path) + "?format=json"),
        style="margin: 8px 0; "
    )

    main = doc << DIV(cls="main")

    main << DIV(SPAN(display_name, cls="identifier"), cls="name")

    if is_function_like(objdoc):
        main << DIV(CODE(objdoc["name"]), format_signature(docsrc, objdoc))
        
    # Show documentation.
    docs = objdoc.get("docs")
    if docs is not None:
        main << format_docs(docs)

    # Summarize property.
    if type_name == "property":
        main << format_property_summary(docsrc, objdoc, lookup_path)

    if is_function_like(objdoc):
        main << format_signature_summary(docsrc, objdoc)

    #----------------------------------------
    # Summarize contents.

    # FIXME
    private = True
    imports = True

    partitions = terminal._partition_members(terminal.get_dict(objdoc, private) or {})

    contents = doc << DIV(cls="contents")

    controls = contents << DIV(cls="controls")

    controls << BUTTON("Imported", id="cb-import", cls="toggle")
    # FIXME: Put this somewhere reasonable.
    controls << SCRIPT("""
      $(function () {
        $('.imported-name').toggle(false);
        // FIXME: This animation is cheesy.
        $('#cb-import').click(function (event) {
          $('.imported-name').toggle('fast');
          $('#cb-import').toggleClass('toggled');
        });
      });
    """)

    controls << BUTTON("Private", id="cb-private", cls="toggle")
    # FIXME: Put this somewhere reasonable.
    controls << SCRIPT("""
      $(function () {
        $('.private-name').toggle(false);
        // FIXME: This animation is cheesy.
        $('#cb-private').click(function (event) {
          $('.private-name').toggle('fast');
          $('#cb-private').toggleClass('toggled');
        });
      });
    """)

    mems = partitions.pop("modules", {})
    if len(mems) > 0:
        contents << H2("Modules")
        contents << format_members(docsrc, mems, path, False, imports=imports)

    mems = partitions.pop("types", {})
    if len(mems) > 0:
        contents << H2("Types" if type_name == "module" else "Member Types")
        contents << format_members(docsrc, mems, path, False, imports=imports)

    mems = partitions.pop("properties", {})
    if len(mems) > 0:
        contents << H2("Properties")
        contents << format_members(docsrc, mems, path, True, imports=imports)

    mems = partitions.pop("functions", {})
    if len(mems) > 0:
        contents << H2("Functions" if type_name == "module" else "Methods")
        contents << format_members(docsrc, mems, path, True, imports=imports)

    mems = partitions.pop("attributes", {})
    if len(mems) > 0:
        contents << H2("Attributes")
        contents << format_members(docsrc, mems, path, True)

    #----------------------------------------

    # Summarize the source.
    source = objdoc.get("source")
    if source is not None:
        doc << format_source(source)

    return html


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

