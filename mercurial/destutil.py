# destutil.py - Mercurial utility function for command destination
#
#  Copyright Matt Mackall <mpm@selenic.com> and other
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from __future__ import absolute_import

from .i18n import _
from . import (
    bookmarks,
    error,
    obsolete,
)

def _destupdatevalidate(repo, rev, clean, check):
    """validate that the destination comply to various rules

    This exists as its own function to help wrapping from extensions."""
    wc = repo[None]
    p1 = wc.p1()
    if not clean:
        # Check that the update is linear.
        #
        # Mercurial do not allow update-merge for non linear pattern
        # (that would be technically possible but was considered too confusing
        # for user a long time ago)
        #
        # See mercurial.merge.update for details
        if p1.rev() not in repo.changelog.ancestors([rev], inclusive=True):
            dirty = wc.dirty(missing=True)
            foreground = obsolete.foreground(repo, [p1.node()])
            if not repo[rev].node() in foreground:
                if dirty:
                    msg = _("uncommitted changes")
                    hint = _("commit and merge, or update --clean to"
                             " discard changes")
                    raise error.UpdateAbort(msg, hint=hint)
                elif not check:  # destination is not a descendant.
                    msg = _("not a linear update")
                    hint = _("merge or update --check to force update")
                    raise error.UpdateAbort(msg, hint=hint)

def _destupdateobs(repo, clean, check):
    """decide of an update destination from obsolescence markers"""
    node = None
    wc = repo[None]
    p1 = wc.p1()
    movemark = None

    if p1.obsolete() and not p1.children():
        # allow updating to successors
        successors = obsolete.successorssets(repo, p1.node())

        # behavior of certain cases is as follows,
        #
        # divergent changesets: update to highest rev, similar to what
        #     is currently done when there are more than one head
        #     (i.e. 'tip')
        #
        # replaced changesets: same as divergent except we know there
        # is no conflict
        #
        # pruned changeset: no update is done; though, we could
        #     consider updating to the first non-obsolete parent,
        #     similar to what is current done for 'hg prune'

        if successors:
            # flatten the list here handles both divergent (len > 1)
            # and the usual case (len = 1)
            successors = [n for sub in successors for n in sub]

            # get the max revision for the given successors set,
            # i.e. the 'tip' of a set
            node = repo.revs('max(%ln)', successors).first()
            if bookmarks.isactivewdirparent(repo):
                movemark = repo['.'].node()
    return node, movemark, None

def _destupdatebook(repo, clean, check):
    """decide on an update destination from active bookmark"""
    # we also move the active bookmark, if any
    activemark = None
    node, movemark = bookmarks.calculateupdate(repo.ui, repo, None)
    if node is not None:
        activemark = node
    return node, movemark, activemark

def _destupdatebranch(repo, clean, check):
    """decide on an update destination from current branch"""
    wc = repo[None]
    movemark = node = None
    try:
        node = repo.revs('max(.::(head() and branch(%s)))'
                         , wc.branch()).first()
        if bookmarks.isactivewdirparent(repo):
            movemark = repo['.'].node()
    except error.RepoLookupError:
        if wc.branch() == 'default': # no default branch!
            node = repo.lookup('tip') # update to tip
        else:
            raise error.Abort(_("branch %s not found") % wc.branch())
    return node, movemark, None

# order in which each step should be evalutated
# steps are run until one finds a destination
destupdatesteps = ['evolution', 'bookmark', 'branch']
# mapping to ease extension overriding steps.
destupdatestepmap = {'evolution': _destupdateobs,
                     'bookmark': _destupdatebook,
                     'branch': _destupdatebranch,
                     }

def destupdate(repo, clean=False, check=False):
    """destination for bare update operation

    return (rev, movemark, activemark)

    - rev: the revision to update to,
    - movemark: node to move the active bookmark from
                (cf bookmark.calculate update),
    - activemark: a bookmark to activate at the end of the update.
    """
    node = movemark = activemark = None

    for step in destupdatesteps:
        node, movemark, activemark = destupdatestepmap[step](repo, clean, check)
        if node is not None:
            break
    rev = repo[node].rev()

    _destupdatevalidate(repo, rev, clean, check)

    return rev, movemark, activemark

msgdestmerge = {
    # too many matching divergent bookmark
    'toomanybookmarks':
        {'merge':
            (_("multiple matching bookmarks to merge -"
               " please merge with an explicit rev or bookmark"),
             _("run 'hg heads' to see all heads")),
        },
    # no other matching divergent bookmark
    'nootherbookmarks':
        {'merge':
            (_("no matching bookmark to merge - "
               "please merge with an explicit rev or bookmark"),
             _("run 'hg heads' to see all heads")),
        },
    # branch have too many unbookmarked heads, no obvious destination
    'toomanyheads':
        {'merge':
            (_("branch '%s' has %d heads - please merge with an explicit rev"),
             _("run 'hg heads .' to see heads")),
        },
    # branch have no other unbookmarked heads
    'bookmarkedheads':
        {'merge':
            (_("heads are bookmarked - please merge with an explicit rev"),
             _("run 'hg heads' to see all heads")),
        },
    # branch have just a single heads, but there is other branches
    'nootherbranchheads':
        {'merge':
            (_("branch '%s' has one head - please merge with an explicit rev"),
             _("run 'hg heads' to see all heads")),
        },
    # repository have a single head
    'nootherheads':
            {'merge':
                (_('nothing to merge'),
         None),
        },
    # repository have a single head and we are not on it
    'nootherheadsbehind':
        {'merge':
            (_('nothing to merge'),
             _("use 'hg update' instead")),
        },
    # We are not on a head
    'notatheads':
        {'merge':
            (_('working directory not at a head revision'),
             _("use 'hg update' or merge with an explicit revision"))
        },
    }

def _destmergebook(repo, action='merge'):
    """find merge destination in the active bookmark case"""
    node = None
    bmheads = repo.bookmarkheads(repo._activebookmark)
    curhead = repo[repo._activebookmark].node()
    if len(bmheads) == 2:
        if curhead == bmheads[0]:
            node = bmheads[1]
        else:
            node = bmheads[0]
    elif len(bmheads) > 2:
        msg, hint = msgdestmerge['toomanybookmarks'][action]
        raise error.Abort(msg, hint=hint)
    elif len(bmheads) <= 1:
        msg, hint = msgdestmerge['nootherbookmarks'][action]
        raise error.Abort(msg, hint=hint)
    assert node is not None
    return node

def _destmergebranch(repo, action='merge'):
    """find merge destination based on branch heads"""
    node = None
    parent = repo.dirstate.p1()
    branch = repo.dirstate.branch()
    bheads = repo.branchheads(branch)
    nbhs = [bh for bh in bheads if not repo[bh].bookmarks()]

    if parent not in bheads:
        # Case A: working copy if not on a head.
        #
        # This is probably a user mistake We bailout pointing at 'hg update'
        if len(repo.heads()) <= 1:
            msg, hint = msgdestmerge['nootherheadsbehind'][action]
        else:
            msg, hint = msgdestmerge['notatheads'][action]
        raise error.Abort(msg, hint=hint)
    elif len(nbhs) > 2:
        # Case B: There is more than 2 anonymous heads
        #
        # This means that there will be more than 1 candidate. This is
        # ambiguous. We abort asking the user to pick as explicit destination
        # instead.
        msg, hint = msgdestmerge['toomanyheads'][action]
        msg %= (branch, len(bheads))
        raise error.Abort(msg, hint=hint)
    elif len(nbhs) <= 1:
        # Case B: There is no other anonymous head that the one we are one
        #
        # This means that there is no natural candidate to merge with.
        # We abort, with various messages for various cases.
        if len(bheads) > 1:
            msg, hint = msgdestmerge['bookmarkedheads'][action]
        elif len(repo.heads()) > 1:
            msg, hint = msgdestmerge['nootherbranchheads'][action]
            msg %= branch
        else:
            msg, hint = msgdestmerge['nootherheads'][action]
        raise error.Abort(msg, hint=hint)
    elif parent == nbhs[0]:
        node = nbhs[-1]
    else:
        node = nbhs[0]
    assert node is not None
    return node

def destmerge(repo, action='merge'):
    """return the default destination for a merge

    (or raise exception about why it can't pick one)

    :action: the action being performed, controls emitted error message
    """
    if repo._activebookmark:
        node = _destmergebook(repo, action=action)
    else:
        node = _destmergebranch(repo, action=action)
    return repo[node].rev()

histeditdefaultrevset = 'reverse(only(.) and not public() and not ::merge())'

def desthistedit(ui, repo):
    """Default base revision to edit for `hg histedit`."""
    # Avoid cycle: scmutil -> revset -> destutil
    from . import scmutil

    default = ui.config('histedit', 'defaultrev', histeditdefaultrevset)
    if default:
        revs = scmutil.revrange(repo, [default])
        if revs:
            # The revset supplied by the user may not be in ascending order nor
            # take the first revision. So do this manually.
            revs.sort()
            return revs.first()

    return None

def _statusotherbook(ui, repo):
    bmheads = repo.bookmarkheads(repo._activebookmark)
    curhead = repo[repo._activebookmark].node()
    if repo.revs('%n and parents()', curhead):
        # we are on the active bookmark
        bmheads = [b for b in bmheads if curhead != b]
        if bmheads:
            msg = _('%i other divergent bookmarks for "%s"\n')
            ui.status(msg % (len(bmheads), repo._activebookmark))

def _statusotherbranchheads(ui, repo):
    currentbranch = repo.dirstate.branch()
    heads = repo.branchheads(currentbranch)
    l = len(heads)
    if repo.revs('%ln and parents()', heads):
        # we are on a head
        heads = repo.revs('%ln - parents()', heads)
        if heads and l != len(heads):
            ui.status(_('%i other heads for branch "%s"\n') %
                      (len(heads), currentbranch))

def statusotherdests(ui, repo):
    """Print message about other head"""
    # XXX we should probably include a hint:
    # - about what to do
    # - how to see such heads
    if repo._activebookmark:
        _statusotherbook(ui, repo)
    else:
        _statusotherbranchheads(ui, repo)
