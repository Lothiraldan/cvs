# Copyright 2009-2010 Gregory P. Ward
# Copyright 2009-2010 Intelerad Medical Systems Incorporated
# Copyright 2010-2011 Fog Creek Software
# Copyright 2010-2011 Unity Technologies
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

'''largefiles utility code: must not import other modules in this package.'''

import os
import errno
import inspect
import shutil
import stat
import hashlib

from mercurial import cmdutil, dirstate, httpconnection, match as match_, \
        url as url_, util
from mercurial.i18n import _

try:
    from mercurial import scmutil
except ImportError:
    pass

shortname = '.hglf'
longname = 'largefiles'


# -- Portability wrappers ----------------------------------------------

if 'subrepos' in inspect.getargspec(dirstate.dirstate.status)[0]:
    # for Mercurial >= 1.5
    def dirstate_walk(dirstate, matcher, unknown=False, ignored=False):
        return dirstate.walk(matcher, [], unknown, ignored)
else:
    # for Mercurial <= 1.4
    def dirstate_walk(dirstate, matcher, unknown=False, ignored=False):
        return dirstate.walk(matcher, unknown, ignored)

def repo_add(repo, list):
    try:
        # Mercurial <= 1.5
        add = repo.add
    except AttributeError:
        # Mercurial >= 1.6
        add = repo[None].add
    return add(list)

def repo_remove(repo, list, unlink=False):
    try:
        # Mercurial <= 1.5
        remove = repo.remove
    except AttributeError:
        # Mercurial >= 1.6
        try:
            # Mercurial <= 1.8
            remove = repo[None].remove
        except AttributeError:
            # Mercurial >= 1.9
            def remove(list, unlink):
                wlock = repo.wlock()
                try:
                    if unlink:
                        for f in list:
                            try:
                                util.unlinkpath(repo.wjoin(f))
                            except OSError, inst:
                                if inst.errno != errno.ENOENT:
                                    raise
                    repo[None].forget(list)
                finally:
                    wlock.release()

    return remove(list, unlink=unlink)

def repo_forget(repo, list):
    try:
        # Mercurial <= 1.5
        forget = repo.forget
    except AttributeError:
        # Mercurial >= 1.6
        forget = repo[None].forget
    return forget(list)

def findoutgoing(repo, remote, force):
    # First attempt is for Mercurial <= 1.5 second is for >= 1.6
    try:
        return repo.findoutgoing(remote)
    except AttributeError:
        from mercurial import discovery
        try:
            # Mercurial <= 1.8
            return discovery.findoutgoing(repo, remote, force=force)
        except AttributeError:
            # Mercurial >= 1.9
            common, _anyinc, _heads = discovery.findcommonincoming(repo,
                remote, force=force)
            return repo.changelog.findmissing(common)

# -- Private worker functions ------------------------------------------

def link(src, dest):
    try:
        util.oslink(src, dest)
    except OSError:
        # If hardlinks fail fall back on copy
        shutil.copyfile(src, dest)
        os.chmod(dest, os.stat(src).st_mode)

def systemcachepath(ui, hash):
    path = ui.config(longname, 'systemcache', None)
    if path:
        path = os.path.join(path, hash)
    else:
        if os.name == 'nt':
            path = os.path.join(os.getenv('LOCALAPPDATA') or \
                os.getenv('APPDATA'), longname, hash)
        elif os.name == 'posix':
            path = os.path.join(os.getenv('HOME'), '.' + longname, hash)
        else:
            raise util.Abort(_('Unknown operating system: %s\n') % os.name)
    return path

def insystemcache(ui, hash):
    return os.path.exists(systemcachepath(ui, hash))

def findfile(repo, hash):
    if incache(repo, hash):
        repo.ui.note(_('Found %s in cache\n') % hash)
        return cachepath(repo, hash)
    if insystemcache(repo.ui, hash):
        repo.ui.note(_('Found %s in system cache\n') % hash)
        return systemcachepath(repo.ui, hash)
    return None

class largefiles_dirstate(dirstate.dirstate):
    def __getitem__(self, key):
        return super(largefiles_dirstate, self).__getitem__(unixpath(key))
    def normal(self, f):
        return super(largefiles_dirstate, self).normal(unixpath(f))
    def remove(self, f):
        return super(largefiles_dirstate, self).remove(unixpath(f))
    def add(self, f):
        return super(largefiles_dirstate, self).add(unixpath(f))
    def drop(self, f):
        return super(largefiles_dirstate, self).drop(unixpath(f))
    def forget(self, f):
        return super(largefiles_dirstate, self).forget(unixpath(f))

def openlfdirstate(ui, repo):
    '''
    Return a dirstate object that tracks big files: i.e. its root is the
    repo root, but it is saved in .hg/largefiles/dirstate.
    '''
    admin = repo.join(longname)
    try:
        # Mercurial >= 1.9
        opener = scmutil.opener(admin)
    except ImportError:
        # Mercurial <= 1.8
        opener = util.opener(admin)
    if util.safehasattr(repo.dirstate, '_validate'):
        lfdirstate = largefiles_dirstate(opener, ui, repo.root,
            repo.dirstate._validate)
    else:
        lfdirstate = largefiles_dirstate(opener, ui, repo.root)

    # If the largefiles dirstate does not exist, populate and create it.  This
    # ensures that we create it on the first meaningful largefiles operation in
    # a new clone.  It also gives us an easy way to forcibly rebuild largefiles
    # state:
    #   rm .hg/largefiles/dirstate && hg status
    # Or even, if things are really messed up:
    #   rm -rf .hg/largefiles && hg status
    if not os.path.exists(os.path.join(admin, 'dirstate')):
        util.makedirs(admin)
        matcher = getstandinmatcher(repo)
        for standin in dirstate_walk(repo.dirstate, matcher):
            lfile = splitstandin(standin)
            hash = readstandin(repo, lfile)
            lfdirstate.normallookup(lfile)
            try:
                if hash == hashfile(lfile):
                    lfdirstate.normal(lfile)
            except IOError, err:
                if err.errno != errno.ENOENT:
                    raise

        lfdirstate.write()

    return lfdirstate

def lfdirstate_status(lfdirstate, repo, rev):
    wlock = repo.wlock()
    try:
        match = match_.always(repo.root, repo.getcwd())
        s = lfdirstate.status(match, [], False, False, False)
        unsure, modified, added, removed, missing, unknown, ignored, clean = s
        for lfile in unsure:
            if repo[rev][standin(lfile)].data().strip() != \
                    hashfile(repo.wjoin(lfile)):
                modified.append(lfile)
            else:
                clean.append(lfile)
                lfdirstate.normal(lfile)
        lfdirstate.write()
    finally:
        wlock.release()
    return (modified, added, removed, missing, unknown, ignored, clean)

def listlfiles(repo, rev=None, matcher=None):
    '''list largefiles in the working copy or specified changeset'''

    if matcher is None:
        matcher = getstandinmatcher(repo)

    # ignore unknown files in working directory
    return [splitstandin(f) for f in repo[rev].walk(matcher) \
            if rev is not None or repo.dirstate[f] != '?']

def incache(repo, hash):
    return os.path.exists(cachepath(repo, hash))

def createdir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

def cachepath(repo, hash):
    return repo.join(os.path.join(longname, hash))

def copyfromcache(repo, hash, filename):
    '''copyfromcache copies the specified largefile from the repo or system
    cache to the specified location in the repository.  It will not throw an
    exception on failure, as it is meant to be called only after ensuring that
    the needed largefile exists in the cache.'''
    path = findfile(repo, hash)
    if path is None:
        return False
    util.makedirs(os.path.dirname(repo.wjoin(filename)))
    shutil.copy(path, repo.wjoin(filename))
    return True

def copytocache(repo, rev, file, uploaded=False):
    hash = readstandin(repo, file)
    if incache(repo, hash):
        return
    copytocacheabsolute(repo, repo.wjoin(file), hash)

def copytocacheabsolute(repo, file, hash):
    createdir(os.path.dirname(cachepath(repo, hash)))
    if insystemcache(repo.ui, hash):
        link(systemcachepath(repo.ui, hash), cachepath(repo, hash))
    else:
        shutil.copyfile(file, cachepath(repo, hash))
        os.chmod(cachepath(repo, hash), os.stat(file).st_mode)
        linktosystemcache(repo, hash)

def linktosystemcache(repo, hash):
    createdir(os.path.dirname(systemcachepath(repo.ui, hash)))
    link(cachepath(repo, hash), systemcachepath(repo.ui, hash))

def getstandinmatcher(repo, pats=[], opts={}):
    '''Return a match object that applies pats to the standin directory'''
    standindir = repo.pathto(shortname)
    if pats:
        # patterns supplied: search standin directory relative to current dir
        cwd = repo.getcwd()
        if os.path.isabs(cwd):
            # cwd is an absolute path for hg -R <reponame>
            # work relative to the repository root in this case
            cwd = ''
        pats = [os.path.join(standindir, cwd, pat) for pat in pats]
    elif os.path.isdir(standindir):
        # no patterns: relative to repo root
        pats = [standindir]
    else:
        # no patterns and no standin dir: return matcher that matches nothing
        match = match_.match(repo.root, None, [], exact=True)
        match.matchfn = lambda f: False
        return match
    return getmatcher(repo, pats, opts, showbad=False)

def getmatcher(repo, pats=[], opts={}, showbad=True):
    '''Wrapper around scmutil.match() that adds showbad: if false, neuter
    the match object\'s bad() method so it does not print any warnings
    about missing files or directories.'''
    try:
        # Mercurial >= 1.9
        match = scmutil.match(repo[None], pats, opts)
    except ImportError:
        # Mercurial <= 1.8
        match = cmdutil.match(repo, pats, opts)

    if not showbad:
        match.bad = lambda f, msg: None
    return match

def composestandinmatcher(repo, rmatcher):
    '''Return a matcher that accepts standins corresponding to the files
    accepted by rmatcher. Pass the list of files in the matcher as the
    paths specified by the user.'''
    smatcher = getstandinmatcher(repo, rmatcher.files())
    isstandin = smatcher.matchfn
    def composed_matchfn(f):
        return isstandin(f) and rmatcher.matchfn(splitstandin(f))
    smatcher.matchfn = composed_matchfn

    return smatcher

def standin(filename):
    '''Return the repo-relative path to the standin for the specified big
    file.'''
    # Notes:
    # 1) Most callers want an absolute path, but _create_standin() needs
    #    it repo-relative so lfadd() can pass it to repo_add().  So leave
    #    it up to the caller to use repo.wjoin() to get an absolute path.
    # 2) Join with '/' because that's what dirstate always uses, even on
    #    Windows. Change existing separator to '/' first in case we are
    #    passed filenames from an external source (like the command line).
    return shortname + '/' + filename.replace(os.sep, '/')

def isstandin(filename):
    '''Return true if filename is a big file standin.  filename must
    be in Mercurial\'s internal form (slash-separated).'''
    return filename.startswith(shortname + '/')

def splitstandin(filename):
    # Split on / because that's what dirstate always uses, even on Windows.
    # Change local separator to / first just in case we are passed filenames
    # from an external source (like the command line).
    bits = filename.replace(os.sep, '/').split('/', 1)
    if len(bits) == 2 and bits[0] == shortname:
        return bits[1]
    else:
        return None

def updatestandin(repo, standin):
    file = repo.wjoin(splitstandin(standin))
    if os.path.exists(file):
        hash = hashfile(file)
        executable = getexecutable(file)
        writestandin(repo, standin, hash, executable)

def readstandin(repo, filename, node=None):
    '''read hex hash from standin for filename at given node, or working
    directory if no node is given'''
    return repo[node][standin(filename)].data().strip()

def writestandin(repo, standin, hash, executable):
    '''write hhash to <repo.root>/<standin>'''
    writehash(hash, repo.wjoin(standin), executable)

def copyandhash(instream, outfile):
    '''Read bytes from instream (iterable) and write them to outfile,
    computing the SHA-1 hash of the data along the way.  Close outfile
    when done and return the binary hash.'''
    hasher = util.sha1('')
    for data in instream:
        hasher.update(data)
        outfile.write(data)

    # Blecch: closing a file that somebody else opened is rude and
    # wrong.  But it's so darn convenient and practical!  After all,
    # outfile was opened just to copy and hash.
    outfile.close()

    return hasher.digest()

def hashrepofile(repo, file):
    return hashfile(repo.wjoin(file))

def hashfile(file):
    if not os.path.exists(file):
        return ''
    hasher = util.sha1('')
    fd = open(file, 'rb')
    for data in blockstream(fd):
        hasher.update(data)
    fd.close()
    return hasher.hexdigest()

class limitreader(object):
    def __init__(self, f, limit):
        self.f = f
        self.limit = limit

    def read(self, length):
        if self.limit == 0:
            return ''
        length = length > self.limit and self.limit or length
        self.limit -= length
        return self.f.read(length)

    def close(self):
        pass

def blockstream(infile, blocksize=128 * 1024):
    """Generator that yields blocks of data from infile and closes infile."""
    while True:
        data = infile.read(blocksize)
        if not data:
            break
        yield data
    # Same blecch as above.
    infile.close()

def readhash(filename):
    rfile = open(filename, 'rb')
    hash = rfile.read(40)
    rfile.close()
    if len(hash) < 40:
        raise util.Abort(_('bad hash in \'%s\' (only %d bytes long)')
                         % (filename, len(hash)))
    return hash

def writehash(hash, filename, executable):
    util.makedirs(os.path.dirname(filename))
    if os.path.exists(filename):
        os.unlink(filename)
    wfile = open(filename, 'wb')

    try:
        wfile.write(hash)
        wfile.write('\n')
    finally:
        wfile.close()
    if os.path.exists(filename):
        os.chmod(filename, getmode(executable))

def getexecutable(filename):
    mode = os.stat(filename).st_mode
    return (mode & stat.S_IXUSR) and (mode & stat.S_IXGRP) and (mode & \
        stat.S_IXOTH)

def getmode(executable):
    if executable:
        return 0755
    else:
        return 0644

def urljoin(first, second, *arg):
    def join(left, right):
        if not left.endswith('/'):
            left += '/'
        if right.startswith('/'):
            right = right[1:]
        return left + right

    url = join(first, second)
    for a in arg:
        url = join(url, a)
    return url

def hexsha1(data):
    """hexsha1 returns the hex-encoded sha1 sum of the data in the file-like
    object data"""
    h = hashlib.sha1()
    for chunk in util.filechunkiter(data):
        h.update(chunk)
    return h.hexdigest()

def httpsendfile(ui, filename):
    try:
        # Mercurial >= 1.9
        return httpconnection.httpsendfile(ui, filename, 'rb')
    except ImportError:
        if 'ui' in inspect.getargspec(url_.httpsendfile.__init__)[0]:
            # Mercurial == 1.8
            return url_.httpsendfile(ui, filename, 'rb')
        else:
            # Mercurial <= 1.7
            return url_.httpsendfile(filename, 'rb')

# Convert a path to a unix style path. This is used to give a
# canonical path to the lfdirstate.
def unixpath(path):
    return os.path.normpath(path).replace(os.sep, '/')

def islfilesrepo(repo):
    return ('largefiles' in repo.requirements and
            any_(shortname + '/' in f[0] for f in repo.store.datafiles()))

def any_(gen):
    for x in gen:
        if x:
            return True
    return False

class storeprotonotcapable(BaseException):
    def __init__(self, storetypes):
        self.storetypes = storetypes
