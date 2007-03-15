# queue.py - patch queues for mercurial
#
# Copyright 2005, 2006 Chris Mason <mason@suse.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

'''patch management and development

This extension lets you work with a stack of patches in a Mercurial
repository.  It manages two stacks of patches - all known patches, and
applied patches (subset of known patches).

Known patches are represented as patch files in the .hg/patches
directory.  Applied patches are both patch files and changesets.

Common tasks (use "hg help command" for more details):

prepare repository to work with patches   qinit
create new patch                          qnew
import existing patch                     qimport

print patch series                        qseries
print applied patches                     qapplied
print name of top applied patch           qtop

add known patch to applied stack          qpush
remove patch from applied stack           qpop
refresh contents of top applied patch     qrefresh
'''

from mercurial.i18n import _
from mercurial import commands, cmdutil, hg, patch, revlog, util, changegroup
import os, sys, re, errno

commands.norepo += " qclone qversion"

# Patch names looks like unix-file names.
# They must be joinable with queue directory and result in the patch path.
normname = util.normpath

class statusentry:
    def __init__(self, rev, name=None):
        if not name:
            fields = rev.split(':', 1)
            if len(fields) == 2:
                self.rev, self.name = fields
            else:
                self.rev, self.name = None, None
        else:
            self.rev, self.name = rev, name

    def __str__(self):
        return self.rev + ':' + self.name

class queue:
    def __init__(self, ui, path, patchdir=None):
        self.basepath = path
        self.path = patchdir or os.path.join(path, "patches")
        self.opener = util.opener(self.path)
        self.ui = ui
        self.applied = []
        self.full_series = []
        self.applied_dirty = 0
        self.series_dirty = 0
        self.series_path = "series"
        self.status_path = "status"
        self.guards_path = "guards"
        self.active_guards = None
        self.guards_dirty = False
        self._diffopts = None

        if os.path.exists(self.join(self.series_path)):
            self.full_series = self.opener(self.series_path).read().splitlines()
        self.parse_series()

        if os.path.exists(self.join(self.status_path)):
            lines = self.opener(self.status_path).read().splitlines()
            self.applied = [statusentry(l) for l in lines]

    def diffopts(self):
        if self._diffopts is None:
            self._diffopts = patch.diffopts(self.ui)
        return self._diffopts

    def join(self, *p):
        return os.path.join(self.path, *p)

    def find_series(self, patch):
        pre = re.compile("(\s*)([^#]+)")
        index = 0
        for l in self.full_series:
            m = pre.match(l)
            if m:
                s = m.group(2)
                s = s.rstrip()
                if s == patch:
                    return index
            index += 1
        return None

    guard_re = re.compile(r'\s?#([-+][^-+# \t\r\n\f][^# \t\r\n\f]*)')

    def parse_series(self):
        self.series = []
        self.series_guards = []
        for l in self.full_series:
            h = l.find('#')
            if h == -1:
                patch = l
                comment = ''
            elif h == 0:
                continue
            else:
                patch = l[:h]
                comment = l[h:]
            patch = patch.strip()
            if patch:
                if patch in self.series:
                    raise util.Abort(_('%s appears more than once in %s') %
                                     (patch, self.join(self.series_path)))
                self.series.append(patch)
                self.series_guards.append(self.guard_re.findall(comment))

    def check_guard(self, guard):
        bad_chars = '# \t\r\n\f'
        first = guard[0]
        for c in '-+':
            if first == c:
                return (_('guard %r starts with invalid character: %r') %
                        (guard, c))
        for c in bad_chars:
            if c in guard:
                return _('invalid character in guard %r: %r') % (guard, c)

    def set_active(self, guards):
        for guard in guards:
            bad = self.check_guard(guard)
            if bad:
                raise util.Abort(bad)
        guards = dict.fromkeys(guards).keys()
        guards.sort()
        self.ui.debug('active guards: %s\n' % ' '.join(guards))
        self.active_guards = guards
        self.guards_dirty = True

    def active(self):
        if self.active_guards is None:
            self.active_guards = []
            try:
                guards = self.opener(self.guards_path).read().split()
            except IOError, err:
                if err.errno != errno.ENOENT: raise
                guards = []
            for i, guard in enumerate(guards):
                bad = self.check_guard(guard)
                if bad:
                    self.ui.warn('%s:%d: %s\n' %
                                 (self.join(self.guards_path), i + 1, bad))
                else:
                    self.active_guards.append(guard)
        return self.active_guards

    def set_guards(self, idx, guards):
        for g in guards:
            if len(g) < 2:
                raise util.Abort(_('guard %r too short') % g)
            if g[0] not in '-+':
                raise util.Abort(_('guard %r starts with invalid char') % g)
            bad = self.check_guard(g[1:])
            if bad:
                raise util.Abort(bad)
        drop = self.guard_re.sub('', self.full_series[idx])
        self.full_series[idx] = drop + ''.join([' #' + g for g in guards])
        self.parse_series()
        self.series_dirty = True

    def pushable(self, idx):
        if isinstance(idx, str):
            idx = self.series.index(idx)
        patchguards = self.series_guards[idx]
        if not patchguards:
            return True, None
        default = False
        guards = self.active()
        exactneg = [g for g in patchguards if g[0] == '-' and g[1:] in guards]
        if exactneg:
            return False, exactneg[0]
        pos = [g for g in patchguards if g[0] == '+']
        exactpos = [g for g in pos if g[1:] in guards]
        if pos:
            if exactpos:
                return True, exactpos[0]
            return False, pos
        return True, ''

    def explain_pushable(self, idx, all_patches=False):
        write = all_patches and self.ui.write or self.ui.warn
        if all_patches or self.ui.verbose:
            if isinstance(idx, str):
                idx = self.series.index(idx)
            pushable, why = self.pushable(idx)
            if all_patches and pushable:
                if why is None:
                    write(_('allowing %s - no guards in effect\n') %
                          self.series[idx])
                else:
                    if not why:
                        write(_('allowing %s - no matching negative guards\n') %
                              self.series[idx])
                    else:
                        write(_('allowing %s - guarded by %r\n') %
                              (self.series[idx], why))
            if not pushable:
                if why:
                    write(_('skipping %s - guarded by %r\n') %
                          (self.series[idx], why))
                else:
                    write(_('skipping %s - no matching guards\n') %
                          self.series[idx])

    def save_dirty(self):
        def write_list(items, path):
            fp = self.opener(path, 'w')
            for i in items:
                print >> fp, i
            fp.close()
        if self.applied_dirty: write_list(map(str, self.applied), self.status_path)
        if self.series_dirty: write_list(self.full_series, self.series_path)
        if self.guards_dirty: write_list(self.active_guards, self.guards_path)

    def readheaders(self, patch):
        def eatdiff(lines):
            while lines:
                l = lines[-1]
                if (l.startswith("diff -") or
                    l.startswith("Index:") or
                    l.startswith("===========")):
                    del lines[-1]
                else:
                    break
        def eatempty(lines):
            while lines:
                l = lines[-1]
                if re.match('\s*$', l):
                    del lines[-1]
                else:
                    break

        pf = self.join(patch)
        message = []
        comments = []
        user = None
        date = None
        format = None
        subject = None
        diffstart = 0

        for line in file(pf):
            line = line.rstrip()
            if line.startswith('diff --git'):
                diffstart = 2
                break
            if diffstart:
                if line.startswith('+++ '):
                    diffstart = 2
                break
            if line.startswith("--- "):
                diffstart = 1
                continue
            elif format == "hgpatch":
                # parse values when importing the result of an hg export
                if line.startswith("# User "):
                    user = line[7:]
                elif line.startswith("# Date "):
                    date = line[7:]
                elif not line.startswith("# ") and line:
                    message.append(line)
                    format = None
            elif line == '# HG changeset patch':
                format = "hgpatch"
            elif (format != "tagdone" and (line.startswith("Subject: ") or
                                           line.startswith("subject: "))):
                subject = line[9:]
                format = "tag"
            elif (format != "tagdone" and (line.startswith("From: ") or
                                           line.startswith("from: "))):
                user = line[6:]
                format = "tag"
            elif format == "tag" and line == "":
                # when looking for tags (subject: from: etc) they
                # end once you find a blank line in the source
                format = "tagdone"
            elif message or line:
                message.append(line)
            comments.append(line)

        eatdiff(message)
        eatdiff(comments)
        eatempty(message)
        eatempty(comments)

        # make sure message isn't empty
        if format and format.startswith("tag") and subject:
            message.insert(0, "")
            message.insert(0, subject)
        return (message, comments, user, date, diffstart > 1)

    def removeundo(self, repo):
        undo = repo.sjoin('undo')
        if not os.path.exists(undo):
            return
        try:
            os.unlink(undo)
        except OSError, inst:
            self.ui.warn('error removing undo: %s\n' % str(inst))

    def printdiff(self, repo, node1, node2=None, files=None,
                  fp=None, changes=None, opts={}):
        fns, matchfn, anypats = cmdutil.matchpats(repo, files, opts)

        patch.diff(repo, node1, node2, fns, match=matchfn,
                   fp=fp, changes=changes, opts=self.diffopts())

    def mergeone(self, repo, mergeq, head, patch, rev, wlock):
        # first try just applying the patch
        (err, n) = self.apply(repo, [ patch ], update_status=False,
                              strict=True, merge=rev, wlock=wlock)

        if err == 0:
            return (err, n)

        if n is None:
            raise util.Abort(_("apply failed for patch %s") % patch)

        self.ui.warn("patch didn't work out, merging %s\n" % patch)

        # apply failed, strip away that rev and merge.
        hg.clean(repo, head, wlock=wlock)
        self.strip(repo, n, update=False, backup='strip', wlock=wlock)

        ctx = repo.changectx(rev)
        ret = hg.merge(repo, rev, wlock=wlock)
        if ret:
            raise util.Abort(_("update returned %d") % ret)
        n = repo.commit(None, ctx.description(), ctx.user(),
                        force=1, wlock=wlock)
        if n == None:
            raise util.Abort(_("repo commit failed"))
        try:
            message, comments, user, date, patchfound = mergeq.readheaders(patch)
        except:
            raise util.Abort(_("unable to read %s") % patch)

        patchf = self.opener(patch, "w")
        if comments:
            comments = "\n".join(comments) + '\n\n'
            patchf.write(comments)
        self.printdiff(repo, head, n, fp=patchf)
        patchf.close()
        self.removeundo(repo)
        return (0, n)

    def qparents(self, repo, rev=None):
        if rev is None:
            (p1, p2) = repo.dirstate.parents()
            if p2 == revlog.nullid:
                return p1
            if len(self.applied) == 0:
                return None
            return revlog.bin(self.applied[-1].rev)
        pp = repo.changelog.parents(rev)
        if pp[1] != revlog.nullid:
            arevs = [ x.rev for x in self.applied ]
            p0 = revlog.hex(pp[0])
            p1 = revlog.hex(pp[1])
            if p0 in arevs:
                return pp[0]
            if p1 in arevs:
                return pp[1]
        return pp[0]

    def mergepatch(self, repo, mergeq, series, wlock):
        if len(self.applied) == 0:
            # each of the patches merged in will have two parents.  This
            # can confuse the qrefresh, qdiff, and strip code because it
            # needs to know which parent is actually in the patch queue.
            # so, we insert a merge marker with only one parent.  This way
            # the first patch in the queue is never a merge patch
            #
            pname = ".hg.patches.merge.marker"
            n = repo.commit(None, '[mq]: merge marker', user=None, force=1,
                            wlock=wlock)
            self.removeundo(repo)
            self.applied.append(statusentry(revlog.hex(n), pname))
            self.applied_dirty = 1

        head = self.qparents(repo)

        for patch in series:
            patch = mergeq.lookup(patch, strict=True)
            if not patch:
                self.ui.warn("patch %s does not exist\n" % patch)
                return (1, None)
            pushable, reason = self.pushable(patch)
            if not pushable:
                self.explain_pushable(patch, all_patches=True)
                continue
            info = mergeq.isapplied(patch)
            if not info:
                self.ui.warn("patch %s is not applied\n" % patch)
                return (1, None)
            rev = revlog.bin(info[1])
            (err, head) = self.mergeone(repo, mergeq, head, patch, rev, wlock)
            if head:
                self.applied.append(statusentry(revlog.hex(head), patch))
                self.applied_dirty = 1
            if err:
                return (err, head)
        return (0, head)

    def patch(self, repo, patchfile):
        '''Apply patchfile  to the working directory.
        patchfile: file name of patch'''
        files = {}
        try:
            fuzz = patch.patch(patchfile, self.ui, strip=1, cwd=repo.root,
                               files=files)
        except Exception, inst:
            self.ui.note(str(inst) + '\n')
            if not self.ui.verbose:
                self.ui.warn("patch failed, unable to continue (try -v)\n")
            return (False, files, False)

        return (True, files, fuzz)

    def apply(self, repo, series, list=False, update_status=True,
              strict=False, patchdir=None, merge=None, wlock=None):
        # TODO unify with commands.py
        if not patchdir:
            patchdir = self.path
        err = 0
        if not wlock:
            wlock = repo.wlock()
        lock = repo.lock()
        tr = repo.transaction()
        n = None
        for patchname in series:
            pushable, reason = self.pushable(patchname)
            if not pushable:
                self.explain_pushable(patchname, all_patches=True)
                continue
            self.ui.warn("applying %s\n" % patchname)
            pf = os.path.join(patchdir, patchname)

            try:
                message, comments, user, date, patchfound = self.readheaders(patchname)
            except:
                self.ui.warn("Unable to read %s\n" % patchname)
                err = 1
                break

            if not message:
                message = "imported patch %s\n" % patchname
            else:
                if list:
                    message.append("\nimported patch %s" % patchname)
                message = '\n'.join(message)

            (patcherr, files, fuzz) = self.patch(repo, pf)
            patcherr = not patcherr

            if merge and files:
                # Mark as merged and update dirstate parent info
                repo.dirstate.update(repo.dirstate.filterfiles(files.keys()), 'm')
                p1, p2 = repo.dirstate.parents()
                repo.dirstate.setparents(p1, merge)
            files = patch.updatedir(self.ui, repo, files, wlock=wlock)
            n = repo.commit(files, message, user, date, force=1, lock=lock,
                            wlock=wlock)

            if n == None:
                raise util.Abort(_("repo commit failed"))

            if update_status:
                self.applied.append(statusentry(revlog.hex(n), patchname))

            if patcherr:
                if not patchfound:
                    self.ui.warn("patch %s is empty\n" % patchname)
                    err = 0
                else:
                    self.ui.warn("patch failed, rejects left in working dir\n")
                    err = 1
                break

            if fuzz and strict:
                self.ui.warn("fuzz found when applying patch, stopping\n")
                err = 1
                break
        tr.close()
        self.removeundo(repo)
        return (err, n)

    def delete(self, repo, patches, opts):
        realpatches = []
        for patch in patches:
            patch = self.lookup(patch, strict=True)
            info = self.isapplied(patch)
            if info:
                raise util.Abort(_("cannot delete applied patch %s") % patch)
            if patch not in self.series:
                raise util.Abort(_("patch %s not in series file") % patch)
            realpatches.append(patch)

        appliedbase = 0
        if opts.get('rev'):
            if not self.applied:
                raise util.Abort(_('no patches applied'))
            revs = cmdutil.revrange(repo, opts['rev'])
            if len(revs) > 1 and revs[0] > revs[1]:
                revs.reverse()
            for rev in revs:
                if appliedbase >= len(self.applied):
                    raise util.Abort(_("revision %d is not managed") % rev)

                base = revlog.bin(self.applied[appliedbase].rev)
                node = repo.changelog.node(rev)
                if node != base:
                    raise util.Abort(_("cannot delete revision %d above "
                                       "applied patches") % rev)
                realpatches.append(self.applied[appliedbase].name)
                appliedbase += 1

        if not opts.get('keep'):
            r = self.qrepo()
            if r:
                r.remove(realpatches, True)
            else:
                for p in realpatches:
                    os.unlink(self.join(p))

        if appliedbase:
            del self.applied[:appliedbase]
            self.applied_dirty = 1
        indices = [self.find_series(p) for p in realpatches]
        indices.sort()
        for i in indices[-1::-1]:
            del self.full_series[i]
        self.parse_series()
        self.series_dirty = 1

    def check_toppatch(self, repo):
        if len(self.applied) > 0:
            top = revlog.bin(self.applied[-1].rev)
            pp = repo.dirstate.parents()
            if top not in pp:
                raise util.Abort(_("queue top not at same revision as working directory"))
            return top
        return None
    def check_localchanges(self, repo, force=False, refresh=True):
        m, a, r, d = repo.status()[:4]
        if m or a or r or d:
            if not force:
                if refresh:
                    raise util.Abort(_("local changes found, refresh first"))
                else:
                    raise util.Abort(_("local changes found"))
        return m, a, r, d
    def new(self, repo, patch, msg=None, force=None):
        if os.path.exists(self.join(patch)):
            raise util.Abort(_('patch "%s" already exists') % patch)
        m, a, r, d = self.check_localchanges(repo, force)
        commitfiles = m + a + r
        self.check_toppatch(repo)
        wlock = repo.wlock()
        insert = self.full_series_end()
        if msg:
            n = repo.commit(commitfiles, "[mq]: %s" % msg, force=True,
                            wlock=wlock)
        else:
            n = repo.commit(commitfiles,
                            "New patch: %s" % patch, force=True, wlock=wlock)
        if n == None:
            raise util.Abort(_("repo commit failed"))
        self.full_series[insert:insert] = [patch]
        self.applied.append(statusentry(revlog.hex(n), patch))
        self.parse_series()
        self.series_dirty = 1
        self.applied_dirty = 1
        p = self.opener(patch, "w")
        if msg:
            msg = msg + "\n"
            p.write(msg)
        p.close()
        wlock = None
        r = self.qrepo()
        if r: r.add([patch])
        if commitfiles:
            self.refresh(repo, short=True)
        self.removeundo(repo)

    def strip(self, repo, rev, update=True, backup="all", wlock=None):
        def limitheads(chlog, stop):
            """return the list of all nodes that have no children"""
            p = {}
            h = []
            stoprev = 0
            if stop in chlog.nodemap:
                stoprev = chlog.rev(stop)

            for r in xrange(chlog.count() - 1, -1, -1):
                n = chlog.node(r)
                if n not in p:
                    h.append(n)
                if n == stop:
                    break
                if r < stoprev:
                    break
                for pn in chlog.parents(n):
                    p[pn] = 1
            return h

        def bundle(cg):
            backupdir = repo.join("strip-backup")
            if not os.path.isdir(backupdir):
                os.mkdir(backupdir)
            name = os.path.join(backupdir, "%s" % revlog.short(rev))
            name = savename(name)
            self.ui.warn("saving bundle to %s\n" % name)
            return changegroup.writebundle(cg, name, "HG10BZ")

        def stripall(revnum):
            mm = repo.changectx(rev).manifest()
            seen = {}

            for x in xrange(revnum, repo.changelog.count()):
                for f in repo.changectx(x).files():
                    if f in seen:
                        continue
                    seen[f] = 1
                    if f in mm:
                        filerev = mm[f]
                    else:
                        filerev = 0
                    seen[f] = filerev
            # we go in two steps here so the strip loop happens in a
            # sensible order.  When stripping many files, this helps keep
            # our disk access patterns under control.
            seen_list = seen.keys()
            seen_list.sort()
            for f in seen_list:
                ff = repo.file(f)
                filerev = seen[f]
                if filerev != 0:
                    if filerev in ff.nodemap:
                        filerev = ff.rev(filerev)
                    else:
                        filerev = 0
                ff.strip(filerev, revnum)

        if not wlock:
            wlock = repo.wlock()
        lock = repo.lock()
        chlog = repo.changelog
        # TODO delete the undo files, and handle undo of merge sets
        pp = chlog.parents(rev)
        revnum = chlog.rev(rev)

        if update:
            self.check_localchanges(repo, refresh=False)
            urev = self.qparents(repo, rev)
            hg.clean(repo, urev, wlock=wlock)
            repo.dirstate.write()

        # save is a list of all the branches we are truncating away
        # that we actually want to keep.  changegroup will be used
        # to preserve them and add them back after the truncate
        saveheads = []
        savebases = {}

        heads = limitheads(chlog, rev)
        seen = {}

        # search through all the heads, finding those where the revision
        # we want to strip away is an ancestor.  Also look for merges
        # that might be turned into new heads by the strip.
        while heads:
            h = heads.pop()
            n = h
            while True:
                seen[n] = 1
                pp = chlog.parents(n)
                if pp[1] != revlog.nullid:
                    for p in pp:
                        if chlog.rev(p) > revnum and p not in seen:
                            heads.append(p)
                if pp[0] == revlog.nullid:
                    break
                if chlog.rev(pp[0]) < revnum:
                    break
                n = pp[0]
                if n == rev:
                    break
            r = chlog.reachable(h, rev)
            if rev not in r:
                saveheads.append(h)
                for x in r:
                    if chlog.rev(x) > revnum:
                        savebases[x] = 1

        # create a changegroup for all the branches we need to keep
        if backup == "all":
            backupch = repo.changegroupsubset([rev], chlog.heads(), 'strip')
            bundle(backupch)
        if saveheads:
            backupch = repo.changegroupsubset(savebases.keys(), saveheads, 'strip')
            chgrpfile = bundle(backupch)

        stripall(revnum)

        change = chlog.read(rev)
        chlog.strip(revnum, revnum)
        repo.manifest.strip(repo.manifest.rev(change[0]), revnum)
        self.removeundo(repo)
        if saveheads:
            self.ui.status("adding branch\n")
            commands.unbundle(self.ui, repo, "file:%s" % chgrpfile,
                              update=False)
            if backup != "strip":
                os.unlink(chgrpfile)

    def isapplied(self, patch):
        """returns (index, rev, patch)"""
        for i in xrange(len(self.applied)):
            a = self.applied[i]
            if a.name == patch:
                return (i, a.rev, a.name)
        return None

    # if the exact patch name does not exist, we try a few
    # variations.  If strict is passed, we try only #1
    #
    # 1) a number to indicate an offset in the series file
    # 2) a unique substring of the patch name was given
    # 3) patchname[-+]num to indicate an offset in the series file
    def lookup(self, patch, strict=False):
        patch = patch and str(patch)

        def partial_name(s):
            if s in self.series:
                return s
            matches = [x for x in self.series if s in x]
            if len(matches) > 1:
                self.ui.warn(_('patch name "%s" is ambiguous:\n') % s)
                for m in matches:
                    self.ui.warn('  %s\n' % m)
                return None
            if matches:
                return matches[0]
            if len(self.series) > 0 and len(self.applied) > 0:
                if s == 'qtip':
                    return self.series[self.series_end(True)-1]
                if s == 'qbase':
                    return self.series[0]
            return None
        if patch == None:
            return None

        # we don't want to return a partial match until we make
        # sure the file name passed in does not exist (checked below)
        res = partial_name(patch)
        if res and res == patch:
            return res

        if not os.path.isfile(self.join(patch)):
            try:
                sno = int(patch)
            except(ValueError, OverflowError):
                pass
            else:
                if sno < len(self.series):
                    return self.series[sno]
            if not strict:
                # return any partial match made above
                if res:
                    return res
                minus = patch.rfind('-')
                if minus >= 0:
                    res = partial_name(patch[:minus])
                    if res:
                        i = self.series.index(res)
                        try:
                            off = int(patch[minus+1:] or 1)
                        except(ValueError, OverflowError):
                            pass
                        else:
                            if i - off >= 0:
                                return self.series[i - off]
                plus = patch.rfind('+')
                if plus >= 0:
                    res = partial_name(patch[:plus])
                    if res:
                        i = self.series.index(res)
                        try:
                            off = int(patch[plus+1:] or 1)
                        except(ValueError, OverflowError):
                            pass
                        else:
                            if i + off < len(self.series):
                                return self.series[i + off]
        raise util.Abort(_("patch %s not in series") % patch)

    def push(self, repo, patch=None, force=False, list=False,
             mergeq=None, wlock=None):
        if not wlock:
            wlock = repo.wlock()
        patch = self.lookup(patch)
        # Suppose our series file is: A B C and the current 'top' patch is B.
        # qpush C should be performed (moving forward)
        # qpush B is a NOP (no change)
        # qpush A is an error (can't go backwards with qpush)
        if patch:
            info = self.isapplied(patch)
            if info:
                if info[0] < len(self.applied) - 1:
                    raise util.Abort(_("cannot push to a previous patch: %s") %
                                     patch)
                if info[0] < len(self.series) - 1:
                    self.ui.warn(_('qpush: %s is already at the top\n') % patch)
                else:
                    self.ui.warn(_('all patches are currently applied\n'))
                return

        # Following the above example, starting at 'top' of B:
        #  qpush should be performed (pushes C), but a subsequent qpush without
        #  an argument is an error (nothing to apply). This allows a loop
        #  of "...while hg qpush..." to work as it detects an error when done
        if self.series_end() == len(self.series):
            self.ui.warn(_('patch series already fully applied\n'))
            return 1
        if not force:
            self.check_localchanges(repo)

        self.applied_dirty = 1;
        start = self.series_end()
        if start > 0:
            self.check_toppatch(repo)
        if not patch:
            patch = self.series[start]
            end = start + 1
        else:
            end = self.series.index(patch, start) + 1
        s = self.series[start:end]
        if mergeq:
            ret = self.mergepatch(repo, mergeq, s, wlock)
        else:
            ret = self.apply(repo, s, list, wlock=wlock)
        top = self.applied[-1].name
        if ret[0]:
            self.ui.write("Errors during apply, please fix and refresh %s\n" %
                          top)
        else:
            self.ui.write("Now at: %s\n" % top)
        return ret[0]

    def pop(self, repo, patch=None, force=False, update=True, all=False,
            wlock=None):
        def getfile(f, rev):
            t = repo.file(f).read(rev)
            repo.wfile(f, "w").write(t)

        if not wlock:
            wlock = repo.wlock()
        if patch:
            # index, rev, patch
            info = self.isapplied(patch)
            if not info:
                patch = self.lookup(patch)
            info = self.isapplied(patch)
            if not info:
                raise util.Abort(_("patch %s is not applied") % patch)

        if len(self.applied) == 0:
            # Allow qpop -a to work repeatedly,
            # but not qpop without an argument
            self.ui.warn(_("no patches applied\n"))
            return not all

        if not update:
            parents = repo.dirstate.parents()
            rr = [ revlog.bin(x.rev) for x in self.applied ]
            for p in parents:
                if p in rr:
                    self.ui.warn("qpop: forcing dirstate update\n")
                    update = True

        if not force and update:
            self.check_localchanges(repo)

        self.applied_dirty = 1;
        end = len(self.applied)
        if not patch:
            if all:
                popi = 0
            else:
                popi = len(self.applied) - 1
        else:
            popi = info[0] + 1
            if popi >= end:
                self.ui.warn("qpop: %s is already at the top\n" % patch)
                return
        info = [ popi ] + [self.applied[popi].rev, self.applied[popi].name]

        start = info[0]
        rev = revlog.bin(info[1])

        # we know there are no local changes, so we can make a simplified
        # form of hg.update.
        if update:
            top = self.check_toppatch(repo)
            qp = self.qparents(repo, rev)
            changes = repo.changelog.read(qp)
            mmap = repo.manifest.read(changes[0])
            m, a, r, d, u = repo.status(qp, top)[:5]
            if d:
                raise util.Abort("deletions found between repo revs")
            for f in m:
                getfile(f, mmap[f])
            for f in r:
                getfile(f, mmap[f])
                util.set_exec(repo.wjoin(f), mmap.execf(f))
            repo.dirstate.update(m + r, 'n')
            for f in a:
                try:
                    os.unlink(repo.wjoin(f))
                except OSError, e:
                    if e.errno != errno.ENOENT:
                        raise
                try: os.removedirs(os.path.dirname(repo.wjoin(f)))
                except: pass
            if a:
                repo.dirstate.forget(a)
            repo.dirstate.setparents(qp, revlog.nullid)
        self.strip(repo, rev, update=False, backup='strip', wlock=wlock)
        del self.applied[start:end]
        if len(self.applied):
            self.ui.write("Now at: %s\n" % self.applied[-1].name)
        else:
            self.ui.write("Patch queue now empty\n")

    def diff(self, repo, pats, opts):
        top = self.check_toppatch(repo)
        if not top:
            self.ui.write("No patches applied\n")
            return
        qp = self.qparents(repo, top)
        if opts.get('git'):
            self.diffopts().git = True
        self.printdiff(repo, qp, files=pats, opts=opts)

    def refresh(self, repo, pats=None, **opts):
        if len(self.applied) == 0:
            self.ui.write("No patches applied\n")
            return 1
        wlock = repo.wlock()
        self.check_toppatch(repo)
        (top, patchfn) = (self.applied[-1].rev, self.applied[-1].name)
        top = revlog.bin(top)
        cparents = repo.changelog.parents(top)
        patchparent = self.qparents(repo, top)
        message, comments, user, date, patchfound = self.readheaders(patchfn)

        patchf = self.opener(patchfn, "w")
        msg = opts.get('msg', '').rstrip()
        if msg:
            if comments:
                # Remove existing message.
                ci = 0
                for mi in xrange(len(message)):
                    while message[mi] != comments[ci]:
                        ci += 1
                    del comments[ci]
            comments.append(msg)
        if comments:
            comments = "\n".join(comments) + '\n\n'
            patchf.write(comments)

        if opts.get('git'):
            self.diffopts().git = True
        fns, matchfn, anypats = cmdutil.matchpats(repo, pats, opts)
        tip = repo.changelog.tip()
        if top == tip:
            # if the top of our patch queue is also the tip, there is an
            # optimization here.  We update the dirstate in place and strip
            # off the tip commit.  Then just commit the current directory
            # tree.  We can also send repo.commit the list of files
            # changed to speed up the diff
            #
            # in short mode, we only diff the files included in the
            # patch already
            #
            # this should really read:
            #   mm, dd, aa, aa2, uu = repo.status(tip, patchparent)[:5]
            # but we do it backwards to take advantage of manifest/chlog
            # caching against the next repo.status call
            #
            mm, aa, dd, aa2, uu = repo.status(patchparent, tip)[:5]
            changes = repo.changelog.read(tip)
            man = repo.manifest.read(changes[0])
            aaa = aa[:]
            if opts.get('short'):
                filelist = mm + aa + dd
            else:
                filelist = None
            m, a, r, d, u = repo.status(files=filelist)[:5]

            # we might end up with files that were added between tip and
            # the dirstate parent, but then changed in the local dirstate.
            # in this case, we want them to only show up in the added section
            for x in m:
                if x not in aa:
                    mm.append(x)
            # we might end up with files added by the local dirstate that
            # were deleted by the patch.  In this case, they should only
            # show up in the changed section.
            for x in a:
                if x in dd:
                    del dd[dd.index(x)]
                    mm.append(x)
                else:
                    aa.append(x)
            # make sure any files deleted in the local dirstate
            # are not in the add or change column of the patch
            forget = []
            for x in d + r:
                if x in aa:
                    del aa[aa.index(x)]
                    forget.append(x)
                    continue
                elif x in mm:
                    del mm[mm.index(x)]
                dd.append(x)

            m = util.unique(mm)
            r = util.unique(dd)
            a = util.unique(aa)
            c = [filter(matchfn, l) for l in (m, a, r, [], u)]
            filelist = util.unique(c[0] + c[1] + c[2])
            patch.diff(repo, patchparent, files=filelist, match=matchfn,
                       fp=patchf, changes=c, opts=self.diffopts())
            patchf.close()

            repo.dirstate.setparents(*cparents)
            copies = {}
            for dst in a:
                src = repo.dirstate.copied(dst)
                if src is None:
                    continue
                copies.setdefault(src, []).append(dst)
            repo.dirstate.update(a, 'a')
            # remember the copies between patchparent and tip
            # this may be slow, so don't do it if we're not tracking copies
            if self.diffopts().git:
                for dst in aaa:
                    f = repo.file(dst)
                    src = f.renamed(man[dst])
                    if src:
                        copies[src[0]] = copies.get(dst, [])
                        if dst in a:
                            copies[src[0]].append(dst)
                    # we can't copy a file created by the patch itself
                    if dst in copies:
                        del copies[dst]
            for src, dsts in copies.iteritems():
                for dst in dsts:
                    repo.dirstate.copy(src, dst)
            repo.dirstate.update(r, 'r')
            # if the patch excludes a modified file, mark that file with mtime=0
            # so status can see it.
            mm = []
            for i in xrange(len(m)-1, -1, -1):
                if not matchfn(m[i]):
                    mm.append(m[i])
                    del m[i]
            repo.dirstate.update(m, 'n')
            repo.dirstate.update(mm, 'n', st_mtime=-1, st_size=-1)
            repo.dirstate.forget(forget)

            if not msg:
                if not message:
                    message = "patch queue: %s\n" % patchfn
                else:
                    message = "\n".join(message)
            else:
                message = msg

            self.strip(repo, top, update=False, backup='strip', wlock=wlock)
            n = repo.commit(filelist, message, changes[1], match=matchfn,
                            force=1, wlock=wlock)
            self.applied[-1] = statusentry(revlog.hex(n), patchfn)
            self.applied_dirty = 1
            self.removeundo(repo)
        else:
            self.printdiff(repo, patchparent, fp=patchf)
            patchf.close()
            added = repo.status()[1]
            for a in added:
                f = repo.wjoin(a)
                try:
                    os.unlink(f)
                except OSError, e:
                    if e.errno != errno.ENOENT:
                        raise
                try: os.removedirs(os.path.dirname(f))
                except: pass
            # forget the file copies in the dirstate
            # push should readd the files later on
            repo.dirstate.forget(added)
            self.pop(repo, force=True, wlock=wlock)
            self.push(repo, force=True, wlock=wlock)

    def init(self, repo, create=False):
        if not create and os.path.isdir(self.path):
            raise util.Abort(_("patch queue directory already exists"))
        try:
            os.mkdir(self.path)
        except OSError, inst:
            if inst.errno != errno.EEXIST or not create:
                raise
        if create:
            return self.qrepo(create=True)

    def unapplied(self, repo, patch=None):
        if patch and patch not in self.series:
            raise util.Abort(_("patch %s is not in series file") % patch)
        if not patch:
            start = self.series_end()
        else:
            start = self.series.index(patch) + 1
        unapplied = []
        for i in xrange(start, len(self.series)):
            pushable, reason = self.pushable(i)
            if pushable:
                unapplied.append((i, self.series[i]))
            self.explain_pushable(i)
        return unapplied

    def qseries(self, repo, missing=None, start=0, length=0, status=None,
                summary=False):
        def displayname(patchname):
            if summary:
                msg = self.readheaders(patchname)[0]
                msg = msg and ': ' + msg[0] or ': '
            else:
                msg = ''
            return '%s%s' % (patchname, msg)

        def pname(i):
            if status == 'A':
                return self.applied[i].name
            else:
                return self.series[i]

        applied = dict.fromkeys([p.name for p in self.applied])
        if not length:
            length = len(self.series) - start
        if not missing:
            for i in xrange(start, start+length):
                pfx = ''
                patch = pname(i)
                if self.ui.verbose:
                    if patch in applied:
                        stat = 'A'
                    elif self.pushable(i)[0]:
                        stat = 'U'
                    else:
                        stat = 'G'
                    pfx = '%d %s ' % (i, stat)
                self.ui.write('%s%s\n' % (pfx, displayname(patch)))
        else:
            msng_list = []
            for root, dirs, files in os.walk(self.path):
                d = root[len(self.path) + 1:]
                for f in files:
                    fl = os.path.join(d, f)
                    if (fl not in self.series and
                        fl not in (self.status_path, self.series_path)
                        and not fl.startswith('.')):
                        msng_list.append(fl)
            msng_list.sort()
            for x in msng_list:
                pfx = self.ui.verbose and ('D ') or ''
                self.ui.write("%s%s\n" % (pfx, displayname(x)))

    def issaveline(self, l):
        if l.name == '.hg.patches.save.line':
            return True

    def qrepo(self, create=False):
        if create or os.path.isdir(self.join(".hg")):
            return hg.repository(self.ui, path=self.path, create=create)

    def restore(self, repo, rev, delete=None, qupdate=None):
        c = repo.changelog.read(rev)
        desc = c[4].strip()
        lines = desc.splitlines()
        i = 0
        datastart = None
        series = []
        applied = []
        qpp = None
        for i in xrange(0, len(lines)):
            if lines[i] == 'Patch Data:':
                datastart = i + 1
            elif lines[i].startswith('Dirstate:'):
                l = lines[i].rstrip()
                l = l[10:].split(' ')
                qpp = [ hg.bin(x) for x in l ]
            elif datastart != None:
                l = lines[i].rstrip()
                se = statusentry(l)
                file_ = se.name
                if se.rev:
                    applied.append(se)
                else:
                    series.append(file_)
        if datastart == None:
            self.ui.warn("No saved patch data found\n")
            return 1
        self.ui.warn("restoring status: %s\n" % lines[0])
        self.full_series = series
        self.applied = applied
        self.parse_series()
        self.series_dirty = 1
        self.applied_dirty = 1
        heads = repo.changelog.heads()
        if delete:
            if rev not in heads:
                self.ui.warn("save entry has children, leaving it alone\n")
            else:
                self.ui.warn("removing save entry %s\n" % hg.short(rev))
                pp = repo.dirstate.parents()
                if rev in pp:
                    update = True
                else:
                    update = False
                self.strip(repo, rev, update=update, backup='strip')
        if qpp:
            self.ui.warn("saved queue repository parents: %s %s\n" %
                         (hg.short(qpp[0]), hg.short(qpp[1])))
            if qupdate:
                print "queue directory updating"
                r = self.qrepo()
                if not r:
                    self.ui.warn("Unable to load queue repository\n")
                    return 1
                hg.clean(r, qpp[0])

    def save(self, repo, msg=None):
        if len(self.applied) == 0:
            self.ui.warn("save: no patches applied, exiting\n")
            return 1
        if self.issaveline(self.applied[-1]):
            self.ui.warn("status is already saved\n")
            return 1

        ar = [ ':' + x for x in self.full_series ]
        if not msg:
            msg = "hg patches saved state"
        else:
            msg = "hg patches: " + msg.rstrip('\r\n')
        r = self.qrepo()
        if r:
            pp = r.dirstate.parents()
            msg += "\nDirstate: %s %s" % (hg.hex(pp[0]), hg.hex(pp[1]))
        msg += "\n\nPatch Data:\n"
        text = msg + "\n".join([str(x) for x in self.applied]) + '\n' + (ar and
                   "\n".join(ar) + '\n' or "")
        n = repo.commit(None, text, user=None, force=1)
        if not n:
            self.ui.warn("repo commit failed\n")
            return 1
        self.applied.append(statusentry(revlog.hex(n),'.hg.patches.save.line'))
        self.applied_dirty = 1
        self.removeundo(repo)

    def full_series_end(self):
        if len(self.applied) > 0:
            p = self.applied[-1].name
            end = self.find_series(p)
            if end == None:
                return len(self.full_series)
            return end + 1
        return 0

    def series_end(self, all_patches=False):
        end = 0
        def next(start):
            if all_patches:
                return start
            i = start
            while i < len(self.series):
                p, reason = self.pushable(i)
                if p:
                    break
                self.explain_pushable(i)
                i += 1
            return i
        if len(self.applied) > 0:
            p = self.applied[-1].name
            try:
                end = self.series.index(p)
            except ValueError:
                return 0
            return next(end + 1)
        return next(end)

    def appliedname(self, index):
        pname = self.applied[index].name
        if not self.ui.verbose:
            p = pname
        else:
            p = str(self.series.index(pname)) + " " + pname
        return p

    def qimport(self, repo, files, patchname=None, rev=None, existing=None,
                force=None, git=False):
        def checkseries(patchname):
            if patchname in self.series:
                raise util.Abort(_('patch %s is already in the series file')
                                 % patchname)
        def checkfile(patchname):
            if not force and os.path.exists(self.join(patchname)):
                raise util.Abort(_('patch "%s" already exists')
                                 % patchname)

        if rev:
            if files:
                raise util.Abort(_('option "-r" not valid when importing '
                                   'files'))
            rev = cmdutil.revrange(repo, rev)
            rev.sort(lambda x, y: cmp(y, x))
        if (len(files) > 1 or len(rev) > 1) and patchname:
            raise util.Abort(_('option "-n" not valid when importing multiple '
                               'patches'))
        i = 0
        added = []
        if rev:
            # If mq patches are applied, we can only import revisions
            # that form a linear path to qbase.
            # Otherwise, they should form a linear path to a head.
            heads = repo.changelog.heads(repo.changelog.node(rev[-1]))
            if len(heads) > 1:
                raise util.Abort(_('revision %d is the root of more than one '
                                   'branch') % rev[-1])
            if self.applied:
                base = revlog.hex(repo.changelog.node(rev[0]))
                if base in [n.rev for n in self.applied]:
                    raise util.Abort(_('revision %d is already managed')
                                     % rev[0])
                if heads != [revlog.bin(self.applied[-1].rev)]:
                    raise util.Abort(_('revision %d is not the parent of '
                                       'the queue') % rev[0])
                base = repo.changelog.rev(revlog.bin(self.applied[0].rev))
                lastparent = repo.changelog.parentrevs(base)[0]
            else:
                if heads != [repo.changelog.node(rev[0])]:
                    raise util.Abort(_('revision %d has unmanaged children')
                                     % rev[0])
                lastparent = None

            if git:
                self.diffopts().git = True

            for r in rev:
                p1, p2 = repo.changelog.parentrevs(r)
                n = repo.changelog.node(r)
                if p2 != revlog.nullrev:
                    raise util.Abort(_('cannot import merge revision %d') % r)
                if lastparent and lastparent != r:
                    raise util.Abort(_('revision %d is not the parent of %d')
                                     % (r, lastparent))
                lastparent = p1

                if not patchname:
                    patchname = normname('%d.diff' % r)
                checkseries(patchname)
                checkfile(patchname)
                self.full_series.insert(0, patchname)

                patchf = self.opener(patchname, "w")
                patch.export(repo, [n], fp=patchf, opts=self.diffopts())
                patchf.close()

                se = statusentry(revlog.hex(n), patchname)
                self.applied.insert(0, se)

                added.append(patchname)
                patchname = None
            self.parse_series()
            self.applied_dirty = 1

        for filename in files:
            if existing:
                if filename == '-':
                    raise util.Abort(_('-e is incompatible with import from -'))
                if not patchname:
                    patchname = normname(filename)
                if not os.path.isfile(self.join(patchname)):
                    raise util.Abort(_("patch %s does not exist") % patchname)
            else:
                try:
                    if filename == '-':
                        if not patchname:
                            raise util.Abort(_('need --name to import a patch from -'))
                        text = sys.stdin.read()
                    else:
                        text = file(filename).read()
                except IOError:
                    raise util.Abort(_("unable to read %s") % patchname)
                if not patchname:
                    patchname = normname(os.path.basename(filename))
                checkfile(patchname)
                patchf = self.opener(patchname, "w")
                patchf.write(text)
            checkseries(patchname)
            index = self.full_series_end() + i
            self.full_series[index:index] = [patchname]
            self.parse_series()
            self.ui.warn("adding %s to series file\n" % patchname)
            i += 1
            added.append(patchname)
            patchname = None
        self.series_dirty = 1
        qrepo = self.qrepo()
        if qrepo:
            qrepo.add(added)

def delete(ui, repo, *patches, **opts):
    """remove patches from queue

    With --rev, mq will stop managing the named revisions. The
    patches must be applied and at the base of the stack. This option
    is useful when the patches have been applied upstream.

    Otherwise, the patches must not be applied.

    With --keep, the patch files are preserved in the patch directory."""
    q = repo.mq
    q.delete(repo, patches, opts)
    q.save_dirty()
    return 0

def applied(ui, repo, patch=None, **opts):
    """print the patches already applied"""
    q = repo.mq
    if patch:
        if patch not in q.series:
            raise util.Abort(_("patch %s is not in series file") % patch)
        end = q.series.index(patch) + 1
    else:
        end = len(q.applied)
    if not end:
        return

    return q.qseries(repo, length=end, status='A', summary=opts.get('summary'))

def unapplied(ui, repo, patch=None, **opts):
    """print the patches not yet applied"""
    q = repo.mq
    if patch:
        if patch not in q.series:
            raise util.Abort(_("patch %s is not in series file") % patch)
        start = q.series.index(patch) + 1
    else:
        start = q.series_end()
    q.qseries(repo, start=start, summary=opts.get('summary'))

def qimport(ui, repo, *filename, **opts):
    """import a patch

    The patch will have the same name as its source file unless you
    give it a new one with --name.

    You can register an existing patch inside the patch directory
    with the --existing flag.

    With --force, an existing patch of the same name will be overwritten.

    An existing changeset may be placed under mq control with --rev
    (e.g. qimport --rev tip -n patch will place tip under mq control).
    With --git, patches imported with --rev will use the git diff
    format.
    """
    q = repo.mq
    q.qimport(repo, filename, patchname=opts['name'],
              existing=opts['existing'], force=opts['force'], rev=opts['rev'],
              git=opts['git'])
    q.save_dirty()
    return 0

def init(ui, repo, **opts):
    """init a new queue repository

    The queue repository is unversioned by default. If -c is
    specified, qinit will create a separate nested repository
    for patches. Use qcommit to commit changes to this queue
    repository."""
    q = repo.mq
    r = q.init(repo, create=opts['create_repo'])
    q.save_dirty()
    if r:
        if not os.path.exists(r.wjoin('.hgignore')):
            fp = r.wopener('.hgignore', 'w')
            fp.write('syntax: glob\n')
            fp.write('status\n')
            fp.write('guards\n')
            fp.close()
        if not os.path.exists(r.wjoin('series')):
            r.wopener('series', 'w').close()
        r.add(['.hgignore', 'series'])
        commands.add(ui, r)
    return 0

def clone(ui, source, dest=None, **opts):
    '''clone main and patch repository at same time

    If source is local, destination will have no patches applied.  If
    source is remote, this command can not check if patches are
    applied in source, so cannot guarantee that patches are not
    applied in destination.  If you clone remote repository, be sure
    before that it has no patches applied.

    Source patch repository is looked for in <src>/.hg/patches by
    default.  Use -p <url> to change.
    '''
    commands.setremoteconfig(ui, opts)
    if dest is None:
        dest = hg.defaultdest(source)
    sr = hg.repository(ui, ui.expandpath(source))
    qbase, destrev = None, None
    if sr.local():
        if sr.mq.applied:
            qbase = revlog.bin(sr.mq.applied[0].rev)
            if not hg.islocal(dest):
                heads = dict.fromkeys(sr.heads())
                for h in sr.heads(qbase):
                    del heads[h]
                destrev = heads.keys()
                destrev.append(sr.changelog.parents(qbase)[0])
    ui.note(_('cloning main repo\n'))
    sr, dr = hg.clone(ui, sr, dest,
                      pull=opts['pull'],
                      rev=destrev,
                      update=False,
                      stream=opts['uncompressed'])
    ui.note(_('cloning patch repo\n'))
    spr, dpr = hg.clone(ui, opts['patches'] or (sr.url() + '/.hg/patches'),
                        dr.url() + '/.hg/patches',
                        pull=opts['pull'],
                        update=not opts['noupdate'],
                        stream=opts['uncompressed'])
    if dr.local():
        if qbase:
            ui.note(_('stripping applied patches from destination repo\n'))
            dr.mq.strip(dr, qbase, update=False, backup=None)
        if not opts['noupdate']:
            ui.note(_('updating destination repo\n'))
            hg.update(dr, dr.changelog.tip())

def commit(ui, repo, *pats, **opts):
    """commit changes in the queue repository"""
    q = repo.mq
    r = q.qrepo()
    if not r: raise util.Abort('no queue repository')
    commands.commit(r.ui, r, *pats, **opts)

def series(ui, repo, **opts):
    """print the entire series file"""
    repo.mq.qseries(repo, missing=opts['missing'], summary=opts['summary'])
    return 0

def top(ui, repo, **opts):
    """print the name of the current patch"""
    q = repo.mq
    t = len(q.applied)
    if t:
        return q.qseries(repo, start=t-1, length=1, status='A',
                         summary=opts.get('summary'))
    else:
        ui.write("No patches applied\n")
        return 1

def next(ui, repo, **opts):
    """print the name of the next patch"""
    q = repo.mq
    end = q.series_end()
    if end == len(q.series):
        ui.write("All patches applied\n")
        return 1
    return q.qseries(repo, start=end, length=1, summary=opts.get('summary'))

def prev(ui, repo, **opts):
    """print the name of the previous patch"""
    q = repo.mq
    l = len(q.applied)
    if l == 1:
        ui.write("Only one patch applied\n")
        return 1
    if not l:
        ui.write("No patches applied\n")
        return 1
    return q.qseries(repo, start=l-2, length=1, status='A',
                     summary=opts.get('summary'))

def new(ui, repo, patch, **opts):
    """create a new patch

    qnew creates a new patch on top of the currently-applied patch
    (if any). It will refuse to run if there are any outstanding
    changes unless -f is specified, in which case the patch will
    be initialised with them.

    -e, -m or -l set the patch header as well as the commit message.
    If none is specified, the patch header is empty and the
    commit message is 'New patch: PATCH'"""
    q = repo.mq
    message = commands.logmessage(opts)
    if opts['edit']:
        message = ui.edit(message, ui.username())
    q.new(repo, patch, msg=message, force=opts['force'])
    q.save_dirty()
    return 0

def refresh(ui, repo, *pats, **opts):
    """update the current patch

    If any file patterns are provided, the refreshed patch will contain only
    the modifications that match those patterns; the remaining modifications
    will remain in the working directory.

    hg add/remove/copy/rename work as usual, though you might want to use
    git-style patches (--git or [diff] git=1) to track copies and renames.
    """
    q = repo.mq
    message = commands.logmessage(opts)
    if opts['edit']:
        if message:
            raise util.Abort(_('option "-e" incompatible with "-m" or "-l"'))
        patch = q.applied[-1].name
        (message, comment, user, date, hasdiff) = q.readheaders(patch)
        message = ui.edit('\n'.join(message), user or ui.username())
    ret = q.refresh(repo, pats, msg=message, **opts)
    q.save_dirty()
    return ret

def diff(ui, repo, *pats, **opts):
    """diff of the current patch"""
    repo.mq.diff(repo, pats, opts)
    return 0

def fold(ui, repo, *files, **opts):
    """fold the named patches into the current patch

    Patches must not yet be applied. Each patch will be successively
    applied to the current patch in the order given. If all the
    patches apply successfully, the current patch will be refreshed
    with the new cumulative patch, and the folded patches will
    be deleted. With -k/--keep, the folded patch files will not
    be removed afterwards.

    The header for each folded patch will be concatenated with
    the current patch header, separated by a line of '* * *'."""

    q = repo.mq

    if not files:
        raise util.Abort(_('qfold requires at least one patch name'))
    if not q.check_toppatch(repo):
        raise util.Abort(_('No patches applied'))

    message = commands.logmessage(opts)
    if opts['edit']:
        if message:
            raise util.Abort(_('option "-e" incompatible with "-m" or "-l"'))

    parent = q.lookup('qtip')
    patches = []
    messages = []
    for f in files:
        p = q.lookup(f)
        if p in patches or p == parent:
            ui.warn(_('Skipping already folded patch %s') % p)
        if q.isapplied(p):
            raise util.Abort(_('qfold cannot fold already applied patch %s') % p)
        patches.append(p)

    for p in patches:
        if not message:
            messages.append(q.readheaders(p)[0])
        pf = q.join(p)
        (patchsuccess, files, fuzz) = q.patch(repo, pf)
        if not patchsuccess:
            raise util.Abort(_('Error folding patch %s') % p)
        patch.updatedir(ui, repo, files)

    if not message:
        message, comments, user = q.readheaders(parent)[0:3]
        for msg in messages:
            message.append('* * *')
            message.extend(msg)
        message = '\n'.join(message)

    if opts['edit']:
        message = ui.edit(message, user or ui.username())

    q.refresh(repo, msg=message)
    q.delete(repo, patches, opts)
    q.save_dirty()

def guard(ui, repo, *args, **opts):
    '''set or print guards for a patch

    Guards control whether a patch can be pushed. A patch with no
    guards is always pushed. A patch with a positive guard ("+foo") is
    pushed only if the qselect command has activated it. A patch with
    a negative guard ("-foo") is never pushed if the qselect command
    has activated it.

    With no arguments, print the currently active guards.
    With arguments, set guards for the named patch.

    To set a negative guard "-foo" on topmost patch ("--" is needed so
    hg will not interpret "-foo" as an option):
      hg qguard -- -foo

    To set guards on another patch:
      hg qguard other.patch +2.6.17 -stable
    '''
    def status(idx):
        guards = q.series_guards[idx] or ['unguarded']
        ui.write('%s: %s\n' % (q.series[idx], ' '.join(guards)))
    q = repo.mq
    patch = None
    args = list(args)
    if opts['list']:
        if args or opts['none']:
            raise util.Abort(_('cannot mix -l/--list with options or arguments'))
        for i in xrange(len(q.series)):
            status(i)
        return
    if not args or args[0][0:1] in '-+':
        if not q.applied:
            raise util.Abort(_('no patches applied'))
        patch = q.applied[-1].name
    if patch is None and args[0][0:1] not in '-+':
        patch = args.pop(0)
    if patch is None:
        raise util.Abort(_('no patch to work with'))
    if args or opts['none']:
        idx = q.find_series(patch)
        if idx is None:
            raise util.Abort(_('no patch named %s') % patch)
        q.set_guards(idx, args)
        q.save_dirty()
    else:
        status(q.series.index(q.lookup(patch)))

def header(ui, repo, patch=None):
    """Print the header of the topmost or specified patch"""
    q = repo.mq

    if patch:
        patch = q.lookup(patch)
    else:
        if not q.applied:
            ui.write('No patches applied\n')
            return 1
        patch = q.lookup('qtip')
    message = repo.mq.readheaders(patch)[0]

    ui.write('\n'.join(message) + '\n')

def lastsavename(path):
    (directory, base) = os.path.split(path)
    names = os.listdir(directory)
    namere = re.compile("%s.([0-9]+)" % base)
    maxindex = None
    maxname = None
    for f in names:
        m = namere.match(f)
        if m:
            index = int(m.group(1))
            if maxindex == None or index > maxindex:
                maxindex = index
                maxname = f
    if maxname:
        return (os.path.join(directory, maxname), maxindex)
    return (None, None)

def savename(path):
    (last, index) = lastsavename(path)
    if last is None:
        index = 0
    newpath = path + ".%d" % (index + 1)
    return newpath

def push(ui, repo, patch=None, **opts):
    """push the next patch onto the stack"""
    q = repo.mq
    mergeq = None

    if opts['all']:
        if not q.series:
            ui.warn(_('no patches in series\n'))
            return 0
        patch = q.series[-1]
    if opts['merge']:
        if opts['name']:
            newpath = opts['name']
        else:
            newpath, i = lastsavename(q.path)
        if not newpath:
            ui.warn("no saved queues found, please use -n\n")
            return 1
        mergeq = queue(ui, repo.join(""), newpath)
        ui.warn("merging with queue at: %s\n" % mergeq.path)
    ret = q.push(repo, patch, force=opts['force'], list=opts['list'],
                 mergeq=mergeq)
    q.save_dirty()
    return ret

def pop(ui, repo, patch=None, **opts):
    """pop the current patch off the stack"""
    localupdate = True
    if opts['name']:
        q = queue(ui, repo.join(""), repo.join(opts['name']))
        ui.warn('using patch queue: %s\n' % q.path)
        localupdate = False
    else:
        q = repo.mq
    ret = q.pop(repo, patch, force=opts['force'], update=localupdate,
                all=opts['all'])
    q.save_dirty()
    return ret

def rename(ui, repo, patch, name=None, **opts):
    """rename a patch

    With one argument, renames the current patch to PATCH1.
    With two arguments, renames PATCH1 to PATCH2."""

    q = repo.mq

    if not name:
        name = patch
        patch = None

    if patch:
        patch = q.lookup(patch)
    else:
        if not q.applied:
            ui.write(_('No patches applied\n'))
            return
        patch = q.lookup('qtip')
    absdest = q.join(name)
    if os.path.isdir(absdest):
        name = normname(os.path.join(name, os.path.basename(patch)))
        absdest = q.join(name)
    if os.path.exists(absdest):
        raise util.Abort(_('%s already exists') % absdest)

    if name in q.series:
        raise util.Abort(_('A patch named %s already exists in the series file') % name)

    if ui.verbose:
        ui.write('Renaming %s to %s\n' % (patch, name))
    i = q.find_series(patch)
    guards = q.guard_re.findall(q.full_series[i])
    q.full_series[i] = name + ''.join([' #' + g for g in guards])
    q.parse_series()
    q.series_dirty = 1

    info = q.isapplied(patch)
    if info:
        q.applied[info[0]] = statusentry(info[1], name)
    q.applied_dirty = 1

    util.rename(q.join(patch), absdest)
    r = q.qrepo()
    if r:
        wlock = r.wlock()
        if r.dirstate.state(name) == 'r':
            r.undelete([name], wlock)
        r.copy(patch, name, wlock)
        r.remove([patch], False, wlock)

    q.save_dirty()

def restore(ui, repo, rev, **opts):
    """restore the queue state saved by a rev"""
    rev = repo.lookup(rev)
    q = repo.mq
    q.restore(repo, rev, delete=opts['delete'],
              qupdate=opts['update'])
    q.save_dirty()
    return 0

def save(ui, repo, **opts):
    """save current queue state"""
    q = repo.mq
    message = commands.logmessage(opts)
    ret = q.save(repo, msg=message)
    if ret:
        return ret
    q.save_dirty()
    if opts['copy']:
        path = q.path
        if opts['name']:
            newpath = os.path.join(q.basepath, opts['name'])
            if os.path.exists(newpath):
                if not os.path.isdir(newpath):
                    raise util.Abort(_('destination %s exists and is not '
                                       'a directory') % newpath)
                if not opts['force']:
                    raise util.Abort(_('destination %s exists, '
                                       'use -f to force') % newpath)
        else:
            newpath = savename(path)
        ui.warn("copy %s to %s\n" % (path, newpath))
        util.copyfiles(path, newpath)
    if opts['empty']:
        try:
            os.unlink(q.join(q.status_path))
        except:
            pass
    return 0

def strip(ui, repo, rev, **opts):
    """strip a revision and all later revs on the same branch"""
    rev = repo.lookup(rev)
    backup = 'all'
    if opts['backup']:
        backup = 'strip'
    elif opts['nobackup']:
        backup = 'none'
    update = repo.dirstate.parents()[0] != revlog.nullid
    repo.mq.strip(repo, rev, backup=backup, update=update)
    return 0

def select(ui, repo, *args, **opts):
    '''set or print guarded patches to push

    Use the qguard command to set or print guards on patch, then use
    qselect to tell mq which guards to use. A patch will be pushed if it
    has no guards or any positive guards match the currently selected guard,
    but will not be pushed if any negative guards match the current guard.
    For example:

        qguard foo.patch -stable    (negative guard)
        qguard bar.patch +stable    (positive guard)
        qselect stable

    This activates the "stable" guard. mq will skip foo.patch (because
    it has a negative match) but push bar.patch (because it
    has a positive match).

    With no arguments, prints the currently active guards.
    With one argument, sets the active guard.

    Use -n/--none to deactivate guards (no other arguments needed).
    When no guards are active, patches with positive guards are skipped
    and patches with negative guards are pushed.

    qselect can change the guards on applied patches. It does not pop
    guarded patches by default. Use --pop to pop back to the last applied
    patch that is not guarded. Use --reapply (which implies --pop) to push
    back to the current patch afterwards, but skip guarded patches.

    Use -s/--series to print a list of all guards in the series file (no
    other arguments needed). Use -v for more information.'''

    q = repo.mq
    guards = q.active()
    if args or opts['none']:
        old_unapplied = q.unapplied(repo)
        old_guarded = [i for i in xrange(len(q.applied)) if
                       not q.pushable(i)[0]]
        q.set_active(args)
        q.save_dirty()
        if not args:
            ui.status(_('guards deactivated\n'))
        if not opts['pop'] and not opts['reapply']:
            unapplied = q.unapplied(repo)
            guarded = [i for i in xrange(len(q.applied))
                       if not q.pushable(i)[0]]
            if len(unapplied) != len(old_unapplied):
                ui.status(_('number of unguarded, unapplied patches has '
                            'changed from %d to %d\n') %
                          (len(old_unapplied), len(unapplied)))
            if len(guarded) != len(old_guarded):
                ui.status(_('number of guarded, applied patches has changed '
                            'from %d to %d\n') %
                          (len(old_guarded), len(guarded)))
    elif opts['series']:
        guards = {}
        noguards = 0
        for gs in q.series_guards:
            if not gs:
                noguards += 1
            for g in gs:
                guards.setdefault(g, 0)
                guards[g] += 1
        if ui.verbose:
            guards['NONE'] = noguards
        guards = guards.items()
        guards.sort(lambda a, b: cmp(a[0][1:], b[0][1:]))
        if guards:
            ui.note(_('guards in series file:\n'))
            for guard, count in guards:
                ui.note('%2d  ' % count)
                ui.write(guard, '\n')
        else:
            ui.note(_('no guards in series file\n'))
    else:
        if guards:
            ui.note(_('active guards:\n'))
            for g in guards:
                ui.write(g, '\n')
        else:
            ui.write(_('no active guards\n'))
    reapply = opts['reapply'] and q.applied and q.appliedname(-1)
    popped = False
    if opts['pop'] or opts['reapply']:
        for i in xrange(len(q.applied)):
            pushable, reason = q.pushable(i)
            if not pushable:
                ui.status(_('popping guarded patches\n'))
                popped = True
                if i == 0:
                    q.pop(repo, all=True)
                else:
                    q.pop(repo, i-1)
                break
    if popped:
        try:
            if reapply:
                ui.status(_('reapplying unguarded patches\n'))
                q.push(repo, reapply)
        finally:
            q.save_dirty()

def reposetup(ui, repo):
    class mqrepo(repo.__class__):
        def abort_if_wdir_patched(self, errmsg, force=False):
            if self.mq.applied and not force:
                parent = revlog.hex(self.dirstate.parents()[0])
                if parent in [s.rev for s in self.mq.applied]:
                    raise util.Abort(errmsg)

        def commit(self, *args, **opts):
            if len(args) >= 6:
                force = args[5]
            else:
                force = opts.get('force')
            self.abort_if_wdir_patched(
                _('cannot commit over an applied mq patch'),
                force)

            return super(mqrepo, self).commit(*args, **opts)

        def push(self, remote, force=False, revs=None):
            if self.mq.applied and not force and not revs:
                raise util.Abort(_('source has mq patches applied'))
            return super(mqrepo, self).push(remote, force, revs)

        def tags(self):
            if self.tagscache:
                return self.tagscache

            tagscache = super(mqrepo, self).tags()

            q = self.mq
            if not q.applied:
                return tagscache

            mqtags = [(revlog.bin(patch.rev), patch.name) for patch in q.applied]
            mqtags.append((mqtags[-1][0], 'qtip'))
            mqtags.append((mqtags[0][0], 'qbase'))
            mqtags.append((self.changelog.parents(mqtags[0][0])[0], 'qparent'))
            for patch in mqtags:
                if patch[1] in tagscache:
                    self.ui.warn('Tag %s overrides mq patch of the same name\n' % patch[1])
                else:
                    tagscache[patch[1]] = patch[0]

            return tagscache

        def _branchtags(self):
            q = self.mq
            if not q.applied:
                return super(mqrepo, self)._branchtags()

            self.branchcache = {} # avoid recursion in changectx
            cl = self.changelog
            partial, last, lrev = self._readbranchcache()

            qbase = cl.rev(revlog.bin(q.applied[0].rev))
            start = lrev + 1
            if start < qbase:
                # update the cache (excluding the patches) and save it
                self._updatebranchcache(partial, lrev+1, qbase)
                self._writebranchcache(partial, cl.node(qbase-1), qbase-1)
                start = qbase
            # if start = qbase, the cache is as updated as it should be.
            # if start > qbase, the cache includes (part of) the patches.
            # we might as well use it, but we won't save it.

            # update the cache up to the tip
            self._updatebranchcache(partial, start, cl.count())

            return partial

    if repo.local():
        repo.__class__ = mqrepo
        repo.mq = queue(ui, repo.join(""))

seriesopts = [('s', 'summary', None, _('print first line of patch header'))]

cmdtable = {
    "qapplied": (applied, [] + seriesopts, 'hg qapplied [-s] [PATCH]'),
    "qclone": (clone,
               [('', 'pull', None, _('use pull protocol to copy metadata')),
                ('U', 'noupdate', None, _('do not update the new working directories')),
                ('', 'uncompressed', None,
                 _('use uncompressed transfer (fast over LAN)')),
                ('e', 'ssh', '', _('specify ssh command to use')),
                ('p', 'patches', '', _('location of source patch repo')),
                ('', 'remotecmd', '',
                 _('specify hg command to run on the remote side'))],
               'hg qclone [OPTION]... SOURCE [DEST]'),
    "qcommit|qci":
        (commit,
         commands.table["^commit|ci"][1],
         'hg qcommit [OPTION]... [FILE]...'),
    "^qdiff": (diff,
               [('g', 'git', None, _('use git extended diff format')),
                ('I', 'include', [], _('include names matching the given patterns')),
                ('X', 'exclude', [], _('exclude names matching the given patterns'))],
               'hg qdiff [-I] [-X] [FILE]...'),
    "qdelete|qremove|qrm":
        (delete,
         [('k', 'keep', None, _('keep patch file')),
          ('r', 'rev', [], _('stop managing a revision'))],
          'hg qdelete [-k] [-r REV]... PATCH...'),
    'qfold':
        (fold,
         [('e', 'edit', None, _('edit patch header')),
          ('k', 'keep', None, _('keep folded patch files'))
          ] + commands.commitopts,
         'hg qfold [-e] [-m <text>] [-l <file] PATCH...'),
    'qguard': (guard, [('l', 'list', None, _('list all patches and guards')),
                       ('n', 'none', None, _('drop all guards'))],
               'hg qguard [PATCH] [+GUARD...] [-GUARD...]'),
    'qheader': (header, [],
                _('hg qheader [PATCH]')),
    "^qimport":
        (qimport,
         [('e', 'existing', None, 'import file in patch dir'),
          ('n', 'name', '', 'patch file name'),
          ('f', 'force', None, 'overwrite existing files'),
          ('r', 'rev', [], 'place existing revisions under mq control'),
          ('g', 'git', None, _('use git extended diff format'))],
         'hg qimport [-e] [-n NAME] [-f] [-g] [-r REV]... FILE...'),
    "^qinit":
        (init,
         [('c', 'create-repo', None, 'create queue repository')],
         'hg qinit [-c]'),
    "qnew":
        (new,
         [('e', 'edit', None, _('edit commit message')),
          ('f', 'force', None, _('import uncommitted changes into patch'))
          ] + commands.commitopts,
         'hg qnew [-e] [-m TEXT] [-l FILE] [-f] PATCH'),
    "qnext": (next, [] + seriesopts, 'hg qnext [-s]'),
    "qprev": (prev, [] + seriesopts, 'hg qprev [-s]'),
    "^qpop":
        (pop,
         [('a', 'all', None, 'pop all patches'),
          ('n', 'name', '', 'queue name to pop'),
          ('f', 'force', None, 'forget any local changes')],
         'hg qpop [-a] [-n NAME] [-f] [PATCH | INDEX]'),
    "^qpush":
        (push,
         [('f', 'force', None, 'apply if the patch has rejects'),
          ('l', 'list', None, 'list patch name in commit text'),
          ('a', 'all', None, 'apply all patches'),
          ('m', 'merge', None, 'merge from another queue'),
          ('n', 'name', '', 'merge queue name')],
         'hg qpush [-f] [-l] [-a] [-m] [-n NAME] [PATCH | INDEX]'),
    "^qrefresh":
        (refresh,
         [('e', 'edit', None, _('edit commit message')),
          ('g', 'git', None, _('use git extended diff format')),
          ('s', 'short', None, 'refresh only files already in the patch'),
          ('I', 'include', [], _('include names matching the given patterns')),
          ('X', 'exclude', [], _('exclude names matching the given patterns'))
          ] + commands.commitopts,
         'hg qrefresh [-I] [-X] [-e] [-m TEXT] [-l FILE] [-s] FILES...'),
    'qrename|qmv':
        (rename, [], 'hg qrename PATCH1 [PATCH2]'),
    "qrestore":
        (restore,
         [('d', 'delete', None, 'delete save entry'),
          ('u', 'update', None, 'update queue working dir')],
         'hg qrestore [-d] [-u] REV'),
    "qsave":
        (save,
         [('c', 'copy', None, 'copy patch directory'),
          ('n', 'name', '', 'copy directory name'),
          ('e', 'empty', None, 'clear queue status file'),
          ('f', 'force', None, 'force copy')] + commands.commitopts,
         'hg qsave [-m TEXT] [-l FILE] [-c] [-n NAME] [-e] [-f]'),
    "qselect": (select,
                [('n', 'none', None, _('disable all guards')),
                 ('s', 'series', None, _('list all guards in series file')),
                 ('', 'pop', None,
                  _('pop to before first guarded applied patch')),
                 ('', 'reapply', None, _('pop, then reapply patches'))],
                'hg qselect [OPTION...] [GUARD...]'),
    "qseries":
        (series,
         [('m', 'missing', None, 'print patches not in series')] + seriesopts,
         'hg qseries [-ms]'),
    "^strip":
        (strip,
         [('f', 'force', None, 'force multi-head removal'),
          ('b', 'backup', None, 'bundle unrelated changesets'),
          ('n', 'nobackup', None, 'no backups')],
         'hg strip [-f] [-b] [-n] REV'),
    "qtop": (top, [] + seriesopts, 'hg qtop [-s]'),
    "qunapplied": (unapplied, [] + seriesopts, 'hg qunapplied [-s] [PATCH]'),
}
