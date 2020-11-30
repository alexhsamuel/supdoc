from   .py import format_ctor

#-------------------------------------------------------------------------------

class Dotname:
    """
    A name consisting of dot-separated parts, e.g. "foo.bar.baz".
    """
    
    """
    The separator character.
    """
    SEP = "."

    @classmethod
    def _assert_valid(cls_, parts):
        """
        :raises:
          `AssertionError` if `parts` do not form a valid name.
        """
        assert len(parts) > 0, "no parts"
        for p in parts:
            assert p != "", "empty part"
            assert cls_.SEP not in p, f"separator in part: {p}"


    def __init__(self, part, *parts):
        """
        Constructs a dotname.

        `part` and `parts` may be parts or fragments containing the separator.
        """
        parts = (str(part), ) + tuple( str(p) for p in parts )
        self.__str = self.SEP.join(parts)
        self.__parts = tuple(self.__str.split(self.SEP))

        try:
            self._assert_valid(self.__parts)
        except AssertionError as exc:
            raise ValueError(str(exc)) from None


    def __repr__(self):
        return format_ctor(self, self.__str)


    def __str__(self):
        return self.__str


    def __hash__(self):
        return hash(self.__str)


    def __eq__(self, other):
        return other is self or other == self.__str


    def __ne__(self, other):
        return other is not self and other != self.__str


    def __lt__(self, other):
        return other is not self and other > self.__str


    def __gt__(self, other):
        return other is not self and other < self.__str


    def __le__(self, other):
        return other is self or other >= self.__str


    def __ge__(self, other):
        return other is self or other <= self.__str


    @classmethod
    def _from_parts(cls_, parts):
        """
        Constructs from `parts` without validation.
        """
        # Avoid __init__ so we don't re-split parts.
        name = super().__new__(cls_)
        name.__str = name.SEP.join(parts)
        name.__parts = parts
        return name


    @classmethod
    def from_parts(cls_, parts):
        """
        Constructs from `parts`; parts may not contain the separator.
        """
        parts = tuple( str(p) for p in parts )
        try:
            cls_._assert_valid(parts)
        except AssertionError as exc:
            raise ValueError(str(exc)) from None
        return cls_._from_parts(parts)


    @property
    def name(self):
        """
        The last part.
        """
        return self.__parts[-1]


    @property
    def parent(self):
        """
        The name the last part removed.

        :raise AttributeError:
          The name has only one part.
        """
        if len(self.__parts) == 1:
            raise AttributeError("name has no parent")
        else:
            return self._from_parts(self.__parts[: -1])


    @property
    def parents(self):
        parent = self
        while len(parent.__parts) > 1:
            parent = parent.parent
            yield parent
            
        
    @property
    def parts(self):
        return self.__parts


    def __truediv__(self, part):
        return type(self)(self.__str, part)


    def joinpath(self, *parts):
        return type(self)(self.__str, *parts)


    def relative_to(self, other):
        # FIXME
        pass


    def with_name(self, name):
        return self.parent / name



#-------------------------------------------------------------------------------

class Qualname(Dotname):

    @classmethod
    def _assert_valid(cls_, parts):
        Dotname._assert_valid(parts)
        for p in parts:
            assert str.isidentifier(p), f"not identifier: {p}"



