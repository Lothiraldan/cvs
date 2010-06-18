# revset.py - revision set queries for mercurial
#
# Copyright 2010 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

import re
import parser, util, error, discovery
import match as _match

elements = {
    "(": (20, ("group", 1, ")"), ("func", 1, ")")),
    "-": (19, ("negate", 19), ("minus", 19)),
    "::": (17, ("dagrangepre", 17), ("dagrange", 17),
           ("dagrangepost", 17)),
    "..": (17, ("dagrangepre", 17), ("dagrange", 17),
           ("dagrangepost", 17)),
    ":": (15, ("rangepre", 15), ("range", 15), ("rangepost", 15)),
    "not": (10, ("not", 10)),
    "!": (10, ("not", 10)),
    "and": (5, None, ("and", 5)),
    "&": (5, None, ("and", 5)),
    "or": (4, None, ("or", 4)),
    "|": (4, None, ("or", 4)),
    "+": (4, None, ("or", 4)),
    ",": (2, None, ("list", 2)),
    ")": (0, None, None),
    "symbol": (0, ("symbol",), None),
    "string": (0, ("string",), None),
    "end": (0, None, None),
}

keywords = set(['and', 'or', 'not'])

def tokenize(program):
    pos, l = 0, len(program)
    while pos < l:
        c = program[pos]
        if c.isspace(): # skip inter-token whitespace
            pass
        elif c == ':' and program[pos:pos + 2] == '::': # look ahead carefully
            yield ('::', None, pos)
            pos += 1 # skip ahead
        elif c == '.' and program[pos:pos + 2] == '..': # look ahead carefully
            yield ('..', None, pos)
            pos += 1 # skip ahead
        elif c in "():,-|&+!": # handle simple operators
            yield (c, None, pos)
        elif c in '"\'': # handle quoted strings
            pos += 1
            s = pos
            while pos < l: # find closing quote
                d = program[pos]
                if d == '\\': # skip over escaped characters
                    pos += 2
                    continue
                if d == c:
                    yield ('string', program[s:pos].decode('string-escape'), s)
                    break
                pos += 1
            else:
                raise error.ParseError("unterminated string", s)
        elif c.isalnum() or c in '.': # gather up a symbol/keyword
            s = pos
            pos += 1
            while pos < l: # find end of symbol
                d = program[pos]
                if not (d.isalnum() or d in "._"):
                    break
                if d == '.' and program[pos - 1] == '.': # special case for ..
                    pos -= 1
                    break
                pos += 1
            sym = program[s:pos]
            if sym in keywords: # operator keywords
                yield (sym, None, s)
            else:
                yield ('symbol', sym, s)
            pos -= 1
        else:
            raise error.ParseError("syntax error", pos)
        pos += 1
    yield ('end', None, pos)

# helpers

def getstring(x, err):
    if x[0] == 'string' or x[0] == 'symbol':
        return x[1]
    raise error.ParseError(err)

def getlist(x):
    if not x:
        return []
    if x[0] == 'list':
        return getlist(x[1]) + [x[2]]
    return [x]

def getargs(x, min, max, err):
    l = getlist(x)
    if len(l) < min or len(l) > max:
        raise error.ParseError(err)
    return l

def getset(repo, subset, x):
    if not x:
        raise error.ParseError("missing argument")
    return methods[x[0]](repo, subset, *x[1:])

# operator methods

def negate(repo, subset, x):
    return getset(repo, subset,
                  ('string', '-' + getstring(x, "can't negate that")))

def stringset(repo, subset, x):
    x = repo[x].rev()
    if x == -1 and len(subset) == len(repo):
        return [-1]
    if x in subset:
        return [x]
    return []

def symbolset(repo, subset, x):
    if x in symbols:
        raise error.ParseError("can't use %s here" % x)
    return stringset(repo, subset, x)

def rangeset(repo, subset, x, y):
    m = getset(repo, subset, x)[0]
    n = getset(repo, subset, y)[-1]
    if m < n:
        return range(m, n + 1)
    return range(m, n - 1, -1)

def andset(repo, subset, x, y):
    return getset(repo, getset(repo, subset, x), y)

def orset(repo, subset, x, y):
    s = set(getset(repo, subset, x))
    s |= set(getset(repo, [r for r in subset if r not in s], y))
    return [r for r in subset if r in s]

def notset(repo, subset, x):
    s = set(getset(repo, subset, x))
    return [r for r in subset if r not in s]

def listset(repo, subset, a, b):
    raise error.ParseError("can't use a list in this context")

def func(repo, subset, a, b):
    if a[0] == 'symbol' and a[1] in symbols:
        return symbols[a[1]](repo, subset, b)
    raise error.ParseError("not a function: %s" % a[1])

# functions

def p1(repo, subset, x):
    ps = set()
    cl = repo.changelog
    for r in getset(repo, subset, x):
        ps.add(cl.parentrevs(r)[0])
    return [r for r in subset if r in ps]

def p2(repo, subset, x):
    ps = set()
    cl = repo.changelog
    for r in getset(repo, subset, x):
        ps.add(cl.parentrevs(r)[1])
    return [r for r in subset if r in ps]

def parents(repo, subset, x):
    ps = set()
    cl = repo.changelog
    for r in getset(repo, subset, x):
        ps.update(cl.parentrevs(r))
    return [r for r in subset if r in ps]

def maxrev(repo, subset, x):
    s = getset(repo, subset, x)
    if s:
        m = max(s)
        if m in subset:
            return [m]
    return []

def limit(repo, subset, x):
    l = getargs(x, 2, 2, "limit wants two args")
    try:
        lim = int(getstring(l[1], "limit wants a number"))
    except ValueError:
        raise error.ParseError("limit expects a number")
    return getset(repo, subset, l[0])[:lim]

def children(repo, subset, x):
    cs = set()
    cl = repo.changelog
    s = set(getset(repo, subset, x))
    for r in xrange(0, len(repo)):
        for p in cl.parentrevs(r):
            if p in s:
                cs.add(r)
    return [r for r in subset if r in cs]

def branch(repo, subset, x):
    s = getset(repo, range(len(repo)), x)
    b = set()
    for r in s:
        b.add(repo[r].branch())
    s = set(s)
    return [r for r in subset if r in s or repo[r].branch() in b]

def ancestor(repo, subset, x):
    l = getargs(x, 2, 2, "ancestor wants two args")
    a = getset(repo, subset, l[0])
    b = getset(repo, subset, l[1])
    if len(a) > 1 or len(b) > 1:
        raise error.ParseError("ancestor args must be single revisions")
    return [repo[a[0]].ancestor(repo[b[0]]).rev()]

def ancestors(repo, subset, x):
    args = getset(repo, range(len(repo)), x)
    s = set(repo.changelog.ancestors(*args)) | set(args)
    return [r for r in subset if r in s]

def descendants(repo, subset, x):
    args = getset(repo, range(len(repo)), x)
    s = set(repo.changelog.descendants(*args)) | set(args)
    return [r for r in subset if r in s]

def follow(repo, subset, x):
    getargs(x, 0, 0, "follow takes no arguments")
    p = repo['.'].rev()
    s = set(repo.changelog.ancestors(p)) | set([p])
    return [r for r in subset if r in s]

def date(repo, subset, x):
    ds = getstring(x, 'date wants a string')
    dm = util.matchdate(ds)
    return [r for r in subset if dm(repo[r].date()[0])]

def keyword(repo, subset, x):
    kw = getstring(x, "keyword wants a string").lower()
    l = []
    for r in subset:
        c = repo[r]
        t = " ".join(c.files() + [c.user(), c.description()])
        if kw in t.lower():
            l.append(r)
    return l

def grep(repo, subset, x):
    gr = re.compile(getstring(x, "grep wants a string"))
    l = []
    for r in subset:
        c = repo[r]
        for e in c.files() + [c.user(), c.description()]:
            if gr.search(e):
                l.append(r)
                continue
    return l

def author(repo, subset, x):
    n = getstring(x, "author wants a string").lower()
    return [r for r in subset if n in repo[r].user().lower()]

def hasfile(repo, subset, x):
    pat = getstring(x, "file wants a pattern")
    m = _match.match(repo.root, repo.getcwd(), [pat])
    s = []
    for r in subset:
        for f in repo[r].files():
            if m(f):
                s.append(r)
                continue
    return s

def contains(repo, subset, x):
    pat = getstring(x, "file wants a pattern")
    m = _match.match(repo.root, repo.getcwd(), [pat])
    s = []
    if m.files() == [pat]:
        for r in subset:
            if pat in repo[r]:
                s.append(r)
                continue
    else:
        for r in subset:
            for f in repo[r].manifest():
                if m(f):
                    s.append(r)
                    continue
    return s

def checkstatus(repo, subset, pat, field):
    m = _match.match(repo.root, repo.getcwd(), [pat])
    s = []
    fast = (m.files() == [pat])
    for r in subset:
        c = repo[r]
        if fast:
            if pat not in c.files():
                continue
        else:
            for f in c.files():
                if m(f):
                    break
            else:
                continue
        files = repo.status(c.p1().node(), c.node())[field]
        if fast:
            if pat in files:
                s.append(r)
                continue
        else:
            for f in files:
                if m(f):
                    s.append(r)
                    continue
    return s

def modifies(repo, subset, x):
    pat = getstring(x, "modifies wants a pattern")
    return checkstatus(repo, subset, pat, 0)

def adds(repo, subset, x):
    pat = getstring(x, "adds wants a pattern")
    return checkstatus(repo, subset, pat, 1)

def removes(repo, subset, x):
    pat = getstring(x, "removes wants a pattern")
    return checkstatus(repo, subset, pat, 2)

def merge(repo, subset, x):
    getargs(x, 0, 0, "merge takes no arguments")
    cl = repo.changelog
    return [r for r in subset if cl.parentrevs(r)[1] != -1]

def closed(repo, subset, x):
    getargs(x, 0, 0, "closed takes no arguments")
    return [r for r in subset if repo[r].extra().get('close')]

def head(repo, subset, x):
    getargs(x, 0, 0, "head takes no arguments")
    hs = set()
    for b, ls in repo.branchmap().iteritems():
        hs.update(repo[h].rev() for h in ls)
    return [r for r in subset if r in hs]

def reverse(repo, subset, x):
    l = getset(repo, subset, x)
    l.reverse()
    return l

def sort(repo, subset, x):
    l = getargs(x, 1, 2, "sort wants one or two arguments")
    keys = "rev"
    if len(l) == 2:
        keys = getstring(l[1], "sort spec must be a string")

    s = l[0]
    keys = keys.split()
    l = []
    def invert(s):
        return "".join(chr(255 - ord(c)) for c in s)
    for r in getset(repo, subset, s):
        c = repo[r]
        e = []
        for k in keys:
            if k == 'rev':
                e.append(r)
            elif k == '-rev':
                e.append(-r)
            elif k == 'branch':
                e.append(c.branch())
            elif k == '-branch':
                e.append(invert(c.branch()))
            elif k == 'desc':
                e.append(c.description())
            elif k == '-desc':
                e.append(invert(c.description()))
            elif k in 'user author':
                e.append(c.user())
            elif k in '-user -author':
                e.append(invert(c.user()))
            elif k == 'date':
                e.append(c.date()[0])
            elif k == '-date':
                e.append(-c.date()[0])
            else:
                raise error.ParseError("unknown sort key %r" % k)
        e.append(r)
        l.append(e)
    l.sort()
    return [e[-1] for e in l]

def getall(repo, subset, x):
    getargs(x, 0, 0, "all takes no arguments")
    return subset

def heads(repo, subset, x):
    s = getset(repo, subset, x)
    ps = set(parents(repo, subset, x))
    return [r for r in s if r not in ps]

def roots(repo, subset, x):
    s = getset(repo, subset, x)
    cs = set(children(repo, subset, x))
    return [r for r in s if r not in cs]

def outgoing(repo, subset, x):
    import hg # avoid start-up nasties
    l = getargs(x, 0, 1, "outgoing wants a repo path")
    dest = l[1:] or ''
    dest = repo.ui.expandpath(dest or 'default-push', dest or 'default')
    dest, branches = hg.parseurl(dest)
    other = hg.repository(hg.remoteui(repo, {}), dest)
    repo.ui.pushbuffer()
    o = discovery.findoutgoing(repo, other)
    repo.ui.popbuffer()
    cl = repo.changelog
    o = set([cl.rev(r) for r in repo.changelog.nodesbetween(o, None)[0]])
    print 'out', dest, o
    return [r for r in subset if r in o]

def tagged(repo, subset, x):
    getargs(x, 0, 0, "tagged takes no arguments")
    cl = repo.changelog
    s = set([cl.rev(n) for t, n in repo.tagslist() if t != 'tip'])
    return [r for r in subset if r in s]

symbols = {
    "adds": adds,
    "all": getall,
    "ancestor": ancestor,
    "ancestors": ancestors,
    "author": author,
    "branch": branch,
    "children": children,
    "closed": closed,
    "contains": contains,
    "date": date,
    "descendants": descendants,
    "file": hasfile,
    "follow": follow,
    "grep": grep,
    "head": head,
    "heads": heads,
    "keyword": keyword,
    "limit": limit,
    "max": maxrev,
    "merge": merge,
    "modifies": modifies,
    "outgoing": outgoing,
    "p1": p1,
    "p2": p2,
    "parents": parents,
    "removes": removes,
    "reverse": reverse,
    "roots": roots,
    "sort": sort,
    "tagged": tagged,
    "user": author,
}

methods = {
    "negate": negate,
    "range": rangeset,
    "string": stringset,
    "symbol": symbolset,
    "and": andset,
    "or": orset,
    "not": notset,
    "list": listset,
    "func": func,
}

def optimize(x, small):
    if x == None:
        return 0, x

    smallbonus = 1
    if small:
        smallbonus = .5

    op = x[0]
    if op == 'minus':
        return optimize(('and', x[1], ('not', x[2])), small)
    elif op == 'dagrange':
        return optimize(('and', ('func', ('symbol', 'descendants'), x[1]),
                         ('func', ('symbol', 'ancestors'), x[2])), small)
    elif op == 'dagrangepre':
        return optimize(('func', ('symbol', 'ancestors'), x[1]), small)
    elif op == 'dagrangepost':
        return optimize(('func', ('symbol', 'descendants'), x[1]), small)
    elif op == 'rangepre':
        return optimize(('range', ('string', '0'), x[1]), small)
    elif op == 'rangepost':
        return optimize(('range', x[1], ('string', 'tip')), small)
    elif op in 'string symbol negate':
        return smallbonus, x # single revisions are small
    elif op == 'and' or op == 'dagrange':
        wa, ta = optimize(x[1], True)
        wb, tb = optimize(x[2], True)
        w = min(wa, wb)
        if wa > wb:
            return w, (op, tb, ta)
        return w, (op, ta, tb)
    elif op == 'or':
        wa, ta = optimize(x[1], False)
        wb, tb = optimize(x[2], False)
        if wb < wa:
            wb, wa = wa, wb
        return max(wa, wb), (op, ta, tb)
    elif op == 'not':
        o = optimize(x[1], not small)
        return o[0], (op, o[1])
    elif op == 'group':
        return optimize(x[1], small)
    elif op in 'range list':
        wa, ta = optimize(x[1], small)
        wb, tb = optimize(x[2], small)
        return wa + wb, (op, ta, tb)
    elif op == 'func':
        f = getstring(x[1], "not a symbol")
        wa, ta = optimize(x[2], small)
        if f in "grep date user author keyword branch file":
            w = 10 # slow
        elif f in "modifies adds removes outgoing":
            w = 30 # slower
        elif f == "contains":
            w = 100 # very slow
        elif f == "ancestor":
            w = 1 * smallbonus
        elif f == "reverse limit":
            w = 0
        elif f in "sort":
            w = 10 # assume most sorts look at changelog
        else:
            w = 1
        return w + wa, (op, x[1], ta)
    return 1, x

parse = parser.parser(tokenize, elements).parse

def match(spec):
    tree = parse(spec)
    weight, tree = optimize(tree, True)
    def mfunc(repo, subset):
        return getset(repo, subset, tree)
    return mfunc
