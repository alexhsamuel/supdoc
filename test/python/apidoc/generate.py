from   unittest import TestCase, main

from   apidoc.generate import get_relative_path
from   apidoc.modules import Name

#-------------------------------------------------------------------------------

class TestGetRelativePath(TestCase):

    def test_basic(self):
        def test(n0, n1, ex):
            self.assertEqual(str(get_relative_path(Name(n0), Name(n1))), ex)

        test("foo", "bar", "bar")
        test("foo", "bar.baz", "bar/baz")
        test("foo.foo.foo", "bar.baz", "../../bar/baz")
        test("foo.bar", "baz", "../baz")
        test("foo.bar", "baz.bif", "../baz/bif")
        test("foo.bar", "foo.baz", "baz")
        test("foo.bar.baz", "foo.bar.bif", "bif")
        test("foo.bar", "foo.bar.baz.bif", "bar/baz/bif")



if __name__ == "__main__":
    main()


