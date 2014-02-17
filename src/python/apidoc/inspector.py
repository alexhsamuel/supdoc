"""
API extraction by importing and inspecting modules.

Invoke like this:

  python3 -m apidoc.inspector /path/to/package > apidoc.json

"""

#-------------------------------------------------------------------------------

import functools
import inspect
import logging
import os
import sys

from   apidoc import modules
from   apidoc.path import Path

#-------------------------------------------------------------------------------

def is_special_symbol(symbol):
    return symbol.startswith("__") and symbol.endswith("__")


#-------------------------------------------------------------------------------

class Context:

    def __init__(self):
        pass


    def include(self, obj):
        try:
            path = inspect.getsourcefile(obj)
        except TypeError:
            # Built-in module.
            return False
        else:
            return path is not None



def _get_doc(obj):
    doc = inspect.getdoc(obj)
    if doc is None or doc.strip() == "":
        return {}
    else:
        # Construct paragraphs separated by blank lines.
        # FIXME: While pretty standard, this behavior should be configurable.
        paragraphs = []
        new = True
        for line in doc.splitlines():
            if line == "":
                new = True
            elif new:
                paragraphs.append(line)
                new = False
            else:
                paragraphs[-1] += " " + line
        return {
            "summary": paragraphs.pop(0),
            "doc": paragraphs,
        }


def _get_lines(obj):
    try:
        lines, start_num = inspect.getsourcelines(obj)
    except (OSError, ValueError):
        return None
    else:
        return [start_num, start_num + len(lines)]


def _get_module_path(module):
    try:
        path = inspect.getsourcefile(module)
    except TypeError:
        # Built-in module.
        path = None
    else:
        if path is None:
            path = inspect.getfile(module)
    return None if path is None else Path(path)


def _inspect_module(context, fqname, module):
    return dict(
        type    ="module",
        fqname  =module.__name__, 
        name    =modules.Name(module.__name__)[-1],
        path    =str(_get_module_path(module)),
        )


def _inspect_package_or_module(context, fqname, module):
    result = _inspect_module(context, fqname, module)

    # FIXME: Work around a bug in Python 3.4 that occurs whe importing
    # an empty module file.
    # source = inspect.getsourcelines(module)
    import tokenize
    path = _get_module_path(module)
    with path.open() as file:
        source = file.readlines()

    result.update(
        source      =source,
        dict        =dict( 
            (n, _inspect(context, fqname + n, o)) 
            for n, o in inspect.getmembers(module)
            if not is_special_symbol(n)
            ),
        )
    result.update(_get_doc(module))

    if modules.is_package(module):
        # Include modules and packages that are direct children.
        result.update(
            type    ="package",
            modules = {
                n: _inspect_package_or_module(context, fqname + n, m)
                for n, m in modules.get_submodules(module)
            })
    return result


def inspect_package(context, path):
    path = Path(path)
    if not modules.is_package_dir(path):
        raise ValueError("not a package directory: {}".format(path))

    fqname = modules.Name(path.stem)
    package = modules.load_module(fqname, path / "__init__.py")
    return dict(
        fqname  =None,
        type    ="toplevel",
        modules ={
            str(fqname): _inspect_package_or_module(context, fqname, package)
            },
        )


def _inspect_class(context, fqname, class_):
    result = dict(
        type        ="class",
        )
    if context.include(class_):
        result.update(
            name    =class_.__name__,
            fqname  =str(fqname),
            lines   =_get_lines(class_),
            bases   =[ c.__name__ for c in class_.__bases__ ],
            mro     =[ c.__name__ for c in inspect.getmro(class_) ],
            dict    ={
                n: _inspect(context, fqname + n, o)
                for n, o in inspect.getmembers(class_)
                if not is_special_symbol(n)
                },
            )
        result.update(_get_doc(class_))
    return result


def _inspect_parameter(parameter):
    get = lambda x: None if x is parameter.empty else repr(x)
    return dict(
        name        =parameter.name,
        kind        =str(parameter.kind),
        annotation  =get(parameter.annotation),
        default     =get(parameter.default),
        )


def _inspect_function(context, fqname, function):
    result = dict(
        name    =function.__name__,
        fqname  =str(fqname),
        type    ="function",
        )
    if context.include(function):
        signature = inspect.signature(function)
        result.update(
            lines       =_get_lines(function),
            parameters  =[
                _inspect_parameter(p)
                for n, p in signature.parameters.items()
                ],
            )
        result.update(_get_doc(function))
    return result


def _inspect(context, fqname, obj):
    if inspect.isfunction(obj):
        return _inspect_function(context, fqname, obj)
    elif inspect.isclass(obj):
        return _inspect_class(context, fqname, obj)
    elif inspect.ismodule(obj):
        return _inspect_module(context, fqname, obj)
    else:
        return {
            "type"  : "value",
            "value" : repr(obj),
            }


#-------------------------------------------------------------------------------

import json

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    infos = inspect_package(Context(), sys.argv[1])
    json.dump(infos, sys.stdout, indent=1)


