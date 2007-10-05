# Subversion 1.4/1.5 Python API backend
#
# Copyright(C) 2007 Daniel Holth et al
#
# Configuration options:
#
# convert.svn.trunk
#   Relative path to the trunk (default: "trunk")
# convert.svn.branches
#   Relative path to tree of branches (default: "branches")
#
# Set these in a hgrc, or on the command line as follows:
#
#   hg convert --config convert.svn.trunk=wackoname [...]

import locale
import os
import sys
import cPickle as pickle
from mercurial import util

# Subversion stuff. Works best with very recent Python SVN bindings
# e.g. SVN 1.5 or backports. Thanks to the bzr folks for enhancing
# these bindings.

from cStringIO import StringIO

from common import NoRepo, commit, converter_source, encodeargs, decodeargs

try:
    from svn.core import SubversionException, Pool
    import svn
    import svn.client
    import svn.core
    import svn.ra
    import svn.delta
    import transport
except ImportError:
    pass

def geturl(path):
    try:
        return svn.client.url_from_path(svn.core.svn_path_canonicalize(path))
    except SubversionException:
        pass
    if os.path.isdir(path):
        return 'file://%s' % os.path.normpath(os.path.abspath(path))
    return path

def optrev(number):
    optrev = svn.core.svn_opt_revision_t()
    optrev.kind = svn.core.svn_opt_revision_number
    optrev.value.number = number
    return optrev

class changedpath(object):
    def __init__(self, p):
        self.copyfrom_path = p.copyfrom_path
        self.copyfrom_rev = p.copyfrom_rev
        self.action = p.action

def get_log_child(fp, url, paths, start, end, limit=0, discover_changed_paths=True,
                    strict_node_history=False):
    protocol = -1
    def receiver(orig_paths, revnum, author, date, message, pool):
        if orig_paths is not None:
            for k, v in orig_paths.iteritems():
                orig_paths[k] = changedpath(v)
        pickle.dump((orig_paths, revnum, author, date, message),
                    fp, protocol)

    try:
        # Use an ra of our own so that our parent can consume
        # our results without confusing the server.
        t = transport.SvnRaTransport(url=url)
        svn.ra.get_log(t.ra, paths, start, end, limit,
                       discover_changed_paths,
                       strict_node_history,
                       receiver)
    except SubversionException, (inst, num):
        pickle.dump(num, fp, protocol)
    else:
        pickle.dump(None, fp, protocol)
    fp.close()

def debugsvnlog(ui, **opts):
    """Fetch SVN log in a subprocess and channel them back to parent to
    avoid memory collection issues.
    """
    util.set_binary(sys.stdin)
    util.set_binary(sys.stdout)
    args = decodeargs(sys.stdin.read())
    get_log_child(sys.stdout, *args)

# SVN conversion code stolen from bzr-svn and tailor
class convert_svn(converter_source):
    def __init__(self, ui, url, rev=None):
        super(convert_svn, self).__init__(ui, url, rev=rev)

        try:
            SubversionException
        except NameError:
            msg = 'subversion python bindings could not be loaded\n'
            ui.warn(msg)
            raise NoRepo(msg)

        self.encoding = locale.getpreferredencoding()
        self.lastrevs = {}

        latest = None
        try:
            # Support file://path@rev syntax. Useful e.g. to convert
            # deleted branches.
            at = url.rfind('@')
            if at >= 0:
                latest = int(url[at+1:])
                url = url[:at]
        except ValueError, e:
            pass
        self.url = geturl(url)
        self.encoding = 'UTF-8' # Subversion is always nominal UTF-8
        try:
            self.transport = transport.SvnRaTransport(url=self.url)
            self.ra = self.transport.ra
            self.ctx = self.transport.client
            self.base = svn.ra.get_repos_root(self.ra)
            self.module = self.url[len(self.base):]
            self.modulemap = {} # revision, module
            self.commits = {}
            self.paths = {}
            self.uuid = svn.ra.get_uuid(self.ra).decode(self.encoding)
        except SubversionException, e:
            raise NoRepo("couldn't open SVN repo %s" % self.url)

        if rev:
            try:
                latest = int(rev)
            except ValueError:
                raise util.Abort('svn: revision %s is not an integer' % rev)

        try:
            self.get_blacklist()
        except IOError, e:
            pass

        self.last_changed = self.latest(self.module, latest)

        self.head = self.revid(self.last_changed)
        self._changescache = None

    def setrevmap(self, revmap, order):
        lastrevs = {}
        for revid in revmap.keys():
            uuid, module, revnum = self.revsplit(revid)
            lastrevnum = lastrevs.setdefault(module, revnum)
            if revnum > lastrevnum:
                lastrevs[module] = revnum
        self.lastrevs = lastrevs

    def exists(self, path, optrev):
        try:
            return svn.client.ls(self.url.rstrip('/') + '/' + path,
                                 optrev, False, self.ctx)
        except SubversionException, err:
            return []

    def getheads(self):
        # detect standard /branches, /tags, /trunk layout
        rev = optrev(self.last_changed)
        rpath = self.url.strip('/')
        cfgtrunk = self.ui.config('convert', 'svn.trunk')
        cfgbranches = self.ui.config('convert', 'svn.branches')
        trunk = (cfgtrunk or 'trunk').strip('/')
        branches = (cfgbranches or 'branches').strip('/')
        if self.exists(trunk, rev) and self.exists(branches, rev):
            self.ui.note('found trunk at %r and branches at %r\n' %
                         (trunk, branches))
            oldmodule = self.module
            self.module += '/' + trunk
            lt = self.latest(self.module, self.last_changed)
            self.head = self.revid(lt)
            self.heads = [self.head]
            branchnames = svn.client.ls(rpath + '/' + branches, rev, False,
                                        self.ctx)
            for branch in branchnames.keys():
                if oldmodule:
                    module = '/' + oldmodule + '/' + branches + '/' + branch
                else:
                    module = '/' + branches + '/' + branch
                brevnum = self.latest(module, self.last_changed)
                brev = self.revid(brevnum, module)
                self.ui.note('found branch %s at %d\n' % (branch, brevnum))
                self.heads.append(brev)
        elif cfgtrunk or cfgbranches:
            raise util.Abort('trunk/branch layout expected, but not found')
        else:
            self.ui.note('working with one branch\n')
            self.heads = [self.head]
        return self.heads

    def getfile(self, file, rev):
        data, mode = self._getfile(file, rev)
        self.modecache[(file, rev)] = mode
        return data

    def getmode(self, file, rev):
        return self.modecache[(file, rev)]

    def getchanges(self, rev):
        if self._changescache and self._changescache[0] == rev:
            return self._changescache[1]
        self._changescache = None
        self.modecache = {}
        (paths, parents) = self.paths[rev]
        files, copies = self.expandpaths(rev, paths, parents)
        files.sort()
        files = zip(files, [rev] * len(files))

        # caller caches the result, so free it here to release memory
        del self.paths[rev]
        return (files, copies)

    def getchangedfiles(self, rev, i):
        changes = self.getchanges(rev)
        self._changescache = (rev, changes)
        return [f[0] for f in changes[0]]

    def getcommit(self, rev):
        if rev not in self.commits:
            uuid, module, revnum = self.revsplit(rev)
            self.module = module
            self.reparent(module)
            stop = self.lastrevs.get(module, 0)
            self._fetch_revisions(from_revnum=revnum, to_revnum=stop)
        commit = self.commits[rev]
        # caller caches the result, so free it here to release memory
        del self.commits[rev]
        return commit

    def get_log(self, paths, start, end, limit=0, discover_changed_paths=True,
                strict_node_history=False):

        def parent(fp):
            while True:
                entry = pickle.load(fp)
                try:
                    orig_paths, revnum, author, date, message = entry
                except:
                    if entry is None:
                        break
                    raise SubversionException("child raised exception", entry)
                yield entry

        args = [self.url, paths, start, end, limit, discover_changed_paths,
                strict_node_history]
        arg = encodeargs(args)
        hgexe = util.hgexecutable()
        cmd = '%s debugsvnlog' % util.shellquote(hgexe)
        stdin, stdout = os.popen2(cmd, 'b')

        stdin.write(arg)
        stdin.close()

        for p in parent(stdout):
            yield p

    def gettags(self):
        tags = {}
        start = self.revnum(self.head)
        try:
            for entry in self.get_log(['/tags'], 0, start):
                orig_paths, revnum, author, date, message = entry
                for path in orig_paths:
                    if not path.startswith('/tags/'):
                        continue
                    ent = orig_paths[path]
                    source = ent.copyfrom_path
                    rev = ent.copyfrom_rev
                    tag = path.split('/', 2)[2]
                    tags[tag] = self.revid(rev, module=source)
        except SubversionException, (inst, num):
            self.ui.note('no tags found at revision %d\n' % start)
        return tags

    # -- helper functions --

    def revid(self, revnum, module=None):
        if not module:
            module = self.module
        return u"svn:%s%s@%s" % (self.uuid, module.decode(self.encoding),
                                 revnum)

    def revnum(self, rev):
        return int(rev.split('@')[-1])

    def revsplit(self, rev):
        url, revnum = rev.encode(self.encoding).split('@', 1)
        revnum = int(revnum)
        parts = url.split('/', 1)
        uuid = parts.pop(0)[4:]
        mod = ''
        if parts:
            mod = '/' + parts[0]
        return uuid, mod, revnum

    def latest(self, path, stop=0):
        'find the latest revision affecting path, up to stop'
        if not stop:
            stop = svn.ra.get_latest_revnum(self.ra)
        try:
            self.reparent('')
            dirent = svn.ra.stat(self.ra, path.strip('/'), stop)
            self.reparent(self.module)
        except SubversionException:
            dirent = None
        if not dirent:
            raise util.Abort('%s not found up to revision %d' % (path, stop))

        return dirent.created_rev

    def get_blacklist(self):
        """Avoid certain revision numbers.
        It is not uncommon for two nearby revisions to cancel each other
        out, e.g. 'I copied trunk into a subdirectory of itself instead
        of making a branch'. The converted repository is significantly
        smaller if we ignore such revisions."""
        self.blacklist = util.set()
        blacklist = self.blacklist
        for line in file("blacklist.txt", "r"):
            if not line.startswith("#"):
                try:
                    svn_rev = int(line.strip())
                    blacklist.add(svn_rev)
                except ValueError, e:
                    pass # not an integer or a comment

    def is_blacklisted(self, svn_rev):
        return svn_rev in self.blacklist

    def reparent(self, module):
        svn_url = self.base + module
        self.ui.debug("reparent to %s\n" % svn_url.encode(self.encoding))
        svn.ra.reparent(self.ra, svn_url.encode(self.encoding))

    def expandpaths(self, rev, paths, parents):
        def get_entry_from_path(path, module=self.module):
            # Given the repository url of this wc, say
            #   "http://server/plone/CMFPlone/branches/Plone-2_0-branch"
            # extract the "entry" portion (a relative path) from what
            # svn log --xml says, ie
            #   "/CMFPlone/branches/Plone-2_0-branch/tests/PloneTestCase.py"
            # that is to say "tests/PloneTestCase.py"
            if path.startswith(module):
                relative = path[len(module):]
                if relative.startswith('/'):
                    return relative[1:]
                else:
                    return relative

            # The path is outside our tracked tree...
            self.ui.debug('%r is not under %r, ignoring\n' % (path, module))
            return None

        entries = []
        copyfrom = {} # Map of entrypath, revision for finding source of deleted revisions.
        copies = {}
        revnum = self.revnum(rev)

        if revnum in self.modulemap:
            new_module = self.modulemap[revnum]
            if new_module != self.module:
                self.module = new_module
                self.reparent(self.module)

        for path, ent in paths:
            entrypath = get_entry_from_path(path, module=self.module)
            entry = entrypath.decode(self.encoding)

            kind = svn.ra.check_path(self.ra, entrypath, revnum)
            if kind == svn.core.svn_node_file:
                if ent.copyfrom_path:
                    copyfrom_path = get_entry_from_path(ent.copyfrom_path)
                    if copyfrom_path:
                        self.ui.debug("Copied to %s from %s@%s\n" % (entry, copyfrom_path, ent.copyfrom_rev))
                        # It's probably important for hg that the source
                        # exists in the revision's parent, not just the
                        # ent.copyfrom_rev
                        fromkind = svn.ra.check_path(self.ra, copyfrom_path, ent.copyfrom_rev)
                        if fromkind != 0:
                            copies[self.recode(entry)] = self.recode(copyfrom_path)
                entries.append(self.recode(entry))
            elif kind == 0: # gone, but had better be a deleted *file*
                self.ui.debug("gone from %s\n" % ent.copyfrom_rev)

                # if a branch is created but entries are removed in the same
                # changeset, get the right fromrev
                if parents:
                    uuid, old_module, fromrev = self.revsplit(parents[0])
                else:
                    fromrev = revnum - 1
                    # might always need to be revnum - 1 in these 3 lines?
                    old_module = self.modulemap.get(fromrev, self.module)

                basepath = old_module + "/" + get_entry_from_path(path, module=self.module)
                entrypath = old_module + "/" + get_entry_from_path(path, module=self.module)

                def lookup_parts(p):
                    rc = None
                    parts = p.split("/")
                    for i in range(len(parts)):
                        part = "/".join(parts[:i])
                        info = part, copyfrom.get(part, None)
                        if info[1] is not None:
                            self.ui.debug("Found parent directory %s\n" % info[1])
                            rc = info
                    return rc

                self.ui.debug("base, entry %s %s\n" % (basepath, entrypath))

                frompath, froment = lookup_parts(entrypath) or (None, revnum - 1)

                # need to remove fragment from lookup_parts and replace with copyfrom_path
                if frompath is not None:
                    self.ui.debug("munge-o-matic\n")
                    self.ui.debug(entrypath + '\n')
                    self.ui.debug(entrypath[len(frompath):] + '\n')
                    entrypath = froment.copyfrom_path + entrypath[len(frompath):]
                    fromrev = froment.copyfrom_rev
                    self.ui.debug("Info: %s %s %s %s\n" % (frompath, froment, ent, entrypath))

                fromkind = svn.ra.check_path(self.ra, entrypath, fromrev)
                if fromkind == svn.core.svn_node_file:   # a deleted file
                    entries.append(self.recode(entry))
                elif fromkind == svn.core.svn_node_dir:
                    # print "Deleted/moved non-file:", revnum, path, ent
                    # children = self._find_children(path, revnum - 1)
                    # print "find children %s@%d from %d action %s" % (path, revnum, ent.copyfrom_rev, ent.action)
                    # Sometimes this is tricky. For example: in
                    # The Subversion Repository revision 6940 a dir
                    # was copied and one of its files was deleted
                    # from the new location in the same commit. This
                    # code can't deal with that yet.
                    if ent.action == 'C':
                        children = self._find_children(path, fromrev)
                    else:
                        oroot = entrypath.strip('/')
                        nroot = path.strip('/')
                        children = self._find_children(oroot, fromrev)
                        children = [s.replace(oroot,nroot) for s in children]
                    # Mark all [files, not directories] as deleted.
                    for child in children:
                        # Can we move a child directory and its
                        # parent in the same commit? (probably can). Could
                        # cause problems if instead of revnum -1,
                        # we have to look in (copyfrom_path, revnum - 1)
                        entrypath = get_entry_from_path("/" + child, module=old_module)
                        if entrypath:
                            entry = self.recode(entrypath.decode(self.encoding))
                            if entry in copies:
                                # deleted file within a copy
                                del copies[entry]
                            else:
                                entries.append(entry)
                else:
                    self.ui.debug('unknown path in revision %d: %s\n' % \
                                  (revnum, path))
            elif kind == svn.core.svn_node_dir:
                # Should probably synthesize normal file entries
                # and handle as above to clean up copy/rename handling.

                # If the directory just had a prop change,
                # then we shouldn't need to look for its children.
                # Also this could create duplicate entries. Not sure
                # whether this will matter. Maybe should make entries a set.
                # print "Changed directory", revnum, path, ent.action, ent.copyfrom_path, ent.copyfrom_rev
                # This will fail if a directory was copied
                # from another branch and then some of its files
                # were deleted in the same transaction.
                children = self._find_children(path, revnum)
                children.sort()
                for child in children:
                    # Can we move a child directory and its
                    # parent in the same commit? (probably can). Could
                    # cause problems if instead of revnum -1,
                    # we have to look in (copyfrom_path, revnum - 1)
                    entrypath = get_entry_from_path("/" + child, module=self.module)
                    # print child, self.module, entrypath
                    if entrypath:
                        # Need to filter out directories here...
                        kind = svn.ra.check_path(self.ra, entrypath, revnum)
                        if kind != svn.core.svn_node_dir:
                            entries.append(self.recode(entrypath))

                # Copies here (must copy all from source)
                # Probably not a real problem for us if
                # source does not exist

                # Can do this with the copy command "hg copy"
                # if ent.copyfrom_path:
                #     copyfrom_entry = get_entry_from_path(ent.copyfrom_path.decode(self.encoding),
                #             module=self.module)
                #     copyto_entry = entrypath
                #
                #     print "copy directory", copyfrom_entry, 'to', copyto_entry
                #
                #     copies.append((copyfrom_entry, copyto_entry))

                if ent.copyfrom_path:
                    copyfrom_path = ent.copyfrom_path.decode(self.encoding)
                    copyfrom_entry = get_entry_from_path(copyfrom_path, module=self.module)
                    if copyfrom_entry:
                        copyfrom[path] = ent
                        self.ui.debug("mark %s came from %s\n" % (path, copyfrom[path]))

                        # Good, /probably/ a regular copy. Really should check
                        # to see whether the parent revision actually contains
                        # the directory in question.
                        children = self._find_children(self.recode(copyfrom_path), ent.copyfrom_rev)
                        children.sort()
                        for child in children:
                            entrypath = get_entry_from_path("/" + child, module=self.module)
                            if entrypath:
                                entry = entrypath.decode(self.encoding)
                                # print "COPY COPY From", copyfrom_entry, entry
                                copyto_path = path + entry[len(copyfrom_entry):]
                                copyto_entry =  get_entry_from_path(copyto_path, module=self.module)
                                # print "COPY", entry, "COPY To", copyto_entry
                                copies[self.recode(copyto_entry)] = self.recode(entry)
                                # copy from quux splort/quuxfile

        return (entries, copies)

    def _fetch_revisions(self, from_revnum = 0, to_revnum = 347):
        self.child_cset = None
        def parselogentry(orig_paths, revnum, author, date, message):
            self.ui.debug("parsing revision %d (%d changes)\n" %
                          (revnum, len(orig_paths)))

            if revnum in self.modulemap:
                new_module = self.modulemap[revnum]
                if new_module != self.module:
                    self.module = new_module
                    self.reparent(self.module)

            rev = self.revid(revnum)
            # branch log might return entries for a parent we already have
            if (rev in self.commits or
                (revnum < self.lastrevs.get(self.module, 0))):
                return

            parents = []
            # check whether this revision is the start of a branch
            if self.module in orig_paths:
                ent = orig_paths[self.module]
                if ent.copyfrom_path:
                    # ent.copyfrom_rev may not be the actual last revision
                    prev = self.latest(ent.copyfrom_path, ent.copyfrom_rev)
                    self.modulemap[prev] = ent.copyfrom_path
                    parents = [self.revid(prev, ent.copyfrom_path)]
                    self.ui.note('found parent of branch %s at %d: %s\n' % \
                                     (self.module, prev, ent.copyfrom_path))
                else:
                    self.ui.debug("No copyfrom path, don't know what to do.\n")

            self.modulemap[revnum] = self.module # track backwards in time

            orig_paths = orig_paths.items()
            orig_paths.sort()
            paths = []
            # filter out unrelated paths
            for path, ent in orig_paths:
                if not path.startswith(self.module):
                    self.ui.debug("boring@%s: %s\n" % (revnum, path))
                    continue
                paths.append((path, ent))

            self.paths[rev] = (paths, parents)

            # Example SVN datetime. Includes microseconds.
            # ISO-8601 conformant
            # '2007-01-04T17:35:00.902377Z'
            date = util.parsedate(date[:18] + " UTC", ["%Y-%m-%dT%H:%M:%S"])

            log = message and self.recode(message)
            author = author and self.recode(author) or ''
            try:
                branch = self.module.split("/")[-1]
                if branch == 'trunk':
                    branch = ''
            except IndexError:
                branch = None

            cset = commit(author=author,
                          date=util.datestr(date),
                          desc=log,
                          parents=parents,
                          branch=branch,
                          rev=rev.encode('utf-8'))

            self.commits[rev] = cset
            if self.child_cset and not self.child_cset.parents:
                self.child_cset.parents = [rev]
            self.child_cset = cset

        self.ui.note('fetching revision log for "%s" from %d to %d\n' %
                     (self.module, from_revnum, to_revnum))

        try:
            for entry in self.get_log([self.module], from_revnum, to_revnum):
                orig_paths, revnum, author, date, message = entry
                if self.is_blacklisted(revnum):
                    self.ui.note('skipping blacklisted revision %d\n' % revnum)
                    continue
                if orig_paths is None:
                    self.ui.debug('revision %d has no entries\n' % revnum)
                    continue
                parselogentry(orig_paths, revnum, author, date, message)
        except SubversionException, (inst, num):
            if num == svn.core.SVN_ERR_FS_NO_SUCH_REVISION:
                raise NoSuchRevision(branch=self,
                    revision="Revision number %d" % to_revnum)
            raise

    def _getfile(self, file, rev):
        io = StringIO()
        # TODO: ra.get_file transmits the whole file instead of diffs.
        mode = ''
        try:
            revnum = self.revnum(rev)
            if self.module != self.modulemap[revnum]:
                self.module = self.modulemap[revnum]
                self.reparent(self.module)
            info = svn.ra.get_file(self.ra, file, revnum, io)
            if isinstance(info, list):
                info = info[-1]
            mode = ("svn:executable" in info) and 'x' or ''
            mode = ("svn:special" in info) and 'l' or mode
        except SubversionException, e:
            notfound = (svn.core.SVN_ERR_FS_NOT_FOUND,
                svn.core.SVN_ERR_RA_DAV_PATH_NOT_FOUND)
            if e.apr_err in notfound: # File not found
                raise IOError()
            raise
        data = io.getvalue()
        if mode == 'l':
            link_prefix = "link "
            if data.startswith(link_prefix):
                data = data[len(link_prefix):]
        return data, mode

    def _find_children(self, path, revnum):
        path = path.strip('/')
        pool = Pool()
        rpath = '/'.join([self.base, path]).strip('/')
        return ['%s/%s' % (path, x) for x in svn.client.ls(rpath, optrev(revnum), True, self.ctx, pool).keys()]
