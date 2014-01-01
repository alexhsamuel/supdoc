import functools
import importlib
import inspect
import logging
import os
import pathlib
import sys

#-------------------------------------------------------------------------------

# FIXME: Get these from a canonical location.
_MODULE_TYPE    = type(inspect)
_FUNCTION_TYPE  = type(lambda: 0)


def is_special_symbol(symbol):
    return symbol.startswith("__") and symbol.endswith("__")


#-------------------------------------------------------------------------------

class Path(pathlib.PosixPath):

    def __new__(class_, *args, **kw_args):
        if len(args) == 1 and len(kw_args) == 0 and isinstance(args[0], Path):
            return args[0]
        else:
            return pathlib.PosixPath.__new__(class_, *args, **kw_args).resolve()


    def starts_with(self, prefix):
        return any( p == prefix for p in self.parents )



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

class Name:
    """
    The fully-qualified name of a Python object.
    """

    def __init__(self, parts):
        if isinstance(parts, str):
            parts = parts.split(".")
        else:
            parts = tuple(parts)
        assert len(parts) > 0
        self.__parts = parts


    def __str__(self):
        return ".".join(self.__parts)


    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__, 
            ", ".join( repr(p) for p in self.__parts ))


    def __len__(self):
        return len(self.__parts)


    def __iter__(self):
        return iter(self.__parts)


    def __getitem__(self, index):
        return self.__parts[index]


    @property
    def parent(self):
        if len(self.__parts) == 1:
            raise AttributeError("name '{}' has no parent".format(self))
        return self.__class__(self.__parts[: -1])



    def __plus__(self, part):
        return self.__class__(self.__parts + (parts, ))



def import_module_from_filename(path):
    path = Path(path)
    if path.is_dir():
        # FIXME: Is this general?  Is this right?
        path = path / "__init__.py"

    for load_path in sys.path:
        try:
            relative = path.with_suffix("").relative_to(load_path)
        except ValueError:
            pass
        else:
            name = Name(relative.parts)
            module = importlib.import_module(str(name))
            if Path(module.__file__) == path:
                return name, module
            else:
                logging.warning(
                    "module {} imports from {}, not expected {}".format(
                        name, module.__file__, path))
    raise RuntimeError("{} is not in the Python path".format(path))


class Inspector:
    """
    Inspects Python modules and constructs a JSON representation of API info.
    """

    def __init__(self, path):
        self.__path = os.path.realpath(path)
        self.__packages = {}


    def inspect_package_dir(self, path):
        pass


    def inspect(self, name, obj):
        # FIXME: Can we use functools.singledispatch on a method?
        if inspect.isfunction(obj):
            return self.inspect_function(name, obj)
        elif inspect.isclass(obj):
            return self.inspect_class(name, obj)
        elif inspect.ismodule(obj):
            return self.inspect_module(name, obj)
        else:
            logging.debug("can't handle {!r}".format(name))
            return None


    def inspect_parameter(self, name, parameter):
        result = { 
            "name": parameter.name,
            "kind": str(parameter.kind),
            }
        if parameter.annotation is not parameter.empty:
            result["annotation"] = repr(parameter.annotation)
        if parameter.default is not parameter.empty:
            result["default"] = repr(parameter.default)
        return result


    def inspect_function(self, name, function):
        logging.debug("inspecting function: {}".format(name))
        signature = inspect.signature(function)
        result = {
            "name": name, 
            "type": "function",
            "parameters": [ 
                self.inspect_parameter(n, p)
                for n, p in signature.parameters.items() 
                ],
            }
        if signature.return_annotation is not signature.empty:
            result["return_annotation"] = repr(signature.return_annotation)
        return result            


    def inspect_class(self, name, class_):
        logging.debug("inspecting class: {}".format(name))
        return "CLASS!!"

        
    def inspect_module(self, name, module):
        if not os.path.realpath(module.__file__).startswith(self.__path):
            logging.debug("skipping module: {}".format(name))
            # FIXME
            return None

        logging.debug("inspect module: {}".format(name))
        contents = [
            self.inspect(n, o)
            for n, o in inspect.getmembers(module)
            if not is_special_symbol(n)
            ]
        return {
            "name": name,
            "type": "module",
            "contents": contents,
            }



#-------------------------------------------------------------------------------

if __name__ == "__main__":
    # Remove this module's directory from the load path.
    sys.path.remove(os.path.dirname(os.path.realpath(sys.argv[0])))

    for path in sys.argv[1 :]:
        name, module = import_module_from_filename(path)
        print("{} -> {}".format(name, module))
    

