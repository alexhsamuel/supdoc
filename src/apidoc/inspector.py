import functools
import inspect
import logging
import os
import sys

from   apidoc import modules
from   apidoc.path import Path

#-------------------------------------------------------------------------------

# FIXME: Get these from a canonical location.
_MODULE_TYPE    = type(inspect)
_FUNCTION_TYPE  = type(lambda: 0)


def is_special_symbol(symbol):
    return symbol.startswith("__") and symbol.endswith("__")


#-------------------------------------------------------------------------------

class Context:

    def __init__(self, path):
        self.__path = Path(path)


    def include(self, obj):
        try:
            path = inspect.getsourcefile(obj)
        except TypeError:
            # Build-in module.
            return False
        else:
            if path is None:
                # FIXME
                # It's a built-in module.
                return False
            else:
                path = Path(path)
                return path == self.__path



def _get_lines(obj):
    try:
        lines, start_num = inspect.getsourcelines(obj)
    except (OSError, ValueError):
        return None
    else:
        return [start_num, start_num + len(lines)]


def _inspect_module(module, context):
    try:
        path = inspect.getsourcefile(module)
    except TypeError:
        # Built-in module.
        path = "(built-in)"
    else:
        if path is None:
            path = inspect.getfile(module)

    result = dict(
        type        ="module",
        path        =path,
        )
    if context.include(module):
        logging.debug("inspecting module {}".format(module.__name__))
        result.update(
            # FIXME
            #source  =inspect.getsourcelines(module),
            dict    =dict( 
                (n, _inspect(o, context)) 
                for n, o in inspect.getmembers(module)
                if not is_special_symbol(n)
                ),
            )
    return result


def _inspect_class(class_, context):
    result = dict(
        type        ="class",
        )
    if context.include(class_):
        result.update(
            lines   =_get_lines(class_),
            bases   =[ c.__name__ for c in class_.__bases__ ],
            mro     =[ c.__name__ for c in inspect.getmro(class_) ],
            dict    =dict(
                (n, _inspect(o, context))
                for n, o in inspect.getmembers(class_)
                if not is_special_symbol(n)
                ),
            )
    return result


def _inspect_parameter(parameter):
    get = lambda x: None if x is parameter.empty else repr(x)
    return dict(
        name        =parameter.name,
        kind        =str(parameter.kind),
        annotation  =get(parameter.annotation),
        default     =get(parameter.default),
        )


def _inspect_function(function, context):
    result = dict(
        type            ="function",
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
    return result


def _inspect(obj, context):
    if inspect.isfunction(obj):
        return _inspect_function(obj, context)
    elif inspect.isclass(obj):
        return _inspect_class(obj, context)
    elif inspect.ismodule(obj):
        return _inspect_module(obj, context)
    else:
        return {
            "type"  : "value",
            "value" : repr(obj),
            }



def inspect_package(path):
    path = Path(path)

    infos = {}
    for name, module_path in modules.enumerate_package(path):
        module = modules.load_module(name, module_path)
        info = _inspect_module(module, Context(module_path))
        infos[str(name)] = info

    return infos


