# templater.py - template expansion for output
#
# Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from __future__ import absolute_import

import os
import re
import types

from .i18n import _
from . import (
    config,
    error,
    minirst,
    parser,
    revset as revsetmod,
    templatefilters,
    templatekw,
    util,
)

# template parsing

elements = {
    # token-type: binding-strength, primary, prefix, infix, suffix
    "(": (20, None, ("group", 1, ")"), ("func", 1, ")"), None),
    ",": (2, None, None, ("list", 2), None),
    "|": (5, None, None, ("|", 5), None),
    "%": (6, None, None, ("%", 6), None),
    ")": (0, None, None, None, None),
    "integer": (0, "integer", None, None, None),
    "symbol": (0, "symbol", None, None, None),
    "string": (0, "string", None, None, None),
    "template": (0, "template", None, None, None),
    "end": (0, None, None, None, None),
}

def tokenize(program, start, end):
    pos = start
    while pos < end:
        c = program[pos]
        if c.isspace(): # skip inter-token whitespace
            pass
        elif c in "(,)%|": # handle simple operators
            yield (c, None, pos)
        elif c in '"\'': # handle quoted templates
            s = pos + 1
            data, pos = _parsetemplate(program, s, end, c)
            yield ('template', data, s)
            pos -= 1
        elif c == 'r' and program[pos:pos + 2] in ("r'", 'r"'):
            # handle quoted strings
            c = program[pos + 1]
            s = pos = pos + 2
            while pos < end: # find closing quote
                d = program[pos]
                if d == '\\': # skip over escaped characters
                    pos += 2
                    continue
                if d == c:
                    yield ('string', program[s:pos], s)
                    break
                pos += 1
            else:
                raise error.ParseError(_("unterminated string"), s)
        elif c.isdigit() or c == '-':
            s = pos
            if c == '-': # simply take negate operator as part of integer
                pos += 1
            if pos >= end or not program[pos].isdigit():
                raise error.ParseError(_("integer literal without digits"), s)
            pos += 1
            while pos < end:
                d = program[pos]
                if not d.isdigit():
                    break
                pos += 1
            yield ('integer', program[s:pos], s)
            pos -= 1
        elif (c == '\\' and program[pos:pos + 2] in (r"\'", r'\"')
              or c == 'r' and program[pos:pos + 3] in (r"r\'", r'r\"')):
            # handle escaped quoted strings for compatibility with 2.9.2-3.4,
            # where some of nested templates were preprocessed as strings and
            # then compiled. therefore, \"...\" was allowed. (issue4733)
            #
            # processing flow of _evalifliteral() at 5ab28a2e9962:
            # outer template string    -> stringify()  -> compiletemplate()
            # ------------------------    ------------    ------------------
            # {f("\\\\ {g(\"\\\"\")}"}    \\ {g("\"")}    [r'\\', {g("\"")}]
            #             ~~~~~~~~
            #             escaped quoted string
            if c == 'r':
                pos += 1
                token = 'string'
            else:
                token = 'template'
            quote = program[pos:pos + 2]
            s = pos = pos + 2
            while pos < end: # find closing escaped quote
                if program.startswith('\\\\\\', pos, end):
                    pos += 4 # skip over double escaped characters
                    continue
                if program.startswith(quote, pos, end):
                    # interpret as if it were a part of an outer string
                    data = parser.unescapestr(program[s:pos])
                    if token == 'template':
                        data = _parsetemplate(data, 0, len(data))[0]
                    yield (token, data, s)
                    pos += 1
                    break
                pos += 1
            else:
                raise error.ParseError(_("unterminated string"), s)
        elif c.isalnum() or c in '_':
            s = pos
            pos += 1
            while pos < end: # find end of symbol
                d = program[pos]
                if not (d.isalnum() or d == "_"):
                    break
                pos += 1
            sym = program[s:pos]
            yield ('symbol', sym, s)
            pos -= 1
        elif c == '}':
            yield ('end', None, pos + 1)
            return
        else:
            raise error.ParseError(_("syntax error"), pos)
        pos += 1
    raise error.ParseError(_("unterminated template expansion"), start)

def _parsetemplate(tmpl, start, stop, quote=''):
    r"""
    >>> _parsetemplate('foo{bar}"baz', 0, 12)
    ([('string', 'foo'), ('symbol', 'bar'), ('string', '"baz')], 12)
    >>> _parsetemplate('foo{bar}"baz', 0, 12, quote='"')
    ([('string', 'foo'), ('symbol', 'bar')], 9)
    >>> _parsetemplate('foo"{bar}', 0, 9, quote='"')
    ([('string', 'foo')], 4)
    >>> _parsetemplate(r'foo\"bar"baz', 0, 12, quote='"')
    ([('string', 'foo"'), ('string', 'bar')], 9)
    >>> _parsetemplate(r'foo\\"bar', 0, 10, quote='"')
    ([('string', 'foo\\')], 6)
    """
    parsed = []
    sepchars = '{' + quote
    pos = start
    p = parser.parser(elements)
    while pos < stop:
        n = min((tmpl.find(c, pos, stop) for c in sepchars),
                key=lambda n: (n < 0, n))
        if n < 0:
            parsed.append(('string', parser.unescapestr(tmpl[pos:stop])))
            pos = stop
            break
        c = tmpl[n]
        bs = (n - pos) - len(tmpl[pos:n].rstrip('\\'))
        if bs % 2 == 1:
            # escaped (e.g. '\{', '\\\{', but not '\\{')
            parsed.append(('string', parser.unescapestr(tmpl[pos:n - 1]) + c))
            pos = n + 1
            continue
        if n > pos:
            parsed.append(('string', parser.unescapestr(tmpl[pos:n])))
        if c == quote:
            return parsed, n + 1

        parseres, pos = p.parse(tokenize(tmpl, n + 1, stop))
        parsed.append(parseres)

    if quote:
        raise error.ParseError(_("unterminated string"), start)
    return parsed, pos

def compiletemplate(tmpl, context):
    parsed, pos = _parsetemplate(tmpl, 0, len(tmpl))
    return [compileexp(e, context, methods) for e in parsed]

def compileexp(exp, context, curmethods):
    t = exp[0]
    if t in curmethods:
        return curmethods[t](exp, context)
    raise error.ParseError(_("unknown method '%s'") % t)

# template evaluation

def getsymbol(exp):
    if exp[0] == 'symbol':
        return exp[1]
    raise error.ParseError(_("expected a symbol, got '%s'") % exp[0])

def getlist(x):
    if not x:
        return []
    if x[0] == 'list':
        return getlist(x[1]) + [x[2]]
    return [x]

def gettemplate(exp, context):
    if exp[0] == 'template':
        return [compileexp(e, context, methods) for e in exp[1]]
    if exp[0] == 'symbol':
        # unlike runsymbol(), here 'symbol' is always taken as template name
        # even if it exists in mapping. this allows us to override mapping
        # by web templates, e.g. 'changelogtag' is redefined in map file.
        return context._load(exp[1])
    raise error.ParseError(_("expected template specifier"))

def evalfuncarg(context, mapping, arg):
    func, data = arg
    # func() may return string, generator of strings or arbitrary object such
    # as date tuple, but filter does not want generator.
    thing = func(context, mapping, data)
    if isinstance(thing, types.GeneratorType):
        thing = stringify(thing)
    return thing

def runinteger(context, mapping, data):
    return int(data)

def runstring(context, mapping, data):
    return data

def _recursivesymbolblocker(key):
    def showrecursion(**args):
        raise error.Abort(_("recursive reference '%s' in template") % key)
    return showrecursion

def _runrecursivesymbol(context, mapping, key):
    raise error.Abort(_("recursive reference '%s' in template") % key)

def runsymbol(context, mapping, key):
    v = mapping.get(key)
    if v is None:
        v = context._defaults.get(key)
    if v is None:
        # put poison to cut recursion. we can't move this to parsing phase
        # because "x = {x}" is allowed if "x" is a keyword. (issue4758)
        safemapping = mapping.copy()
        safemapping[key] = _recursivesymbolblocker(key)
        try:
            v = context.process(key, safemapping)
        except TemplateNotFound:
            v = ''
    if callable(v):
        return v(**mapping)
    return v

def buildtemplate(exp, context):
    ctmpl = [compileexp(e, context, methods) for e in exp[1]]
    if len(ctmpl) == 1:
        return ctmpl[0]  # fast path for string with no template fragment
    return (runtemplate, ctmpl)

def runtemplate(context, mapping, template):
    for func, data in template:
        yield func(context, mapping, data)

def buildfilter(exp, context):
    arg = compileexp(exp[1], context, methods)
    n = getsymbol(exp[2])
    if n in context._filters:
        filt = context._filters[n]
        return (runfilter, (arg, filt))
    if n in funcs:
        f = funcs[n]
        return (f, [arg])
    raise error.ParseError(_("unknown function '%s'") % n)

def runfilter(context, mapping, data):
    arg, filt = data
    thing = evalfuncarg(context, mapping, arg)
    try:
        return filt(thing)
    except (ValueError, AttributeError, TypeError):
        if isinstance(arg[1], tuple):
            dt = arg[1][1]
        else:
            dt = arg[1]
        raise error.Abort(_("template filter '%s' is not compatible with "
                           "keyword '%s'") % (filt.func_name, dt))

def buildmap(exp, context):
    func, data = compileexp(exp[1], context, methods)
    ctmpl = gettemplate(exp[2], context)
    return (runmap, (func, data, ctmpl))

def runmap(context, mapping, data):
    func, data, ctmpl = data
    d = func(context, mapping, data)
    if util.safehasattr(d, 'itermaps'):
        d = d.itermaps()

    for i in d:
        lm = mapping.copy()
        if isinstance(i, dict):
            lm.update(i)
            lm['originalnode'] = mapping.get('node')
            yield runtemplate(context, lm, ctmpl)
        else:
            # v is not an iterable of dicts, this happen when 'key'
            # has been fully expanded already and format is useless.
            # If so, return the expanded value.
            yield i

def buildfunc(exp, context):
    n = getsymbol(exp[1])
    args = [compileexp(x, context, exprmethods) for x in getlist(exp[2])]
    if n in funcs:
        f = funcs[n]
        return (f, args)
    if n in context._filters:
        if len(args) != 1:
            raise error.ParseError(_("filter %s expects one argument") % n)
        f = context._filters[n]
        return (runfilter, (args[0], f))
    raise error.ParseError(_("unknown function '%s'") % n)

def date(context, mapping, args):
    """:date(date[, fmt]): Format a date. See :hg:`help dates` for formatting
    strings. The default is a Unix date format, including the timezone:
    "Mon Sep 04 15:13:13 2006 0700"."""
    if not (1 <= len(args) <= 2):
        # i18n: "date" is a keyword
        raise error.ParseError(_("date expects one or two arguments"))

    date = args[0][0](context, mapping, args[0][1])
    fmt = None
    if len(args) == 2:
        fmt = stringify(args[1][0](context, mapping, args[1][1]))
    try:
        if fmt is None:
            return util.datestr(date)
        else:
            return util.datestr(date, fmt)
    except (TypeError, ValueError):
        # i18n: "date" is a keyword
        raise error.ParseError(_("date expects a date information"))

def diff(context, mapping, args):
    """:diff([includepattern [, excludepattern]]): Show a diff, optionally
    specifying files to include or exclude."""
    if len(args) > 2:
        # i18n: "diff" is a keyword
        raise error.ParseError(_("diff expects zero, one, or two arguments"))

    def getpatterns(i):
        if i < len(args):
            s = stringify(args[i][0](context, mapping, args[i][1])).strip()
            if s:
                return [s]
        return []

    ctx = mapping['ctx']
    chunks = ctx.diff(match=ctx.match([], getpatterns(0), getpatterns(1)))

    return ''.join(chunks)

def fill(context, mapping, args):
    """:fill(text[, width[, initialident[, hangindent]]]): Fill many
    paragraphs with optional indentation. See the "fill" filter."""
    if not (1 <= len(args) <= 4):
        # i18n: "fill" is a keyword
        raise error.ParseError(_("fill expects one to four arguments"))

    text = stringify(args[0][0](context, mapping, args[0][1]))
    width = 76
    initindent = ''
    hangindent = ''
    if 2 <= len(args) <= 4:
        try:
            width = int(stringify(args[1][0](context, mapping, args[1][1])))
        except ValueError:
            # i18n: "fill" is a keyword
            raise error.ParseError(_("fill expects an integer width"))
        try:
            initindent = stringify(args[2][0](context, mapping, args[2][1]))
            hangindent = stringify(args[3][0](context, mapping, args[3][1]))
        except IndexError:
            pass

    return templatefilters.fill(text, width, initindent, hangindent)

def pad(context, mapping, args):
    """:pad(text, width[, fillchar=' '[, right=False]]): Pad text with a
    fill character."""
    if not (2 <= len(args) <= 4):
        # i18n: "pad" is a keyword
        raise error.ParseError(_("pad() expects two to four arguments"))

    width = int(args[1][1])

    text = stringify(args[0][0](context, mapping, args[0][1]))

    right = False
    fillchar = ' '
    if len(args) > 2:
        fillchar = stringify(args[2][0](context, mapping, args[2][1]))
    if len(args) > 3:
        right = util.parsebool(args[3][1])

    if right:
        return text.rjust(width, fillchar)
    else:
        return text.ljust(width, fillchar)

def indent(context, mapping, args):
    """:indent(text, indentchars[, firstline]): Indents all non-empty lines
    with the characters given in the indentchars string. An optional
    third parameter will override the indent for the first line only
    if present."""
    if not (2 <= len(args) <= 3):
        # i18n: "indent" is a keyword
        raise error.ParseError(_("indent() expects two or three arguments"))

    text = stringify(args[0][0](context, mapping, args[0][1]))
    indent = stringify(args[1][0](context, mapping, args[1][1]))

    if len(args) == 3:
        firstline = stringify(args[2][0](context, mapping, args[2][1]))
    else:
        firstline = indent

    # the indent function doesn't indent the first line, so we do it here
    return templatefilters.indent(firstline + text, indent)

def get(context, mapping, args):
    """:get(dict, key): Get an attribute/key from an object. Some keywords
    are complex types. This function allows you to obtain the value of an
    attribute on these types."""
    if len(args) != 2:
        # i18n: "get" is a keyword
        raise error.ParseError(_("get() expects two arguments"))

    dictarg = evalfuncarg(context, mapping, args[0])
    if not util.safehasattr(dictarg, 'get'):
        # i18n: "get" is a keyword
        raise error.ParseError(_("get() expects a dict as first argument"))

    key = evalfuncarg(context, mapping, args[1])
    return dictarg.get(key)

def if_(context, mapping, args):
    """:if(expr, then[, else]): Conditionally execute based on the result of
    an expression."""
    if not (2 <= len(args) <= 3):
        # i18n: "if" is a keyword
        raise error.ParseError(_("if expects two or three arguments"))

    test = stringify(args[0][0](context, mapping, args[0][1]))
    if test:
        yield args[1][0](context, mapping, args[1][1])
    elif len(args) == 3:
        yield args[2][0](context, mapping, args[2][1])

def ifcontains(context, mapping, args):
    """:ifcontains(search, thing, then[, else]): Conditionally execute based
    on whether the item "search" is in "thing"."""
    if not (3 <= len(args) <= 4):
        # i18n: "ifcontains" is a keyword
        raise error.ParseError(_("ifcontains expects three or four arguments"))

    item = stringify(args[0][0](context, mapping, args[0][1]))
    items = evalfuncarg(context, mapping, args[1])

    if item in items:
        yield args[2][0](context, mapping, args[2][1])
    elif len(args) == 4:
        yield args[3][0](context, mapping, args[3][1])

def ifeq(context, mapping, args):
    """:ifeq(expr1, expr2, then[, else]): Conditionally execute based on
    whether 2 items are equivalent."""
    if not (3 <= len(args) <= 4):
        # i18n: "ifeq" is a keyword
        raise error.ParseError(_("ifeq expects three or four arguments"))

    test = stringify(args[0][0](context, mapping, args[0][1]))
    match = stringify(args[1][0](context, mapping, args[1][1]))
    if test == match:
        yield args[2][0](context, mapping, args[2][1])
    elif len(args) == 4:
        yield args[3][0](context, mapping, args[3][1])

def join(context, mapping, args):
    """:join(list, sep): Join items in a list with a delimiter."""
    if not (1 <= len(args) <= 2):
        # i18n: "join" is a keyword
        raise error.ParseError(_("join expects one or two arguments"))

    joinset = args[0][0](context, mapping, args[0][1])
    if util.safehasattr(joinset, 'itermaps'):
        jf = joinset.joinfmt
        joinset = [jf(x) for x in joinset.itermaps()]

    joiner = " "
    if len(args) > 1:
        joiner = stringify(args[1][0](context, mapping, args[1][1]))

    first = True
    for x in joinset:
        if first:
            first = False
        else:
            yield joiner
        yield x

def label(context, mapping, args):
    """:label(label, expr): Apply a label to generated content. Content with
    a label applied can result in additional post-processing, such as
    automatic colorization."""
    if len(args) != 2:
        # i18n: "label" is a keyword
        raise error.ParseError(_("label expects two arguments"))

    # ignore args[0] (the label string) since this is supposed to be a a no-op
    yield args[1][0](context, mapping, args[1][1])

def latesttag(context, mapping, args):
    """:latesttag([pattern]): The global tags matching the given pattern on the
    most recent globally tagged ancestor of this changeset."""
    if len(args) > 1:
        # i18n: "latesttag" is a keyword
        raise error.ParseError(_("latesttag expects at most one argument"))

    pattern = None
    if len(args) == 1:
        pattern = stringify(args[0][0](context, mapping, args[0][1]))

    return templatekw.showlatesttags(pattern, **mapping)

def localdate(context, mapping, args):
    """:localdate(date[, tz]): Converts a date to the specified timezone.
    The default is local date."""
    if not (1 <= len(args) <= 2):
        # i18n: "localdate" is a keyword
        raise error.ParseError(_("localdate expects one or two arguments"))

    date = evalfuncarg(context, mapping, args[0])
    try:
        date = util.parsedate(date)
    except AttributeError:  # not str nor date tuple
        # i18n: "localdate" is a keyword
        raise error.ParseError(_("localdate expects a date information"))
    if len(args) >= 2:
        tzoffset = None
        tz = evalfuncarg(context, mapping, args[1])
        if isinstance(tz, str):
            tzoffset = util.parsetimezone(tz)
        if tzoffset is None:
            try:
                tzoffset = int(tz)
            except (TypeError, ValueError):
                # i18n: "localdate" is a keyword
                raise error.ParseError(_("localdate expects a timezone"))
    else:
        tzoffset = util.makedate()[1]
    return (date[0], tzoffset)

def revset(context, mapping, args):
    """:revset(query[, formatargs...]): Execute a revision set query. See
    :hg:`help revset`."""
    if not len(args) > 0:
        # i18n: "revset" is a keyword
        raise error.ParseError(_("revset expects one or more arguments"))

    raw = stringify(args[0][0](context, mapping, args[0][1]))
    ctx = mapping['ctx']
    repo = ctx.repo()

    def query(expr):
        m = revsetmod.match(repo.ui, expr)
        return m(repo)

    if len(args) > 1:
        formatargs = [evalfuncarg(context, mapping, a) for a in args[1:]]
        revs = query(revsetmod.formatspec(raw, *formatargs))
        revs = list(revs)
    else:
        revsetcache = mapping['cache'].setdefault("revsetcache", {})
        if raw in revsetcache:
            revs = revsetcache[raw]
        else:
            revs = query(raw)
            revs = list(revs)
            revsetcache[raw] = revs

    return templatekw.showrevslist("revision", revs, **mapping)

def rstdoc(context, mapping, args):
    """:rstdoc(text, style): Format ReStructuredText."""
    if len(args) != 2:
        # i18n: "rstdoc" is a keyword
        raise error.ParseError(_("rstdoc expects two arguments"))

    text = stringify(args[0][0](context, mapping, args[0][1]))
    style = stringify(args[1][0](context, mapping, args[1][1]))

    return minirst.format(text, style=style, keep=['verbose'])

def shortest(context, mapping, args):
    """:shortest(node, minlength=4): Obtain the shortest representation of
    a node."""
    if not (1 <= len(args) <= 2):
        # i18n: "shortest" is a keyword
        raise error.ParseError(_("shortest() expects one or two arguments"))

    node = stringify(args[0][0](context, mapping, args[0][1]))

    minlength = 4
    if len(args) > 1:
        minlength = int(args[1][1])

    cl = mapping['ctx']._repo.changelog
    def isvalid(test):
        try:
            try:
                cl.index.partialmatch(test)
            except AttributeError:
                # Pure mercurial doesn't support partialmatch on the index.
                # Fallback to the slow way.
                if cl._partialmatch(test) is None:
                    return False

            try:
                i = int(test)
                # if we are a pure int, then starting with zero will not be
                # confused as a rev; or, obviously, if the int is larger than
                # the value of the tip rev
                if test[0] == '0' or i > len(cl):
                    return True
                return False
            except ValueError:
                return True
        except error.RevlogError:
            return False

    shortest = node
    startlength = max(6, minlength)
    length = startlength
    while True:
        test = node[:length]
        if isvalid(test):
            shortest = test
            if length == minlength or length > startlength:
                return shortest
            length -= 1
        else:
            length += 1
            if len(shortest) <= length:
                return shortest

def strip(context, mapping, args):
    """:strip(text[, chars]): Strip characters from a string. By default,
    strips all leading and trailing whitespace."""
    if not (1 <= len(args) <= 2):
        # i18n: "strip" is a keyword
        raise error.ParseError(_("strip expects one or two arguments"))

    text = stringify(args[0][0](context, mapping, args[0][1]))
    if len(args) == 2:
        chars = stringify(args[1][0](context, mapping, args[1][1]))
        return text.strip(chars)
    return text.strip()

def sub(context, mapping, args):
    """:sub(pattern, replacement, expression): Perform text substitution
    using regular expressions."""
    if len(args) != 3:
        # i18n: "sub" is a keyword
        raise error.ParseError(_("sub expects three arguments"))

    pat = stringify(args[0][0](context, mapping, args[0][1]))
    rpl = stringify(args[1][0](context, mapping, args[1][1]))
    src = stringify(args[2][0](context, mapping, args[2][1]))
    try:
        patre = re.compile(pat)
    except re.error:
        # i18n: "sub" is a keyword
        raise error.ParseError(_("sub got an invalid pattern: %s") % pat)
    try:
        yield patre.sub(rpl, src)
    except re.error:
        # i18n: "sub" is a keyword
        raise error.ParseError(_("sub got an invalid replacement: %s") % rpl)

def startswith(context, mapping, args):
    """:startswith(pattern, text): Returns the value from the "text" argument
    if it begins with the content from the "pattern" argument."""
    if len(args) != 2:
        # i18n: "startswith" is a keyword
        raise error.ParseError(_("startswith expects two arguments"))

    patn = stringify(args[0][0](context, mapping, args[0][1]))
    text = stringify(args[1][0](context, mapping, args[1][1]))
    if text.startswith(patn):
        return text
    return ''


def word(context, mapping, args):
    """:word(number, text[, separator]): Return the nth word from a string."""
    if not (2 <= len(args) <= 3):
        # i18n: "word" is a keyword
        raise error.ParseError(_("word expects two or three arguments, got %d")
                               % len(args))

    try:
        num = int(stringify(args[0][0](context, mapping, args[0][1])))
    except ValueError:
        # i18n: "word" is a keyword
        raise error.ParseError(_("word expects an integer index"))
    text = stringify(args[1][0](context, mapping, args[1][1]))
    if len(args) == 3:
        splitter = stringify(args[2][0](context, mapping, args[2][1]))
    else:
        splitter = None

    tokens = text.split(splitter)
    if num >= len(tokens) or num < -len(tokens):
        return ''
    else:
        return tokens[num]

# methods to interpret function arguments or inner expressions (e.g. {_(x)})
exprmethods = {
    "integer": lambda e, c: (runinteger, e[1]),
    "string": lambda e, c: (runstring, e[1]),
    "symbol": lambda e, c: (runsymbol, e[1]),
    "template": buildtemplate,
    "group": lambda e, c: compileexp(e[1], c, exprmethods),
#    ".": buildmember,
    "|": buildfilter,
    "%": buildmap,
    "func": buildfunc,
    }

# methods to interpret top-level template (e.g. {x}, {x|_}, {x % "y"})
methods = exprmethods.copy()
methods["integer"] = exprmethods["symbol"]  # '{1}' as variable

funcs = {
    "date": date,
    "diff": diff,
    "fill": fill,
    "get": get,
    "if": if_,
    "ifcontains": ifcontains,
    "ifeq": ifeq,
    "indent": indent,
    "join": join,
    "label": label,
    "latesttag": latesttag,
    "localdate": localdate,
    "pad": pad,
    "revset": revset,
    "rstdoc": rstdoc,
    "shortest": shortest,
    "startswith": startswith,
    "strip": strip,
    "sub": sub,
    "word": word,
}

# template engine

stringify = templatefilters.stringify

def _flatten(thing):
    '''yield a single stream from a possibly nested set of iterators'''
    if isinstance(thing, str):
        yield thing
    elif not util.safehasattr(thing, '__iter__'):
        if thing is not None:
            yield str(thing)
    else:
        for i in thing:
            if isinstance(i, str):
                yield i
            elif not util.safehasattr(i, '__iter__'):
                if i is not None:
                    yield str(i)
            elif i is not None:
                for j in _flatten(i):
                    yield j

def unquotestring(s):
    '''unwrap quotes'''
    if len(s) < 2 or s[0] != s[-1]:
        raise SyntaxError(_('unmatched quotes'))
    return s[1:-1]

class engine(object):
    '''template expansion engine.

    template expansion works like this. a map file contains key=value
    pairs. if value is quoted, it is treated as string. otherwise, it
    is treated as name of template file.

    templater is asked to expand a key in map. it looks up key, and
    looks for strings like this: {foo}. it expands {foo} by looking up
    foo in map, and substituting it. expansion is recursive: it stops
    when there is no more {foo} to replace.

    expansion also allows formatting and filtering.

    format uses key to expand each item in list. syntax is
    {key%format}.

    filter uses function to transform value. syntax is
    {key|filter1|filter2|...}.'''

    def __init__(self, loader, filters=None, defaults=None):
        self._loader = loader
        if filters is None:
            filters = {}
        self._filters = filters
        if defaults is None:
            defaults = {}
        self._defaults = defaults
        self._cache = {}

    def _load(self, t):
        '''load, parse, and cache a template'''
        if t not in self._cache:
            # put poison to cut recursion while compiling 't'
            self._cache[t] = [(_runrecursivesymbol, t)]
            try:
                self._cache[t] = compiletemplate(self._loader(t), self)
            except: # re-raises
                del self._cache[t]
                raise
        return self._cache[t]

    def process(self, t, mapping):
        '''Perform expansion. t is name of map element to expand.
        mapping contains added elements for use during expansion. Is a
        generator.'''
        return _flatten(runtemplate(self, mapping, self._load(t)))

engines = {'default': engine}

def stylelist():
    paths = templatepaths()
    if not paths:
        return _('no templates found, try `hg debuginstall` for more info')
    dirlist = os.listdir(paths[0])
    stylelist = []
    for file in dirlist:
        split = file.split(".")
        if split[0] == "map-cmdline":
            stylelist.append(split[1])
    return ", ".join(sorted(stylelist))

class TemplateNotFound(error.Abort):
    pass

class templater(object):

    def __init__(self, mapfile, filters=None, defaults=None, cache=None,
                 minchunk=1024, maxchunk=65536):
        '''set up template engine.
        mapfile is name of file to read map definitions from.
        filters is dict of functions. each transforms a value into another.
        defaults is dict of default map definitions.'''
        if filters is None:
            filters = {}
        if defaults is None:
            defaults = {}
        if cache is None:
            cache = {}
        self.mapfile = mapfile or 'template'
        self.cache = cache.copy()
        self.map = {}
        if mapfile:
            self.base = os.path.dirname(mapfile)
        else:
            self.base = ''
        self.filters = templatefilters.filters.copy()
        self.filters.update(filters)
        self.defaults = defaults
        self.minchunk, self.maxchunk = minchunk, maxchunk
        self.ecache = {}

        if not mapfile:
            return
        if not os.path.exists(mapfile):
            raise error.Abort(_("style '%s' not found") % mapfile,
                             hint=_("available styles: %s") % stylelist())

        conf = config.config(includepaths=templatepaths())
        conf.read(mapfile)

        for key, val in conf[''].items():
            if not val:
                raise SyntaxError(_('%s: missing value') % conf.source('', key))
            if val[0] in "'\"":
                try:
                    self.cache[key] = unquotestring(val)
                except SyntaxError as inst:
                    raise SyntaxError('%s: %s' %
                                      (conf.source('', key), inst.args[0]))
            else:
                val = 'default', val
                if ':' in val[1]:
                    val = val[1].split(':', 1)
                self.map[key] = val[0], os.path.join(self.base, val[1])

    def __contains__(self, key):
        return key in self.cache or key in self.map

    def load(self, t):
        '''Get the template for the given template name. Use a local cache.'''
        if t not in self.cache:
            try:
                self.cache[t] = util.readfile(self.map[t][1])
            except KeyError as inst:
                raise TemplateNotFound(_('"%s" not in template map') %
                                       inst.args[0])
            except IOError as inst:
                raise IOError(inst.args[0], _('template file %s: %s') %
                              (self.map[t][1], inst.args[1]))
        return self.cache[t]

    def __call__(self, t, **mapping):
        ttype = t in self.map and self.map[t][0] or 'default'
        if ttype not in self.ecache:
            self.ecache[ttype] = engines[ttype](self.load,
                                                 self.filters, self.defaults)
        proc = self.ecache[ttype]

        stream = proc.process(t, mapping)
        if self.minchunk:
            stream = util.increasingchunks(stream, min=self.minchunk,
                                           max=self.maxchunk)
        return stream

def templatepaths():
    '''return locations used for template files.'''
    pathsrel = ['templates']
    paths = [os.path.normpath(os.path.join(util.datapath, f))
             for f in pathsrel]
    return [p for p in paths if os.path.isdir(p)]

def templatepath(name):
    '''return location of template file. returns None if not found.'''
    for p in templatepaths():
        f = os.path.join(p, name)
        if os.path.exists(f):
            return f
    return None

def stylemap(styles, paths=None):
    """Return path to mapfile for a given style.

    Searches mapfile in the following locations:
    1. templatepath/style/map
    2. templatepath/map-style
    3. templatepath/map
    """

    if paths is None:
        paths = templatepaths()
    elif isinstance(paths, str):
        paths = [paths]

    if isinstance(styles, str):
        styles = [styles]

    for style in styles:
        # only plain name is allowed to honor template paths
        if (not style
            or style in (os.curdir, os.pardir)
            or os.sep in style
            or os.altsep and os.altsep in style):
            continue
        locations = [os.path.join(style, 'map'), 'map-' + style]
        locations.append('map')

        for path in paths:
            for location in locations:
                mapfile = os.path.join(path, location)
                if os.path.isfile(mapfile):
                    return style, mapfile

    raise RuntimeError("No hgweb templates found in %r" % paths)

# tell hggettext to extract docstrings from these functions:
i18nfunctions = funcs.values()
