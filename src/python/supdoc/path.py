"""
Logic for manipulating fully-qualified lookup paths to Python objects.
"""

#-------------------------------------------------------------------------------

import collections
import types
import sys

import pln.py

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


    def __repr__(self):
        return pln.py.format_ctor(self, self.modname, self.qualname)


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

def import_(modname):
    """
    Imports a module.

    @param modname
      The fully-qualified module name.
    @rtype
      module
    @raise ImportError
      The name could not be imported.
    """
    __import__(modname)
    return sys.modules[modname]


def getattr_qualname(name, obj):
    """
    Looks up a qualified name in (nested) attributes of `obj`.

    Splits qualified `name` at dots, and successively looks up parts as 
    attributes in `obj`.
    """
    result = obj
    for part in name.split("."):
        result = getattr(result, part)
    return result


def get_obj(path):
    """
    Returns the object specified by `path`.

    Imports the modname of `path`, if necessary.

    @raise ImportError
      The specified module could not be imported.
    @raise AttributeError
      The specified qualname could not be found.
    """
    module = import_(path.modname)
    if path.qualname is None:
        return module
    else:
        return getattr_qualname(path.qualname, module)


def is_obj(path):
    try:
        get_obj(path)
    except (ImportError, AttributeError):
        return False
    else:
        return True


def get_legit_path(obj):
    """
    Returns the `Path` reported by `obj`, if the path resolved to `obj`; `None`
    otherwise.
    """
    path = Path.of(obj)
    if path is None:
        return None
    else:
        # Got a path; now resolve it.
        try:
            target = get_obj(path)
        except (ImportError, AttributeError):
            # Can't resolve the path at all.
            return None
        else:
            # Check if the path resolved to something else.
            return path if target is obj else None


def split(name):
    """
    Interprets `name` as a path.

    Attempts to split fully-qualified `name` into modname and qualname.  The
    name consists of full module name and optionally an object's qualname in
    that module.  This method attempts to split it by importing a prefix `name`
    as a module and then resolving the rest in that module.  It starts with the
    longest possible prefix and continues right-to-left.

    If this does not succeed, also attempts resolving `name` in the `builtins`
    module.

    For example, the name `"html.parser.HTMLParser.close"` is resolved
    as follows:

    1. Attempt to import `"html.parser.HTMLParser.close"`.  This fails.

    2. Attempt to import `"html.parser.HTMLParser"`.  This fails.

    3. Attempt to import `"html.parser"`.  This succeeds.  In the resulting
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

        path = Path(modname, qualname)
        try:
            obj = get_obj(path)
        except:
            raise NameError("can't find {} in {}".format(qualname, modname))

    else:
        parts = name.split(".")
        # Try successively shorter prefixes as the modname.
        for i in range(len(parts), 0, -1):
            path = Path(
                ".".join(parts[: i]), 
                None if i == len(parts) else ".".join(parts[i :]))
            try:
                obj = get_obj(path)
            except (ImportError, AttributeError):
                continue
            else:
                break
        else:
            # Also try in builtins.
            try:
                obj = getattr_qualname(name, builtins)
            except:
                raise NameError("can't find {}".format(name))
            else:
                path = Path("builtins", name)

    return path, obj


