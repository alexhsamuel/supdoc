"""
Functions for working with objdoc and ref objects.
"""

#-------------------------------------------------------------------------------

from   contextlib import suppress
from   inspect import Signature, Parameter

from   .path import *

#-------------------------------------------------------------------------------

def is_ref(obj):
    """
    Returns true if `obj` is a ref.
    """
    return "$ref" in obj


def make_ref(path):
    """
    Builds a ref for `path`.

    @type path
      `Path`.
    """
    ref = "#/modules/" + path.modname
    if path.qualname is not None:
        ref += "/dict/" + "/dict/".join(path.qualname.split("."))
    return {"$ref": ref}


def parse_ref(ref):
    """
    Parses a ref.

    @see
      `make_ref()`.
    @rtype
      `Path`.
    """
    part0, part1, modname, *parts = ref["$ref"].split("/")
    assert part0 == "#",        "ref must be absolute in current doc"
    assert part1 == "modules",  "ref must start with module"
    assert all( n == "dict" for n in parts[:: 2] )
    qualname = None if len(parts) == 0 else ".".join(parts[1 :: 2])
    return Path(modname, qualname)


def get_path(objdoc):
    """
    Returns the path for an objdoc or ref.

    For an objdoc, this is taken from its modname and qualname, assuming they
    are present.  For a ref, it's parsed from the ref target.

    If `objdoc` doesn't have a module and qualname, returns `None`.

    @rtype
      `Path` or `None`.
    """
    assert objdoc is not None
    
    if is_ref(objdoc):
        return parse_ref(objdoc)
    else:
        # FIXME: Should we store and use the name path, in place of qualname?
        module      = objdoc.get("module")
        qualname    = objdoc.get("qualname")
        if module is None or qualname is None:
            return None
        else:
            return Path(get_path(module).modname, qualname)


def is_callable(objdoc):
    """
    Returns true if the object is callable or wraps a callable.
    """
    return objdoc.get("callable") or objdoc.get("func", {}).get("callable")


def is_function_like(objdoc):
    """
    Returns true if `objdoc` is for a function or similar object.
    """
    return (
        objdoc.get("callable") 
        and objdoc.get("type_name") not in (
            "type", 
        )
    )


def get_signature(objdoc):
    """
    Returns the signature of a callable object or the wrapped callable.

    @return
      The signature, or `None` if none is available, for example for a built-in
      or extension function or method.
    """
    with suppress(KeyError):
        return objdoc["signature"]
    with suppress(KeyError):
        return objdoc["func"]["signature"]


# FIXME: Hack.
class ReprObj:

    def __init__(self, repr):
        self.__repr = repr


    def __repr__(self):
        return self.__repr



def parameter_from_jso(jso, docsrc):
    """
    Reconstitutes a parameter from an objdoc parameter JSO.

    @rtype
      `Parameter`.
    """
    name = jso["name"]
    kind = getattr(Parameter, jso["kind"])
    try:
        default = jso["default"]
    except KeyError:
        default = Parameter.empty
    else:
        default = docsrc.resolve(default)
        # FIXME
        default = ReprObj(default.get("repr", "???"))
    try:
        annotation = jso["annotation"]
    except KeyError:
        annotation = Parameter.empty
    else:
        # FIXME
        annotation = annotation["repr"]
    return Parameter(name, kind, default=default, annotation=annotation)


def signature_from_jso(jso, docsrc):
    """
    Reconstitutes a signature from an object signature JSO.

    @rtype
      `Signature`
    """
    # FIXME: Add the return annotation.
    parameters = [
        parameter_from_jso(o, docsrc)
        for o in jso.get("params", [])
    ]
    return Signature(parameters)


