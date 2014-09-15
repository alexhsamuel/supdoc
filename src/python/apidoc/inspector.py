"""
API extraction by importing and inspecting modules.

Invoke like this:

  python3 -m apidoc.inspector /path/to/package > apidoc.json

Use `inspect_modules()` to produce API documentation for modules.
"""

#-------------------------------------------------------------------------------

import functools
import importlib
import inspect
import logging
import os
import sys
import traceback
import types

from   . import modules, parse, base
from   .modules import Name
from   .path import Path

#-------------------------------------------------------------------------------

UNINTERESTING_BASE_TYPES = {
    object,
    type,
    }

# Identifiers that are implementation details.
INTERNAL_NAMES = {
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

# Types that have docstrings.
DOCSTRING_TYPES = (
    property,
    type,
    types.FunctionType,
    types.ModuleType,
    )


def is_value_type(obj):
    """
    Returns iff the value of obj should be included directly in docs.
    """
    NOT_VALUE_TYPES = (
        property,
        type,
        types.FunctionType,
        types.ModuleType,
        # FIXME: Others.
        )
    return not isinstance(obj, NOT_VALUE_TYPES)


def has_attributes(obj):
    """
    Returns true if an object has attributes that should be included.
    """
    return isinstance(obj, (type, types.ModuleType))


doc_warning = logging.warning
doc_info    = logging.info


def is_class_method(obj):
    return inspect.ismethod(obj) and isinstance(obj.__self__, type)


def is_internal_name(symbol):
    """
    Returns true if `symbol` is a Python special symbol.

    Special symbols begin and end with double underscores.
    """
    return symbol.startswith("__") and symbol.endswith("__")


def is_in_module(obj, module, default=True):
    """
    Returns true if an object is defined in a module.

    Uses the object's `__module__` attribute.  Returns `default` if that's not
    available.
    """
    obj = getattr(obj, "__func__", obj)

    if inspect.isfunction(obj) or inspect.ismethod(obj) or inspect.isclass(obj):
        try:
            return obj.__module__ == module.__name__
        except AttributeError:
            return False
    else:
        return default


#-------------------------------------------------------------------------------

def _format_identifier_obj(name, obj):
    """
    Formats an identifier that has been resolved to some `obj`.
    """
    return parse.OBJ(name, module=getattr(obj, "__module__", None))


def _format_identifier(name, contexts):
    for context in contexts:
        # If the context is callable, check its parameters.
        if callable(context):
            try:
                sig = inspect.signature(context)
            except ValueError:
                pass
            else:
                if name in sig.parameters:
                    return parse.PARAMETER(name)

        # Look up the name in the context, if any.
        try:
            obj = base.look_up(name, context)
        except AttributeError:
            pass
        else:
            return _format_identifier_obj(name, obj)

        # If the context is a module, look up the name in all parent packages.
        if isinstance(context, types.ModuleType):
            module = context
            while True:
                package = sys.modules[modules.__package__]
                if package == module:
                    break
                module = package
                try:
                    obj = base.look_up(name, module)
                except AttributeError:
                    pass
                else:
                    return _format_identifier_obj(name, obj)
            
    # Try as a fully-qualified name at the top level.
    try:
        obj = base.import_look_up(name)
    except NameError:
        pass
    else:
        return _format_identifier_obj(name, obj)

    return parse.OBJ(name)


#-------------------------------------------------------------------------------

def _get_doc(obj, contexts):
    # Use the docs only for types that carry docstrings, or for objects that
    # carry __doc__ attributes explicitly.  We don't want to pick up a type's
    # __doc__ for an instance of that type.
    if (isinstance(obj, DOCSTRING_TYPES) 
        or "__doc__" in getattr(obj, "__dict__", ())):
        doc = inspect.getdoc(obj)
        if doc is None or doc.strip() == "":
            return {}
        else:
            summary, doc = parse.parse_doc(
                doc, lambda n: _format_identifier(n, contexts))
            return {
                "summary": summary,
                "doc": doc,
            }
    else:
        return {}


def _get_lines(obj):
    try:
        lines, start_num = inspect.getsourcelines(obj)
    except (OSError, TypeError, ValueError) as exc:
        # logging.debug("no source lines for: {!r}: {}".format(obj, exc))
        return None
    else:
        # FIXME: Not sure why this is necessary.
        if not isinstance(obj, types.ModuleType):
            start_num -= 1
        return [start_num, start_num + len(lines)]


def _get_module_path(module):
    try:
        path = inspect.getsourcefile(module)
    except TypeError:
        # Built-in module.
        path = None
    else:
        if path is None:
            path = inspect.getfile(module)
    return None if path is None else Path(path)


def _inspect_ref(obj, module):
    if isinstance(obj, types.ModuleType):
        modname = obj.__name__
        name    = None
    else:
        modname = getattr(obj, "__module__", None)
        name    = getattr(obj, "__qualname__", getattr(obj, "__name__", None))

    return dict(
        modname =modname,
        name    =name,
        type    =type(obj).__name__,
        )


def _resolve_attr(obj, attr_name):
    """
    Finds an attribute; returns it and the parent it came from.
    """
    # If there's an MRO, use it; otherwise, just this object.
    mro = getattr(obj, "__mro__", (obj, ))

    for src in mro:
        try:
            attr = src.__dict__[attr_name]
        except KeyError:
            pass
        else:
            return src, attr
    raise AttributeError(attr_name)


def _add_tags(doc, *tags):
    if len(tags) > 0:
        doc.setdefault("tags", []).extend(tags)


def _inspect_attributes(obj, module):
    """
    Inspects the attributes of an object.

    @param module
      The containing module.  Only a reference will be included for an 
      attribute that is defined in other module.
    """
    # Get all attributes.
    attrs = ( 
        (n, ) + _resolve_attr(obj, n) 
        for n, _ in inspect.getmembers(obj) 
        )

    # Skip attributes inherited from very generic bases.
    attrs = ( 
        (n, s, a) for n, s, a in attrs if s not in UNINTERESTING_BASE_TYPES )
    # Skip internal stuff.
    attrs = ( (n, s, a) for n, s, a in attrs if n not in INTERNAL_NAMES )
        

    def inspect_attr(name, source, attr):
        """
        Returns documentation for an attribute of the class.
        """
        tags = []

        # Look through to underlying function.
        if isinstance(attr, (classmethod, staticmethod)):
            tags.append(type(attr).__name__)
            attr = attr.__func__

        # Check that it matches the class we're inspecting.  Don't embed other
        # module documentation, though.
        # FIXME: Include inherited members?
        if isinstance(attr, types.ModuleType):
            doc = _inspect_ref(attr, module)
            _add_tags(doc, "imported")

        elif source != obj:
            # Not originally member of this, even though it appears here.
            doc = _inspect_ref(attr, module)
            _add_tags(doc, "inherited")

        else:
            # It's defined here.  Include full documentation.
            doc = _inspect(attr, module)

        _add_tags(doc, *tags)
        logging.debug("inspect_attr({!r}) -> {!r}".format(name, doc))
        return doc

    return { n: inspect_attr(n, s, a) for n, s, a in attrs }


def _inspect_parameter(parameter):
    get = lambda x: None if x is parameter.empty else repr(x)
    return dict(
        name        =parameter.name,
        kind        =str(parameter.kind),
        annotation  =get(parameter.annotation),
        default     =get(parameter.default),
        )


def _inspect_obj(obj, module):
    """
    Inspects an object.

    @param module
      The containing module.  For subobjects, only referneces will be included
      for those defined in other modules.
    """
    doc = _inspect_ref(obj, module)

    doc.update(
        _get_doc(obj, (obj, module)),
        lines       =_get_lines(obj),
        )
        
    if has_attributes(obj):
        doc["dict"] = _inspect_attributes(obj, module)

    if callable(obj) and not isinstance(obj, type):
        try:
            signature = inspect.signature(obj)
        except ValueError:
            parameters = [{"name": "?"}]
        else:
            parameters = [
                _inspect_parameter(p)
                for n, p in signature.parameters.items()
                ]
        doc["parameters"] = parameters

    if isinstance(obj, property):
        if obj.fget is not None:
            _add_tags(doc, "get")
        if obj.fset is not None:
            _add_tags(doc, "set")
        if obj.fdel is not None:
            _add_tags(doc, "del")

    if is_value_type(obj):
        doc["value"] = repr(obj)

    return doc
 
       
done = set()

def _inspect(obj, module):
    if is_in_module(obj, module, True) or obj is module:
        doc_info("inspecting {}".format(obj))
        # FIXME: Completely bogus.
        if id(obj) in done:
            doc_warning("already processed {!r}".format(obj))
            return {}
        done.add(id(obj))
        return _inspect_obj(obj, module)
    else:
        doc = _inspect_ref(obj, module)
        _add_tags(doc, "imported")
        return doc


def inspect_module(modname):
    """
    Imports and inspects a module.

    @param modname
      The full name of the module to inspect.
    @return
      The module's docs.
    """
    try:
        module = importlib.import_module(str(modname))
        return _inspect(module, module)
    except Exception:
        logging.error(traceback.format_exc())
        raise


def _get_module_source(module):
    """
    Returns source lines of a module.

    @rtype
      sequence of `str`
    """
    # FIXME: Work around a bug in Python 3.4 that occurs whe importing
    # an empty module file.
    # source = inspect.getsourcelines(module)
    path = _get_module_path(module)
    with path.open() as file:
        return file.readlines()


def get_module_source(modname):
    return _get_module_source(importlib.import_module(str(modname)))


def inspect_modules(full_names):
    """
    Imports and inspects modules.

    @param full_names
      Iterable of importable full names of modules.
    @return
      JSO API documentation for the modules.
    """
    modules = ( importlib.import_module(str(n)) for n in full_names )
    modules = { m.__name__: _inspect(m, m) for m in modules }
    return dict(
        type        ="modules",
        modules     =modules,
        )


