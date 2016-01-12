"""
Functions for working with objdoc and ref objects.
"""

#-------------------------------------------------------------------------------

from   contextlib import suppress

from   .inspector import Path

#-------------------------------------------------------------------------------

def is_ref(obj):
    """
    Returns true if `obj` is a ref.
    """
    return "$ref" in obj


def parse_ref(ref):
    """
    Parses a ref.

    @return
      The fully-qualified module name and the name path.
    """
    parts = ref["$ref"].split("/")
    assert parts[0] == "#",         "ref must be absolute in current doc"
    assert len(parts) >= 3,         "ref must include module"
    assert parts[1] == "modules",   "ref must start with module"
    modname, name_path = parts[2], ".".join(parts[3 :])
    return modname, name_path


def get_path(objdoc):
    """
    Returns the path for an objdoc or ref.

    For an objdoc, this is taken from its modname and qualname, assuming they
    are present.  For a ref, it's parsed from the ref target.

    @rtype
      `Path`.
    """
    if is_ref(objdoc):
        modname, name_path = parse_ref(objdoc)
        if len(name_path) > 0:
            parts = name_path.split(".")
            assert all( n == "dict" for n in parts[:: 2] )
            qualname = ".".join(parts[1 :: 2])
        else:
            qualname = None
    else:
        modname = objdoc.get("modname")
        # FIXME: Should we store and use the name path, in place of qualname?
        qualname = objdoc.get("qualname")
    return Path(modname, qualname)


def look_up_ref(sdoc, ref):
    """
    Resolves a reference in its sdoc.
    """
    parts = ref["$ref"].split("/")
    assert parts[0] == "#", "ref must be absolute in current doc"
    jso = sdoc
    for part in parts[1 :]:
        try:
            jso = jso[part]
        except KeyError:
            raise LookupError("no {} in {}".format(part, "/".join(parts))) \
                from None
    return docs


def resolve_ref(sdoc, objdoc):
    """
    If `objdoc` is a reference, resolves it.
    """
    try:
        objdoc["$ref"]
    except KeyError:
        return objdoc
    else:
        return look_up_ref(sdoc, objdoc)


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


