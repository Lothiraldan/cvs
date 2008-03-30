#
# Copyright 21 May 2005 - (c) 2005 Jake Edge <jake@edge2.net>
# Copyright 2005-2007 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

import os, mimetypes, re
import webutil
from mercurial import revlog, archival
from mercurial.node import hex, nullid
from mercurial.util import binary
from mercurial.repo import RepoError
from common import paritygen, staticfile, get_contact, ErrorResponse
from common import HTTP_OK, HTTP_NOT_FOUND

# __all__ is populated with the allowed commands. Be sure to add to it if
# you're adding a new command, or the new command won't work.

__all__ = [
   'log', 'rawfile', 'file', 'changelog', 'shortlog', 'changeset', 'rev',
   'manifest', 'tags', 'summary', 'filediff', 'diff', 'annotate', 'filelog',
   'archive', 'static',
]

def log(web, req, tmpl):
    if 'file' in req.form and req.form['file'][0]:
        return filelog(web, req, tmpl)
    else:
        return changelog(web, req, tmpl)

def rawfile(web, req, tmpl):
    path = webutil.cleanpath(web.repo, req.form.get('file', [''])[0])
    if not path:
        content = manifest(web, req, tmpl)
        req.respond(HTTP_OK, web.ctype)
        return content

    try:
        fctx = webutil.filectx(web.repo, req)
    except revlog.LookupError, inst:
        try:
            content = manifest(web, req, tmpl)
            req.respond(HTTP_OK, web.ctype)
            return content
        except ErrorResponse:
            raise inst

    path = fctx.path()
    text = fctx.data()
    mt = mimetypes.guess_type(path)[0]
    if mt is None or binary(text):
        mt = mt or 'application/octet-stream'

    req.respond(HTTP_OK, mt, path, len(text))
    return [text]

def _filerevision(web, tmpl, fctx):
    f = fctx.path()
    text = fctx.data()
    fl = fctx.filelog()
    n = fctx.filenode()
    parity = paritygen(web.stripecount)

    if binary(text):
        mt = mimetypes.guess_type(f)[0] or 'application/octet-stream'
        text = '(binary:%s)' % mt

    def lines():
        for lineno, t in enumerate(text.splitlines(1)):
            yield {"line": t,
                   "lineid": "l%d" % (lineno + 1),
                   "linenumber": "% 6d" % (lineno + 1),
                   "parity": parity.next()}

    return tmpl("filerevision",
                file=f,
                path=webutil.up(f),
                text=lines(),
                rev=fctx.rev(),
                node=hex(fctx.node()),
                author=fctx.user(),
                date=fctx.date(),
                desc=fctx.description(),
                branch=webutil.nodebranchnodefault(fctx),
                parent=webutil.siblings(fctx.parents()),
                child=webutil.siblings(fctx.children()),
                rename=webutil.renamelink(fl, n),
                permissions=fctx.manifest().flags(f))

def file(web, req, tmpl):
    path = webutil.cleanpath(web.repo, req.form.get('file', [''])[0])
    if path:
        try:
            return _filerevision(web, tmpl, webutil.filectx(web.repo, req))
        except revlog.LookupError, inst:
            pass

    try:
        return manifest(web, req, tmpl)
    except ErrorResponse:
        raise inst

def _search(web, tmpl, query):

    def changelist(**map):
        cl = web.repo.changelog
        count = 0
        qw = query.lower().split()

        def revgen():
            for i in xrange(cl.count() - 1, 0, -100):
                l = []
                for j in xrange(max(0, i - 100), i + 1):
                    ctx = web.repo.changectx(j)
                    l.append(ctx)
                l.reverse()
                for e in l:
                    yield e

        for ctx in revgen():
            miss = 0
            for q in qw:
                if not (q in ctx.user().lower() or
                        q in ctx.description().lower() or
                        q in " ".join(ctx.files()).lower()):
                    miss = 1
                    break
            if miss:
                continue

            count = 1
            n = ctx.node()
            showtags = webutil.showtag(web.repo, tmpl, 'changelogtag', n)

            yield tmpl('searchentry',
                       parity=parity.next(),
                       author=ctx.user(),
                       parent=webutil.siblings(ctx.parents()),
                       child=webutil.siblings(ctx.children()),
                       changelogtag=showtags,
                       desc=ctx.description(),
                       date=ctx.date(),
                       files=web.listfilediffs(tmpl, ctx.files(), n),
                       rev=ctx.rev(),
                       node=hex(n),
                       tags=webutil.nodetagsdict(web.repo, n),
                       inbranch=webutil.nodeinbranch(web.repo, ctx),
                       branches=webutil.nodebranchdict(web.repo, ctx))

            if count >= web.maxchanges:
                break

    cl = web.repo.changelog
    parity = paritygen(web.stripecount)

    return tmpl('search',
                query=query,
                node=hex(cl.tip()),
                entries=changelist,
                archives=web.archivelist("tip"))

def changelog(web, req, tmpl, shortlog = False):
    if 'node' in req.form:
        ctx = webutil.changectx(web.repo, req)
    else:
        if 'rev' in req.form:
            hi = req.form['rev'][0]
        else:
            hi = web.repo.changelog.count() - 1
        try:
            ctx = web.repo.changectx(hi)
        except RepoError:
            return _search(web, tmpl, hi) # XXX redirect to 404 page?

    def changelist(limit=0, **map):
        cl = web.repo.changelog
        l = [] # build a list in forward order for efficiency
        for i in xrange(start, end):
            ctx = web.repo.changectx(i)
            n = ctx.node()
            showtags = webutil.showtag(web.repo, tmpl, 'changelogtag', n)

            l.insert(0, {"parity": parity.next(),
                         "author": ctx.user(),
                         "parent": webutil.siblings(ctx.parents(), i - 1),
                         "child": webutil.siblings(ctx.children(), i + 1),
                         "changelogtag": showtags,
                         "desc": ctx.description(),
                         "date": ctx.date(),
                         "files": web.listfilediffs(tmpl, ctx.files(), n),
                         "rev": i,
                         "node": hex(n),
                         "tags": webutil.nodetagsdict(web.repo, n),
                         "inbranch": webutil.nodeinbranch(web.repo, ctx),
                         "branches": webutil.nodebranchdict(web.repo, ctx)
                        })

        if limit > 0:
            l = l[:limit]

        for e in l:
            yield e

    maxchanges = shortlog and web.maxshortchanges or web.maxchanges
    cl = web.repo.changelog
    count = cl.count()
    pos = ctx.rev()
    start = max(0, pos - maxchanges + 1)
    end = min(count, start + maxchanges)
    pos = end - 1
    parity = paritygen(web.stripecount, offset=start-end)

    changenav = webutil.revnavgen(pos, maxchanges, count, web.repo.changectx)

    return tmpl(shortlog and 'shortlog' or 'changelog',
                changenav=changenav,
                node=hex(cl.tip()),
                rev=pos, changesets=count,
                entries=lambda **x: changelist(limit=0,**x),
                latestentry=lambda **x: changelist(limit=1,**x),
                archives=web.archivelist("tip"))

def shortlog(web, req, tmpl):
    return changelog(web, req, tmpl, shortlog = True)

def changeset(web, req, tmpl):
    ctx = webutil.changectx(web.repo, req)
    n = ctx.node()
    showtags = webutil.showtag(web.repo, tmpl, 'changesettag', n)
    parents = ctx.parents()
    p1 = parents[0].node()

    files = []
    parity = paritygen(web.stripecount)
    for f in ctx.files():
        files.append(tmpl("filenodelink",
                          node=hex(n), file=f,
                          parity=parity.next()))

    diffs = web.diff(tmpl, p1, n, None)
    return tmpl('changeset',
                diff=diffs,
                rev=ctx.rev(),
                node=hex(n),
                parent=webutil.siblings(parents),
                child=webutil.siblings(ctx.children()),
                changesettag=showtags,
                author=ctx.user(),
                desc=ctx.description(),
                date=ctx.date(),
                files=files,
                archives=web.archivelist(hex(n)),
                tags=webutil.nodetagsdict(web.repo, n),
                branch=webutil.nodebranchnodefault(ctx),
                inbranch=webutil.nodeinbranch(web.repo, ctx),
                branches=webutil.nodebranchdict(web.repo, ctx))

rev = changeset

def manifest(web, req, tmpl):
    ctx = webutil.changectx(web.repo, req)
    path = webutil.cleanpath(web.repo, req.form.get('file', [''])[0])
    mf = ctx.manifest()
    node = ctx.node()

    files = {}
    parity = paritygen(web.stripecount)

    if path and path[-1] != "/":
        path += "/"
    l = len(path)
    abspath = "/" + path

    for f, n in mf.items():
        if f[:l] != path:
            continue
        remain = f[l:]
        if "/" in remain:
            short = remain[:remain.index("/") + 1] # bleah
            files[short] = (f, None)
        else:
            short = os.path.basename(remain)
            files[short] = (f, n)

    if not files:
        raise ErrorResponse(HTTP_NOT_FOUND, 'path not found: ' + path)

    def filelist(**map):
        fl = files.keys()
        fl.sort()
        for f in fl:
            full, fnode = files[f]
            if not fnode:
                continue

            fctx = ctx.filectx(full)
            yield {"file": full,
                   "parity": parity.next(),
                   "basename": f,
                   "date": fctx.changectx().date(),
                   "size": fctx.size(),
                   "permissions": mf.flags(full)}

    def dirlist(**map):
        fl = files.keys()
        fl.sort()
        for f in fl:
            full, fnode = files[f]
            if fnode:
                continue

            yield {"parity": parity.next(),
                   "path": "%s%s" % (abspath, f),
                   "basename": f[:-1]}

    return tmpl("manifest",
                rev=ctx.rev(),
                node=hex(node),
                path=abspath,
                up=webutil.up(abspath),
                upparity=parity.next(),
                fentries=filelist,
                dentries=dirlist,
                archives=web.archivelist(hex(node)),
                tags=webutil.nodetagsdict(web.repo, node),
                inbranch=webutil.nodeinbranch(web.repo, ctx),
                branches=webutil.nodebranchdict(web.repo, ctx))

def tags(web, req, tmpl):
    i = web.repo.tagslist()
    i.reverse()
    parity = paritygen(web.stripecount)

    def entries(notip=False,limit=0, **map):
        count = 0
        for k, n in i:
            if notip and k == "tip":
                continue
            if limit > 0 and count >= limit:
                continue
            count = count + 1
            yield {"parity": parity.next(),
                   "tag": k,
                   "date": web.repo.changectx(n).date(),
                   "node": hex(n)}

    return tmpl("tags",
                node=hex(web.repo.changelog.tip()),
                entries=lambda **x: entries(False,0, **x),
                entriesnotip=lambda **x: entries(True,0, **x),
                latestentry=lambda **x: entries(True,1, **x))

def summary(web, req, tmpl):
    i = web.repo.tagslist()
    i.reverse()

    def tagentries(**map):
        parity = paritygen(web.stripecount)
        count = 0
        for k, n in i:
            if k == "tip": # skip tip
                continue

            count = 1
            if count > 10: # limit to 10 tags
                break

            yield tmpl("tagentry",
                       parity=parity.next(),
                       tag=k,
                       node=hex(n),
                       date=web.repo.changectx(n).date())

    def branches(**map):
        parity = paritygen(web.stripecount)

        b = web.repo.branchtags()
        l = [(-web.repo.changelog.rev(n), n, t) for t, n in b.items()]
        l.sort()

        for r,n,t in l:
            ctx = web.repo.changectx(n)
            yield {'parity': parity.next(),
                   'branch': t,
                   'node': hex(n),
                   'date': ctx.date()}

    def changelist(**map):
        parity = paritygen(web.stripecount, offset=start-end)
        l = [] # build a list in forward order for efficiency
        for i in xrange(start, end):
            ctx = web.repo.changectx(i)
            n = ctx.node()
            hn = hex(n)

            l.insert(0, tmpl(
               'shortlogentry',
                parity=parity.next(),
                author=ctx.user(),
                desc=ctx.description(),
                date=ctx.date(),
                rev=i,
                node=hn,
                tags=webutil.nodetagsdict(web.repo, n),
                inbranch=webutil.nodeinbranch(web.repo, ctx),
                branches=webutil.nodebranchdict(web.repo, ctx)))

        yield l

    cl = web.repo.changelog
    count = cl.count()
    start = max(0, count - web.maxchanges)
    end = min(count, start + web.maxchanges)

    return tmpl("summary",
                desc=web.config("web", "description", "unknown"),
                owner=get_contact(web.config) or "unknown",
                lastchange=cl.read(cl.tip())[2],
                tags=tagentries,
                branches=branches,
                shortlog=changelist,
                node=hex(cl.tip()),
                archives=web.archivelist("tip"))

def filediff(web, req, tmpl):
    fctx = webutil.filectx(web.repo, req)
    n = fctx.node()
    path = fctx.path()
    parents = fctx.parents()
    p1 = parents and parents[0].node() or nullid

    diffs = web.diff(tmpl, p1, n, [path])
    return tmpl("filediff",
                file=path,
                node=hex(n),
                rev=fctx.rev(),
                branch=webutil.nodebranchnodefault(fctx),
                parent=webutil.siblings(parents),
                child=webutil.siblings(fctx.children()),
                diff=diffs)

diff = filediff

def annotate(web, req, tmpl):
    fctx = webutil.filectx(web.repo, req)
    f = fctx.path()
    n = fctx.filenode()
    fl = fctx.filelog()
    parity = paritygen(web.stripecount)

    def annotate(**map):
        last = None
        if binary(fctx.data()):
            mt = (mimetypes.guess_type(fctx.path())[0]
                  or 'application/octet-stream')
            lines = enumerate([((fctx.filectx(fctx.filerev()), 1),
                                '(binary:%s)' % mt)])
        else:
            lines = enumerate(fctx.annotate(follow=True, linenumber=True))
        for lineno, ((f, targetline), l) in lines:
            fnode = f.filenode()
            name = web.repo.ui.shortuser(f.user())

            if last != fnode:
                last = fnode

            yield {"parity": parity.next(),
                   "node": hex(f.node()),
                   "rev": f.rev(),
                   "author": name,
                   "file": f.path(),
                   "targetline": targetline,
                   "line": l,
                   "lineid": "l%d" % (lineno + 1),
                   "linenumber": "% 6d" % (lineno + 1)}

    return tmpl("fileannotate",
                file=f,
                annotate=annotate,
                path=webutil.up(f),
                rev=fctx.rev(),
                node=hex(fctx.node()),
                author=fctx.user(),
                date=fctx.date(),
                desc=fctx.description(),
                rename=webutil.renamelink(fl, n),
                branch=webutil.nodebranchnodefault(fctx),
                parent=webutil.siblings(fctx.parents()),
                child=webutil.siblings(fctx.children()),
                permissions=fctx.manifest().flags(f))

def filelog(web, req, tmpl):
    fctx = webutil.filectx(web.repo, req)
    f = fctx.path()
    fl = fctx.filelog()
    count = fl.count()
    pagelen = web.maxshortchanges
    pos = fctx.filerev()
    start = max(0, pos - pagelen + 1)
    end = min(count, start + pagelen)
    pos = end - 1
    parity = paritygen(web.stripecount, offset=start-end)

    def entries(limit=0, **map):
        l = []

        for i in xrange(start, end):
            ctx = fctx.filectx(i)
            n = fl.node(i)

            l.insert(0, {"parity": parity.next(),
                         "filerev": i,
                         "file": f,
                         "node": hex(ctx.node()),
                         "author": ctx.user(),
                         "date": ctx.date(),
                         "rename": webutil.renamelink(fl, n),
                         "parent": webutil.siblings(fctx.parents()),
                         "child": webutil.siblings(fctx.children()),
                         "desc": ctx.description()})

        if limit > 0:
            l = l[:limit]

        for e in l:
            yield e

    nodefunc = lambda x: fctx.filectx(fileid=x)
    nav = webutil.revnavgen(pos, pagelen, count, nodefunc)
    return tmpl("filelog", file=f, node=hex(fctx.node()), nav=nav,
                entries=lambda **x: entries(limit=0, **x),
                latestentry=lambda **x: entries(limit=1, **x))


def archive(web, req, tmpl):
    type_ = req.form['type'][0]
    allowed = web.configlist("web", "allow_archive")
    key = req.form['node'][0]

    if not (type_ in web.archives and (type_ in allowed or
        web.configbool("web", "allow" + type_, False))):
        msg = 'Unsupported archive type: %s' % type_
        raise ErrorResponse(HTTP_NOT_FOUND, msg)

    reponame = re.sub(r"\W+", "-", os.path.basename(web.reponame))
    cnode = web.repo.lookup(key)
    arch_version = key
    if cnode == key or key == 'tip':
        arch_version = short(cnode)
    name = "%s-%s" % (reponame, arch_version)
    mimetype, artype, extension, encoding = web.archive_specs[type_]
    headers = [
        ('Content-Type', mimetype),
        ('Content-Disposition', 'attachment; filename=%s%s' % (name, extension))
    ]
    if encoding:
        headers.append(('Content-Encoding', encoding))
    req.header(headers)
    req.respond(HTTP_OK)
    archival.archive(web.repo, req, cnode, artype, prefix=name)
    return []


def static(web, req, tmpl):
    fname = req.form['file'][0]
    # a repo owner may set web.static in .hg/hgrc to get any file
    # readable by the user running the CGI script
    static = web.config("web", "static",
                        os.path.join(web.templatepath, "static"),
                        untrusted=False)
    return [staticfile(static, fname, req)]
