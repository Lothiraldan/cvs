# exchange.py - utily to exchange data between repo.
#
# Copyright 2005-2007 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from i18n import _
from node import hex
import errno
import util, scmutil, changegroup
import discovery, phases, obsolete, bookmarks


class pushoperation(object):
    """A object that represent a single push operation

    It purpose is to carry push related state and very common operation.

    A new should be created at the begining of each push and discarded
    afterward.
    """

    def __init__(self, repo, remote, force=False, revs=None, newbranch=False):
        # repo we push from
        self.repo = repo
        self.ui = repo.ui
        # repo we push to
        self.remote = remote
        # force option provided
        self.force = force
        # revs to be pushed (None is "all")
        self.revs = revs
        # allow push of new branch
        self.newbranch = newbranch

def push(repo, remote, force=False, revs=None, newbranch=False):
    '''Push outgoing changesets (limited by revs) from a local
    repository to remote. Return an integer:
      - None means nothing to push
      - 0 means HTTP error
      - 1 means we pushed and remote head count is unchanged *or*
        we have outgoing changesets but refused to push
      - other values as described by addchangegroup()
    '''
    pushop = pushoperation(repo, remote, force, revs, newbranch)
    if pushop.remote.local():
        missing = (set(pushop.repo.requirements)
                   - pushop.remote.local().supported)
        if missing:
            msg = _("required features are not"
                    " supported in the destination:"
                    " %s") % (', '.join(sorted(missing)))
            raise util.Abort(msg)

    # there are two ways to push to remote repo:
    #
    # addchangegroup assumes local user can lock remote
    # repo (local filesystem, old ssh servers).
    #
    # unbundle assumes local user cannot lock remote repo (new ssh
    # servers, http servers).

    if not pushop.remote.canpush():
        raise util.Abort(_("destination does not support push"))
    unfi = pushop.repo.unfiltered()
    def localphasemove(nodes, phase=phases.public):
        """move <nodes> to <phase> in the local source repo"""
        if locallock is not None:
            phases.advanceboundary(pushop.repo, phase, nodes)
        else:
            # repo is not locked, do not change any phases!
            # Informs the user that phases should have been moved when
            # applicable.
            actualmoves = [n for n in nodes if phase < pushop.repo[n].phase()]
            phasestr = phases.phasenames[phase]
            if actualmoves:
                pushop.ui.status(_('cannot lock source repo, skipping '
                                   'local %s phase update\n') % phasestr)
    # get local lock as we might write phase data
    locallock = None
    try:
        locallock = pushop.repo.lock()
    except IOError, err:
        if err.errno != errno.EACCES:
            raise
        # source repo cannot be locked.
        # We do not abort the push, but just disable the local phase
        # synchronisation.
        msg = 'cannot lock source repository: %s\n' % err
        pushop.ui.debug(msg)
    try:
        pushop.repo.checkpush(pushop.force, pushop.revs)
        lock = None
        unbundle = pushop.remote.capable('unbundle')
        if not unbundle:
            lock = pushop.remote.lock()
        try:
            # discovery
            fci = discovery.findcommonincoming
            commoninc = fci(unfi, pushop.remote, force=pushop.force)
            common, inc, remoteheads = commoninc
            fco = discovery.findcommonoutgoing
            outgoing = fco(unfi, pushop.remote, onlyheads=pushop.revs,
                           commoninc=commoninc, force=pushop.force)


            if not outgoing.missing:
                # nothing to push
                scmutil.nochangesfound(unfi.ui, unfi, outgoing.excluded)
                ret = None
            else:
                # something to push
                if not pushop.force:
                    # if repo.obsstore == False --> no obsolete
                    # then, save the iteration
                    if unfi.obsstore:
                        # this message are here for 80 char limit reason
                        mso = _("push includes obsolete changeset: %s!")
                        mst = "push includes %s changeset: %s!"
                        # plain versions for i18n tool to detect them
                        _("push includes unstable changeset: %s!")
                        _("push includes bumped changeset: %s!")
                        _("push includes divergent changeset: %s!")
                        # If we are to push if there is at least one
                        # obsolete or unstable changeset in missing, at
                        # least one of the missinghead will be obsolete or
                        # unstable. So checking heads only is ok
                        for node in outgoing.missingheads:
                            ctx = unfi[node]
                            if ctx.obsolete():
                                raise util.Abort(mso % ctx)
                            elif ctx.troubled():
                                raise util.Abort(_(mst)
                                                 % (ctx.troubles()[0],
                                                    ctx))
                    newbm = pushop.ui.configlist('bookmarks', 'pushing')
                    discovery.checkheads(unfi, pushop.remote, outgoing,
                                         remoteheads, pushop.newbranch,
                                         bool(inc), newbm)

                # TODO: get bundlecaps from remote
                bundlecaps = None
                # create a changegroup from local
                if pushop.revs is None and not (outgoing.excluded
                                        or pushop.repo.changelog.filteredrevs):
                    # push everything,
                    # use the fast path, no race possible on push
                    bundler = changegroup.bundle10(pushop.repo, bundlecaps)
                    cg = pushop.repo._changegroupsubset(outgoing,
                                                        bundler,
                                                        'push',
                                                        fastpath=True)
                else:
                    cg = pushop.repo.getlocalbundle('push', outgoing,
                                                    bundlecaps)

                # apply changegroup to remote
                if unbundle:
                    # local repo finds heads on server, finds out what
                    # revs it must push. once revs transferred, if server
                    # finds it has different heads (someone else won
                    # commit/push race), server aborts.
                    if pushop.force:
                        remoteheads = ['force']
                    # ssh: return remote's addchangegroup()
                    # http: return remote's addchangegroup() or 0 for error
                    ret = pushop.remote.unbundle(cg, remoteheads, 'push')
                else:
                    # we return an integer indicating remote head count
                    # change
                    ret = pushop.remote.addchangegroup(cg, 'push',
                                                       pushop.repo.url())

            if ret:
                # push succeed, synchronize target of the push
                cheads = outgoing.missingheads
            elif pushop.revs is None:
                # All out push fails. synchronize all common
                cheads = outgoing.commonheads
            else:
                # I want cheads = heads(::missingheads and ::commonheads)
                # (missingheads is revs with secret changeset filtered out)
                #
                # This can be expressed as:
                #     cheads = ( (missingheads and ::commonheads)
                #              + (commonheads and ::missingheads))"
                #              )
                #
                # while trying to push we already computed the following:
                #     common = (::commonheads)
                #     missing = ((commonheads::missingheads) - commonheads)
                #
                # We can pick:
                # * missingheads part of common (::commonheads)
                common = set(outgoing.common)
                nm = pushop.repo.changelog.nodemap
                cheads = [node for node in pushop.revs if nm[node] in common]
                # and
                # * commonheads parents on missing
                revset = unfi.set('%ln and parents(roots(%ln))',
                                 outgoing.commonheads,
                                 outgoing.missing)
                cheads.extend(c.node() for c in revset)
            # even when we don't push, exchanging phase data is useful
            remotephases = pushop.remote.listkeys('phases')
            if (pushop.ui.configbool('ui', '_usedassubrepo', False)
                and remotephases    # server supports phases
                and ret is None # nothing was pushed
                and remotephases.get('publishing', False)):
                # When:
                # - this is a subrepo push
                # - and remote support phase
                # - and no changeset was pushed
                # - and remote is publishing
                # We may be in issue 3871 case!
                # We drop the possible phase synchronisation done by
                # courtesy to publish changesets possibly locally draft
                # on the remote.
                remotephases = {'publishing': 'True'}
            if not remotephases: # old server or public only repo
                localphasemove(cheads)
                # don't push any phase data as there is nothing to push
            else:
                ana = phases.analyzeremotephases(pushop.repo, cheads,
                                                 remotephases)
                pheads, droots = ana
                ### Apply remote phase on local
                if remotephases.get('publishing', False):
                    localphasemove(cheads)
                else: # publish = False
                    localphasemove(pheads)
                    localphasemove(cheads, phases.draft)
                ### Apply local phase on remote

                # Get the list of all revs draft on remote by public here.
                # XXX Beware that revset break if droots is not strictly
                # XXX root we may want to ensure it is but it is costly
                outdated =  unfi.set('heads((%ln::%ln) and public())',
                                     droots, cheads)
                for newremotehead in outdated:
                    r = pushop.remote.pushkey('phases',
                                              newremotehead.hex(),
                                              str(phases.draft),
                                              str(phases.public))
                    if not r:
                        pushop.ui.warn(_('updating %s to public failed!\n')
                                       % newremotehead)
            pushop.ui.debug('try to push obsolete markers to remote\n')
            _pushobsolete(pushop)
        finally:
            if lock is not None:
                lock.release()
    finally:
        if locallock is not None:
            locallock.release()

    _pushbookmark(pushop)
    return ret

def _pushobsolete(pushop):
    """utility function to push obsolete markers to a remote

    Exist mostly to allow overriding for experimentation purpose"""
    repo = pushop.repo
    remote = pushop.remote
    if (obsolete._enabled and repo.obsstore and
        'obsolete' in remote.listkeys('namespaces')):
        rslts = []
        remotedata = repo.listkeys('obsolete')
        for key in sorted(remotedata, reverse=True):
            # reverse sort to ensure we end with dump0
            data = remotedata[key]
            rslts.append(remote.pushkey('obsolete', key, '', data))
        if [r for r in rslts if not r]:
            msg = _('failed to push some obsolete markers!\n')
            repo.ui.warn(msg)

def _pushbookmark(pushop):
    """Update bookmark position on remote"""
    ui = pushop.ui
    repo = pushop.repo.unfiltered()
    remote = pushop.remote
    ui.debug("checking for updated bookmarks\n")
    revnums = map(repo.changelog.rev, pushop.revs or [])
    ancestors = [a for a in repo.changelog.ancestors(revnums, inclusive=True)]
    (addsrc, adddst, advsrc, advdst, diverge, differ, invalid
     ) = bookmarks.compare(repo, repo._bookmarks, remote.listkeys('bookmarks'),
                           srchex=hex)

    for b, scid, dcid in advsrc:
        if ancestors and repo[scid].rev() not in ancestors:
            continue
        if remote.pushkey('bookmarks', b, dcid, scid):
            ui.status(_("updating bookmark %s\n") % b)
        else:
            ui.warn(_('updating bookmark %s failed!\n') % b)
