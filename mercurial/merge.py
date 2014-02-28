# merge.py - directory-level update/merge handling for Mercurial
#
# Copyright 2006, 2007 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

import struct

from node import nullid, nullrev, hex, bin
from i18n import _
from mercurial import obsolete
import error, util, filemerge, copies, subrepo, worker, dicthelpers
import errno, os, shutil

_pack = struct.pack
_unpack = struct.unpack

def _droponode(data):
    # used for compatibility for v1
    bits = data.split("\0")
    bits = bits[:-2] + bits[-1:]
    return "\0".join(bits)

class mergestate(object):
    '''track 3-way merge state of individual files

    it is stored on disk when needed. Two file are used, one with an old
    format, one with a new format. Both contains similar data, but the new
    format can store new kind of field.

    Current new format is a list of arbitrary record of the form:

        [type][length][content]

    Type is a single character, length is a 4 bytes integer, content is an
    arbitrary suites of bytes of length `length`.

    Type should be a letter. Capital letter are mandatory record, Mercurial
    should abort if they are unknown. lower case record can be safely ignored.

    Currently known record:

    L: the node of the "local" part of the merge (hexified version)
    O: the node of the "other" part of the merge (hexified version)
    F: a file to be merged entry
    '''
    statepathv1 = "merge/state"
    statepathv2 = "merge/state2"

    def __init__(self, repo):
        self._repo = repo
        self._dirty = False
        self._read()

    def reset(self, node=None, other=None):
        self._state = {}
        if node:
            self._local = node
            self._other = other
        shutil.rmtree(self._repo.join("merge"), True)
        self._dirty = False

    def _read(self):
        """Analyse each record content to restore a serialized state from disk

        This function process "record" entry produced by the de-serialization
        of on disk file.
        """
        self._state = {}
        records = self._readrecords()
        for rtype, record in records:
            if rtype == 'L':
                self._local = bin(record)
            elif rtype == 'O':
                self._other = bin(record)
            elif rtype == "F":
                bits = record.split("\0")
                self._state[bits[0]] = bits[1:]
            elif not rtype.islower():
                raise util.Abort(_('unsupported merge state record:'
                                   % rtype))
        self._dirty = False

    def _readrecords(self):
        """Read merge state from disk and return a list of record (TYPE, data)

        We read data from both V1 and Ve files decide which on to use.

        V1 have been used by version prior to 2.9.1 and contains less data than
        v2. We read both version and check if no data in v2 contradict one in
        v1. If there is not contradiction we can safely assume that both v1
        and v2 were written at the same time and use the extract data in v2. If
        there is contradiction we ignore v2 content as we assume an old version
        of Mercurial have over written the mergstate file and left an old v2
        file around.

        returns list of record [(TYPE, data), ...]"""
        v1records = self._readrecordsv1()
        v2records = self._readrecordsv2()
        oldv2 = set() # old format version of v2 record
        for rec in v2records:
            if rec[0] == 'L':
                oldv2.add(rec)
            elif rec[0] == 'F':
                # drop the onode data (not contained in v1)
                oldv2.add(('F', _droponode(rec[1])))
        for rec in v1records:
            if rec not in oldv2:
                # v1 file is newer than v2 file, use it
                # we have to infer the "other" changeset of the merge
                # we cannot do better than that with v1 of the format
                mctx = self._repo[None].parents()[-1]
                v1records.append(('O', mctx.hex()))
                # add place holder "other" file node information
                # nobody is using it yet so we do no need to fetch the data
                # if mctx was wrong `mctx[bits[-2]]` may fails.
                for idx, r in enumerate(v1records):
                    if r[0] == 'F':
                        bits = r[1].split("\0")
                        bits.insert(-2, '')
                        v1records[idx] = (r[0], "\0".join(bits))
                return v1records
        else:
            return v2records

    def _readrecordsv1(self):
        """read on disk merge state for version 1 file

        returns list of record [(TYPE, data), ...]

        Note: the "F" data from this file are one entry short
              (no "other file node" entry)
        """
        records = []
        try:
            f = self._repo.opener(self.statepathv1)
            for i, l in enumerate(f):
                if i == 0:
                    records.append(('L', l[:-1]))
                else:
                    records.append(('F', l[:-1]))
            f.close()
        except IOError, err:
            if err.errno != errno.ENOENT:
                raise
        return records

    def _readrecordsv2(self):
        """read on disk merge state for version 2 file

        returns list of record [(TYPE, data), ...]
        """
        records = []
        try:
            f = self._repo.opener(self.statepathv2)
            data = f.read()
            off = 0
            end = len(data)
            while off < end:
                rtype = data[off]
                off += 1
                length = _unpack('>I', data[off:(off + 4)])[0]
                off += 4
                record = data[off:(off + length)]
                off += length
                records.append((rtype, record))
            f.close()
        except IOError, err:
            if err.errno != errno.ENOENT:
                raise
        return records

    def commit(self):
        """Write current state on disk (if necessary)"""
        if self._dirty:
            records = []
            records.append(("L", hex(self._local)))
            records.append(("O", hex(self._other)))
            for d, v in self._state.iteritems():
                records.append(("F", "\0".join([d] + v)))
            self._writerecords(records)
            self._dirty = False

    def _writerecords(self, records):
        """Write current state on disk (both v1 and v2)"""
        self._writerecordsv1(records)
        self._writerecordsv2(records)

    def _writerecordsv1(self, records):
        """Write current state on disk in a version 1 file"""
        f = self._repo.opener(self.statepathv1, "w")
        irecords = iter(records)
        lrecords = irecords.next()
        assert lrecords[0] == 'L'
        f.write(hex(self._local) + "\n")
        for rtype, data in irecords:
            if rtype == "F":
                f.write("%s\n" % _droponode(data))
        f.close()

    def _writerecordsv2(self, records):
        """Write current state on disk in a version 2 file"""
        f = self._repo.opener(self.statepathv2, "w")
        for key, data in records:
            assert len(key) == 1
            format = ">sI%is" % len(data)
            f.write(_pack(format, key, len(data), data))
        f.close()

    def add(self, fcl, fco, fca, fd):
        """add a new (potentially?) conflicting file the merge state
        fcl: file context for local,
        fco: file context for remote,
        fca: file context for ancestors,
        fd:  file path of the resulting merge.

        note: also write the local version to the `.hg/merge` directory.
        """
        hash = util.sha1(fcl.path()).hexdigest()
        self._repo.opener.write("merge/" + hash, fcl.data())
        self._state[fd] = ['u', hash, fcl.path(),
                           fca.path(), hex(fca.filenode()),
                           fco.path(), hex(fco.filenode()),
                           fcl.flags()]
        self._dirty = True

    def __contains__(self, dfile):
        return dfile in self._state

    def __getitem__(self, dfile):
        return self._state[dfile][0]

    def __iter__(self):
        l = self._state.keys()
        l.sort()
        for f in l:
            yield f

    def files(self):
        return self._state.keys()

    def mark(self, dfile, state):
        self._state[dfile][0] = state
        self._dirty = True

    def resolve(self, dfile, wctx):
        """rerun merge process for file path `dfile`"""
        if self[dfile] == 'r':
            return 0
        stateentry = self._state[dfile]
        state, hash, lfile, afile, anode, ofile, onode, flags = stateentry
        octx = self._repo[self._other]
        fcd = wctx[dfile]
        fco = octx[ofile]
        fca = self._repo.filectx(afile, fileid=anode)
        # "premerge" x flags
        flo = fco.flags()
        fla = fca.flags()
        if 'x' in flags + flo + fla and 'l' not in flags + flo + fla:
            if fca.node() == nullid:
                self._repo.ui.warn(_('warning: cannot merge flags for %s\n') %
                                   afile)
            elif flags == fla:
                flags = flo
        # restore local
        f = self._repo.opener("merge/" + hash)
        self._repo.wwrite(dfile, f.read(), flags)
        f.close()
        r = filemerge.filemerge(self._repo, self._local, lfile, fcd, fco, fca)
        if r is None:
            # no real conflict
            del self._state[dfile]
            self._dirty = True
        elif not r:
            self.mark(dfile, 'r')
        return r

def _checkunknownfile(repo, wctx, mctx, f):
    return (not repo.dirstate._ignore(f)
        and os.path.isfile(repo.wjoin(f))
        and repo.wopener.audit.check(f)
        and repo.dirstate.normalize(f) not in repo.dirstate
        and mctx[f].cmp(wctx[f]))

def _checkunknown(repo, wctx, mctx):
    "check for collisions between unknown files and files in mctx"

    error = False
    for f in mctx:
        if f not in wctx and _checkunknownfile(repo, wctx, mctx, f):
            error = True
            wctx._repo.ui.warn(_("%s: untracked file differs\n") % f)
    if error:
        raise util.Abort(_("untracked files in working directory differ "
                           "from files in requested revision"))

def _forgetremoved(wctx, mctx, branchmerge):
    """
    Forget removed files

    If we're jumping between revisions (as opposed to merging), and if
    neither the working directory nor the target rev has the file,
    then we need to remove it from the dirstate, to prevent the
    dirstate from listing the file when it is no longer in the
    manifest.

    If we're merging, and the other revision has removed a file
    that is not present in the working directory, we need to mark it
    as removed.
    """

    actions = []
    state = branchmerge and 'r' or 'f'
    for f in wctx.deleted():
        if f not in mctx:
            actions.append((f, state, None, "forget deleted"))

    if not branchmerge:
        for f in wctx.removed():
            if f not in mctx:
                actions.append((f, "f", None, "forget removed"))

    return actions

def _checkcollision(repo, wmf, actions):
    # build provisional merged manifest up
    pmmf = set(wmf)

    def addop(f, args):
        pmmf.add(f)
    def removeop(f, args):
        pmmf.discard(f)
    def nop(f, args):
        pass

    def renameop(f, args):
        f2, fd, flags = args
        if f:
            pmmf.discard(f)
        pmmf.add(fd)
    def mergeop(f, args):
        f2, fd, move = args
        if move:
            pmmf.discard(f)
        pmmf.add(fd)

    opmap = {
        "a": addop,
        "d": renameop,
        "dr": nop,
        "e": nop,
        "f": addop, # untracked file should be kept in working directory
        "g": addop,
        "m": mergeop,
        "r": removeop,
        "rd": nop,
        "cd": addop,
        "dc": addop,
    }
    for f, m, args, msg in actions:
        op = opmap.get(m)
        assert op, m
        op(f, args)

    # check case-folding collision in provisional merged manifest
    foldmap = {}
    for f in sorted(pmmf):
        fold = util.normcase(f)
        if fold in foldmap:
            raise util.Abort(_("case-folding collision between %s and %s")
                             % (f, foldmap[fold]))
        foldmap[fold] = f

def manifestmerge(repo, wctx, p2, pa, branchmerge, force, partial,
                  acceptremote=False):
    """
    Merge p1 and p2 with ancestor pa and generate merge action list

    branchmerge and force are as passed in to update
    partial = function to filter file lists
    acceptremote = accept the incoming changes without prompting
    """

    overwrite = force and not branchmerge
    actions, copy, movewithdir = [], {}, {}

    followcopies = False
    if overwrite:
        pa = wctx
    elif pa == p2: # backwards
        pa = wctx.p1()
    elif not branchmerge and not wctx.dirty(missing=True):
        pass
    elif pa and repo.ui.configbool("merge", "followcopies", True):
        followcopies = True

    # manifests fetched in order are going to be faster, so prime the caches
    [x.manifest() for x in
     sorted(wctx.parents() + [p2, pa], key=lambda x: x.rev())]

    if followcopies:
        ret = copies.mergecopies(repo, wctx, p2, pa)
        copy, movewithdir, diverge, renamedelete = ret
        for of, fl in diverge.iteritems():
            actions.append((of, "dr", (fl,), "divergent renames"))
        for of, fl in renamedelete.iteritems():
            actions.append((of, "rd", (fl,), "rename and delete"))

    repo.ui.note(_("resolving manifests\n"))
    repo.ui.debug(" branchmerge: %s, force: %s, partial: %s\n"
                  % (bool(branchmerge), bool(force), bool(partial)))
    repo.ui.debug(" ancestor: %s, local: %s, remote: %s\n" % (pa, wctx, p2))

    m1, m2, ma = wctx.manifest(), p2.manifest(), pa.manifest()
    copied = set(copy.values())
    copied.update(movewithdir.values())

    if '.hgsubstate' in m1:
        # check whether sub state is modified
        for s in sorted(wctx.substate):
            if wctx.sub(s).dirty():
                m1['.hgsubstate'] += "+"
                break

    aborts = []
    # Compare manifests
    fdiff = dicthelpers.diff(m1, m2)
    flagsdiff = m1.flagsdiff(m2)
    diff12 = dicthelpers.join(fdiff, flagsdiff)

    for f, (n12, fl12) in diff12.iteritems():
        if n12:
            n1, n2 = n12
        else: # file contents didn't change, but flags did
            n1 = n2 = m1.get(f, None)
            if n1 is None:
                # Since n1 == n2, the file isn't present in m2 either. This
                # means that the file was removed or deleted locally and
                # removed remotely, but that residual entries remain in flags.
                # This can happen in manifests generated by workingctx.
                continue
        if fl12:
            fl1, fl2 = fl12
        else: # flags didn't change, file contents did
            fl1 = fl2 = m1.flags(f)

        if partial and not partial(f):
            continue
        if n1 and n2:
            fa = f
            a = ma.get(f, nullid)
            if a == nullid:
                fa = copy.get(f, f)
                # Note: f as default is wrong - we can't really make a 3-way
                # merge without an ancestor file.
            fla = ma.flags(fa)
            nol = 'l' not in fl1 + fl2 + fla
            if n2 == a and fl2 == fla:
                pass # remote unchanged - keep local
            elif n1 == a and fl1 == fla: # local unchanged - use remote
                if n1 == n2: # optimization: keep local content
                    actions.append((f, "e", (fl2,), "update permissions"))
                else:
                    actions.append((f, "g", (fl2,), "remote is newer"))
            elif nol and n2 == a: # remote only changed 'x'
                actions.append((f, "e", (fl2,), "update permissions"))
            elif nol and n1 == a: # local only changed 'x'
                actions.append((f, "g", (fl1,), "remote is newer"))
            else: # both changed something
                actions.append((f, "m", (f, f, False), "versions differ"))
        elif f in copied: # files we'll deal with on m2 side
            pass
        elif n1 and f in movewithdir: # directory rename
            f2 = movewithdir[f]
            actions.append((f, "d", (None, f2, fl1),
                            "remote renamed directory to " + f2))
        elif n1 and f in copy:
            f2 = copy[f]
            actions.append((f, "m", (f2, f, False),
                            "local copied/moved to " + f2))
        elif n1 and f in ma: # clean, a different, no remote
            if n1 != ma[f]:
                if acceptremote:
                    actions.append((f, "r", None, "remote delete"))
                else:
                    actions.append((f, "cd", None, "prompt changed/deleted"))
            elif n1[20:] == "a": # added, no remote
                actions.append((f, "f", None, "remote deleted"))
            else:
                actions.append((f, "r", None, "other deleted"))
        elif n2 and f in movewithdir:
            f2 = movewithdir[f]
            actions.append((None, "d", (f, f2, fl2),
                            "local renamed directory to " + f2))
        elif n2 and f in copy:
            f2 = copy[f]
            if f2 in m2:
                actions.append((f2, "m", (f, f, False),
                                "remote copied to " + f))
            else:
                actions.append((f2, "m", (f, f, True),
                                "remote moved to " + f))
        elif n2 and f not in ma:
            # local unknown, remote created: the logic is described by the
            # following table:
            #
            # force  branchmerge  different  |  action
            #   n         *           n      |    get
            #   n         *           y      |   abort
            #   y         n           *      |    get
            #   y         y           n      |    get
            #   y         y           y      |   merge
            #
            # Checking whether the files are different is expensive, so we
            # don't do that when we can avoid it.
            if force and not branchmerge:
                actions.append((f, "g", (fl2,), "remote created"))
            else:
                different = _checkunknownfile(repo, wctx, p2, f)
                if force and branchmerge and different:
                    actions.append((f, "m", (f, f, False),
                                    "remote differs from untracked local"))
                elif not force and different:
                    aborts.append((f, "ud"))
                else:
                    actions.append((f, "g", (fl2,), "remote created"))
        elif n2 and n2 != ma[f]:
            different = _checkunknownfile(repo, wctx, p2, f)
            if not force and different:
                aborts.append((f, "ud"))
            else:
                # if different: old untracked f may be overwritten and lost
                if acceptremote:
                    actions.append((f, "g", (m2.flags(f),),
                                   "remote recreating"))
                else:
                    actions.append((f, "dc", (m2.flags(f),),
                                   "prompt deleted/changed"))

    for f, m in sorted(aborts):
        if m == "ud":
            repo.ui.warn(_("%s: untracked file differs\n") % f)
        else: assert False, m
    if aborts:
        raise util.Abort(_("untracked files in working directory differ "
                           "from files in requested revision"))

    if not util.checkcase(repo.path):
        # check collision between files only in p2 for clean update
        if (not branchmerge and
            (force or not wctx.dirty(missing=True, branch=False))):
            _checkcollision(repo, m2, [])
        else:
            _checkcollision(repo, m1, actions)

    return actions

def actionkey(a):
    return a[1] in "rf" and -1 or 0, a

def getremove(repo, mctx, overwrite, args):
    """apply usually-non-interactive updates to the working directory

    mctx is the context to be merged into the working copy

    yields tuples for progress updates
    """
    verbose = repo.ui.verbose
    unlink = util.unlinkpath
    wjoin = repo.wjoin
    fctx = mctx.filectx
    wwrite = repo.wwrite
    audit = repo.wopener.audit
    i = 0
    for arg in args:
        f = arg[0]
        if arg[1] == 'r':
            if verbose:
                repo.ui.note(_("removing %s\n") % f)
            audit(f)
            try:
                unlink(wjoin(f), ignoremissing=True)
            except OSError, inst:
                repo.ui.warn(_("update failed to remove %s: %s!\n") %
                             (f, inst.strerror))
        else:
            if verbose:
                repo.ui.note(_("getting %s\n") % f)
            wwrite(f, fctx(f).data(), arg[2][0])
        if i == 100:
            yield i, f
            i = 0
        i += 1
    if i > 0:
        yield i, f

def applyupdates(repo, actions, wctx, mctx, actx, overwrite):
    """apply the merge action list to the working directory

    wctx is the working copy context
    mctx is the context to be merged into the working copy
    actx is the context of the common ancestor

    Return a tuple of counts (updated, merged, removed, unresolved) that
    describes how many files were affected by the update.
    """

    updated, merged, removed, unresolved = 0, 0, 0, 0
    ms = mergestate(repo)
    ms.reset(wctx.p1().node(), mctx.node())
    moves = []
    actions.sort(key=actionkey)

    # prescan for merges
    for a in actions:
        f, m, args, msg = a
        repo.ui.debug(" %s: %s -> %s\n" % (f, msg, m))
        if m == "m": # merge
            f2, fd, move = args
            if fd == '.hgsubstate': # merged internally
                continue
            repo.ui.debug("  preserving %s for resolve of %s\n" % (f, fd))
            fcl = wctx[f]
            fco = mctx[f2]
            if mctx == actx: # backwards, use working dir parent as ancestor
                if fcl.parents():
                    fca = fcl.p1()
                else:
                    fca = repo.filectx(f, fileid=nullrev)
            else:
                fca = fcl.ancestor(fco, actx)
            if not fca:
                fca = repo.filectx(f, fileid=nullrev)
            ms.add(fcl, fco, fca, fd)
            if f != fd and move:
                moves.append(f)

    audit = repo.wopener.audit

    # remove renamed files after safely stored
    for f in moves:
        if os.path.lexists(repo.wjoin(f)):
            repo.ui.debug("removing %s\n" % f)
            audit(f)
            util.unlinkpath(repo.wjoin(f))

    numupdates = len(actions)
    workeractions = [a for a in actions if a[1] in 'gr']
    updateactions = [a for a in workeractions if a[1] == 'g']
    updated = len(updateactions)
    removeactions = [a for a in workeractions if a[1] == 'r']
    removed = len(removeactions)
    actions = [a for a in actions if a[1] not in 'gr']

    hgsub = [a[1] for a in workeractions if a[0] == '.hgsubstate']
    if hgsub and hgsub[0] == 'r':
        subrepo.submerge(repo, wctx, mctx, wctx, overwrite)

    z = 0
    prog = worker.worker(repo.ui, 0.001, getremove, (repo, mctx, overwrite),
                         removeactions)
    for i, item in prog:
        z += i
        repo.ui.progress(_('updating'), z, item=item, total=numupdates,
                         unit=_('files'))
    prog = worker.worker(repo.ui, 0.001, getremove, (repo, mctx, overwrite),
                         updateactions)
    for i, item in prog:
        z += i
        repo.ui.progress(_('updating'), z, item=item, total=numupdates,
                         unit=_('files'))

    if hgsub and hgsub[0] == 'g':
        subrepo.submerge(repo, wctx, mctx, wctx, overwrite)

    _updating = _('updating')
    _files = _('files')
    progress = repo.ui.progress

    for i, a in enumerate(actions):
        f, m, args, msg = a
        progress(_updating, z + i + 1, item=f, total=numupdates, unit=_files)
        if m == "m": # merge
            f2, fd, move = args
            if fd == '.hgsubstate': # subrepo states need updating
                subrepo.submerge(repo, wctx, mctx, wctx.ancestor(mctx),
                                 overwrite)
                continue
            audit(fd)
            r = ms.resolve(fd, wctx)
            if r is not None and r > 0:
                unresolved += 1
            else:
                if r is None:
                    updated += 1
                else:
                    merged += 1
        elif m == "d": # directory rename
            f2, fd, flags = args
            if f:
                repo.ui.note(_("moving %s to %s\n") % (f, fd))
                audit(fd)
                repo.wwrite(fd, wctx.filectx(f).data(), flags)
                util.unlinkpath(repo.wjoin(f))
            if f2:
                repo.ui.note(_("getting %s to %s\n") % (f2, fd))
                repo.wwrite(fd, mctx.filectx(f2).data(), flags)
            updated += 1
        elif m == "dr": # divergent renames
            fl, = args
            repo.ui.warn(_("note: possible conflict - %s was renamed "
                           "multiple times to:\n") % f)
            for nf in fl:
                repo.ui.warn(" %s\n" % nf)
        elif m == "rd": # rename and delete
            fl, = args
            repo.ui.warn(_("note: possible conflict - %s was deleted "
                           "and renamed to:\n") % f)
            for nf in fl:
                repo.ui.warn(" %s\n" % nf)
        elif m == "e": # exec
            flags, = args
            audit(f)
            util.setflags(repo.wjoin(f), 'l' in flags, 'x' in flags)
            updated += 1
    ms.commit()
    progress(_updating, None, total=numupdates, unit=_files)

    return updated, merged, removed, unresolved

def calculateupdates(repo, tctx, mctx, ancestor, branchmerge, force, partial,
                     acceptremote=False):
    "Calculate the actions needed to merge mctx into tctx"
    actions = []
    actions += manifestmerge(repo, tctx, mctx,
                             ancestor,
                             branchmerge, force,
                             partial, acceptremote)

    # Filter out prompts.
    newactions, prompts = [], []
    for a in actions:
        if a[1] in ("cd", "dc"):
            prompts.append(a)
        else:
            newactions.append(a)
    # Prompt and create actions. TODO: Move this towards resolve phase.
    for f, m, args, msg in sorted(prompts):
        if m == "cd":
            if repo.ui.promptchoice(
                _("local changed %s which remote deleted\n"
                  "use (c)hanged version or (d)elete?"
                  "$$ &Changed $$ &Delete") % f, 0):
                newactions.append((f, "r", None, "prompt delete"))
            else:
                newactions.append((f, "a", None, "prompt keep"))
        elif m == "dc":
            flags, = args
            if repo.ui.promptchoice(
                _("remote changed %s which local deleted\n"
                  "use (c)hanged version or leave (d)eleted?"
                  "$$ &Changed $$ &Deleted") % f, 0) == 0:
                newactions.append((f, "g", (flags,), "prompt recreating"))
        else: assert False, m

    if tctx.rev() is None:
        newactions += _forgetremoved(tctx, mctx, branchmerge)

    return newactions

def recordupdates(repo, actions, branchmerge):
    "record merge actions to the dirstate"

    for a in actions:
        f, m, args, msg = a
        if m == "r": # remove
            if branchmerge:
                repo.dirstate.remove(f)
            else:
                repo.dirstate.drop(f)
        elif m == "a": # re-add
            if not branchmerge:
                repo.dirstate.add(f)
        elif m == "f": # forget
            repo.dirstate.drop(f)
        elif m == "e": # exec change
            repo.dirstate.normallookup(f)
        elif m == "g": # get
            if branchmerge:
                repo.dirstate.otherparent(f)
            else:
                repo.dirstate.normal(f)
        elif m == "m": # merge
            f2, fd, move = args
            if branchmerge:
                # We've done a branch merge, mark this file as merged
                # so that we properly record the merger later
                repo.dirstate.merge(fd)
                if f != f2: # copy/rename
                    if move:
                        repo.dirstate.remove(f)
                    if f != fd:
                        repo.dirstate.copy(f, fd)
                    else:
                        repo.dirstate.copy(f2, fd)
            else:
                # We've update-merged a locally modified file, so
                # we set the dirstate to emulate a normal checkout
                # of that file some time in the past. Thus our
                # merge will appear as a normal local file
                # modification.
                if f2 == fd: # file not locally copied/moved
                    repo.dirstate.normallookup(fd)
                if move:
                    repo.dirstate.drop(f)
        elif m == "d": # directory rename
            f2, fd, flag = args
            if not f2 and f not in repo.dirstate:
                # untracked file moved
                continue
            if branchmerge:
                repo.dirstate.add(fd)
                if f:
                    repo.dirstate.remove(f)
                    repo.dirstate.copy(f, fd)
                if f2:
                    repo.dirstate.copy(f2, fd)
            else:
                repo.dirstate.normal(fd)
                if f:
                    repo.dirstate.drop(f)

def update(repo, node, branchmerge, force, partial, ancestor=None,
           mergeancestor=False):
    """
    Perform a merge between the working directory and the given node

    node = the node to update to, or None if unspecified
    branchmerge = whether to merge between branches
    force = whether to force branch merging or file overwriting
    partial = a function to filter file lists (dirstate not updated)
    mergeancestor = whether it is merging with an ancestor. If true,
      we should accept the incoming changes for any prompts that occur.
      If false, merging with an ancestor (fast-forward) is only allowed
      between different named branches. This flag is used by rebase extension
      as a temporary fix and should be avoided in general.

    The table below shows all the behaviors of the update command
    given the -c and -C or no options, whether the working directory
    is dirty, whether a revision is specified, and the relationship of
    the parent rev to the target rev (linear, on the same named
    branch, or on another named branch).

    This logic is tested by test-update-branches.t.

    -c  -C  dirty  rev  |  linear   same  cross
     n   n    n     n   |    ok     (1)     x
     n   n    n     y   |    ok     ok     ok
     n   n    y     n   |   merge   (2)    (2)
     n   n    y     y   |   merge   (3)    (3)
     n   y    *     *   |    ---  discard  ---
     y   n    y     *   |    ---    (4)    ---
     y   n    n     *   |    ---    ok     ---
     y   y    *     *   |    ---    (5)    ---

    x = can't happen
    * = don't-care
    1 = abort: not a linear update (merge or update --check to force update)
    2 = abort: uncommitted changes (commit and merge, or update --clean to
                 discard changes)
    3 = abort: uncommitted changes (commit or update --clean to discard changes)
    4 = abort: uncommitted changes (checked in commands.py)
    5 = incompatible options (checked in commands.py)

    Return the same tuple as applyupdates().
    """

    onode = node
    wlock = repo.wlock()
    try:
        wc = repo[None]
        pl = wc.parents()
        p1 = pl[0]
        pa = None
        if ancestor:
            pa = repo[ancestor]

        if node is None:
            # Here is where we should consider bookmarks, divergent bookmarks,
            # foreground changesets (successors), and tip of current branch;
            # but currently we are only checking the branch tips.
            try:
                node = repo.branchtip(wc.branch())
            except error.RepoLookupError:
                if wc.branch() == "default": # no default branch!
                    node = repo.lookup("tip") # update to tip
                else:
                    raise util.Abort(_("branch %s not found") % wc.branch())

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
                    node = repo.revs("max(%ln)", successors)[0]
                    pa = p1

        overwrite = force and not branchmerge

        p2 = repo[node]
        if pa is None:
            pa = p1.ancestor(p2)

        fp1, fp2, xp1, xp2 = p1.node(), p2.node(), str(p1), str(p2)

        ### check phase
        if not overwrite and len(pl) > 1:
            raise util.Abort(_("outstanding uncommitted merges"))
        if branchmerge:
            if pa == p2:
                raise util.Abort(_("merging with a working directory ancestor"
                                   " has no effect"))
            elif pa == p1:
                if not mergeancestor and p1.branch() == p2.branch():
                    raise util.Abort(_("nothing to merge"),
                                     hint=_("use 'hg update' "
                                            "or check 'hg heads'"))
            if not force and (wc.files() or wc.deleted()):
                raise util.Abort(_("uncommitted changes"),
                                 hint=_("use 'hg status' to list changes"))
            for s in sorted(wc.substate):
                if wc.sub(s).dirty():
                    raise util.Abort(_("uncommitted changes in "
                                       "subrepository '%s'") % s)

        elif not overwrite:
            if p1 == p2: # no-op update
                # call the hooks and exit early
                repo.hook('preupdate', throw=True, parent1=xp2, parent2='')
                repo.hook('update', parent1=xp2, parent2='', error=0)
                return 0, 0, 0, 0

            if pa not in (p1, p2):  # nonlinear
                dirty = wc.dirty(missing=True)
                if dirty or onode is None:
                    # Branching is a bit strange to ensure we do the minimal
                    # amount of call to obsolete.background.
                    foreground = obsolete.foreground(repo, [p1.node()])
                    # note: the <node> variable contains a random identifier
                    if repo[node].node() in foreground:
                        pa = p1  # allow updating to successors
                    elif dirty:
                        msg = _("uncommitted changes")
                        if onode is None:
                            hint = _("commit and merge, or update --clean to"
                                     " discard changes")
                        else:
                            hint = _("commit or update --clean to discard"
                                     " changes")
                        raise util.Abort(msg, hint=hint)
                    else:  # node is none
                        msg = _("not a linear update")
                        hint = _("merge or update --check to force update")
                        raise util.Abort(msg, hint=hint)
                else:
                    # Allow jumping branches if clean and specific rev given
                    pa = p1

        ### calculate phase
        actions = calculateupdates(repo, wc, p2, pa,
                                   branchmerge, force, partial, mergeancestor)

        ### apply phase
        if not branchmerge: # just jump to the new rev
            fp1, fp2, xp1, xp2 = fp2, nullid, xp2, ''
        if not partial:
            repo.hook('preupdate', throw=True, parent1=xp1, parent2=xp2)
            # note that we're in the middle of an update
            repo.vfs.write('updatestate', p2.hex())

        stats = applyupdates(repo, actions, wc, p2, pa, overwrite)

        if not partial:
            repo.setparents(fp1, fp2)
            recordupdates(repo, actions, branchmerge)
            # update completed, clear state
            util.unlink(repo.join('updatestate'))

            if not branchmerge:
                repo.dirstate.setbranch(p2.branch())
    finally:
        wlock.release()

    if not partial:
        repo.hook('update', parent1=xp1, parent2=xp2, error=stats[3])
    return stats
