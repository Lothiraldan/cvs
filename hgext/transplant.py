# Patch transplanting extension for Mercurial
#
# Copyright 2006, 2007 Brendan Cully <brendan@kublai.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from mercurial.i18n import _
import os, tempfile
from mercurial import bundlerepo, changegroup, cmdutil, commands, hg, merge
from mercurial import patch, revlog, util

'''patch transplanting tool

This extension allows you to transplant patches from another branch.

Transplanted patches are recorded in .hg/transplant/transplants, as a map
from a changeset hash to its hash in the source repository.
'''

class transplantentry:
    def __init__(self, lnode, rnode):
        self.lnode = lnode
        self.rnode = rnode

class transplants:
    def __init__(self, path=None, transplantfile=None, opener=None):
        self.path = path
        self.transplantfile = transplantfile
        self.opener = opener

        if not opener:
            self.opener = util.opener(self.path)
        self.transplants = []
        self.dirty = False
        self.read()

    def read(self):
        abspath = os.path.join(self.path, self.transplantfile)
        if self.transplantfile and os.path.exists(abspath):
            for line in self.opener(self.transplantfile).read().splitlines():
                lnode, rnode = map(revlog.bin, line.split(':'))
                self.transplants.append(transplantentry(lnode, rnode))

    def write(self):
        if self.dirty and self.transplantfile:
            if not os.path.isdir(self.path):
                os.mkdir(self.path)
            fp = self.opener(self.transplantfile, 'w')
            for c in self.transplants:
                l, r = map(revlog.hex, (c.lnode, c.rnode))
                fp.write(l + ':' + r + '\n')
            fp.close()
        self.dirty = False

    def get(self, rnode):
        return [t for t in self.transplants if t.rnode == rnode]

    def set(self, lnode, rnode):
        self.transplants.append(transplantentry(lnode, rnode))
        self.dirty = True

    def remove(self, transplant):
        del self.transplants[self.transplants.index(transplant)]
        self.dirty = True

class transplanter:
    def __init__(self, ui, repo):
        self.ui = ui
        self.path = repo.join('transplant')
        self.opener = util.opener(self.path)
        self.transplants = transplants(self.path, 'transplants', opener=self.opener)

    def applied(self, repo, node, parent):
        '''returns True if a node is already an ancestor of parent
        or has already been transplanted'''
        if hasnode(repo, node):
            if node in repo.changelog.reachable(parent, stop=node):
                return True
        for t in self.transplants.get(node):
            # it might have been stripped
            if not hasnode(repo, t.lnode):
                self.transplants.remove(t)
                return False
            if t.lnode in repo.changelog.reachable(parent, stop=t.lnode):
                return True
        return False

    def apply(self, repo, source, revmap, merges, opts={}):
        '''apply the revisions in revmap one by one in revision order'''
        revs = revmap.keys()
        revs.sort()

        p1, p2 = repo.dirstate.parents()
        pulls = []
        diffopts = patch.diffopts(self.ui, opts)
        diffopts.git = True

        wlock = repo.wlock()
        lock = repo.lock()
        try:
            for rev in revs:
                node = revmap[rev]
                revstr = '%s:%s' % (rev, revlog.short(node))

                if self.applied(repo, node, p1):
                    self.ui.warn(_('skipping already applied revision %s\n') %
                                 revstr)
                    continue

                parents = source.changelog.parents(node)
                if not opts.get('filter'):
                    # If the changeset parent is the same as the wdir's parent,
                    # just pull it.
                    if parents[0] == p1:
                        pulls.append(node)
                        p1 = node
                        continue
                    if pulls:
                        if source != repo:
                            repo.pull(source, heads=pulls, lock=lock)
                        merge.update(repo, pulls[-1], False, False, None,
                                     wlock=wlock)
                        p1, p2 = repo.dirstate.parents()
                        pulls = []

                domerge = False
                if node in merges:
                    # pulling all the merge revs at once would mean we couldn't
                    # transplant after the latest even if transplants before them
                    # fail.
                    domerge = True
                    if not hasnode(repo, node):
                        repo.pull(source, heads=[node], lock=lock)

                if parents[1] != revlog.nullid:
                    self.ui.note(_('skipping merge changeset %s:%s\n')
                                 % (rev, revlog.short(node)))
                    patchfile = None
                else:
                    fd, patchfile = tempfile.mkstemp(prefix='hg-transplant-')
                    fp = os.fdopen(fd, 'w')
                    patch.diff(source, parents[0], node, fp=fp, opts=diffopts)
                    fp.close()

                del revmap[rev]
                if patchfile or domerge:
                    try:
                        n = self.applyone(repo, node, source.changelog.read(node),
                                          patchfile, merge=domerge,
                                          log=opts.get('log'),
                                          filter=opts.get('filter'),
                                          lock=lock, wlock=wlock)
                        if n and domerge:
                            self.ui.status(_('%s merged at %s\n') % (revstr,
                                      revlog.short(n)))
                        elif n:
                            self.ui.status(_('%s transplanted to %s\n') % (revlog.short(node),
                                                                       revlog.short(n)))
                    finally:
                        if patchfile:
                            os.unlink(patchfile)
            if pulls:
                repo.pull(source, heads=pulls, lock=lock)
                merge.update(repo, pulls[-1], False, False, None, wlock=wlock)
        finally:
            self.saveseries(revmap, merges)
            self.transplants.write()

    def filter(self, filter, changelog, patchfile):
        '''arbitrarily rewrite changeset before applying it'''

        self.ui.status('filtering %s\n' % patchfile)
        user, date, msg = (changelog[1], changelog[2], changelog[4])

        fd, headerfile = tempfile.mkstemp(prefix='hg-transplant-')
        fp = os.fdopen(fd, 'w')
        fp.write("# HG changeset patch\n")
        fp.write("# User %s\n" % user)
        fp.write("# Date %d %d\n" % date)
        fp.write(changelog[4])
        fp.close()

        try:
            util.system('%s %s %s' % (filter, util.shellquote(headerfile),
                                   util.shellquote(patchfile)),
                        environ={'HGUSER': changelog[1]},
                        onerr=util.Abort, errprefix=_('filter failed'))
            user, date, msg = self.parselog(file(headerfile))[1:4]
        finally:
            os.unlink(headerfile)

        return (user, date, msg)

    def applyone(self, repo, node, cl, patchfile, merge=False, log=False,
                 filter=None, lock=None, wlock=None):
        '''apply the patch in patchfile to the repository as a transplant'''
        (manifest, user, (time, timezone), files, message) = cl[:5]
        date = "%d %d" % (time, timezone)
        extra = {'transplant_source': node}
        if filter:
            (user, date, message) = self.filter(filter, cl, patchfile)

        if log:
            message += '\n(transplanted from %s)' % revlog.hex(node)

        self.ui.status(_('applying %s\n') % revlog.short(node))
        self.ui.note('%s %s\n%s\n' % (user, date, message))

        if not patchfile and not merge:
            raise util.Abort(_('can only omit patchfile if merging'))
        if patchfile:
            try:
                files = {}
                try:
                    fuzz = patch.patch(patchfile, self.ui, cwd=repo.root,
                                       files=files)
                    if not files:
                        self.ui.warn(_('%s: empty changeset') % revlog.hex(node))
                        return None
                finally:
                    files = patch.updatedir(self.ui, repo, files, wlock=wlock)
            except Exception, inst:
                if filter:
                    os.unlink(patchfile)
                seriespath = os.path.join(self.path, 'series')
                if os.path.exists(seriespath):
                    os.unlink(seriespath)
                p1 = repo.dirstate.parents()[0]
                p2 = node
                self.log(user, date, message, p1, p2, merge=merge)
                self.ui.write(str(inst) + '\n')
                raise util.Abort(_('Fix up the merge and run hg transplant --continue'))
        else:
            files = None
        if merge:
            p1, p2 = repo.dirstate.parents()
            repo.dirstate.setparents(p1, node)

        n = repo.commit(files, message, user, date, lock=lock, wlock=wlock,
                        extra=extra)
        if not merge:
            self.transplants.set(n, node)

        return n

    def resume(self, repo, source, opts=None):
        '''recover last transaction and apply remaining changesets'''
        if os.path.exists(os.path.join(self.path, 'journal')):
            n, node = self.recover(repo)
            self.ui.status(_('%s transplanted as %s\n') % (revlog.short(node),
                                                           revlog.short(n)))
        seriespath = os.path.join(self.path, 'series')
        if not os.path.exists(seriespath):
            self.transplants.write()
            return
        nodes, merges = self.readseries()
        revmap = {}
        for n in nodes:
            revmap[source.changelog.rev(n)] = n
        os.unlink(seriespath)

        self.apply(repo, source, revmap, merges, opts)

    def recover(self, repo):
        '''commit working directory using journal metadata'''
        node, user, date, message, parents = self.readlog()
        merge = len(parents) == 2

        if not user or not date or not message or not parents[0]:
            raise util.Abort(_('transplant log file is corrupt'))

        extra = {'transplant_source': node}
        wlock = repo.wlock()
        p1, p2 = repo.dirstate.parents()
        if p1 != parents[0]:
            raise util.Abort(_('working dir not at transplant parent %s') %
                             revlog.hex(parents[0]))
        if merge:
            repo.dirstate.setparents(p1, parents[1])
        n = repo.commit(None, message, user, date, wlock=wlock, extra=extra)
        if not n:
            raise util.Abort(_('commit failed'))
        if not merge:
            self.transplants.set(n, node)
        self.unlog()

        return n, node

    def readseries(self):
        nodes = []
        merges = []
        cur = nodes
        for line in self.opener('series').read().splitlines():
            if line.startswith('# Merges'):
                cur = merges
                continue
            cur.append(revlog.bin(line))

        return (nodes, merges)

    def saveseries(self, revmap, merges):
        if not revmap:
            return

        if not os.path.isdir(self.path):
            os.mkdir(self.path)
        series = self.opener('series', 'w')
        revs = revmap.keys()
        revs.sort()
        for rev in revs:
            series.write(revlog.hex(revmap[rev]) + '\n')
        if merges:
            series.write('# Merges\n')
            for m in merges:
                series.write(revlog.hex(m) + '\n')
        series.close()

    def parselog(self, fp):
        parents = []
        message = []
        node = revlog.nullid
        inmsg = False
        for line in fp.read().splitlines():
            if inmsg:
                message.append(line)
            elif line.startswith('# User '):
                user = line[7:]
            elif line.startswith('# Date '):
                date = line[7:]
            elif line.startswith('# Node ID '):
                node = revlog.bin(line[10:])
            elif line.startswith('# Parent '):
                parents.append(revlog.bin(line[9:]))
            elif not line.startswith('#'):
                inmsg = True
                message.append(line)
        return (node, user, date, '\n'.join(message), parents)

    def log(self, user, date, message, p1, p2, merge=False):
        '''journal changelog metadata for later recover'''

        if not os.path.isdir(self.path):
            os.mkdir(self.path)
        fp = self.opener('journal', 'w')
        fp.write('# User %s\n' % user)
        fp.write('# Date %s\n' % date)
        fp.write('# Node ID %s\n' % revlog.hex(p2))
        fp.write('# Parent ' + revlog.hex(p1) + '\n')
        if merge:
            fp.write('# Parent ' + revlog.hex(p2) + '\n')
        fp.write(message.rstrip() + '\n')
        fp.close()

    def readlog(self):
        return self.parselog(self.opener('journal'))

    def unlog(self):
        '''remove changelog journal'''
        absdst = os.path.join(self.path, 'journal')
        if os.path.exists(absdst):
            os.unlink(absdst)

    def transplantfilter(self, repo, source, root):
        def matchfn(node):
            if self.applied(repo, node, root):
                return False
            if source.changelog.parents(node)[1] != revlog.nullid:
                return False
            extra = source.changelog.read(node)[5]
            cnode = extra.get('transplant_source')
            if cnode and self.applied(repo, cnode, root):
                return False
            return True

        return matchfn

def hasnode(repo, node):
    try:
        return repo.changelog.rev(node) != None
    except revlog.RevlogError:
        return False

def browserevs(ui, repo, nodes, opts):
    '''interactively transplant changesets'''
    def browsehelp(ui):
        ui.write('y: transplant this changeset\n'
                 'n: skip this changeset\n'
                 'm: merge at this changeset\n'
                 'p: show patch\n'
                 'c: commit selected changesets\n'
                 'q: cancel transplant\n'
                 '?: show this help\n')

    displayer = cmdutil.show_changeset(ui, repo, opts)
    transplants = []
    merges = []
    for node in nodes:
        displayer.show(changenode=node)
        action = None
        while not action:
            action = ui.prompt(_('apply changeset? [ynmpcq?]:'))
            if action == '?':
                browsehelp(ui)
                action = None
            elif action == 'p':
                parent = repo.changelog.parents(node)[0]
                patch.diff(repo, parent, node)
                action = None
            elif action not in ('y', 'n', 'm', 'c', 'q'):
                ui.write('no such option\n')
                action = None
        if action == 'y':
            transplants.append(node)
        elif action == 'm':
            merges.append(node)
        elif action == 'c':
            break
        elif action == 'q':
            transplants = ()
            merges = ()
            break
    return (transplants, merges)

def transplant(ui, repo, *revs, **opts):
    '''transplant changesets from another branch

    Selected changesets will be applied on top of the current working
    directory with the log of the original changeset. If --log is
    specified, log messages will have a comment appended of the form:

    (transplanted from CHANGESETHASH)

    You can rewrite the changelog message with the --filter option.
    Its argument will be invoked with the current changelog message
    as $1 and the patch as $2.

    If --source is specified, selects changesets from the named
    repository. If --branch is specified, selects changesets from the
    branch holding the named revision, up to that revision. If --all
    is specified, all changesets on the branch will be transplanted,
    otherwise you will be prompted to select the changesets you want.

    hg transplant --branch REVISION --all will rebase the selected branch
    (up to the named revision) onto your current working directory.

    You can optionally mark selected transplanted changesets as
    merge changesets. You will not be prompted to transplant any
    ancestors of a merged transplant, and you can merge descendants
    of them normally instead of transplanting them.

    If no merges or revisions are provided, hg transplant will start
    an interactive changeset browser.

    If a changeset application fails, you can fix the merge by hand and
    then resume where you left off by calling hg transplant --continue.
    '''
    def getoneitem(opts, item, errmsg):
        val = opts.get(item)
        if val:
            if len(val) > 1:
                raise util.Abort(errmsg)
            else:
                return val[0]

    def getremotechanges(repo, url):
        sourcerepo = ui.expandpath(url)
        source = hg.repository(ui, sourcerepo)
        incoming = repo.findincoming(source, force=True)
        if not incoming:
            return (source, None, None)

        bundle = None
        if not source.local():
            cg = source.changegroup(incoming, 'incoming')
            bundle = changegroup.writebundle(cg, None, 'HG10UN')
            source = bundlerepo.bundlerepository(ui, repo.root, bundle)

        return (source, incoming, bundle)

    def incwalk(repo, incoming, branches, match=util.always):
        if not branches:
            branches=None
        for node in repo.changelog.nodesbetween(incoming, branches)[0]:
            if match(node):
                yield node

    def transplantwalk(repo, root, branches, match=util.always):
        if not branches:
            branches = repo.heads()
        ancestors = []
        for branch in branches:
            ancestors.append(repo.changelog.ancestor(root, branch))
        for node in repo.changelog.nodesbetween(ancestors, branches)[0]:
            if match(node):
                yield node

    def checkopts(opts, revs):
        if opts.get('continue'):
            if filter(lambda opt: opts.get(opt), ('branch', 'all', 'merge')):
                raise util.Abort(_('--continue is incompatible with branch, all or merge'))
            return
        if not (opts.get('source') or revs or
                opts.get('merge') or opts.get('branch')):
            raise util.Abort(_('no source URL, branch tag or revision list provided'))
        if opts.get('all'):
            if not opts.get('branch'):
                raise util.Abort(_('--all requires a branch revision'))
            if revs:
                raise util.Abort(_('--all is incompatible with a revision list'))

    checkopts(opts, revs)

    if not opts.get('log'):
        opts['log'] = ui.config('transplant', 'log')
    if not opts.get('filter'):
        opts['filter'] = ui.config('transplant', 'filter')

    tp = transplanter(ui, repo)

    p1, p2 = repo.dirstate.parents()
    if p1 == revlog.nullid:
        raise util.Abort(_('no revision checked out'))
    if not opts.get('continue'):
        if p2 != revlog.nullid:
            raise util.Abort(_('outstanding uncommitted merges'))
        m, a, r, d = repo.status()[:4]
        if m or a or r or d:
            raise util.Abort(_('outstanding local changes'))

    bundle = None
    source = opts.get('source')
    if source:
        (source, incoming, bundle) = getremotechanges(repo, source)
    else:
        source = repo

    try:
        if opts.get('continue'):
            tp.resume(repo, source, opts)
            return

        tf=tp.transplantfilter(repo, source, p1)
        if opts.get('prune'):
            prune = [source.lookup(r)
                     for r in cmdutil.revrange(source, opts.get('prune'))]
            matchfn = lambda x: tf(x) and x not in prune
        else:
            matchfn = tf
        branches = map(source.lookup, opts.get('branch', ()))
        merges = map(source.lookup, opts.get('merge', ()))
        revmap = {}
        if revs:
            for r in cmdutil.revrange(source, revs):
                revmap[int(r)] = source.lookup(r)
        elif opts.get('all') or not merges:
            if source != repo:
                alltransplants = incwalk(source, incoming, branches, match=matchfn)
            else:
                alltransplants = transplantwalk(source, p1, branches, match=matchfn)
            if opts.get('all'):
                revs = alltransplants
            else:
                revs, newmerges = browserevs(ui, source, alltransplants, opts)
                merges.extend(newmerges)
            for r in revs:
                revmap[source.changelog.rev(r)] = r
        for r in merges:
            revmap[source.changelog.rev(r)] = r

        revs = revmap.keys()
        revs.sort()
        pulls = []

        tp.apply(repo, source, revmap, merges, opts)
    finally:
        if bundle:
            source.close()
            os.unlink(bundle)

cmdtable = {
    "transplant":
        (transplant,
         [('s', 'source', '', _('pull patches from REPOSITORY')),
          ('b', 'branch', [], _('pull patches from branch BRANCH')),
          ('a', 'all', None, _('pull all changesets up to BRANCH')),
          ('p', 'prune', [], _('skip over REV')),
          ('m', 'merge', [], _('merge at REV')),
          ('', 'log', None, _('append transplant info to log message')),
          ('c', 'continue', None, _('continue last transplant session after repair')),
          ('', 'filter', '', _('filter changesets through FILTER'))],
         _('hg transplant [-s REPOSITORY] [-b BRANCH [-a]] [-p REV] [-m REV] [REV]...'))
}
