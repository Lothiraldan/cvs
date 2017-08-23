# drawdag.py - convert ASCII revision DAG to actual changesets
#
# Copyright 2016 Facebook, Inc.
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.
"""
create changesets from an ASCII graph for testing purpose.

For example, given the following input::

    c d
    |/
    b
    |
    a

4 changesets and 4 local tags will be created.
`hg log -G -T "{rev} {desc} (tag: {tags})"` will output::

    o  3 d (tag: d tip)
    |
    | o  2 c (tag: c)
    |/
    o  1 b (tag: b)
    |
    o  0 a (tag: a)

For root nodes (nodes without parents) in the graph, they can be revsets
pointing to existing nodes.  The ASCII graph could also have disconnected
components with same names referring to the same changeset.

Therefore, given the repo having the 4 changesets (and tags) above, with the
following ASCII graph as input::

    foo    bar       bar  foo
     |     /          |    |
    ancestor(c,d)     a   baz

The result (`hg log -G -T "{desc}"`) will look like::

    o    foo
    |\
    +---o  bar
    | | |
    | o |  baz
    |  /
    +---o  d
    | |
    +---o  c
    | |
    o |  b
    |/
    o  a

Note that if you take the above `hg log` output directly as input. It will work
as expected - the result would be an isomorphic graph::

    o    foo
    |\
    | | o  d
    | |/
    | | o  c
    | |/
    | | o  bar
    | |/|
    | o |  b
    | |/
    o /  baz
     /
    o  a

This is because 'o' is specially handled in the input: instead of using 'o' as
the node name, the word to the right will be used.

Some special comments could have side effects:

    - Create obsmarkers
      # replace: A -> B -> C -> D  # chained 1 to 1 replacements
      # split: A -> B, C           # 1 to many
      # prune: A, B, C             # many to nothing
"""
from __future__ import absolute_import, print_function

import collections
import itertools
import re

from mercurial.i18n import _
from mercurial import (
    context,
    error,
    node,
    obsolete,
    pycompat,
    registrar,
    scmutil,
    tags as tagsmod,
)

cmdtable = {}
command = registrar.command(cmdtable)

_pipechars = b'\\/+-|'
_nonpipechars = b''.join(pycompat.bytechr(i) for i in range(33, 127)
                         if pycompat.bytechr(i) not in _pipechars)

def _isname(ch):
    """char -> bool. return True if ch looks like part of a name, False
    otherwise"""
    return ch in _nonpipechars

def _parseasciigraph(text):
    r"""str -> {str : [str]}. convert the ASCII graph to edges

    >>> import pprint
    >>> pprint.pprint({pycompat.sysstr(k): [pycompat.sysstr(vv) for vv in v]
    ...  for k, v in _parseasciigraph(br'''
    ...        G
    ...        |
    ...  I D C F   # split: B -> E, F, G
    ...   \ \| |   # replace: C -> D -> H
    ...    H B E   # prune: F, I
    ...     \|/
    ...      A
    ... ''').items()})
    {'A': [],
     'B': ['A'],
     'C': ['B'],
     'D': ['B'],
     'E': ['A'],
     'F': ['E'],
     'G': ['F'],
     'H': ['A'],
     'I': ['H']}
    >>> pprint.pprint({pycompat.sysstr(k): [pycompat.sysstr(vv) for vv in v]
    ...  for k, v in _parseasciigraph(br'''
    ...  o    foo
    ...  |\
    ...  +---o  bar
    ...  | | |
    ...  | o |  baz
    ...  |  /
    ...  +---o  d
    ...  | |
    ...  +---o  c
    ...  | |
    ...  o |  b
    ...  |/
    ...  o  a
    ... ''').items()})
    {'a': [],
     'b': ['a'],
     'bar': ['b', 'a'],
     'baz': [],
     'c': ['b'],
     'd': ['b'],
     'foo': ['baz', 'b']}
    """
    lines = text.splitlines()
    edges = collections.defaultdict(list)  # {node: []}

    def get(y, x):
        """(int, int) -> char. give a coordinate, return the char. return a
        space for anything out of range"""
        if x < 0 or y < 0:
            return b' '
        try:
            return lines[y][x:x + 1] or b' '
        except IndexError:
            return b' '

    def getname(y, x):
        """(int, int) -> str. like get(y, x) but concatenate left and right
        parts. if name is an 'o', try to replace it to the right"""
        result = b''
        for i in itertools.count(0):
            ch = get(y, x - i)
            if not _isname(ch):
                break
            result = ch + result
        for i in itertools.count(1):
            ch = get(y, x + i)
            if not _isname(ch):
                break
            result += ch
        if result == b'o':
            # special handling, find the name to the right
            result = b''
            for i in itertools.count(2):
                ch = get(y, x + i)
                if ch == b' ' or ch in _pipechars:
                    if result or x + i >= len(lines[y]):
                        break
                else:
                    result += ch
            return result or b'o'
        return result

    def parents(y, x):
        """(int, int) -> [str]. follow the ASCII edges at given position,
        return a list of parents"""
        visited = {(y, x)}
        visit = []
        result = []

        def follow(y, x, expected):
            """conditionally append (y, x) to visit array, if it's a char
            in excepted. 'o' in expected means an '_isname' test.
            if '-' (or '+') is not in excepted, and get(y, x) is '-' (or '+'),
            the next line (y + 1, x) will be checked instead."""
            ch = get(y, x)
            if any(ch == c and c not in expected for c in (b'-', b'+')):
                y += 1
                return follow(y + 1, x, expected)
            if ch in expected or (b'o' in expected and _isname(ch)):
                visit.append((y, x))

        #  -o-  # starting point:
        #  /|\ # follow '-' (horizontally), and '/|\' (to the bottom)
        follow(y + 1, x, b'|')
        follow(y + 1, x - 1, b'/')
        follow(y + 1, x + 1, b'\\')
        follow(y, x - 1, b'-')
        follow(y, x + 1, b'-')

        while visit:
            y, x = visit.pop()
            if (y, x) in visited:
                continue
            visited.add((y, x))
            ch = get(y, x)
            if _isname(ch):
                result.append(getname(y, x))
                continue
            elif ch == b'|':
                follow(y + 1, x, b'/|o')
                follow(y + 1, x - 1, b'/')
                follow(y + 1, x + 1, b'\\')
            elif ch == b'+':
                follow(y, x - 1, b'-')
                follow(y, x + 1, b'-')
                follow(y + 1, x - 1, b'/')
                follow(y + 1, x + 1, b'\\')
                follow(y + 1, x, b'|')
            elif ch == b'\\':
                follow(y + 1, x + 1, b'\\|o')
            elif ch == b'/':
                follow(y + 1, x - 1, b'/|o')
            elif ch == b'-':
                follow(y, x - 1, b'-+o')
                follow(y, x + 1, b'-+o')
        return result

    for y, line in enumerate(lines):
        for x, ch in enumerate(pycompat.bytestr(line)):
            if ch == b'#':  # comment
                break
            if _isname(ch):
                edges[getname(y, x)] += parents(y, x)

    return dict(edges)

class simplefilectx(object):
    def __init__(self, path, data):
        self._data = data
        self._path = path

    def data(self):
        return self._data

    def filenode(self):
        return None

    def path(self):
        return self._path

    def renamed(self):
        return None

    def flags(self):
        return b''

class simplecommitctx(context.committablectx):
    def __init__(self, repo, name, parentctxs, added):
        opts = {
            'changes': scmutil.status([], list(added), [], [], [], [], []),
            'date': b'0 0',
            'extra': {b'branch': b'default'},
        }
        super(simplecommitctx, self).__init__(self, name, **opts)
        self._repo = repo
        self._added = added
        self._parents = parentctxs
        while len(self._parents) < 2:
            self._parents.append(repo[node.nullid])

    def filectx(self, key):
        return simplefilectx(key, self._added[key])

    def commit(self):
        return self._repo.commitctx(self)

def _walkgraph(edges):
    """yield node, parents in topologically order"""
    visible = set(edges.keys())
    remaining = {}  # {str: [str]}
    for k, vs in edges.items():
        for v in vs:
            if v not in remaining:
                remaining[v] = []
        remaining[k] = vs[:]
    while remaining:
        leafs = [k for k, v in remaining.items() if not v]
        if not leafs:
            raise error.Abort(_('the graph has cycles'))
        for leaf in sorted(leafs):
            if leaf in visible:
                yield leaf, edges[leaf]
            del remaining[leaf]
            for k, v in remaining.items():
                if leaf in v:
                    v.remove(leaf)

def _getcomments(text):
    """
    >>> [pycompat.sysstr(s) for s in _getcomments(br'''
    ...        G
    ...        |
    ...  I D C F   # split: B -> E, F, G
    ...   \ \| |   # replace: C -> D -> H
    ...    H B E   # prune: F, I
    ...     \|/
    ...      A
    ... ''')]
    ['split: B -> E, F, G', 'replace: C -> D -> H', 'prune: F, I']
    """
    for line in text.splitlines():
        if b' # ' not in line:
            continue
        yield line.split(b' # ', 1)[1].split(b' # ')[0].strip()

@command(b'debugdrawdag', [])
def debugdrawdag(ui, repo, **opts):
    """read an ASCII graph from stdin and create changesets

    The ASCII graph is like what :hg:`log -G` outputs, with each `o` replaced
    to the name of the node. The command will create dummy changesets and local
    tags with those names to make the dummy changesets easier to be referred
    to.

    If the name of a node is a single character 'o', It will be replaced by the
    word to the right. This makes it easier to reuse
    :hg:`log -G -T '{desc}'` outputs.

    For root (no parents) nodes, revset can be used to query existing repo.
    Note that the revset cannot have confusing characters which can be seen as
    the part of the graph edges, like `|/+-\`.
    """
    text = ui.fin.read()

    # parse the graph and make sure len(parents) <= 2 for each node
    edges = _parseasciigraph(text)
    for k, v in edges.items():
        if len(v) > 2:
            raise error.Abort(_('%s: too many parents: %s')
                              % (k, b' '.join(v)))

    # parse comments to get extra file content instructions
    files = collections.defaultdict(dict) # {(name, path): content}
    comments = list(_getcomments(text))
    filere = re.compile(br'^(\w+)/([\w/]+)\s*=\s*(.*)$', re.M)
    for name, path, content in filere.findall(b'\n'.join(comments)):
        files[name][path] = content.replace(br'\n', b'\n')

    committed = {None: node.nullid}  # {name: node}

    # for leaf nodes, try to find existing nodes in repo
    for name, parents in edges.items():
        if len(parents) == 0:
            try:
                committed[name] = scmutil.revsingle(repo, name)
            except error.RepoLookupError:
                pass

    # commit in topological order
    for name, parents in _walkgraph(edges):
        if name in committed:
            continue
        pctxs = [repo[committed[n]] for n in parents]
        pctxs.sort(key=lambda c: c.node())
        added = {}
        if len(parents) > 1:
            # If it's a merge, take the files and contents from the parents
            for f in pctxs[1].manifest():
                if f not in pctxs[0].manifest():
                    added[f] = pctxs[1][f].data()
        else:
            # If it's not a merge, add a single file
            added[name] = name
        # add extra file contents in comments
        for path, content in files.get(name, {}).items():
            added[path] = content
        ctx = simplecommitctx(repo, name, pctxs, added)
        n = ctx.commit()
        committed[name] = n
        tagsmod.tag(repo, [name], n, message=None, user=None, date=None,
                    local=True)

    # handle special comments
    with repo.wlock(), repo.lock(), repo.transaction(b'drawdag'):
        getctx = lambda x: repo.unfiltered()[committed[x.strip()]]
        for comment in comments:
            rels = [] # obsolete relationships
            args = comment.split(b':', 1)
            if len(args) <= 1:
                continue

            cmd = args[0].strip()
            arg = args[1].strip()

            if cmd in (b'replace', b'rebase', b'amend'):
                nodes = [getctx(m) for m in arg.split(b'->')]
                for i in range(len(nodes) - 1):
                    rels.append((nodes[i], (nodes[i + 1],)))
            elif cmd in (b'split',):
                pre, succs = arg.split(b'->')
                succs = succs.split(b',')
                rels.append((getctx(pre), (getctx(s) for s in succs)))
            elif cmd in (b'prune',):
                for n in arg.split(b','):
                    rels.append((getctx(n), ()))
            if rels:
                obsolete.createmarkers(repo, rels, date=(0, 0), operation=cmd)
