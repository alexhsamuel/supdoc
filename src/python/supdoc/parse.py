#-------------------------------------------------------------------------------
# NOTE: Not currently used.
#-------------------------------------------------------------------------------

import re
import sys

#-------------------------------------------------------------------------------

def inot_none(it):
    return ( e for e in it if e is not None )


#-------------------------------------------------------------------------------

WHITESPACE = ' '

BULLETS = {'-', '*'}

BULLETS_REGEX = { 
    re.compile(
        "^([{ws}]*)({b})[{ws}]*(.*)$".format(ws=WHITESPACE, b=re.escape(b))) 
    for b in BULLETS 
    }


class Text:

    def __init__(self, text):
        self.text = text


    def __str__(self):
        return self.text


    @property
    def empty(self):
        return self.text.strip(WHITESPACE) == ''


    @property
    def indent(self):
        for count, char in enumerate(self.text):
            if char not in WHITESPACE:
                return count
        else:
            return None



class Block:

    def __init__(self, content=(), *, tag=None, classes=(), attrs={}):
        self.content = list(content)
        self.tag = tag
        self.classes = set(classes)
        self.attrs = dict(attrs)

        self.indent = (
            0 if len(self.content) == 0 
            else min(inot_none( o.indent for o in self ))
            )


    def __len__(self):
        return self.content.__len__()


    def __str__(self):
        return "\n".join(format_block(self))


    def __iter__(self):
        return self.content.__iter__()


    def __getitem__(self, index):
        return self.content.__getitem__(index)


    def __setitem__(self, index, value):
        return self.content.__setitem__(index, value)


    def __delitem__(self, index):
        return self.content.__delitem__(index)


    def append(self, item):
        return self.content.append(item)



def format_block(block, indent=0):
    prefix = ' ' * indent

    # Opening.
    if block.tag is None and False:
        content_prefix = prefix
    else:
        parts = []
        if block.tag is not None:
            parts.append(block.tag)
        if len(block.classes) > 0:
            parts.append('class="{}"'.format(' '.join(block.classes)))
        for name, value in block.attrs.items():
            parts.append('{}="{}"'.format(name, value))
        parts.append('indent={}'.format(block.indent))
        yield prefix + '<' + ' '.join(parts) + '>'
        content_prefix = prefix + ' '

    for obj in block.content:
        if isinstance(obj, Block):
            yield from format_block(obj, indent + 1)
        else:
            yield content_prefix + str(obj)

    # Closing.
    yield prefix + '</' + (block.tag or '') + '>'


def walk(block, fn, pre=False):
    """
    Applies `fn` to a block and its children.

    @param pre
      If true, applies pre-order, else post-order.
    """
    if pre:
        fn(block)
    for obj in block.content:
        if isinstance(obj, Block):
            walk(obj, fn, pre=pre)
    if not pre:
        fn(block)


#-------------------------------------------------------------------------------

def split_indent(block):
    def gen():
        base_indent = block.indent
        div = None

        for obj in block:
            if obj.indent == base_indent:
                if div is not None:
                    # No longer indented.  End this DIV.
                    yield div
                    div = None
                yield obj
            else:
                if div is None:
                    # Start a new DIV.
                    div = Block(tag='DIV')
                div.append(obj)

        if div is not None:
            yield div
                
    block[:] = gen()


def split_paragraphs(block):
    """
    Combines text in block contents into paragraphs.
    """
    # Break block contents into paragraphs by blank lines.
    def gen(block):
        par = []
        for obj in block:
            if isinstance(obj, Text) and obj.empty:
                # New paragraph.
                yield par
                par = []
            else:
                par.append(obj)
        yield par

    # Combine paragraphs.  
    def finish(pars):
        for par in pars:
            if len(par) == 0:
                continue
            elif any( isinstance(o, Text) for o in par ):
                # Paragraph contains text.  Use a P element.
                yield Block(par, tag='P')
            else:
                # Doesn't contain text; don't wrap it.
                yield from par

    block[:] = finish(gen(block))


def split_doctest(block):
    if (isinstance(block, Block) 
        and len(block) > 0 
        and isinstance(block[0], Text)
        and block[0].text.startswith('>>> ')):
        block.tag = 'DOCTEST'


def split_blocks(block):
    base_indent = block.indent

    def gen(objs):
        block = None
        for obj in objs:
            if isinstance(obj, Text) and obj.empty:
                # Blank line.
                if block is None:
                    # Ignore it.
                    continue
                elif block.indent == base_indent:
                    # End the paragraph.
                    yield block
                    block = None
                    continue

            if (block is not None 
                and ((obj.indent == base_indent) 
                     ^ (block.indent == base_indent))):
                yield block
                block = None

            if block is None:
                block = Block(tag='P' if obj.indent == base_indent else 'DIV')
            block.append(obj)

        if block is not None:
            yield block

    block[:] = gen(block)


def split(block):
    split_doctest(block)
    split_blocks(block)


def get_bullet(obj):
    """
    If `obj` is a `Text` and starts with a bullet, separates it.

    @return
      The bullet and the text with bullet removed, or `(None, None)` otherwise.
    """
    if not isinstance(obj, Text):
        return None, None
    
    for regex in BULLETS_REGEX:
        match = regex.match(obj.text)
        if match is not None:
            indent, bullet, text = match.groups()
            return bullet, indent + text
    else:
        return None, obj.text


def split_bullet_list(block):
    """
    Finds and assembles bullet lists in block contents.

    Look for bullet lists that satisfy:
    - Each bullet is the same.
    - The indentation of each bullet matches the first.
    - Continuation lines are indented at least as much.
    - If continuation lines are not indented, they end at blanks.
    """
    def gen():
        ul = None
        at_blank = False

        for obj in block:
            obj_bullet, obj_text = get_bullet(obj)

            if ul is not None and (
                    # Outdented.
                    (obj.indent is not None and obj.indent < indent)
                    # Mismatched bullet character.
                    or (obj_bullet is not None and obj_bullet != bullet)
                    # Same indent following a blank line.
                    or (at_blank 
                        and obj_bullet is None and obj.indent == indent)):
                # End the current list.
                yield ul
                ul = None

            if obj_bullet is not None and ul is None:
                # Start a new bullet list.
                li = Block([Text(obj_text)], tag="LI")
                ul = Block([li], tag="UL")
                indent = obj.indent
                assert indent is not None
                bullet = obj_bullet
                
            elif obj_bullet is not None and obj.indent == indent:
                # Start a new bullet item in the current list.
                li = Block([Text(obj_text)], tag="LI")
                ul.append(li)

            elif ul is not None:
                # Add it to the current item.
                li.append(obj)

            else:
                # Normal line.
                yield obj

            at_blank = isinstance(obj, Text) and obj.empty

        if ul is not None:
            # Yield the list in progress.
            yield ul

    block[:] = gen()


#-------------------------------------------------------------------------------

def get():
    with open("/Users/samuel/dev/supdoc/test/input/markup/doctest0.txt") as file:
        return Block(content=[ Text(l) for l in file.read().splitlines() ])


if __name__ == '__main__':
    input = sys.stdin.read()
    block = Block(content=input.splitlines(), tag='DIV')
    walk(block, split_bullet_list)
    walk(block, split_paragraphs)
    for line in format_block(block):
        print(line)


