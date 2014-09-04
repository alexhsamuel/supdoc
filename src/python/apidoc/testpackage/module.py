from   . import lib
from   .lib import LibClass, lib_function, LIB_CONSTANT
from   .lib import LibClass as RenamedLibClass
from   .lib import lib_function as renamed_lib_function
from   .lib import LIB_CONSTANT as RENAMED_LIB_CONSTANT


class BaseClass:
    """
    Base class for other useful classes.

    Throws some attributes and methods into the mix.  Most of them are really
    not so useful in the end.
    """

    def base_method(self):
        """
        Base method that returns `None`.
        """
        return None


    def _protected_base_method(self):
        """
        Protected base method that returns `None`.
        """
        return None


    def __private_base_method(self):
        """
        Private method that returns `None`.
        """
        return None



class Class(BaseClass, RenamedLibClass):
    """
    The main class of this module.

    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
    tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
    quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
    consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
    cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat
    non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

    Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium
    doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore
    veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim
    ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia
    consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Neque
    porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur,
    adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et
    dolore magnam aliquam quaerat voluptatem. Ut enim ad minima veniam, quis
    nostrum exercitationem ullam corporis suscipit laboriosam, nisi ut aliquid
    ex ea commodi consequatur? Quis autem vel eum iure reprehenderit qui in ea
    voluptate velit esse quam nihil molestiae consequatur, vel illum qui dolorem
    eum fugiat quo voluptas nulla pariatur?
    """

    A_CONSTANT = 2
    ANOTHER_CONSTANT = None
    A_THIRD_CONSTANT = "Hello, world."
    A_LONG_CONSTANT = [ i**2 for i in range(100) ]


    def __new__(class_, x, y):
        """
        Allocates an instance.

        Returns `None` instead if `x` < `y`.
        """
        if x < y:
            return None
        else:
            return super().__new__(x, y)


    def __init__(self, x, y):
        """
        Constructs an instance.

        @param x
          The initial x value.
        @param y
          The initial y value.
        """
        self.__x = x
        self.__y = y


    def __repr__(self):
        return "{}(x={!r}, y={!r})".format(
            self.__class__.__name__, self.__x, self.__y)


    def __str__(self):
        return "{{{}/{}}}".format(self.__x, self.__y)


    def __add__(self, other):
        return self.__class__(self.__x, self.__y + int(other))


    def __cmp__(self, other):
        return -1


    def __ne__(self, other):
        return True


    @property
    def y(self):
        """
        The value of y.
        """
        return self.__y


    def __get_x(self):
        return self.__x


    def __set_x(self, x):
        self.__x = x


    def __del_x(self):
        raise RuntimeError("stop doing that!")


    x = property(
        __get_x, __set_x, __del_x,
        """
        The value of x.

        The value should not be deleted!  Or bad things will happen.
        """)


    def normal_method(self, z):
        """
        Returns some stuff.

        This is a rather normal, prosaic instance method of the class.
        """
        return self.__x * z + self.__y


    @classmethod
    def class_method(class_, z):
        """
        Creates an instance.

        This is a typical use of a class method, to construct an instance oif
        the class in an alternate way.
        """ 
        return class_(z - 1, z)


    @staticmethod
    def static_method(z):
        """
        Does some useful helper stuff.

        This is a static method.  These are often used to attach helper
        functionality to a class.
        """
        return z * (z - 1)


    def _protected_method(self, u, v):
        """
        Protected method, for child class use only.

        Don't use use this method unless you are one of my children.  If you
        are not my child but you bother me anyway, I will get very upset.
        """
        return u - v


    def __private_method(self, x):
        """
        Private method, for internal use only.

        If you manage to find and then call this method, I will see to it that
        all hell breaks loose.
        """
        return x / (1 - x)


    class InnerClass:
        """
        A helper class defined inside `Class`.

        Here we put all sorts of stuff, collected together, that doesn't
        really belong in the outer class.
        """
        
        def __init__(self, a):
            """
            Initializes an instance.

            @param a
              What to initialize with.
            """
            self.__a = a


        def foo(self):
            """
            Does some stuff.

            This method is the one with everyone's favorite name.
            """
            # I lied.  Doesn't do any stuff.
            pass



