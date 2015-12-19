import argparse
from   contextlib import suppress
from   enum import Enum
import json
import shutil
import sys

import html2text

import pln.json
from   pln.terminal import ansi

#-------------------------------------------------------------------------------

def look_up(docs, module, name=None):
    """
    Looks up a module or object in docs.

    Finds `module`, then recursively finds `name` by traversing the module's
    and then objects' dictionaries.  

    If `name` is `None`, returns the object itself.

    @param module
      The fully qualified module name.
    @type module
      `str`
    @param name
      The fully qualified name of the object in the module, or `None` for 
      the module itself.
    @type name
      `str` or `None`
    """
    modules = docs["modules"]
    try:
        obj = modules[module]
    except KeyError:
        raise LookupError("no such module: {}".format(module)) from None
    if name is not None:
        parts = name.split(".")
        for i in range(len(parts)):
            try:
                obj = obj["dict"][parts[i]]
            except KeyError:
                missing_name = ".".join(parts[: i + 1])
                raise LookupError("no such name: {}".format(missing_name))
    return obj


def is_last(iterable):
    for item in iterable:
        with suppress(NameError):
            yield False, next_item
        next_item = item
    with suppress(NameError):
        yield True, next_item


#-------------------------------------------------------------------------------

class ReprObj:

    def __init__(self, repr):
        self.__repr = repr


    def __repr__(self):
        return self.__repr



from  inspect import Signature, Parameter

# FIXME: Change the signature JSO to encode a params array and return
# annotation.

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
    parameters = [ parameter_from_jso(o) for o in jso ]
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
        result = prefix + ansi.fg("dark_green")(param.name)
        if param.annotation is not Parameter.empty:
            result += ":" + repr(param.annotation)
        if param.default is not Parameter.empty:
            result += "=" + repr(param.default)
        yield result


width = shutil.get_terminal_size().columns

def format_html(html):
    return html2text.html2text(html, bodywidth=width)


#-------------------------------------------------------------------------------

def print_docs(docs):
    section_header = lambda s: ansi.underline(s) + ":"

    signature = docs.get("signature", None)
    docstring = docs.get("docs", None)

    # Show the name.
    print(ansi.bold(docs["name"]), end="")
    # Show its callable signature, if it has one.
    if signature is not None:
        sig = signature_from_jso(signature)
        print("(")
        for last, line in is_last(format_parameters(sig.parameters)):
            print("  " + line + ("" if last else ","))
        print(")")
    print()

    # Show the doc summary.
    if docstring is not None:
        summary = format_html(docstring.get("summary", "")).strip()
        print(ansi.bold(summary))
        # Show paragraphs of doc body.
        for d in docstring.get("body", []):
            print(format_html(d), end="")
        print()

    # Summarize parameters.
    if signature is not None and len(signature) > 0:
        print(section_header("Parameters"))
        for param in signature:
            print("- " + ansi.fg("dark_green")(param["name"]))
            doc_type = param.get("doc_type")
            if doc_type is not None:
                print("  type: " + doc_type)
            default = param.get("default")
            if default is not None:
                print("  default: " + default["repr"])
            doc = param.get("doc")
            if doc is not None:
                print("  " + ansi.fg("dark_gray")(doc))
        print()

    # Summarize contents.
    dict = docs.get("dict", {})
    if len(dict) > 0:
        print("dict:")
        for name in sorted(dict):
            print("- " + name)


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json", default=False, action="store_true",
        help="dump JSON docs")
    parser.add_argument(
        "--path", metavar="FILE", default=None,
        help="read JSON docs from FILE")
    parser.add_argument(
        "module", metavar="MODULE",
        help="full module name")
    parser.add_argument(
        "name", metavar="NAME", default=None, nargs="?",
        help="object name")
    args = parser.parse_args()

    if args.path is None:
        from . import inspector
        all_docs = inspector.inspect_modules([args.module])
    else:
        # Read the docs file.
        with open(args.path) as file:
            all_docs = json.load(file)

    # Find the requested object.
    try:
        docs = look_up(all_docs, args.module, args.name)
    except LookupError as error:
        # FIXME
        print(error, file=sys.stderr)
        raise SystemExit(1)

    if args.json:
        pln.json.pprint(docs)
    else:
        print_docs(docs)


if __name__ == "__main__":
    _main()
