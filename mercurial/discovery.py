# discovery.py - protocol changeset discovery functions
#
# Copyright 2010 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from node import nullid, short
from i18n import _
import util, setdiscovery, treediscovery, phases

def findcommonincoming(repo, remote, heads=None, force=False):
    """Return a tuple (common, anyincoming, heads) used to identify the common
    subset of nodes between repo and remote.

    "common" is a list of (at least) the heads of the common subset.
    "anyincoming" is testable as a boolean indicating if any nodes are missing
      locally. If remote does not support getbundle, this actually is a list of
      roots of the nodes that would be incoming, to be supplied to
      changegroupsubset. No code except for pull should be relying on this fact
      any longer.
    "heads" is either the supplied heads, or else the remote's heads.

    If you pass heads and they are all known locally, the reponse lists justs
    these heads in "common" and in "heads".

    Please use findcommonoutgoing to compute the set of outgoing nodes to give
    extensions a good hook into outgoing.
    """

    if not remote.capable('getbundle'):
        return treediscovery.findcommonincoming(repo, remote, heads, force)

    if heads:
        allknown = True
        nm = repo.changelog.nodemap
        for h in heads:
            if nm.get(h) is None:
                allknown = False
                break
        if allknown:
            return (heads, False, heads)

    res = setdiscovery.findcommonheads(repo.ui, repo, remote,
                                       abortwhenunrelated=not force)
    common, anyinc, srvheads = res
    return (list(common), anyinc, heads or list(srvheads))

class outgoing(object):
    '''Represents the set of nodes present in a local repo but not in a
    (possibly) remote one.

    Members:

      missing is a list of all nodes present in local but not in remote.
      common is a list of all nodes shared between the two repos.
      excluded is the list of missing changeset that shouldn't be sent remotely.
      missingheads is the list of heads of missing.
      commonheads is the list of heads of common.

    The sets are computed on demand from the heads, unless provided upfront
    by discovery.'''

    def __init__(self, revlog, commonheads, missingheads):
        self.commonheads = commonheads
        self.missingheads = missingheads
        self._revlog = revlog
        self._common = None
        self._missing = None
        self.excluded = []

    def _computecommonmissing(self):
        sets = self._revlog.findcommonmissing(self.commonheads,
                                              self.missingheads)
        self._common, self._missing = sets

    @util.propertycache
    def common(self):
        if self._common is None:
            self._computecommonmissing()
        return self._common

    @util.propertycache
    def missing(self):
        if self._missing is None:
            self._computecommonmissing()
        return self._missing

def findcommonoutgoing(repo, other, onlyheads=None, force=False, commoninc=None):
    '''Return an outgoing instance to identify the nodes present in repo but
    not in other.

    If onlyheads is given, only nodes ancestral to nodes in onlyheads (inclusive)
    are included. If you already know the local repo's heads, passing them in
    onlyheads is faster than letting them be recomputed here.

    If commoninc is given, it must the the result of a prior call to
    findcommonincoming(repo, other, force) to avoid recomputing it here.'''
    # declare an empty outgoing object to be filled later
    og = outgoing(repo.changelog, None, None)

    # get common set if not provided
    if commoninc is None:
        commoninc = findcommonincoming(repo, other, force=force)
    og.commonheads, _any, _hds = commoninc

    # compute outgoing
    if not repo._phaseroots[phases.secret]:
        og.missingheads = onlyheads or repo.heads()
    elif onlyheads is None:
        # use visible heads as it should be cached
        og.missingheads = phases.visibleheads(repo)
        og.excluded = [ctx.node() for ctx in repo.set('secret()')]
    else:
        # compute common, missing and exclude secret stuff
        sets = repo.changelog.findcommonmissing(og.commonheads, onlyheads)
        og._common, allmissing = sets
        og._missing = missing = []
        og._excluded = excluded = []
        for node in allmissing:
            if repo[node].phase() >= phases.secret:
                excluded.append(node)
            else:
                missing.append(node)
        if excluded:
            # update missing heads
            rset = repo.set('heads(%ln)', missing)
            missingheads = [ctx.node() for ctx in rset]
        else:
            missingheads = onlyheads
        og.missingheads = missingheads

    return og

def prepush(repo, remote, force, revs, newbranch):
    '''Analyze the local and remote repositories and determine which
    changesets need to be pushed to the remote. Return value depends
    on circumstances:

    If we are not going to push anything, return a tuple (None,
    outgoing, common) where outgoing is 0 if there are no outgoing
    changesets and 1 if there are, but we refuse to push them
    (e.g. would create new remote heads). The third element "common"
    is the list of heads of the common set between local and remote.

    Otherwise, return a tuple (changegroup, remoteheads, futureheads),
    where changegroup is a readable file-like object whose read()
    returns successive changegroup chunks ready to be sent over the
    wire, remoteheads is the list of remote heads and futureheads is
    the list of heads of the common set between local and remote to
    be after push completion.
    '''
    commoninc = findcommonincoming(repo, remote, force=force)
    outgoing = findcommonoutgoing(repo, remote, onlyheads=revs,
                                      commoninc=commoninc, force=force)
    _common, inc, remoteheads = commoninc

    cl = repo.changelog
    outg = outgoing.missing
    common = outgoing.commonheads

    if not outg:
        if outgoing.excluded:
            repo.ui.status(_("no changes to push but %i secret changesets\n")
                           % len(outgoing.excluded))
        else:
            repo.ui.status(_("no changes found\n"))
        return None, 1, common

    if not force and remoteheads != [nullid]:
        if remote.capable('branchmap'):
            # Check for each named branch if we're creating new remote heads.
            # To be a remote head after push, node must be either:
            # - unknown locally
            # - a local outgoing head descended from update
            # - a remote head that's known locally and not
            #   ancestral to an outgoing head

            # 1. Create set of branches involved in the push.
            branches = set(repo[n].branch() for n in outg)

            # 2. Check for new branches on the remote.
            remotemap = remote.branchmap()
            newbranches = branches - set(remotemap)
            if newbranches and not newbranch: # new branch requires --new-branch
                branchnames = ', '.join(sorted(newbranches))
                raise util.Abort(_("push creates new remote branches: %s!")
                                   % branchnames,
                                 hint=_("use 'hg push --new-branch' to create"
                                        " new remote branches"))
            branches.difference_update(newbranches)

            # 3. Construct the initial oldmap and newmap dicts.
            # They contain information about the remote heads before and
            # after the push, respectively.
            # Heads not found locally are not included in either dict,
            # since they won't be affected by the push.
            # unsynced contains all branches with incoming changesets.
            oldmap = {}
            newmap = {}
            unsynced = set()
            for branch in branches:
                remotebrheads = remotemap[branch]
                prunedbrheads = [h for h in remotebrheads if h in cl.nodemap]
                oldmap[branch] = prunedbrheads
                newmap[branch] = list(prunedbrheads)
                if len(remotebrheads) > len(prunedbrheads):
                    unsynced.add(branch)

            # 4. Update newmap with outgoing changes.
            # This will possibly add new heads and remove existing ones.
            ctxgen = (repo[n] for n in outg)
            repo._updatebranchcache(newmap, ctxgen)

        else:
            # 1-4b. old servers: Check for new topological heads.
            # Construct {old,new}map with branch = None (topological branch).
            # (code based on _updatebranchcache)
            oldheads = set(h for h in remoteheads if h in cl.nodemap)
            newheads = oldheads.union(outg)
            if len(newheads) > 1:
                for latest in reversed(outg):
                    if latest not in newheads:
                        continue
                    minhrev = min(cl.rev(h) for h in newheads)
                    reachable = cl.reachable(latest, cl.node(minhrev))
                    reachable.remove(latest)
                    newheads.difference_update(reachable)
            branches = set([None])
            newmap = {None: newheads}
            oldmap = {None: oldheads}
            unsynced = inc and branches or set()

        # 5. Check for new heads.
        # If there are more heads after the push than before, a suitable
        # error message, depending on unsynced status, is displayed.
        error = None
        for branch in branches:
            newhs = set(newmap[branch])
            oldhs = set(oldmap[branch])
            if len(newhs) > len(oldhs):
                dhs = list(newhs - oldhs)
                if error is None:
                    if branch not in ('default', None):
                        error = _("push creates new remote head %s "
                                  "on branch '%s'!") % (short(dhs[0]), branch)
                    else:
                        error = _("push creates new remote head %s!"
                                  ) % short(dhs[0])
                    if branch in unsynced:
                        hint = _("you should pull and merge or "
                                 "use push -f to force")
                    else:
                        hint = _("did you forget to merge? "
                                 "use push -f to force")
                if branch is not None:
                    repo.ui.note(_("new remote heads on branch '%s'\n") % branch)
                for h in dhs:
                    repo.ui.note(_("new remote head %s\n") % short(h))
        if error:
            raise util.Abort(error, hint=hint)

        # 6. Check for unsynced changes on involved branches.
        if unsynced:
            repo.ui.warn(_("note: unsynced remote changes!\n"))

    if revs is None and not outgoing.excluded:
        # push everything,
        # use the fast path, no race possible on push
        cg = repo._changegroup(outg, 'push')
    else:
        cg = repo.getlocalbundle('push', outgoing)
    # no need to compute outg ancestor. All node in outg have either:
    # - parents in outg
    # - parents in common
    # - nullid parent
    rset = repo.set('heads(%ln + %ln)', common, outg)
    futureheads = [ctx.node() for ctx in rset]
    return cg, remoteheads, futureheads
