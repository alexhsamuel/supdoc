import html
import re

import markdown.extensions
import markdown.preprocessors
import pygments
import pygments.lexers
import pygments.formatters

#-------------------------------------------------------------------------------

class Extension(markdown.extensions.Extension):

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        md.preprocessors.add(
            "python_doctest", 
            Preprocessor(md), 
            ">normalize_whitespace")



PS1_RE = re.compile("( *)(>>> .*)")

def extract(lines):
    lines = iter(lines)

    try:
        line = next(lines)

        while True:
            # Look for a PS1 line.
            match = PS1_RE.match(line)
            if match is None:
                # Not a doctest.
                yield line
                line = next(lines)
                continue

            # Got the PS1 line; start a doctest.
            indent, line = match.groups()
            source_lines = [line]
            line = next(lines)

            # Gather any following PS2 lines.
            while line.startswith(indent + "... "):
                source_lines.append(line[len(indent) :])
                line = next(lines)

            # Any remaining indented nonempty lines are output.
            output_lines = []
            while (line.startswith(indent) 
                   and line.strip() != ""
                   and not line.startswith(indent + ">>>")):
                output_lines.append(html.escape(line[len(indent) :]))
                line = next(lines)

            # FIXME: Why do we build a paragraph and then split it right back?
            yield from format(source_lines, output_lines).split("\n")

    except StopIteration:
        return


def format(source, output):
    # Cut off the prompts.
    prompts, source = zip(*( (l[: 4], l[4: ]) for l in source ))

    # Use pygments to format the remaining code.
    lexer = pygments.lexers.get_lexer_by_name("python")
    formatter = pygments.formatters.get_formatter_by_name(
        "html", cssclass="src")
    source = pygments.highlight("\n".join(source), lexer, formatter).split("\n")

    # Now we do something hacky and make assumptions about the output from
    # pygmnets in order to reinsert the prompts.
    prompts = [ '<span class="prompt">' + p + '</span>' for p in prompts ]
    i = source[0].find("<span")
    source[0] = source[0][: i] + prompts[0] + source[0][i :]
    for i in range(1, len(prompts)):
        source[i] = prompts[i] + source[i]

    return (
          '<div class="doctest">' 
          + "\n".join(source)
        + '<div class="out"><pre>' + "\n".join(output) + '</pre></div>'
        + '</div>'
    )



class Preprocessor(markdown.preprocessors.Preprocessor):

    def __init__(self, md):
        super().__init__(md)


    def run(self, lines):
        return list(extract(lines))



