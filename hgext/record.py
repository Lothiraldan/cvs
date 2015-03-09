# record.py
#
# Copyright 2007 Bryan O'Sullivan <bos@serpentine.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

'''commands to interactively select changes for commit/qrefresh'''

from mercurial.i18n import _
from mercurial import cmdutil, commands, extensions, hg, patch
from mercurial import util
import copy, cStringIO, errno, os, shutil, tempfile

cmdtable = {}
command = cmdutil.command(cmdtable)
testedwith = 'internal'


def parsepatch(fp):
    """patch -> [] of headers -> [] of hunks """
    class parser(object):
        """patch parsing state machine"""
        def __init__(self):
            self.fromline = 0
            self.toline = 0
            self.proc = ''
            self.header = None
            self.context = []
            self.before = []
            self.hunk = []
            self.headers = []

        def addrange(self, limits):
            fromstart, fromend, tostart, toend, proc = limits
            self.fromline = int(fromstart)
            self.toline = int(tostart)
            self.proc = proc

        def addcontext(self, context):
            if self.hunk:
                h = patch.recordhunk(self.header, self.fromline, self.toline,
                         self.proc, self.before, self.hunk, context)
                self.header.hunks.append(h)
                self.fromline += len(self.before) + h.removed
                self.toline += len(self.before) + h.added
                self.before = []
                self.hunk = []
                self.proc = ''
            self.context = context

        def addhunk(self, hunk):
            if self.context:
                self.before = self.context
                self.context = []
            self.hunk = hunk

        def newfile(self, hdr):
            self.addcontext([])
            h = patch.header(hdr)
            self.headers.append(h)
            self.header = h

        def addother(self, line):
            pass # 'other' lines are ignored

        def finished(self):
            self.addcontext([])
            return self.headers

        transitions = {
            'file': {'context': addcontext,
                     'file': newfile,
                     'hunk': addhunk,
                     'range': addrange},
            'context': {'file': newfile,
                        'hunk': addhunk,
                        'range': addrange,
                        'other': addother},
            'hunk': {'context': addcontext,
                     'file': newfile,
                     'range': addrange},
            'range': {'context': addcontext,
                      'hunk': addhunk},
            'other': {'other': addother},
            }

    p = parser()

    state = 'context'
    for newstate, data in patch.scanpatch(fp):
        try:
            p.transitions[state][newstate](p, data)
        except KeyError:
            raise patch.PatchError('unhandled transition: %s -> %s' %
                                   (state, newstate))
        state = newstate
    return p.finished()

def filterpatch(ui, headers):
    """Interactively filter patch chunks into applied-only chunks"""

    def prompt(skipfile, skipall, query, chunk):
        """prompt query, and process base inputs

        - y/n for the rest of file
        - y/n for the rest
        - ? (help)
        - q (quit)

        Return True/False and possibly updated skipfile and skipall.
        """
        newpatches = None
        if skipall is not None:
            return skipall, skipfile, skipall, newpatches
        if skipfile is not None:
            return skipfile, skipfile, skipall, newpatches
        while True:
            resps = _('[Ynesfdaq?]'
                      '$$ &Yes, record this change'
                      '$$ &No, skip this change'
                      '$$ &Edit this change manually'
                      '$$ &Skip remaining changes to this file'
                      '$$ Record remaining changes to this &file'
                      '$$ &Done, skip remaining changes and files'
                      '$$ Record &all changes to all remaining files'
                      '$$ &Quit, recording no changes'
                      '$$ &? (display help)')
            r = ui.promptchoice("%s %s" % (query, resps))
            ui.write("\n")
            if r == 8: # ?
                for c, t in ui.extractchoices(resps)[1]:
                    ui.write('%s - %s\n' % (c, t.lower()))
                continue
            elif r == 0: # yes
                ret = True
            elif r == 1: # no
                ret = False
            elif r == 2: # Edit patch
                if chunk is None:
                    ui.write(_('cannot edit patch for whole file'))
                    ui.write("\n")
                    continue
                if chunk.header.binary():
                    ui.write(_('cannot edit patch for binary file'))
                    ui.write("\n")
                    continue
                # Patch comment based on the Git one (based on comment at end of
                # http://mercurial.selenic.com/wiki/RecordExtension)
                phelp = '---' + _("""
To remove '-' lines, make them ' ' lines (context).
To remove '+' lines, delete them.
Lines starting with # will be removed from the patch.

If the patch applies cleanly, the edited hunk will immediately be
added to the record list. If it does not apply cleanly, a rejects
file will be generated: you can use that when you try again. If
all lines of the hunk are removed, then the edit is aborted and
the hunk is left unchanged.
""")
                (patchfd, patchfn) = tempfile.mkstemp(prefix="hg-editor-",
                        suffix=".diff", text=True)
                ncpatchfp = None
                try:
                    # Write the initial patch
                    f = os.fdopen(patchfd, "w")
                    chunk.header.write(f)
                    chunk.write(f)
                    f.write('\n'.join(['# ' + i for i in phelp.splitlines()]))
                    f.close()
                    # Start the editor and wait for it to complete
                    editor = ui.geteditor()
                    ui.system("%s \"%s\"" % (editor, patchfn),
                              environ={'HGUSER': ui.username()},
                              onerr=util.Abort, errprefix=_("edit failed"))
                    # Remove comment lines
                    patchfp = open(patchfn)
                    ncpatchfp = cStringIO.StringIO()
                    for line in patchfp:
                        if not line.startswith('#'):
                            ncpatchfp.write(line)
                    patchfp.close()
                    ncpatchfp.seek(0)
                    newpatches = parsepatch(ncpatchfp)
                finally:
                    os.unlink(patchfn)
                    del ncpatchfp
                # Signal that the chunk shouldn't be applied as-is, but
                # provide the new patch to be used instead.
                ret = False
            elif r == 3: # Skip
                ret = skipfile = False
            elif r == 4: # file (Record remaining)
                ret = skipfile = True
            elif r == 5: # done, skip remaining
                ret = skipall = False
            elif r == 6: # all
                ret = skipall = True
            elif r == 7: # quit
                raise util.Abort(_('user quit'))
            return ret, skipfile, skipall, newpatches

    seen = set()
    applied = {}        # 'filename' -> [] of chunks
    skipfile, skipall = None, None
    pos, total = 1, sum(len(h.hunks) for h in headers)
    for h in headers:
        pos += len(h.hunks)
        skipfile = None
        fixoffset = 0
        hdr = ''.join(h.header)
        if hdr in seen:
            continue
        seen.add(hdr)
        if skipall is None:
            h.pretty(ui)
        msg = (_('examine changes to %s?') %
               _(' and ').join("'%s'" % f for f in h.files()))
        r, skipfile, skipall, np = prompt(skipfile, skipall, msg, None)
        if not r:
            continue
        applied[h.filename()] = [h]
        if h.allhunks():
            applied[h.filename()] += h.hunks
            continue
        for i, chunk in enumerate(h.hunks):
            if skipfile is None and skipall is None:
                chunk.pretty(ui)
            if total == 1:
                msg = _("record this change to '%s'?") % chunk.filename()
            else:
                idx = pos - len(h.hunks) + i
                msg = _("record change %d/%d to '%s'?") % (idx, total,
                                                           chunk.filename())
            r, skipfile, skipall, newpatches = prompt(skipfile,
                    skipall, msg, chunk)
            if r:
                if fixoffset:
                    chunk = copy.copy(chunk)
                    chunk.toline += fixoffset
                applied[chunk.filename()].append(chunk)
            elif newpatches is not None:
                for newpatch in newpatches:
                    for newhunk in newpatch.hunks:
                        if fixoffset:
                            newhunk.toline += fixoffset
                        applied[newhunk.filename()].append(newhunk)
            else:
                fixoffset += chunk.removed - chunk.added
    return sum([h for h in applied.itervalues()
               if h[0].special() or len(h) > 1], [])

@command("record",
         # same options as commit + white space diff options
         commands.table['^commit|ci'][1][:] + commands.diffwsopts,
          _('hg record [OPTION]... [FILE]...'))
def record(ui, repo, *pats, **opts):
    '''interactively select changes to commit

    If a list of files is omitted, all changes reported by :hg:`status`
    will be candidates for recording.

    See :hg:`help dates` for a list of formats valid for -d/--date.

    You will be prompted for whether to record changes to each
    modified file, and for files with multiple changes, for each
    change to use. For each query, the following responses are
    possible::

      y - record this change
      n - skip this change
      e - edit this change manually

      s - skip remaining changes to this file
      f - record remaining changes to this file

      d - done, skip remaining changes and files
      a - record all changes to all remaining files
      q - quit, recording no changes

      ? - display help

    This command is not available when committing a merge.'''

    dorecord(ui, repo, commands.commit, 'commit', False, *pats, **opts)

def qrefresh(origfn, ui, repo, *pats, **opts):
    if not opts['interactive']:
        return origfn(ui, repo, *pats, **opts)

    mq = extensions.find('mq')

    def committomq(ui, repo, *pats, **opts):
        # At this point the working copy contains only changes that
        # were accepted. All other changes were reverted.
        # We can't pass *pats here since qrefresh will undo all other
        # changed files in the patch that aren't in pats.
        mq.refresh(ui, repo, **opts)

    # backup all changed files
    dorecord(ui, repo, committomq, 'qrefresh', True, *pats, **opts)

# This command registration is replaced during uisetup().
@command('qrecord',
    [],
    _('hg qrecord [OPTION]... PATCH [FILE]...'),
    inferrepo=True)
def qrecord(ui, repo, patch, *pats, **opts):
    '''interactively record a new patch

    See :hg:`help qnew` & :hg:`help record` for more information and
    usage.
    '''

    try:
        mq = extensions.find('mq')
    except KeyError:
        raise util.Abort(_("'mq' extension not loaded"))

    repo.mq.checkpatchname(patch)

    def committomq(ui, repo, *pats, **opts):
        opts['checkname'] = False
        mq.new(ui, repo, patch, *pats, **opts)

    dorecord(ui, repo, committomq, 'qnew', False, *pats, **opts)

def qnew(origfn, ui, repo, patch, *args, **opts):
    if opts['interactive']:
        return qrecord(ui, repo, patch, *args, **opts)
    return origfn(ui, repo, patch, *args, **opts)

def dorecord(ui, repo, commitfunc, cmdsuggest, backupall, *pats, **opts):
    if not ui.interactive():
        raise util.Abort(_('running non-interactively, use %s instead') %
                         cmdsuggest)

    # make sure username is set before going interactive
    if not opts.get('user'):
        ui.username() # raise exception, username not provided

    def recordfunc(ui, repo, message, match, opts):
        """This is generic record driver.

        Its job is to interactively filter local changes, and
        accordingly prepare working directory into a state in which the
        job can be delegated to a non-interactive commit command such as
        'commit' or 'qrefresh'.

        After the actual job is done by non-interactive command, the
        working directory is restored to its original state.

        In the end we'll record interesting changes, and everything else
        will be left in place, so the user can continue working.
        """

        cmdutil.checkunfinished(repo, commit=True)
        merge = len(repo[None].parents()) > 1
        if merge:
            raise util.Abort(_('cannot partially commit a merge '
                               '(use "hg commit" instead)'))

        status = repo.status(match=match)
        diffopts = patch.difffeatureopts(ui, opts=opts, whitespace=True)
        diffopts.nodates = True
        diffopts.git = True
        originalchunks = patch.diff(repo, changes=status, opts=diffopts)
        fp = cStringIO.StringIO()
        fp.write(''.join(originalchunks))
        fp.seek(0)

        # 1. filter patch, so we have intending-to apply subset of it
        try:
            chunks = filterpatch(ui, parsepatch(fp))
        except patch.PatchError, err:
            raise util.Abort(_('error parsing patch: %s') % err)

        del fp

        contenders = set()
        for h in chunks:
            try:
                contenders.update(set(h.files()))
            except AttributeError:
                pass

        changed = status.modified + status.added + status.removed
        newfiles = [f for f in changed if f in contenders]
        if not newfiles:
            ui.status(_('no changes to record\n'))
            return 0

        newandmodifiedfiles = set()
        for h in chunks:
            ishunk = isinstance(h, patch.recordhunk)
            isnew = h.filename() in status.added
            if ishunk and isnew and not h in originalchunks:
                newandmodifiedfiles.add(h.filename())

        modified = set(status.modified)

        # 2. backup changed files, so we can restore them in the end

        if backupall:
            tobackup = changed
        else:
            tobackup = [f for f in newfiles
                        if f in modified or f in newandmodifiedfiles]

        backups = {}
        if tobackup:
            backupdir = repo.join('record-backups')
            try:
                os.mkdir(backupdir)
            except OSError, err:
                if err.errno != errno.EEXIST:
                    raise
        try:
            # backup continues
            for f in tobackup:
                fd, tmpname = tempfile.mkstemp(prefix=f.replace('/', '_')+'.',
                                               dir=backupdir)
                os.close(fd)
                ui.debug('backup %r as %r\n' % (f, tmpname))
                util.copyfile(repo.wjoin(f), tmpname)
                shutil.copystat(repo.wjoin(f), tmpname)
                backups[f] = tmpname

            fp = cStringIO.StringIO()
            for c in chunks:
                fname = c.filename()
                if fname in backups or fname in newandmodifiedfiles:
                    c.write(fp)
            dopatch = fp.tell()
            fp.seek(0)

            [os.unlink(c) for c in newandmodifiedfiles]

            # 3a. apply filtered patch to clean repo  (clean)
            if backups:
                hg.revert(repo, repo.dirstate.p1(),
                          lambda key: key in backups)

            # 3b. (apply)
            if dopatch:
                try:
                    ui.debug('applying patch\n')
                    ui.debug(fp.getvalue())
                    patch.internalpatch(ui, repo, fp, 1, '', eolmode=None)
                except patch.PatchError, err:
                    raise util.Abort(str(err))
            del fp

            # 4. We prepared working directory according to filtered
            #    patch. Now is the time to delegate the job to
            #    commit/qrefresh or the like!

            # Make all of the pathnames absolute.
            newfiles = [repo.wjoin(nf) for nf in newfiles]
            commitfunc(ui, repo, *newfiles, **opts)

            return 0
        finally:
            # 5. finally restore backed-up files
            try:
                for realname, tmpname in backups.iteritems():
                    ui.debug('restoring %r to %r\n' % (tmpname, realname))
                    util.copyfile(tmpname, repo.wjoin(realname))
                    # Our calls to copystat() here and above are a
                    # hack to trick any editors that have f open that
                    # we haven't modified them.
                    #
                    # Also note that this racy as an editor could
                    # notice the file's mtime before we've finished
                    # writing it.
                    shutil.copystat(tmpname, repo.wjoin(realname))
                    os.unlink(tmpname)
                if tobackup:
                    os.rmdir(backupdir)
            except OSError:
                pass

    # wrap ui.write so diff output can be labeled/colorized
    def wrapwrite(orig, *args, **kw):
        label = kw.pop('label', '')
        for chunk, l in patch.difflabel(lambda: args):
            orig(chunk, label=label + l)
    oldwrite = ui.write
    extensions.wrapfunction(ui, 'write', wrapwrite)
    try:
        return cmdutil.commit(ui, repo, recordfunc, pats, opts)
    finally:
        ui.write = oldwrite

def uisetup(ui):
    try:
        mq = extensions.find('mq')
    except KeyError:
        return

    cmdtable["qrecord"] = \
        (qrecord,
         # same options as qnew, but copy them so we don't get
         # -i/--interactive for qrecord and add white space diff options
         mq.cmdtable['^qnew'][1][:] + commands.diffwsopts,
         _('hg qrecord [OPTION]... PATCH [FILE]...'))

    _wrapcmd('qnew', mq.cmdtable, qnew, _("interactively record a new patch"))
    _wrapcmd('qrefresh', mq.cmdtable, qrefresh,
             _("interactively select changes to refresh"))

def _wrapcmd(cmd, table, wrapfn, msg):
    entry = extensions.wrapcommand(table, cmd, wrapfn)
    entry[1].append(('i', 'interactive', None, msg))
