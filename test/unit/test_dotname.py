from   supdoc.lib.dotname import Dotname, Qualname

#-------------------------------------------------------------------------------

def test_init():
    n = Dotname("foo.bar.baz")
    assert str(n) == "foo.bar.baz"

    assert Dotname("foo", "bar", "baz") == n
    assert Dotname("foo.bar", "baz") == n
    assert Dotname("foo", "bar.baz") == n
    assert Dotname(n) == n


def test_attrs():
    n = Dotname("foo.bar.baz")
    assert n.name == "baz"
    assert n.parent == Dotname("foo.bar")
    assert list(n.parents) == [Dotname("foo.bar"), Dotname("foo")]
    assert n.parts == ("foo", "bar", "baz")


def test_join():
    n = Dotname("foo.bar.baz")
    assert n / "bif" == "foo.bar.baz.bif"
    assert n / "bif.bof" == "foo.bar.baz.bif.bof"
    assert n.joinpath() == n
    assert n.joinpath("bif") == "foo.bar.baz.bif"
    assert n.joinpath("bif", "bof") == "foo.bar.baz.bif.bof"
    assert n.joinpath("bif.bof") == "foo.bar.baz.bif.bof"
    assert n.with_name("bif") == "foo.bar.bif"
    assert n.with_name("bif.bof") == "foo.bar.bif.bof"


