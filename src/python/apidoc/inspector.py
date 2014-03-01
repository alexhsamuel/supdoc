"""
API extraction by importing and inspecting modules.

Invoke like this:

  python3 -m apidoc.inspector /path/to/package > apidoc.json

"""

#-------------------------------------------------------------------------------

import functools
import importlib
import inspect
import logging
import os
import sys

from   . import modules
from   .modules import Name
from   .path import Path

#-------------------------------------------------------------------------------

def is_special_symbol(symbol):
    return symbol.startswith("__") and symbol.endswith("__")


def is_in_module(obj, module):
    return sys.modules[obj.__module__] is module


def is_in_class(obj, class_):
    return Name(obj.__qualname__).parent == class_.__qualmame__


#-------------------------------------------------------------------------------

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


def _inspect_module_ref(module):
    return dict(
        type    ="module",
        name    =str(Name.of(module)),
        path    =str(_get_module_path(module)),
        )


INCLUDE_SOURCE = False  # FIXME

def _inspect_module(module):
    result = _inspect_module_ref(module)

    if INCLUDE_SOURCE:
        # FIXME: Work around a bug in Python 3.4 that occurs whe importing
        # an empty module file.
        # source = inspect.getsourcelines(module)
        import tokenize
        path = _get_module_path(module)
        with path.open() as file:
            source = file.readlines()
    else:
        source = None

    result.update(
        source      =source,
        dict        =dict( 
            (n, _inspect(o, module)) 
            for n, o in inspect.getmembers(module)
            if not is_special_symbol(n) 
            ),
        )
    result.update(_get_doc(module))

    if modules.is_package(module):
        result["type"] = "package"
    return result


def _inspect_class(class_, module):
    result = dict(
        type    ="class",
        name    =class_.__name__,
        qualname=class_.__qualname__,
        module  =class_.__module__,
        )
    if is_in_module(class_, module):
        result.update(
            lines   =_get_lines(class_),
            bases   =[ c.__name__ for c in class_.__bases__ ],
            mro     =[ c.__name__ for c in inspect.getmro(class_) ],
            dict    ={
                n: _inspect(o, module)
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


def _inspect_function(function, module):
    signature = inspect.signature(function)
    result = dict(
        type        ="function",
        name        =function.__name__,
        qualname    =function.__qualname__,
        module      =function.__module__,
        parameters  =[
            _inspect_parameter(p)
            for n, p in signature.parameters.items()
            ],
        )
    if is_in_module(function, module):
        result.update(
            lines       =_get_lines(function),
            )
        result.update(_get_doc(function))
    return result


def _inspect(obj, module):
    if inspect.isfunction(obj):
        return _inspect_function(obj, module)
    elif inspect.isclass(obj):
        return _inspect_class(obj, module)
    elif inspect.ismodule(obj):
        return _inspect_module_ref(obj)
    else:
        return {
            "type"  : "value",
            "value" : repr(obj),
            }



def inspect_modules(full_names):
    modules = {
        str(n): _inspect_module(importlib.import_module(str(n)))
        for n in full_names
        }
    return dict(
        type        ="modules",
        modules     =modules,
        )


#-------------------------------------------------------------------------------

import json

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    module_names = modules.find_modules(sys.argv[1])
    infos = inspect_modules(module_names)
    json.dump(infos, sys.stdout, indent=1)


