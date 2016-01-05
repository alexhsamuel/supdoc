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
from   pln.terminal.printer import Printer
import pln.terminal.html

#-------------------------------------------------------------------------------

STYLES = {
    "docs"              : {},
    "header"            : {"underline": True, "fg": 53, },
    "identifier"        : {"bold": True, },
    "modname"           : {"fg": 52, },
    "repr"              : {"fg": "gray60", },
    "rule"              : {"fg": "gray95", },
    "source"            : {"fg": "#222845", },
    "summary"           : {},
    "type_name"         : {"fg": 23, },
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

def parameter_from_jso(jso):
    name = jso["name"]
    kind = getattr(Parameter, jso["kind"])
    try:
        default = jso["default"]
    except KeyError:
        default = Parameter.empty
    else:
        # FIXME
        default = ReprObj(default["repr"])
    try:
        annotation = jso["annotation"]
    except KeyError:
        annotation = Parameter.empty
    else:
        # FIXME
        annotation = annotation["repr"]
    return Parameter(name, kind, default=default, annotation=annotation)


def signature_from_jso(jso):
    # FIXME: return annotation.
    parameters = [ parameter_from_jso(o) for o in jso.get("params", []) ]
    return Signature(parameters)


def format_parameters(parameters):
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


#-------------------------------------------------------------------------------

from   . import inspector

BULLET              = ansi.fg(109)("\u203a ")
ELLIPSIS            = "\u2026"
NOTE                = ansi.fg("dark_red")


# FIXME: Break this function up.
def print_docs(sdoc, odoc, printer=Printer()):
    while is_ref(odoc):
        modname, fqname = parse_ref(odoc)
        printer << NOTE("Reference!")
        odoc = look_up_ref(sdoc, odoc)

    name        = odoc.get("name")
    qualname    = odoc.get("qualname")
    module      = odoc.get("module")
    type_name   = odoc.get("type_name")
    signature   = odoc.get("signature")
    source      = odoc.get("source")
    docs        = odoc.get("docs")
    dict        = odoc.get("dict")

    html_printer = pln.terminal.html.Converter(printer)
    print_header = lambda h: printer.write_line(h, style=STYLES["header"])
    print_rule = lambda: printer.write_line(
        "\u2501" * printer.width, style=STYLES["rule"])

    printer.newline()

    # Show the name.
    if module is not None:
        modname, _ = parse_ref(module)
        printer.push_style(**STYLES["modname"])
        printer << modname
        printer.pop_style()
        printer <=  "."
    print_rule()

    if qualname is not None:
        if qualname.endswith(name):
            printer << qualname[: -len(name)]
            printer << ansi.bold(name)
        else:
            printer << ansi.bold(qualname)
    elif name is not None:
        printer << ansi.bold(name)
    # Show its callable signature, if it has one.
    if signature is not None:
        sig = signature_from_jso(signature)
        printer << "(" + ", ".join(format_parameters(sig.parameters)) + ")"
    # Show its type.
    if type_name is not None:
        printer.right_justify(
            " \u220a " + type_name + "", style=STYLES["type_name"])
    else:
        printer.newline()
    print_rule()
    printer.newline()

    # Summarize the source / import location.
    if source is not None:
        loc = source.get("source_file") or source.get("file")
        if loc is not None:
            print_header("Location")
            printer << loc

            lines = source.get("lines")
            if lines is not None:
                start, end = lines
                printer.right_justify(" lines {}-{}".format(start + 1, end + 1))

            printer.newline()

        source_text = source.get("source")
        if source_text is not None:
            print_header("Source")
            printer.push_indent("\u205a ")
            width = printer.width
            # Elide long lines of source.
            source_text = "\n".join(
                l if len(l) <= width else l[: width - 1] + ELLIPSIS
                for l in source_text.split("\n")
            )
            printer.write(ansi.style(**STYLES["source"])(source_text))
            printer.pop_indent()
            printer.newline()

    # Show documentation.
    if docs is not None:
        summary = docs.get("summary", "")
        body    = docs.get("body", "")

        if summary or body:
            print_header("Documentation")

        printer.push_style(**STYLES["docs"])
        # Show the doc summary.
        if summary:
            html_printer.convert(summary, style=STYLES["summary"])
            printer.newline(2)
        # Show the doc body.
        if body:
            html_printer.convert(body)
            printer.newline(2)
        printer.pop_style()

    # Summarize parameters.
    if signature is not None and len(signature) > 0:
        print_header("Parameters")
        for param in signature["params"]:
            name        = param["name"]
            default     = param.get("default")
            doc_type    = param.get("doc_type")
            doc         = param.get("doc")

            printer.push_style(**STYLES["identifier"])
            printer << BULLET + name
            printer.pop_style()
            if default is not None:
                printer << " \u225d " + default["repr"]

            printer.newline()
            printer.push_indent("  ")

            if doc_type is not None:
                html_printer.convert(
                    "\u220a " + doc_type, style=STYLES["type_name"])
                printer.newline()

            if doc is not None:
                html_printer.convert(doc, style=STYLES["docs"])
                printer.newline()

            printer.pop_indent()
            printer.newline()
                
    # FIXME: Summarize return value and raises.

    # Summarize contents.
    if dict is not None and len(dict) > 0:
        print_header("Members")
        for name in sorted(dict):
            printer << BULLET
            printer.write_string(name, style=STYLES["identifier"])

            odoc        = dict[name]
            if is_ref(odoc):
                try:
                    odoc = look_up_ref(sdoc, odoc)
                except LookupError:
                    pass
                if odoc is None:
                    odoc = {}

            type_name   = odoc.get("type_name")
            repr        = odoc.get("repr")
            signature   = odoc.get("signature")
            docs        = odoc.get("docs", {})
            summary     = docs.get("summary")

            if signature is not None:
                # FIXME
                printer << "(...)"
            if type_name is not None:
                printer.right_justify(
                    " \u220a " + type_name + "", style=STYLES["type_name"])
            else:
                printer.newline()

            printer.push_indent("   ")

            if signature is None and type_name != "module" and repr is not None:
                printer.elide("= " + repr, style=STYLES["repr"])

            if summary is not None:
                html_printer.convert(summary, style=STYLES["docs"])
                printer.newline()

            printer.pop_indent()

    printer.newline()


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

    if args.json:
        pln.json.pprint(odoc)
    else:
        width = pln.terminal.get_width() - 1
        print_docs(sdoc, odoc, Printer(indent=" ", width=width))


if __name__ == "__main__":
    _main()
