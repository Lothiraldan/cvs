# archival.py - revision archival for mercurial
#
# Copyright 2006 Vadim Gelfer <vadim.gelfer@gmail.com>
#
# This software may be used and distributed according to the terms of
# the GNU General Public License, incorporated herein by reference.

from demandload import *
from i18n import gettext as _
from node import *
demandload(globals(), 'cStringIO os stat tarfile time util zipfile')

def tidyprefix(dest, prefix, suffixes):
    '''choose prefix to use for names in archive.  make sure prefix is
    safe for consumers.'''

    if prefix:
        prefix = prefix.replace('\\', '/')
    else:
        if not isinstance(dest, str):
            raise ValueError('dest must be string if no prefix')
        prefix = os.path.basename(dest)
        lower = prefix.lower()
        for sfx in suffixes:
            if lower.endswith(sfx):
                prefix = prefix[:-len(sfx)]
                break
    lpfx = os.path.normpath(util.localpath(prefix))
    prefix = util.pconvert(lpfx)
    if not prefix.endswith('/'):
        prefix += '/'
    if prefix.startswith('../') or os.path.isabs(lpfx) or '/../' in prefix:
        raise util.Abort(_('archive prefix contains illegal components'))
    return prefix

class tarit:
    '''write archive to tar file or stream.  can write uncompressed,
    or compress with gzip or bzip2.'''

    def __init__(self, dest, prefix, kind=''):
        self.prefix = tidyprefix(dest, prefix, ['.tar', '.tar.bz2', '.tar.gz',
                                                '.tgz', 'tbz2'])
        self.mtime = int(time.time())
        if isinstance(dest, str):
            self.z = tarfile.open(dest, mode='w:'+kind)
        else:
            self.z = tarfile.open(mode='w|'+kind, fileobj=dest)

    def addfile(self, name, mode, data):
        i = tarfile.TarInfo(self.prefix + name)
        i.mtime = self.mtime
        i.size = len(data)
        i.mode = mode
        self.z.addfile(i, cStringIO.StringIO(data))

    def done(self):
        self.z.close()

class tellable:
    '''provide tell method for zipfile.ZipFile when writing to http
    response file object.'''

    def __init__(self, fp):
        self.fp = fp
        self.offset = 0

    def __getattr__(self, key):
        return getattr(self.fp, key)

    def write(self, s):
        self.fp.write(s)
        self.offset += len(s)

    def tell(self):
        return self.offset

class zipit:
    '''write archive to zip file or stream.  can write uncompressed,
    or compressed with deflate.'''

    def __init__(self, dest, prefix, compress=True):
        self.prefix = tidyprefix(dest, prefix, ('.zip',))
        if not isinstance(dest, str):
            try:
                dest.tell()
            except (AttributeError, IOError):
                dest = tellable(dest)
        self.z = zipfile.ZipFile(dest, 'w',
                                 compress and zipfile.ZIP_DEFLATED or
                                 zipfile.ZIP_STORED)
        self.date_time = time.gmtime(time.time())[:6]

    def addfile(self, name, mode, data):
        i = zipfile.ZipInfo(self.prefix + name, self.date_time)
        i.compress_type = self.z.compression
        i.flag_bits = 0x08
        # unzip will not honor unix file modes unless file creator is
        # set to unix (id 3).
        i.create_system = 3
        i.external_attr = (mode | stat.S_IFREG) << 16L
        self.z.writestr(i, data)

    def done(self):
        self.z.close()

class fileit:
    '''write archive as files in directory.'''

    def __init__(self, name, prefix):
        if prefix:
            raise util.Abort(_('cannot give prefix when archiving to files'))
        self.basedir = name
        self.dirs = {}
        self.oflags = (os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                       getattr(os, 'O_BINARY', 0) |
                       getattr(os, 'O_NOFOLLOW', 0))

    def addfile(self, name, mode, data):
        destfile = os.path.join(self.basedir, name)
        destdir = os.path.dirname(destfile)
        if destdir not in self.dirs:
            if not os.path.isdir(destdir):
                os.makedirs(destdir)
            self.dirs[destdir] = 1
        os.fdopen(os.open(destfile, self.oflags, mode), 'wb').write(data)

    def done(self):
        pass

archivers = {
    'files': fileit,
    'tar': tarit,
    'tbz2': lambda name, prefix: tarit(name, prefix, 'bz2'),
    'tgz': lambda name, prefix: tarit(name, prefix, 'gz'),
    'uzip': lambda name, prefix: zipit(name, prefix, False),
    'zip': zipit,
    }

def archive(repo, dest, node, kind, decode=True, matchfn=None,
            prefix=None):
    '''create archive of repo as it was at node.

    dest can be name of directory, name of archive file, or file
    object to write archive to.

    kind is type of archive to create.

    decode tells whether to put files through decode filters from
    hgrc.

    matchfn is function to filter names of files to write to archive.

    prefix is name of path to put before every archive member.'''

    def write(name, mode, data):
        if matchfn and not matchfn(name): return
        if decode:
            fp = cStringIO.StringIO()
            repo.wwrite(None, data, fp)
            data = fp.getvalue()
        archiver.addfile(name, mode, data)

    archiver = archivers[kind](dest, prefix)
    mn = repo.changelog.read(node)[0]
    mf = repo.manifest.read(mn).items()
    mff = repo.manifest.readflags(mn)
    mf.sort()
    write('.hg_archival.txt', 0644,
          'repo: %s\nnode: %s\n' % (hex(repo.changelog.node(0)), hex(node)))
    for filename, filenode in mf:
        write(filename, mff[filename] and 0755 or 0644,
              repo.file(filename).read(filenode))
    archiver.done()
