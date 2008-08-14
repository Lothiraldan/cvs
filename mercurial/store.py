# store.py - repository store handling for Mercurial
#
# Copyright 2008 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

import os, stat, osutil, util

def _buildencodefun():
    e = '_'
    win_reserved = [ord(x) for x in '\\:*?"<>|']
    cmap = dict([ (chr(x), chr(x)) for x in xrange(127) ])
    for x in (range(32) + range(126, 256) + win_reserved):
        cmap[chr(x)] = "~%02x" % x
    for x in range(ord("A"), ord("Z")+1) + [ord(e)]:
        cmap[chr(x)] = e + chr(x).lower()
    dmap = {}
    for k, v in cmap.iteritems():
        dmap[v] = k
    def decode(s):
        i = 0
        while i < len(s):
            for l in xrange(1, 4):
                try:
                    yield dmap[s[i:i+l]]
                    i += l
                    break
                except KeyError:
                    pass
            else:
                raise KeyError
    return (lambda s: "".join([cmap[c] for c in s]),
            lambda s: "".join(list(decode(s))))

encodefilename, decodefilename = _buildencodefun()

def _calcmode(path):
    try:
        # files in .hg/ will be created using this mode
        mode = os.stat(path).st_mode
            # avoid some useless chmods
        if (0777 & ~util._umask) == (0777 & mode):
            mode = None
    except OSError:
        mode = None
    return mode

_data = 'data 00manifest.d 00manifest.i 00changelog.d  00changelog.i'

class basicstore:
    '''base class for local repository stores'''
    def __init__(self, path, opener):
        self.path = path
        self.createmode = _calcmode(path)
        self.opener = opener(self.path)
        self.opener.createmode = self.createmode

    def join(self, f):
        return os.path.join(self.path, f)

    def _walk(self, relpath, recurse):
        '''yields (unencoded, encoded, size)'''
        path = os.path.join(self.path, relpath)
        striplen = len(self.path) + len(os.sep)
        prefix = path[striplen:]
        l = []
        if os.path.isdir(path):
            visit = [path]
            while visit:
                p = visit.pop()
                for f, kind, st in osutil.listdir(p, stat=True):
                    fp = os.path.join(p, f)
                    if kind == stat.S_IFREG and f[-2:] in ('.d', '.i'):
                        n = util.pconvert(fp[striplen:])
                        l.append((n, n, st.st_size))
                    elif kind == stat.S_IFDIR and recurse:
                        visit.append(fp)
        return util.sort(l)

    def datafiles(self):
        return self._walk('data', True)

    def walk(self):
        '''yields (unencoded, encoded, size)'''
        # yield data files first
        for x in self.datafiles():
            yield x
        # yield manifest before changelog
        meta = self._walk('', False)
        meta.reverse()
        for x in meta:
            yield x

    def copylist(self):
        return ['requires'] + _data.split()

class encodedstore(basicstore):
    def __init__(self, path, opener):
        self.path = os.path.join(path, 'store')
        self.createmode = _calcmode(self.path)
        op = opener(self.path)
        op.createmode = self.createmode
        self.opener = lambda f, *args, **kw: op(encodefilename(f), *args, **kw)

    def datafiles(self):
        for a, b, size in self._walk('data', True):
            try:
                a = decodefilename(a)
            except KeyError:
                a = None
            yield a, b, size

    def join(self, f):
        return os.path.join(self.path, encodefilename(f))

    def copylist(self):
        return (['requires', '00changelog.i'] +
                ['store/' + f for f in _data.split()])

def store(requirements, path, opener):
    if 'store' in requirements:
        return encodedstore(path, opener)
    return basicstore(path, opener)
