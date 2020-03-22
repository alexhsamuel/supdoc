"""
Infrastructure code.

This module contains infrastructure and utility code not directly related to
the application.  The contents should be considered candidates for contribution
to more general packages or libraries.
"""

#-------------------------------------------------------------------------------

from   collections import ChainMap, deque
import inspect
import logging
import sys

#-------------------------------------------------------------------------------

class Token:

    def __init__(self, name):
        self.__name = name


    def __str__(self):
        return self.__name


    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.__name)


    def __hash__(self):
        return hash(self.__name)


    def __eq__(self, other):
        return other is self


    def __ne__(self, other):
        return other is not self


    def __lt__(self, other):
        return NotImplemented


    __gt__ = __le__ = __ge__ = __lt__


        
UNDEFINED = Token("UNDEFINED")

def log_call(log=logging.debug):
    frame = inspect.stack()[1][0]
    try:
        arg_info = inspect.getargvalues(frame)
        args = [ 
            "{}={!r}".format(n, arg_info.locals.get(n, UNDEFINED)) 
            for n in arg_info.args 
            ]
        if arg_info.varargs is not None:
            args.append("*{!r}".format(arg_info.varargs))
        if arg_info.keywords is not None:
            args.append("**{!r}".format(arg_info.keywords))
        fn_name = inspect.getframeinfo(frame).function
        log("{}({})".format(fn_name, ", ".join(args)))
    finally:
        del frame


def format_ctor(obj, *args, **kw_args):
    name = obj.__class__.__name__
    args = [ repr(a) for a in args ]
    args.extend( n + "=" + repr(v) for n, v in kw_args.items() )
    return "{}({})".format(name, ", ".join(args))


class BaseStruct:

    def __init__(self, **kw_args):
        for name in self.__slots__:
            super(BaseStruct, self).__setattr__(name, kw_args.pop(name, None))
        if len(kw_args) > 0:
            raise AttributeError("no attributes {}".format(", ".join(kw_args)))
        

    def __repr__(self):
        return format_ctor(
            self, **{ n: getattr(self, n) for n in self.__slots__ })


    def __setattr__(self, name, value):
        raise RuntimeError("read-only struct")


    def copy(self, **kw_args):
        for name in self.__slots__:
            kw_args.setdefault(name, getattr(self, name))
        return self.__class__(**kw_args)



def Struct(*names, name="Struct"):
    names = tuple( str(n) for n in names )
    return type(name, (BaseStruct, ), {"__slots__": names})


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
        except (ImportError, ValueError):
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

    raise NameError(name)
    

#-------------------------------------------------------------------------------

def tupleize(obj):
    if isinstance(obj, str):
        return (obj, )
    else:
        try:
            return tuple(obj)
        except:
            return (obj, )


class QIter:
    """
    Iterator wrapper that supports arbitrary push back and peek ahead.
    """

    def __init__(self, iterable):
        self.__iter = iter(iterable)
        self.__items = deque()


    def __iter__(self):
        # FIXME: Sloppy.
        return self


    def __next__(self):
        try:
            return self.__items.popleft()
        except IndexError:
            return next(self.__iter)


    @property
    def is_done(self):
        """
        True if the iterator is exhausted.
        """
        if len(self.__items) > 0:
            return False
        else:
            try:
                self.__items.append(next(self._iter))
            except StopIteration:
                return True
            else:
                return False


    def push(self, item):
        """
        Pushes an `item` to the front of the iterator so that it is next.
        """
        self.__items.appendleft(item)


    def peek(self, ahead=0):
        """
        Returns a future item from the iterator, without advancing.

        @param ahead
          The number of items to peek ahead; 0 for the next item.
        """
        while len(self.__items) <= ahead:
            self.__items.append(next(self.__iter))
        return self.__items[ahead]



