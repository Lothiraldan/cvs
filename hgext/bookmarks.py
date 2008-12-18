# Mercurial extension to provide the 'hg bookmark' command
#
# Copyright 2008 David Soria Parra <dsp@php.net>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

'''mercurial bookmarks

Mercurial bookmarks are local moveable pointers to changesets. Every
bookmark points to a changeset identified by its hash. If you commit a
changeset that is based on a changeset that has a bookmark on it, the
bookmark is forwarded to the new changeset.

It is possible to use bookmark names in every revision lookup (e.g. hg
merge, hg update).

The bookmark extension offers the possiblity to have a more git-like experience
by adding the following configuration option to your .hgrc:

[bookmarks]
track.current = True

This will cause bookmarks to track the bookmark that you are currently on, and
just updates it. This is similar to git's approach of branching.
'''

from mercurial.commands import templateopts, hex, short
from mercurial import extensions
from mercurial.i18n import _
from mercurial import cmdutil, util, commands, changelog
from mercurial.node import nullid, nullrev
from mercurial.repo import RepoError
import mercurial, mercurial.localrepo, mercurial.repair, os

def parse(repo):
    '''Parse .hg/bookmarks file and return a dictionary

    Bookmarks are stored as {HASH}\s{NAME}\n (localtags format) values
    in the .hg/bookmarks file. They are read by the parse() method and
    returned as a dictionary with name => hash values.

    The parsed dictionary is cached until a write() operation is done.
    '''
    try:
        if repo._bookmarks:
            return repo._bookmarks
        repo._bookmarks = {}
        for line in repo.opener('bookmarks'):
            sha, refspec = line.strip().split(' ', 1)
            repo._bookmarks[refspec] = repo.lookup(sha)
    except:
        pass
    return repo._bookmarks

def write(repo, refs):
    '''Write bookmarks

    Write the given bookmark => hash dictionary to the .hg/bookmarks file
    in a format equal to those of localtags.

    We also store a backup of the previous state in undo.bookmarks that
    can be copied back on rollback.
    '''
    if os.path.exists(repo.join('bookmarks')):
        util.copyfile(repo.join('bookmarks'), repo.join('undo.bookmarks'))
    if current(repo) not in refs:
        setcurrent(repo, None)
    file = repo.opener('bookmarks', 'w+')
    for refspec, node in refs.items():
        file.write("%s %s\n" % (hex(node), refspec))
    file.close()

def current(repo):
    '''Get the current bookmark

    If we use gittishsh branches we have a current bookmark that
    we are on. This function returns the name of the bookmark. It
    is stored in .hg/bookmarks.current
    '''
    if repo._bookmarkcurrent:
        return repo._bookmarkcurrent
    mark = None
    if os.path.exists(repo.join('bookmarks.current')):
        file = repo.opener('bookmarks.current')
        mark = file.readline()
        if mark == '':
            mark = None
        file.close()
    repo._bookmarkcurrent = mark
    return mark

def setcurrent(repo, mark):
    '''Set the name of the bookmark that we are currently on

    Set the name of the bookmark that we are on (hg update <bookmark>).
    The name is recoreded in .hg/bookmarks.current
    '''
    if current(repo) == mark:
        return

    refs = parse(repo)

    'do not update if we do update to an rev equal to the current bookmark'
    if (mark not in refs and
        current(repo) and refs[current(repo)] == repo.changectx('.').node()):
        return
    if mark not in refs:
        mark = ''
    file = repo.opener('bookmarks.current', 'w+')
    file.write(mark)
    file.close()
    repo._bookmarkcurrent = mark

def bookmark(ui, repo, mark=None, rev=None, force=False, delete=False, rename=None):
    '''mercurial bookmarks

    Bookmarks are pointers to certain commits that move when
    commiting. Bookmarks are local. They can be renamed, copied and
    deleted. It is possible to use bookmark names in 'hg merge' and 'hg
    update' to update to a given bookmark.

    You can use 'hg bookmark NAME' to set a bookmark on the current
    tip with the given name. If you specify a revision using -r REV
    (where REV may be an existing bookmark), the bookmark is set to
    that revision.
    '''
    hexfn = ui.debugflag and hex or short
    marks = parse(repo)
    cur   = repo.changectx('.').node()

    if rename:
        if rename not in marks:
            raise util.Abort(_("a bookmark of this name does not exist"))
        if mark in marks and not force:
            raise util.Abort(_("a bookmark of the same name already exists"))
        if mark is None:
            raise util.Abort(_("new bookmark name required"))
        marks[mark] = marks[rename]
        del marks[rename]
        if current(repo) == rename:
            setcurrent(repo, mark)
        write(repo, marks)
        return

    if delete:
        if mark == None:
            raise util.Abort(_("bookmark name required"))
        if mark not in marks:
            raise util.Abort(_("a bookmark of this name does not exist"))
        del marks[mark]
        write(repo, marks)
        return

    if mark != None:
        if "\n" in mark:
            raise util.Abort(_("bookmark name cannot contain newlines"))
        mark = mark.strip()
        if mark in marks and not force:
            raise util.Abort(_("a bookmark of the same name already exists"))
        if ((mark in repo.branchtags() or mark == repo.dirstate.branch())
            and not force):
            raise util.Abort(
                _("a bookmark cannot have the name of an existing branch"))
        if rev:
            marks[mark] = repo.lookup(rev)
        else:
            marks[mark] = repo.changectx('.').node()
        write(repo, marks)
        return

    if mark == None:
        if rev:
            raise util.Abort(_("bookmark name required"))
        if len(marks) == 0:
            ui.status("no bookmarks set\n")
        else:
            for bmark, n in marks.iteritems():
                if ui.configbool('bookmarks', 'track.current'):
                    prefix = (bmark == current(repo) and n == cur) and '*' or ' '
                else:
                    prefix = (n == cur) and '*' or ' '

                ui.write(" %s %-25s %d:%s\n" % (
                    prefix, bmark, repo.changelog.rev(n), hexfn(n)))
        return

def _revstostrip(changelog, node):
    srev = changelog.rev(node)
    tostrip = [srev]
    saveheads = []
    for r in xrange(srev, len(changelog)):
        parents = changelog.parentrevs(r)
        if parents[0] in tostrip or parents[1] in tostrip:
            tostrip.append(r)
            if parents[1] != nullrev:
                for p in parents:
                    if p not in tostrip and p > srev:
                        saveheads.append(p)
    return [r for r in tostrip if r not in saveheads]

def strip(ui, repo, node, backup="all"):
    """Strip bookmarks if revisions are stripped using
    the mercurial.strip method. This usually happens during
    qpush and qpop"""
    revisions = _revstostrip(repo.changelog, node)
    marks = parse(repo)
    update = []
    for mark, n in marks.items():
        if repo.changelog.rev(n) in revisions:
            update.append(mark)
    oldstrip(ui, repo, node, backup)
    if len(update) > 0:
        for m in update:
            marks[m] = repo.changectx('.').node()
        write(repo, marks)

oldstrip = mercurial.repair.strip
mercurial.repair.strip = strip

def reposetup(ui, repo):
    if not isinstance(repo, mercurial.localrepo.localrepository):
        return

    # init a bookmark cache as otherwise we would get a infinite reading
    # in lookup()
    repo._bookmarks = None
    repo._bookmarkcurrent = None

    class bookmark_repo(repo.__class__):
        def rollback(self):
            if os.path.exists(self.join('undo.bookmarks')):
                util.rename(self.join('undo.bookmarks'), self.join('bookmarks'))
            return super(bookmark_repo, self).rollback()

        def lookup(self, key):
            if self._bookmarks is None:
                self._bookmarks = parse(self)
            if key in self._bookmarks:
                key = self._bookmarks[key]
            return super(bookmark_repo, self).lookup(key)

        def commit(self, *k, **kw):
            """Add a revision to the repository and
            move the bookmark"""
            node  = super(bookmark_repo, self).commit(*k, **kw)
            if node == None:
                return None
            parents = repo.changelog.parents(node)
            if parents[1] == nullid:
                parents = (parents[0],)
            marks = parse(repo)
            update = False
            for mark, n in marks.items():
                if ui.configbool('bookmarks', 'track.current'):
                    if mark == current(repo) and n in parents:
                        marks[mark] = node
                        update = True
                else:
                    if n in parents:
                        marks[mark] = node
                        update = True
            if update:
                write(repo, marks)
            return node

        def addchangegroup(self, source, srctype, url, emptyok=False):
            parents = repo.dirstate.parents()

            result = super(bookmark_repo, self).addchangegroup(
                source, srctype, url, emptyok)
            if result > 1:
                # We have more heads than before
                return result
            node = repo.changelog.tip()
            marks = parse(repo)
            update = False
            for mark, n in marks.items():
                if n in parents:
                    marks[mark] = node
                    update = True
            if update:
                write(repo, marks)
            return result

        def tags(self):
            """Merge bookmarks with normal tags"""
            if self.tagscache:
                return self.tagscache

            tagscache = super(bookmark_repo, self).tags()
            tagscache.update(parse(repo))
            return tagscache

    repo.__class__ = bookmark_repo

def updatecurbookmark(orig, ui, repo, *args, **opts):
    '''Set the current bookmark

    If the user updates to a bookmark we update the .hg/bookmarks.current
    file.
    '''
    res = orig(ui, repo, *args, **opts)
    rev = opts['rev']
    if not rev and len(args) > 0:
        rev = args[0]
    setcurrent(repo, rev)
    return res

def uisetup(ui):
    'Replace push with a decorator to provide --non-bookmarked option'
    if ui.configbool('bookmarks', 'track.current'):
        extensions.wrapcommand(commands.table, 'update', updatecurbookmark)

cmdtable = {
    "bookmarks":
        (bookmark,
         [('f', 'force', False, _('force')),
          ('r', 'rev', '', _('revision')),
          ('d', 'delete', False, _('delete a given bookmark')),
          ('m', 'rename', '', _('rename a given bookmark'))],
         _('hg bookmarks [-d] [-m NAME] [-r NAME] [NAME]')),
}
