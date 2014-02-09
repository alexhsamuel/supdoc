import logging
import pathlib

#-------------------------------------------------------------------------------

def resolve(path):
    """
    Resolves the existing part of a path.
    """
    if path.exists():
        return path.resolve()
    else:
        return resolve(path.parent) / path.name


class Path(pathlib.PosixPath):

    def __new__(class_, *args, **kw_args):
        if len(args) == 1 and len(kw_args) == 0 and isinstance(args[0], Path):
            return args[0]
        else:
            return resolve(pathlib.PosixPath.__new__(class_, *args, **kw_args))


    def with_suffix(self, suffix):
        """
        @todo
          This hopefully will not be needed when the base method is fixed.
        """
        if suffix is None:
            if self.suffix == "":
                return self
            else:
                return self.parent / self.name[: -len(self.suffix)]
        else:
            return super().with_suffix(suffix)


    def starts_with(self, prefix):
        return any( p == prefix for p in self.parents )



