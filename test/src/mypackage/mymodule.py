"""
The main module.

This is where all the fun happens.
"""

#-------------------------------------------------------------------------------

import collections
import logging
import sys

# FIXME: This doesn't work.
# print(sys.path)
# print(__file__)
# print(__loader__)
# from   . import support
from  mypackage import support

#-------------------------------------------------------------------------------

def foo(x, y="0"):
    x = int(x)
    y = int(y)
    logging.debug("invoking foo({}, {})".format(x, y))
    return support.foo(x, y)


#-------------------------------------------------------------------------------

class Master:
    """
    The master class.
    """
    
    __total_value = 0

    def __init__(self, value):
        self.__value = value
        Master.__total_value += value


    @property
    def value(self):
        """
        The value.
        """
        return self.__value


    @staticmethod
    def get_total_value():
        return Master.__total_value


    @classmethod
    def build(class_, x, y):
        return class_(foo(x, y))



class Child(Master):

    class Inner(collections.namedtuple("Inner", ("foo", "bar", "baz"))):

        pass



    def __init__(self):
        super(Child, self).__init__(42)
        self.__tally = self.get_total_value()
        self.__stuff = Child(10, 20, 30)


    def __get_tally(self):
        """
        Tally-Ho!
        """
        return self.__tally


    def __set_tally(self, tally):
        self.__tally = tally


    tally = property(__get_tally, __set_tally)


    
