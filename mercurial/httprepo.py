# httprepo.py - HTTP repository proxy classes for mercurial
#
# Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>
# Copyright 2006 Vadim Gelfer <vadim.gelfer@gmail.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from node import *
from remoterepo import *
from i18n import gettext as _
from demandload import *
demandload(globals(), "hg os urllib urllib2 urlparse zlib util httplib")
demandload(globals(), "errno keepalive tempfile socket changegroup")

class passwordmgr(urllib2.HTTPPasswordMgrWithDefaultRealm):
    def __init__(self, ui):
        urllib2.HTTPPasswordMgrWithDefaultRealm.__init__(self)
        self.ui = ui

    def find_user_password(self, realm, authuri):
        authinfo = urllib2.HTTPPasswordMgrWithDefaultRealm.find_user_password(
            self, realm, authuri)
        user, passwd = authinfo
        if user and passwd:
            return (user, passwd)

        if not self.ui.interactive:
            raise util.Abort(_('http authorization required'))

        self.ui.write(_("http authorization required\n"))
        self.ui.status(_("realm: %s\n") % realm)
        if user:
            self.ui.status(_("user: %s\n") % user)
        else:
            user = self.ui.prompt(_("user:"), default=None)

        if not passwd:
            passwd = self.ui.getpass()

        self.add_password(realm, authuri, user, passwd)
        return (user, passwd)

def netlocsplit(netloc):
    '''split [user[:passwd]@]host[:port] into 4-tuple.'''

    a = netloc.find('@')
    if a == -1:
        user, passwd = None, None
    else:
        userpass, netloc = netloc[:a], netloc[a+1:]
        c = userpass.find(':')
        if c == -1:
            user, passwd = urllib.unquote(userpass), None
        else:
            user = urllib.unquote(userpass[:c])
            passwd = urllib.unquote(userpass[c+1:])
    c = netloc.find(':')
    if c == -1:
        host, port = netloc, None
    else:
        host, port = netloc[:c], netloc[c+1:]
    return host, port, user, passwd

def netlocunsplit(host, port, user=None, passwd=None):
    '''turn host, port, user, passwd into [user[:passwd]@]host[:port].'''
    if port:
        hostport = host + ':' + port
    else:
        hostport = host
    if user:
        if passwd:
            userpass = urllib.quote(user) + ':' + urllib.quote(passwd)
        else:
            userpass = urllib.quote(user)
        return userpass + '@' + hostport
    return hostport

class httpconnection(keepalive.HTTPConnection):
    # must be able to send big bundle as stream.

    def send(self, data):
        if isinstance(data, str):
            keepalive.HTTPConnection.send(self, data)
        else:
            # if auth required, some data sent twice, so rewind here
            data.seek(0)
            for chunk in util.filechunkiter(data):
                keepalive.HTTPConnection.send(self, chunk)

class basehttphandler(keepalive.HTTPHandler):
    def http_open(self, req):
        return self.do_open(httpconnection, req)

has_https = hasattr(urllib2, 'HTTPSHandler')
if has_https:
    class httpsconnection(httplib.HTTPSConnection):
        response_class = keepalive.HTTPResponse
        # must be able to send big bundle as stream.

        def send(self, data):
            if isinstance(data, str):
                httplib.HTTPSConnection.send(self, data)
            else:
                # if auth required, some data sent twice, so rewind here
                data.seek(0)
                for chunk in util.filechunkiter(data):
                    httplib.HTTPSConnection.send(self, chunk)

    class httphandler(basehttphandler, urllib2.HTTPSHandler):
        def https_open(self, req):
            return self.do_open(httpsconnection, req)
else:
    class httphandler(basehttphandler):
        pass

def zgenerator(f):
    zd = zlib.decompressobj()
    try:
        for chunk in util.filechunkiter(f):
            yield zd.decompress(chunk)
    except httplib.HTTPException, inst:
        raise IOError(None, _('connection ended unexpectedly'))
    yield zd.flush()

class httprepository(remoterepository):
    def __init__(self, ui, path):
        self.path = path
        self.caps = None
        scheme, netloc, urlpath, query, frag = urlparse.urlsplit(path)
        if query or frag:
            raise util.Abort(_('unsupported URL component: "%s"') %
                             (query or frag))
        if not urlpath: urlpath = '/'
        host, port, user, passwd = netlocsplit(netloc)

        # urllib cannot handle URLs with embedded user or passwd
        self._url = urlparse.urlunsplit((scheme, netlocunsplit(host, port),
                                         urlpath, '', ''))
        self.ui = ui

        proxyurl = ui.config("http_proxy", "host") or os.getenv('http_proxy')
        # XXX proxyauthinfo = None
        handlers = [httphandler()]

        if proxyurl:
            # proxy can be proper url or host[:port]
            if not (proxyurl.startswith('http:') or
                    proxyurl.startswith('https:')):
                proxyurl = 'http://' + proxyurl + '/'
            snpqf = urlparse.urlsplit(proxyurl)
            proxyscheme, proxynetloc, proxypath, proxyquery, proxyfrag = snpqf
            hpup = netlocsplit(proxynetloc)

            proxyhost, proxyport, proxyuser, proxypasswd = hpup
            if not proxyuser:
                proxyuser = ui.config("http_proxy", "user")
                proxypasswd = ui.config("http_proxy", "passwd")

            # see if we should use a proxy for this url
            no_list = [ "localhost", "127.0.0.1" ]
            no_list.extend([p.lower() for
                            p in ui.configlist("http_proxy", "no")])
            no_list.extend([p.strip().lower() for
                            p in os.getenv("no_proxy", '').split(',')
                            if p.strip()])
            # "http_proxy.always" config is for running tests on localhost
            if (not ui.configbool("http_proxy", "always") and
                host.lower() in no_list):
                ui.debug(_('disabling proxy for %s\n') % host)
            else:
                proxyurl = urlparse.urlunsplit((
                    proxyscheme, netlocunsplit(proxyhost, proxyport,
                                               proxyuser, proxypasswd or ''),
                    proxypath, proxyquery, proxyfrag))
                handlers.append(urllib2.ProxyHandler({scheme: proxyurl}))
                ui.debug(_('proxying through http://%s:%s\n') %
                          (proxyhost, proxyport))

        # urllib2 takes proxy values from the environment and those
        # will take precedence if found, so drop them
        for env in ["HTTP_PROXY", "http_proxy", "no_proxy"]:
            try:
                if os.environ.has_key(env):
                    del os.environ[env]
            except OSError:
                pass

        passmgr = passwordmgr(ui)
        if user:
            ui.debug(_('http auth: user %s, password %s\n') %
                     (user, passwd and '*' * len(passwd) or 'not set'))
            passmgr.add_password(None, host, user, passwd or '')

        handlers.extend((urllib2.HTTPBasicAuthHandler(passmgr),
                         urllib2.HTTPDigestAuthHandler(passmgr)))
        opener = urllib2.build_opener(*handlers)

        # 1.0 here is the _protocol_ version
        opener.addheaders = [('User-agent', 'mercurial/proto-1.0')]
        urllib2.install_opener(opener)

    def url(self):
        return self.path

    # look up capabilities only when needed

    def get_caps(self):
        if self.caps is None:
            try:
                self.caps = self.do_read('capabilities').split()
            except hg.RepoError:
                self.caps = ()
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
                self.ui.debug(_("sending %s bytes\n") %
                              headers.get('content-length', 'X'))
            resp = urllib2.urlopen(urllib2.Request(cu, data, headers))
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
        if not proto.startswith('application/mercurial-') and \
               not proto.startswith('text/plain') and \
               not proto.startswith('application/hg-changegroup'):
            raise hg.RepoError(_("'%s' does not appear to be an hg repository") %
                               self._url)

        if proto.startswith('application/mercurial-'):
            try:
                version = float(proto[22:])
            except ValueError:
                raise hg.RepoError(_("'%s' sent a broken Content-type "
                                     "header (%s)") % (self._url, proto))
            if version > 0.1:
                raise hg.RepoError(_("'%s' uses newer protocol %s") %
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
        d = self.do_cmd("lookup", key = key).read()
        success, data = d[:-1].split(' ', 1)
        if int(success):
            return bin(data)
        raise hg.RepoError(data)

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
        n = "\n".join(["-".join(map(hex, p)) for p in pairs])
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
        fp = file(tempname, "rb")
        try:
            length = os.stat(tempname).st_size
            try:
                rfp = self.do_cmd(
                    'unbundle', data=fp,
                    headers={'content-length': str(length),
                             'content-type': 'application/octet-stream'},
                    heads=' '.join(map(hex, heads)))
                try:
                    ret = int(rfp.readline())
                    self.ui.write(rfp.read())
                    return ret
                finally:
                    rfp.close()
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
    if path.startswith('hg:'):
        ui.warn(_("hg:// syntax is deprecated, please use http:// instead\n"))
        path = 'http:' + path[3:]
    if path.startswith('https:'):
        return httpsrepository(ui, path)
    return httprepository(ui, path)
