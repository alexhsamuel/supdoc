import inspect
import shutil
import sys
import types

# FIXME: __all__

#-------------------------------------------------------------------------------

# Inject some missing internal types into the 'types' module.
types.MethodWrapperType = type("".__eq__)

METHOD_TYPES = (
    types.MethodType, 
    types.MethodWrapperType, 
    types.BuiltinMethodType,
)

#-------------------------------------------------------------------------------
# Tokens

DEFAULT = object()
NO_DEFAULT = object()

#-------------------------------------------------------------------------------

def idem(obj):
    """
    Returns its argument.
    """
    return obj


def if_none(obj, default):
    """
    Returns `obj`, unless it's `None`, in which case returns `default`.

      >>> if_none(42, "Hello!")
      42
      >>> if_none(None, "Hello!")
      'Hello'

    """
    return default if obj is None else obj


def is_seq(obj):
    """
    Returns true if `obj` is a non-string sequence.
    """
    try:
        len(obj)
    except (TypeError, ValueError):
        return False
    else:
        return not isinstance(obj, str)


def iterize(obj):
    """
    Converts into or wraps in an iterator.

    If `obj` is an iterable object other than a `str`, returns an iterator.
    Otherwise, returns a one-element iterable of `obj`.

      >>> list(iterize((1, 2, 3)))
      [1, 2, 3]

      >>> list(iterize("Hello!"))
      ['Hello!']
      >>> list(iterize(42))
      [42]

    """
    if isinstance(obj, str):
        return iter((obj, ))
    else:
        try:
            return iter(obj)
        except TypeError:
            return iter((obj, ))


def tupleize(obj):
    """
    Converts into or wraps in a tuple.

    If `obj` is an iterable object other than a `str`, converts it to a `tuple`.

      >>> tupleize((1, 2, 3))
      (1, 2, 3)
      >>> tupleize([1, 2, 3])
      (1, 2, 3)
      >>> tupleize(range(1, 4))
      (1, 2, 3)

    Otherwise, wraps `obj` in a one-element `tuple`.

      >>> tupleize(42)
      (42,)
      >>> tupleize(None)
      (None,)
      >>> tupleize("Hello, world!")
      ('Hello, world!',)

    @type obj
      Any.
    @rtype
      `tuple`.
    """
    if isinstance(obj, str):
        return (obj, )
    else:
        try:
            return tuple(obj)
        except:
            return (obj, )


def format_call(__fn, *args, **kw_args):
    """
    Formats a function call, with arguments, as a string.

      >>> format_call(open, "data.csv", mode="r")
      "open('data.csv', mode='r')"

    @param __fn
      The function to call, or its name.
    @rtype
       `str`
    """
    try:
        name = __fn.__name__
    except AttributeError:
        name = str(__fn)
    args = [ repr(a) for a in args ]
    args.extend( n + "=" + repr(v) for n, v in kw_args.items() )
    return "{}({})".format(name, ", ".join(args))


def format_ctor(obj, *args, **kw_args):
    return format_call(obj.__class__, *args, **kw_args)


def look_up(name, obj):
    """
    Looks up a qualified name.
    """
    result = obj
    for part in name.split("."):
        result = getattr(result, part)
    return result


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


def import_look_up(name):
    """
    Looks up a fully qualified name, importing modules as needed.

    @param name
      A fully-qualified name.
    @raise NameError
      The name could not be found.
    """
    # Split the name into parts.
    parts = name.split(".")
    # Try to import as much of the name as possible.
    # FIXME: Import left to right as much as possible.
    for i in range(len(parts) + 1, 0, -1):
        module_name = ".".join(parts[: i])
        try:
            obj = import_(module_name)
        except ImportError:
            pass
        else:
            # Imported some.  Resolve the rest with getattr.
            for j in range(i, len(parts)):
                try:
                    obj = getattr(obj, parts[j])
                except AttributeError:
                    raise NameError(name) from None
            else:
                # Found all parts.
                return obj
    else:
        raise NameError(name)
    

def export(obj):
    """
    Marks a top-level object in a module for export.

    This decorator adds the name of `obj` to global `__all__`.  If `__all__`
    doesn't exist in the module namespace, it is initialized to an empty list.

    Use like this::

      @export
      def foo(a, b):
          return 2 * a + b

    @param obj
      The object to add.  It should be a top-level object with a qualname
      that does not contain any dots.
    @return
      `obj`.
    @note
      This decorator does not work on names for values, such as strings,
      as those do not have a `__qualname__`.
    """
    try:
        name = obj.__qualname__
    except AttributeError:
        raise TypeError("obj must have a __qualname__")
    # Make sure the object's name is unqualified.
    if "." in name:
        raise TypeError("obj must have a simple __qualname__")

    # Get the caller's globals.
    glbls = inspect.stack()[1][0].f_globals
    # Get or add an __all__ list.
    all_names = glbls.setdefault("__all__", [])
    # Add the name.
    all_names.append(name)

    return obj
    

# FIXME: This doesn't work for values.  Add one that takes a name, or something.

#-------------------------------------------------------------------------------

def dump_attrs(obj):
    width = shutil.get_terminal_size().columns
    for name in sorted(dir(obj)):
        attr = getattr(obj, name)
        if not isinstance(attr, METHOD_TYPES):
            is_getset = isinstance(
                getattr(type(obj), name, None), types.GetSetDescriptorType)
            line = "{:24s} {} {}".format(
                name, "\u2192" if is_getset else "=", repr(repr(attr))[1 : -1])
            if len(line) > width:
                line = line[: width - 1] + "\u2026"
            print(line)


def dump_methods(obj):
    width = shutil.get_terminal_size().columns
    for name in sorted(dir(obj)):
        attr = getattr(obj, name)
        if isinstance(attr, types.MethodType):
            line = attr.__name__ + str(inspect.signature(attr)) 
            if len(line) > width:
                line = line[: width - 1] + "\u2026"
            print(line)
    

