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
from   apidoc.modules import Name
from   apidoc.path import Path

#-------------------------------------------------------------------------------

def is_special_symbol(symbol):
    return symbol.startswith("__") and symbol.endswith("__")


def is_in_module(obj, module):
    return sys.modules[obj.__module__] is module


def is_in_class(obj, class_):
    return Name(obj.__qualname__).parent == class_.__qualmame__


def get_fqname(obj):
    return Name(obj.__module__) + obj.__qualname__


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


def _inspect_module(fqname, module):
    return dict(
        type    ="module",
        module  =module.__name__,
        name    =Name.of(module).base,
        path    =str(_get_module_path(module)),
        )


def _inspect_package_or_module(fqname, module):
    result = _inspect_module(fqname, module)

    # FIXME: Work around a bug in Python 3.4 that occurs whe importing
    # an empty module file.
    # source = inspect.getsourcelines(module)
    import tokenize
    path = _get_module_path(module)
    with path.open() as file:
        source = file.readlines()
    # FIXME
    source = None

    result.update(
        source      =source,
        dict        =dict( 
            (n, _inspect(fqname + n, o, module)) 
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
                n: _inspect_package_or_module(fqname + n, m)
                for n, m in modules.get_submodules(module)
            })
    return result


def inspect_packages(paths):
    modules = {}
    for path in paths:
        path = Path(path)
        if not modules.is_package_dir(path):
            raise ValueError("not a package directory: {}".format(path))

        fqname = Name(path.stem)
        package = modules.load_module(fqname, path / "__init__.py")
        apidoc = _inspect_package_or_module(fqname, package)
        return (str(fqname), apidoc)

    return dict(
        type        ="modules",
        modules     =modules,
        )


def _inspect_class(fqname, class_, module):
    result = dict(
        type    ="class",
        name    =class_.__name__,
        qualname=class_.__qualname__,
        module  =class_.__module__,
        fqname  =str(get_fqname(class_)),
        )
    if is_in_module(class_, module):
        result.update(
            lines   =_get_lines(class_),
            bases   =[ c.__name__ for c in class_.__bases__ ],
            mro     =[ c.__name__ for c in inspect.getmro(class_) ],
            dict    ={
                n: _inspect(fqname + n, o, module)
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
    fqname = get_fqname(function)
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


def _inspect(fqname, obj, module):
    if inspect.isfunction(obj):
        return _inspect_function(obj, module)
    elif inspect.isclass(obj):
        return _inspect_class(fqname, obj, module)
    elif inspect.ismodule(obj):
        return _inspect_module(fqname, obj)
    else:
        return {
            "type"  : "value",
            "value" : repr(obj),
            }



#-------------------------------------------------------------------------------

import json

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    infos = inspect_packages(sys.argv[1 :])
    json.dump(infos, sys.stdout, indent=1)


