# win32.py - utility functions that use win32 API
#
# Copyright 2005-2009 Matt Mackall <mpm@selenic.com> and others
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2, incorporated herein by reference.

"""Utility functions that use win32 API.

Mark Hammond's win32all package allows better functionality on
Windows. This module overrides definitions in util.py. If not
available, import of this module will fail, and generic code will be
used.
"""

import win32api

import errno, os, sys, pywintypes, win32con, win32file, win32process
import cStringIO, winerror
import osutil, encoding
import util
from win32com.shell import shell,shellcon

class WinError(Exception):
    winerror_map = {
        winerror.ERROR_ACCESS_DENIED: errno.EACCES,
        winerror.ERROR_ACCOUNT_DISABLED: errno.EACCES,
        winerror.ERROR_ACCOUNT_RESTRICTION: errno.EACCES,
        winerror.ERROR_ALREADY_ASSIGNED: errno.EBUSY,
        winerror.ERROR_ALREADY_EXISTS: errno.EEXIST,
        winerror.ERROR_ARITHMETIC_OVERFLOW: errno.ERANGE,
        winerror.ERROR_BAD_COMMAND: errno.EIO,
        winerror.ERROR_BAD_DEVICE: errno.ENODEV,
        winerror.ERROR_BAD_DRIVER_LEVEL: errno.ENXIO,
        winerror.ERROR_BAD_EXE_FORMAT: errno.ENOEXEC,
        winerror.ERROR_BAD_FORMAT: errno.ENOEXEC,
        winerror.ERROR_BAD_LENGTH: errno.EINVAL,
        winerror.ERROR_BAD_PATHNAME: errno.ENOENT,
        winerror.ERROR_BAD_PIPE: errno.EPIPE,
        winerror.ERROR_BAD_UNIT: errno.ENODEV,
        winerror.ERROR_BAD_USERNAME: errno.EINVAL,
        winerror.ERROR_BROKEN_PIPE: errno.EPIPE,
        winerror.ERROR_BUFFER_OVERFLOW: errno.ENAMETOOLONG,
        winerror.ERROR_BUSY: errno.EBUSY,
        winerror.ERROR_BUSY_DRIVE: errno.EBUSY,
        winerror.ERROR_CALL_NOT_IMPLEMENTED: errno.ENOSYS,
        winerror.ERROR_CANNOT_MAKE: errno.EACCES,
        winerror.ERROR_CANTOPEN: errno.EIO,
        winerror.ERROR_CANTREAD: errno.EIO,
        winerror.ERROR_CANTWRITE: errno.EIO,
        winerror.ERROR_CRC: errno.EIO,
        winerror.ERROR_CURRENT_DIRECTORY: errno.EACCES,
        winerror.ERROR_DEVICE_IN_USE: errno.EBUSY,
        winerror.ERROR_DEV_NOT_EXIST: errno.ENODEV,
        winerror.ERROR_DIRECTORY: errno.EINVAL,
        winerror.ERROR_DIR_NOT_EMPTY: errno.ENOTEMPTY,
        winerror.ERROR_DISK_CHANGE: errno.EIO,
        winerror.ERROR_DISK_FULL: errno.ENOSPC,
        winerror.ERROR_DRIVE_LOCKED: errno.EBUSY,
        winerror.ERROR_ENVVAR_NOT_FOUND: errno.EINVAL,
        winerror.ERROR_EXE_MARKED_INVALID: errno.ENOEXEC,
        winerror.ERROR_FILENAME_EXCED_RANGE: errno.ENAMETOOLONG,
        winerror.ERROR_FILE_EXISTS: errno.EEXIST,
        winerror.ERROR_FILE_INVALID: errno.ENODEV,
        winerror.ERROR_FILE_NOT_FOUND: errno.ENOENT,
        winerror.ERROR_GEN_FAILURE: errno.EIO,
        winerror.ERROR_HANDLE_DISK_FULL: errno.ENOSPC,
        winerror.ERROR_INSUFFICIENT_BUFFER: errno.ENOMEM,
        winerror.ERROR_INVALID_ACCESS: errno.EACCES,
        winerror.ERROR_INVALID_ADDRESS: errno.EFAULT,
        winerror.ERROR_INVALID_BLOCK: errno.EFAULT,
        winerror.ERROR_INVALID_DATA: errno.EINVAL,
        winerror.ERROR_INVALID_DRIVE: errno.ENODEV,
        winerror.ERROR_INVALID_EXE_SIGNATURE: errno.ENOEXEC,
        winerror.ERROR_INVALID_FLAGS: errno.EINVAL,
        winerror.ERROR_INVALID_FUNCTION: errno.ENOSYS,
        winerror.ERROR_INVALID_HANDLE: errno.EBADF,
        winerror.ERROR_INVALID_LOGON_HOURS: errno.EACCES,
        winerror.ERROR_INVALID_NAME: errno.EINVAL,
        winerror.ERROR_INVALID_OWNER: errno.EINVAL,
        winerror.ERROR_INVALID_PARAMETER: errno.EINVAL,
        winerror.ERROR_INVALID_PASSWORD: errno.EPERM,
        winerror.ERROR_INVALID_PRIMARY_GROUP: errno.EINVAL,
        winerror.ERROR_INVALID_SIGNAL_NUMBER: errno.EINVAL,
        winerror.ERROR_INVALID_TARGET_HANDLE: errno.EIO,
        winerror.ERROR_INVALID_WORKSTATION: errno.EACCES,
        winerror.ERROR_IO_DEVICE: errno.EIO,
        winerror.ERROR_IO_INCOMPLETE: errno.EINTR,
        winerror.ERROR_LOCKED: errno.EBUSY,
        winerror.ERROR_LOCK_VIOLATION: errno.EACCES,
        winerror.ERROR_LOGON_FAILURE: errno.EACCES,
        winerror.ERROR_MAPPED_ALIGNMENT: errno.EINVAL,
        winerror.ERROR_META_EXPANSION_TOO_LONG: errno.E2BIG,
        winerror.ERROR_MORE_DATA: errno.EPIPE,
        winerror.ERROR_NEGATIVE_SEEK: errno.ESPIPE,
        winerror.ERROR_NOACCESS: errno.EFAULT,
        winerror.ERROR_NONE_MAPPED: errno.EINVAL,
        winerror.ERROR_NOT_ENOUGH_MEMORY: errno.ENOMEM,
        winerror.ERROR_NOT_READY: errno.EAGAIN,
        winerror.ERROR_NOT_SAME_DEVICE: errno.EXDEV,
        winerror.ERROR_NO_DATA: errno.EPIPE,
        winerror.ERROR_NO_MORE_SEARCH_HANDLES: errno.EIO,
        winerror.ERROR_NO_PROC_SLOTS: errno.EAGAIN,
        winerror.ERROR_NO_SUCH_PRIVILEGE: errno.EACCES,
        winerror.ERROR_OPEN_FAILED: errno.EIO,
        winerror.ERROR_OPEN_FILES: errno.EBUSY,
        winerror.ERROR_OPERATION_ABORTED: errno.EINTR,
        winerror.ERROR_OUTOFMEMORY: errno.ENOMEM,
        winerror.ERROR_PASSWORD_EXPIRED: errno.EACCES,
        winerror.ERROR_PATH_BUSY: errno.EBUSY,
        winerror.ERROR_PATH_NOT_FOUND: errno.ENOENT,
        winerror.ERROR_PIPE_BUSY: errno.EBUSY,
        winerror.ERROR_PIPE_CONNECTED: errno.EPIPE,
        winerror.ERROR_PIPE_LISTENING: errno.EPIPE,
        winerror.ERROR_PIPE_NOT_CONNECTED: errno.EPIPE,
        winerror.ERROR_PRIVILEGE_NOT_HELD: errno.EACCES,
        winerror.ERROR_READ_FAULT: errno.EIO,
        winerror.ERROR_SEEK: errno.EIO,
        winerror.ERROR_SEEK_ON_DEVICE: errno.ESPIPE,
        winerror.ERROR_SHARING_BUFFER_EXCEEDED: errno.ENFILE,
        winerror.ERROR_SHARING_VIOLATION: errno.EACCES,
        winerror.ERROR_STACK_OVERFLOW: errno.ENOMEM,
        winerror.ERROR_SWAPERROR: errno.ENOENT,
        winerror.ERROR_TOO_MANY_MODULES: errno.EMFILE,
        winerror.ERROR_TOO_MANY_OPEN_FILES: errno.EMFILE,
        winerror.ERROR_UNRECOGNIZED_MEDIA: errno.ENXIO,
        winerror.ERROR_UNRECOGNIZED_VOLUME: errno.ENODEV,
        winerror.ERROR_WAIT_NO_CHILDREN: errno.ECHILD,
        winerror.ERROR_WRITE_FAULT: errno.EIO,
        winerror.ERROR_WRITE_PROTECT: errno.EROFS,
        }

    def __init__(self, err):
        try:
            # unpack a pywintypes.error tuple
            self.win_errno, self.win_function, self.win_strerror = err
        except ValueError:
            # get attributes from a WindowsError
            self.win_errno = err.winerror
            self.win_function = None
            self.win_strerror = err.strerror
        self.win_strerror = self.win_strerror.rstrip('.')

class WinIOError(WinError, IOError):
    def __init__(self, err, filename=None):
        WinError.__init__(self, err)
        IOError.__init__(self, self.winerror_map.get(self.win_errno, 0),
                         self.win_strerror)
        self.filename = filename

class WinOSError(WinError, OSError):
    def __init__(self, err):
        WinError.__init__(self, err)
        OSError.__init__(self, self.winerror_map.get(self.win_errno, 0),
                         self.win_strerror)

def os_link(src, dst):
    try:
        win32file.CreateHardLink(dst, src)
        # CreateHardLink sometimes succeeds on mapped drives but
        # following nlinks() returns 1. Check it now and bail out.
        if nlinks(src) < 2:
            try:
                win32file.DeleteFile(dst)
            except:
                pass
            # Fake hardlinking error
            raise WinOSError((18, 'CreateHardLink', 'The system cannot '
                              'move the file to a different disk drive'))
    except pywintypes.error, details:
        raise WinOSError(details)
    except NotImplementedError: # Another fake error win Win98
        raise WinOSError((18, 'CreateHardLink', 'Hardlinking not supported'))

def nlinks(pathname):
    """Return number of hardlinks for the given file."""
    try:
        fh = win32file.CreateFile(pathname,
            win32file.GENERIC_READ, win32file.FILE_SHARE_READ,
            None, win32file.OPEN_EXISTING, 0, None)
        res = win32file.GetFileInformationByHandle(fh)
        fh.Close()
        return res[7]
    except pywintypes.error:
        return os.lstat(pathname).st_nlink

def testpid(pid):
    '''return True if pid is still running or unable to
    determine, False otherwise'''
    try:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION, False, pid)
        if handle:
            status = win32process.GetExitCodeProcess(handle)
            return status == win32con.STILL_ACTIVE
    except pywintypes.error, details:
        return details[0] != winerror.ERROR_INVALID_PARAMETER
    return True

def lookup_reg(key, valname=None, scope=None):
    ''' Look up a key/value name in the Windows registry.

    valname: value name. If unspecified, the default value for the key
    is used.
    scope: optionally specify scope for registry lookup, this can be
    a sequence of scopes to look up in order. Default (CURRENT_USER,
    LOCAL_MACHINE).
    '''
    try:
        from _winreg import HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, \
            QueryValueEx, OpenKey
    except ImportError:
        return None

    if scope is None:
        scope = (HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE)
    elif not isinstance(scope, (list, tuple)):
        scope = (scope,)
    for s in scope:
        try:
            val = QueryValueEx(OpenKey(s, key), valname)[0]
            # never let a Unicode string escape into the wild
            return encoding.tolocal(val.encode('UTF-8'))
        except EnvironmentError:
            pass

def system_rcpath_win32():
    '''return default os-specific hgrc search path'''
    proc = win32api.GetCurrentProcess()
    try:
        # This will fail on windows < NT
        filename = win32process.GetModuleFileNameEx(proc, 0)
    except:
        filename = win32api.GetModuleFileName(0)
    # Use mercurial.ini found in directory with hg.exe
    progrc = os.path.join(os.path.dirname(filename), 'mercurial.ini')
    if os.path.isfile(progrc):
        return [progrc]
    # else look for a system rcpath in the registry
    try:
        value = win32api.RegQueryValue(
                win32con.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Mercurial')
        rcpath = []
        for p in value.split(os.pathsep):
            if p.lower().endswith('mercurial.ini'):
                rcpath.append(p)
            elif os.path.isdir(p):
                for f, kind in osutil.listdir(p):
                    if f.endswith('.rc'):
                        rcpath.append(os.path.join(p, f))
        return rcpath
    except pywintypes.error:
        return []

def user_rcpath_win32():
    '''return os-specific hgrc search path to the user dir'''
    userdir = os.path.expanduser('~')
    if sys.getwindowsversion()[3] != 2 and userdir == '~':
        # We are on win < nt: fetch the APPDATA directory location and use
        # the parent directory as the user home dir.
        appdir = shell.SHGetPathFromIDList(
            shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_APPDATA))
        userdir = os.path.dirname(appdir)
    return [os.path.join(userdir, 'mercurial.ini'),
            os.path.join(userdir, '.hgrc')]

def getuser():
    '''return name of current user'''
    return win32api.GetUserName()

def set_signal_handler_win32():
    """Register a termination handler for console events including
    CTRL+C. python signal handlers do not work well with socket
    operations.
    """
    def handler(event):
        win32process.ExitProcess(1)
    win32api.SetConsoleCtrlHandler(handler)

