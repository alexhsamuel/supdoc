"""
API extraction by importing and inspecting modules.

Invoke like this:

  python3 -m apidoc.inspector /path/to/package > apidoc.json

Use `inspect_modules()` to produce API documentation for modules.
"""

#-------------------------------------------------------------------------------

import functools
import importlib
import inspect
import logging
import os
import sys
import types

from   . import modules, parse, base
from   .modules import Name
from   .path import Path

#-------------------------------------------------------------------------------

def is_special_symbol(symbol):
    """
    Returns true if `symbol` is a Python special symbol.

    Special symbols begin and end with double underscores.
    """
    return symbol.startswith("__") and symbol.endswith("__")


def is_in_module(obj, module):
    """
    Returns true if an object is defined in a module.

    Uses the object's `__module__` attribute.  If not available, returns False.
    """
    if inspect.isfunction(obj) or inspect.isclass(obj):
        try:
            return obj.__module__ == module.__name__
        except AttributeError:
            return False
    else:
        return False


def is_in_class(obj, class_):
    """
    Returns true if and object is an attribute of a class.

    All sorts of attriutes (including various method types) are included.
    """
    return Name(obj.__qualname__).parent == class_.__qualname__


#-------------------------------------------------------------------------------

def _format_identifier_obj(name, obj):
    """
    Formats an identifier that has been resolved to some `obj`.
    """
    if isinstance(obj, types.ModuleType):
        return parse.MODULE(obj.__name__)
    elif isinstance(obj, type):
        # FIXME: Classes?
        return parse.CLASS(
            name, module=obj.__module__, fullname=obj.__qualname__)
    elif callable(obj):
        return parse.FUNCTION(
            name, module=obj.__module__, fullname=obj.__qualname__)
    else:
        return parse.IDENTIFIER(name)


def _format_identifier(name, contexts):
    for context in contexts:
        # If the context is callable, check its parameters.
        if callable(context):
            sig = inspect.signature(context)
            if name in sig.parameters:
                return parse.PARAMETER(name)

        # Look up the name in the context, if any.
        try:
            obj = base.look_up(name, context)
        except AttributeError:
            pass
        else:
            return _format_identifier_obj(name, obj)

        # If the context is a module, look up the name in all parent packages.
        if isinstance(context, types.ModuleType):
            module = context
            while True:
                package = sys.modules[modules.__package__]
                if package == module:
                    break
                module = package
                try:
                    obj = base.look_up(name, module)
                except AttributeError:
                    pass
                else:
                    return _format_identifier_obj(name, obj)
            
    # Try as a fully-qualified name at the top level.
    try:
        obj = base.import_look_up(name)
    except NameError:
        pass
    else:
        return _format_identifier_obj(name, obj)

    return parse.IDENTIFIER(name)


#-------------------------------------------------------------------------------

def _get_doc(obj, contexts):
    doc = inspect.getdoc(obj)
    if doc is None or doc.strip() == "":
        return {}
    else:
        summary, doc = parse.parse_doc(
            doc, lambda n: _format_identifier(n, contexts))
        return {
            "summary": summary,
            "doc": doc,
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
        type        ="module",
        name        =str(Name.of(module)),
        path        =str(_get_module_path(module)),
        is_import   =True,
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
    result.update(_get_doc(module, (module, )))

    if modules.is_package(module):
        result["type"] = "package"
    return result


def _inspect_class_ref(class_):
    """
    Returns API documentation for a reference to a class.
    """
    return dict(
        type        ="class",
        name        =class_.__name__,
        qualname    =class_.__qualname__,
        module      =class_.__module__,
        is_import   =True,
        )


def _inspect_class(class_, module):
    # Start with basic reference information.
    result = _inspect_class_ref(class_)
    result.update(is_import=False)

    class_name = class_.__qualname__

    def inspect_attr(obj):
        """
        Returns documentation for an attribute of the class.
        """
        # Infer the object's containing class from the qualname, if present.
        try:
            qualname = Name(obj.__qualname__)
        except AttributeError:
            parent = None
        else:
            parent = str(qualname.parent) if qualname.has_parent else None

        # Check that it matches the class we're inspecting.
        if parent is not None and parent != class_name:
            # Not originally member of this class, even though it appears here.
            return _inspect_ref(obj)
        else:
            result = _inspect(obj, module)
            result["class"] = class_name
            return result

    class_dict = {
        n: inspect_attr(o)
        for n, o in inspect.getmembers(class_)
      # if not is_special_symbol(n)
        }

    result.update(
        lines       =_get_lines(class_),
        bases       =[ c.__name__ for c in class_.__bases__ ],
        mro         =[ c.__name__ for c in inspect.getmro(class_) ],
        dict        =class_dict,
       )
    result.update(_get_doc(class_, (class_, module, )))

    return result


def _inspect_parameter(parameter):
    get = lambda x: None if x is parameter.empty else repr(x)
    return dict(
        name        =parameter.name,
        kind        =str(parameter.kind),
        annotation  =get(parameter.annotation),
        default     =get(parameter.default),
        )


def _inspect_function_ref(function):
    return dict(
        type        ="function",
        name        =function.__name__,
        qualname    =function.__qualname__,
        module      =function.__module__,
        )


def _inspect_function(function, module):
    result = _inspect_function_ref(function)
    result.update(is_import=False)

    signature = inspect.signature(function)
    parameters = [
        _inspect_parameter(p)
        for n, p in signature.parameters.items()
        ]

    result.update(
        _get_doc(function, (function, module, )),
        lines       =_get_lines(function),
        parameters  =parameters,
        )
    return result


def _inspect_value(obj):
    return dict(
        type        ="value",
        value_type  =_inspect_ref(type(obj)),
        value       =repr(obj),
        )


def _inspect_ref(obj):
    if inspect.isfunction(obj):
        return _inspect_function_ref(obj)
    elif inspect.isclass(obj):
        return _inspect_class_ref(obj)
    elif inspect.ismodule(obj):
        return _inspect_module_ref(obj)
    else:
        return _inspect_value(obj)


done = set()

def _inspect(obj, module):
    if is_in_module(obj, module):
        # FIXME: Completely bogus.
        if id(obj) in done:
            print("WARNING: already processed {!r}".format(obj), file=sys.stderr)
            return {}
        done.add(id(obj))

        if inspect.isfunction(obj):
            return _inspect_function(obj, module)
        elif inspect.isclass(obj):
            return _inspect_class(obj, module)
        else:
            # FIXME
            raise NotImplementedError(
                "don't know how to inspect {!r}".format(obj))
    else:
        return _inspect_ref(obj)


def inspect_modules(full_names):
    """
    Imports and inspects modules.

    @param full_names
      Iterable of importable full names of modules.
    @return
      JSO API documentation for the modules.
    """
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


