import cStringIO, email, os, errno, re, posixpath, copy
import tempfile, zlib, shutil
# On python2.4 you have to import these by name or they fail to
# load. This was not a problem on Python 2.7.
import email.Generator
import email.Parser

from i18n import _
from node import hex, short
import cStringIO
import base85, mdiff, scmutil, util, diffhelpers, copies, encoding, error
import pathutil
        return cStringIO.StringIO(''.join(lines))
            fp = cStringIO.StringIO()
    return tuple (filename, message, user, date, branch, node, p1, p2).
    Any item in the returned tuple can be None. If filename is None,
    tmpfp = os.fdopen(fd, 'w')
        subject = msg['Subject']
        user = msg['From']
        if not subject and not user:
        date = None
        nodeid = None
        branch = None
        if user:
            ui.debug('From: %s\n' % user)
                cfp = cStringIO.StringIO()
                            user = line[7:]
                            ui.debug('From: %s\n' % user)
                        elif line.startswith("# Date "):
                            date = line[7:]
                        elif line.startswith("# Branch "):
                            branch = line[9:]
                        elif line.startswith("# Node ID "):
                            nodeid = line[10:]
                        elif not line.startswith("# "):
    if not diffs_seen:
        os.unlink(tmpname)
        return None, message, user, date, branch, None, None, None

        p1 = parents.pop(0)
    else:
        p1 = None
    if parents:
        p2 = parents.pop(0)
        p2 = None

    return tmpname, message, user, date, branch, nodeid, p1, p2
        islink = mode & 020000
        isexec = mode & 0100
        while True:
            l = self.readline()
            if not l:
                break
            yield l
        self.opener = scmutil.opener(basedir)
            isexec = self.opener.lstat(fname).st_mode & 0100 != 0
        except OSError, e:
        except IOError, e:
                self.opener = scmutil.opener(root)
        for fuzzlen in xrange(3):
        return util.any(h.startswith('index ') for h in self.header)
        return util.any(self.allhunks_re.match(h) for h in self.header)
        return util.any(self.newfile_re.match(h) for h in self.header)
                util.any(self.special_re.match(h) for h in self.header)
def filterpatch(ui, headers):
                    ui.write('%s - %s\n' % (c, t.lower()))
                # http://mercurial.selenic.com/wiki/RecordExtension)
                    f = os.fdopen(patchfd, "w")
                    ui.system("%s \"%s\"" % (editor, patchfn),
                              environ={'HGUSER': ui.username()},
                              onerr=util.Abort, errprefix=_("edit failed"))
                    ncpatchfp = cStringIO.StringIO()
                    for line in patchfp:
                raise util.Abort(_('user quit'))
                msg = _("record this change to '%s'?") % chunk.filename()
                msg = _("record change %d/%d to '%s'?") % (idx, total,
                                                           chunk.filename())
    return sum([h for h in applied.itervalues()
               if h[0].special() or len(h) > 1], [])
            except ValueError, e:
                self.proc = ''
    fp = cStringIO.StringIO()
        while True:
            line = lr.readline()
            if not line:
                break
    while True:
        line = lr.readline()
        if not line:
            break
        fp = cStringIO.StringIO(lr.fp.read())
    while True:
        x = lr.readline()
        if not x:
            break
                    # FIXME: failing getfile has never been handled here
                    assert data is not None
            except PatchError, inst:
            raise util.Abort(_('unsupported parser state: %s') % state)
        for line in fp:
        raise util.Abort(_('unsupported line endings type: %s') % eolmode)
    fp = open(patchpath, 'rb')
    try:
                raise util.Abort(_('unsupported parser state: %s') % state)
    finally:
        fp.close()
            if v:
        buildopts['nobinary'] = get('nobinary')
def diff(repo, node1=None, node2=None, match=None, changes=None, opts=None,
         losedatafn=None, prefix='', relroot=''):
    patterns that fall outside it will be ignored.'''
        order = util.deque()
    copy = {}
    if opts.git or opts.upgrade:
        copy = copies.pathcopies(ctx1, ctx2, match=match)
def _filepairs(ctx1, modified, added, removed, copy, opts):
    # Fix up  added, since merged-in additions appear as
    # modifications during merges
    for f in modified:
        if f not in ctx1:
            addedset.add(f)
        s = util.sha1('blob %d\0' % l)
    for f1, f2, copyop in _filepairs(
            ctx1, modified, added, removed, copy, opts):
            text = mdiff.unidiff(content1, date1,
                                 content2, date2,
                                 path1, path2, opts=opts)
        if header and (text or len(header) > 1):
            yield '\n'.join(header) + '\n'
        if text:
            yield text
def diffstat(lines, width=80, git=False):