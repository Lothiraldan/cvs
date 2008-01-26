# convcmd - convert extension commands definition
#
# Copyright 2005-2007 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from common import NoRepo, SKIPREV, converter_source, converter_sink
from cvs import convert_cvs
from darcs import darcs_source
from git import convert_git
from hg import mercurial_source, mercurial_sink
from subversion import svn_source, debugsvnlog
import filemap

import os, shutil
from mercurial import hg, util
from mercurial.i18n import _

source_converters = [
    ('cvs', convert_cvs),
    ('git', convert_git),
    ('svn', svn_source),
    ('hg', mercurial_source),
    ('darcs', darcs_source),
    ]

sink_converters = [
    ('hg', mercurial_sink),
    ]

def convertsource(ui, path, type, rev):
    exceptions = []
    for name, source in source_converters:
        try:
            if not type or name == type:
                return source(ui, path, rev)
        except NoRepo, inst:
            exceptions.append(inst)
    if not ui.quiet:
        for inst in exceptions:
            ui.write(_("%s\n") % inst)
    raise util.Abort('%s: unknown repository type' % path)

def convertsink(ui, path, type):
    for name, sink in sink_converters:
        try:
            if not type or name == type:
                return sink(ui, path)
        except NoRepo, inst:
            ui.note(_("convert: %s\n") % inst)
    raise util.Abort('%s: unknown repository type' % path)

class converter(object):
    def __init__(self, ui, source, dest, revmapfile, opts):

        self.source = source
        self.dest = dest
        self.ui = ui
        self.opts = opts
        self.commitcache = {}
        self.revmapfile = revmapfile
        self.revmapfilefd = None
        self.authors = {}
        self.authorfile = None

        self.maporder = []
        self.map = {}
        try:
            origrevmapfile = open(self.revmapfile, 'r')
            for l in origrevmapfile:
                sv, dv = l[:-1].split()
                if sv not in self.map:
                    self.maporder.append(sv)
                self.map[sv] = dv
            origrevmapfile.close()
        except IOError:
            pass

        # Read first the dst author map if any
        authorfile = self.dest.authorfile()
        if authorfile and os.path.exists(authorfile):
            self.readauthormap(authorfile)
        # Extend/Override with new author map if necessary
        if opts.get('authors'):
            self.readauthormap(opts.get('authors'))
            self.authorfile = self.dest.authorfile()

    def walktree(self, heads):
        '''Return a mapping that identifies the uncommitted parents of every
        uncommitted changeset.'''
        visit = heads
        known = {}
        parents = {}
        while visit:
            n = visit.pop(0)
            if n in known or n in self.map: continue
            known[n] = 1
            commit = self.cachecommit(n)
            parents[n] = []
            for p in commit.parents:
                parents[n].append(p)
                visit.append(p)

        return parents

    def toposort(self, parents):
        '''Return an ordering such that every uncommitted changeset is
        preceeded by all its uncommitted ancestors.'''
        visit = parents.keys()
        seen = {}
        children = {}

        while visit:
            n = visit.pop(0)
            if n in seen: continue
            seen[n] = 1
            # Ensure that nodes without parents are present in the 'children'
            # mapping.
            children.setdefault(n, [])
            for p in parents[n]:
                if not p in self.map:
                    visit.append(p)
                children.setdefault(p, []).append(n)

        s = []
        removed = {}
        visit = children.keys()
        while visit:
            n = visit.pop(0)
            if n in removed: continue
            dep = 0
            if n in parents:
                for p in parents[n]:
                    if p in self.map: continue
                    if p not in removed:
                        # we're still dependent
                        visit.append(n)
                        dep = 1
                        break

            if not dep:
                # all n's parents are in the list
                removed[n] = 1
                if n not in self.map:
                    s.append(n)
                if n in children:
                    for c in children[n]:
                        visit.insert(0, c)

        if self.opts.get('datesort'):
            depth = {}
            for n in s:
                depth[n] = 0
                pl = [p for p in self.commitcache[n].parents
                      if p not in self.map]
                if pl:
                    depth[n] = max([depth[p] for p in pl]) + 1

            s = [(depth[n], self.commitcache[n].date, n) for n in s]
            s.sort()
            s = [e[2] for e in s]

        return s

    def mapentry(self, src, dst):
        if self.revmapfilefd is None:
            try:
                self.revmapfilefd = open(self.revmapfile, "a")
            except IOError, (errno, strerror):
                raise util.Abort("Could not open map file %s: %s, %s\n" % (self.revmapfile, errno, strerror))
        self.map[src] = dst
        self.revmapfilefd.write("%s %s\n" % (src, dst))
        self.revmapfilefd.flush()

    def writeauthormap(self):
        authorfile = self.authorfile
        if authorfile:
           self.ui.status('Writing author map file %s\n' % authorfile)
           ofile = open(authorfile, 'w+')
           for author in self.authors:
               ofile.write("%s=%s\n" % (author, self.authors[author]))
           ofile.close()

    def readauthormap(self, authorfile):
        afile = open(authorfile, 'r')
        for line in afile:
            try:
                srcauthor = line.split('=')[0].strip()
                dstauthor = line.split('=')[1].strip()
                if srcauthor in self.authors and dstauthor != self.authors[srcauthor]:
                    self.ui.status(
                        'Overriding mapping for author %s, was %s, will be %s\n'
                        % (srcauthor, self.authors[srcauthor], dstauthor))
                else:
                    self.ui.debug('Mapping author %s to %s\n'
                                  % (srcauthor, dstauthor))
                    self.authors[srcauthor] = dstauthor
            except IndexError:
                self.ui.warn(
                    'Ignoring bad line in author file map %s: %s\n'
                    % (authorfile, line))
        afile.close()

    def cachecommit(self, rev):
        commit = self.source.getcommit(rev)
        commit.author = self.authors.get(commit.author, commit.author)
        self.commitcache[rev] = commit
        return commit

    def copy(self, rev):
        commit = self.commitcache[rev]
        do_copies = hasattr(self.dest, 'copyfile')
        filenames = []

        changes = self.source.getchanges(rev)
        if isinstance(changes, basestring):
            if changes == SKIPREV:
                dest = SKIPREV
            else:
                dest = self.map[changes]
            self.mapentry(rev, dest)
            return
        files, copies = changes
        pbranches = []
        if commit.parents:
            for prev in commit.parents:
                if prev not in self.commitcache:
                    self.cachecommit(prev)
                pbranches.append((self.map[prev], 
                                  self.commitcache[prev].branch))
        self.dest.setbranch(commit.branch, pbranches)
        for f, v in files:
            filenames.append(f)
            try:
                data = self.source.getfile(f, v)
            except IOError, inst:
                self.dest.delfile(f)
            else:
                e = self.source.getmode(f, v)
                self.dest.putfile(f, e, data)
                if do_copies:
                    if f in copies:
                        copyf = copies[f]
                        # Merely marks that a copy happened.
                        self.dest.copyfile(copyf, f)

        parents = [b[0] for b in pbranches]
        newnode = self.dest.putcommit(filenames, parents, commit)
        self.mapentry(rev, newnode)

    def convert(self):
        try:
            self.source.before()
            self.dest.before()
            self.source.setrevmap(self.map, self.maporder)
            self.ui.status("scanning source...\n")
            heads = self.source.getheads()
            parents = self.walktree(heads)
            self.ui.status("sorting...\n")
            t = self.toposort(parents)
            num = len(t)
            c = None

            self.ui.status("converting...\n")
            for c in t:
                num -= 1
                desc = self.commitcache[c].desc
                if "\n" in desc:
                    desc = desc.splitlines()[0]
                self.ui.status("%d %s\n" % (num, desc))
                self.copy(c)

            tags = self.source.gettags()
            ctags = {}
            for k in tags:
                v = tags[k]
                if self.map.get(v, SKIPREV) != SKIPREV:
                    ctags[k] = self.map[v]

            if c and ctags:
                nrev = self.dest.puttags(ctags)
                # write another hash correspondence to override the previous
                # one so we don't end up with extra tag heads
                if nrev:
                    self.mapentry(c, nrev)

            self.writeauthormap()
        finally:
            self.cleanup()

    def cleanup(self):
        try:
            self.dest.after()
        finally:
            self.source.after()
        if self.revmapfilefd:
            self.revmapfilefd.close()

def convert(ui, src, dest=None, revmapfile=None, **opts):
    util._encoding = 'UTF-8'

    if not dest:
        dest = hg.defaultdest(src) + "-hg"
        ui.status("assuming destination %s\n" % dest)

    destc = convertsink(ui, dest, opts.get('dest_type'))

    try:
        srcc = convertsource(ui, src, opts.get('source_type'),
                             opts.get('rev'))
    except Exception:
        for path in destc.created:
            shutil.rmtree(path, True)
        raise

    fmap = opts.get('filemap')
    if fmap:
        srcc = filemap.filemap_source(ui, srcc, fmap)
        destc.setfilemapmode(True)

    if not revmapfile:
        try:
            revmapfile = destc.revmapfile()
        except:
            revmapfile = os.path.join(destc, "map")

    c = converter(ui, srcc, destc, revmapfile, opts)
    c.convert()

