# posix.py - Posix utility function implementations for Mercurial
#
#  Copyright 2005-2009 Matt Mackall <mpm@selenic.com> and others
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from __future__ import absolute_import

import errno
import fcntl
import getpass
import grp
import os
import pwd
import re
import select
import stat
import sys
import tempfile
import unicodedata

from .i18n import _
from . import (
    encoding,
    error,
    pycompat,
)

posixfile = open
normpath = os.path.normpath
samestat = os.path.samestat
try:
    oslink = os.link
except AttributeError:
    # Some platforms build Python without os.link on systems that are
    # vaguely unix-like but don't have hardlink support. For those
    # poor souls, just say we tried and that it failed so we fall back
    # to copies.
    def oslink(src, dst):
        raise OSError(errno.EINVAL,
                      'hardlinks not supported: %s to %s' % (src, dst))
unlink = os.unlink
rename = os.rename
removedirs = os.removedirs
expandglobs = False

umask = os.umask(0)
os.umask(umask)

def split(p):
    '''Same as posixpath.split, but faster

    >>> import posixpath
    >>> for f in ['/absolute/path/to/file',
    ...           'relative/path/to/file',
    ...           'file_alone',
    ...           'path/to/directory/',
    ...           '/multiple/path//separators',
    ...           '/file_at_root',
    ...           '///multiple_leading_separators_at_root',
    ...           '']:
    ...     assert split(f) == posixpath.split(f), f
    '''
    ht = p.rsplit('/', 1)
    if len(ht) == 1:
        return '', p
    nh = ht[0].rstrip('/')
    if nh:
        return nh, ht[1]
    return ht[0] + '/', ht[1]

def openhardlinks():
    '''return true if it is safe to hold open file handles to hardlinks'''
    return True

def nlinks(name):
    '''return number of hardlinks for the given file'''
    return os.lstat(name).st_nlink

def parsepatchoutput(output_line):
    """parses the output produced by patch and returns the filename"""
    pf = output_line[14:]
    if pycompat.sysplatform == 'OpenVMS':
        if pf[0] == '`':
            pf = pf[1:-1] # Remove the quotes
    else:
        if pf.startswith("'") and pf.endswith("'") and " " in pf:
            pf = pf[1:-1] # Remove the quotes
    return pf

def sshargs(sshcmd, host, user, port):
    '''Build argument list for ssh'''
    args = user and ("%s@%s" % (user, host)) or host
    if '-' in args[:2]:
        raise error.Abort(
            _('illegal ssh hostname or username starting with -: %s') % args)
    return port and ("%s -p %s" % (args, port)) or args

def isexec(f):
    """check whether a file is executable"""
    return (os.lstat(f).st_mode & 0o100 != 0)

def setflags(f, l, x):
    st = os.lstat(f)
    s = st.st_mode
    if l:
        if not stat.S_ISLNK(s):
            # switch file to link
            fp = open(f)
            data = fp.read()
            fp.close()
            unlink(f)
            try:
                os.symlink(data, f)
            except OSError:
                # failed to make a link, rewrite file
                fp = open(f, "w")
                fp.write(data)
                fp.close()
        # no chmod needed at this point
        return
    if stat.S_ISLNK(s):
        # switch link to file
        data = os.readlink(f)
        unlink(f)
        fp = open(f, "w")
        fp.write(data)
        fp.close()
        s = 0o666 & ~umask # avoid restatting for chmod

    sx = s & 0o100
    if st.st_nlink > 1 and bool(x) != bool(sx):
        # the file is a hardlink, break it
        with open(f, "rb") as fp:
            data = fp.read()
        unlink(f)
        with open(f, "wb") as fp:
            fp.write(data)

    if x and not sx:
        # Turn on +x for every +r bit when making a file executable
        # and obey umask.
        os.chmod(f, s | (s & 0o444) >> 2 & ~umask)
    elif not x and sx:
        # Turn off all +x bits
        os.chmod(f, s & 0o666)

def copymode(src, dst, mode=None):
    '''Copy the file mode from the file at path src to dst.
    If src doesn't exist, we're using mode instead. If mode is None, we're
    using umask.'''
    try:
        st_mode = os.lstat(src).st_mode & 0o777
    except OSError as inst:
        if inst.errno != errno.ENOENT:
            raise
        st_mode = mode
        if st_mode is None:
            st_mode = ~umask
        st_mode &= 0o666
    os.chmod(dst, st_mode)

def checkexec(path):
    """
    Check whether the given path is on a filesystem with UNIX-like exec flags

    Requires a directory (like /foo/.hg)
    """

    # VFAT on some Linux versions can flip mode but it doesn't persist
    # a FS remount. Frequently we can detect it if files are created
    # with exec bit on.

    try:
        EXECFLAGS = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        cachedir = os.path.join(path, '.hg', 'cache')
        if os.path.isdir(cachedir):
            checkisexec = os.path.join(cachedir, 'checkisexec')
            checknoexec = os.path.join(cachedir, 'checknoexec')

            try:
                m = os.stat(checkisexec).st_mode
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
                # checkisexec does not exist - fall through ...
            else:
                # checkisexec exists, check if it actually is exec
                if m & EXECFLAGS != 0:
                    # ensure checkisexec exists, check it isn't exec
                    try:
                        m = os.stat(checknoexec).st_mode
                    except OSError as e:
                        if e.errno != errno.ENOENT:
                            raise
                        open(checknoexec, 'w').close() # might fail
                        m = os.stat(checknoexec).st_mode
                    if m & EXECFLAGS == 0:
                        # check-exec is exec and check-no-exec is not exec
                        return True
                    # checknoexec exists but is exec - delete it
                    unlink(checknoexec)
                # checkisexec exists but is not exec - delete it
                unlink(checkisexec)

            # check using one file, leave it as checkisexec
            checkdir = cachedir
        else:
            # check directly in path and don't leave checkisexec behind
            checkdir = path
            checkisexec = None
        fh, fn = tempfile.mkstemp(dir=checkdir, prefix='hg-checkexec-')
        try:
            os.close(fh)
            m = os.stat(fn).st_mode
            if m & EXECFLAGS == 0:
                os.chmod(fn, m & 0o777 | EXECFLAGS)
                if os.stat(fn).st_mode & EXECFLAGS != 0:
                    if checkisexec is not None:
                        os.rename(fn, checkisexec)
                        fn = None
                    return True
        finally:
            if fn is not None:
                unlink(fn)
    except (IOError, OSError):
        # we don't care, the user probably won't be able to commit anyway
        return False

def checklink(path):
    """check whether the given path is on a symlink-capable filesystem"""
    # mktemp is not racy because symlink creation will fail if the
    # file already exists
    while True:
        cachedir = os.path.join(path, '.hg', 'cache')
        checklink = os.path.join(cachedir, 'checklink')
        # try fast path, read only
        if os.path.islink(checklink):
            return True
        if os.path.isdir(cachedir):
            checkdir = cachedir
        else:
            checkdir = path
            cachedir = None
        fscheckdir = pycompat.fsdecode(checkdir)
        name = tempfile.mktemp(dir=fscheckdir,
                               prefix=r'checklink-')
        name = pycompat.fsencode(name)
        try:
            fd = None
            if cachedir is None:
                fd = tempfile.NamedTemporaryFile(dir=fscheckdir,
                                                 prefix=r'hg-checklink-')
                target = pycompat.fsencode(os.path.basename(fd.name))
            else:
                # create a fixed file to link to; doesn't matter if it
                # already exists.
                target = 'checklink-target'
                try:
                    open(os.path.join(cachedir, target), 'w').close()
                except IOError as inst:
                    if inst[0] == errno.EACCES:
                        # If we can't write to cachedir, just pretend
                        # that the fs is readonly and by association
                        # that the fs won't support symlinks. This
                        # seems like the least dangerous way to avoid
                        # data loss.
                        return False
                    raise
            try:
                os.symlink(target, name)
                if cachedir is None:
                    unlink(name)
                else:
                    try:
                        os.rename(name, checklink)
                    except OSError:
                        unlink(name)
                return True
            except OSError as inst:
                # link creation might race, try again
                if inst[0] == errno.EEXIST:
                    continue
                raise
            finally:
                if fd is not None:
                    fd.close()
        except AttributeError:
            return False
        except OSError as inst:
            # sshfs might report failure while successfully creating the link
            if inst[0] == errno.EIO and os.path.exists(name):
                unlink(name)
            return False

def checkosfilename(path):
    '''Check that the base-relative path is a valid filename on this platform.
    Returns None if the path is ok, or a UI string describing the problem.'''
    pass # on posix platforms, every path is ok

def setbinary(fd):
    pass

def pconvert(path):
    return path

def localpath(path):
    return path

def samefile(fpath1, fpath2):
    """Returns whether path1 and path2 refer to the same file. This is only
    guaranteed to work for files, not directories."""
    return os.path.samefile(fpath1, fpath2)

def samedevice(fpath1, fpath2):
    """Returns whether fpath1 and fpath2 are on the same device. This is only
    guaranteed to work for files, not directories."""
    st1 = os.lstat(fpath1)
    st2 = os.lstat(fpath2)
    return st1.st_dev == st2.st_dev

# os.path.normcase is a no-op, which doesn't help us on non-native filesystems
def normcase(path):
    return path.lower()

# what normcase does to ASCII strings
normcasespec = encoding.normcasespecs.lower
# fallback normcase function for non-ASCII strings
normcasefallback = normcase

if pycompat.sysplatform == 'darwin':

    def normcase(path):
        '''
        Normalize a filename for OS X-compatible comparison:
        - escape-encode invalid characters
        - decompose to NFD
        - lowercase
        - omit ignored characters [200c-200f, 202a-202e, 206a-206f,feff]

        >>> normcase('UPPER')
        'upper'
        >>> normcase('Caf\xc3\xa9')
        'cafe\\xcc\\x81'
        >>> normcase('\xc3\x89')
        'e\\xcc\\x81'
        >>> normcase('\xb8\xca\xc3\xca\xbe\xc8.JPG') # issue3918
        '%b8%ca%c3\\xca\\xbe%c8.jpg'
        '''

        try:
            return encoding.asciilower(path)  # exception for non-ASCII
        except UnicodeDecodeError:
            return normcasefallback(path)

    normcasespec = encoding.normcasespecs.lower

    def normcasefallback(path):
        try:
            u = path.decode('utf-8')
        except UnicodeDecodeError:
            # OS X percent-encodes any bytes that aren't valid utf-8
            s = ''
            pos = 0
            l = len(path)
            while pos < l:
                try:
                    c = encoding.getutf8char(path, pos)
                    pos += len(c)
                except ValueError:
                    c = '%%%02X' % ord(path[pos])
                    pos += 1
                s += c

            u = s.decode('utf-8')

        # Decompose then lowercase (HFS+ technote specifies lower)
        enc = unicodedata.normalize('NFD', u).lower().encode('utf-8')
        # drop HFS+ ignored characters
        return encoding.hfsignoreclean(enc)

if pycompat.sysplatform == 'cygwin':
    # workaround for cygwin, in which mount point part of path is
    # treated as case sensitive, even though underlying NTFS is case
    # insensitive.

    # default mount points
    cygwinmountpoints = sorted([
            "/usr/bin",
            "/usr/lib",
            "/cygdrive",
            ], reverse=True)

    # use upper-ing as normcase as same as NTFS workaround
    def normcase(path):
        pathlen = len(path)
        if (pathlen == 0) or (path[0] != pycompat.ossep):
            # treat as relative
            return encoding.upper(path)

        # to preserve case of mountpoint part
        for mp in cygwinmountpoints:
            if not path.startswith(mp):
                continue

            mplen = len(mp)
            if mplen == pathlen: # mount point itself
                return mp
            if path[mplen] == pycompat.ossep:
                return mp + encoding.upper(path[mplen:])

        return encoding.upper(path)

    normcasespec = encoding.normcasespecs.other
    normcasefallback = normcase

    # Cygwin translates native ACLs to POSIX permissions,
    # but these translations are not supported by native
    # tools, so the exec bit tends to be set erroneously.
    # Therefore, disable executable bit access on Cygwin.
    def checkexec(path):
        return False

    # Similarly, Cygwin's symlink emulation is likely to create
    # problems when Mercurial is used from both Cygwin and native
    # Windows, with other native tools, or on shared volumes
    def checklink(path):
        return False

_needsshellquote = None
def shellquote(s):
    if pycompat.sysplatform == 'OpenVMS':
        return '"%s"' % s
    global _needsshellquote
    if _needsshellquote is None:
        _needsshellquote = re.compile(br'[^a-zA-Z0-9._/+-]').search
    if s and not _needsshellquote(s):
        # "s" shouldn't have to be quoted
        return s
    else:
        return "'%s'" % s.replace("'", "'\\''")

def quotecommand(cmd):
    return cmd

def popen(command, mode='r'):
    return os.popen(command, mode)

def testpid(pid):
    '''return False if pid dead, True if running or not sure'''
    if pycompat.sysplatform == 'OpenVMS':
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError as inst:
        return inst.errno != errno.ESRCH

def explainexit(code):
    """return a 2-tuple (desc, code) describing a subprocess status
    (codes from kill are negative - not os.system/wait encoding)"""
    if code >= 0:
        return _("exited with status %d") % code, code
    return _("killed by signal %d") % -code, -code

def isowner(st):
    """Return True if the stat object st is from the current user."""
    return st.st_uid == os.getuid()

def findexe(command):
    '''Find executable for command searching like which does.
    If command is a basename then PATH is searched for command.
    PATH isn't searched if command is an absolute or relative path.
    If command isn't found None is returned.'''
    if pycompat.sysplatform == 'OpenVMS':
        return command

    def findexisting(executable):
        'Will return executable if existing file'
        if os.path.isfile(executable) and os.access(executable, os.X_OK):
            return executable
        return None

    if pycompat.ossep in command:
        return findexisting(command)

    if pycompat.sysplatform == 'plan9':
        return findexisting(os.path.join('/bin', command))

    for path in encoding.environ.get('PATH', '').split(pycompat.ospathsep):
        executable = findexisting(os.path.join(path, command))
        if executable is not None:
            return executable
    return None

def setsignalhandler():
    pass

_wantedkinds = {stat.S_IFREG, stat.S_IFLNK}

def statfiles(files):
    '''Stat each file in files. Yield each stat, or None if a file does not
    exist or has a type we don't care about.'''
    lstat = os.lstat
    getkind = stat.S_IFMT
    for nf in files:
        try:
            st = lstat(nf)
            if getkind(st.st_mode) not in _wantedkinds:
                st = None
        except OSError as err:
            if err.errno not in (errno.ENOENT, errno.ENOTDIR):
                raise
            st = None
        yield st

def getuser():
    '''return name of current user'''
    return pycompat.fsencode(getpass.getuser())

def username(uid=None):
    """Return the name of the user with the given uid.

    If uid is None, return the name of the current user."""

    if uid is None:
        uid = os.getuid()
    try:
        return pwd.getpwuid(uid)[0]
    except KeyError:
        return str(uid)

def groupname(gid=None):
    """Return the name of the group with the given gid.

    If gid is None, return the name of the current group."""

    if gid is None:
        gid = os.getgid()
    try:
        return grp.getgrgid(gid)[0]
    except KeyError:
        return str(gid)

def groupmembers(name):
    """Return the list of members of the group with the given
    name, KeyError if the group does not exist.
    """
    return list(grp.getgrnam(name).gr_mem)

def spawndetached(args):
    return os.spawnvp(os.P_NOWAIT | getattr(os, 'P_DETACH', 0),
                      args[0], args)

def gethgcmd():
    return sys.argv[:1]

def makedir(path, notindexed):
    os.mkdir(path)

def lookupreg(key, name=None, scope=None):
    return None

def hidewindow():
    """Hide current shell window.

    Used to hide the window opened when starting asynchronous
    child process under Windows, unneeded on other systems.
    """
    pass

class cachestat(object):
    def __init__(self, path):
        self.stat = os.stat(path)

    def cacheable(self):
        return bool(self.stat.st_ino)

    __hash__ = object.__hash__

    def __eq__(self, other):
        try:
            # Only dev, ino, size, mtime and atime are likely to change. Out
            # of these, we shouldn't compare atime but should compare the
            # rest. However, one of the other fields changing indicates
            # something fishy going on, so return False if anything but atime
            # changes.
            return (self.stat.st_mode == other.stat.st_mode and
                    self.stat.st_ino == other.stat.st_ino and
                    self.stat.st_dev == other.stat.st_dev and
                    self.stat.st_nlink == other.stat.st_nlink and
                    self.stat.st_uid == other.stat.st_uid and
                    self.stat.st_gid == other.stat.st_gid and
                    self.stat.st_size == other.stat.st_size and
                    self.stat.st_mtime == other.stat.st_mtime and
                    self.stat.st_ctime == other.stat.st_ctime)
        except AttributeError:
            return False

    def __ne__(self, other):
        return not self == other

def executablepath():
    return None # available on Windows only

def statislink(st):
    '''check whether a stat result is a symlink'''
    return st and stat.S_ISLNK(st.st_mode)

def statisexec(st):
    '''check whether a stat result is an executable file'''
    return st and (st.st_mode & 0o100 != 0)

def poll(fds):
    """block until something happens on any file descriptor

    This is a generic helper that will check for any activity
    (read, write.  exception) and return the list of touched files.

    In unsupported cases, it will raise a NotImplementedError"""
    try:
        while True:
            try:
                res = select.select(fds, fds, fds)
                break
            except select.error as inst:
                if inst.args[0] == errno.EINTR:
                    continue
                raise
    except ValueError: # out of range file descriptor
        raise NotImplementedError()
    return sorted(list(set(sum(res, []))))

def readpipe(pipe):
    """Read all available data from a pipe."""
    # We can't fstat() a pipe because Linux will always report 0.
    # So, we set the pipe to non-blocking mode and read everything
    # that's available.
    flags = fcntl.fcntl(pipe, fcntl.F_GETFL)
    flags |= os.O_NONBLOCK
    oldflags = fcntl.fcntl(pipe, fcntl.F_SETFL, flags)

    try:
        chunks = []
        while True:
            try:
                s = pipe.read()
                if not s:
                    break
                chunks.append(s)
            except IOError:
                break

        return ''.join(chunks)
    finally:
        fcntl.fcntl(pipe, fcntl.F_SETFL, oldflags)

def bindunixsocket(sock, path):
    """Bind the UNIX domain socket to the specified path"""
    # use relative path instead of full path at bind() if possible, since
    # AF_UNIX path has very small length limit (107 chars) on common
    # platforms (see sys/un.h)
    dirname, basename = os.path.split(path)
    bakwdfd = None
    if dirname:
        bakwdfd = os.open('.', os.O_DIRECTORY)
        os.chdir(dirname)
    sock.bind(basename)
    if bakwdfd:
        os.fchdir(bakwdfd)
        os.close(bakwdfd)
