import collections
from   contextlib import suppress
import importlib
import inspect
import json
import logging
import sys
import traceback
import types

#-------------------------------------------------------------------------------

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

Path = collections.namedtuple("Path", ("module", "qualname"))

def _get_path(obj):
    """
    Returns the path reported by an object.
    """
    if isinstance(obj, types.ModuleType):
        try:
            name = obj.__name__
        except AttributeError:
            pass
        else:
            if name is not None:
                return Path(name, None)

    try:
        module = obj.__module__
        qualname = obj.__qualname__
    except AttributeError:
        pass
    else:
        if module is not None:
            return Path(module, qualname)

    return None


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


def import_path(path):
    module = import_(path.module)
    return module if path.qualname is None else look_up(path.qualname, module)


def _make_ref(path):
    assert path is not None

    ref = "#/modules/" + path.module
    if path.qualname is not None:
        ref += "/dict/" + "/dict/".join(path.qualname.split("."))
    return {"$ref": ref}


def _inspect(obj, inspect_path):
    logging.info("_inspect({!r}, {!r})".format(obj, inspect_path))
    path = _get_path(obj)
    if path is not None and (inspect_path is None or path != inspect_path):
        # Defined elsewhere.  Produce a ref.
        return _make_ref(path)
    
    if path is not None:
        # Look up the object's name, and make sure it resolves to the object.
        named_obj = import_path(path)
        if named_obj is not obj:
            logging.warning(
                "{} is not at {}; instead {}".format(obj, path, named_obj))

    jso = {}

    type_path = _get_path(type(obj))
    if type_path is not None:
        jso["type"] = _make_ref(type_path)
    jso["type_name"] = type(obj).__name__
    try:
        jso["repr"] = repr(obj)
    except Exception:
        log.warning("failed to get repr: {}".format(traceback.format_exc()))

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
            logging.debug("can't get signature for {!r}".format(obj))
        else:
            jso["signature"] = [
                _inspect_parameter(p) for p in sig.parameters.values() ]

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

def main():
    logging.getLogger().setLevel(logging.INFO)
    import csv, builtins, supdoc.test
    modules = [supdoc.test]

    jso = {"modules": [ _inspect(m, _get_path(m)) for m in modules ]}
    json.dump(jso, sys.stdout, indent=1, sort_keys=True)

    # FIXME: Track all the ids we've inspected, and if an orphan object
    # (it's path doesn't resolve to it) matches one, fix it up afterward.


if __name__ == "__main__":
    main()

