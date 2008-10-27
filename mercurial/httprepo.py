# httprepo.py - HTTP repository proxy classes for mercurial
#
# Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>
# Copyright 2006 Vadim Gelfer <vadim.gelfer@gmail.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from node import bin, hex, nullid
from i18n import _
import repo, os, urllib, urllib2, urlparse, zlib, util, httplib
import errno, keepalive, socket, changegroup, statichttprepo
import url

def zgenerator(f):
    zd = zlib.decompressobj()
    try:
        for chunk in util.filechunkiter(f):
            yield zd.decompress(chunk)
    except httplib.HTTPException, inst:
        raise IOError(None, _('connection ended unexpectedly'))
    yield zd.flush()

class httprepository(repo.repository):
    def __init__(self, ui, path):
        self.path = path
        self.caps = None
        self.handler = None
        scheme, netloc, urlpath, query, frag = urlparse.urlsplit(path)
        if query or frag:
            raise util.Abort(_('unsupported URL component: "%s"') %
                             (query or frag))

        # urllib cannot handle URLs with embedded user or passwd
        self._url, authinfo = url.getauthinfo(path)

        self.ui = ui
        self.ui.debug(_('using %s\n') % self._url)

        self.urlopener = url.opener(ui, authinfo)

    def url(self):
        return self.path

    # look up capabilities only when needed

    def get_caps(self):
        if self.caps is None:
            try:
                self.caps = util.set(self.do_read('capabilities').split())
            except repo.RepoError:
                self.caps = util.set()
            self.ui.debug(_('capabilities: %s\n') %
                          (' '.join(self.caps or ['none'])))
        return self.caps

    capabilities = property(get_caps)

    def lock(self):
        raise util.Abort(_('operation not supported over http'))

    def do_cmd(self, cmd, **args):
        data = args.pop('data', None)
        headers = args.pop('headers', {})
        self.ui.debug(_("sending %s command\n") % cmd)
        q = {"cmd": cmd}
        q.update(args)
        qs = '?%s' % urllib.urlencode(q)
        cu = "%s%s" % (self._url, qs)
        try:
            if data:
                self.ui.debug(_("sending %s bytes\n") % len(data))
            resp = self.urlopener.open(urllib2.Request(cu, data, headers))
        except urllib2.HTTPError, inst:
            if inst.code == 401:
                raise util.Abort(_('authorization failed'))
            raise
        except httplib.HTTPException, inst:
            self.ui.debug(_('http error while sending %s command\n') % cmd)
            self.ui.print_exc()
            raise IOError(None, inst)
        except IndexError:
            # this only happens with Python 2.3, later versions raise URLError
            raise util.Abort(_('http error, possibly caused by proxy setting'))
        # record the url we got redirected to
        resp_url = resp.geturl()
        if resp_url.endswith(qs):
            resp_url = resp_url[:-len(qs)]
        if self._url != resp_url:
            self.ui.status(_('real URL is %s\n') % resp_url)
            self._url = resp_url
        try:
            proto = resp.getheader('content-type')
        except AttributeError:
            proto = resp.headers['content-type']

        # accept old "text/plain" and "application/hg-changegroup" for now
        if not (proto.startswith('application/mercurial-') or
                proto.startswith('text/plain') or
                proto.startswith('application/hg-changegroup')):
            self.ui.debug(_("Requested URL: '%s'\n") % cu)
            raise repo.RepoError(_("'%s' does not appear to be an hg repository")
                               % self._url)

        if proto.startswith('application/mercurial-'):
            try:
                version = proto.split('-', 1)[1]
                version_info = tuple([int(n) for n in version.split('.')])
            except ValueError:
                raise repo.RepoError(_("'%s' sent a broken Content-Type "
                                     "header (%s)") % (self._url, proto))
            if version_info > (0, 1):
                raise repo.RepoError(_("'%s' uses newer protocol %s") %
                                   (self._url, version))

        return resp

    def do_read(self, cmd, **args):
        fp = self.do_cmd(cmd, **args)
        try:
            return fp.read()
        finally:
            # if using keepalive, allow connection to be reused
            fp.close()

    def lookup(self, key):
        self.requirecap('lookup', _('look up remote revision'))
        d = self.do_cmd("lookup", key = key).read()
        success, data = d[:-1].split(' ', 1)
        if int(success):
            return bin(data)
        raise repo.RepoError(data)

    def heads(self):
        d = self.do_read("heads")
        try:
            return map(bin, d[:-1].split(" "))
        except:
            raise util.UnexpectedOutput(_("unexpected response:"), d)

    def branches(self, nodes):
        n = " ".join(map(hex, nodes))
        d = self.do_read("branches", nodes=n)
        try:
            br = [ tuple(map(bin, b.split(" "))) for b in d.splitlines() ]
            return br
        except:
            raise util.UnexpectedOutput(_("unexpected response:"), d)

    def between(self, pairs):
        n = " ".join(["-".join(map(hex, p)) for p in pairs])
        d = self.do_read("between", pairs=n)
        try:
            p = [ l and map(bin, l.split(" ")) or [] for l in d.splitlines() ]
            return p
        except:
            raise util.UnexpectedOutput(_("unexpected response:"), d)

    def changegroup(self, nodes, kind):
        n = " ".join(map(hex, nodes))
        f = self.do_cmd("changegroup", roots=n)
        return util.chunkbuffer(zgenerator(f))

    def changegroupsubset(self, bases, heads, source):
        self.requirecap('changegroupsubset', _('look up remote changes'))
        baselst = " ".join([hex(n) for n in bases])
        headlst = " ".join([hex(n) for n in heads])
        f = self.do_cmd("changegroupsubset", bases=baselst, heads=headlst)
        return util.chunkbuffer(zgenerator(f))

    def unbundle(self, cg, heads, source):
        # have to stream bundle to a temp file because we do not have
        # http 1.1 chunked transfer.

        type = ""
        types = self.capable('unbundle')
        # servers older than d1b16a746db6 will send 'unbundle' as a
        # boolean capability
        try:
            types = types.split(',')
        except AttributeError:
            types = [""]
        if types:
            for x in types:
                if x in changegroup.bundletypes:
                    type = x
                    break

        tempname = changegroup.writebundle(cg, None, type)
        fp = url.httpsendfile(tempname, "rb")
        try:
            try:
                resp = self.do_read(
                     'unbundle', data=fp,
                     headers={'Content-Type': 'application/octet-stream'},
                     heads=' '.join(map(hex, heads)))
                resp_code, output = resp.split('\n', 1)
                try:
                    ret = int(resp_code)
                except ValueError, err:
                    raise util.UnexpectedOutput(
                            _('push failed (unexpected response):'), resp)
                self.ui.write(output)
                return ret
            except socket.error, err:
                if err[0] in (errno.ECONNRESET, errno.EPIPE):
                    raise util.Abort(_('push failed: %s') % err[1])
                raise util.Abort(err[1])
        finally:
            fp.close()
            os.unlink(tempname)

    def stream_out(self):
        return self.do_cmd('stream_out')

class httpsrepository(httprepository):
    def __init__(self, ui, path):
        if not has_https:
            raise util.Abort(_('Python support for SSL and HTTPS '
                               'is not installed'))
        httprepository.__init__(self, ui, path)

def instance(ui, path, create):
    if create:
        raise util.Abort(_('cannot create new http repository'))
    try:
        if path.startswith('https:'):
            inst = httpsrepository(ui, path)
        else:
            inst = httprepository(ui, path)
        inst.between([(nullid, nullid)])
        return inst
    except repo.RepoError:
        ui.note('(falling back to static-http)\n')
        return statichttprepo.instance(ui, "static-" + path, create)
