from   collections import ChainMap

#-------------------------------------------------------------------------------

class Context:

    def __init__(self, **kw_args):
        self.__dict__.update(kw_args)


    def __call__(self, **kw_args):
        unknown = [ n for n in kw_args if n not in self.__dict__ ]
        if len(unknown) > 0:
            raise AttributeError(
                "unknown attributes: {}".format(", ".join(unknown)))
        return self.__class__(**ChainMap(kw_args, self.__dict__))



