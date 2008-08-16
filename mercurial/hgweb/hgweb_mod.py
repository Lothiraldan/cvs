# hgweb/hgweb_mod.py - Web interface for a repository.
#
# Copyright 21 May 2005 - (c) 2005 Jake Edge <jake@edge2.net>
# Copyright 2005-2007 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

import os, mimetypes
from mercurial.node import hex, nullid
from mercurial.repo import RepoError
from mercurial import mdiff, ui, hg, util, patch, hook
from mercurial import revlog, templater, templatefilters
from common import get_mtime, style_map, paritygen, countgen, ErrorResponse
from common import HTTP_OK, HTTP_BAD_REQUEST, HTTP_NOT_FOUND, HTTP_SERVER_ERROR
from request import wsgirequest
import webcommands, protocol, webutil

perms = {
    'changegroup': 'pull',
    'changegroupsubset': 'pull',
    'unbundle': 'push',
    'stream_out': 'pull',
}

class hgweb(object):
    def __init__(self, repo, name=None):
        if isinstance(repo, str):
            parentui = ui.ui(report_untrusted=False, interactive=False)
            self.repo = hg.repository(parentui, repo)
        else:
            self.repo = repo

        hook.redirect(True)
        self.mtime = -1
        self.reponame = name
        self.archives = 'zip', 'gz', 'bz2'
        self.stripecount = 1
        # a repo owner may set web.templates in .hg/hgrc to get any file
        # readable by the user running the CGI script
        self.templatepath = self.config("web", "templates",
                                        templater.templatepath(),
                                        untrusted=False)

    # The CGI scripts are often run by a user different from the repo owner.
    # Trust the settings from the .hg/hgrc files by default.
    def config(self, section, name, default=None, untrusted=True):
        return self.repo.ui.config(section, name, default,
                                   untrusted=untrusted)

    def configbool(self, section, name, default=False, untrusted=True):
        return self.repo.ui.configbool(section, name, default,
                                       untrusted=untrusted)

    def configlist(self, section, name, default=None, untrusted=True):
        return self.repo.ui.configlist(section, name, default,
                                       untrusted=untrusted)

    def refresh(self):
        mtime = get_mtime(self.repo.root)
        if mtime != self.mtime:
            self.mtime = mtime
            self.repo = hg.repository(self.repo.ui, self.repo.root)
            self.maxchanges = int(self.config("web", "maxchanges", 10))
            self.stripecount = int(self.config("web", "stripes", 1))
            self.maxshortchanges = int(self.config("web", "maxshortchanges", 60))
            self.maxfiles = int(self.config("web", "maxfiles", 10))
            self.allowpull = self.configbool("web", "allowpull", True)
            self.encoding = self.config("web", "encoding", util._encoding)

    def run(self):
        if not os.environ.get('GATEWAY_INTERFACE', '').startswith("CGI/1."):
            raise RuntimeError("This function is only intended to be called while running as a CGI script.")
        import mercurial.hgweb.wsgicgi as wsgicgi
        wsgicgi.launch(self)

    def __call__(self, env, respond):
        req = wsgirequest(env, respond)
        return self.run_wsgi(req)

    def run_wsgi(self, req):

        self.refresh()

        # process this if it's a protocol request
        # protocol bits don't need to create any URLs
        # and the clients always use the old URL structure

        cmd = req.form.get('cmd', [''])[0]
        if cmd and cmd in protocol.__all__:
            if cmd in perms and not self.check_perm(req, perms[cmd]):
                return []
            method = getattr(protocol, cmd)
            return method(self.repo, req)

        # work with CGI variables to create coherent structure
        # use SCRIPT_NAME, PATH_INFO and QUERY_STRING as well as our REPO_NAME

        req.url = req.env['SCRIPT_NAME']
        if not req.url.endswith('/'):
            req.url += '/'
        if 'REPO_NAME' in req.env:
            req.url += req.env['REPO_NAME'] + '/'

        if 'PATH_INFO' in req.env:
            parts = req.env['PATH_INFO'].strip('/').split('/')
            repo_parts = req.env.get('REPO_NAME', '').split('/')
            if parts[:len(repo_parts)] == repo_parts:
                parts = parts[len(repo_parts):]
            query = '/'.join(parts)
        else:
            query = req.env['QUERY_STRING'].split('&', 1)[0]
            query = query.split(';', 1)[0]

        # translate user-visible url structure to internal structure

        args = query.split('/', 2)
        if 'cmd' not in req.form and args and args[0]:

            cmd = args.pop(0)
            style = cmd.rfind('-')
            if style != -1:
                req.form['style'] = [cmd[:style]]
                cmd = cmd[style+1:]

            # avoid accepting e.g. style parameter as command
            if hasattr(webcommands, cmd):
                req.form['cmd'] = [cmd]
            else:
                cmd = ''

            if args and args[0]:
                node = args.pop(0)
                req.form['node'] = [node]
            if args:
                req.form['file'] = args

            if cmd == 'static':
                req.form['file'] = req.form['node']
            elif cmd == 'archive':
                fn = req.form['node'][0]
                for type_, spec in self.archive_specs.iteritems():
                    ext = spec[2]
                    if fn.endswith(ext):
                        req.form['node'] = [fn[:-len(ext)]]
                        req.form['type'] = [type_]

        # process the web interface request

        try:

            tmpl = self.templater(req)
            ctype = tmpl('mimetype', encoding=self.encoding)
            ctype = templater.stringify(ctype)

            if cmd == '':
                req.form['cmd'] = [tmpl.cache['default']]
                cmd = req.form['cmd'][0]

            if cmd not in webcommands.__all__:
                msg = 'no such method: %s' % cmd
                raise ErrorResponse(HTTP_BAD_REQUEST, msg)
            elif cmd == 'file' and 'raw' in req.form.get('style', []):
                self.ctype = ctype
                content = webcommands.rawfile(self, req, tmpl)
            else:
                content = getattr(webcommands, cmd)(self, req, tmpl)
                req.respond(HTTP_OK, ctype)

            req.write(content)
            return []

        except revlog.LookupError, err:
            req.respond(HTTP_NOT_FOUND, ctype)
            msg = str(err)
            if 'manifest' not in msg:
                msg = 'revision not found: %s' % err.name
            req.write(tmpl('error', error=msg))
            return []
        except (RepoError, revlog.RevlogError), inst:
            req.respond(HTTP_SERVER_ERROR, ctype)
            req.write(tmpl('error', error=str(inst)))
            return []
        except ErrorResponse, inst:
            req.respond(inst.code, ctype)
            req.write(tmpl('error', error=inst.message))
            return []

    def templater(self, req):

        # determine scheme, port and server name
        # this is needed to create absolute urls

        proto = req.env.get('wsgi.url_scheme')
        if proto == 'https':
            proto = 'https'
            default_port = "443"
        else:
            proto = 'http'
            default_port = "80"

        port = req.env["SERVER_PORT"]
        port = port != default_port and (":" + port) or ""
        urlbase = '%s://%s%s' % (proto, req.env['SERVER_NAME'], port)
        staticurl = self.config("web", "staticurl") or req.url + 'static/'
        if not staticurl.endswith('/'):
            staticurl += '/'

        # some functions for the templater

        def header(**map):
            yield tmpl('header', encoding=self.encoding, **map)

        def footer(**map):
            yield tmpl("footer", **map)

        def motd(**map):
            yield self.config("web", "motd", "")

        def sessionvars(**map):
            fields = []
            if 'style' in req.form:
                style = req.form['style'][0]
                if style != self.config('web', 'style', ''):
                    fields.append(('style', style))

            separator = req.url[-1] == '?' and ';' or '?'
            for name, value in fields:
                yield dict(name=name, value=value, separator=separator)
                separator = ';'

        # figure out which style to use

        style = self.config("web", "style", "")
        if 'style' in req.form:
            style = req.form['style'][0]
        mapfile = style_map(self.templatepath, style)

        if not self.reponame:
            self.reponame = (self.config("web", "name")
                             or req.env.get('REPO_NAME')
                             or req.url.strip('/') or self.repo.root)

        # create the templater

        tmpl = templater.templater(mapfile, templatefilters.filters,
                                   defaults={"url": req.url,
                                             "staticurl": staticurl,
                                             "urlbase": urlbase,
                                             "repo": self.reponame,
                                             "header": header,
                                             "footer": footer,
                                             "motd": motd,
                                             "sessionvars": sessionvars
                                            })
        return tmpl

    def archivelist(self, nodeid):
        allowed = self.configlist("web", "allow_archive")
        for i, spec in self.archive_specs.iteritems():
            if i in allowed or self.configbool("web", "allow" + i):
                yield {"type" : i, "extension" : spec[2], "node" : nodeid}

    def listfilediffs(self, tmpl, files, changeset):
        for f in files[:self.maxfiles]:
            yield tmpl("filedifflink", node=hex(changeset), file=f)
        if len(files) > self.maxfiles:
            yield tmpl("fileellipses")

    def diff(self, tmpl, node1, node2, files):
        def filterfiles(filters, files):
            l = [x for x in files if x in filters]

            for t in filters:
                if t and t[-1] != os.sep:
                    t += os.sep
                l += [x for x in files if x.startswith(t)]
            return l

        parity = paritygen(self.stripecount)
        def diffblock(diff, f, fn):
            yield tmpl("diffblock",
                       lines=prettyprintlines(diff),
                       parity=parity.next(),
                       file=f,
                       filenode=hex(fn or nullid))

        blockcount = countgen()
        def prettyprintlines(diff):
            blockno = blockcount.next()
            for lineno, l in enumerate(diff.splitlines(1)):
                if blockno == 0:
                    lineno = lineno + 1
                else:
                    lineno = "%d.%d" % (blockno, lineno + 1)
                if l.startswith('+'):
                    ltype = "difflineplus"
                elif l.startswith('-'):
                    ltype = "difflineminus"
                elif l.startswith('@'):
                    ltype = "difflineat"
                else:
                    ltype = "diffline"
                yield tmpl(ltype,
                           line=l,
                           lineid="l%s" % lineno,
                           linenumber="% 8s" % lineno)

        r = self.repo
        c1 = r[node1]
        c2 = r[node2]
        date1 = util.datestr(c1.date())
        date2 = util.datestr(c2.date())

        modified, added, removed, deleted, unknown = r.status(node1, node2)[:5]
        if files:
            modified, added, removed = map(lambda x: filterfiles(files, x),
                                           (modified, added, removed))

        diffopts = patch.diffopts(self.repo.ui, untrusted=True)
        for f in modified:
            to = c1.filectx(f).data()
            tn = c2.filectx(f).data()
            yield diffblock(mdiff.unidiff(to, date1, tn, date2, f, f,
                                          opts=diffopts), f, tn)
        for f in added:
            to = None
            tn = c2.filectx(f).data()
            yield diffblock(mdiff.unidiff(to, date1, tn, date2, f, f,
                                          opts=diffopts), f, tn)
        for f in removed:
            to = c1.filectx(f).data()
            tn = None
            yield diffblock(mdiff.unidiff(to, date1, tn, date2, f, f,
                                          opts=diffopts), f, tn)

    archive_specs = {
        'bz2': ('application/x-tar', 'tbz2', '.tar.bz2', None),
        'gz': ('application/x-tar', 'tgz', '.tar.gz', None),
        'zip': ('application/zip', 'zip', '.zip', None),
        }

    def check_perm(self, req, op):
        '''Check permission for operation based on request data (including
        authentication info. Return true if op allowed, else false.'''

        def error(status, message):
            req.respond(status, protocol.HGTYPE)
            req.write('0\n%s\n' % message)

        if op == 'pull':
            return self.allowpull

        # enforce that you can only push using POST requests
        if req.env['REQUEST_METHOD'] != 'POST':
            error('405 Method Not Allowed', 'push requires POST request')
            return False

        # require ssl by default for pushing, auth info cannot be sniffed
        # and replayed
        scheme = req.env.get('wsgi.url_scheme')
        if self.configbool('web', 'push_ssl', True) and scheme != 'https':
            error(HTTP_OK, 'ssl required')
            return False

        user = req.env.get('REMOTE_USER')

        deny = self.configlist('web', 'deny_push')
        if deny and (not user or deny == ['*'] or user in deny):
            error('401 Unauthorized', 'push not authorized')
            return False

        allow = self.configlist('web', 'allow_push')
        result = allow and (allow == ['*'] or user in allow)
        if not result:
            error('401 Unauthorized', 'push not authorized')

        return result
