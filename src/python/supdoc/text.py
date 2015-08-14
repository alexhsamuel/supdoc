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

    # json.dump(obj_docs, sys.stdout, indent=1, sort_keys=True)

    for d in obj_docs["docs"]["body"]:
        print(html2text.html2text(d))


if __name__ == "__main__":
    main()


