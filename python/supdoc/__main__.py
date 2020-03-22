"""
Command line interface to supdoc.

Invoke as::

  python -m supdoc ...

Invoke with `--help` for usage info.
"""

#-------------------------------------------------------------------------------

import argparse
import sys
import traceback

import aslib.terminal

from   . import inspector
from   .exc import FullNameError, ImportFailure, QualnameError
from   .path import split
from   .terminal import print_docs

#-------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    # FIXME: Share some arguments with supdoc.inspector.main().
    parser.add_argument(
        "name", metavar="NAME",
        help="fully-qualified module or object name")
    parser.add_argument(
        "--imports", dest="imports", default=False, action="store_true",
        help="show imported mambers")
    parser.add_argument(
        "--no-imports", dest="imports", action="store_false",
        help="don't show imported members")
    parser.add_argument(
        "--objdoc", default=False, action="store_true",
        help="dump object documentation as JSON")
    parser.add_argument(
        "--sdoc", default=False, action="store_true",
        help="dump JSON sdoc")
    parser.add_argument(
        "--path", metavar="FILE", default=None,
        help="read JSON docs from FILE")
    parser.add_argument(
        "--private", default=False, action="store_true",
        help="show private module/class members")
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
    except FullNameError:
        print("can't find name: {}".format(args.name), file=sys.stderr)
        raise SystemExit(1)
    except ImportFailure as error:
        print(
            "error importing module: {}:\n".format(error.modname),
            file=sys.stderr)
        cause = error.__context__
        traceback.print_exception(
            type(cause), cause, cause.__traceback__, file=sys.stderr)
        raise SystemExit(1)

    if args.path is None:
        docsrc = inspector.DocSource(source=args.source)
    else:
        # Read the docs file.
        # FIXME
        # with open(args.path) as file:
        #     sdoc = json.load(file)
        raise NotImplementedError("docs file")

    try:
        objdoc = docsrc.get(path)
    except QualnameError as error:
        # FIXME
        print(error, file=sys.stderr)
        raise SystemExit(1)

    try:
        if args.sdoc:
            aslib.json.pprint(objdoc)
        elif args.objdoc:
            aslib.json.pprint(objdoc)
        else:
            # Leave a one-space border on the right.
            print_docs(
                docsrc, objdoc, path, 
                private=args.private, imports=args.imports)
    except BrokenPipeError:
        # Eat this; probably the user killed the pager attached to stdout.
        pass


if __name__ == "__main__":
    main()


