import importlib
from   importlib.machinery import SourceFileLoader
import logging
import os
import sys

from   apidoc.path import Path

#-------------------------------------------------------------------------------

class Name:
    """
    The fully-qualified name of a Python object.
    """

    def __init__(self, parts):
        if isinstance(parts, str):
            parts = parts.split(".")
        else:
            parts = tuple(parts)
        assert len(parts) > 0
        self.__parts = parts


    def __str__(self):
        return ".".join(self.__parts)


    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__, 
            ", ".join( repr(p) for p in self.__parts ))


    def __len__(self):
        return len(self.__parts)


    def __iter__(self):
        return iter(self.__parts)


    def __getitem__(self, index):
        return self.__parts[index]


    @property
    def parent(self):
        if len(self.__parts) == 1:
            raise AttributeError("name '{}' has no parent".format(self))
        return self.__class__(self.__parts[: -1])


    def __plus__(self, part):
        return self.__class__(self.__parts + (parts, ))



def get_module_name_from_path(path, base_path):
    """
    Constructs the name of a module from its path relative to the import path.
    """
    path = Path(path)
    base_path = Path(base_path)
    parts = path.with_suffix("").relative_to(base_path).parts
    return Name(parts)
    

# FIXME: Don't rely on the module in the path.
def import_module_from_filename(path):
    path = Path(path)
    if path.is_dir():
        # FIXME: Is this general?  Is this right?
        path = path / "__init__.py"

    for load_path in sys.path:
        try:
            relative = path.with_suffix("").relative_to(load_path)
        except ValueError:
            pass
        else:
            name = Name(relative.parts)
            module = importlib.import_module(str(name))
            if Path(module.__file__) == path:
                return name, module
            else:
                logging.warning(
                    "module {} imports from {}, not expected {}".format(
                        name, module.__file__, path))
    raise RuntimeError("{} is not in the Python path".format(path))


def is_package_dir(path):
    """
    Returns true if 'path' is a package directory.
    """
    path = Path(path)
    return path.is_dir() and (path / "__init__.py").exists()


def enumerate_package(path):
    """
    Generates subpackages and modules under a top-level package.
    """
    path = Path(path)
    if not is_package_dir(path):
        raise ValueError("{} is not a package dir".format(path))

    # The import base is the parent of the top-level package.
    base_path = path.parent

    def enumerate(path):
        yield get_module_name_from_path(path, base_path), path / "__init__.py"
        for sub_path in path.iterdir():
            if sub_path.suffix == ".py" and sub_path.stem != "__init__":
                yield get_module_name_from_path(sub_path, base_path), sub_path
            elif is_package_dir(sub_path):
                yield from enumerate(sub_path)
    
    yield from enumerate(path)


def load_module(name, path):
    logging.info("loading {} from {}".format(name, path))
    module = SourceFileLoader(str(name), str(path)).load_module()
    if len(name) > 1:
        parent_name = Name(name[: -1])
        parent = sys.modules[str(parent_name)]
        setattr(parent, name[-1], module)
    return module


#-------------------------------------------------------------------------------

if __name__ == "__main__":
    # Remove this module's directory from the load path.
    sys.path.remove(os.path.dirname(os.path.realpath(sys.argv[0])))

    pkg = Path(sys.argv[1])
    top = pkg.parent

    for name, path in enumerate_package(pkg):
        print("{!s:24} -> {}".format(name, path))

        module = SourceFileLoader(str(name), str(path)).load_module()
        print(module)


