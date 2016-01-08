import argparse
from   contextlib import suppress
from   enum import Enum
import json
import re
import shutil
import sys

import pln.itr
import pln.json
from   pln.terminal import ansi
from   pln.terminal.printer import Printer, NL

from   . import inspector

#-------------------------------------------------------------------------------

# FIXME: Look up refs consistently.

# FIXME: A color for each of:
# - modules
# - types
# - callables
# and then use bold for emphasis (summary / parameters)

STYLES = {
    "docs"              : {"fg": "gray24", },
    "header"            : {"underline": True, "fg": 89, },
    "identifier"        : {"bold": True, "fg": "black", },
    "mangled_name"      : {"bold": True, "fg": "black", },
    "modname"           : {"fg": 17, },
    "path"              : {"fg": "gray60", },
    "repr"              : {"fg": "gray70", },
    "rule"              : {"fg": "gray95", },
    "source"            : {"fg": "#222845", },
    "summary"           : {"fg": "black", },
    "type_name"         : {"fg": 23, },
    "warning"           : {"fg": 130, },
}

#-------------------------------------------------------------------------------

# FIXME: Elsewhere.

def is_ref(obj):
    return "$ref" in obj


def parse_ref(ref):
    """
    Parses a ref.

    @return
      The fully-qualified module name and the name path.
    """
    parts = ref["$ref"].split("/")
    assert parts[0] == "#",         "ref must be absolute in current doc"
    assert len(parts) >= 3,         "ref must include module"
    assert parts[1] == "modules",   "ref must start with module"
    modname, name_path = parts[2], ".".join(parts[3 :])
    return modname, name_path


def _get_path(odoc):
    """
    Returns the lookup path for an odoc or ref.

    @rtype
      `inspector.Path`.
    """
    if is_ref(odoc):
        modname, name_path = parse_ref(odoc)
        if len(name_path) > 0:
            parts = name_path.split(".")
            assert all( n == "dict" for n in parts[:: 2] )
            qualname = ".".join(parts[1 :: 2])
        else:
            qualname = None
    else:
        modname = odoc.get("modname")
        # FIXME: Should we store and use the name path, in place of qualname?
        qualname = odoc.get("qualname")
    return inspector.Path(modname, qualname)


def look_up_ref(sdoc, ref):
    """
    Resolves a reference in its sdoc.
    """
    parts = ref["$ref"].split("/")
    assert parts[0] == "#", "ref must be absolute in current doc"
    docs = sdoc
    for part in parts[1 :]:
        if docs is None:
            raise LookupError("can't look up {} in {}".format(part, "/".join(parts)))
        docs = docs[part]
    return docs


def resolve_ref(sdoc, odoc):
    """
    If `odoc` is a reference, resolves it.
    """
    try:
        odoc["$ref"]
    except KeyError:
        return odoc
    else:
        return look_up_ref(sdoc, ref)


def look_up(sdoc, modname, name_path=None, refs=False):
    """
    Looks up a module or object in an sdoc.

    Finds `modname`, then recursively finds `name_path` by traversing the
    module's and then objects' dictionaries.

    If `name_path` is `None`, returns the object itself.

    @param modname
      The fully qualified module name.
    @type modname
      `str`
    @param name_path
      The name path of the object in the module, or `None` for the module
      itself.
    @type name_path
      `str` or `None`
    @param refs
      If true, resolve refs.  If the value is callable, call it whenever
      resolving a ref.
    """
    modules = sdoc["modules"]
    try:
        odoc = modules[modname]
    except KeyError:
        raise LookupError("no such module: {}".format(modname)) from None
    if name_path is not None:
        parts = name_path.split(".")
        for i in range(len(parts)):
            try:
                odoc = odoc["dict"][parts[i]]
            except KeyError:
                missing_name = ".".join(parts[: i + 1])
                raise LookupError("no such name: {}".format(missing_name))

    # Resolve references.
    while refs and is_ref(odoc):
        if callable(refs):
            refs(*parse_ref(odoc))
        odoc = look_up_ref(sdoc, odoc)

    return odoc


#-------------------------------------------------------------------------------

class ReprObj:

    def __init__(self, repr):
        self.__repr = repr


    def __repr__(self):
        return self.__repr



from  inspect import Signature, Parameter

def parameter_from_jso(jso, sdoc):
    name = jso["name"]
    kind = getattr(Parameter, jso["kind"])
    try:
        default = jso["default"]
    except KeyError:
        default = Parameter.empty
    else:
        if is_ref(default):
            # FIXME
            try:
                default = look_up_ref(sdoc, default)
            except:
                pass
        # FIXME
        default = ReprObj(default.get("repr", "???"))
    try:
        annotation = jso["annotation"]
    except KeyError:
        annotation = Parameter.empty
    else:
        # FIXME
        annotation = annotation["repr"]
    return Parameter(name, kind, default=default, annotation=annotation)


def signature_from_jso(jso, sdoc):
    # FIXME: return annotation.
    parameters = [ parameter_from_jso(o, sdoc) for o in jso.get("params", []) ]
    return Signature(parameters)


#-------------------------------------------------------------------------------

BULLET              = ansi.fg(89)("\u203a ")
ELLIPSIS            = "\u2026"
MISSING             = "\u2047"
MEMBER_OF           = "\u220a"

# FIXME
NOTE                = ansi.fg("dark_red")


def is_callable(odoc):
    """
    Returns true if the object is callable or wraps a callable.
    """
    return odoc.get("callable") or odoc.get("func", {}).get("callable")


def get_signature(odoc):
    """
    Returns the signature of a callable object or the wrapped callable.

    @return
      The signature, or `None` if none is available, for example for a built-in
      or extension function or method.
    """
    with suppress(KeyError):
        return odoc["signature"]
    with suppress(KeyError):
        return odoc["func"]["signature"]


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


def is_function_like(odoc):
    """
    Returns true if `odoc` is for a function or similar object.
    """
    return (
        odoc.get("callable") 
        and odoc.get("type_name") not in (
            "type", 
        )
    )


def _print_signature(sdoc, odoc, pr):
    """
    If `odoc` is callable, prints its call signature in parentheses.

    Does not print default arguments, annotations, or other metadata.
    """
    if not is_function_like(odoc):
        return

    pr << "("
    signature = get_signature(odoc)
    if signature is not None:
        sig = signature_from_jso(signature, sdoc)
        pr << ", ".join(_format_parameters(sig.parameters))
    else:
        with pr(**STYLES["warning"]):
            pr << MISSING
    pr << ")"
    # FIXME: Return value annotation


# FIXME: Break this function up.
def print_docs(sdoc, odoc, printer=Printer()):
    pr = printer  # For brevity.

    # FIXME
    while is_ref(odoc):
        pr << NOTE("Reference!") << NL
        odoc = look_up_ref(sdoc, odoc)

    name            = odoc.get("name")
    qualname        = odoc.get("qualname")
    mangled_name    = odoc.get("mangled_name")
    module          = odoc.get("module")
    type_name       = odoc.get("type_name")
    callable        = is_callable(odoc)
    signature       = get_signature(odoc)
    source          = odoc.get("source")
    docs            = odoc.get("docs")
    dict            = odoc.get("dict")

    def header(header):
        with pr(**STYLES["header"]):
            pr << header << NL

    def rule():
        with pr(**STYLES["rule"]):
            pr << "\u2501" * pr.remaining << NL

    rule()

    if qualname is not None:
        if qualname.endswith(name):
            pr << qualname[: -len(name)] << ansi.bold(name)
        else:
            pr << ansi.bold(qualname)
    elif name is not None:
        pr << ansi.bold(name)
    # Show its callable signature, if it has one.
    _print_signature(sdoc, odoc, pr)
    # Show its type.
    if type_name is not None:
        with pr(**STYLES["type_name"]):
            pr >> type_name

    pr << NL
    rule()

    # Show the name.
    if module is not None:
        modname, _ = parse_ref(module)
        pr << "in module "
        with pr(**STYLES["modname"]):
            pr << modname << NL
        pr << NL

    # Show the mangled name.
    if mangled_name is not None:
        pr << "external name "
        with pr(**STYLES["mangled_name"]):
            pr << mangled_name << NL 
    pr << NL

    # Summarize the source / import location.
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
                pr.html(body) << NL << NL

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

    # Summarize contents.
    partitions = _partition_members(dict or {})

    partition = partitions.pop("modules", {})
    if len(partition) > 0:
        header("Modules")
        _print_members(sdoc, partition, pr, False)

    partition = partitions.pop("types", {})
    if len(partition) > 0:
        header("Types")
        _print_members(sdoc, partition, pr, False)

    partition = partitions.pop("properties", {})
    if len(partition) > 0:
        header("Properties")
        _print_members(sdoc, partition, pr, False)

    partition = partitions.pop("functions", {})
    if len(partition) > 0:
        header("Functions" if type_name == "module" else "Methods")
        _print_members(sdoc, partition, pr, True)

    partition = partitions.pop("attributes", {})
    if len(partition) > 0:
        header("Attributes")
        _print_members(sdoc, partition, pr, True)

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
    for name, odoc in dict.items():
        type_path = ".".join(_get_path(odoc["type"]))
        partition_name = _PARTITIONS.get(str(type_path), "attributes")
        partitions.setdefault(partition_name, {})[name] = odoc
    return partitions
        

def _print_members(sdoc, dict, pr, show_type):
    for dict_name in sorted(dict):
        odoc        = dict[dict_name]

        if is_ref(odoc):
            # Find the full name from which this was imported.
            import_path = _get_path(odoc)
            # Read through the ref.
            try:
                resolved = look_up_ref(sdoc, odoc)
            except LookupError:
                pass
            else:
                if resolved is not None:
                    odoc = resolved
        else:
            import_path = None

        name            = odoc.get("name")
        type_name       = odoc.get("type_name")
        repr            = odoc.get("repr")
        callable        = is_callable(odoc)
        signature       = get_signature(odoc)
        docs            = odoc.get("docs", {})
        summary         = docs.get("summary")

        pr << BULLET
        with pr(**STYLES["identifier"]):
            pr << name

        # Show the repr if this is not a callable or one of several other
        # types with uninteresting reprs.
        show_repr = (
            repr is not None 
            and signature is None 
            and type_name not in ("module", "property", "type", )
        )
        long_repr = show_repr and (
            len(repr) > pr.width - pr.column - len(type_name) - 8)

        # FIXME: Distinguish normal / static / class methods from functions.

        _print_signature(sdoc, odoc, pr)
        # FIXME: Common code with print_docs().
        if show_repr and not long_repr and not is_function_like(odoc):
            with pr(**STYLES["repr"]):
                pr << " = " << repr
        if import_path is not None:
            pr << " \u27f8  "
            with pr(**STYLES["identifier"]):
                with pr(**STYLES["modname"]):
                    pr << import_path.modname
                if import_path.qualname is not None:
                    pr << "." << import_path.qualname
        # For properties, show which get/set/del operations are available.
        if type_name == "property":
            tags = []
            if odoc.get("get") is not None:
                tags.append("get")
            if odoc.get("set") is not None:
                tags.append("set")
            if odoc.get("del") is not None:
                tags.append("del")
            pr << " [" << "/".join(tags) << "]"
        if show_type and type_name is not None:
            with pr(**STYLES["type_name"]):
                pr >> type_name
        pr << NL

        with pr(indent="   "):
            if long_repr:
                with pr(**STYLES["repr"]):
                    pr.elide("= " + repr)
                pr << NL
            if summary is not None:
                with pr(**STYLES["docs"]):
                    pr.html(summary) << NL

    pr << NL


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
        "--source", dest="include_source", default=False, action="store_true",
        help="include source")
    parser.add_argument(
        "--no-source", dest="include_source",  action="store_false",
        help="don't include source")
    args = parser.parse_args()

    # Find the requested object.
    try:
        path, obj = inspector.split(args.name)
    except NameError as error:
        print("bad NAME: {}".format(error), file=sys.stderr)
        raise SystemExit(1)

    if args.path is None:
        sdoc = inspector.inspect_modules(
            [path.modname], include_source=args.include_source)
    else:
        # Read the docs file.
        with open(args.path) as file:
            sdoc = json.load(file)

    if args.json:
        refs = False
    else:
        def refs(modname, name_path):
            full_name = modname + "." + name_path if name_path else modname
            print(NOTE("redirects to: " + full_name))

    try:
        odoc = look_up(sdoc, path.modname, path.qualname, refs=refs)
    except LookupError as error:
        # FIXME
        print(error, file=sys.stderr)
        raise SystemExit(1)

    if args.sdoc:
        pln.json.pprint(sdoc)
    elif args.json:
        pln.json.pprint(odoc)
    else:
        # Leave a one-space border on the right.
        width = pln.terminal.get_width() - 1 
        print_docs(sdoc, odoc, Printer(indent=" ", width=width))


if __name__ == "__main__":
    _main()
