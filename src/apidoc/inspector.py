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

class Inspector:
    """
    Inspects Python modules and constructs a JSON representation of API info.
    """

    def __init__(self):
        self.__modules = {}


    def inspect(self, name, module):
        result = self._inspect(name, module)
        result["contents"] = [
            self._inspect(n, o)
            for n, o in inspect.getmembers(module)
            if not is_special_symbol(n)
            ]
        
        package = self.__modules
        for part in name[: -1]:
            package = package.setdefault(part)
        package[name[-1]] = result

        return result


    def _inspect(self, name, obj):
        try:
            lines, start_line = inspect.getsourcelines(obj)
        except (TypeError, OSError):
            pass
        else:
            result["lines"] = [start_line, start_line + len(lines)]

        # FIXME: Can we use functools.singledispatch on a method?
        if inspect.isfunction(obj):
            return self._inspect_function(name, obj, result)
        elif inspect.isclass(obj):
            return self._inspect_class(name, obj, result)
        elif inspect.ismodule(obj):
            return self._inspect_module_reference(name, obj, result)
        else:
            logging.debug("can't handle {} {!r}".format(type(name).__name__, name))
            return None


    def _inspect_parameter(self, parameter):
        result = { 
            "name": parameter.name,
            "kind": str(parameter.kind),
            }
        if parameter.annotation is not parameter.empty:
            result["annotation"] = repr(parameter.annotation)
        if parameter.default is not parameter.empty:
            result["default"] = repr(parameter.default)
        return result


    def _inspect_function(self, name, function, result):
        logging.debug("inspecting function: {}".format(name))
        signature = inspect.signature(function)
        result.update(
            type        ="function",
            parameters  =[
                self._inspect_parameter(p)
                for n, p in signature.parameters.items() 
                ],
            )
        if signature.return_annotation is not signature.empty:
            result["return_annotation"] = repr(signature.return_annotation)
        return result            


    def _inspect_class(self, name, class_, result):
        logging.debug("inspecting class: {}".format(name))
        result.update(
            type    ="class",
            name    =class_.__name__,
            bases   =class_.__bases__,
            mro     =inspect.getmro(class_),
            contents=[ 
                self._inspect(n, o)
                for n, o in inspect.getmembers(class_)
                if not is_special_symbol(n)
                ],
            )
        return result

        
    def _inspect_module_reference(self, name, module, result):
        logging.debug("inspect module: {}".format(name))
        result.update(
            type    ="module",
            )
        try:
            _add(result, "path", inspect.getsourcefile(module))
        except TypeError:
            pass
        return result



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


