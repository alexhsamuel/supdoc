import logging
import pathlib

from   .htmlgen import *
from   .modules import Name
from   .path import Path

#-------------------------------------------------------------------------------

def wrap_document(*body, title=None):
    head = []
    if title is not None:
        head.append(TITLE(title))

    return HTML(HEAD(*head), BODY(*body))


def gen_doc(doc):
    return PRE(doc, class_="doc")


def get_relative_path(name0, name1):
    parts0 = [] if name0 is None else list(name0)
    parts1 = [] if name1 is None else list(name1)
    # Remove common prefixes.
    while len(parts0) > 0 and len(parts1) > 0 and parts0[0] == parts1[0]:
        _ = parts0.pop(0)
        _ = parts1.pop(0)
    return pathlib.PurePosixPath._from_parts([".."] * len(parts0) + parts1)


#-------------------------------------------------------------------------------

class Generator:
    """
    Implementation detail.
    """

    def __init__(self, modules):
        self.__modules = { Name(n): m for n, m in modules.items() }
        self.__name = None


    @property
    def names(self):
        return sorted( Name(n) for n in self.__modules )


    def generate_module(self, name):
        name = Name(name)
        self.__name = name  # FIXME: Shame.

        info = self.__modules[name]
        assert info["type"] == "module"

        parts = [DIV(name, class_="module-name")]

        doc = info.get("doc", None)
        if doc is not None:
            parts.append(gen_doc(doc))

        contents = info.get("dict", {})
        contents = [ 
            self._gen(n, v) 
            for n, v in sorted(contents.items()) 
            ]
        contents = DIV(*contents, class_="module-contents")
        parts.append(contents)

        module = DIV(*parts, class_="module")
        self.__name = None  # FIXME: Shame.
        return module


    def _gen(self, name, info):
        fn_name = "_gen_" + info["type"]
        fn = getattr(self, fn_name)
        return fn(name, info)


    def _gen_module(self, name, info):
        assert info["type"] == "module"
        
        module_name = Name(info["name"])
        if module_name in self.__modules:
            link = get_relative_path(self.__name.parent, module_name).with_suffix(".html")
            module_name = A(module_name, href=link)
        return DIV(
            "{} = {} ".format(name, module_name), 
            class_="module-reference")


    def _gen_function(self, name, info):
        assert info["type"] == "function"
        return DIV("function " + name, class_="function")


    def _gen_class(self, name, info):
        assert info["type"] == "class"
        return DIV("class " + name, class_="class")



#-------------------------------------------------------------------------------

def write_module_file(generator, name, path):
    name = Name(name)
    path = Path(path)

    logging.debug("generating HTML for {}".format(name))
    html = generator.generate_module(name)
    html = wrap_document(html, title="module {}".format(name))

    logging.debug("writing HTML to {}".format(path))
    if not path.parent.is_dir():
        path.parent.mkdir(parents=True)
    with path.open("w") as file:
        file.write(html.format())


def write_module_files(generator, dir):
    dir = Path(dir)

    index = []

    for name in generator.names:
        path = get_relative_path(None, name).with_suffix(".html")
        write_module_file(generator, name, dir / path)

        link = A(name, href=path, class_="module-link")
        index.append(DIV(link, class_="index-entry"))

    index = wrap_document(DIV(*index, class_="module-index"))
    index_path = dir / "index.html"
    with index_path.open("w") as file:
        file.write(index.format())


#-------------------------------------------------------------------------------

__all__ = (
    "Generator",
    "write_module_file",
    "write_module_files",
    )

