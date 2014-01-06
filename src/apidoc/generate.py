from   .htmlgen import *

def gen_doc(doc):
    return PRE(doc, class_="doc")


def gen(name, info):
    fn_name = "_gen_" + info["type"]
    fn = globals()[fn_name]
    return fn(name, info)


def gen_module(name, info):
    assert info["type"] == "module"

    parts = [DIV(str(name), class_="module-name")]

    doc = info.get("doc", None)
    if doc is not None:
        parts.append(gen_doc(doc))

    contents = info.get("dict", {})
    contents = [ gen(name + n, v) for n, v in sorted(contents.items()) ]
    contents = DIV(*contents, class_="module-contents")
    parts.append(contents)

    return DIV(*parts, class_="module")


def _gen_module(name, info):
    return DIV("module " + str(name), class_="module-reference")


def _gen_function(name, info):
    return DIV("function " + name.base, class_="function")


def _gen_class(name, info):
    return DIV("class " + name.base, class_="class")

