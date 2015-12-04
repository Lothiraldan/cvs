# changegroup.py - Mercurial changegroup manipulation functions
#
#  Copyright 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from __future__ import absolute_import

import os
import struct
import tempfile
import weakref

from .i18n import _
from .node import (
    hex,
    nullid,
    nullrev,
    short,
)

from . import (
    branchmap,
    dagutil,
    discovery,
    error,
    mdiff,
    phases,
    util,
)

_CHANGEGROUPV1_DELTA_HEADER = "20s20s20s20s"
_CHANGEGROUPV2_DELTA_HEADER = "20s20s20s20s20s"

def readexactly(stream, n):
    '''read n bytes from stream.read and abort if less was available'''
    s = stream.read(n)
    if len(s) < n:
        raise error.Abort(_("stream ended unexpectedly"
                           " (got %d bytes, expected %d)")
                          % (len(s), n))
    return s

def getchunk(stream):
    """return the next chunk from stream as a string"""
    d = readexactly(stream, 4)
    l = struct.unpack(">l", d)[0]
    if l <= 4:
        if l:
            raise error.Abort(_("invalid chunk length %d") % l)
        return ""
    return readexactly(stream, l - 4)

def chunkheader(length):
    """return a changegroup chunk header (string)"""
    return struct.pack(">l", length + 4)

def closechunk():
    """return a changegroup chunk header (string) for a zero-length chunk"""
    return struct.pack(">l", 0)

def combineresults(results):
    """logic to combine 0 or more addchangegroup results into one"""
    changedheads = 0
    result = 1
    for ret in results:
        # If any changegroup result is 0, return 0
        if ret == 0:
            result = 0
            break
        if ret < -1:
            changedheads += ret + 1
        elif ret > 1:
            changedheads += ret - 1
    if changedheads > 0:
        result = 1 + changedheads
    elif changedheads < 0:
        result = -1 + changedheads
    return result

bundletypes = {
    "": ("", None),       # only when using unbundle on ssh and old http servers
                          # since the unification ssh accepts a header but there
                          # is no capability signaling it.
    "HG20": (), # special-cased below
    "HG10UN": ("HG10UN", None),
    "HG10BZ": ("HG10", 'BZ'),
    "HG10GZ": ("HG10GZ", 'GZ'),
}

# hgweb uses this list to communicate its preferred type
bundlepriority = ['HG10GZ', 'HG10BZ', 'HG10UN']

def writechunks(ui, chunks, filename, vfs=None):
    """Write chunks to a file and return its filename.

    The stream is assumed to be a bundle file.
    Existing files will not be overwritten.
    If no filename is specified, a temporary file is created.
    """
    fh = None
    cleanup = None
    try:
        if filename:
            if vfs:
                fh = vfs.open(filename, "wb")
            else:
                fh = open(filename, "wb")
        else:
            fd, filename = tempfile.mkstemp(prefix="hg-bundle-", suffix=".hg")
            fh = os.fdopen(fd, "wb")
        cleanup = filename
        for c in chunks:
            fh.write(c)
        cleanup = None
        return filename
    finally:
        if fh is not None:
            fh.close()
        if cleanup is not None:
            if filename and vfs:
                vfs.unlink(cleanup)
            else:
                os.unlink(cleanup)

def writebundle(ui, cg, filename, bundletype, vfs=None, compression=None):
    """Write a bundle file and return its filename.

    Existing files will not be overwritten.
    If no filename is specified, a temporary file is created.
    bz2 compression can be turned off.
    The bundle file will be deleted in case of errors.
    """

    if bundletype == "HG20":
        from . import bundle2
        bundle = bundle2.bundle20(ui)
        bundle.setcompression(compression)
        part = bundle.newpart('changegroup', data=cg.getchunks())
        part.addparam('version', cg.version)
        chunkiter = bundle.getchunks()
    else:
        # compression argument is only for the bundle2 case
        assert compression is None
        if cg.version != '01':
            raise error.Abort(_('old bundle types only supports v1 '
                                'changegroups'))
        header, comp = bundletypes[bundletype]
        if comp not in util.compressors:
            raise error.Abort(_('unknown stream compression type: %s')
                              % comp)
        z = util.compressors[comp]()
        subchunkiter = cg.getchunks()
        def chunkiter():
            yield header
            for chunk in subchunkiter:
                yield z.compress(chunk)
            yield z.flush()
        chunkiter = chunkiter()

    # parse the changegroup data, otherwise we will block
    # in case of sshrepo because we don't know the end of the stream

    # an empty chunkgroup is the end of the changegroup
    # a changegroup has at least 2 chunkgroups (changelog and manifest).
    # after that, an empty chunkgroup is the end of the changegroup
    return writechunks(ui, chunkiter, filename, vfs=vfs)

class cg1unpacker(object):
    """Unpacker for cg1 changegroup streams.

    A changegroup unpacker handles the framing of the revision data in
    the wire format. Most consumers will want to use the apply()
    method to add the changes from the changegroup to a repository.

    If you're forwarding a changegroup unmodified to another consumer,
    use getchunks(), which returns an iterator of changegroup
    chunks. This is mostly useful for cases where you need to know the
    data stream has ended by observing the end of the changegroup.

    deltachunk() is useful only if you're applying delta data. Most
    consumers should prefer apply() instead.

    A few other public methods exist. Those are used only for
    bundlerepo and some debug commands - their use is discouraged.
    """
    deltaheader = _CHANGEGROUPV1_DELTA_HEADER
    deltaheadersize = struct.calcsize(deltaheader)
    version = '01'
    def __init__(self, fh, alg):
        if alg == 'UN':
            alg = None # get more modern without breaking too much
        if not alg in util.decompressors:
            raise error.Abort(_('unknown stream compression type: %s')
                             % alg)
        if alg == 'BZ':
            alg = '_truncatedBZ'
        self._stream = util.decompressors[alg](fh)
        self._type = alg
        self.callback = None

    # These methods (compressed, read, seek, tell) all appear to only
    # be used by bundlerepo, but it's a little hard to tell.
    def compressed(self):
        return self._type is not None
    def read(self, l):
        return self._stream.read(l)
    def seek(self, pos):
        return self._stream.seek(pos)
    def tell(self):
        return self._stream.tell()
    def close(self):
        return self._stream.close()

    def _chunklength(self):
        d = readexactly(self._stream, 4)
        l = struct.unpack(">l", d)[0]
        if l <= 4:
            if l:
                raise error.Abort(_("invalid chunk length %d") % l)
            return 0
        if self.callback:
            self.callback()
        return l - 4

    def changelogheader(self):
        """v10 does not have a changelog header chunk"""
        return {}

    def manifestheader(self):
        """v10 does not have a manifest header chunk"""
        return {}

    def filelogheader(self):
        """return the header of the filelogs chunk, v10 only has the filename"""
        l = self._chunklength()
        if not l:
            return {}
        fname = readexactly(self._stream, l)
        return {'filename': fname}

    def _deltaheader(self, headertuple, prevnode):
        node, p1, p2, cs = headertuple
        if prevnode is None:
            deltabase = p1
        else:
            deltabase = prevnode
        return node, p1, p2, deltabase, cs

    def deltachunk(self, prevnode):
        l = self._chunklength()
        if not l:
            return {}
        headerdata = readexactly(self._stream, self.deltaheadersize)
        header = struct.unpack(self.deltaheader, headerdata)
        delta = readexactly(self._stream, l - self.deltaheadersize)
        node, p1, p2, deltabase, cs = self._deltaheader(header, prevnode)
        return {'node': node, 'p1': p1, 'p2': p2, 'cs': cs,
                'deltabase': deltabase, 'delta': delta}

    def getchunks(self):
        """returns all the chunks contains in the bundle

        Used when you need to forward the binary stream to a file or another
        network API. To do so, it parse the changegroup data, otherwise it will
        block in case of sshrepo because it don't know the end of the stream.
        """
        # an empty chunkgroup is the end of the changegroup
        # a changegroup has at least 2 chunkgroups (changelog and manifest).
        # after that, an empty chunkgroup is the end of the changegroup
        empty = False
        count = 0
        while not empty or count <= 2:
            empty = True
            count += 1
            while True:
                chunk = getchunk(self)
                if not chunk:
                    break
                empty = False
                yield chunkheader(len(chunk))
                pos = 0
                while pos < len(chunk):
                    next = pos + 2**20
                    yield chunk[pos:next]
                    pos = next
            yield closechunk()

    def _unpackmanifests(self, repo, revmap, trp, prog, numchanges):
        # We know that we'll never have more manifests than we had
        # changesets.
        self.callback = prog(_('manifests'), numchanges)
        # no need to check for empty manifest group here:
        # if the result of the merge of 1 and 2 is the same in 3 and 4,
        # no new manifest will be created and the manifest group will
        # be empty during the pull
        self.manifestheader()
        repo.manifest.addgroup(self, revmap, trp)
        repo.ui.progress(_('manifests'), None)

    def apply(self, repo, srctype, url, emptyok=False,
              targetphase=phases.draft, expectedtotal=None):
        """Add the changegroup returned by source.read() to this repo.
        srctype is a string like 'push', 'pull', or 'unbundle'.  url is
        the URL of the repo where this changegroup is coming from.

        Return an integer summarizing the change to this repo:
        - nothing changed or no source: 0
        - more heads than before: 1+added heads (2..n)
        - fewer heads than before: -1-removed heads (-2..-n)
        - number of heads stays the same: 1
        """
        repo = repo.unfiltered()
        wasempty = (len(repo.changelog) == 0)
        def csmap(x):
            repo.ui.debug("add changeset %s\n" % short(x))
            return len(cl)

        def revmap(x):
            return cl.rev(x)

        changesets = files = revisions = 0

        tr = repo.transaction("\n".join([srctype, util.hidepassword(url)]))
        try:
            # The transaction could have been created before and already
            # carries source information. In this case we use the top
            # level data. We overwrite the argument because we need to use
            # the top level value (if they exist) in this function.
            srctype = tr.hookargs.setdefault('source', srctype)
            url = tr.hookargs.setdefault('url', url)
            repo.hook('prechangegroup', throw=True, **tr.hookargs)

            # write changelog data to temp files so concurrent readers
            # will not see an inconsistent view
            cl = repo.changelog
            cl.delayupdate(tr)
            oldheads = cl.heads()

            trp = weakref.proxy(tr)
            # pull off the changeset group
            repo.ui.status(_("adding changesets\n"))
            clstart = len(cl)
            class prog(object):
                def __init__(self, step, total):
                    self._step = step
                    self._total = total
                    self._count = 1
                def __call__(self):
                    repo.ui.progress(self._step, self._count, unit=_('chunks'),
                                     total=self._total)
                    self._count += 1
            self.callback = prog(_('changesets'), expectedtotal)

            efiles = set()
            def onchangelog(cl, node):
                efiles.update(cl.read(node)[3])

            self.changelogheader()
            srccontent = cl.addgroup(self, csmap, trp,
                                     addrevisioncb=onchangelog)
            efiles = len(efiles)

            if not (srccontent or emptyok):
                raise error.Abort(_("received changelog group is empty"))
            clend = len(cl)
            changesets = clend - clstart
            repo.ui.progress(_('changesets'), None)

            # pull off the manifest group
            repo.ui.status(_("adding manifests\n"))
            self._unpackmanifests(repo, revmap, trp, prog, changesets)

            needfiles = {}
            if repo.ui.configbool('server', 'validate', default=False):
                # validate incoming csets have their manifests
                for cset in xrange(clstart, clend):
                    mfnode = repo.changelog.read(repo.changelog.node(cset))[0]
                    mfest = repo.manifest.readdelta(mfnode)
                    # store file nodes we must see
                    for f, n in mfest.iteritems():
                        needfiles.setdefault(f, set()).add(n)

            # process the files
            repo.ui.status(_("adding file changes\n"))
            self.callback = None
            pr = prog(_('files'), efiles)
            newrevs, newfiles = _addchangegroupfiles(
                repo, self, revmap, trp, pr, needfiles, wasempty)
            revisions += newrevs
            files += newfiles

            dh = 0
            if oldheads:
                heads = cl.heads()
                dh = len(heads) - len(oldheads)
                for h in heads:
                    if h not in oldheads and repo[h].closesbranch():
                        dh -= 1
            htext = ""
            if dh:
                htext = _(" (%+d heads)") % dh

            repo.ui.status(_("added %d changesets"
                             " with %d changes to %d files%s\n")
                             % (changesets, revisions, files, htext))
            repo.invalidatevolatilesets()

            if changesets > 0:
                if 'node' not in tr.hookargs:
                    tr.hookargs['node'] = hex(cl.node(clstart))
                    hookargs = dict(tr.hookargs)
                else:
                    hookargs = dict(tr.hookargs)
                    hookargs['node'] = hex(cl.node(clstart))
                repo.hook('pretxnchangegroup', throw=True, **hookargs)

            added = [cl.node(r) for r in xrange(clstart, clend)]
            publishing = repo.publishing()
            if srctype in ('push', 'serve'):
                # Old servers can not push the boundary themselves.
                # New servers won't push the boundary if changeset already
                # exists locally as secret
                #
                # We should not use added here but the list of all change in
                # the bundle
                if publishing:
                    phases.advanceboundary(repo, tr, phases.public, srccontent)
                else:
                    # Those changesets have been pushed from the outside, their
                    # phases are going to be pushed alongside. Therefor
                    # `targetphase` is ignored.
                    phases.advanceboundary(repo, tr, phases.draft, srccontent)
                    phases.retractboundary(repo, tr, phases.draft, added)
            elif srctype != 'strip':
                # publishing only alter behavior during push
                #
                # strip should not touch boundary at all
                phases.retractboundary(repo, tr, targetphase, added)

            if changesets > 0:
                if srctype != 'strip':
                    # During strip, branchcache is invalid but coming call to
                    # `destroyed` will repair it.
                    # In other case we can safely update cache on disk.
                    branchmap.updatecache(repo.filtered('served'))

                def runhooks():
                    # These hooks run when the lock releases, not when the
                    # transaction closes. So it's possible for the changelog
                    # to have changed since we last saw it.
                    if clstart >= len(repo):
                        return

                    # forcefully update the on-disk branch cache
                    repo.ui.debug("updating the branch cache\n")
                    repo.hook("changegroup", **hookargs)

                    for n in added:
                        args = hookargs.copy()
                        args['node'] = hex(n)
                        repo.hook("incoming", **args)

                    newheads = [h for h in repo.heads() if h not in oldheads]
                    repo.ui.log("incoming",
                                "%s incoming changes - new heads: %s\n",
                                len(added),
                                ', '.join([hex(c[:6]) for c in newheads]))

                tr.addpostclose('changegroup-runhooks-%020i' % clstart,
                                lambda tr: repo._afterlock(runhooks))

            tr.close()

        finally:
            tr.release()
            repo.ui.flush()
        # never return 0 here:
        if dh < 0:
            return dh - 1
        else:
            return dh + 1

class cg2unpacker(cg1unpacker):
    """Unpacker for cg2 streams.

    cg2 streams add support for generaldelta, so the delta header
    format is slightly different. All other features about the data
    remain the same.
    """
    deltaheader = _CHANGEGROUPV2_DELTA_HEADER
    deltaheadersize = struct.calcsize(deltaheader)
    version = '02'

    def _deltaheader(self, headertuple, prevnode):
        node, p1, p2, deltabase, cs = headertuple
        return node, p1, p2, deltabase, cs

class headerlessfixup(object):
    def __init__(self, fh, h):
        self._h = h
        self._fh = fh
    def read(self, n):
        if self._h:
            d, self._h = self._h[:n], self._h[n:]
            if len(d) < n:
                d += readexactly(self._fh, n - len(d))
            return d
        return readexactly(self._fh, n)

class cg1packer(object):
    deltaheader = _CHANGEGROUPV1_DELTA_HEADER
    version = '01'
    def __init__(self, repo, bundlecaps=None):
        """Given a source repo, construct a bundler.

        bundlecaps is optional and can be used to specify the set of
        capabilities which can be used to build the bundle.
        """
        # Set of capabilities we can use to build the bundle.
        if bundlecaps is None:
            bundlecaps = set()
        self._bundlecaps = bundlecaps
        # experimental config: bundle.reorder
        reorder = repo.ui.config('bundle', 'reorder', 'auto')
        if reorder == 'auto':
            reorder = None
        else:
            reorder = util.parsebool(reorder)
        self._repo = repo
        self._reorder = reorder
        self._progress = repo.ui.progress
        if self._repo.ui.verbose and not self._repo.ui.debugflag:
            self._verbosenote = self._repo.ui.note
        else:
            self._verbosenote = lambda s: None

    def close(self):
        return closechunk()

    def fileheader(self, fname):
        return chunkheader(len(fname)) + fname

    def group(self, nodelist, revlog, lookup, units=None):
        """Calculate a delta group, yielding a sequence of changegroup chunks
        (strings).

        Given a list of changeset revs, return a set of deltas and
        metadata corresponding to nodes. The first delta is
        first parent(nodelist[0]) -> nodelist[0], the receiver is
        guaranteed to have this parent as it has all history before
        these changesets. In the case firstparent is nullrev the
        changegroup starts with a full revision.

        If units is not None, progress detail will be generated, units specifies
        the type of revlog that is touched (changelog, manifest, etc.).
        """
        # if we don't have any revisions touched by these changesets, bail
        if len(nodelist) == 0:
            yield self.close()
            return

        # for generaldelta revlogs, we linearize the revs; this will both be
        # much quicker and generate a much smaller bundle
        if (revlog._generaldelta and self._reorder is None) or self._reorder:
            dag = dagutil.revlogdag(revlog)
            revs = set(revlog.rev(n) for n in nodelist)
            revs = dag.linearize(revs)
        else:
            revs = sorted([revlog.rev(n) for n in nodelist])

        # add the parent of the first rev
        p = revlog.parentrevs(revs[0])[0]
        revs.insert(0, p)

        # build deltas
        total = len(revs) - 1
        msgbundling = _('bundling')
        for r in xrange(len(revs) - 1):
            if units is not None:
                self._progress(msgbundling, r + 1, unit=units, total=total)
            prev, curr = revs[r], revs[r + 1]
            linknode = lookup(revlog.node(curr))
            for c in self.revchunk(revlog, curr, prev, linknode):
                yield c

        if units is not None:
            self._progress(msgbundling, None)
        yield self.close()

    # filter any nodes that claim to be part of the known set
    def prune(self, revlog, missing, commonrevs):
        rr, rl = revlog.rev, revlog.linkrev
        return [n for n in missing if rl(rr(n)) not in commonrevs]

    def _packmanifests(self, mfnodes, lookuplinknode):
        """Pack flat manifests into a changegroup stream."""
        ml = self._repo.manifest
        size = 0
        for chunk in self.group(
                mfnodes, ml, lookuplinknode, units=_('manifests')):
            size += len(chunk)
            yield chunk
        self._verbosenote(_('%8.i (manifests)\n') % size)

    def generate(self, commonrevs, clnodes, fastpathlinkrev, source):
        '''yield a sequence of changegroup chunks (strings)'''
        repo = self._repo
        cl = repo.changelog
        ml = repo.manifest

        clrevorder = {}
        mfs = {} # needed manifests
        fnodes = {} # needed file nodes
        # maps manifest node id -> set(changed files)
        mfchangedfiles = {}

        # Callback for the changelog, used to collect changed files and manifest
        # nodes.
        # Returns the linkrev node (identity in the changelog case).
        def lookupcl(x):
            c = cl.read(x)
            clrevorder[x] = len(clrevorder)
            n = c[0]
            # record the first changeset introducing this manifest version
            mfs.setdefault(n, x)
            # Record a complete list of potentially-changed files in
            # this manifest.
            mfchangedfiles.setdefault(n, set()).update(c[3])
            return x

        self._verbosenote(_('uncompressed size of bundle content:\n'))
        size = 0
        for chunk in self.group(clnodes, cl, lookupcl, units=_('changesets')):
            size += len(chunk)
            yield chunk
        self._verbosenote(_('%8.i (changelog)\n') % size)

        # We need to make sure that the linkrev in the changegroup refers to
        # the first changeset that introduced the manifest or file revision.
        # The fastpath is usually safer than the slowpath, because the filelogs
        # are walked in revlog order.
        #
        # When taking the slowpath with reorder=None and the manifest revlog
        # uses generaldelta, the manifest may be walked in the "wrong" order.
        # Without 'clrevorder', we would get an incorrect linkrev (see fix in
        # cc0ff93d0c0c).
        #
        # When taking the fastpath, we are only vulnerable to reordering
        # of the changelog itself. The changelog never uses generaldelta, so
        # it is only reordered when reorder=True. To handle this case, we
        # simply take the slowpath, which already has the 'clrevorder' logic.
        # This was also fixed in cc0ff93d0c0c.
        fastpathlinkrev = fastpathlinkrev and not self._reorder
        # Callback for the manifest, used to collect linkrevs for filelog
        # revisions.
        # Returns the linkrev node (collected in lookupcl).
        if fastpathlinkrev:
            lookupmflinknode = mfs.__getitem__
        else:
            def lookupmflinknode(x):
                """Callback for looking up the linknode for manifests.

                Returns the linkrev node for the specified manifest.

                SIDE EFFECT:

                  fclnodes gets populated with the list of relevant
                  file nodes.

                Note that this means you can't trust fclnodes until
                after manifests have been sent to the client.
                """
                clnode = mfs[x]
                mdata = ml.readfast(x)
                for f in mfchangedfiles[x]:
                    try:
                        n = mdata[f]
                    except KeyError:
                        continue
                    # record the first changeset introducing this filelog
                    # version
                    fclnodes = fnodes.setdefault(f, {})
                    fclnode = fclnodes.setdefault(n, clnode)
                    if clrevorder[clnode] < clrevorder[fclnode]:
                        fclnodes[n] = clnode
                return clnode

        mfnodes = self.prune(ml, mfs, commonrevs)
        for x in self._packmanifests(mfnodes, lookupmflinknode):
            yield x

        mfs.clear()
        clrevs = set(cl.rev(x) for x in clnodes)

        def linknodes(filerevlog, fname):
            if fastpathlinkrev:
                llr = filerevlog.linkrev
                def genfilenodes():
                    for r in filerevlog:
                        linkrev = llr(r)
                        if linkrev in clrevs:
                            yield filerevlog.node(r), cl.node(linkrev)
                return dict(genfilenodes())
            return fnodes.get(fname, {})

        changedfiles = set()
        for x in mfchangedfiles.itervalues():
            changedfiles.update(x)
        for chunk in self.generatefiles(changedfiles, linknodes, commonrevs,
                                        source):
            yield chunk

        yield self.close()

        if clnodes:
            repo.hook('outgoing', node=hex(clnodes[0]), source=source)

    # The 'source' parameter is useful for extensions
    def generatefiles(self, changedfiles, linknodes, commonrevs, source):
        repo = self._repo
        progress = self._progress
        msgbundling = _('bundling')

        total = len(changedfiles)
        # for progress output
        msgfiles = _('files')
        for i, fname in enumerate(sorted(changedfiles)):
            filerevlog = repo.file(fname)
            if not filerevlog:
                raise error.Abort(_("empty or missing revlog for %s") % fname)

            linkrevnodes = linknodes(filerevlog, fname)
            # Lookup for filenodes, we collected the linkrev nodes above in the
            # fastpath case and with lookupmf in the slowpath case.
            def lookupfilelog(x):
                return linkrevnodes[x]

            filenodes = self.prune(filerevlog, linkrevnodes, commonrevs)
            if filenodes:
                progress(msgbundling, i + 1, item=fname, unit=msgfiles,
                         total=total)
                h = self.fileheader(fname)
                size = len(h)
                yield h
                for chunk in self.group(filenodes, filerevlog, lookupfilelog):
                    size += len(chunk)
                    yield chunk
                self._verbosenote(_('%8.i  %s\n') % (size, fname))
        progress(msgbundling, None)

    def deltaparent(self, revlog, rev, p1, p2, prev):
        return prev

    def revchunk(self, revlog, rev, prev, linknode):
        node = revlog.node(rev)
        p1, p2 = revlog.parentrevs(rev)
        base = self.deltaparent(revlog, rev, p1, p2, prev)

        prefix = ''
        if revlog.iscensored(base) or revlog.iscensored(rev):
            try:
                delta = revlog.revision(node)
            except error.CensoredNodeError as e:
                delta = e.tombstone
            if base == nullrev:
                prefix = mdiff.trivialdiffheader(len(delta))
            else:
                baselen = revlog.rawsize(base)
                prefix = mdiff.replacediffheader(baselen, len(delta))
        elif base == nullrev:
            delta = revlog.revision(node)
            prefix = mdiff.trivialdiffheader(len(delta))
        else:
            delta = revlog.revdiff(base, rev)
        p1n, p2n = revlog.parents(node)
        basenode = revlog.node(base)
        meta = self.builddeltaheader(node, p1n, p2n, basenode, linknode)
        meta += prefix
        l = len(meta) + len(delta)
        yield chunkheader(l)
        yield meta
        yield delta
    def builddeltaheader(self, node, p1n, p2n, basenode, linknode):
        # do nothing with basenode, it is implicitly the previous one in HG10
        return struct.pack(self.deltaheader, node, p1n, p2n, linknode)

class cg2packer(cg1packer):
    version = '02'
    deltaheader = _CHANGEGROUPV2_DELTA_HEADER

    def __init__(self, repo, bundlecaps=None):
        super(cg2packer, self).__init__(repo, bundlecaps)
        if self._reorder is None:
            # Since generaldelta is directly supported by cg2, reordering
            # generally doesn't help, so we disable it by default (treating
            # bundle.reorder=auto just like bundle.reorder=False).
            self._reorder = False

    def deltaparent(self, revlog, rev, p1, p2, prev):
        dp = revlog.deltaparent(rev)
        # avoid storing full revisions; pick prev in those cases
        # also pick prev when we can't be sure remote has dp
        if dp == nullrev or (dp != p1 and dp != p2 and dp != prev):
            return prev
        return dp

    def builddeltaheader(self, node, p1n, p2n, basenode, linknode):
        return struct.pack(self.deltaheader, node, p1n, p2n, basenode, linknode)

packermap = {'01': (cg1packer, cg1unpacker),
             # cg2 adds support for exchanging generaldelta
             '02': (cg2packer, cg2unpacker),
}

def _changegroupinfo(repo, nodes, source):
    if repo.ui.verbose or source == 'bundle':
        repo.ui.status(_("%d changesets found\n") % len(nodes))
    if repo.ui.debugflag:
        repo.ui.debug("list of changesets:\n")
        for node in nodes:
            repo.ui.debug("%s\n" % hex(node))

def getsubsetraw(repo, outgoing, bundler, source, fastpath=False):
    repo = repo.unfiltered()
    commonrevs = outgoing.common
    csets = outgoing.missing
    heads = outgoing.missingheads
    # We go through the fast path if we get told to, or if all (unfiltered
    # heads have been requested (since we then know there all linkrevs will
    # be pulled by the client).
    heads.sort()
    fastpathlinkrev = fastpath or (
            repo.filtername is None and heads == sorted(repo.heads()))

    repo.hook('preoutgoing', throw=True, source=source)
    _changegroupinfo(repo, csets, source)
    return bundler.generate(commonrevs, csets, fastpathlinkrev, source)

def getsubset(repo, outgoing, bundler, source, fastpath=False):
    gengroup = getsubsetraw(repo, outgoing, bundler, source, fastpath)
    return packermap[bundler.version][1](util.chunkbuffer(gengroup), None)

def changegroupsubset(repo, roots, heads, source, version='01'):
    """Compute a changegroup consisting of all the nodes that are
    descendants of any of the roots and ancestors of any of the heads.
    Return a chunkbuffer object whose read() method will return
    successive changegroup chunks.

    It is fairly complex as determining which filenodes and which
    manifest nodes need to be included for the changeset to be complete
    is non-trivial.

    Another wrinkle is doing the reverse, figuring out which changeset in
    the changegroup a particular filenode or manifestnode belongs to.
    """
    cl = repo.changelog
    if not roots:
        roots = [nullid]
    discbases = []
    for n in roots:
        discbases.extend([p for p in cl.parents(n) if p != nullid])
    # TODO: remove call to nodesbetween.
    csets, roots, heads = cl.nodesbetween(roots, heads)
    included = set(csets)
    discbases = [n for n in discbases if n not in included]
    outgoing = discovery.outgoing(cl, discbases, heads)
    bundler = packermap[version][0](repo)
    return getsubset(repo, outgoing, bundler, source)

def getlocalchangegroupraw(repo, source, outgoing, bundlecaps=None,
                           version='01'):
    """Like getbundle, but taking a discovery.outgoing as an argument.

    This is only implemented for local repos and reuses potentially
    precomputed sets in outgoing. Returns a raw changegroup generator."""
    if not outgoing.missing:
        return None
    bundler = packermap[version][0](repo, bundlecaps)
    return getsubsetraw(repo, outgoing, bundler, source)

def getlocalchangegroup(repo, source, outgoing, bundlecaps=None,
                        version='01'):
    """Like getbundle, but taking a discovery.outgoing as an argument.

    This is only implemented for local repos and reuses potentially
    precomputed sets in outgoing."""
    if not outgoing.missing:
        return None
    bundler = packermap[version][0](repo, bundlecaps)
    return getsubset(repo, outgoing, bundler, source)

def computeoutgoing(repo, heads, common):
    """Computes which revs are outgoing given a set of common
    and a set of heads.

    This is a separate function so extensions can have access to
    the logic.

    Returns a discovery.outgoing object.
    """
    cl = repo.changelog
    if common:
        hasnode = cl.hasnode
        common = [n for n in common if hasnode(n)]
    else:
        common = [nullid]
    if not heads:
        heads = cl.heads()
    return discovery.outgoing(cl, common, heads)

def getchangegroup(repo, source, heads=None, common=None, bundlecaps=None,
                   version='01'):
    """Like changegroupsubset, but returns the set difference between the
    ancestors of heads and the ancestors common.

    If heads is None, use the local heads. If common is None, use [nullid].

    The nodes in common might not all be known locally due to the way the
    current discovery protocol works.
    """
    outgoing = computeoutgoing(repo, heads, common)
    return getlocalchangegroup(repo, source, outgoing, bundlecaps=bundlecaps,
                               version=version)

def changegroup(repo, basenodes, source):
    # to avoid a race we use changegroupsubset() (issue1320)
    return changegroupsubset(repo, basenodes, repo.heads(), source)

def _addchangegroupfiles(repo, source, revmap, trp, pr, needfiles, wasempty):
    revisions = 0
    files = 0
    while True:
        chunkdata = source.filelogheader()
        if not chunkdata:
            break
        f = chunkdata["filename"]
        repo.ui.debug("adding %s revisions\n" % f)
        pr()
        fl = repo.file(f)
        o = len(fl)
        try:
            if not fl.addgroup(source, revmap, trp):
                raise error.Abort(_("received file revlog group is empty"))
        except error.CensoredBaseError as e:
            raise error.Abort(_("received delta base is censored: %s") % e)
        revisions += len(fl) - o
        files += 1
        if f in needfiles:
            needs = needfiles[f]
            for new in xrange(o, len(fl)):
                n = fl.node(new)
                if n in needs:
                    needs.remove(n)
                else:
                    raise error.Abort(
                        _("received spurious file revlog entry"))
            if not needs:
                del needfiles[f]
    repo.ui.progress(_('files'), None)

    for f, needs in needfiles.iteritems():
        fl = repo.file(f)
        for n in needs:
            try:
                fl.rev(n)
            except error.LookupError:
                raise error.Abort(
                    _('missing file data for %s:%s - run hg verify') %
                    (f, hex(n)))

    return revisions, files
