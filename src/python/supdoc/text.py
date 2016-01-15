import argparse
from   contextlib import suppress
from   enum import Enum
import json
import re
import shutil
import sys

from   pln import if_none, or_none
import pln.itr
import pln.json
from   pln.terminal import ansi
from   pln.terminal.printer import Printer, NL

from   . import inspector
from   .objdoc import *
from   .path import *

#-------------------------------------------------------------------------------

# FIXME: A color for each of:
# - modules
# - types
# - callables
# and then use bold for emphasis (summary / parameters)

STYLES = {
    "docs"              : {"fg": "gray24", },
    "header"            : {"underline": True, "fg": 89, },
    "identifier"        : {"bold": True, },
    "label"             : {"fg": 89, },
    "mangled_name"      : {"fg": "gray70", },
    "modname"           : {"fg": 17, },
    "path"              : {"fg": "gray60", },
    "repr"              : {"fg": "gray70", },
    "rule"              : {"fg": "gray95", },
    "source"            : {"fg": "#222845", },
    "summary"           : {"fg": "black", },
    "type_name"         : {"fg": 23, },
    "warning"           : {"fg": 130, },
}

BULLET              = ansi.fg(89)("\u203a") + " "
ELLIPSIS            = "\u2026"
MISSING             = "\u2047"
MEMBER_OF           = "\u220a"
IMPORT_ARROW        = " \u21d2 "

#-------------------------------------------------------------------------------

# FIXME: Elsewhere.

def unmangle(name, parent_name):
    """
    Unmangles a private mangled name.

      >>> unmangle("_MyClass__foo", "MyClass")
      '__foo'
      >>> unmangle("_MyClass__foo", "MyOtherClass")
      '_MyClass__foo'
      >>> unmangle("__foo", "MyClass")
      '__foo'

    @return
      If `name` is mangled for `parent_name`, the mangled name; `name`
      otherwise.
    """
    if parent_name is not None and name.startswith("_" + parent_name + "__"):
        return name[1 + len(parent_name) :]
    else:
        return name


#-------------------------------------------------------------------------------

def _format_parameters(parameters):
    star = False
    for param in parameters.values():
        prefix = ""
        if param.kind is Parameter.KEYWORD_ONLY and not star:
            yield "*"
            star = True
        elif param.kind is Parameter.VAR_POSITIONAL:
            prefix = "*"
            star = True
        elif param.kind is Parameter.VAR_KEYWORD:
            prefix = "**"
            star = True
        result = prefix + ansi.style(**STYLES["identifier"])(param.name)
        yield result


def _print_signature(docsrc, objdoc, pr):
    """
    If `objdoc` is callable, prints its call signature in parentheses.

    Does not print default arguments, annotations, or other metadata.
    """
    if not is_function_like(objdoc):
        return

    pr << "("
    signature = get_signature(objdoc)
    if signature is not None:
        sig = signature_from_jso(signature, docsrc)
        pr << ", ".join(_format_parameters(sig.parameters))
    else:
        with pr(**STYLES["warning"]):
            pr << MISSING
    pr << ")"
    # FIXME: Return value annotation


def _print_name(qualname, name, pr):
    if qualname is not None:
        if name is None:
            name = qualname.rsplit(".", 1)[1] if "." in qualname else qualname
        if qualname.endswith("." + name):
            pr << qualname[: -len(name)] << ansi.bold(name)
        else:
            pr << ansi.bold(qualname)
    elif name is not None:
        pr << ansi.bold(name)
    else:
        pr << ansi.style(**STYLES["warning"])("(no name)")


def format_path(path, *, modname=None):
    """
    Prints a fully-qualified path.

    Prints the path, including modname and qualname.  If the modname matches
    the context `modname`, it is not shown.  Also, if the modname is "builtins",
    it is not shown.

    @type path
      `Path`.
    @param modname
      The context module name. 
    """
    result = (
        "" if     path.modname in ("builtins", modname)
              and path.qualname is not None
        else ansi.style(**STYLES["modname"])(path.modname)
    )
    if path.qualname is not None:
        if result != "":
            result += "."
        result += path.qualname
    return ansi.style(**STYLES["identifier"])(result)


# FIXME: Break this function up.
def print_docs(docsrc, objdoc, lookup_path=None, printer=Printer()):
    """
    @param lookup_path
      The path under which this objdoc was found.
    """
    pr = printer  # For brevity.

    from_path = lookup_path or get_path(objdoc)
    while is_ref(objdoc):
        path = parse_ref(objdoc)
        pr << format_path(from_path) << IMPORT_ARROW << NL
        objdoc = docsrc.resolve(objdoc)
        from_path = path

    name            = objdoc.get("name")
    qualname        = objdoc.get("qualname")
    mangled_name    = objdoc.get("mangled_name")
    # FIXME: Merge with logic in _print_name().
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

    type_name       = objdoc.get("type_name")
    callable        = is_callable(objdoc)
    signature       = get_signature(objdoc)
    source          = objdoc.get("source")
    repr            = objdoc.get("repr")
    docs            = objdoc.get("docs")
    dict            = objdoc.get("dict")

    def header(header):
        with pr(**STYLES["header"]):
            pr << header << NL

    def rule():
        with pr(**STYLES["rule"]):
            pr << "\u2501" * pr.remaining << NL

    rule()

    # Show its name.
    _print_name(display_name, name, pr)
    
    # Show its callable signature, if it has one.
    _print_signature(docsrc, objdoc, pr)

    # Show its type.
    if type_name is not None:
        with pr(**STYLES["type_name"]):
            pr >> type_name

    pr << NL
    rule()

    # Show the module name.
    if type_name != "module" and modname is not None:
        pr << "in module " << format_path(Path(modname, None)) << NL

    pr << NL

    # Show the mangled name.
    if mangled_name is not None:
        pr << "external name "
        with pr(**STYLES["mangled_name"]):
            pr << mangled_name << NL 
        pr << NL

    # Summarize the source.
    if source is not None:
        loc         = source.get("source_file") or source.get("file")
        source_text = source.get("source")

        if loc is not None or source_text is not None:
            header("Source")

        if loc is not None:
            with pr(**STYLES["path"]):
                pr << loc
            lines = source.get("lines")
            if lines is not None:
                start, end = lines
                pr >> " lines {}-{}".format(start + 1, end + 1)
            pr << NL << NL

        if source_text is not None:
            with pr(indent="\u2506 ", **STYLES["source"]):
                pr.elide(source_text)
            pr << NL << NL

    # Show documentation.
    if docs is not None:
        summary = docs.get("summary", "")
        body    = docs.get("body", "")

        if summary or body:
            header("Documentation")

        with pr(**STYLES["docs"]):
            # Show the doc summary.
            if summary:
                with pr(**STYLES["summary"]):
                    pr.html(summary) << NL << NL
            # Show the doc body.
            if body:
                pr.html(body)

    # Summarize type.
    if type_name == "type":
        bases   = objdoc.get("bases")
        mro     = objdoc.get("mro")
        if bases is not None or mro is not None:
            header("Type")
            if bases is not None:
                with pr(**STYLES["label"]):
                    pr << "Base types:" 
                for base in bases:
                    pr << " "
                    with pr(**STYLES["type_name"]):
                        pr << format_path(get_path(base), modname=modname)
                pr << NL
            if mro is not None:
                with pr(**STYLES["label"]):
                    pr << "MRO: "
                for first, mro_type in pln.itr.first(mro):
                    entry = format_path(get_path(mro_type), modname=modname)
                    entry = ansi.style(**STYLES["type_name"])(entry)
                    entry = entry if first else " \u2192 " + entry
                    if not pr.fits(entry):
                        pr << NL << "  "
                    pr << entry
                pr << NL
            pr << NL

    # Summarize property.
    if type_name == "property":
        header("Property")
        for accessor_name in ("get", "set", "del"):
            accessor = objdoc.get(accessor_name)
            accessor = None if accessor is None else docsrc.resolve(accessor)
            with pr(**STYLES["label"]):
                pr << "{}: ".format(accessor_name)
            if accessor is not None:
                _print_member(docsrc, accessor, None, None, pr)
            else:
                pr << "none" << NL
        pr << NL 

    # Summarize parameters.
    if signature is not None and len(signature) > 0:
        header("Parameters")
        for param in signature["params"]:
            name        = param["name"]
            default     = param.get("default")
            doc_type    = param.get("doc_type")
            doc         = param.get("doc")

            with pr(**STYLES["identifier"]):
                pr << BULLET + name
            if default is not None:
                pr << " \u225d " + default["repr"]

            pr << NL
            with pr(indent="  "):
                if doc_type is not None:
                    pr << MEMBER_OF << " "
                    with pr(**STYLES["type_name"]):
                        pr.html(doc_type) << NL

                if doc is not None:
                    with pr(**STYLES["docs"]):
                        pr.html(doc) << NL

            pr << NL
                
    # FIXME: Summarize return value and raises.

    # Show the repr.
    if repr is not None and not repr_is_uninteresting(objdoc):
        header("Repr")
        with pr(**STYLES["repr"]):
            pr << repr << NL << NL

    # Summarize contents.
    partitions = _partition_members(dict or {})

    partition = partitions.pop("modules", {})
    if len(partition) > 0:
        header("Modules")
        _print_members(docsrc, partition, name, pr, False)

    partition = partitions.pop("types", {})
    if len(partition) > 0:
        header("Types" if type_name == "module" else "Member Types")
        _print_members(docsrc, partition, name, pr, False)

    partition = partitions.pop("properties", {})
    if len(partition) > 0:
        header("Properties")
        _print_members(docsrc, partition, name, pr, True)

    partition = partitions.pop("functions", {})
    if len(partition) > 0:
        header("Functions" if type_name == "module" else "Methods")
        _print_members(docsrc, partition, name, pr, True)

    partition = partitions.pop("attributes", {})
    if len(partition) > 0:
        header("Attributes")
        _print_members(docsrc, partition, name, pr, True)

    assert len(partitions) == 0


_PARTITIONS = {
    "builtins.builtin_function_or_method"   : "functions",
    "builtins.classmethod"                  : "functions",
    "builtins.classmethod_descriptor"       : "functions",
    "builtins.function"                     : "functions",
    "builtins.method_descriptor"            : "functions",
    "builtins.module"                       : "modules",
    "builtins.property"                     : "properties",
    "builtins.staticmethod"                 : "functions",
    "builtins.type"                         : "types",
    "builtins.wrapper_descriptor"           : "functions",
    "_ctypes.PyCStructType"                 : "types",
}

def _partition_members(dict):
    partitions = {}
    for name, objdoc in dict.items():
        type_path = ".".join(get_path(objdoc["type"]))
        partition_name = _PARTITIONS.get(str(type_path), "attributes")
        partitions.setdefault(partition_name, {})[name] = objdoc
    return partitions
        

def repr_is_uninteresting(objdoc):
    # FIXME
    type_path = ".".join(get_path(objdoc["type"]))
    return type_path in _PARTITIONS


# FIXME: WTF is this signature anyway?
def _print_member(docsrc, objdoc, lookup_name, parent_name, pr, show_type=True):
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
    unmangled_name  = if_none(unmangle(lookup_name, parent_name), name)
    type_name       = objdoc.get("type_name")
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
    long_repr = show_repr and (
        len(repr) > pr.width - pr.column - len(type_name) - 8)

    with pr(**STYLES["identifier"]):
        pr << unmangled_name

    # FIXME: Distinguish normal / static / class methods from functions.

    _print_signature(docsrc, objdoc, pr)
    # FIXME: Common code with print_docs().
    if import_path is not None:
        pr << IMPORT_ARROW << format_path(import_path, modname=modname)

    # If this is a mangled name, we showed the unmangled name earlier.  Now
    # show the mangled name too.
    if unmangled_name != lookup_name and lookup_name is not None:
        with pr(**STYLES["mangled_name"]):
            pr << " \u224b "  # FIXME: Something better?
            with pr(**STYLES["identifier"]):
                pr << lookup_name 

    # For less common types, show the repr.
    if show_repr and not long_repr and not is_function_like(objdoc):
        with pr(**STYLES["repr"]):
            pr << " = " << repr

    right = ""
    # For properties, show which get/set/del operations are available.
    if type_name == "property":
        tags = []
        if objdoc.get("get") is not None:
            tags.append("get")
        if objdoc.get("set") is not None:
            tags.append("set")
        if objdoc.get("del") is not None:
            tags.append("del")
        right += "/".join(tags) + " "

    # Show the type.
    if show_type and type_name is not None:
        right += ansi.style(**STYLES["type_name"])(type_name)
    if right:
        pr >> right
    pr << NL

    with pr(indent="   "):
        if long_repr:
            with pr(**STYLES["repr"]):
                pr.elide("= " + repr)
            pr << NL
        if summary is not None:
            with pr(**STYLES["docs"]):
                pr.html(summary)
            if body:
                # Don't print the body, but indicate that there are more docs.
                with pr(fg="gray80"):
                    pr << " " << ELLIPSIS
            pr << NL


def _print_members(docsrc, dict, parent_name, pr, show_type=True):
    for lookup_name in sorted(dict):
        objdoc = dict[lookup_name]
        pr << BULLET
        _print_member(docsrc, objdoc, lookup_name, parent_name, pr, show_type)
    pr << NL


#-------------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser()
    # FIXME: Share some arguments with supdoc.inspector.main().
    parser.add_argument(
        "name", metavar="NAME",
        help="fully-qualified module or object name")
    parser.add_argument(
        "--json", default=False, action="store_true",
        help="dump JSON docs")
    parser.add_argument(
        "--sdoc", default=False, action="store_true",
        help="dump JSON sdoc")
    parser.add_argument(
        "--path", metavar="FILE", default=None,
        help="read JSON docs from FILE")
    parser.add_argument(
        "--source", dest="source", default=False, action="store_true",
        help="include source")
    parser.add_argument(
        "--no-source", dest="source",  action="store_false",
        help="don't include source")
    args = parser.parse_args()

    # Find the requested object.
    try:
        path, obj = split(args.name)
    except NameError as error:
        print("bad NAME: {}".format(error), file=sys.stderr)
        raise SystemExit(1)

    if args.path is None:
        docsrc = inspector.DocSource(source=args.source)
    else:
        # Read the docs file.
        # FIXME
        # with open(args.path) as file:
        #     sdoc = json.load(file)
        raise NotImplementedException("docs file")

    try:
        objdoc = docsrc.get(path)
    except LookupError as error:
        # FIXME
        print(error, file=sys.stderr)
        raise SystemExit(1)

    if args.sdoc:
        pln.json.pprint(sdoc)
    elif args.json:
        pln.json.pprint(objdoc)
    else:
        # Leave a one-space border on the right.
        width = pln.terminal.get_width() - 1 
        print_docs(docsrc, objdoc, path, Printer(indent=" ", width=width))


if __name__ == "__main__":
    _main()



