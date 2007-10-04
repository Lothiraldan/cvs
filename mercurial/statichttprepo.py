# statichttprepo.py - simple http repository class for mercurial
#
# This provides read-only repo access to repositories exported via static http
#
# Copyright 2005-2007 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from i18n import _
import changelog, filelog, httprangereader
import repo, localrepo, manifest, os, urllib, urllib2, util

class rangereader(httprangereader.httprangereader):
    def read(self, size=None):
        try:
            return httprangereader.httprangereader.read(self, size)
        except urllib2.HTTPError, inst:
            raise IOError(None, inst)
        except urllib2.URLError, inst:
            raise IOError(None, inst.reason[1])

def opener(base):
    """return a function that opens files over http"""
    p = base
    def o(path, mode="r"):
        f = "/".join((p, urllib.quote(path)))
        return rangereader(f)
    return o

class statichttprepository(localrepo.localrepository):
    def __init__(self, ui, path):
        self._url = path
        self.ui = ui

        self.path = path.rstrip('/') + "/.hg"
        self.opener = opener(self.path)
        # find requirements
        try:
            requirements = self.opener("requires").read().splitlines()
        except IOError:
            requirements = []
        # check them
        for r in requirements:
            if r not in self.supported:
                raise repo.RepoError(_("requirement '%s' not supported") % r)

        # setup store
        if "store" in requirements:
            self.encodefn = util.encodefilename
            self.decodefn = util.decodefilename
            self.spath = self.path + "/store"
        else:
            self.encodefn = lambda x: x
            self.decodefn = lambda x: x
            self.spath = self.path
        self.sopener = util.encodedopener(opener(self.spath), self.encodefn)

        self.manifest = manifest.manifest(self.sopener)
        self.changelog = changelog.changelog(self.sopener)
        self.tagscache = None
        self.nodetagscache = None
        self.encodepats = None
        self.decodepats = None

    def url(self):
        return 'static-' + self._url

    def dev(self):
        return -1

    def local(self):
        return False

def instance(ui, path, create):
    if create:
        raise util.Abort(_('cannot create new static-http repository'))
    if path.startswith('old-http:'):
        ui.warn(_("old-http:// syntax is deprecated, "
                  "please use static-http:// instead\n"))
        path = path[4:]
    else:
        path = path[7:]
    return statichttprepository(ui, path)
