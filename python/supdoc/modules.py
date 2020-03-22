"""
Tools for finding and importing modules.
"""

#-------------------------------------------------------------------------------

import importlib
from   importlib.machinery import SourceFileLoader
import inspect
import logging
import os
import sys
import types

from   .path import Path

#-------------------------------------------------------------------------------

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

    def get_name(path):
        return ".".join(path.with_suffix(None).relative_to(base_path).parts)

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


def find_modules_in_path():
    """
    Generates names of modules in the import path.
    """
    for path in sys.path:
        if path == "":
            path = os.getcwd()
        # FIXME: Normalize path.
        if path.startswith(sys.prefix):
            continue
        try:
            yield from find_all_modules(path)
        except IOError:
            pass


def load_module(name, path):
    logging.info("loading {} from {}".format(name, path))
    module = SourceFileLoader(str(name), str(path)).load_module()
    if len(name) > 1:
        parent_name = Name(name[: -1])
        parent = sys.modules[str(parent_name)]
        setattr(parent, name[-1], module)
    return module


