# histedit.py - interactive history editing for mercurial
#
# Copyright 2009 Augie Fackler <raf@durin42.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.
"""interactive history editing

With this extension installed, Mercurial gains one new command: histedit. Usage
is as follows, assuming the following history::

 @  3[tip]   7c2fd3b9020c   2009-04-27 18:04 -0500   durin42
 |    Add delta
 |
 o  2   030b686bedc4   2009-04-27 18:04 -0500   durin42
 |    Add gamma
 |
 o  1   c561b4e977df   2009-04-27 18:04 -0500   durin42
 |    Add beta
 |
 o  0   d8d2fcd0e319   2009-04-27 18:04 -0500   durin42
      Add alpha

If you were to run ``hg histedit c561b4e977df``, you would see the following
file open in your editor::

 pick c561b4e977df Add beta
 pick 030b686bedc4 Add gamma
 pick 7c2fd3b9020c Add delta

 # Edit history between 633536316234 and 7c2fd3b9020c
 #
 # Commands:
 #  p, pick = use commit
 #  e, edit = use commit, but stop for amending
 #  f, fold = use commit, but fold into previous commit (combines N and N-1)
 #  d, drop = remove commit from history
 #  m, mess = edit message without changing commit content
 #

In this file, lines beginning with ``#`` are ignored. You must specify a rule
for each revision in your history. For example, if you had meant to add gamma
before beta, and then wanted to add delta in the same revision as beta, you
would reorganize the file to look like this::

 pick 030b686bedc4 Add gamma
 pick c561b4e977df Add beta
 fold 7c2fd3b9020c Add delta

 # Edit history between 633536316234 and 7c2fd3b9020c
 #
 # Commands:
 #  p, pick = use commit
 #  e, edit = use commit, but stop for amending
 #  f, fold = use commit, but fold into previous commit (combines N and N-1)
 #  d, drop = remove commit from history
 #  m, mess = edit message without changing commit content
 #

At which point you close the editor and ``histedit`` starts working. When you
specify a ``fold`` operation, ``histedit`` will open an editor when it folds
those revisions together, offering you a chance to clean up the commit message::

 Add beta
 ***
 Add delta

Edit the commit message to your liking, then close the editor. For
this example, let's assume that the commit message was changed to
``Add beta and delta.`` After histedit has run and had a chance to
remove any old or temporary revisions it needed, the history looks
like this::

 @  2[tip]   989b4d060121   2009-04-27 18:04 -0500   durin42
 |    Add beta and delta.
 |
 o  1   081603921c3f   2009-04-27 18:04 -0500   durin42
 |    Add gamma
 |
 o  0   d8d2fcd0e319   2009-04-27 18:04 -0500   durin42
      Add alpha

Note that ``histedit`` does *not* remove any revisions (even its own temporary
ones) until after it has completed all the editing operations, so it will
probably perform several strip operations when it's done. For the above example,
it had to run strip twice. Strip can be slow depending on a variety of factors,
so you might need to be a little patient. You can choose to keep the original
revisions by passing the ``--keep`` flag.

The ``edit`` operation will drop you back to a command prompt,
allowing you to edit files freely, or even use ``hg record`` to commit
some changes as a separate commit. When you're done, any remaining
uncommitted changes will be committed as well. When done, run ``hg
histedit --continue`` to finish this step. You'll be prompted for a
new commit message, but the default commit message will be the
original message for the ``edit`` ed revision.

The ``message`` operation will give you a chance to revise a commit
message without changing the contents. It's a shortcut for doing
``edit`` immediately followed by `hg histedit --continue``.

If ``histedit`` encounters a conflict when moving a revision (while
handling ``pick`` or ``fold``), it'll stop in a similar manner to
``edit`` with the difference that it won't prompt you for a commit
message when done. If you decide at this point that you don't like how
much work it will be to rearrange history, or that you made a mistake,
you can use ``hg histedit --abort`` to abandon the new changes you
have made and return to the state before you attempted to edit your
history.

If we clone the example repository above and add three more changes, such that
we have the following history::

   @  6[tip]   038383181893   2009-04-27 18:04 -0500   stefan
   |    Add theta
   |
   o  5   140988835471   2009-04-27 18:04 -0500   stefan
   |    Add eta
   |
   o  4   122930637314   2009-04-27 18:04 -0500   stefan
   |    Add zeta
   |
   o  3   836302820282   2009-04-27 18:04 -0500   stefan
   |    Add epsilon
   |
   o  2   989b4d060121   2009-04-27 18:04 -0500   durin42
   |    Add beta and delta.
   |
   o  1   081603921c3f   2009-04-27 18:04 -0500   durin42
   |    Add gamma
   |
   o  0   d8d2fcd0e319   2009-04-27 18:04 -0500   durin42
        Add alpha

If you run ``hg histedit --outgoing`` on the clone then it is the same
as running ``hg histedit 836302820282``. If you need plan to push to a
repository that Mercurial does not detect to be related to the source
repo, you can add a ``--force`` option.
"""

try:
    import cPickle as pickle
except ImportError:
    import pickle
import os

from mercurial import bookmarks
from mercurial import cmdutil
from mercurial import discovery
from mercurial import error
from mercurial import copies
from mercurial import context
from mercurial import hg
from mercurial import lock as lockmod
from mercurial import node
from mercurial import repair
from mercurial import scmutil
from mercurial import util
from mercurial import merge as mergemod
from mercurial.i18n import _

cmdtable = {}
command = cmdutil.command(cmdtable)

testedwith = 'internal'

# i18n: command names and abbreviations must remain untranslated
editcomment = _("""# Edit history between %s and %s
#
# Commands:
#  p, pick = use commit
#  e, edit = use commit, but stop for amending
#  f, fold = use commit, but fold into previous commit (combines N and N-1)
#  d, drop = remove commit from history
#  m, mess = edit message without changing commit content
#
""")

def applychanges(ui, repo, ctx, opts):
    """Merge changeset from ctx (only) in the current working directory"""
    wcpar = repo.dirstate.parents()[0]
    if ctx.p1().node() == wcpar:
        # edition ar "in place" we do not need to make any merge,
        # just applies changes on parent for edition
        cmdutil.revert(ui, repo, ctx, (wcpar, node.nullid), all=True)
        stats = None
    else:
        try:
            # ui.forcemerge is an internal variable, do not document
            repo.ui.setconfig('ui', 'forcemerge', opts.get('tool', ''))
            stats = mergemod.update(repo, ctx.node(), True, True, False,
                                    ctx.p1().node())
        finally:
            repo.ui.setconfig('ui', 'forcemerge', '')
        repo.setparents(wcpar, node.nullid)
        repo.dirstate.write()
        # fix up dirstate for copies and renames
    cmdutil.duplicatecopies(repo, ctx.rev(), ctx.p1().rev())
    return stats

def collapse(repo, first, last, commitopts):
    """collapse the set of revisions from first to last as new one.

    Expected commit options are:
        - message
        - date
        - username
    Edition of commit message is trigered in all case.

    This function works in memory."""
    ctxs = list(repo.set('%d::%d', first, last))
    if not ctxs:
        return None
    base = first.parents()[0]

    # commit a new version of the old changeset, including the update
    # collect all files which might be affected
    files = set()
    for ctx in ctxs:
        files.update(ctx.files())

    # Recompute copies (avoid recording a -> b -> a)
    copied = copies.pathcopies(first, last)

    # prune files which were reverted by the updates
    def samefile(f):
        if f in last.manifest():
            a = last.filectx(f)
            if f in base.manifest():
                b = base.filectx(f)
                return (a.data() == b.data()
                        and a.flags() == b.flags())
            else:
                return False
        else:
            return f not in base.manifest()
    files = [f for f in files if not samefile(f)]
    # commit version of these files as defined by head
    headmf = last.manifest()
    def filectxfn(repo, ctx, path):
        if path in headmf:
            fctx = last[path]
            flags = fctx.flags()
            mctx = context.memfilectx(fctx.path(), fctx.data(),
                                      islink='l' in flags,
                                      isexec='x' in flags,
                                      copied=copied.get(path))
            return mctx
        raise IOError()

    if commitopts.get('message'):
        message = commitopts['message']
    else:
        message = first.description()
    user = commitopts.get('user')
    date = commitopts.get('date')
    extra = first.extra()

    parents = (first.p1().node(), first.p2().node())
    new = context.memctx(repo,
                         parents=parents,
                         text=message,
                         files=files,
                         filectxfn=filectxfn,
                         user=user,
                         date=date,
                         extra=extra)
    new._text = cmdutil.commitforceeditor(repo, new, [])
    return repo.commitctx(new)

def pick(ui, repo, ctx, ha, opts):
    oldctx = repo[ha]
    if oldctx.parents()[0] == ctx:
        ui.debug('node %s unchanged\n' % ha)
        return oldctx, [], [], []
    hg.update(repo, ctx.node())
    stats = applychanges(ui, repo, oldctx, opts)
    if stats and stats[3] > 0:
        raise util.Abort(_('Fix up the change and run '
                           'hg histedit --continue'))
    # drop the second merge parent
    n = repo.commit(text=oldctx.description(), user=oldctx.user(),
                    date=oldctx.date(), extra=oldctx.extra())
    if n is None:
        ui.warn(_('%s: empty changeset\n')
                     % node.hex(ha))
        return ctx, [], [], []
    return repo[n], [n], [oldctx.node()], []


def edit(ui, repo, ctx, ha, opts):
    oldctx = repo[ha]
    hg.update(repo, ctx.node())
    applychanges(ui, repo, oldctx, opts)
    raise util.Abort(_('Make changes as needed, you may commit or record as '
                       'needed now.\nWhen you are finished, run hg'
                       ' histedit --continue to resume.'))

def fold(ui, repo, ctx, ha, opts):
    oldctx = repo[ha]
    hg.update(repo, ctx.node())
    stats = applychanges(ui, repo, oldctx, opts)
    if stats and stats[3] > 0:
        raise util.Abort(_('Fix up the change and run '
                           'hg histedit --continue'))
    n = repo.commit(text='fold-temp-revision %s' % ha, user=oldctx.user(),
                    date=oldctx.date(), extra=oldctx.extra())
    if n is None:
        ui.warn(_('%s: empty changeset')
                     % node.hex(ha))
        return ctx, [], [], []
    return finishfold(ui, repo, ctx, oldctx, n, opts, [])

def finishfold(ui, repo, ctx, oldctx, newnode, opts, internalchanges):
    parent = ctx.parents()[0].node()
    hg.update(repo, parent)
    ### prepare new commit data
    commitopts = opts.copy()
    # username
    if ctx.user() == oldctx.user():
        username = ctx.user()
    else:
        username = ui.username()
    commitopts['user'] = username
    # commit message
    newmessage = '\n***\n'.join(
        [ctx.description()] +
        [repo[r].description() for r in internalchanges] +
        [oldctx.description()]) + '\n'
    commitopts['message'] = newmessage
    # date
    commitopts['date'] = max(ctx.date(), oldctx.date())
    n = collapse(repo, ctx, repo[newnode], commitopts)
    if n is None:
        return ctx, [], [], []
    hg.update(repo, n)
    return repo[n], [n], [oldctx.node(), ctx.node()], [newnode]

def drop(ui, repo, ctx, ha, opts):
    return ctx, [], [repo[ha].node()], []


def message(ui, repo, ctx, ha, opts):
    oldctx = repo[ha]
    hg.update(repo, ctx.node())
    stats = applychanges(ui, repo, oldctx, opts)
    if stats and stats[3] > 0:
        raise util.Abort(_('Fix up the change and run '
                           'hg histedit --continue'))
    message = oldctx.description() + '\n'
    message = ui.edit(message, ui.username())
    new = repo.commit(text=message, user=oldctx.user(), date=oldctx.date(),
                      extra=oldctx.extra())
    newctx = repo[new]
    if oldctx.node() != newctx.node():
        return newctx, [new], [oldctx.node()], []
    # We didn't make an edit, so just indicate no replaced nodes
    return newctx, [new], [], []

actiontable = {'p': pick,
               'pick': pick,
               'e': edit,
               'edit': edit,
               'f': fold,
               'fold': fold,
               'd': drop,
               'drop': drop,
               'm': message,
               'mess': message,
               }

@command('histedit',
    [('', 'commands', '',
      _('Read history edits from the specified file.')),
     ('c', 'continue', False, _('continue an edit already in progress')),
     ('k', 'keep', False,
      _("don't strip old nodes after edit is complete")),
     ('', 'abort', False, _('abort an edit in progress')),
     ('o', 'outgoing', False, _('changesets not found in destination')),
     ('f', 'force', False,
      _('force outgoing even for unrelated repositories')),
     ('r', 'rev', [], _('first revision to be edited'))],
     _("[PARENT]"))
def histedit(ui, repo, *parent, **opts):
    """interactively edit changeset history
    """
    # TODO only abort if we try and histedit mq patches, not just
    # blanket if mq patches are applied somewhere
    mq = getattr(repo, 'mq', None)
    if mq and mq.applied:
        raise util.Abort(_('source has mq patches applied'))

    parent = list(parent) + opts.get('rev', [])
    if opts.get('outgoing'):
        if len(parent) > 1:
            raise util.Abort(
                _('only one repo argument allowed with --outgoing'))
        elif parent:
            parent = parent[0]

        dest = ui.expandpath(parent or 'default-push', parent or 'default')
        dest, revs = hg.parseurl(dest, None)[:2]
        ui.status(_('comparing with %s\n') % util.hidepassword(dest))

        revs, checkout = hg.addbranchrevs(repo, repo, revs, None)
        other = hg.peer(repo, opts, dest)

        if revs:
            revs = [repo.lookup(rev) for rev in revs]

        parent = discovery.findcommonoutgoing(
            repo, other, [], force=opts.get('force')).missing[0:1]
    else:
        if opts.get('force'):
            raise util.Abort(_('--force only allowed with --outgoing'))

    if opts.get('continue', False):
        if len(parent) != 0:
            raise util.Abort(_('no arguments allowed with --continue'))
        (parentctxnode, created, replaced, tmpnodes,
         existing, rules, keep, topmost, replacemap) = readstate(repo)
        currentparent, wantnull = repo.dirstate.parents()
        parentctx = repo[parentctxnode]
        # existing is the list of revisions initially considered by
        # histedit. Here we use it to list new changesets, descendants
        # of parentctx without an 'existing' changeset in-between. We
        # also have to exclude 'existing' changesets which were
        # previously dropped.
        descendants = set(c.node() for c in
                repo.set('(%n::) - %n', parentctxnode, parentctxnode))
        existing = set(existing)
        notdropped = set(n for n in existing if n in descendants and
                (n not in replacemap or replacemap[n] in descendants))
        # Discover any nodes the user has added in the interim. We can
        # miss changesets which were dropped and recreated the same.
        newchildren = list(c.node() for c in repo.set(
            'sort(%ln - (%ln or %ln::))', descendants, existing, notdropped))
        action, currentnode = rules.pop(0)
        if action in ('f', 'fold'):
            tmpnodes.extend(newchildren)
        else:
            created.extend(newchildren)

        m, a, r, d = repo.status()[:4]
        oldctx = repo[currentnode]
        message = oldctx.description() + '\n'
        if action in ('e', 'edit', 'm', 'mess'):
            message = ui.edit(message, ui.username())
        elif action in ('f', 'fold'):
            message = 'fold-temp-revision %s' % currentnode
        new = None
        if m or a or r or d:
            new = repo.commit(text=message, user=oldctx.user(),
                              date=oldctx.date(), extra=oldctx.extra())

        # If we're resuming a fold and we have new changes, mark the
        # replacements and finish the fold. If not, it's more like a
        # drop of the changesets that disappeared, and we can skip
        # this step.
        if action in ('f', 'fold') and (new or newchildren):
            if new:
                tmpnodes.append(new)
            else:
                new = newchildren[-1]
            (parentctx, created_, replaced_, tmpnodes_) = finishfold(
                ui, repo, parentctx, oldctx, new, opts, newchildren)
            replaced.extend(replaced_)
            created.extend(created_)
            tmpnodes.extend(tmpnodes_)
        elif action not in ('d', 'drop'):
            if new != oldctx.node():
                replaced.append(oldctx.node())
            if new:
                if new != oldctx.node():
                    created.append(new)
                parentctx = repo[new]

    elif opts.get('abort', False):
        if len(parent) != 0:
            raise util.Abort(_('no arguments allowed with --abort'))
        (parentctxnode, created, replaced, tmpnodes,
         existing, rules, keep, topmost, replacemap) = readstate(repo)
        ui.debug('restore wc to old parent %s\n' % node.short(topmost))
        hg.clean(repo, topmost)
        cleanupnode(ui, repo, 'created', created)
        cleanupnode(ui, repo, 'temp', tmpnodes)
        os.unlink(os.path.join(repo.path, 'histedit-state'))
        return
    else:
        cmdutil.bailifchanged(repo)
        if os.path.exists(os.path.join(repo.path, 'histedit-state')):
            raise util.Abort(_('history edit already in progress, try '
                               '--continue or --abort'))

        topmost, empty = repo.dirstate.parents()


        if len(parent) != 1:
            raise util.Abort(_('histedit requires exactly one parent revision'))
        parent = scmutil.revsingle(repo, parent[0]).node()

        keep = opts.get('keep', False)
        revs = between(repo, parent, topmost, keep)

        ctxs = [repo[r] for r in revs]
        existing = [r.node() for r in ctxs]
        rules = opts.get('commands', '')
        if not rules:
            rules = '\n'.join([makedesc(c) for c in ctxs])
            rules += '\n\n'
            rules += editcomment % (node.short(parent), node.short(topmost))
            rules = ui.edit(rules, ui.username())
            # Save edit rules in .hg/histedit-last-edit.txt in case
            # the user needs to ask for help after something
            # surprising happens.
            f = open(repo.join('histedit-last-edit.txt'), 'w')
            f.write(rules)
            f.close()
        else:
            f = open(rules)
            rules = f.read()
            f.close()
        rules = [l for l in (r.strip() for r in rules.splitlines())
                 if l and not l[0] == '#']
        rules = verifyrules(rules, repo, ctxs)

        parentctx = repo[parent].parents()[0]
        keep = opts.get('keep', False)
        replaced = []
        replacemap = {}
        tmpnodes = []
        created = []


    while rules:
        writestate(repo, parentctx.node(), created, replaced,
                   tmpnodes, existing, rules, keep, topmost, replacemap)
        action, ha = rules.pop(0)
        ui.debug('histedit: processing %s %s\n' % (action, ha))
        (parentctx, created_, replaced_, tmpnodes_) = actiontable[action](
            ui, repo, parentctx, ha, opts)

        if replaced_:
            clen, rlen = len(created_), len(replaced_)
            if clen == rlen == 1:
                ui.debug('histedit: exact replacement of %s with %s\n' % (
                    node.short(replaced_[0]), node.short(created_[0])))

                replacemap[replaced_[0]] = created_[0]
            elif clen > rlen:
                assert rlen == 1, ('unexpected replacement of '
                                   '%d changes with %d changes' % (rlen, clen))
                # made more changesets than we're replacing
                # TODO synthesize patch names for created patches
                replacemap[replaced_[0]] = created_[-1]
                ui.debug('histedit: created many, assuming %s replaced by %s' %
                         (node.short(replaced_[0]), node.short(created_[-1])))
            elif rlen > clen:
                if not created_:
                    # This must be a drop. Try and put our metadata on
                    # the parent change.
                    assert rlen == 1
                    r = replaced_[0]
                    ui.debug('histedit: %s seems replaced with nothing, '
                            'finding a parent\n' % (node.short(r)))
                    pctx = repo[r].parents()[0]
                    if pctx.node() in replacemap:
                        ui.debug('histedit: parent is already replaced\n')
                        replacemap[r] = replacemap[pctx.node()]
                    else:
                        replacemap[r] = pctx.node()
                    ui.debug('histedit: %s best replaced by %s\n' % (
                        node.short(r), node.short(replacemap[r])))
                else:
                    assert len(created_) == 1
                    for r in replaced_:
                        ui.debug('histedit: %s replaced by %s\n' % (
                            node.short(r), node.short(created_[0])))
                        replacemap[r] = created_[0]
            else:
                assert False, (
                    'Unhandled case in replacement mapping! '
                    'replacing %d changes with %d changes' % (rlen, clen))
        created.extend(created_)
        replaced.extend(replaced_)
        tmpnodes.extend(tmpnodes_)

    hg.update(repo, parentctx.node())

    if not keep:
        if replacemap:
            movebookmarks(ui, repo, replacemap, tmpnodes, created)
            # TODO update mq state
        cleanupnode(ui, repo, 'replaced', replaced)

    cleanupnode(ui, repo, 'temp', tmpnodes)
    os.unlink(os.path.join(repo.path, 'histedit-state'))
    if os.path.exists(repo.sjoin('undo')):
        os.unlink(repo.sjoin('undo'))


def between(repo, old, new, keep):
    """select and validate the set of revision to edit

    When keep is false, the specified set can't have children."""
    revs = [old]
    current = old
    while current != new:
        ctx = repo[current]
        if not keep and len(ctx.children()) > 1:
            raise util.Abort(_('cannot edit history that would orphan nodes'))
        if len(ctx.parents()) != 1 and ctx.parents()[1] != node.nullid:
            raise util.Abort(_("can't edit history with merges"))
        if not ctx.children():
            current = new
        else:
            current = ctx.children()[0].node()
            revs.append(current)
    if len(repo[current].children()) and not keep:
        raise util.Abort(_('cannot edit history that would orphan nodes'))
    return revs


def writestate(repo, parentctxnode, created, replaced,
               tmpnodes, existing, rules, keep, topmost, replacemap):
    fp = open(os.path.join(repo.path, 'histedit-state'), 'w')
    pickle.dump((parentctxnode, created, replaced,
                 tmpnodes, existing, rules, keep, topmost, replacemap),
                fp)
    fp.close()

def readstate(repo):
    """Returns a tuple of (parentnode, created, replaced, tmp, existing, rules,
                           keep, topmost, replacemap ).
    """
    fp = open(os.path.join(repo.path, 'histedit-state'))
    return pickle.load(fp)


def makedesc(c):
    """build a initial action line for a ctx `c`

    line are in the form:

      pick <hash> <rev> <summary>
    """
    summary = ''
    if c.description():
        summary = c.description().splitlines()[0]
    line = 'pick %s %d %s' % (c, c.rev(), summary)
    return line[:80]  # trim to 80 chars so it's not stupidly wide in my editor

def verifyrules(rules, repo, ctxs):
    """Verify that there exists exactly one edit rule per given changeset.

    Will abort if there are to many or too few rules, a malformed rule,
    or a rule on a changeset outside of the user-given range.
    """
    parsed = []
    if len(rules) != len(ctxs):
        raise util.Abort(_('must specify a rule for each changeset once'))
    for r in rules:
        if ' ' not in r:
            raise util.Abort(_('malformed line "%s"') % r)
        action, rest = r.split(' ', 1)
        if ' ' in rest.strip():
            ha, rest = rest.split(' ', 1)
        else:
            ha = r.strip()
        try:
            if repo[ha] not in ctxs:
                raise util.Abort(
                    _('may not use changesets other than the ones listed'))
        except error.RepoError:
            raise util.Abort(_('unknown changeset %s listed') % ha)
        if action not in actiontable:
            raise util.Abort(_('unknown action "%s"') % action)
        parsed.append([action, ha])
    return parsed

def movebookmarks(ui, repo, replacemap, tmpnodes, created):
    """Move bookmark from old to newly created node"""
    ui.note(_('histedit: Should update metadata for the following '
              'changes:\n'))

    def copybms(old, new):
        if old in tmpnodes or old in created:
            # can't have any metadata we'd want to update
            return
        while new in replacemap:
            new = replacemap[new]
        ui.note(_('histedit:  %s to %s\n') % (node.short(old),
                                              node.short(new)))
        octx = repo[old]
        marks = octx.bookmarks()
        if marks:
            ui.note(_('histedit:     moving bookmarks %s\n') %
                      ', '.join(marks))
            for mark in marks:
                repo._bookmarks[mark] = new
            bookmarks.write(repo)

    # We assume that bookmarks on the tip should remain
    # tipmost, but bookmarks on non-tip changesets should go
    # to their most reasonable successor. As a result, find
    # the old tip and new tip and copy those bookmarks first,
    # then do the rest of the bookmark copies.
    oldtip = sorted(replacemap.keys(), key=repo.changelog.rev)[-1]
    newtip = sorted(replacemap.values(), key=repo.changelog.rev)[-1]
    copybms(oldtip, newtip)

    for old, new in sorted(replacemap.iteritems()):
        copybms(old, new)

def cleanupnode(ui, repo, name, nodes):
    """strip a group of nodes from the repository

    The set of node to strip may contains unknown nodes."""
    ui.debug('should strip %s nodes %s\n' %
             (name, ', '.join([node.short(n) for n in nodes])))
    lock = None
    try:
        lock = repo.lock()
        # Find all node that need to be stripped
        # (we hg %lr instead of %ln to silently ignore unknown item
        nm = repo.changelog.nodemap
        nodes = [n for n in nodes if n in nm]
        roots = [c.node() for c in repo.set("roots(%ln)", nodes)]
        for c in roots:
            # We should process node in reverse order to strip tip most first.
            # but this trigger a bug in changegroup hook.
            # This would reduce bundle overhead
            repair.strip(ui, repo, c)
    finally:
        lockmod.release(lock)

