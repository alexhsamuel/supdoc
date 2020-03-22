"""
Functions for working with objdoc and ref objects.
"""

#-------------------------------------------------------------------------------

from   contextlib import suppress

from   .path import Path

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

    For an objdoc, this is taken from its module and qualname, assuming they are
    present, except for a module, where its simply the name.  For a ref, it's
    parsed from the ref target.

    If `objdoc` doesn't have a module and qualname, returns `None`.

    @rtype
      `Path` or `None`.
    """
    assert objdoc is not None
    
    if is_ref(objdoc):
        return parse_ref(objdoc)
    elif objdoc.get("type_name") == "module":
        return Path(objdoc.get("name"), None)
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
    try:
        func = objdoc["func"]
    except KeyError:
        return (
            objdoc.get("callable") 
            and objdoc.get("type_name") not in (
                "type", 
            )
        ) 
    else:
        return is_function_like(func)


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



