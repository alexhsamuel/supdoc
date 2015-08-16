import argparse
import json
import sys

import html2text

#-------------------------------------------------------------------------------

def look_up(docs, module, name):
    obj = docs["modules"][module]
    parts = () if name == "" else name.split(".")
    for part in parts:
        obj = obj["dict"][part]
    return obj


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
        "name", metavar="NAME", default="", nargs="?",
        help="object name")
    args = parser.parse_args()

    with open(args.path) as file:
        all_docs = json.load(file)
    obj_docs = look_up(all_docs, args.module, args.name)

    # json.dump(
    #     { n: v for n, v in obj_docs.items() if n not in {"docs", } },
    #     sys.stdout,
    #     indent=1, sort_keys=True)
    # print()
    # print()

    try:
        docs = obj_docs["docs"]
    except KeyError:
        # None.
        return

    try:
        signature = obj_docs["signature"]
    except KeyError:
        print(obj_docs["name"])
    else:
        signature = signature_from_jso(signature)
        print(obj_docs["name"] + str(signature))
        
    summary = html2text.html2text(docs.get("summary", "")).strip()
    print(summary)
    print("=" * len(summary))

    for d in docs.get("body", []):
        print(html2text.html2text(d), end="")


if __name__ == "__main__":
    main()


