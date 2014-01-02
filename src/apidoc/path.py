import pathlib

#-------------------------------------------------------------------------------

class Path(pathlib.PosixPath):

    def __new__(class_, *args, **kw_args):
        if len(args) == 1 and len(kw_args) == 0 and isinstance(args[0], Path):
            return args[0]
        else:
            return pathlib.PosixPath.__new__(class_, *args, **kw_args).resolve()


    def starts_with(self, prefix):
        return any( p == prefix for p in self.parents )



