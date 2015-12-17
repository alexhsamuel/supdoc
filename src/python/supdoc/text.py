import argparse
from   contextlib import suppress
from   enum import Enum
import json
import shutil
import sys

import html2text

from   . import ansi

#-------------------------------------------------------------------------------

def look_up(docs, module, name=None):
    """
    Looks up a module or object in docs.

    @param module
      The fully qualified module name.
    @param name
      The fully qualified name of the object in the module, or `None` for 
      the module itself.
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
        result = prefix + ansi.fg(param.name, ansi.GREEN, False)
        if param.annotation is not Parameter.empty:
            result += ":" + repr(param.annotation)
        if param.default is not Parameter.empty:
            result += "=" + repr(param.default)
        yield result


width = shutil.get_terminal_size().columns

def format_html(html):
    return html2text.html2text(html, bodywidth=width)


#-------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", metavar="FILE",
        help="file to read")
    parser.add_argument(
        "module", metavar="MODULE",
        help="full module name")
    parser.add_argument(
        "name", metavar="NAME", default=None, nargs="?",
        help="object name")
    args = parser.parse_args()

    # Read the docs file.
    with open(args.path) as file:
        all_docs = json.load(file)

    # Find the requested object.
    try:
        docs = look_up(all_docs, args.module, args.name)
    except LookupError:
        # None.
        pass
    else:
        # Show the name.
        print(ansi.bold(docs["name"]), end="")
        # Show its callable signature, if it has one.
        try:
            signature = docs["signature"]
        except KeyError:
            print()
        else:
            signature = signature_from_jso(signature)
            print("(")
            for last, line in is_last(format_parameters(signature.parameters)):
                print("  " + line + ("" if last else ","))
            print(")")

        # Show the doc summary.
        summary = format_html(docs.get("summary", "")).strip()
        print(summary)
        print("=" * len(summary))
        # Show paragraphs of doc body.
        for d in docs.get("body", []):
            print(format_html(d), end="")
        print()

    # Summarize contents.
    for name in sorted(docs.get("dict", {})):
        print("-" + name)


if __name__ == "__main__":
    main()
