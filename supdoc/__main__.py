"""
Command line interface to supdoc.

Invoke as::

  python -m supdoc ...

Invoke with `--help` for usage info.
"""

#-------------------------------------------------------------------------------

import argparse
import logging
import json
import sys

from   .cache import get_inspector
from   .exc import FullNameError, ImportFailure, QualnameError
from   .inspector import inspect_path, Inspector
from   .path import split
from   .terminal import print_docs

#-------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    # FIXME: Share some arguments with supdoc.inspector.main().
    parser.add_argument(
        "name", metavar="NAME",
        help="fully-qualified module or object name")
    # FIXME: Generalize this to various caching strategies.
    parser.add_argument(
        "--no-cache", action="store_true", default=False,
        help="don't use or write doc caches")
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
        parser.error(f"can't find name: {args.name}")
    except ImportFailure as exc:
        logging.error(f"error importing module: {exc.modname}", exc_info=True)
        raise SystemExit(1)

    inspector = Inspector() if args.no_cache else get_inspector()

    try:
        objdoc = inspect_path(inspector, path)
    except QualnameError as error:
        # FIXME
        print(error, file=sys.stderr)
        raise SystemExit(1)

    try:
        if args.sdoc:
            json.dump(obj, sys.stdout, indent=1, sort_keys=True)
        elif args.objdoc:
            json.dump(objdoc, sys.stdout, indent=1, sort_keys=True)
        else:
            print_docs(
                inspector, objdoc, path,
                private=args.private, imports=args.imports, source=args.source,
            )
    except BrokenPipeError:
        # Eat this; probably the user killed the pager attached to stdout.
        pass


if __name__ == "__main__":
    main()


