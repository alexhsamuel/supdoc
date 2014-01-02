import functools
from   importlib.machinery import SourceFileLoader
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

@functools.singledispatch
def do(obj, name):
    if False:
        yield


@do.register(_MODULE_TYPE)
def _(module, name):
    logging.debug("module '{}' in {}".format(name, module.__file__))
    contents = [ do(o, n) for n, o in inspect.getmembers(module) ]
    return DIV(
        SPAN(name, class_="module-name"),
        DIV(*contents, class_="module-contents"),
        class_="module")


@do.register(_FUNCTION_TYPE)
def _(function, name):
    logging.debug("function '{}'".format(name))
    signature = inspect.signature(function)
    return DIV(
        SPAN(name, class_="function-name"),
        SPAN(signature, class_="function-signature"),
        class_="function")


#-------------------------------------------------------------------------------

class Inspector:
    """
    Inspects Python modules and constructs a JSON representation of API info.
    """

    def __init__(self):
        self.__modules = {}


    def inspect(self, name, module):
        result = self._inspect_module(name, module)
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
        # FIXME: Can we use functools.singledispatch on a method?
        if inspect.isfunction(obj):
            return self._inspect_function(name, obj)
        elif inspect.isclass(obj):
            return self._inspect_class(name, obj)
        elif inspect.ismodule(obj):
            return self._inspect_module(name, obj)
        else:
            logging.debug("can't handle {!r}".format(name))
            return None


    def _inspect_parameter(self, name, parameter):
        result = { 
            "name": parameter.name,
            "kind": str(parameter.kind),
            }
        if parameter.annotation is not parameter.empty:
            result["annotation"] = repr(parameter.annotation)
        if parameter.default is not parameter.empty:
            result["default"] = repr(parameter.default)
        return result


    def _inspect_function(self, name, function):
        logging.debug("inspecting function: {}".format(name))
        signature = inspect.signature(function)
        result = {
            "name": name, 
            "type": "function",
            "parameters": [ 
                self._inspect_parameter(n, p)
                for n, p in signature.parameters.items() 
                ],
            }
        if signature.return_annotation is not signature.empty:
            result["return_annotation"] = repr(signature.return_annotation)
        return result            


    def _inspect_class(self, name, class_):
        logging.debug("inspecting class: {}".format(name))
        contents = [ 
            self._inspect(n, o)
            for n, o in inspect.getmembers(class_)
            if not is_special_symbol(n)
            ]
        result = {
            "type": "class",
            "name": class_.__name__,
            "contents": contents,
            }
        return result

        
    def _inspect_module(self, name, module):
        logging.debug("inspect module: {}".format(name))
        result = {
            "name": name,
            "type": "module",
            }
        try:
            result["path"] = module.__file__
        except AttributeError:
            pass
        return result



#-------------------------------------------------------------------------------

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)

    inspector = Inspector()

    for name, path in modules.enumerate_package(sys.argv[1]):
        module = SourceFileLoader(str(name), str(path)).load_module()
        docs = inspector.inspect(name, module)
        print(docs)
        print()


