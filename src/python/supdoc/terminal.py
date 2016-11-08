from   contextlib import suppress
from   enum import Enum
import json
import re
import shutil
import sys

from   aslib import if_none, or_none
import aslib.itr
import aslib.json
from   aslib.terminal import ansi
from   aslib.terminal.printer import Printer, NL

from   . import inspector
from   .exc import *
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
    "header"            : {"underline": True, "fg": 0x82, },
    "identifier"        : {"bold": True, },
    "label"             : {"fg": 0x82, },
    "mangled_name"      : {"fg": "gray70", },
    "modname"           : {"fg": 17, },
    "path"              : {"fg": "gray60", },
    "repr"              : {"fg": "gray70", },
    "rule"              : {"fg": 0xdf, },
    "source"            : {"fg": "#222845", },
    "summary"           : {"fg": "black", },
    "type_name"         : {"fg": 23, },
    "warning"           : {"fg": 0x7c, },
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


_NICE_TYPE_NAMES = {
    Path("builtins", "builtin_function_or_method")  : "extension function",
    Path("builtins", "classmethod")                 : "class method",
    Path("builtins", "classmethod_descriptor")      : "extenson class method",
    Path("builtins", "getset_descriptor")           : "extension property",
    Path("builtins", "method_descriptor")           : "extention method",
    Path("builtins", "wrapper_descriptor")          : "special method",
    Path("builtins", "staticmethod")                : "static method",
}


def format_nice_type_name(objdoc, lookup_path):
    """
    Returns a human-friendly type name for `objdoc`.
    """
    try:
        type_ = objdoc["type"]
    except KeyError:
        return None
    path = get_path(type_)

    # Special handling for properties.
    if path == Path("builtins", "property"):
        tags = []
        if objdoc.get("get") is not None:
            tags.append("get")
        if objdoc.get("set") is not None:
            tags.append("set")
        if objdoc.get("del") is not None:
            tags.append("del")
        return "/".join(tags) + " property"

    # Special handling for functions.
    elif path == Path("builtins", "function"):
        if objdoc.get("name") == "<lambda>":
            return "lambda function"
        else:
            return "function"

    else:
        return _NICE_TYPE_NAMES.get(path, None)


#-------------------------------------------------------------------------------

def _format_parameters(params):
    star = False
    for param in params:
        prefix = ""
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
        result = prefix + ansi.style(**STYLES["identifier"])(param["name"])
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
        pr << ", ".join(_format_parameters(signature["params"]))
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
        pr << ansi.style(**STYLES["warning"])("(unnamed object)")


# FIXME: Can't restore previous style.  Replace with print_path(). 
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


def get_dict(objdoc, private):
    """
    @param private
      If true, includes all names; otherwise, excludes private names.
    """
    dict = objdoc.get("dict")
    if dict is None:
        return None

    if not private:
        # Remove private members.
        if objdoc.get("type_name") == "module":
            # Was the set of all public names specified explicitly?
            try:
                all_names = objdoc["all_names"]
            except KeyError:
                # If not, remove names that start with an underscore.
                dict = { 
                    n: v for n, v in dict.items() if not n.startswith("_")
                }
            else:
                # If so, filter by it.
                dict = { 
                    n: v for n, v in dict.items() if n in all_names 
                }
        else:
            # For other things, remove private but not special names.
            dict = { 
                n: v for n, v in dict.items() 
                if not n.startswith("_")
                   or (n.startswith("__") and n.endswith("__"))
            }
    
    return dict


def print_docs(docsrc, objdoc, lookup_path=None, *, 
               private=True, imports=True, file=None, width=None):
    """
    @param lookup_path
      The path under which this objdoc was found.
    @param private
      If true, shows all names in `dict`; otherwise, excludes private names.
    @param imports
      If true, shows imported names in modules; otherwise, excludes them.
    """
    if file is None:
        file = sys.stdout
    if width is None:
        # Substract one to leave a one-space border on the right.
        width = aslib.terminal.get_width() - 1

    printer = Printer(file.write, indent=" ", width=width)
    try:
        _print_docs(docsrc, objdoc, lookup_path, printer, private, imports)
    finally:
        file.flush()


# FIXME: Break this function up.
def _print_docs(docsrc, objdoc, lookup_path, printer, private, imports):
    pr = printer  # For brevity.

    from_path   = lookup_path or get_path(objdoc)
    while is_ref(objdoc):
        path = parse_ref(objdoc)
        pr << format_path(from_path) << IMPORT_ARROW << NL
        objdoc = docsrc.resolve(objdoc)
        from_path = path

    path            = get_path(objdoc) or lookup_path
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
    lookup_modname  = None if lookup_path is None else lookup_path.modname

    type            = objdoc.get("type")
    type_name       = objdoc.get("type_name")
    type_path       = get_path(type)
    callable        = is_callable(objdoc)
    signature       = get_signature(objdoc)
    source          = objdoc.get("source")
    repr            = objdoc.get("repr")
    docs            = objdoc.get("docs")

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

    pr << NL
    rule()

    # Show its type.
    instance_of = (
        "instance of " + format_path(type_path, modname=lookup_modname))
    nice_type_name = format_nice_type_name(objdoc, lookup_path)
    with pr(**STYLES["type_name"]):
        if nice_type_name is None:
            pr << instance_of
        else:
            pr << nice_type_name << " (" << instance_of << ")"
        pr << NL

    # Show the module name.
    if type_name != "module" and module is not None:
        pr << "in module " 
        pr << format_path(Path(parse_ref(module)[0], None)) << NL

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
                for first, mro_type in aslib.itr.first(mro):
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
                _print_member(docsrc, accessor, None, pr)
            else:
                pr << "none" << NL
        pr << NL 

    if signature is not None and len(signature) > 0:
        # Summarize parameters.
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
                
        # Show the return type type and documentation.
        return_ = signature.get("return")
        if return_ is not None:
            doc         = return_.get("doc")
            doc_type    = return_.get("doc_type")

            header("Return Value")

            if doc_type is not None:
                pr << MEMBER_OF << " "
                with pr(**STYLES["type_name"]):
                    pr.html(doc_type) << NL

            if doc is not None:
                with pr(**STYLES["docs"]):
                    pr.html(doc) << NL

            pr << NL

    # Show the repr.
    if repr is not None and not repr_is_uninteresting(objdoc):
        header("Repr")
        with pr(**STYLES["repr"]):
            pr << repr << NL << NL

    # Summarize contents.
    partitions = _partition_members(get_dict(objdoc, private) or {})

    partition = partitions.pop("modules", {})
    if len(partition) > 0:
        header("Modules")
        _print_members(docsrc, partition, path, pr, False, imports=imports)

    partition = partitions.pop("types", {})
    if len(partition) > 0:
        header("Types" if type_name == "module" else "Member Types")
        _print_members(docsrc, partition, path, pr, False, imports=imports)

    partition = partitions.pop("properties", {})
    if len(partition) > 0:
        header("Properties")
        _print_members(docsrc, partition, path, pr, True, imports=imports)

    partition = partitions.pop("functions", {})
    if len(partition) > 0:
        header("Functions" if type_name == "module" else "Methods")
        _print_members(docsrc, partition, path, pr, True, imports=imports)

    partition = partitions.pop("attributes", {})
    if len(partition) > 0:
        header("Attributes")
        _print_members(docsrc, partition, path, pr, True)

    assert len(partitions) == 0
    if not private or not imports:
        omitted = []
        if not imports:
            omitted.append("imported")
        if not private:
            omitted.append("private")
        with pr(**STYLES["warning"]):
            pr << " and ".join(omitted).capitalize() + " members omitted." << NL
            pr << NL


# FIXME: Use paths.
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
        type = objdoc.get("type")
        if type is None:
            # Missing type...?
            partition_name = "attributes"
        else:
            type_path = ".".join(get_path(objdoc["type"]))
            partition_name = _PARTITIONS.get(str(type_path), "attributes")
        partitions.setdefault(partition_name, {})[name] = objdoc
    return partitions
        

def repr_is_uninteresting(objdoc):
    # FIXME
    type_path = ".".join(get_path(objdoc["type"]))
    return type_path in _PARTITIONS


# FIXME: WTF is this signature anyway?
def _print_member(docsrc, objdoc, lookup_path, pr, show_type=True):
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
    unmangled_name  = if_none(unmangle(lookup_name, parent_name), name)
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

    with pr(**STYLES["identifier"]):
        pr << unmangled_name

    _print_signature(docsrc, objdoc, pr)

    # If this is a mangled name, we showed the unmangled name earlier.  Now
    # show the mangled name too.
    if unmangled_name != lookup_name and lookup_name is not None:
        with pr(**STYLES["mangled_name"]):
            pr << " \u224b "  # FIXME: Something better?
            with pr(**STYLES["identifier"]):
                pr << lookup_name 

    if show_type:
        nice_type = format_nice_type_name(objdoc, lookup_path)
        if nice_type is None:
            nice_type = ansi.bold(type_name)
        with pr(**STYLES["type_name"]):
            pr >> nice_type

    pr << NL

    with pr(indent="   "):
        # Show where this was imported from.
        if import_path is not None:
            path = format_path(
                import_path, 
                modname=None if lookup_path is None else lookup_path.modname)
            pr << "import" << IMPORT_ARROW << path << NL

        if show_repr:
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


def _print_members(docsrc, dict, parent_path, pr, show_type=True, imports=True):
    for name in sorted(dict):
        objdoc = dict[name]
        if imports or not is_ref(objdoc):
            # FIXME: Even if parent_path is None, we need to pass the local
            # name, in case the object doesn't know its own name.
            lookup_path = None if parent_path is None else parent_path / name
            pr << BULLET
            _print_member(docsrc, objdoc, lookup_path, pr, show_type)
    pr << NL


