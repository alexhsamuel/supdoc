"""
Caching for objdoc data.
"""

from   __future__ import annotations

from   contextlib import suppress
from   importlib.machinery import ModuleSpec
import importlib.util
import gzip
import json
import logging
import os
from   pathlib import Path
import sys

from   .inspector import VERSION, Inspector
from   .lib import memo
from   .modules import find_submodules
from   .objdoc import Objdoc

#-------------------------------------------------------------------------------

class CannotCache(RuntimeError):
    """
    A cache is not able to cache a particular item.
    """


def _get_check(spec: ModuleSpec) -> dict:
    # For now, we only know how to handle module files.
    if spec.origin is None:
        # Doesn't appear to be a module file. 
        raise CannotCache(f"not a module file: {spec.name}")

    # Get the mtime and size of the module file, if any.  This is to detect
    # changes to the file.
    stat = os.stat(spec.origin)
    return {
        "version"   : VERSION,
        "path"      : spec.origin,
        "mtime"     : stat.st_mtime,
        "size"      : stat.st_size,
    }


def _compare_check(spec: ModuleSpec, check: dict) -> bool:
    if check["version"] != VERSION:
        return False
    if spec.origin is None:
        # Doesn't appear to be a module file.
        return False
    if check["path"] != spec.origin:
        return False

    # Check against the mtime and size of the module file.
    stat = os.stat(spec.origin)
    return (
            check["mtime"] == stat.st_mtime
        and check["size"] == stat.st_size
    )


class Cache:

    def __init__(self, get_path):
        self.__get_path = get_path


    def __setitem__(self, modname: str, objdoc: Objdoc):
        """
        Attempts to cache `objdoc` for module `modname`.

        :raie CannontCache:
          A cache cannot be written for the module.
        """
        spec = importlib.util.find_spec(modname)
        if spec.origin is None:
            raise CannotCache(f"not a module file; can't cache: {modname}")

        path = self.__get_path(spec)
        path = path.parent / (path.name + ".json.gz")
        check = _get_check(spec)

        try:
            file = gzip.open(path, "wt", encoding="utf-8")
        except OSError:
            raise CannotCache(f"can't write cache: {modname}")
        with file:
            json.dump({"check": check, "objdoc": objdoc}, file)
        print("TO CACHE:", path)


    def __getitem__(self, modname: str) -> Objdoc:
        spec = importlib.util.find_spec(modname)
        if spec.origin is None:
            return False

        try:
            path = self.__get_path(spec)
        except CannotCache:
            raise KeyError(modname)
        path = path.parent / (path.name + ".json.gz")

        try:
            file = gzip.open(path, "rt", encoding="utf-8")
        except FileNotFoundError:
            raise KeyError(modname)
        except OSError as exc:
            logging.debug(f"can't read objdoc cache: {exc}")
            raise KeyError(modname)
        with file:
            cache = json.load(file)

        _compare_check(spec, cache["check"])

        return cache["objdoc"]



# FIXME: Elsewhere.
def is_subpath(path: Path, other: Path):
    """
    True if `path` is a subpath of `other`.
    """
    try:
        Path(path).relative_to(other)
    except ValueError:
        return False
    else:
        return True


def _get_pycache_path(spec: ModuleSpec) -> Path:
    """
    Returns the path to the objdoc cache for a module.
    """
    # Refuse to do __pycache__ caching for anything in PREFIX.
    # FIXME: Not sure if this is the right policy.
    if is_subpath(spec.origin, sys.prefix):
        raise CannotCache(spec.name)

    # Find out where the module cache file goes.
    mod_cache_path = importlib.util.cache_from_source(spec.origin)
    # Put the odoc cache next to it.
    *_, name = spec.name.rsplit(".", 1)
    return Path(mod_cache_path).parent / (name + ".supdoc")



PYCACHE = Cache(_get_pycache_path)

#-------------------------------------------------------------------------------

# FIXME: Elsewhere.

@memo.memoize
def get_cache_dir() -> Path:
    """
    Returns the path to the supdoc cache directory.
    """
    try:
        cache_dir = Path(os.environ["SUPDOC_CACHE_DIR"])
    except KeyError:
        try:
            cache_dir = Path(os.environ["XDG_CACHE_DIR"])
        except KeyError:
            if sys.platform == "linux":
                cache_dir = Path.home() / ".cache"
            elif sys.platform == "darwin":
                cache_dir = Path.home() / "Library/Caches"
        cache_dir /= "supdoc"

    # Make sure the directory exists.  Use restrictive permissions for our cache
    # directory, but default permissions for the parents.
    os.makedirs(cache_dir.parent, exist_ok=True)
    with suppress(FileExistsError):
        os.mkdir(cache_dir, mode=0o700)

    return cache_dir


def DirCache(dir: Path) -> Cache:
    """
    Returns a cache that stores files in a separate directory.
    """
    dir = Path(dir)
    return Cache(lambda spec: dir / spec.name)


#-------------------------------------------------------------------------------

class CachingInspector:
    """
    An inspector with caching.
    """
    
    def __init__(self, inspector, caches):
        self.__inspector = inspector
        self.__caches = tuple(caches)


    def inspect_module(self, modname: str) -> Objdoc:
        # Try to use a cached value.
        for cache in self.__caches:
            try:
                return cache[modname]
            except KeyError:
                continue

        # No cached value.  Inspect it.
        objdoc = self.__inspector.inspect_module(modname)

        # Write back to caches.
        for cache in self.__caches:
            try:
                cache[modname] = objdoc
            except Exception:
                # Try the next cache.
                continue
            else:
                break

        return objdoc



#-------------------------------------------------------------------------------

@memo.memoize
def get_inspector():
    # Try the __pycache__ dir first, then fall back to a global cache for
    # packages installed in $PREFIX.
    caches = [PYCACHE, DirCache(get_cache_dir())]
    return CachingInspector(Inspector(), caches,)


def cache_modules(*modnames) -> None:
    """
    Caches modules in `modnames` and their submodules.
    """
    inspector = Inspector()
    modnames = { n for m in modnames for n in find_submodules(m) }

    for modname in modnames:
        logging.debug(f"inspecting: {modname}")
        objdoc = inspector.inspect_module(modname)
        logging.debug(f"writing cache: {modname}")
        try:
            PYCACHE[modname] = objdoc
        except CannotCache as exc:
            logging.warning(f"cannot cache: {exc}")


def main():
    import argparse

    # logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "modnames", metavar="MODNAME", nargs="*",
        help="names of modules or packages to cache")
    args = parser.parse_args()

    cache_modules(*args.modnames)


if __name__ == "__main__":
    main()

