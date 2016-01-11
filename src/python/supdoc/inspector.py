import builtins
import collections
from   contextlib import suppress
import importlib
import inspect
import json
import os
import sys
import sysconfig
import traceback
import types

import pln.log

#-------------------------------------------------------------------------------

LOG = pln.log.get()

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


def _make_ref(path):
    if path is None:
        return None
    else:
        ref = "#/modules/" + path.modname
        if path.qualname is not None:
            ref += "/dict/" + "/dict/".join(path.qualname.split("."))
        return {
            "$ref"  : ref,
        }


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


#-------------------------------------------------------------------------------

class Inspector:

    def __init__(self, *, source):
        self.__source = bool(source)
        self.__ref_modnames = set()


    @property
    def referenced_modnames(self):
        """
        Names of modules that have been referenced during inspection.
        """
        return self.__ref_modnames


    @classmethod
    def _get_source(class_, obj):
        """
        Returns source code and line number range for `obj`.

        @return
          The source code, and a [start, end) pair of line numbers in the source
          file.
        @raise LookupError
          `obj` has no source, or the source cannot be obtained.
        """
        try:
            lines, start_num = inspect.getsourcelines(obj)
        except (OSError, TypeError, ValueError) as exc:
            raise LookupError("no source for {!r}".format(obj))
        else:
            # FIXME: Not sure why this is necessary.
            if not isinstance(obj, types.ModuleType):
                start_num -= 1
            return "".join(lines), [start_num, start_num + len(lines)]


    def _inspect_source(self, obj):
        """
        Returns information about the source of `obj`.

        @return
          A JSO object with source information.
        """
        result = {}
        
        module = inspect.getmodule(obj)
        if module is not None:
            with suppress(TypeError):
                result["source_file"] = inspect.getsourcefile(module)
            with suppress(TypeError):
                result["file"] = inspect.getfile(module)
        try:
            source, result["lines"] = self._get_source(obj)
        except LookupError:
            pass
        else:
            if self.__source:
                result["source"] = source

        return result


    def _inspect_ref(self, obj, *, with_type=True):
        """
        Returns a ref to `obj`.

        @param with_type
          If true, include a "type" field with a ref to `type(obj)`.
        @return
          A JSO object with a "$ref" key.
        """
        path = Path.of(obj)
        self.__ref_modnames.add(path.modname)
        ref = _make_ref(path)
        if with_type:
            # Add information about its type.
            ref["type"] = _make_ref(Path.of(type(obj)))
        return ref


    def _inspect(self, obj, lookup_path=None):
        """
        Inspects `obj` and produces an objdoc or ref.

        Inspects `obj` to determine its type, signature, documentation, and
        other relevant details.  Captures characteristics visible to Python, not
        specified in documentation.

        `lookup_path` is the path by which `obj` was located.  If `obj` carries
        a path and it does not match `lookup_path`, returns a ref instead of
        inspecting, since this object (a module, class, or function) is not the
        location at which it was defined.

        @param obj
          The object to inspect.
        @param lookup_path
          The path by which the object has been reached, by module import
          followed by successive `getattr`.  It may not be the same as the name
          by which the object knows itself.
        @type lookup_path
          `Path`.
        @return
          The objdoc extracted from `obj`, or a ref to it.
        """
        path = Path.of(obj)
        if path is not None and lookup_path is not None and path != lookup_path:
            # Defined elsewhere.  Produce a ref.
            return self._inspect_ref(obj)

        if isinstance(obj, types.ModuleType):
            LOG.info("inspecting module {}".format(obj.__name__))
        LOG.debug("_inspect({!r}, {!r})".format(obj, lookup_path))

        objdoc = {}

        if Path.of(type(obj)) is not None:
            objdoc["type"] = _make_ref(Path.of(type(obj)))
        objdoc["type_name"] = type(obj).__name__
        try:
            obj_repr = repr(obj)
        except Exception:
            LOG.warning("failed to get repr: {}".format(traceback.format_exc()))
        else:
            objdoc["repr"] = obj_repr[: MAX_REPR_LENGTH]

        try:
            name = obj.__name__
        except AttributeError:
            pass
        else:
            objdoc["name"] = name

        try:
            qualname = obj.__qualname__
        except AttributeError:
            pass
        else:
            objdoc["qualname"] = qualname

        modname = getattr(obj, "__module__", None)
        if modname is not None:
            # Convert the module name into a ref.
            objdoc["module"] = _make_ref(Path(modname, None))

        # Get documentation, if it belongs to this object itself (not to the
        # object's type).
        doc = getattr(obj, "__doc__", None)
        if (doc is not None 
            and (isinstance(obj, type) 
                 or doc != getattr(type(obj), "__doc__", None))):
            objdoc["docs"] = {"doc": doc}

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
                dict_jso[attr_name] = self._inspect(attr_value, attr_path)
            objdoc["dict"] = dict_jso

        if isinstance(obj, (type, types.ModuleType, types.FunctionType)):
            objdoc["source"] = self._inspect_source(obj)

        try:
            bases = obj.__bases__
        except AttributeError:
            pass
        else:
            objdoc["bases"] = [ self._inspect(b, None) for b in bases ]

        try:
            mro = obj.__mro__
        except AttributeError:
            pass
        else:
            objdoc["mro"] = [
                self._inspect(c, None) for c in mro if c is not obj
            ]

        # If this is callable, get its signature; however, skip types, as we 
        # get their __init__ signature.
        objdoc["callable"] = callable(obj)
        if callable(obj) and not isinstance(obj, type):
            try:
                sig = inspect.signature(obj)
            except ValueError:
                # Doesn't work for extension functions.
                pass
            else:
                objdoc["signature"] = {
                    "params": [
                        self._inspect_parameter(p)
                        for p in sig.parameters.values()
                    ]
                }

        # If this is a classmethod or staticmethod wrapper, inspect the
        # underlying function.
        try:
            func = obj.__func__
        except AttributeError:
            pass
        else:
            objdoc["func"] = self._inspect(func, lookup_path)

        # If this is a property, inspect the underlying accessors.
        if isinstance(obj, property):
            def insp(obj):
                return None if obj is None else self._inspect(obj, lookup_path)

            objdoc["get"] = insp(obj.fget)
            objdoc["set"] = insp(obj.fset)
            objdoc["del"] = insp(obj.fdel)

        return objdoc


    def _inspect_parameter(self, param):
        """
        Inspects a single parameter in a callable signature.

        @return
          A JSO object with information about `param`.
        """
        jso = {
            "name"      : param.name,
            "kind"      : str(param.kind),
        }

        annotation = param.annotation
        if annotation is not param.empty:
            jso["annotation"] = self._inspect(annotation)

        default = param.default 
        if default is not param.empty:
            jso["default"] = self._inspect(default)

        return jso


    def inspect_module(self, modname):
        """
        Imports (if necessary) and inspects a module.

        @return
          Objdoc for the module.
        """
        try:
            obj = import_(modname)
        except ImportError:
            LOG.debug("skipping unimportable module {}".format(modname))
            return None

        return self._inspect(obj, Path(modname, None))
        


def inspect_modules(*modnames, referenced=0, source=False):
    """
    Imports and inspects modules.

    @param referenced
      Whether to inspect referenced modules.  If `False`, does not inspect
      referenced modules.  If 1, inspects only modules referenced directly by
      modules in `modnames`.  If `True`, inspects all directly and indirectly
      referenced modules.
    @param source
      If true, include source in objdocs.
    """
    # Mapping from modname to module objdoc.
    objdocs = {}

    # Set up an inspector for our modules.
    inspector = Inspector(source=source)
    def inspect(modname):
        if modname not in objdocs:
            objdocs[modname] = inspector.inspect_module(modname)
    
    # Inspect modules.
    for modname in modnames:
        inspect(modname)

    if referenced:
        # Inspect referenced modules.
        remaining = inspector.referenced_modnames - set(objdocs)
        while len(remaining) > 0:
            for modname in remaining:
                inspect(modname)
            if referenced == 1:
                break

    # Parse and process docstrings.
    from . import docs
    docs.enrich_modules(objdocs)

    return {"modules": objdocs}


#-------------------------------------------------------------------------------

# FIXME: Elsewhere.

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
        LOG.warning("no __file__ for {!r}".format(module_obj))
        return False
    else:
        path = os.path.normpath(module_obj.__file__)
        return path.startswith(_STDLIB_PATH)


#-------------------------------------------------------------------------------

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
        "--source", dest="source", default=False, action="store_true",
        help="include source")
    parser.add_argument(
        "--no-source", dest="source",  action="store_false",
        help="don't include source")
    parser.add_argument(
        "modules", nargs="*", metavar="MODULE",
        help="packages and modules to inspect")
    args = parser.parse_args()

    if args.log_level is not None:
        # FIXME: Put in pln.logging.
        import logging
        try:
            level = getattr(logging, args.log_level.upper())
        except AttributeError:
            parser.error("invalid log level: {}".format(args.log_level))
        else:
            LOG.setLevel(level)

    docs = inspect_modules(
        args.modules, builtins=args.builtins, refs=args.refs, 
        source=args.source)
    json.dump(docs, sys.stdout, indent=1, sort_keys=True)

    # FIXME: Track all the ids we've inspected, and if an orphan object
    # (its path doesn't resolve to it) matches one, fix it up afterward.


if __name__ == "__main__":
    main()


