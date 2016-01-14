"""
Functions for working with objdoc and ref objects.
"""

#-------------------------------------------------------------------------------

from   contextlib import suppress
import collections
from   inspect import Signature, Parameter
import types

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
      The qualname, or `None` for the module itself.
    """

    def __new__(class_, modname, qualname):
        if modname in ("", None):
            raise ValueError("modname may not be empty")
        if qualname == "":
            raise ValueError("qualname may not be empty")
        return super().__new__(class_, modname, qualname)


    @classmethod
    def of(class_, obj):
        """
        Returns the path reported by an object.

        @return
          The `Path` to `obj`, or `None` if none is reported.
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

    @rtype
      `Path`.
    """
    if is_ref(objdoc):
        return parse_ref(objdoc)
    else:
        # FIXME: Should we store and use the name path, in place of qualname?
        modname = get_path(objdoc.get("module")).modname
        return Path(modname, objdoc.get("qualname"))


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


