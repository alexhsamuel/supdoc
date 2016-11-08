from   contextlib import closing
import json
import math
import typing

#-------------------------------------------------------------------------------

def toplevel_function(x, y, z=10, *, w=None, **kw_args):
    """
    Computes a _very_ important quantity.

    This is a top-level function.  It adds `x` and `y` and `z`, and adds
    the sum of any additional keyword arguments' values.  `w` is ignored.

        >>> func(3, 4, 5, w=6, q=10)
        22
   
    Markdown is **absolutely**, _positively_ supported.  Here's an example.

    ```
    The quick brown fox
      jumped
        over
          the lazy dogs.
    ```

    ## First topic

    Let's talk about something.

        10 PRINT "Hello!"
        20 GOTO 10

    That's a bit of BASIC.

    ## Second topic

    Now let's talk about something else.  How about some fruit?  For example,

      - pineapples
      - grapefruits
      - mangosteins
      - kiwis

    @param x
      The first argument.  This is required.
    @type x
      number
    @param y
      The second argument.  This is also required.
    @type y
      number
    @param z
      The third argument. 

      This argument is **not** required.  If no value is passed, as either a
      positional or a keyword argument, the default value of `10` will be used.
    @param kw_args
      Additional keyword arguments.  Their values must all be numerical,
      as they are added together.  

      The keyword arguments' names are ignored.
    @return
      The computed value.
    @rtype
      `float`
    """
    return x + y + z + sum(kw_args.values())


def annotated(
        x: str, 
        y: int=42, 
        *a: "stuff", 
        fn: typing.Callable=math.sqrt, 
        **kw: "more"
    ) -> str:
    """
    A function with annotations.
    """
    return "x={} y={} a={} k={} kw={}".format(x, y, a, k, kw)


#-------------------------------------------------------------------------------

class C:
    """
    A sample class for demonstrating **supdoc**'s features.

    `C` is a top-level class in module `test`.  It serves mainly as a container
    for test methods, which are normal methods, classmethods, staticmethods,
    properties, and so forth.

    Use it like this:

        c = C()
        c.method()

    This is the second paragraph of the docstring.  The quick brown fox jumped
    over the lazy dogs.

    >>> C.staticmethod()
    This runs a static method.
    >>> C.classmethod()
    This runs a class method
    for class C.
    >>> c = C(42)
    >>> for _ in range(3):
    ...    c.method("world")
    Hello, world!
    Hello, world!
    Hello, world!
    >>> c.x
    42

    """

    def __init__(self, x, y=10):
        "This is C.__init__()."
        self.__x = x


    def method(self, name):
        "This is C.method()."
        return "Hello, {}!".format(name)


    @classmethod
    def classmethod(class_):
        "This is C.classmethod()."
        print("This runs a class method")
        print("for class {}.".format(class_.__name__))


    @staticmethod
    def staticmethod():
        "This is C.staticmethod()."
        return "This runs a static method."


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

    @property
    def constant(self):
        return 42
    

    C_CLASS_ATTR = 42


    class Subclass:
        "This is class C.Subclass."

        def __init__(self):
            "This is C.Subclass.__init__()."
            pass


        C_SUBCLASS_ATTR = "Hello, world."



#-------------------------------------------------------------------------------

def exc_function(x):
    """
    This function sometimes raises exceptions.

    @param x
      Might be exceptional, or might not.
    @raise TypeError
      `x` is not an `int`.
    @raise ValueError
      `x` is negative.
    @raise RuntimeError
      Something is broken in the environment.  Something is broken in the
      environment.  Something is broken in the environment.  Something is broken
      in the environment.
    """
    x = int(x)
    if x < 0:
        raise ValueError("x is negative")


