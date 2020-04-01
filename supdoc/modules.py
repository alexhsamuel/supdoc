"""
Tools for finding and importing modules.
"""

#-------------------------------------------------------------------------------

import inspect
import os
import pkgutil
import sys
import types

from   .lib.path import Path
from   .path import import_

#-------------------------------------------------------------------------------

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

    :param path:
      Path to a module or a package directory, which is assumed to be at the
      top level.
    :param base_path:
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


# FIXME: This is bogus and should be removed.
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


def find_submodules(modname):
    """
    Generate names of submodules, including subpackages, of module `modname`.
    """
    mod = import_(modname)
    # Not sure if this is right.
    path = os.path.dirname(mod.__spec__.origin)

    yield mod.__name__
    for modinfo in pkgutil.walk_packages([path], mod.__name__ + "."):
        yield(modinfo.name)


