# 'supdoc

'supdoc is a browser for API documentation automatically extracted from Python
source code.  Docstrings are among my favorite Python features, because they
keep the documentation close to the code.  This tool aims to extract code
structure and docstrings, to parse and interpret the latter, and to present it
in a modern web UI.

Sphinx, the leading Python documentation tool, is great for hand-written
documentation, but I find that in many projects, writing manuals is just too low
a priority to get done ever.  Docstrings, however, are cheap to write, and
further can contain doctests, simple code snippets that can serve both as unit
tests and code samples.  Epydoc is the best docstring-focused documentation I
know of, but is old and no longer maintained.

Finally, in this web-focused day and age, I think an API documentation system
should be constructed in modular and service-oriented way.

1. A documentation extract library.  This may be run in batch mode, for
instance, as part of a build process, or just in time, in response to
documentation queries.

2. A library for interpreting as many types and variants of documentation markup
as possible (incuding <i>ad hoc</i> markup) and interpreting it in the context
of code.  For instance, documentation of function parameters should be
associated with the parameters themselves.

3. A JSON-based format for representing the API documentation for a code
module.  

4. User interfaces for browsing the API documentation, responsible for
presentation aspects.


# Document structure

Since the term "doc" is heavily overloaded, we invent variants to describe the
documents and documentation in supdoc.

A **docsrc** is a top-level JSON document encoding content summary and
documentation for one or more Python modules (or packages).  A docsrc looks like
this:

```js
{
  "modules": {
    "mod0": { ... },
    "mod1": { ... }
  }
}
```

A key of `modules` is a fully-qualified Python module name.  The corresponding
value is an objdoc describing the Python module.

An **objdoc** is a JSON object ecoding summary and documentation for a Python
object.  An objdoc may document any type of Python object, such as a module,
class, function, method, or scalar value.  An objdoc may be recursive, i.e. 
contain other objdoc instances, to express composition of Python objects.

With a docsrc, an objdoc can be located given two pieces of information: its
fully-qualified module name and its name path within the module.  The latter is
the dotted series of names by which the object is found by successive calls to
`getattr()`, starting with the module itself.  If the name path is omitted, this
indicates the module object itself.  The name path is generally, but not always,
the same as the object's qualname.

A **ref** is a JSON object that refers to another objdoc.  The syntax follows the
[JSON Reference draft
standard](https://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03).  It is
looks as follows

```js
{
  "$ref": "#/modules/modname/path0/..."
}
```

The reference is always relative to the top of the docsrc.  The reference path
is is `"modules"`, followed by the fully qualified module name, followed by
components of the path within the module.

A ref can be used anywhere in place of an objdoc.


## objdoc fields

Field names of an objdoc and their semantics are given below.  _All_ fields in an
objdoc are optional; an implementation should be able to handle an instance with
any or all omitted.

- `name`: The unqualified name of the object, generally the value of its
  `__name__` attribute.

- `qualname`: The qualified name of the object, generally the value of its
  `__qualname__` attribute.

- `type_name`: The name of the object's type, generally the `__name__` attribute
  of its type.

- `type`: The object's type, an objdoc or (most likely) ref.

- `repr`: A string containing the object's `repr`.

- `dict`: The contents of the object's `__dict__`.  Note that this does not
  contain names from predecessors in the object's MRO.

- `all_names`: An array of names of `dict` entries that make up the public
  interface.  This is generally set for modules only, taken from the `__all__`
  variable.

- `signature`: For a callable object, the object's signature; see below.

- `docs`: The object's documentation, generally extracted from its docstring; 
  see below.


## Signature

A signature is a JSON object encoding the calling signature of a callable
object.  It looks like this:

```js
{
  "params": [
    {
      "name": "...",
      "kind": "...",
      "default": { ... },
      "doc": "...",
      "doc_type": "...",
      "annotation": { ... }
    },
    ...
  ]
}
```

The callable's parameters are given in declaration order.  Each includes the
`name` and `kind` field; the others may be missing.  

- `name`: The parameter name.

- `kind`: The names of one of the parameter kind constants in
  `inspect.Parameter`: `"KEYWORD_ONLY"`, `"POSITIONAL_ONLY"`,
  `"POSITIONAL_OR_KEYWORD"`, `"VAR_KEYWORD"`, OR `"VAR_POSITIONAL"`.

- `default`: A objdoc for the default value.

- `doc`: A string containing parameter documentation extracted from the
callable's docstring.

- `doc_type`: A string containing documentation about the parameter's type,
  extracted from the callable's docstring.

- `annotation`: An objdoc for the parameter annotation.


## Docs

An objdoc's `docs` field containins a JSON object with information extracted from
the object's docstring.  It looks like this:

```js
{
  "doc": "...",
  "summary": "...",
  "body": [ "...", ... ],
  "javadoc": [ ... ]
}
```

As above, all fields may be missing.  Their interpretations are,

- `doc`: The full docstring (without any indentation stripped or other munging).

- `summary`: A summary of the object, extracted from the first line or sentence
  of the docstring

- `body`: An array of paragraphs or other blocks constituting the
  documentation's body.

- `javadoc`: An array of extracted Javadoc-style tags.


### Javadoc

A Javadoc comment looks as follows:

```java
/**
 * Lorem ipsum dolor sit amet, consectetur adipiscing elit.
 *
 * @tag1         sed do eiusmod tempor incididunt
 * @tag2 foobar  ut labore et dolore magna aliqua
 */
```

Some tags, such as tag2 above, accept a single-word argument, while others, 
such as tag1, do not.  A tag is followed by associated text, which may start
or extend onto following lines, and extends until the next tag or the end of
the docstring.

The Javadoc-style tag objects look as follows:

```js
{
  "tag": "tag2",
  "arg": "foobar",
  "text": "sed do eiusmod tempor incididunt"
}
```


