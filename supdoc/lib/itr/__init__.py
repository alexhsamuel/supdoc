"""
Tools for working with iterators.
"""

#-------------------------------------------------------------------------------

from   collections import deque

from   .recipes import *  # also imports * from itertools

#-------------------------------------------------------------------------------

def ntimes(value, times):
    """
    Generates `times` copies of `value`.
    """
    for _ in range(times):
        yield value


def first(iterable):
    """
    Generates `(first, item)` for each item in `iterable`, where `first` is 
    true for the first time and false for subsequent items.
    """
    i = iter(iterable)
    try:
        yield True, next(i)
        while True:
            yield False, next(i)
    except StopIteration:
        return


def last(iterable):
    """
    Generates `(last, item)` for each item in `iterable`, where `last` is 
    false except for the last item.
    """
    i = iter(iterable)
    item = next(i)
    while True:
        try:
            next_item = next(i)
        except StopIteration:
            yield True, item
            break
        else:
            yield False, item
            item = next_item


#-------------------------------------------------------------------------------

# FIXME: Elsewhere

def ensure_incl(obj):
    if obj is None:
        return (True, False)
    if obj in (True, False):
        return (obj, obj)
    begin, end = obj
    return bool(begin), bool(end)


def range(start, end, step=1, *, incl=None):
    """
    Generates values starting at `start` that are less than `end`, incrementing
    by `step` for each.
    """
    incl_start, incl_end = ensure_incl(incl)
    val = start
    if not incl_start:
        val += step
    while val < end or (incl_end and val == end):
        yield val
        val += step


#-------------------------------------------------------------------------------

class PeekIter:
    """
    Iterator wrapper that supports arbitrary push back and peek ahead.
    """

    def __init__(self, iterable):
        self.__iter = iter(iterable)
        self.__items = deque()


    def __iter__(self):
        # FIXME: Sloppy.
        return self


    def __next__(self):
        try:
            return self.__items.popleft()
        except IndexError:
            return next(self.__iter)


    @property
    def is_done(self):
        """
        True if the iterator is exhausted.
        """
        if len(self.__items) > 0:
            return False
        else:
            try:
                self.__items.append(next(self._iter))
            except StopIteration:
                return True
            else:
                return False


    def push(self, item):
        """
        Pushes an `item` to the front of the iterator so that it is next.
        """
        self.__items.appendleft(item)


    def peek(self, ahead=0):
        """
        Returns a future item from the iterator, without advancing.

        @param ahead
          The number of items to peek ahead; 0 for the next item.
        """
        while len(self.__items) <= ahead:
            self.__items.append(next(self.__iter))
        return self.__items[ahead]



