"""
Tools for finding and importing modules.
"""

#-------------------------------------------------------------------------------

import functools
import importlib
from   importlib.machinery import SourceFileLoader
import inspect
import logging
import os
import sys
import types

from   .path import Path

#-------------------------------------------------------------------------------

@functools.total_ordering
class Name:
    """
    The fully-qualified name of a Python object.
    """

    def __init__(self, parts):
        if isinstance(parts, str):
            parts = tuple(parts.split("."))
        else:
            parts = tuple(parts)
        assert len(parts) > 0
        self.__parts = parts


    @classmethod
    def of(class_, obj):
        """
        The name of an arbitrary object.
        """
        if inspect.ismodule(obj):
            name = obj.__name__
        else:
            name = obj.__qualname__
        return class_(name)


    def __str__(self):
        return ".".join(self.__parts)


    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__, 
            ", ".join( repr(p) for p in self.__parts ))


    def __eq__(self, other):
        return str(self) == str(other)


    def __le__(self, other):
        return str(self) < str(other)


    def __hash__(self):
        return hash(self.__parts)


    def __len__(self):
        return len(self.__parts)


    def __iter__(self):
        return iter(self.__parts)


    def __getitem__(self, index):
        return self.__parts[index]


    @property
    def base(self):
        """
        The last part of the name.
        """
        return self.__parts[-1]


    @property
    def has_parent(self):
        """
        True if there is a parent name; false for a top-level name.
        """
        return len(self.__parts) > 1


    @property
    def parent(self):
        """
        The name of the parent component of the name.
        """
        if len(self.__parts) == 1:
            raise AttributeError("name '{}' has no parent".format(self))
        return self.__class__(self.__parts[: -1])


    def __add__(self, part):
        return self.__class__(self.__parts + tuple(part.split(".")))



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


def is_package(obj):
    return isinstance(obj, types.ModuleType) and obj.__name__ == obj.__package__


def is_package_dir(path):
    """
    Returns true if 'path' is a package directory.
    """
    path = Path(path)
    return path.is_dir() and (path / "__init__.py").exists()


def name_getter(base_path):
    base_path = Path.ensure(base_path)

    def get_name(path):
        path = Path.ensure(path)
        return Name(path.with_suffix(None).relative_to(base_path).parts)

    return get_name


def find_modules(path, base_path=None):
    """
    Generates full names of packages and modules under a top-level package.

    Includes standard Python module files and package directories only.
    A package name will be generated before its submodules.

    @param path
      Path to a module or a package directory, which is assumed to be at the
      top level.
    @param base_path
      The base path to import from (i.e. what would be in the PYTHONPATH).
      If None, uses the parent of 'path'.
    """
    path = Path.ensure(path)
    base_path = path.parent if base_path is None else Path.ensure(base_path)

    get_name = name_getter(base_path)
    def find(path):
        if path.suffix == ".py" and path.stem != "__init__":
            yield get_name(path)
        elif is_package_dir(path):
            yield get_name(path)
            for sub_path in path.iterdir():
                yield from find(sub_path)

    return find(path)
        

def find_all_modules(path):
    """
    Generates full names of all packages and modules in a directory.

    The directory is treated as the PYTHONPATH directory for imports.
    """
    base_path = Path.ensure(path)
    for path in base_path.iterdir():
        if path.suffix == ".py" or is_package_dir(path):
            yield from find_modules(path, base_path)


def find_std_modules():
    """
    Generates full names of Python standard library modules.
    """
    lib_dir = os.path.dirname(inspect.__file__)
    names = find_all_modules(lib_dir)
    # Leave out pesky test modules.
    names = ( n for n in names if "test" not in n )

    return names


def get_package_contents(package):
    """
    Returns the full names of modules contained directly in a package.
    """
    if not is_package(package):
        raise TypeError("not a package")

    fqname = Name(package.__name__)
    package_dir = Path(package.__file__).parent

    for sub_path in package_dir.iterdir():
        name = sub_path.stem
        if sub_path.suffix == ".py" and name != "__init__":
            yield name, load_module(fqname + name, sub_path)


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
    try:
        sys.path.remove(os.path.dirname(os.path.realpath(sys.argv[0])))
    except ValueError as exc:
        logging.info(exc)

    path = sys.argv[1]
    sys.path.insert(0, path)
    for full_name in find_all_modules(path):
        try:
            module = importlib.import_module(str(full_name))
        except Exception as exc:
            logging.error("can't import {}: {}".format(full_name, exc))
        else:
            print(module)


