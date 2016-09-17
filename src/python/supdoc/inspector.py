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
from   weakref import WeakKeyDictionary

import aslib.log

from   .docs import parse_doc, parse_doc_markdown, attach_javadoc_to_signature
from   .objdoc import *
from   .path import *

#-------------------------------------------------------------------------------

LOG = aslib.log.get()
# LOG.setLevel(20)

# Maximum length of an object repr to store.
MAX_REPR_LENGTH = 65536

# Identifiers that are implementation details.
INTERNAL_NAMES = {
    "__all__",
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

# FIXME: Elsewhere.

_STDLIB_PATH = os.path.normpath(sysconfig.get_path("stdlib"))

_BUILTIN_IMPORTER = builtins.__spec__.loader

def is_standard_library(module):
    """
    Returns true if `module` is from the Python standard library.

    Standard library modules are either built-in or are imported from the
    standard library location.

    @type module
      `types.ModuleType`.
    """
    if module.__spec__.loader is _BUILTIN_IMPORTER:
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

_CODE_TYPES = {
    "builtin_function_or_method",
    "classmethod",
    "classmethod_descriptor",
    "function",
    "method_descriptor",
    "module",
    "property",
    "staticmethod",
    "type",
    "wrapper_descriptor",
}

def has_code(obj):
    """
    Returns true iff `obj` is associated with code.

    An object with code lives in a module and may have a docstring.
    """
    # FIXME: This is probably not the best way to do it.
    typ = type(obj)
    return typ.__module__ == "builtins" and typ.__name__ in _CODE_TYPES


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
        resolved_obj = get_obj(mangled_path)
    except (ImportError, AttributeError):
        # Nothing at the mangled path.
        return False
    else:
        # Does the mangled path resolve back to the object?
        return resolved_obj is obj


#-------------------------------------------------------------------------------

# Used in the objdoc cache to mark an object curretly under inspection; used to
# detect loop.
IN_PROGRESS = object()

class Inspector:

    def __init__(self, *, source):
        self.__source = bool(source)
        self.__ref_modnames = set()
        # Cache from object to its objdoc.
        self.__cache = WeakKeyDictionary()


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
        # FIXME: getsourcelines() is expensive.  Is it necessary?  Perhaps we
        # don't have to call it on each object in a module?
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
        ref = make_ref(path)
        if with_type:
            # Add information about its type.
            ref["type"] = make_ref(Path.of(type(obj)))
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
        # Get the object's path.  If the path doesn't refer back to the object,
        # though, ignore it.
        path = None if is_imposter(obj) else Path.of(obj)

        if path is not None and lookup_path is not None and path != lookup_path:
            # Defined elsewhere.  Produce a ref.
            return self._inspect_ref(obj)

        # Use the cached objdoc, if available.
        try:
            objdoc = self.__cache[obj]
        except KeyError:
            # Not in the cache.  Mark that we're processing it, and continue.
            self.__cache[obj] = IN_PROGRESS
        except TypeError:
            # Not hashable or doesn't support weakrefs.
            # FIXME: We need something to detect reference loops of unhashable
            # items, like `d = {}; d[0] = d`.
            pass
        else:
            if objdoc is IN_PROGRESS:
                # Found a loop; return a ref.
                del self.__cache[obj]
                LOG.info("found loop: {}".format(lookup_path))  # FIXME: Remove.
                return self._inspect_ref(obj)
            else:
                return objdoc

        if isinstance(obj, types.ModuleType):
            LOG.info("inspecting module {}".format(obj.__name__))
        else:
            LOG.debug("inspecting {}".format(lookup_path))

        objdoc = {}

        if Path.of(type(obj)) is not None:
            objdoc["type"] = self._inspect_ref(type(obj))
        # FIXME: Get rid of this; we shouldn't need it.
        objdoc["type_name"] = type(obj).__name__

        # Add the repr, unless it's the default repr.
        is_default_repr = type(obj).__repr__ is object.__repr__
        if not is_default_repr:
            try:
                obj_repr = repr(obj)
            except Exception:
                LOG.warning(
                    "failed to get repr: {}".format(traceback.format_exc()))
            else:
                objdoc["repr"] = obj_repr[: MAX_REPR_LENGTH]

        try:
            name = obj.__name__
        except (AttributeError, KeyError):
            pass
        else:
            objdoc["name"] = name

        try:
            qualname = obj.__qualname__
        except (AttributeError, KeyError):
            pass
        else:
            objdoc["qualname"] = qualname

        # Everything that actually is in a module, i.e. is code, such as as 
        # class or function, is an instance of a builtin type.  Anything else
        # that reports a __modname__ is probably getting it from its own type.
        modname = getattr(obj, "__module__", None) if has_code(obj) else None
        if modname is not None:
            # Convert the module name into a ref.
            objdoc["module"] = make_ref(Path(modname, None))

        try:
            all_names = obj.__all__
        except AttributeError:
            pass
        else:
            objdoc["all_names"] = [ str(n) for n in all_names ]

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
                attr_path = (
                    None if lookup_path is None 
                    else lookup_path / attr_name
                )

                # Inspect the value, unless it's a module, in which case just
                # put in a ref.
                # FIXME: Should _inspect() always return a ref for a module?
                dict_jso[attr_name] = (
                    self._inspect_ref(attr_value)
                    if isinstance(attr_value, types.ModuleType)
                    else self._inspect(attr_value, attr_path)
                )
                
            objdoc["dict"] = dict_jso

        if isinstance(obj, (type, types.ModuleType, types.FunctionType)):
            objdoc["source"] = self._inspect_source(obj)

        try:
            bases = obj.__bases__
        except (AttributeError, KeyError):
            pass
        else:
            objdoc["bases"] = [ self._inspect_ref(b) for b in bases ]

        try:
            mro = obj.__mro__
        except (AttributeError, KeyError):
            pass
        else:
            objdoc["mro"] = [ self._inspect_ref(c) for c in mro ]

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
        except (AttributeError, KeyError):
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

        # Get documentation, if it belongs to this object itself (not to the
        # object's type).
        doc = getattr(obj, "__doc__", None) if has_code(obj) else None
        if (    doc is not None 
            and isinstance(doc, str)
            and (isinstance(obj, type) 
                 or doc != getattr(type(obj), "__doc__", None))):
            objdoc["docs"] = obj_docs = {"doc": doc}

            # Parse and process docs.
            # FIXME: Wrap these two in a function?
            obj_docs.update(parse_doc_markdown(doc))
            attach_javadoc_to_signature(objdoc)

        # Put this item in the cache.  Some objects are unhashable, though, so
        # they can't be cached.  Oh well.
        # FIXME: Is there a way around this?
        with suppress(TypeError):
            self.__cache[obj] = objdoc
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
            LOG.info("skipping unimportable module {}".format(modname))
            return {}

        return self._inspect(obj, Path(modname, None))
        


#-------------------------------------------------------------------------------

class DocSource:
    # FIXME: Cache invalidation logic: check file mtime and reload?

    def __init__(self, *, source=False):
        self.__source = bool(source)
        self.__inspector = Inspector(source=source)
        

    def inspect_module(self, modname):
        return self.__inspector.inspect_module(modname)


    # FIXME: Do we need this?
    def inspect_modules(self, *modnames, referenced=0):
        """
        Imports and inspects modules.

        @param referenced
          Whether to inspect referenced modules.  If `False`, does not inspect
          referenced modules.  If 1, inspects only modules referenced directly
          by modules in `modnames`.  If `True`, inspects all directly and
          indirectly referenced modules.
        """
        # Mapping from modname to module objdoc.
        objdocs = {}

        # Set up an inspector for our modules.
        def inspect(modname):
            if modname not in objdocs:
                objdocs[modname] = self.inspect_module(modname)

        # Inspect modules.
        for modname in modnames:
            inspect(modname)

        if referenced:
            # Inspect referenced modules.
            remaining = self.referenced_modnames - set(objdocs)
            while len(remaining) > 0:
                for modname in remaining:
                    inspect(modname)
                if referenced == 1:
                    break

        # Parse and process docstrings.
        from . import docs
        docs.enrich_modules(objdocs)

        return {"modules": objdocs}


    def get(self, path):
        """
        Returns an objdoc for the object at `path`.

        @raise QualnameError
          The qualname of `path` could not be found in the module objdoc.
        """
        objdoc = self.inspect_module(path.modname)
        if path.qualname is not None:
            parts = path.qualname.split(".")
            for i in range(len(parts)):
                try:
                    objdoc = objdoc["dict"][parts[i]]
                except KeyError:
                    missing_name = ".".join(parts[: i + 1])
                    raise QualnameError(
                        "no such name: {} in: {}".format(missing_name, path))

        return objdoc


    def resolve_ref(self, ref):
        """
        Returns the objdoc or ref referred to by `ref`.
        """
        assert is_ref(ref)
        return self.get(parse_ref(ref))


    def resolve(self, objdoc, *, recursive=True):
        """
        Resolves `objdoc` if it is a ref, otherwise returns it.

        @param recursive
          If true, keep resolving the result until it is not a ref.
        """
        while is_ref(objdoc):
            objdoc = self.resolve_ref(objdoc)
            if not recursive:
                break
        return objdoc



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
        # FIXME: Put in aslib.logging.
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


