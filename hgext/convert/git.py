# git support for the convert extension

import os
from mercurial import util

from common import NoRepo, commit, converter_source

class convert_git(converter_source):
    # Windows does not support GIT_DIR= construct while other systems
    # cannot remove environment variable. Just assume none have
    # both issues.
    if hasattr(os, 'unsetenv'):
        def gitcmd(self, s):
            prevgitdir = os.environ.get('GIT_DIR')
            os.environ['GIT_DIR'] = self.path
            try:
                return util.popen(s)
            finally:
                if prevgitdir is None:
                    del os.environ['GIT_DIR']
                else:
                    os.environ['GIT_DIR'] = prevgitdir
    else:
        def gitcmd(self, s):
            return util.popen('GIT_DIR=%s %s' % (self.path, s))

    def __init__(self, ui, path, rev=None):
        super(convert_git, self).__init__(ui, path, rev=rev)

        if os.path.isdir(path + "/.git"):
            path += "/.git"
        if not os.path.exists(path + "/objects"):
            raise NoRepo("%s does not look like a Git repo" % path)
        self.path = path

    def getheads(self):
        if not self.rev:
            return self.gitcmd('git-rev-parse --branches').read().splitlines()
        else:
            fh = self.gitcmd("git-rev-parse --verify %s" % self.rev)
            return [fh.read()[:-1]]

    def catfile(self, rev, type):
        if rev == "0" * 40: raise IOError()
        fh = self.gitcmd("git-cat-file %s %s" % (type, rev))
        return fh.read()

    def getfile(self, name, rev):
        return self.catfile(rev, "blob")

    def getmode(self, name, rev):
        return self.modecache[(name, rev)]

    def getchanges(self, version):
        self.modecache = {}
        fh = self.gitcmd("git-diff-tree --root -m -r %s" % version)
        changes = []
        seen = {}
        for l in fh:
            if "\t" not in l:
                continue
            m, f = l[:-1].split("\t")
            if f in seen:
                continue
            seen[f] = 1
            m = m.split()
            h = m[3]
            p = (m[1] == "100755")
            s = (m[1] == "120000")
            self.modecache[(f, h)] = (p and "x") or (s and "l") or ""
            changes.append((f, h))
        return (changes, {})

    def getcommit(self, version):
        c = self.catfile(version, "commit") # read the commit hash
        end = c.find("\n\n")
        message = c[end+2:]
        message = self.recode(message)
        l = c[:end].splitlines()
        manifest = l[0].split()[1]
        parents = []
        for e in l[1:]:
            n, v = e.split(" ", 1)
            if n == "author":
                p = v.split()
                tm, tz = p[-2:]
                author = " ".join(p[:-2])
                if author[0] == "<": author = author[1:-1]
                author = self.recode(author)
            if n == "committer":
                p = v.split()
                tm, tz = p[-2:]
                committer = " ".join(p[:-2])
                if committer[0] == "<": committer = committer[1:-1]
                committer = self.recode(committer)
                message += "\ncommitter: %s\n" % committer
            if n == "parent": parents.append(v)

        tzs, tzh, tzm = tz[-5:-4] + "1", tz[-4:-2], tz[-2:]
        tz = -int(tzs) * (int(tzh) * 3600 + int(tzm))
        date = tm + " " + str(tz)
        author = author or "unknown"

        c = commit(parents=parents, date=date, author=author, desc=message,
                   rev=version)
        return c

    def gettags(self):
        tags = {}
        fh = self.gitcmd('git-ls-remote --tags "%s"' % self.path)
        prefix = 'refs/tags/'
        for line in fh:
            line = line.strip()
            if not line.endswith("^{}"):
                continue
            node, tag = line.split(None, 1)
            if not tag.startswith(prefix):
                continue
            tag = tag[len(prefix):-3]
            tags[tag] = node

        return tags

    def getchangedfiles(self, version, i):
        changes = []
        if i is None:
            fh = self.gitcmd("git-diff-tree --root -m -r %s" % version)
            for l in fh:
                if "\t" not in l:
                    continue
                m, f = l[:-1].split("\t")
                changes.append(f)
            fh.close()
        else:
            fh = self.gitcmd('git-diff-tree --name-only --root -r %s "%s^%s" --'
                             % (version, version, i+1))
            changes = [f.rstrip('\n') for f in fh]
            fh.close()

        return changes
