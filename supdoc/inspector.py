from   __future__ import annotations

from   contextlib import suppress
import enum
import inspect
import logging
import traceback
import types
from   weakref import WeakKeyDictionary

from   .docs import enrich
from   .exc import QualnameError
from   .objdoc import make_ref, is_ref, parse_ref, look_up
from   .path import Path, is_imposter, import_, get_obj

#-------------------------------------------------------------------------------

LOG = logging.getLogger(__name__)

# Objdoc schema version.  Bump this whenever anything changes.
VERSION = 1

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
DOCSTRING_TYPES = {
    property,
    type,
    types.FunctionType,
    types.ModuleType,
}

# Types that have paths, i.e. are defined somewhere.
# FIXME: Do we need this?
DEFINED_TYPES = {
    enum.EnumMeta,
    type,
    types.BuiltinFunctionType,
    types.BuiltinMethodType,
    types.FunctionType,
}

#-------------------------------------------------------------------------------

_CODE_TYPES = {
    "builtin_function_or_method",
    "classmethod",
    "classmethod_descriptor",
    "function",
    "getset_descriptor",
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
    return (
        isinstance(typ, type)
        or (typ.__module__ == "builtins" and typ.__name__ in _CODE_TYPES)
    )


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

class Inspector:

    # Used in the objdoc cache to mark an object currently under inspection; used to
    # detect loop.
    IN_PROGRESS = object()

    @staticmethod
    def _get_source(obj):
        """
        Returns source code and line number range for `obj`.

        :return:
          The source code, and a [start, end) pair of line numbers in the source
          file.
        :raise LookupError:
          `obj` has no source, or the source cannot be obtained.
        """
        # FIXME: getsourcelines() is expensive.  Is it necessary?  Perhaps we
        # don't have to call it on each object in a module?
        try:
            lines, start_num = inspect.getsourcelines(obj)
        except (OSError, TypeError, ValueError):
            raise LookupError(f"no source for {obj!r}")
        else:
            # FIXME: Not sure why this is necessary.
            if not isinstance(obj, types.ModuleType):
                start_num -= 1
            return "".join(lines), [start_num, start_num + len(lines)]


    def _inspect_source(self, obj):
        """
        Returns information about the source of `obj`.

        :return:
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
            result["source"], result["lines"] = self._get_source(obj)
        except LookupError:
            pass

        return result


    @staticmethod
    def _inspect_ref(obj):
        """
        Returns a ref to `obj`.

        :param with_type:
          If true, include a "type" field with a ref to `type(obj)`.
        :return:
          A JSO object with a "$ref" key.
        """
        path = Path.of(obj)
        ref = make_ref(path)
        # Add information about its type.
        ref["type"] = make_ref(Path.of(type(obj)))
        return ref


    def _inspect(self, cache, obj, lookup_path: Path=None):
        """
        Inspects `obj` and produces an objdoc or ref.

        Inspects `obj` to determine its type, signature, documentation, and
        other relevant details.  Captures characteristics visible to Python, not
        specified in documentation.

        `lookup_path` is the path by which `obj` was located.  If `obj` carries
        a path and it does not match `lookup_path`, returns a ref instead of
        inspecting, since this object (a module, class, or function) is not the
        location at which it was defined.

        :param obj:
          The object to inspect.
        :param lookup_path:
          The path by which the object has been reached, by module import
          followed by successive `getattr`.  It may not be the same as the name
          by which the object knows itself.
        :return:
          The objdoc extracted from `obj`, or a ref to it.
        """
        # Get the object's path.  If the path doesn't refer back to the object,
        # though, ignore it.
        # FIXME: Simplify this code.
        path = None if is_imposter(obj) else Path.of(obj)

        if path is not None and path != lookup_path:
            # Defined elsewhere.  Produce a ref.
            return self._inspect_ref(obj)

        # Use the cached objdoc, if available.
        try:
            objdoc = cache[obj]
        except KeyError:
            # Not in the cache.  Mark that we're processing it, and continue.
            cache[obj] = self.IN_PROGRESS
        except TypeError:
            # Not hashable or doesn't support weakrefs.
            # FIXME: We need something to detect reference loops of unhashable
            # items, like `d = {}; d[0] = d`.
            pass
        else:
            if objdoc is self.IN_PROGRESS:
                # Found a loop; return a ref.
                del cache[obj]
                return self._inspect_ref(obj)
            else:
                return objdoc

        if isinstance(obj, types.ModuleType):
            LOG.info(f"inspecting module {obj.__name__}")
        else:
            LOG.debug(f"inspecting {lookup_path}")

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
                LOG.warning(f"failed to get repr", exc_info=True)
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

        if isinstance(obj, types.ModuleType):
            try:
                all_names = obj.__all__
            except AttributeError:
                all_names = None
            except KeyError:
                # Some poorly-designed objects raise KeyError on attribute access.
                all_names = None
            else:
                # Just in case.
                all_names = [ str(n) for n in all_names ]
            objdoc["all_names"] = all_names
        else:
            all_names = None

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
                attr_objdoc = (
                    self._inspect_ref(attr_value)
                    if isinstance(attr_value, types.ModuleType)
                    else self._inspect(cache, attr_value, attr_path)
                )
                if all_names is not None:
                    attr_objdoc["exported"] = attr_name in all_names
                dict_jso[attr_name] = attr_objdoc

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
                objdoc["signature"] = self._inspect_signature(cache, sig)

        # If this is a classmethod or staticmethod wrapper, inspect the
        # underlying function.
        try:
            func = obj.__func__
        except (AttributeError, KeyError):
            pass
        else:
            objdoc["func"] = self._inspect(cache, func, lookup_path)

        # If this is a property, inspect the underlying accessors.
        if isinstance(obj, property):
            def insp(obj):
                return (
                    None if obj is None
                    else self._inspect(cache, obj, lookup_path)
                )

            objdoc["get"] = insp(obj.fget)
            objdoc["set"] = insp(obj.fset)
            objdoc["del"] = insp(obj.fdel)

        # Get documentation, if it belongs to this object itself (not to the
        # object's type).
        # FIXME: Maybe just compare obj.__doc__ to type(obj).__doc__?
        doc = getattr(obj, "__doc__", None) if has_code(obj) else None
        if (    doc is not None 
            and isinstance(doc, str)
            and (isinstance(obj, type) 
                 or doc != getattr(type(obj), "__doc__", None))):
            objdoc["docs"] = {"doc": doc}
            # Parse and process docs.
            enrich(objdoc)

        # Put this item in the cache.  Some objects are unhashable, though, so
        # they can't be cached.  Oh well.
        # FIXME: Is there a way around this?
        with suppress(TypeError):
            cache[obj] = objdoc
        return objdoc


    def _inspect_signature(self, cache, sig: inspect.Signature):
        """
        Inspects a signature object.
        """
        objdoc = {
            "params": [
                self._inspect_parameter(cache, p)
                for p in sig.parameters.values()
            ]
        }
        if sig.return_annotation != inspect.Signature.empty:
            # FIXME: Handle future annotations.
            objdoc.setdefault("return", {})["annotation"] = \
                self._inspect(cache, sig.return_annotation)
        return objdoc


    def _inspect_parameter(self, cache, param):
        """
        Inspects a single parameter in a callable signature.

        :return:
          A JSO object with information about `param`.
        """
        jso = {
            "name"      : param.name,
            "kind"      : str(param.kind),
        }

        annotation = param.annotation
        if annotation is not param.empty:
            jso["annotation"] = self._inspect(cache, annotation)

        default = param.default 
        if default is not param.empty:
            jso["default"] = self._inspect(cache, default)

        return jso


    def inspect(self, obj):
        cache = WeakKeyDictionary()
        return self._inspect(cache, obj)


    def inspect_module(self, modname):
        """
        Imports (if necessary) and inspects a module.

        :return:
          Objdoc for the module.
        """
        try:
            obj = import_(modname)
        except ImportError:
            LOG.info(f"skipping unimportable module {modname}")
            return {}

        cache = WeakKeyDictionary()
        return self._inspect(cache, obj, Path(modname, None))



#-------------------------------------------------------------------------------

def inspect_path(inspector, path):
    """
    Returns an objdoc for the object at `path`.

    :raise QualnameError:
      The qualname of `path` could not be found in the module objdoc.
    """
    objdoc = inspector.inspect_module(path.modname)
    if path.qualname is not None:
        try:
            return look_up(objdoc, path.qualname)
        except LookupError as exc:
            raise QualnameError(f"no such name: {exc} in: {path}") from None

    return objdoc


def resolve_ref(inspector, ref):
    """
    Returns the objdoc or ref referred to by `ref`.
    """
    assert is_ref(ref)
    return inspect_path(inspector, parse_ref(ref))


def resolve(inspector, objdoc, *, recursive=True):
    """
    Resolves `objdoc` if it is a ref, otherwise returns it.

    :param recursive:
      If true, keep resolving the result until it is not a ref.
    """
    while is_ref(objdoc):
        objdoc = resolve_ref(inspector, objdoc)
        if not recursive:
            break
    return objdoc


