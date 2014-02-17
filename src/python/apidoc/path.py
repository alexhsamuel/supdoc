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
    """
    Customization of 'pathlib.PosixPath'.

      - The path is resolved to an absolute path at construction.
      - Adds convenience methods.

    """

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


    # FIXME: Rename to 'has_parent'.
    def starts_with(self, prefix):
        """
        True if 'prefix' a parent of this path.

          >>> prefix = Path('/foo/bar')
          >>> Path('/foo/bar/baz/bif').starts_with(prefix)
          True
          >>> Path('/foo/bar').starts_with(prefix)
          True
          >>> Path('/foo/baz/bif').starts_with(prefix)
          False
          >>> Path('/foo/barbaz/bif').starts_with(prefix)
          False

        """
        return any( p == prefix for p in self.parents )



