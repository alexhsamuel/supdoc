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
    "docs"              : {"fg": "gray30", },
    "identifier"        : {"fg": "#243", },
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

BULLET              = "\u2023 "
SECTION_HEADER      = lambda s: ansi.underline(s)
NOTE                = ansi.fg("dark_red")


# FIXME: We need some kind of terminal object to handle width and indentation.

def print_docs(sdoc, odoc, printer=Printer()):
    while is_ref(odoc):
        modname, fqname = parse_ref(odoc)
        printer << NOTE("Reference!")
        odoc = look_up_ref(sdoc, odoc)

    name        = odoc.get("name")
    signature   = odoc.get("signature")
    docs        = odoc.get("docs")
    dict        = odoc.get("dict")

    doc_style   = ansi.style(**STYLES["docs"])

    printer.newline()

    # Show the name.
    if name is not None:
        printer << ansi.bold(odoc["name"])
    # Show its callable signature, if it has one.
    if signature is not None:
        sig = signature_from_jso(signature)
        printer << "(" + ", ".join(format_parameters(sig.parameters)) + ")"
    printer.newline(2)

    if docs is not None:
        # Show the doc summary.
        summary = docs.get("summary", "")
        if summary:
            pln.terminal.html.Converter(printer).convert(summary, style={"bold": True})
            printer.newline(1)
        # Show the doc body.
        body = docs.get("body", "")
        if body:
            printer.push_indent("\u2506 ")
            printer.newline()
            pln.terminal.html.Converter(printer).convert(body)
            printer.pop_indent()
            printer.newline(2)

    # Summarize parameters.
    if signature is not None and len(signature) > 0:
        printer <= SECTION_HEADER("Parameters")
        for param in signature["params"]:
            name        = param["name"]
            default     = param.get("default")
            doc_type    = param.get("doc_type")
            doc         = param.get("doc")

            printer << BULLET + ansi.style(**STYLES["identifier"])(name)
            if default is not None:
                printer << " default=" + default["repr"]
            printer.newline()

            if doc_type is not None:
                printer <= "  [type: " + doc_style(doc_type) + "]"
            if doc is not None:
                printer <= "  " + doc_style(doc)

        printer.newline()

    # Summarize contents.
    if dict is not None and len(dict) > 0:
        printer <= "dict:"
        for name in sorted(dict):
            printer <= BULLET + name


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "name", metavar="NAME",
        help="fully-qualified module or object name")
    parser.add_argument(
        "--json", default=False, action="store_true",
        help="dump JSON docs")
    parser.add_argument(
        "--path", metavar="FILE", default=None,
        help="read JSON docs from FILE")
    args = parser.parse_args()

    # Find the requested object.
    try:
        path, obj = inspector.split(args.name)
    except NameError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)

    if args.path is None:
        sdoc = inspector.inspect_modules([path.modname])
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
        print_docs(sdoc, odoc, Printer(indent=" "))


if __name__ == "__main__":
    _main()
