from   collections import ChainMap

#-------------------------------------------------------------------------------

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


