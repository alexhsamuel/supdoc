import logging
import pathlib
import shutil

from   . import base
from   .htmlgen import *
from   .modules import Name
from   .path import Path

#-------------------------------------------------------------------------------

def wrap_document(ctx, *body, title=None):
    stylesheet = get_relative_path(ctx.name, None) / "apidoc.css"
    head = [LINK(rel="stylesheet", type="text/css", href=stylesheet)]

    if title is not None:
        head.append(TITLE(title))

    return HTML(HEAD(*head), BODY(*body))


def gen_doc(doc):
    return PRE(doc, class_="doc")


def get_relative_path(name0, name1):
    parts0 = [] if name0 is None else list(name0)[: -1]
    parts1 = [] if name1 is None else list(name1)
    # Remove common prefixes.
    while len(parts0) > 0 and len(parts1) > 1 and parts0[0] == parts1[0]:
        _ = parts0.pop(0)
        _ = parts1.pop(0)
    return pathlib.PurePosixPath._from_parts([".."] * len(parts0) + parts1)


def make_module_link(name, from_name=None):
    path = get_relative_path(from_name, name).with_suffix(".html")
    return A(name, href=path, class_="module-link")


#-------------------------------------------------------------------------------

class Context(base.Struct("modules", "name")):

    def __init__(self, modules, **kw_args):
        modules = { Name(n): m for n, m in modules.items() }
        super(Context, self).__init__(modules=modules, **kw_args)
        


def gen(ctx, name, info):
    fn_name = "gen_" + info["type"]
    fn = globals()[fn_name]
    return fn(ctx, name, info)


def gen_module(ctx, name, module):
    assert module["type"] == "module"

    module_name = Name(module["name"])
    if module_name in ctx.modules:
        module_name = make_module_link(module_name, ctx.name)
    return DIV(
        "{} = {} ".format(name, module_name), 
        class_="module-reference")


def gen_function(ctx, name, function):
    assert function["type"] == "function"
    return DIV("function " + name, class_="function")


def gen_class(ctx, name, class_):
    assert class_["type"] == "class"
    return DIV("class " + name, class_="class")


#-------------------------------------------------------------------------------

def generate_module(ctx):
    module = ctx.modules[ctx.name]
    assert module["type"] == "module"

    parts = [DIV(ctx.name, class_="module-name")]

    doc = module.get("doc", None)
    if doc is not None:
        parts.append(gen_doc(doc))

    contents = {}
    for n, v in module.get("dict", {}).items():
        contents.setdefault(v["type"], {})[n] = v

    def section(name, contents):
        contents = ( gen(ctx, n, i) for n, i in sorted(contents.items()) )
        return DIV(
            SPAN(name, class_="module-section-name"),
            *contents,
            class_="module-section")

    parts.extend((
        section("Modules",   contents.pop("module", {})),
        section("Classes",   contents.pop("class", {})),
        section("Functions", contents.pop("function", {})),
        ))
    assert len(contents) == 0
    return DIV(*parts, class_="module")


def write_module_file(ctx, name, path):
    ctx = ctx.copy(name=Name(name))
    path = Path(path)

    logging.debug("generating HTML for {}".format(ctx.name))
    html = generate_module(ctx)
    html = wrap_document(ctx, html, title="module {}".format(ctx.name))

    logging.debug("writing HTML to {}".format(path))
    if not path.parent.is_dir():
        path.parent.mkdir(parents=True)
    with path.open("w") as file:
        file.write(html.format())


def write_module_files(modules, dir):
    ctx = Context(modules=modules)
    dir = Path(dir)

    index = []

    for name in sorted(modules):
        name = Name(name)
        # FIXME: Duplicated with make_module_link().
        path = get_relative_path(None, name).with_suffix(".html")
        write_module_file(ctx, name, dir / path)

        index.append(DIV(make_module_link(name), class_="index-entry"))

    index = wrap_document(ctx, DIV(*index, class_="module-index"))
    index_path = dir / "index.html"
    with index_path.open("w") as file:
        file.write(index.format())

    # Install the stylesheet.
    shutil.copy(
        str(Path(__file__).parent / "apidoc.css"),
        str(dir / "apidoc.css"))


#-------------------------------------------------------------------------------

__all__ = (
    "write_module_files",
    )

