from   contextlib import closing
import json

#-------------------------------------------------------------------------------

def func(x, y, z=10, *, w=None, **kw_args):
    """
    func().
    """
    return x + y + z + sum(args)


#-------------------------------------------------------------------------------

class C:
    "This is class C."

    def __init__(self, x, y=10):
        "This is C.__init__()."
        self.__x = x


    def method(self):
        "This is C.method()."
        pass


    @classmethod
    def classmethod(class_):
        "This is C.classmethod()."
        pass


    @staticmethod
    def staticmethod():
        "This is C.staticmethod()."
        pass


    def __private_method(self):
        "This is C.__private_method()."
        pass


    def __get_x(self):
        "This is the property C.x."
        return self.__x


    def __set_x(self, x):
        self.__x = x


    def __del_x(self):
        self.__x = None


    x = property(__get_x, __set_x)

    C_CLASS_ATTR = 42


    class Subclass:
        "This is class C.Subclass."

        def __init__(self):
            "This is C.Subclass.__init__()."
            pass


        C_SUBCLASS_ATTR = "Hello, world."



