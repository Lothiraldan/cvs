# Mercurial extension to provide the 'hg bookmark' command
#
# Copyright 2008 David Soria Parra <dsp@php.net>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.
'''mercurial bookmarks

Mercurial bookmarks are local moveable pointers to changesets. Every bookmark
points to a changesets identified by it's hash. If you commit a changeset
that is based on a changeset that has a bookmark on it, the bookmark is forwarded
to the new changeset.

It is possible to use bookmark names in every revision lookup (e.g. hg merge, hg update)
'''
from mercurial.commands import templateopts, hex, short
from mercurial.i18n import _
from mercurial import cmdutil, util, commands, changelog
from mercurial.node import nullrev
from mercurial.repo import RepoError
import mercurial, mercurial.localrepo, mercurial.repair, os


def parse(repo):
    '''Parse .hg/bookmarks file and return a dictionary
    
    Bookmarks are stored as {HASH}\s{NAME}\n (localtags format) 
    values in the .hg/bookmarks file.
    They are read by the parse() method and returned as a dictionary with
    name => hash values.
    
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
    util.copyfile(repo.join('bookmarks'), repo.join('undo.bookmarks'))
    file = repo.opener('bookmarks', 'w+')
    for refspec, node in refs.items():
        file.write("%s %s\n" % (hex(node), refspec))
    file.close()

def bookmark(ui, repo, mark=None, rev=None, force=False, delete=False, move=None):
    '''mercurial bookmarks
    
    Bookmarks are pointer to certain commits that move when commiting.
    Bookmarks are local. They can be renamed, copied and deleted.
    It is possible to use bookmark names in 'hg merge' and 'hg update' to 
    update to a given bookmark.
    
    You can use 'hg bookmark [NAME]' to set a bookmark on the current tip
    with the given name. If you specify a second [NAME] the bookmark is
    set to the bookmark that has that name. You can also pass revision
    identifiers to set bookmarks too.
    '''
    hexfn = ui.debugflag and hex or short
    marks = parse(repo)
    cur   = repo.changectx('.').node()

    if move:
        if move not in marks:
            raise util.Abort(_("a bookmark of this name doesnot exists"))
        if mark in marks and not force:
            raise util.Abort(_("a bookmark of the same name already exists"))
        marks[mark] = marks[move]
        del marks[move]
        write(repo, marks)
        return
    
    if delete:
        if mark == None:
            raise util.Abort(_("bookmark name required"))
        if mark not in marks:
            raise util.Abort(_("a bookmark of this name does not exists"))
        del marks[mark]
        write(repo, marks)
        return

    if mark != None:
        if mark.strip().count("\n") > 0:
            raise Exception("bookmark cannot contain newlines")
        if mark in marks and not force:
            raise util.Abort(_("a bookmark of the same name already exists"))
        if ((mark in repo.branchtags() or mark == repo.dirstate.branch()) 
            and not force):
            raise util.Abort(_("a bookmark cannot have the name of an existing branch"))
        if rev:
            marks[mark] = repo.lookup(rev)
        else:
            marks[mark] = repo.changectx('.').node()
        write(repo, marks)
        return

    if mark == None:
        if len(marks) == 0:
            ui.status("no bookmarks set\n")
        else:
            for bmark, n in marks.iteritems():
                prefix = (n == cur) and '*' or ' '
                ui.write(" %s %-25s %d:%s\n" % (prefix, bmark, repo.changelog.rev(n), hexfn(n)))
        return

def _revstostrip(changelog, node):
    srev = changelog.rev(node)
    tostrip = [srev]
    saveheads = []
    for r in xrange(srev, changelog.rev(changelog.tip()) + 1):
        parents = changelog.parentrevs(r)
        if parents[0] in tostrip or parents[1] in tostrip:
            tostrip.append(r)
            if parents[1] != nullrev:
                for p in parents:
                    if p not in tostrip and p > striprev:
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
    result = oldstrip(ui, repo, node, backup)
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
            parents = repo.changelog.parents(node)
            marks = parse(repo)
            update = False
            for mark, n in marks.items():
                if n in parents:
                    marks[mark] = node
                    update = True
            if update:
                write(repo, marks)
            return node

        def addchangegroup(self, source, srctype, url, emptyok=False):
            try:
                onode = repo.changectx('.').node()
            except RepoError, inst:
                pass

            result = super(bookmark_repo, self).addchangegroup(source, srctype, url, emptyok)
            if result > 1:
                # We have more heads than before
                return result
            node = repo.changelog.tip()
            marks = parse(repo)
            update = False
            for mark, n in marks.items():
                if n == onode:
                    marks[mark] = node
                    update = True
            if update:
                write(repo, marks)
            return result

    repo.__class__ = bookmark_repo

cmdtable = {
    "bookmarks":
        (bookmark,
         [('f', 'force', False, _('force')),
          ('r', 'rev', '', _('revision')),
          ('d', 'delete', False, _('delete a given bookmark')),
          ('m', 'move', '', _('move a given bookmark'))],
         _('hg bookmarks [-d] [-m NAME] [-r NAME] [NAME]')),
}
