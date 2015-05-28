import builtins
import collections
from   contextlib import suppress
import importlib
import inspect
import json
import logging
import os
import sys
import sysconfig
import traceback
import types

#-------------------------------------------------------------------------------

# Maximum length of an object repr to store.
MAX_REPR_LENGTH = 65536

# Identifiers that are implementation details.
INTERNAL_NAMES = {
    "__all__",  # FIXME: Indicate this somehow.
    "__builtins__",
    "__cached__",
    "__dict__",
    "__doc__",
    "__file__",
    "__loader__",
    "__module__",
    "__name__",
    "__package__",
    "__spec__",
    "__weakref__",
    }

# FIXME: Look up the rest.
SPECIAL_NAMES = {
    "__cmp__"       : "comparison",
    "__delattr__"   : "delete attribute",
    "__delitem__"   : "delete item",
    "__eq__"        : "equality",
    "__ge__"        : "greater than or equal",
    "__getattr__"   : "get attribute",
    "__getitem__"   : "get item",
    "__gt__"        : "greater than",
    "__hash__"      : "hash code",
    "__init__"      : "constructor",
    "__le__"        : "less than or equal",
    "__lt__"        : "less-than",
    "__ne__"        : "inequality",
    "__new__"       : "allocator",
    "__repr__"      : "representation",
    "__setattr__"   : "set attribute",
    "__setitem__"   : "set item",
    "__str__"       : "string",
    }

# Types that have docstrings.
DOCSTRING_TYPES = (
    property,
    type,
    types.FunctionType,
    types.ModuleType,
    )

#-------------------------------------------------------------------------------

class Path(collections.namedtuple("Path", ("module", "qualname"))):

    @classmethod
    def of(class_, obj):
        """
        Returns the path reported by an object.
        """
        if isinstance(obj, types.ModuleType):
            try:
                name = obj.__name__
            except AttributeError:
                return None
            else:
                if name is not None:
                    return class_(name, None)

        try:
            module = obj.__module__
            qualname = obj.__qualname__
        except AttributeError:
            pass
        else:
            if module is not None:
                return class_(module, qualname)

        return None


    def mangle(self):
        if self.qualname is None:
            raise ValueError("no qualname")
        parts = self.qualname.split(".")
        if len(parts) < 2 or not parts[-1].startswith("__"):
            raise ValueError("not a private name")
        else:
            mangled = ".".join(parts[: -1]) + "._" + parts[-2] + parts[-1]
            return self.__class__(self.module, mangled)



def import_(name):
    """
    Imports a module.

    @param name
      The fully-qualified module name.
    @rtype
      module
    @raise ImportError
      The name could not be imported.
    """
    __import__(name)
    return sys.modules[name]


def look_up(name, obj):
    """
    Looks up a qualified name.
    """
    result = obj
    for part in name.split("."):
        result = getattr(result, part)
    return result


def resolve(path):
    module = import_(path.module)
    return module if path.qualname is None else look_up(path.qualname, module)


_ref_modules = set()
_orphans = {}


def _make_ref(path):
    assert path is not None

    _ref_modules.add(path.module)

    ref = "#/modules/" + path.module
    if path.qualname is not None:
        ref += "/dict/" + "/dict/".join(path.qualname.split("."))
    return {"$ref": ref}


# FIXME: Not used.
def is_imposter(obj):
    """
    Returns true if `obj` has a path that doesn't resolve back to it.
    """
    path = Path.of(obj)
    if path is None:
        # Doesn't carry its own path.
        return False
    try:
        resolved_obj = resolve(path)
    except AttributeError:
        # Doesn't resolve to anything.
        return True
    # Does the path resolve back to the object?
    return resolved_obj is not obj


def is_mangled(obj):
    """
    Returns true if `obj` has a mangled private name.
    """
    # Check by constructing the mangled path, resolving that, and comparing.
    path = Path.of(obj)
    if path is None:
        # Doesn't carry its own path.
        return False
    try:
        mangled_path = path.mangle()
    except ValueError:
        # Doesn't have a private name.
        return False
    try:
        resolved_obj = resolve(mangled_path)
    except AttributeError:
        # Nothing at the mangled path.
        return False
    else:
        # Does the mangled path resolve back to the object?
        return resolved_obj is obj


def _inspect(obj, inspect_path):
    logging.info("_inspect({!r}, {!r})".format(obj, inspect_path))

    mangled = is_mangled(obj)
    imposter = not mangled and is_imposter(obj)

    path = Path.of(obj)
    if mangled:
        path = path.mangle()

    if path is not None and (inspect_path is None or path != inspect_path):
        # Defined elsewhere.  Produce a ref.
        return _make_ref(path)
    
    jso = {}

    if mangled:
        jso["mangled"] = True

    type_path = Path.of(type(obj))
    if type_path is not None:
        jso["type"] = _make_ref(type_path)
    jso["type_name"] = type(obj).__name__
    try:
        obj_repr = repr(obj)
    except Exception:
        log.warning("failed to get repr: {}".format(traceback.format_exc()))
    else:
        jso["repr"] = obj_repr[: MAX_REPR_LENGTH]

    try:
        name = obj.__name__
    except AttributeError:
        pass
    else:
        jso["name"] = name

    try:
        qualname = obj.__qualname__
    except AttributeError:
        pass
    else:
        jso["qualname"] = qualname

    try:
        module = obj.__module__
    except AttributeError:
        pass
    else:
        if module is not None:
            # Convert the module name into a ref.
            jso["module"] = _make_ref(Path(module, None))

    # Get documentation, if it belongs to this object itself (not to the
    # object's type).
    doc = getattr(obj, "__doc__", None)
    if (doc is not None 
        and (isinstance(obj, type) 
             or doc != getattr(type(obj), "__doc__", None))):
        jso["docs"] = {"doc": doc}

    try:
        dict = obj.__dict__
    except AttributeError:
        pass
    else:
        dict_jso = {}
        # FIXME: Don't need to sort, but do this for debuggability.
        names = sorted( n for n in dict if n not in INTERNAL_NAMES )
        for attr_name in names:
            attr_value = dict[attr_name]
            attr_path = Path(
                inspect_path.module, 
                attr_name if inspect_path.qualname is None 
                    else inspect_path.qualname + '.' + attr_name)
            dict_jso[attr_name] = _inspect(attr_value, attr_path)
        jso["dict"] = dict_jso

    try:
        bases = obj.__bases__
    except AttributeError:
        pass
    else:
        jso["bases"] = [ _inspect(b, None) for b in bases ]

    try:
        mro = obj.__mro__
    except AttributeError:
        pass
    else:
        jso["mro"] = [ _inspect(c, None) for c in mro ]

    # If this is callable, get its signature; however, skip types, as we 
    # get their __init__ signature.
    if callable(obj) and not isinstance(obj, type):
        try:
            sig = inspect.signature(obj)
        except ValueError:
            # Doesn't work for extension functions.
            pass
        else:
            jso["signature"] = [
                _inspect_parameter(p) for p in sig.parameters.values() ]

    # If this is a classmethod or staticmethod wrapper, inspect the underlying
    # function.
    try:
        func = obj.__func__
    except AttributeError:
        pass
    else:
        jso["func"] = _inspect(func, inspect_path)

    # If this is a property, inspect the underlying accessors.
    if isinstance(obj, property):
        jso["get"] = None if obj.fget is None else _inspect(obj.fget, inspect_path)
        jso["set"] = None if obj.fset is None else _inspect(obj.fset, inspect_path)
        jso["del"] = None if obj.fdel is None else _inspect(obj.fdel, inspect_path)

    return jso


def _inspect_parameter(param):
    jso = {
        "name"      : param.name,
        "kind"      : str(param.kind),
    }
    
    annotation = param.annotation
    if annotation is not param.empty:
        jso["annotation"] = _inspect(annotation, None)

    default = param.default 
    if default is not param.empty:
        jso["default"] = _inspect(default, None)

    return jso


#-------------------------------------------------------------------------------

_STDLIB_PATH = os.path.normpath(sysconfig.get_path("stdlib"))

def is_builtin(module_obj):
    """
    @return
      True if `module_obj` is a builtin module.
    """
    if module_obj in {builtins, }:
        return True

    try:
        path = module_obj.__file__
    except AttributeError:
        logging.warning("no __file__ for {!r}".format(module_obj))
        return False
    else:
        path = os.path.normpath(module_obj.__file__)
        return path.startswith(_STDLIB_PATH)


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument(
        "--log-level", metavar="LEVEL", default=None,
        help="log at LEVEL")
    parser.add_argument(
        "--builtins", dest="builtins", default=True, action="store_true",
        help="include builtin modules (default)")
    parser.add_argument(
        "--no-builtins", dest="builtins", default=True, action="store_false",
        help="don't include builtin modules")
    parser.add_argument(
        "modules", nargs="*", metavar="MODULE",
        help="packages and modules to inspect")
    args = parser.parse_args()

    if args.log_level is not None:
        try:
            level = getattr(logging, args.log_level.upper())
        except AttributeError:
            parser.error("invalid log level: {}".format(args.log_level))
        else:
            logging.getLogger().setLevel(level)

    modules_jso = {}

    def inspect_module(module):
        obj = import_(module)
        if args.builtins or not is_builtin(obj):
            logging.debug("inspecting module {}".format(module))
            modules_jso[module] = _inspect(obj, Path(module, None))
        else:
            logging.debug("skipping builtin module {}".format(module))
            modules_jso[module] = None

    for module in "supdoc.test", :
        inspect_module(module)
    while _ref_modules != set(modules_jso):
        for module in _ref_modules - set(modules_jso):
            inspect_module(module)
        
    json.dump({"modules": modules_jso}, sys.stdout, indent=1, sort_keys=True)

    # FIXME: Track all the ids we've inspected, and if an orphan object
    # (it's path doesn't resolve to it) matches one, fix it up afterward.


if __name__ == "__main__":
    main()

