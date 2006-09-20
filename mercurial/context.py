# context.py - changeset and file context objects for mercurial
#
# Copyright 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

class changectx(object):
    """A changecontext object makes access to data related to a particular
    changeset convenient."""
    def __init__(self, repo, changeid=None):
        """changeid is a revision number, node, or tag"""
        self._repo = repo

        if not changeid:
            p1, p2 = self._repo.dirstate.parents()
            self._rev = self._repo.changelog.rev(p1)
            if self._rev == -1:
                changeid = 'tip'
            else:
                self._node = p1
                return

        self._node = self._repo.lookup(changeid)
        self._rev = self._repo.changelog.rev(self._node)

    def changeset(self):
        try:
            return self._changeset
        except AttributeError:
            self._changeset = self._repo.changelog.read(self.node())
            return self._changeset

    def manifest(self):
        try:
            return self._manifest
        except AttributeError:
            self._manifest = self._repo.manifest.read(self.changeset()[0])
            return self._manifest

    def rev(self): return self._rev
    def node(self): return self._node
    def user(self): return self.changeset()[1]
    def date(self): return self.changeset()[2]
    def changedfiles(self): return self.changeset()[3]
    def description(self): return self.changeset()[4]

    def parents(self):
        """return contexts for each parent changeset"""
        p = self._repo.changelog.parents(self._node)
        return [ changectx(self._repo, x) for x in p ]

    def children(self):
        """return contexts for each child changeset"""
        c = self._repo.changelog.children(self._node)
        return [ changectx(self._repo, x) for x in c ]

    def filenode(self, path):
        node, flag = self._repo.manifest.find(self.changeset()[0], path)
        return node

    def filectx(self, path, fileid=None):
        """get a file context from this changeset"""
        if fileid is None:
            fileid = self.filenode(path)
        return filectx(self._repo, path, fileid=fileid)

    def filectxs(self):
        """generate a file context for each file in this changeset's
           manifest"""
        mf = self.manifest()
        m = mf.keys()
        m.sort()
        for f in m:
            yield self.filectx(f, fileid=mf[f])

class filectx(object):
    """A filecontext object makes access to data related to a particular
       filerevision convenient."""
    def __init__(self, repo, path, changeid=None, fileid=None):
        """changeid can be a changeset revision, node, or tag.
           fileid can be a file revision or node."""
        self._repo = repo
        self._path = path

        assert changeid or fileid

        if not fileid:
            # if given a changeset id, go ahead and look up the file
            self._changeid = changeid
            self._changectx = self.changectx()
            self._filelog = self._repo.file(self._path)
            self._filenode = self._changectx.filenode(self._path)
        else:
            # else be lazy
            self._filelog = self._repo.file(self._path)
            self._filenode = self._filelog.lookup(fileid)
            self._changeid = self._filelog.linkrev(self._filenode)
        self._filerev = self._filelog.rev(self._filenode)

    def changectx(self):
        try:
            return self._changectx
        except AttributeError:
            self._changectx = changectx(self._repo, self._changeid)
            return self._changectx

    def filerev(self): return self._filerev
    def filenode(self): return self._filenode
    def filelog(self): return self._filelog

    def rev(self): return self.changectx().rev()
    def node(self): return self.changectx().node()
    def user(self): return self.changectx().user()
    def date(self): return self.changectx().date()
    def files(self): return self.changectx().files()
    def description(self): return self.changectx().description()
    def manifest(self): return self.changectx().manifest()

    def data(self): return self._filelog.read(self._filenode)
    def metadata(self): return self._filelog.readmeta(self._filenode)
    def renamed(self): return self._filelog.renamed(self._filenode)

    def parents(self):
        # need to fix for renames
        p = self._filelog.parents(self._filenode)
        return [ filectx(self._repo, self._path, fileid=x) for x in p ]

    def children(self):
        # hard for renames
        c = self._filelog.children(self._filenode)
        return [ filectx(self._repo, self._path, fileid=x) for x in c ]

    def annotate(self):
        return self._filelog.annotate(self._filenode)
