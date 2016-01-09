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
    "__path__",
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

class Path(collections.namedtuple("Path", ("modname", "qualname"))):
    """
    A fully-qualified lookup path to an object.

    Represents the path to find an object, first by importing a module and then
    by successively using `getattr` to obtain subobjects.  `qualname` is the
    dot-delimited path of names for `getattr`.

    @ivar modname
      The full module name.
    @ivar qualname
      The qualname.
    """

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
            modname = obj.__module__
            qualname = obj.__qualname__
        except AttributeError:
            pass
        else:
            if modname is not None:
                return class_(modname, qualname)

        return None


    def __str__(self):
        return (
            self.modname if self.qualname is None 
            else self.modname + "." + self.qualname
        )


    def mangle(self):
        if self.qualname is None:
            raise ValueError("no qualname")
        parts = self.qualname.split(".")
        if len(parts) < 2 or not parts[-1].startswith("__"):
            raise ValueError("not a private name")
        else:
            mangled = ".".join(parts[: -1]) + "._" + parts[-2] + parts[-1]
            return self.__class__(self.modname, mangled)



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
    module = import_(path.modname)
    return module if path.qualname is None else look_up(path.qualname, module)


def split(name):
    """
    Attempts to split a fully-qualified name into modname and qualname.

    `name` is a fully-qualified name consisting of full module name and
    optionally an object's qualname in that module.  This method attempts to
    split it by importing a prefix `name` as a module and then resolving the
    rest in that module.  It starts with the longest possible prefix and
    continues right-to-left.

    For example, the name `"html.parser.HTMLParser.close"` is resolved
    as follows:

    1. Attempt to import `"html.parser.HTMLParser.close"`.  This fails.
    1. Attempt to import `"html.parser.HTMLParser"`.  This fails.
    1. Attempt to import `"html.parser"`.  This succeeds.  In the resulting
       module, look up `"HTMLParser.close"`, which succeeds.

    The result is thus `Path("html.parser", "HTMLParser.close")`.

    If name contains a colon "`:`", this is unconditionally assumed to be the
    separator between the modname and the qualname, e.g. 
    `"html.parser:HTMLParser.close"`.

    @return
      A `Path` object for the split name, and the object itself.
    @raise NameError
      `name` could not be resolved.
    """
    if ":" in name:
        # Fixed separator between modname and qualname.
        modname, qualname = name.split(":", 1)
        if qualname == "":
            qualname = None

        try:
            module = import_(modname)
            obj = module if qualname is None else look_up(qualname, module)
        except:
            raise NameError("can't find {} in {}".format(qualname, modname))

    else:
        parts = name.split(".")
        # Try successively shorter prefixes as the modname.
        for i in range(len(parts), 0, -1):
            modname = ".".join(parts[: i])
            qualname = None if i == len(parts) else ".".join(parts[i :])
            try:
                module = import_(modname)
                obj = module if qualname is None else look_up(qualname, module)
            except:
                continue
            else:
                break
        else:
            raise NameError("can't find {}".format(name))

    return Path(modname, qualname), obj


# FIXME: Global state.  Possible resolutions:
#  - Pass this stuff around (awkward).
#  - Go fully global: keep a cache of inspected modules.
#  - Encapsulate in a class.
_ref_modules = set()
_orphans = {}
_include_source = False


def _ref_from_path(path):
    if path is None:
        return None
    _ref_modules.add(path.modname)

    ref = "#/modules/" + path.modname
    if path.qualname is not None:
        ref += "/dict/" + "/dict/".join(path.qualname.split("."))

    return {
        "$ref"  : ref,
    }


def _make_ref(obj, *, with_type=True):
    """
    @param with_type
      If true, include a "type" field with a ref to the object's type.
    """
    ref = _ref_from_path(Path.of(obj))
    if ref is not None:
        ref["type"] = (
            _make_ref(type(obj), with_type=False) if with_type else None)
    return ref


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
    except (ImportError, AttributeError):
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
    except (ImportError, AttributeError):
        # Nothing at the mangled path.
        return False
    else:
        # Does the mangled path resolve back to the object?
        return resolved_obj is obj


def _get_source(obj):
    try:
        lines, start_num = inspect.getsourcelines(obj)
    except (OSError, TypeError, ValueError) as exc:
        return None, None
    else:
        # FIXME: Not sure why this is necessary.
        if not isinstance(obj, types.ModuleType):
            start_num -= 1
        return lines, [start_num, start_num + len(lines)]


def _inspect_source(obj):
    module = inspect.getmodule(obj)
    if module is None:
        source_file = None
    else:
        try:
            source_file = inspect.getsourcefile(module)
        except TypeError:
            # Built-in module.
            source_file = None

    try:
        file = inspect.getfile(module)
    except:
        file = None

    source_lines, line_numbers = _get_source(obj)

    result = {
        "source_file"   : source_file,
        "file"          : file,
        "lines"         : line_numbers,
    }
    if _include_source and source_lines is not None:
        result["source"] = "".join(source_lines)
    return result


def _inspect(obj, lookup_path):
    """
    Main inspection function.

    Inspects `obj` to determine its type, signature, documentation, and other
    relevant details.  Captures characteristics visible to Python, not
    specified in documentation.

    If `obj` has a path and it does not match `lookup_path`, returns a 
    `$ref` JSO object instead of inspecting.

    @param obj
      The object to inspect.
    @param lookup_path
      The qualname of the object.  This is the path by which the object has
      been reached, by module import followed by successive `getattr`.  It
      may not be the same as the name by which the object knows itself.
    @type lookup_path
      `Path`.
    @return
      Odoc extracted from the object.
    """
    logging.info("_inspect({!r}, {!r})".format(obj, lookup_path))

    mangled = is_mangled(obj)
    # imposter = not mangled and is_imposter(obj)

    path = Path.of(obj)
    if mangled:
        path = path.mangle()

    if path is not None and (lookup_path is None or path != lookup_path):
        # Defined elsewhere.  Produce a ref.
        # FIXME: If obj has a private name, we should mangle it in the ref.
        return _make_ref(obj)
    
    odoc = {}

    if mangled:
        odoc["mangled_name"] = path.qualname.rsplit(".")[-1]

    if Path.of(type(obj)) is not None:
        odoc["type"] = _make_ref(type(obj))
    odoc["type_name"] = type(obj).__name__
    try:
        obj_repr = repr(obj)
    except Exception:
        log.warning("failed to get repr: {}".format(traceback.format_exc()))
    else:
        odoc["repr"] = obj_repr[: MAX_REPR_LENGTH]

    try:
        name = obj.__name__
    except AttributeError:
        pass
    else:
        odoc["name"] = name

    try:
        qualname = obj.__qualname__
    except AttributeError:
        pass
    else:
        odoc["qualname"] = qualname

    modname = getattr(obj, "__module__", None)
    if modname is not None:
        # Convert the module name into a ref.
        odoc["module"] = _ref_from_path(Path(modname, None))

    # Get documentation, if it belongs to this object itself (not to the
    # object's type).
    doc = getattr(obj, "__doc__", None)
    if (doc is not None 
        and (isinstance(obj, type) 
             or doc != getattr(type(obj), "__doc__", None))):
        odoc["docs"] = {"doc": doc}

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
            if lookup_path is None:
                attr_path = None
            else:
                attr_path = Path(
                    lookup_path.modname, 
                    attr_name if lookup_path.qualname is None 
                        else lookup_path.qualname + '.' + attr_name)
            dict_jso[attr_name] = _inspect(attr_value, attr_path)
        odoc["dict"] = dict_jso

    if isinstance(obj, (type, types.ModuleType, types.FunctionType)):
        odoc["source"] = _inspect_source(obj)

    try:
        bases = obj.__bases__
    except AttributeError:
        pass
    else:
        odoc["bases"] = [ _inspect(b, None) for b in bases ]

    try:
        mro = obj.__mro__
    except AttributeError:
        pass
    else:
        odoc["mro"] = [ _inspect(c, None) for c in mro ]

    # If this is callable, get its signature; however, skip types, as we 
    # get their __init__ signature.
    odoc["callable"] = callable(obj)
    if callable(obj) and not isinstance(obj, type):
        try:
            sig = inspect.signature(obj)
        except ValueError:
            # Doesn't work for extension functions.
            pass
        else:
            odoc["signature"] = {
                "params": [
                    _inspect_parameter(p) for p in sig.parameters.values() ]
            }

    # If this is a classmethod or staticmethod wrapper, inspect the underlying
    # function.
    try:
        func = obj.__func__
    except AttributeError:
        pass
    else:
        odoc["func"] = _inspect(func, lookup_path)

    # If this is a property, inspect the underlying accessors.
    if isinstance(obj, property):
        odoc["get"] = None if obj.fget is None else _inspect(obj.fget, lookup_path)
        odoc["set"] = None if obj.fset is None else _inspect(obj.fset, lookup_path)
        odoc["del"] = None if obj.fdel is None else _inspect(obj.fdel, lookup_path)

    return odoc


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

_BUILTIN_IMPORTER = builtins.__spec__.loader

def is_builtin(module_obj):
    """
    @type module_obj
      `module`.
    @return
      True if `module_obj` is a builtin module.
    """
    if module_obj.__spec__.loader is _BUILTIN_IMPORTER:
        return True

    try:
        path = module_obj.__file__
    except AttributeError:
        logging.warning("no __file__ for {!r}".format(module_obj))
        return False
    else:
        path = os.path.normpath(module_obj.__file__)
        return path.startswith(_STDLIB_PATH)


def inspect_module(modname, *, builtins=False):
    try:
        obj = import_(modname)
    except ImportError:
        logging.debug("skipping unimportable module {}".format(modname))
        return None

    if builtins or not is_builtin(obj):
        logging.debug("inspecting module {}".format(modname))
        return _inspect(obj, Path(modname, None))
    else:
        logging.debug("skipping builtin module {}".format(modname))
        return None


def inspect_modules(modnames, *, refs=True, builtins=False, 
                    include_source=False):
    """
    @param refs
      If true, also inspect any directly or indirectly referenced modules.
    """
    # FIXME: Global state.
    _ref_modules.clear()
    module_docs = {}
    global _include_source
    _include_source = bool(include_source)

    # Inspect all the requested modules.
    for modname in modnames:
        docs = inspect_module(modname, builtins=True)
        # FIXME
        if docs is not None:
            module_docs[modname] = docs
    # Inspect referenced modules.
    while refs and len(_ref_modules - set(module_docs)) > 0:
        for modname in _ref_modules - set(module_docs):
            module_docs[modname] = inspect_module(modname, builtins=builtins)

    from . import docs
    docs.enrich_modules(module_docs)
        
    return {"modules": module_docs}


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument(
        "--log-level", metavar="LEVEL", default=None,
        help="log at LEVEL")
    parser.add_argument(
        "--builtins", dest="builtins", default=True, action="store_true",
        help="inspect builtin modules (default)")
    parser.add_argument(
        "--no-builtins", dest="builtins", default=True, action="store_false",
        help="don't inspect builtin modules")
    parser.add_argument(
        "--referencess", dest="refs", default=True, action="store_true",
        help="inspect referenced modules")
    parser.add_argument(
        "--no-references", dest="refs", default=True, action="store_false",
        help="don't inspect referenced modules")
    parser.add_argument(
        "--source", dest="include_source", default=False, action="store_true",
        help="include source")
    parser.add_argument(
        "--no-source", dest="include_source",  action="store_false",
        help="don't include source")
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

    docs = inspect_modules(
        args.modules, builtins=args.builtins, refs=args.refs, 
        include_source=args.include_source)
    json.dump(docs, sys.stdout, indent=1, sort_keys=True)

    # FIXME: Track all the ids we've inspected, and if an orphan object
    # (its path doesn't resolve to it) matches one, fix it up afterward.


if __name__ == "__main__":
    main()

