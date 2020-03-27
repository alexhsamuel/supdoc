"""
Memoizers.
"""

#-------------------------------------------------------------------------------

import functools

__all__ = [
    "memoize",
    "memoize_method",
    "memoize_with",
]

#-------------------------------------------------------------------------------

def memoize_with(memo):
    def memoize(fn):
        @functools.wraps(fn)
        def memoized(*args, **kw_args):
            # FIXME: It would be better to bind to the signature first, to pick
            # up default arguments.
            key = args + tuple(sorted(kw_args.items()))
            try:
                return memo[key]
            except KeyError:
                value = memo[key] = fn(*args, **kw_args)
                return value

        memoized.__memo__ = memo
        return memoized

    return memoize


def memoize(fn):
    """
    Memoizes with a new empty `dict`.
    """
    return memoize_with({})(fn)


def memoize_method(fn):
    """
    Memoizes an ordinary method.

    Uses a memo dictionary attached as an attribute to each instance of the
    containing class.  The attribute name is stored in `__memo_name__` on the
    method function.

    ```py
    class C:

        @memoize_method
        def expensive(self, arg):
            # ...
            return result

    ```
    """
    name = "__" + fn.__name__
    @functools.wraps(fn)
    def memoized(self, *args, **kw_args):
        # FIXME: Bind to signature first.
        key = args + tuple(sorted(kw_args.items()))
        memo = self.__dict__.setdefault(name, {})
        try:
            return memo[key]
        except KeyError:
            value = memo[key] = fn(self, *args, **kw_args)
            return value

    memoized.__memo_name__ = name
    return memoized



