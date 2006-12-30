# localrepo.py - read/write repository class for mercurial
#
# Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from node import *
from i18n import _
import repo, appendfile, changegroup
import changelog, dirstate, filelog, manifest, context
import re, lock, transaction, tempfile, stat, mdiff, errno, ui
import os, revlog, time, util

class localrepository(repo.repository):
    capabilities = ('lookup', 'changegroupsubset')
    supported = ('revlogv1', 'store')

    def __del__(self):
        self.transhandle = None
    def __init__(self, parentui, path=None, create=0):
        repo.repository.__init__(self)
        if not path:
            p = os.getcwd()
            while not os.path.isdir(os.path.join(p, ".hg")):
                oldp = p
                p = os.path.dirname(p)
                if p == oldp:
                    raise repo.RepoError(_("There is no Mercurial repository"
                                           " here (.hg not found)"))
            path = p

        self.path = os.path.join(path, ".hg")
        self.root = os.path.realpath(path)
        self.origroot = path
        self.opener = util.opener(self.path)
        self.wopener = util.opener(self.root)

        if not os.path.isdir(self.path):
            if create:
                if not os.path.exists(path):
                    os.mkdir(path)
                os.mkdir(self.path)
                os.mkdir(os.path.join(self.path, "store"))
                requirements = ("revlogv1", "store")
                reqfile = self.opener("requires", "w")
                for r in requirements:
                    reqfile.write("%s\n" % r)
                reqfile.close()
                # create an invalid changelog
                self.opener("00changelog.i", "a").write(
                    '\0\0\0\2' # represents revlogv2
                    ' dummy changelog to prevent using the old repo layout'
                )
            else:
                raise repo.RepoError(_("repository %s not found") % path)
        elif create:
            raise repo.RepoError(_("repository %s already exists") % path)
        else:
            # find requirements
            try:
                requirements = self.opener("requires").read().splitlines()
            except IOError, inst:
                if inst.errno != errno.ENOENT:
                    raise
                requirements = []
        # check them
        for r in requirements:
            if r not in self.supported:
                raise repo.RepoError(_("requirement '%s' not supported") % r)

        # setup store
        if "store" in requirements:
            self.encodefn = util.encodefilename
            self.decodefn = util.decodefilename
            self.spath = os.path.join(self.path, "store")
        else:
            self.encodefn = lambda x: x
            self.decodefn = lambda x: x
            self.spath = self.path
        self.sopener = util.encodedopener(util.opener(self.spath), self.encodefn)

        self.ui = ui.ui(parentui=parentui)
        try:
            self.ui.readconfig(self.join("hgrc"), self.root)
        except IOError:
            pass

        v = self.ui.configrevlog()
        self.revlogversion = int(v.get('format', revlog.REVLOG_DEFAULT_FORMAT))
        self.revlogv1 = self.revlogversion != revlog.REVLOGV0
        fl = v.get('flags', None)
        flags = 0
        if fl != None:
            for x in fl.split():
                flags |= revlog.flagstr(x)
        elif self.revlogv1:
            flags = revlog.REVLOG_DEFAULT_FLAGS

        v = self.revlogversion | flags
        self.manifest = manifest.manifest(self.sopener, v)
        self.changelog = changelog.changelog(self.sopener, v)

        fallback = self.ui.config('ui', 'fallbackencoding')
        if fallback:
            util._fallbackencoding = fallback

        # the changelog might not have the inline index flag
        # on.  If the format of the changelog is the same as found in
        # .hgrc, apply any flags found in the .hgrc as well.
        # Otherwise, just version from the changelog
        v = self.changelog.version
        if v == self.revlogversion:
            v |= flags
        self.revlogversion = v

        self.tagscache = None
        self.branchcache = None
        self.nodetagscache = None
        self.filterpats = {}
        self.transhandle = None

        self._link = lambda x: False
        if util.checklink(self.root):
            r = self.root # avoid circular reference in lambda
            self._link = lambda x: util.is_link(os.path.join(r, x))

        self.dirstate = dirstate.dirstate(self.opener, self.ui, self.root)

    def url(self):
        return 'file:' + self.root

    def hook(self, name, throw=False, **args):
        def callhook(hname, funcname):
            '''call python hook. hook is callable object, looked up as
            name in python module. if callable returns "true", hook
            fails, else passes. if hook raises exception, treated as
            hook failure. exception propagates if throw is "true".

            reason for "true" meaning "hook failed" is so that
            unmodified commands (e.g. mercurial.commands.update) can
            be run as hooks without wrappers to convert return values.'''

            self.ui.note(_("calling hook %s: %s\n") % (hname, funcname))
            d = funcname.rfind('.')
            if d == -1:
                raise util.Abort(_('%s hook is invalid ("%s" not in a module)')
                                 % (hname, funcname))
            modname = funcname[:d]
            try:
                obj = __import__(modname)
            except ImportError:
                try:
                    # extensions are loaded with hgext_ prefix
                    obj = __import__("hgext_%s" % modname)
                except ImportError:
                    raise util.Abort(_('%s hook is invalid '
                                       '(import of "%s" failed)') %
                                     (hname, modname))
            try:
                for p in funcname.split('.')[1:]:
                    obj = getattr(obj, p)
            except AttributeError, err:
                raise util.Abort(_('%s hook is invalid '
                                   '("%s" is not defined)') %
                                 (hname, funcname))
            if not callable(obj):
                raise util.Abort(_('%s hook is invalid '
                                   '("%s" is not callable)') %
                                 (hname, funcname))
            try:
                r = obj(ui=self.ui, repo=self, hooktype=name, **args)
            except (KeyboardInterrupt, util.SignalInterrupt):
                raise
            except Exception, exc:
                if isinstance(exc, util.Abort):
                    self.ui.warn(_('error: %s hook failed: %s\n') %
                                 (hname, exc.args[0]))
                else:
                    self.ui.warn(_('error: %s hook raised an exception: '
                                   '%s\n') % (hname, exc))
                if throw:
                    raise
                self.ui.print_exc()
                return True
            if r:
                if throw:
                    raise util.Abort(_('%s hook failed') % hname)
                self.ui.warn(_('warning: %s hook failed\n') % hname)
            return r

        def runhook(name, cmd):
            self.ui.note(_("running hook %s: %s\n") % (name, cmd))
            env = dict([('HG_' + k.upper(), v) for k, v in args.iteritems()])
            r = util.system(cmd, environ=env, cwd=self.root)
            if r:
                desc, r = util.explain_exit(r)
                if throw:
                    raise util.Abort(_('%s hook %s') % (name, desc))
                self.ui.warn(_('warning: %s hook %s\n') % (name, desc))
            return r

        r = False
        hooks = [(hname, cmd) for hname, cmd in self.ui.configitems("hooks")
                 if hname.split(".", 1)[0] == name and cmd]
        hooks.sort()
        for hname, cmd in hooks:
            if cmd.startswith('python:'):
                r = callhook(hname, cmd[7:].strip()) or r
            else:
                r = runhook(hname, cmd) or r
        return r

    tag_disallowed = ':\r\n'

    def tag(self, name, node, message, local, user, date):
        '''tag a revision with a symbolic name.

        if local is True, the tag is stored in a per-repository file.
        otherwise, it is stored in the .hgtags file, and a new
        changeset is committed with the change.

        keyword arguments:

        local: whether to store tag in non-version-controlled file
        (default False)

        message: commit message to use if committing

        user: name of user to use if committing

        date: date tuple to use if committing'''

        for c in self.tag_disallowed:
            if c in name:
                raise util.Abort(_('%r cannot be used in a tag name') % c)

        self.hook('pretag', throw=True, node=hex(node), tag=name, local=local)

        if local:
            # local tags are stored in the current charset
            self.opener('localtags', 'a').write('%s %s\n' % (hex(node), name))
            self.hook('tag', node=hex(node), tag=name, local=local)
            return

        for x in self.status()[:5]:
            if '.hgtags' in x:
                raise util.Abort(_('working copy of .hgtags is changed '
                                   '(please commit .hgtags manually)'))

        # committed tags are stored in UTF-8
        line = '%s %s\n' % (hex(node), util.fromlocal(name))
        self.wfile('.hgtags', 'ab').write(line)
        if self.dirstate.state('.hgtags') == '?':
            self.add(['.hgtags'])

        self.commit(['.hgtags'], message, user, date)
        self.hook('tag', node=hex(node), tag=name, local=local)

    def tags(self):
        '''return a mapping of tag to node'''
        if not self.tagscache:
            self.tagscache = {}

            def parsetag(line, context):
                if not line:
                    return
                s = l.split(" ", 1)
                if len(s) != 2:
                    self.ui.warn(_("%s: cannot parse entry\n") % context)
                    return
                node, key = s
                key = util.tolocal(key.strip()) # stored in UTF-8
                try:
                    bin_n = bin(node)
                except TypeError:
                    self.ui.warn(_("%s: node '%s' is not well formed\n") %
                                 (context, node))
                    return
                if bin_n not in self.changelog.nodemap:
                    self.ui.warn(_("%s: tag '%s' refers to unknown node\n") %
                                 (context, key))
                    return
                self.tagscache[key] = bin_n

            # read the tags file from each head, ending with the tip,
            # and add each tag found to the map, with "newer" ones
            # taking precedence
            f = None
            for rev, node, fnode in self._hgtagsnodes():
                f = (f and f.filectx(fnode) or
                     self.filectx('.hgtags', fileid=fnode))
                count = 0
                for l in f.data().splitlines():
                    count += 1
                    parsetag(l, _("%s, line %d") % (str(f), count))

            try:
                f = self.opener("localtags")
                count = 0
                for l in f:
                    # localtags are stored in the local character set
                    # while the internal tag table is stored in UTF-8
                    l = util.fromlocal(l)
                    count += 1
                    parsetag(l, _("localtags, line %d") % count)
            except IOError:
                pass

            self.tagscache['tip'] = self.changelog.tip()

        return self.tagscache

    def _hgtagsnodes(self):
        heads = self.heads()
        heads.reverse()
        last = {}
        ret = []
        for node in heads:
            c = self.changectx(node)
            rev = c.rev()
            try:
                fnode = c.filenode('.hgtags')
            except revlog.LookupError:
                continue
            ret.append((rev, node, fnode))
            if fnode in last:
                ret[last[fnode]] = None
            last[fnode] = len(ret) - 1
        return [item for item in ret if item]

    def tagslist(self):
        '''return a list of tags ordered by revision'''
        l = []
        for t, n in self.tags().items():
            try:
                r = self.changelog.rev(n)
            except:
                r = -2 # sort to the beginning of the list if unknown
            l.append((r, t, n))
        l.sort()
        return [(t, n) for r, t, n in l]

    def nodetags(self, node):
        '''return the tags associated with a node'''
        if not self.nodetagscache:
            self.nodetagscache = {}
            for t, n in self.tags().items():
                self.nodetagscache.setdefault(n, []).append(t)
        return self.nodetagscache.get(node, [])

    def _branchtags(self):
        partial, last, lrev = self._readbranchcache()

        tiprev = self.changelog.count() - 1
        if lrev != tiprev:
            self._updatebranchcache(partial, lrev+1, tiprev+1)
            self._writebranchcache(partial, self.changelog.tip(), tiprev)

        return partial

    def branchtags(self):
        if self.branchcache is not None:
            return self.branchcache

        self.branchcache = {} # avoid recursion in changectx
        partial = self._branchtags()

        # the branch cache is stored on disk as UTF-8, but in the local
        # charset internally
        for k, v in partial.items():
            self.branchcache[util.tolocal(k)] = v
        return self.branchcache

    def _readbranchcache(self):
        partial = {}
        try:
            f = self.opener("branches.cache")
            lines = f.read().split('\n')
            f.close()
            last, lrev = lines.pop(0).rstrip().split(" ", 1)
            last, lrev = bin(last), int(lrev)
            if not (lrev < self.changelog.count() and
                    self.changelog.node(lrev) == last): # sanity check
                # invalidate the cache
                raise ValueError('Invalid branch cache: unknown tip')
            for l in lines:
                if not l: continue
                node, label = l.rstrip().split(" ", 1)
                partial[label] = bin(node)
        except (KeyboardInterrupt, util.SignalInterrupt):
            raise
        except Exception, inst:
            if self.ui.debugflag:
                self.ui.warn(str(inst), '\n')
            partial, last, lrev = {}, nullid, nullrev
        return partial, last, lrev

    def _writebranchcache(self, branches, tip, tiprev):
        try:
            f = self.opener("branches.cache", "w")
            f.write("%s %s\n" % (hex(tip), tiprev))
            for label, node in branches.iteritems():
                f.write("%s %s\n" % (hex(node), label))
        except IOError:
            pass

    def _updatebranchcache(self, partial, start, end):
        for r in xrange(start, end):
            c = self.changectx(r)
            b = c.branch()
            if b:
                partial[b] = c.node()

    def lookup(self, key):
        if key == '.':
            key = self.dirstate.parents()[0]
            if key == nullid:
                raise repo.RepoError(_("no revision checked out"))
        elif key == 'null':
            return nullid
        n = self.changelog._match(key)
        if n:
            return n
        if key in self.tags():
            return self.tags()[key]
        if key in self.branchtags():
            return self.branchtags()[key]
        n = self.changelog._partialmatch(key)
        if n:
            return n
        raise repo.RepoError(_("unknown revision '%s'") % key)

    def dev(self):
        return os.lstat(self.path).st_dev

    def local(self):
        return True

    def join(self, f):
        return os.path.join(self.path, f)

    def sjoin(self, f):
        f = self.encodefn(f)
        return os.path.join(self.spath, f)

    def wjoin(self, f):
        return os.path.join(self.root, f)

    def file(self, f):
        if f[0] == '/':
            f = f[1:]
        return filelog.filelog(self.sopener, f, self.revlogversion)

    def changectx(self, changeid=None):
        return context.changectx(self, changeid)

    def workingctx(self):
        return context.workingctx(self)

    def parents(self, changeid=None):
        '''
        get list of changectxs for parents of changeid or working directory
        '''
        if changeid is None:
            pl = self.dirstate.parents()
        else:
            n = self.changelog.lookup(changeid)
            pl = self.changelog.parents(n)
        if pl[1] == nullid:
            return [self.changectx(pl[0])]
        return [self.changectx(pl[0]), self.changectx(pl[1])]

    def filectx(self, path, changeid=None, fileid=None):
        """changeid can be a changeset revision, node, or tag.
           fileid can be a file revision or node."""
        return context.filectx(self, path, changeid, fileid)

    def getcwd(self):
        return self.dirstate.getcwd()

    def wfile(self, f, mode='r'):
        return self.wopener(f, mode)

    def _filter(self, filter, filename, data):
        if filter not in self.filterpats:
            l = []
            for pat, cmd in self.ui.configitems(filter):
                mf = util.matcher(self.root, "", [pat], [], [])[1]
                l.append((mf, cmd))
            self.filterpats[filter] = l

        for mf, cmd in self.filterpats[filter]:
            if mf(filename):
                self.ui.debug(_("filtering %s through %s\n") % (filename, cmd))
                data = util.filter(data, cmd)
                break

        return data

    def wread(self, filename):
        if self._link(filename):
            data = os.readlink(self.wjoin(filename))
        else:
            data = self.wopener(filename, 'r').read()
        return self._filter("encode", filename, data)

    def wwrite(self, filename, data, fd=None):
        data = self._filter("decode", filename, data)
        if fd:
            return fd.write(data)
        return self.wopener(filename, 'w').write(data)

    def transaction(self):
        tr = self.transhandle
        if tr != None and tr.running():
            return tr.nest()

        # save dirstate for rollback
        try:
            ds = self.opener("dirstate").read()
        except IOError:
            ds = ""
        self.opener("journal.dirstate", "w").write(ds)

        renames = [(self.sjoin("journal"), self.sjoin("undo")),
                   (self.join("journal.dirstate"), self.join("undo.dirstate"))]
        tr = transaction.transaction(self.ui.warn, self.sopener,
                                       self.sjoin("journal"),
                                       aftertrans(renames))
        self.transhandle = tr
        return tr

    def recover(self):
        l = self.lock()
        if os.path.exists(self.sjoin("journal")):
            self.ui.status(_("rolling back interrupted transaction\n"))
            transaction.rollback(self.sopener, self.sjoin("journal"))
            self.reload()
            return True
        else:
            self.ui.warn(_("no interrupted transaction available\n"))
            return False

    def rollback(self, wlock=None):
        if not wlock:
            wlock = self.wlock()
        l = self.lock()
        if os.path.exists(self.sjoin("undo")):
            self.ui.status(_("rolling back last transaction\n"))
            transaction.rollback(self.sopener, self.sjoin("undo"))
            util.rename(self.join("undo.dirstate"), self.join("dirstate"))
            self.reload()
            self.wreload()
        else:
            self.ui.warn(_("no rollback information available\n"))

    def wreload(self):
        self.dirstate.read()

    def reload(self):
        self.changelog.load()
        self.manifest.load()
        self.tagscache = None
        self.nodetagscache = None

    def do_lock(self, lockname, wait, releasefn=None, acquirefn=None,
                desc=None):
        try:
            l = lock.lock(lockname, 0, releasefn, desc=desc)
        except lock.LockHeld, inst:
            if not wait:
                raise
            self.ui.warn(_("waiting for lock on %s held by %r\n") %
                         (desc, inst.locker))
            # default to 600 seconds timeout
            l = lock.lock(lockname, int(self.ui.config("ui", "timeout", "600")),
                          releasefn, desc=desc)
        if acquirefn:
            acquirefn()
        return l

    def lock(self, wait=1):
        return self.do_lock(self.sjoin("lock"), wait, acquirefn=self.reload,
                            desc=_('repository %s') % self.origroot)

    def wlock(self, wait=1):
        return self.do_lock(self.join("wlock"), wait, self.dirstate.write,
                            self.wreload,
                            desc=_('working directory of %s') % self.origroot)

    def filecommit(self, fn, manifest1, manifest2, linkrev, transaction, changelist):
        """
        commit an individual file as part of a larger transaction
        """

        t = self.wread(fn)
        fl = self.file(fn)
        fp1 = manifest1.get(fn, nullid)
        fp2 = manifest2.get(fn, nullid)

        meta = {}
        cp = self.dirstate.copied(fn)
        if cp:
            meta["copy"] = cp
            if not manifest2: # not a branch merge
                meta["copyrev"] = hex(manifest1.get(cp, nullid))
                fp2 = nullid
            elif fp2 != nullid: # copied on remote side
                meta["copyrev"] = hex(manifest1.get(cp, nullid))
            elif fp1 != nullid: # copied on local side, reversed
                meta["copyrev"] = hex(manifest2.get(cp))
                fp2 = nullid
            else: # directory rename
                meta["copyrev"] = hex(manifest1.get(cp, nullid))
            self.ui.debug(_(" %s: copy %s:%s\n") %
                          (fn, cp, meta["copyrev"]))
            fp1 = nullid
        elif fp2 != nullid:
            # is one parent an ancestor of the other?
            fpa = fl.ancestor(fp1, fp2)
            if fpa == fp1:
                fp1, fp2 = fp2, nullid
            elif fpa == fp2:
                fp2 = nullid

            # is the file unmodified from the parent? report existing entry
            if fp2 == nullid and not fl.cmp(fp1, t):
                return fp1

        changelist.append(fn)
        return fl.add(t, meta, transaction, linkrev, fp1, fp2)

    def rawcommit(self, files, text, user, date, p1=None, p2=None, wlock=None, extra={}):
        if p1 is None:
            p1, p2 = self.dirstate.parents()
        return self.commit(files=files, text=text, user=user, date=date,
                           p1=p1, p2=p2, wlock=wlock, extra=extra)

    def commit(self, files=None, text="", user=None, date=None,
               match=util.always, force=False, lock=None, wlock=None,
               force_editor=False, p1=None, p2=None, extra={}):

        commit = []
        remove = []
        changed = []
        use_dirstate = (p1 is None) # not rawcommit
        extra = extra.copy()

        if use_dirstate:
            if files:
                for f in files:
                    s = self.dirstate.state(f)
                    if s in 'nmai':
                        commit.append(f)
                    elif s == 'r':
                        remove.append(f)
                    else:
                        self.ui.warn(_("%s not tracked!\n") % f)
            else:
                changes = self.status(match=match)[:5]
                modified, added, removed, deleted, unknown = changes
                commit = modified + added
                remove = removed
        else:
            commit = files

        if use_dirstate:
            p1, p2 = self.dirstate.parents()
            update_dirstate = True
        else:
            p1, p2 = p1, p2 or nullid
            update_dirstate = (self.dirstate.parents()[0] == p1)

        c1 = self.changelog.read(p1)
        c2 = self.changelog.read(p2)
        m1 = self.manifest.read(c1[0]).copy()
        m2 = self.manifest.read(c2[0])

        if use_dirstate:
            branchname = self.workingctx().branch()
            try:
                branchname = branchname.decode('UTF-8').encode('UTF-8')
            except UnicodeDecodeError:
                raise util.Abort(_('branch name not in UTF-8!'))
        else:
            branchname = ""

        if use_dirstate:
            oldname = c1[5].get("branch", "") # stored in UTF-8
            if not commit and not remove and not force and p2 == nullid and \
                   branchname == oldname:
                self.ui.status(_("nothing changed\n"))
                return None

        xp1 = hex(p1)
        if p2 == nullid: xp2 = ''
        else: xp2 = hex(p2)

        self.hook("precommit", throw=True, parent1=xp1, parent2=xp2)

        if not wlock:
            wlock = self.wlock()
        if not lock:
            lock = self.lock()
        tr = self.transaction()

        # check in files
        new = {}
        linkrev = self.changelog.count()
        commit.sort()
        is_exec = util.execfunc(self.root, m1.execf)
        is_link = util.linkfunc(self.root, m1.linkf)
        for f in commit:
            self.ui.note(f + "\n")
            try:
                new[f] = self.filecommit(f, m1, m2, linkrev, tr, changed)
                m1.set(f, is_exec(f), is_link(f))
            except OSError:
                if use_dirstate:
                    self.ui.warn(_("trouble committing %s!\n") % f)
                    raise
                else:
                    remove.append(f)

        # update manifest
        m1.update(new)
        remove.sort()
        removed = []

        for f in remove:
            if f in m1:
                del m1[f]
                removed.append(f)
        mn = self.manifest.add(m1, tr, linkrev, c1[0], c2[0], (new, removed))

        # add changeset
        new = new.keys()
        new.sort()

        user = user or self.ui.username()
        if not text or force_editor:
            edittext = []
            if text:
                edittext.append(text)
            edittext.append("")
            edittext.append("HG: user: %s" % user)
            if p2 != nullid:
                edittext.append("HG: branch merge")
            edittext.extend(["HG: changed %s" % f for f in changed])
            edittext.extend(["HG: removed %s" % f for f in removed])
            if not changed and not remove:
                edittext.append("HG: no files changed")
            edittext.append("")
            # run editor in the repository root
            olddir = os.getcwd()
            os.chdir(self.root)
            text = self.ui.edit("\n".join(edittext), user)
            os.chdir(olddir)

        lines = [line.rstrip() for line in text.rstrip().splitlines()]
        while lines and not lines[0]:
            del lines[0]
        if not lines:
            return None
        text = '\n'.join(lines)
        if branchname:
            extra["branch"] = branchname
        n = self.changelog.add(mn, changed + removed, text, tr, p1, p2,
                               user, date, extra)
        self.hook('pretxncommit', throw=True, node=hex(n), parent1=xp1,
                  parent2=xp2)
        tr.close()

        if use_dirstate or update_dirstate:
            self.dirstate.setparents(n)
            if use_dirstate:
                self.dirstate.update(new, "n")
                self.dirstate.forget(removed)

        self.hook("commit", node=hex(n), parent1=xp1, parent2=xp2)
        return n

    def walk(self, node=None, files=[], match=util.always, badmatch=None):
        '''
        walk recursively through the directory tree or a given
        changeset, finding all files matched by the match
        function

        results are yielded in a tuple (src, filename), where src
        is one of:
        'f' the file was found in the directory tree
        'm' the file was only in the dirstate and not in the tree
        'b' file was not found and matched badmatch
        '''

        if node:
            fdict = dict.fromkeys(files)
            for fn in self.manifest.read(self.changelog.read(node)[0]):
                for ffn in fdict:
                    # match if the file is the exact name or a directory
                    if ffn == fn or fn.startswith("%s/" % ffn):
                        del fdict[ffn]
                        break
                if match(fn):
                    yield 'm', fn
            for fn in fdict:
                if badmatch and badmatch(fn):
                    if match(fn):
                        yield 'b', fn
                else:
                    self.ui.warn(_('%s: No such file in rev %s\n') % (
                        util.pathto(self.getcwd(), fn), short(node)))
        else:
            for src, fn in self.dirstate.walk(files, match, badmatch=badmatch):
                yield src, fn

    def status(self, node1=None, node2=None, files=[], match=util.always,
                wlock=None, list_ignored=False, list_clean=False):
        """return status of files between two nodes or node and working directory

        If node1 is None, use the first dirstate parent instead.
        If node2 is None, compare node1 with working directory.
        """

        def fcmp(fn, mf):
            t1 = self.wread(fn)
            return self.file(fn).cmp(mf.get(fn, nullid), t1)

        def mfmatches(node):
            change = self.changelog.read(node)
            mf = self.manifest.read(change[0]).copy()
            for fn in mf.keys():
                if not match(fn):
                    del mf[fn]
            return mf

        modified, added, removed, deleted, unknown = [], [], [], [], []
        ignored, clean = [], []

        compareworking = False
        if not node1 or (not node2 and node1 == self.dirstate.parents()[0]):
            compareworking = True

        if not compareworking:
            # read the manifest from node1 before the manifest from node2,
            # so that we'll hit the manifest cache if we're going through
            # all the revisions in parent->child order.
            mf1 = mfmatches(node1)

        # are we comparing the working directory?
        if not node2:
            if not wlock:
                try:
                    wlock = self.wlock(wait=0)
                except lock.LockException:
                    wlock = None
            (lookup, modified, added, removed, deleted, unknown,
             ignored, clean) = self.dirstate.status(files, match,
                                                    list_ignored, list_clean)

            # are we comparing working dir against its parent?
            if compareworking:
                if lookup:
                    # do a full compare of any files that might have changed
                    mf2 = mfmatches(self.dirstate.parents()[0])
                    for f in lookup:
                        if fcmp(f, mf2):
                            modified.append(f)
                        else:
                            clean.append(f)
                            if wlock is not None:
                                self.dirstate.update([f], "n")
            else:
                # we are comparing working dir against non-parent
                # generate a pseudo-manifest for the working dir
                # XXX: create it in dirstate.py ?
                mf2 = mfmatches(self.dirstate.parents()[0])
                is_exec = util.execfunc(self.root, mf2.execf)
                is_link = util.linkfunc(self.root, mf2.linkf)
                for f in lookup + modified + added:
                    mf2[f] = ""
                    mf2.set(f, is_exec(f), is_link(f))
                for f in removed:
                    if f in mf2:
                        del mf2[f]
        else:
            # we are comparing two revisions
            mf2 = mfmatches(node2)

        if not compareworking:
            # flush lists from dirstate before comparing manifests
            modified, added, clean = [], [], []

            # make sure to sort the files so we talk to the disk in a
            # reasonable order
            mf2keys = mf2.keys()
            mf2keys.sort()
            for fn in mf2keys:
                if mf1.has_key(fn):
                    if mf1.flags(fn) != mf2.flags(fn) or \
                       (mf1[fn] != mf2[fn] and (mf2[fn] != "" or fcmp(fn, mf1))):
                        modified.append(fn)
                    elif list_clean:
                        clean.append(fn)
                    del mf1[fn]
                else:
                    added.append(fn)

            removed = mf1.keys()

        # sort and return results:
        for l in modified, added, removed, deleted, unknown, ignored, clean:
            l.sort()
        return (modified, added, removed, deleted, unknown, ignored, clean)

    def add(self, list, wlock=None):
        if not wlock:
            wlock = self.wlock()
        for f in list:
            p = self.wjoin(f)
            if not os.path.exists(p):
                self.ui.warn(_("%s does not exist!\n") % f)
            elif not os.path.isfile(p):
                self.ui.warn(_("%s not added: only files supported currently\n")
                             % f)
            elif self.dirstate.state(f) in 'an':
                self.ui.warn(_("%s already tracked!\n") % f)
            else:
                self.dirstate.update([f], "a")

    def forget(self, list, wlock=None):
        if not wlock:
            wlock = self.wlock()
        for f in list:
            if self.dirstate.state(f) not in 'ai':
                self.ui.warn(_("%s not added!\n") % f)
            else:
                self.dirstate.forget([f])

    def remove(self, list, unlink=False, wlock=None):
        if unlink:
            for f in list:
                try:
                    util.unlink(self.wjoin(f))
                except OSError, inst:
                    if inst.errno != errno.ENOENT:
                        raise
        if not wlock:
            wlock = self.wlock()
        for f in list:
            p = self.wjoin(f)
            if os.path.exists(p):
                self.ui.warn(_("%s still exists!\n") % f)
            elif self.dirstate.state(f) == 'a':
                self.dirstate.forget([f])
            elif f not in self.dirstate:
                self.ui.warn(_("%s not tracked!\n") % f)
            else:
                self.dirstate.update([f], "r")

    def undelete(self, list, wlock=None):
        p = self.dirstate.parents()[0]
        mn = self.changelog.read(p)[0]
        m = self.manifest.read(mn)
        if not wlock:
            wlock = self.wlock()
        for f in list:
            if self.dirstate.state(f) not in  "r":
                self.ui.warn("%s not removed!\n" % f)
            else:
                t = self.file(f).read(m[f])
                self.wwrite(f, t)
                util.set_exec(self.wjoin(f), m.execf(f))
                self.dirstate.update([f], "n")

    def copy(self, source, dest, wlock=None):
        p = self.wjoin(dest)
        if not os.path.exists(p):
            self.ui.warn(_("%s does not exist!\n") % dest)
        elif not os.path.isfile(p):
            self.ui.warn(_("copy failed: %s is not a file\n") % dest)
        else:
            if not wlock:
                wlock = self.wlock()
            if self.dirstate.state(dest) == '?':
                self.dirstate.update([dest], "a")
            self.dirstate.copy(source, dest)

    def heads(self, start=None):
        heads = self.changelog.heads(start)
        # sort the output in rev descending order
        heads = [(-self.changelog.rev(h), h) for h in heads]
        heads.sort()
        return [n for (r, n) in heads]

    def branches(self, nodes):
        if not nodes:
            nodes = [self.changelog.tip()]
        b = []
        for n in nodes:
            t = n
            while 1:
                p = self.changelog.parents(n)
                if p[1] != nullid or p[0] == nullid:
                    b.append((t, n, p[0], p[1]))
                    break
                n = p[0]
        return b

    def between(self, pairs):
        r = []

        for top, bottom in pairs:
            n, l, i = top, [], 0
            f = 1

            while n != bottom:
                p = self.changelog.parents(n)[0]
                if i == f:
                    l.append(n)
                    f = f * 2
                n = p
                i += 1

            r.append(l)

        return r

    def findincoming(self, remote, base=None, heads=None, force=False):
        """Return list of roots of the subsets of missing nodes from remote

        If base dict is specified, assume that these nodes and their parents
        exist on the remote side and that no child of a node of base exists
        in both remote and self.
        Furthermore base will be updated to include the nodes that exists
        in self and remote but no children exists in self and remote.
        If a list of heads is specified, return only nodes which are heads
        or ancestors of these heads.

        All the ancestors of base are in self and in remote.
        All the descendants of the list returned are missing in self.
        (and so we know that the rest of the nodes are missing in remote, see
        outgoing)
        """
        m = self.changelog.nodemap
        search = []
        fetch = {}
        seen = {}
        seenbranch = {}
        if base == None:
            base = {}

        if not heads:
            heads = remote.heads()

        if self.changelog.tip() == nullid:
            base[nullid] = 1
            if heads != [nullid]:
                return [nullid]
            return []

        # assume we're closer to the tip than the root
        # and start by examining the heads
        self.ui.status(_("searching for changes\n"))

        unknown = []
        for h in heads:
            if h not in m:
                unknown.append(h)
            else:
                base[h] = 1

        if not unknown:
            return []

        req = dict.fromkeys(unknown)
        reqcnt = 0

        # search through remote branches
        # a 'branch' here is a linear segment of history, with four parts:
        # head, root, first parent, second parent
        # (a branch always has two parents (or none) by definition)
        unknown = remote.branches(unknown)
        while unknown:
            r = []
            while unknown:
                n = unknown.pop(0)
                if n[0] in seen:
                    continue

                self.ui.debug(_("examining %s:%s\n")
                              % (short(n[0]), short(n[1])))
                if n[0] == nullid: # found the end of the branch
                    pass
                elif n in seenbranch:
                    self.ui.debug(_("branch already found\n"))
                    continue
                elif n[1] and n[1] in m: # do we know the base?
                    self.ui.debug(_("found incomplete branch %s:%s\n")
                                  % (short(n[0]), short(n[1])))
                    search.append(n) # schedule branch range for scanning
                    seenbranch[n] = 1
                else:
                    if n[1] not in seen and n[1] not in fetch:
                        if n[2] in m and n[3] in m:
                            self.ui.debug(_("found new changeset %s\n") %
                                          short(n[1]))
                            fetch[n[1]] = 1 # earliest unknown
                        for p in n[2:4]:
                            if p in m:
                                base[p] = 1 # latest known

                    for p in n[2:4]:
                        if p not in req and p not in m:
                            r.append(p)
                            req[p] = 1
                seen[n[0]] = 1

            if r:
                reqcnt += 1
                self.ui.debug(_("request %d: %s\n") %
                            (reqcnt, " ".join(map(short, r))))
                for p in xrange(0, len(r), 10):
                    for b in remote.branches(r[p:p+10]):
                        self.ui.debug(_("received %s:%s\n") %
                                      (short(b[0]), short(b[1])))
                        unknown.append(b)

        # do binary search on the branches we found
        while search:
            n = search.pop(0)
            reqcnt += 1
            l = remote.between([(n[0], n[1])])[0]
            l.append(n[1])
            p = n[0]
            f = 1
            for i in l:
                self.ui.debug(_("narrowing %d:%d %s\n") % (f, len(l), short(i)))
                if i in m:
                    if f <= 2:
                        self.ui.debug(_("found new branch changeset %s\n") %
                                          short(p))
                        fetch[p] = 1
                        base[i] = 1
                    else:
                        self.ui.debug(_("narrowed branch search to %s:%s\n")
                                      % (short(p), short(i)))
                        search.append((p, i))
                    break
                p, f = i, f * 2

        # sanity check our fetch list
        for f in fetch.keys():
            if f in m:
                raise repo.RepoError(_("already have changeset ") + short(f[:4]))

        if base.keys() == [nullid]:
            if force:
                self.ui.warn(_("warning: repository is unrelated\n"))
            else:
                raise util.Abort(_("repository is unrelated"))

        self.ui.debug(_("found new changesets starting at ") +
                     " ".join([short(f) for f in fetch]) + "\n")

        self.ui.debug(_("%d total queries\n") % reqcnt)

        return fetch.keys()

    def findoutgoing(self, remote, base=None, heads=None, force=False):
        """Return list of nodes that are roots of subsets not in remote

        If base dict is specified, assume that these nodes and their parents
        exist on the remote side.
        If a list of heads is specified, return only nodes which are heads
        or ancestors of these heads, and return a second element which
        contains all remote heads which get new children.
        """
        if base == None:
            base = {}
            self.findincoming(remote, base, heads, force=force)

        self.ui.debug(_("common changesets up to ")
                      + " ".join(map(short, base.keys())) + "\n")

        remain = dict.fromkeys(self.changelog.nodemap)

        # prune everything remote has from the tree
        del remain[nullid]
        remove = base.keys()
        while remove:
            n = remove.pop(0)
            if n in remain:
                del remain[n]
                for p in self.changelog.parents(n):
                    remove.append(p)

        # find every node whose parents have been pruned
        subset = []
        # find every remote head that will get new children
        updated_heads = {}
        for n in remain:
            p1, p2 = self.changelog.parents(n)
            if p1 not in remain and p2 not in remain:
                subset.append(n)
            if heads:
                if p1 in heads:
                    updated_heads[p1] = True
                if p2 in heads:
                    updated_heads[p2] = True

        # this is the set of all roots we have to push
        if heads:
            return subset, updated_heads.keys()
        else:
            return subset

    def pull(self, remote, heads=None, force=False, lock=None):
        mylock = False
        if not lock:
            lock = self.lock()
            mylock = True

        try:
            fetch = self.findincoming(remote, force=force)
            if fetch == [nullid]:
                self.ui.status(_("requesting all changes\n"))

            if not fetch:
                self.ui.status(_("no changes found\n"))
                return 0

            if heads is None:
                cg = remote.changegroup(fetch, 'pull')
            else:
                if 'changegroupsubset' not in remote.capabilities:
                    raise util.Abort(_("Partial pull cannot be done because other repository doesn't support changegroupsubset."))
                cg = remote.changegroupsubset(fetch, heads, 'pull')
            return self.addchangegroup(cg, 'pull', remote.url())
        finally:
            if mylock:
                lock.release()

    def push(self, remote, force=False, revs=None):
        # there are two ways to push to remote repo:
        #
        # addchangegroup assumes local user can lock remote
        # repo (local filesystem, old ssh servers).
        #
        # unbundle assumes local user cannot lock remote repo (new ssh
        # servers, http servers).

        if remote.capable('unbundle'):
            return self.push_unbundle(remote, force, revs)
        return self.push_addchangegroup(remote, force, revs)

    def prepush(self, remote, force, revs):
        base = {}
        remote_heads = remote.heads()
        inc = self.findincoming(remote, base, remote_heads, force=force)

        update, updated_heads = self.findoutgoing(remote, base, remote_heads)
        if revs is not None:
            msng_cl, bases, heads = self.changelog.nodesbetween(update, revs)
        else:
            bases, heads = update, self.changelog.heads()

        if not bases:
            self.ui.status(_("no changes found\n"))
            return None, 1
        elif not force:
            # check if we're creating new remote heads
            # to be a remote head after push, node must be either
            # - unknown locally
            # - a local outgoing head descended from update
            # - a remote head that's known locally and not
            #   ancestral to an outgoing head

            warn = 0

            if remote_heads == [nullid]:
                warn = 0
            elif not revs and len(heads) > len(remote_heads):
                warn = 1
            else:
                newheads = list(heads)
                for r in remote_heads:
                    if r in self.changelog.nodemap:
                        desc = self.changelog.heads(r, heads)
                        l = [h for h in heads if h in desc]
                        if not l:
                            newheads.append(r)
                    else:
                        newheads.append(r)
                if len(newheads) > len(remote_heads):
                    warn = 1

            if warn:
                self.ui.warn(_("abort: push creates new remote branches!\n"))
                self.ui.status(_("(did you forget to merge?"
                                 " use push -f to force)\n"))
                return None, 1
            elif inc:
                self.ui.warn(_("note: unsynced remote changes!\n"))


        if revs is None:
            cg = self.changegroup(update, 'push')
        else:
            cg = self.changegroupsubset(update, revs, 'push')
        return cg, remote_heads

    def push_addchangegroup(self, remote, force, revs):
        lock = remote.lock()

        ret = self.prepush(remote, force, revs)
        if ret[0] is not None:
            cg, remote_heads = ret
            return remote.addchangegroup(cg, 'push', self.url())
        return ret[1]

    def push_unbundle(self, remote, force, revs):
        # local repo finds heads on server, finds out what revs it
        # must push.  once revs transferred, if server finds it has
        # different heads (someone else won commit/push race), server
        # aborts.

        ret = self.prepush(remote, force, revs)
        if ret[0] is not None:
            cg, remote_heads = ret
            if force: remote_heads = ['force']
            return remote.unbundle(cg, remote_heads, 'push')
        return ret[1]

    def changegroupinfo(self, nodes):
        self.ui.note(_("%d changesets found\n") % len(nodes))
        if self.ui.debugflag:
            self.ui.debug(_("List of changesets:\n"))
            for node in nodes:
                self.ui.debug("%s\n" % hex(node))

    def changegroupsubset(self, bases, heads, source):
        """This function generates a changegroup consisting of all the nodes
        that are descendents of any of the bases, and ancestors of any of
        the heads.

        It is fairly complex as determining which filenodes and which
        manifest nodes need to be included for the changeset to be complete
        is non-trivial.

        Another wrinkle is doing the reverse, figuring out which changeset in
        the changegroup a particular filenode or manifestnode belongs to."""

        self.hook('preoutgoing', throw=True, source=source)

        # Set up some initial variables
        # Make it easy to refer to self.changelog
        cl = self.changelog
        # msng is short for missing - compute the list of changesets in this
        # changegroup.
        msng_cl_lst, bases, heads = cl.nodesbetween(bases, heads)
        self.changegroupinfo(msng_cl_lst)
        # Some bases may turn out to be superfluous, and some heads may be
        # too.  nodesbetween will return the minimal set of bases and heads
        # necessary to re-create the changegroup.

        # Known heads are the list of heads that it is assumed the recipient
        # of this changegroup will know about.
        knownheads = {}
        # We assume that all parents of bases are known heads.
        for n in bases:
            for p in cl.parents(n):
                if p != nullid:
                    knownheads[p] = 1
        knownheads = knownheads.keys()
        if knownheads:
            # Now that we know what heads are known, we can compute which
            # changesets are known.  The recipient must know about all
            # changesets required to reach the known heads from the null
            # changeset.
            has_cl_set, junk, junk = cl.nodesbetween(None, knownheads)
            junk = None
            # Transform the list into an ersatz set.
            has_cl_set = dict.fromkeys(has_cl_set)
        else:
            # If there were no known heads, the recipient cannot be assumed to
            # know about any changesets.
            has_cl_set = {}

        # Make it easy to refer to self.manifest
        mnfst = self.manifest
        # We don't know which manifests are missing yet
        msng_mnfst_set = {}
        # Nor do we know which filenodes are missing.
        msng_filenode_set = {}

        junk = mnfst.index[mnfst.count() - 1] # Get around a bug in lazyindex
        junk = None

        # A changeset always belongs to itself, so the changenode lookup
        # function for a changenode is identity.
        def identity(x):
            return x

        # A function generating function.  Sets up an environment for the
        # inner function.
        def cmp_by_rev_func(revlog):
            # Compare two nodes by their revision number in the environment's
            # revision history.  Since the revision number both represents the
            # most efficient order to read the nodes in, and represents a
            # topological sorting of the nodes, this function is often useful.
            def cmp_by_rev(a, b):
                return cmp(revlog.rev(a), revlog.rev(b))
            return cmp_by_rev

        # If we determine that a particular file or manifest node must be a
        # node that the recipient of the changegroup will already have, we can
        # also assume the recipient will have all the parents.  This function
        # prunes them from the set of missing nodes.
        def prune_parents(revlog, hasset, msngset):
            haslst = hasset.keys()
            haslst.sort(cmp_by_rev_func(revlog))
            for node in haslst:
                parentlst = [p for p in revlog.parents(node) if p != nullid]
                while parentlst:
                    n = parentlst.pop()
                    if n not in hasset:
                        hasset[n] = 1
                        p = [p for p in revlog.parents(n) if p != nullid]
                        parentlst.extend(p)
            for n in hasset:
                msngset.pop(n, None)

        # This is a function generating function used to set up an environment
        # for the inner function to execute in.
        def manifest_and_file_collector(changedfileset):
            # This is an information gathering function that gathers
            # information from each changeset node that goes out as part of
            # the changegroup.  The information gathered is a list of which
            # manifest nodes are potentially required (the recipient may
            # already have them) and total list of all files which were
            # changed in any changeset in the changegroup.
            #
            # We also remember the first changenode we saw any manifest
            # referenced by so we can later determine which changenode 'owns'
            # the manifest.
            def collect_manifests_and_files(clnode):
                c = cl.read(clnode)
                for f in c[3]:
                    # This is to make sure we only have one instance of each
                    # filename string for each filename.
                    changedfileset.setdefault(f, f)
                msng_mnfst_set.setdefault(c[0], clnode)
            return collect_manifests_and_files

        # Figure out which manifest nodes (of the ones we think might be part
        # of the changegroup) the recipient must know about and remove them
        # from the changegroup.
        def prune_manifests():
            has_mnfst_set = {}
            for n in msng_mnfst_set:
                # If a 'missing' manifest thinks it belongs to a changenode
                # the recipient is assumed to have, obviously the recipient
                # must have that manifest.
                linknode = cl.node(mnfst.linkrev(n))
                if linknode in has_cl_set:
                    has_mnfst_set[n] = 1
            prune_parents(mnfst, has_mnfst_set, msng_mnfst_set)

        # Use the information collected in collect_manifests_and_files to say
        # which changenode any manifestnode belongs to.
        def lookup_manifest_link(mnfstnode):
            return msng_mnfst_set[mnfstnode]

        # A function generating function that sets up the initial environment
        # the inner function.
        def filenode_collector(changedfiles):
            next_rev = [0]
            # This gathers information from each manifestnode included in the
            # changegroup about which filenodes the manifest node references
            # so we can include those in the changegroup too.
            #
            # It also remembers which changenode each filenode belongs to.  It
            # does this by assuming the a filenode belongs to the changenode
            # the first manifest that references it belongs to.
            def collect_msng_filenodes(mnfstnode):
                r = mnfst.rev(mnfstnode)
                if r == next_rev[0]:
                    # If the last rev we looked at was the one just previous,
                    # we only need to see a diff.
                    delta = mdiff.patchtext(mnfst.delta(mnfstnode))
                    # For each line in the delta
                    for dline in delta.splitlines():
                        # get the filename and filenode for that line
                        f, fnode = dline.split('\0')
                        fnode = bin(fnode[:40])
                        f = changedfiles.get(f, None)
                        # And if the file is in the list of files we care
                        # about.
                        if f is not None:
                            # Get the changenode this manifest belongs to
                            clnode = msng_mnfst_set[mnfstnode]
                            # Create the set of filenodes for the file if
                            # there isn't one already.
                            ndset = msng_filenode_set.setdefault(f, {})
                            # And set the filenode's changelog node to the
                            # manifest's if it hasn't been set already.
                            ndset.setdefault(fnode, clnode)
                else:
                    # Otherwise we need a full manifest.
                    m = mnfst.read(mnfstnode)
                    # For every file in we care about.
                    for f in changedfiles:
                        fnode = m.get(f, None)
                        # If it's in the manifest
                        if fnode is not None:
                            # See comments above.
                            clnode = msng_mnfst_set[mnfstnode]
                            ndset = msng_filenode_set.setdefault(f, {})
                            ndset.setdefault(fnode, clnode)
                # Remember the revision we hope to see next.
                next_rev[0] = r + 1
            return collect_msng_filenodes

        # We have a list of filenodes we think we need for a file, lets remove
        # all those we now the recipient must have.
        def prune_filenodes(f, filerevlog):
            msngset = msng_filenode_set[f]
            hasset = {}
            # If a 'missing' filenode thinks it belongs to a changenode we
            # assume the recipient must have, then the recipient must have
            # that filenode.
            for n in msngset:
                clnode = cl.node(filerevlog.linkrev(n))
                if clnode in has_cl_set:
                    hasset[n] = 1
            prune_parents(filerevlog, hasset, msngset)

        # A function generator function that sets up the a context for the
        # inner function.
        def lookup_filenode_link_func(fname):
            msngset = msng_filenode_set[fname]
            # Lookup the changenode the filenode belongs to.
            def lookup_filenode_link(fnode):
                return msngset[fnode]
            return lookup_filenode_link

        # Now that we have all theses utility functions to help out and
        # logically divide up the task, generate the group.
        def gengroup():
            # The set of changed files starts empty.
            changedfiles = {}
            # Create a changenode group generator that will call our functions
            # back to lookup the owning changenode and collect information.
            group = cl.group(msng_cl_lst, identity,
                             manifest_and_file_collector(changedfiles))
            for chnk in group:
                yield chnk

            # The list of manifests has been collected by the generator
            # calling our functions back.
            prune_manifests()
            msng_mnfst_lst = msng_mnfst_set.keys()
            # Sort the manifestnodes by revision number.
            msng_mnfst_lst.sort(cmp_by_rev_func(mnfst))
            # Create a generator for the manifestnodes that calls our lookup
            # and data collection functions back.
            group = mnfst.group(msng_mnfst_lst, lookup_manifest_link,
                                filenode_collector(changedfiles))
            for chnk in group:
                yield chnk

            # These are no longer needed, dereference and toss the memory for
            # them.
            msng_mnfst_lst = None
            msng_mnfst_set.clear()

            changedfiles = changedfiles.keys()
            changedfiles.sort()
            # Go through all our files in order sorted by name.
            for fname in changedfiles:
                filerevlog = self.file(fname)
                # Toss out the filenodes that the recipient isn't really
                # missing.
                if msng_filenode_set.has_key(fname):
                    prune_filenodes(fname, filerevlog)
                    msng_filenode_lst = msng_filenode_set[fname].keys()
                else:
                    msng_filenode_lst = []
                # If any filenodes are left, generate the group for them,
                # otherwise don't bother.
                if len(msng_filenode_lst) > 0:
                    yield changegroup.genchunk(fname)
                    # Sort the filenodes by their revision #
                    msng_filenode_lst.sort(cmp_by_rev_func(filerevlog))
                    # Create a group generator and only pass in a changenode
                    # lookup function as we need to collect no information
                    # from filenodes.
                    group = filerevlog.group(msng_filenode_lst,
                                             lookup_filenode_link_func(fname))
                    for chnk in group:
                        yield chnk
                if msng_filenode_set.has_key(fname):
                    # Don't need this anymore, toss it to free memory.
                    del msng_filenode_set[fname]
            # Signal that no more groups are left.
            yield changegroup.closechunk()

            if msng_cl_lst:
                self.hook('outgoing', node=hex(msng_cl_lst[0]), source=source)

        return util.chunkbuffer(gengroup())

    def changegroup(self, basenodes, source):
        """Generate a changegroup of all nodes that we have that a recipient
        doesn't.

        This is much easier than the previous function as we can assume that
        the recipient has any changenode we aren't sending them."""

        self.hook('preoutgoing', throw=True, source=source)

        cl = self.changelog
        nodes = cl.nodesbetween(basenodes, None)[0]
        revset = dict.fromkeys([cl.rev(n) for n in nodes])
        self.changegroupinfo(nodes)

        def identity(x):
            return x

        def gennodelst(revlog):
            for r in xrange(0, revlog.count()):
                n = revlog.node(r)
                if revlog.linkrev(n) in revset:
                    yield n

        def changed_file_collector(changedfileset):
            def collect_changed_files(clnode):
                c = cl.read(clnode)
                for fname in c[3]:
                    changedfileset[fname] = 1
            return collect_changed_files

        def lookuprevlink_func(revlog):
            def lookuprevlink(n):
                return cl.node(revlog.linkrev(n))
            return lookuprevlink

        def gengroup():
            # construct a list of all changed files
            changedfiles = {}

            for chnk in cl.group(nodes, identity,
                                 changed_file_collector(changedfiles)):
                yield chnk
            changedfiles = changedfiles.keys()
            changedfiles.sort()

            mnfst = self.manifest
            nodeiter = gennodelst(mnfst)
            for chnk in mnfst.group(nodeiter, lookuprevlink_func(mnfst)):
                yield chnk

            for fname in changedfiles:
                filerevlog = self.file(fname)
                nodeiter = gennodelst(filerevlog)
                nodeiter = list(nodeiter)
                if nodeiter:
                    yield changegroup.genchunk(fname)
                    lookup = lookuprevlink_func(filerevlog)
                    for chnk in filerevlog.group(nodeiter, lookup):
                        yield chnk

            yield changegroup.closechunk()

            if nodes:
                self.hook('outgoing', node=hex(nodes[0]), source=source)

        return util.chunkbuffer(gengroup())

    def addchangegroup(self, source, srctype, url):
        """add changegroup to repo.

        return values:
        - nothing changed or no source: 0
        - more heads than before: 1+added heads (2..n)
        - less heads than before: -1-removed heads (-2..-n)
        - number of heads stays the same: 1
        """
        def csmap(x):
            self.ui.debug(_("add changeset %s\n") % short(x))
            return cl.count()

        def revmap(x):
            return cl.rev(x)

        if not source:
            return 0

        self.hook('prechangegroup', throw=True, source=srctype, url=url)

        changesets = files = revisions = 0

        tr = self.transaction()

        # write changelog data to temp files so concurrent readers will not see
        # inconsistent view
        cl = None
        try:
            cl = appendfile.appendchangelog(self.sopener,
                                            self.changelog.version)

            oldheads = len(cl.heads())

            # pull off the changeset group
            self.ui.status(_("adding changesets\n"))
            cor = cl.count() - 1
            chunkiter = changegroup.chunkiter(source)
            if cl.addgroup(chunkiter, csmap, tr, 1) is None:
                raise util.Abort(_("received changelog group is empty"))
            cnr = cl.count() - 1
            changesets = cnr - cor

            # pull off the manifest group
            self.ui.status(_("adding manifests\n"))
            chunkiter = changegroup.chunkiter(source)
            # no need to check for empty manifest group here:
            # if the result of the merge of 1 and 2 is the same in 3 and 4,
            # no new manifest will be created and the manifest group will
            # be empty during the pull
            self.manifest.addgroup(chunkiter, revmap, tr)

            # process the files
            self.ui.status(_("adding file changes\n"))
            while 1:
                f = changegroup.getchunk(source)
                if not f:
                    break
                self.ui.debug(_("adding %s revisions\n") % f)
                fl = self.file(f)
                o = fl.count()
                chunkiter = changegroup.chunkiter(source)
                if fl.addgroup(chunkiter, revmap, tr) is None:
                    raise util.Abort(_("received file revlog group is empty"))
                revisions += fl.count() - o
                files += 1

            cl.writedata()
        finally:
            if cl:
                cl.cleanup()

        # make changelog see real files again
        self.changelog = changelog.changelog(self.sopener,
                                             self.changelog.version)
        self.changelog.checkinlinesize(tr)

        newheads = len(self.changelog.heads())
        heads = ""
        if oldheads and newheads != oldheads:
            heads = _(" (%+d heads)") % (newheads - oldheads)

        self.ui.status(_("added %d changesets"
                         " with %d changes to %d files%s\n")
                         % (changesets, revisions, files, heads))

        if changesets > 0:
            self.hook('pretxnchangegroup', throw=True,
                      node=hex(self.changelog.node(cor+1)), source=srctype,
                      url=url)

        tr.close()

        if changesets > 0:
            self.hook("changegroup", node=hex(self.changelog.node(cor+1)),
                      source=srctype, url=url)

            for i in xrange(cor + 1, cnr + 1):
                self.hook("incoming", node=hex(self.changelog.node(i)),
                          source=srctype, url=url)

        # never return 0 here:
        if newheads < oldheads:
            return newheads - oldheads - 1
        else:
            return newheads - oldheads + 1


    def stream_in(self, remote):
        fp = remote.stream_out()
        l = fp.readline()
        try:
            resp = int(l)
        except ValueError:
            raise util.UnexpectedOutput(
                _('Unexpected response from remote server:'), l)
        if resp == 1:
            raise util.Abort(_('operation forbidden by server'))
        elif resp == 2:
            raise util.Abort(_('locking the remote repository failed'))
        elif resp != 0:
            raise util.Abort(_('the server sent an unknown error code'))
        self.ui.status(_('streaming all changes\n'))
        l = fp.readline()
        try:
            total_files, total_bytes = map(int, l.split(' ', 1))
        except ValueError, TypeError:
            raise util.UnexpectedOutput(
                _('Unexpected response from remote server:'), l)
        self.ui.status(_('%d files to transfer, %s of data\n') %
                       (total_files, util.bytecount(total_bytes)))
        start = time.time()
        for i in xrange(total_files):
            # XXX doesn't support '\n' or '\r' in filenames
            l = fp.readline()
            try:
                name, size = l.split('\0', 1)
                size = int(size)
            except ValueError, TypeError:
                raise util.UnexpectedOutput(
                    _('Unexpected response from remote server:'), l)
            self.ui.debug('adding %s (%s)\n' % (name, util.bytecount(size)))
            ofp = self.sopener(name, 'w')
            for chunk in util.filechunkiter(fp, limit=size):
                ofp.write(chunk)
            ofp.close()
        elapsed = time.time() - start
        self.ui.status(_('transferred %s in %.1f seconds (%s/sec)\n') %
                       (util.bytecount(total_bytes), elapsed,
                        util.bytecount(total_bytes / elapsed)))
        self.reload()
        return len(self.heads()) + 1

    def clone(self, remote, heads=[], stream=False):
        '''clone remote repository.

        keyword arguments:
        heads: list of revs to clone (forces use of pull)
        stream: use streaming clone if possible'''

        # now, all clients that can request uncompressed clones can
        # read repo formats supported by all servers that can serve
        # them.

        # if revlog format changes, client will have to check version
        # and format flags on "stream" capability, and use
        # uncompressed only if compatible.

        if stream and not heads and remote.capable('stream'):
            return self.stream_in(remote)
        return self.pull(remote, heads)

# used to avoid circular references so destructors work
def aftertrans(files):
    renamefiles = [tuple(t) for t in files]
    def a():
        for src, dest in renamefiles:
            util.rename(src, dest)
    return a

def instance(ui, path, create):
    return localrepository(ui, util.drop_scheme('file', path), create)

def islocal(path):
    return True
