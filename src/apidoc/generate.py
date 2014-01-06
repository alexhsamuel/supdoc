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
    parts0 = () if name0 is None else tuple(name0)
    parts1 = () if name1 is None else tuple(name1)
    # Remove common prefixes.
    while len(parts0) > 0 and len(parts1) > 0 and parts0[0] == parts1[0]:
        _, *parts0 = parts0
        _, *parts1 = parts1
    return pathlib.PurePosixPath._from_parts(("..", ) * len(parts0) + parts1)


#-------------------------------------------------------------------------------

def _gen(name, info):
    fn_name = "_gen_" + info["type"]
    fn = globals()[fn_name]
    return fn(name, info)


def _gen_module(name, info):
    assert info["type"] == "module"
    return DIV("module " + str(name), class_="module-reference")


def _gen_function(name, info):
    assert info["type"] == "function"
    return DIV("function " + name.base, class_="function")


def _gen_class(name, info):
    assert info["type"] == "class"
    return DIV("class " + name.base, class_="class")


#-------------------------------------------------------------------------------

def generate_module(name, info):
    assert info["type"] == "module"

    parts = [DIV(name, class_="module-name")]

    doc = info.get("doc", None)
    if doc is not None:
        parts.append(gen_doc(doc))

    contents = info.get("dict", {})
    contents = [ _gen(name + n, v) for n, v in sorted(contents.items()) ]
    contents = DIV(*contents, class_="module-contents")
    parts.append(contents)

    return DIV(*parts, class_="module")


def write_module_file(name, module, path):
    path = Path(path)

    logging.debug("generating HTML for {}".format(name))
    html = generate_module(name, module)
    html = wrap_document(html, title="module {}".format(name))

    logging.debug("writing HTML to {}".format(path))
    if not path.parent.is_dir():
        path.parent.mkdir(parents=True)
    with path.open("w") as file:
        file.write(html.format())


def write_module_files(modules, dir):
    dir = Path(dir)

    index = []

    for name, module in sorted(modules.items()):
        name = Name(name)
        path = get_relative_path(None, name).with_suffix(".html")
        write_module_file(name, module, dir / path)

        link = A(name, href=path, class_="module-link")
        index.append(DIV(link, class_="index-entry"))

    index = wrap_document(DIV(*index, class_="module-index"))
    index_path = dir / "index.html"
    with index_path.open("w") as file:
        file.write(index.format())


#-------------------------------------------------------------------------------

__all__ = (
    "generate_module",
    "write_module_file",
    "write_module_files",
    )

