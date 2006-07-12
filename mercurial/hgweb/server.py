# hgweb/server.py - The standalone hg web server.
#
# Copyright 21 May 2005 - (c) 2005 Jake Edge <jake@edge2.net>
# Copyright 2005 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from mercurial.demandload import demandload
import os, sys, errno
demandload(globals(), "urllib BaseHTTPServer socket SocketServer")
demandload(globals(), "mercurial:ui,hg,util,templater")
demandload(globals(), "hgweb_mod:hgweb hgwebdir_mod:hgwebdir request:wsgiapplication")
from mercurial.i18n import gettext as _

def _splitURI(uri):
    """ Return path and query splited from uri

    Just like CGI environment, the path is unquoted, the query is
    not.
    """
    if '?' in uri:
        path, query = uri.split('?', 1)
    else:
        path, query = uri, ''
    return urllib.unquote(path), query

class _error_logger(object):
    def __init__(self, handler):
        self.handler = handler
    def flush(self):
        pass
    def write(str):
        self.writelines(str.split('\n'))
    def writelines(seq):
        for msg in seq:
            self.handler.log_error("HG error:  %s", msg)

class _hgwebhandler(object, BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, *args, **kargs):
        self.protocol_version = 'HTTP/1.1'
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args, **kargs)

    def log_error(self, format, *args):
        errorlog = self.server.errorlog
        errorlog.write("%s - - [%s] %s\n" % (self.address_string(),
                                             self.log_date_time_string(),
                                             format % args))

    def log_message(self, format, *args):
        accesslog = self.server.accesslog
        accesslog.write("%s - - [%s] %s\n" % (self.address_string(),
                                              self.log_date_time_string(),
                                              format % args))

    def do_POST(self):
        try:
            self.do_hgweb()
        except socket.error, inst:
            if inst[0] != errno.EPIPE:
                raise

    def do_GET(self):
        self.do_POST()

    def do_hgweb(self):
        path_info, query = _splitURI(self.path)

        env = {}
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['REQUEST_METHOD'] = self.command
        env['SERVER_NAME'] = self.server.server_name
        env['SERVER_PORT'] = str(self.server.server_port)
        env['REQUEST_URI'] = "/"
        env['PATH_INFO'] = path_info
        if query:
            env['QUERY_STRING'] = query
        host = self.address_string()
        if host != self.client_address[0]:
            env['REMOTE_HOST'] = host
            env['REMOTE_ADDR'] = self.client_address[0]

        if self.headers.typeheader is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = self.headers.typeheader
        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length
        for header in [h for h in self.headers.keys() \
                       if h not in ('content-type', 'content-length')]:
            hkey = 'HTTP_' + header.replace('-', '_').upper()
            hval = self.headers.getheader(header)
            hval = hval.replace('\n', '').strip()
            if hval:
                env[hkey] = hval
        env['SERVER_PROTOCOL'] = self.request_version
        env['wsgi.version'] = (1, 0)
        env['wsgi.url_scheme'] = 'http'
        env['wsgi.input'] = self.rfile
        env['wsgi.errors'] = _error_logger(self)
        env['wsgi.multithread'] = isinstance(self.server,
                                             SocketServer.ThreadingMixIn)
        env['wsgi.multiprocess'] = isinstance(self.server,
                                              SocketServer.ForkingMixIn)
        env['wsgi.run_once'] = 0

        self.close_connection = True
        self.saved_status = None
        self.saved_headers = []
        self.sent_headers = False
        self.length = None
        req = self.server.reqmaker(env, self._start_response)
        for data in req:
            if data:
                self._write(data)

    def send_headers(self):
        if not self.saved_status:
            raise AssertionError("Sending headers before start_response() called")
        saved_status = self.saved_status.split(None, 1)
        saved_status[0] = int(saved_status[0])
        self.send_response(*saved_status)
        should_close = True
        for h in self.saved_headers:
            self.send_header(*h)
            if h[0].lower() == 'content-length':
                should_close = False
                self.length = int(h[1])
        # The value of the Connection header is a list of case-insensitive
        # tokens separated by commas and optional whitespace.
        if 'close' in [token.strip().lower() for token in
                       self.headers.get('connection', '').split(',')]:
            should_close = True
        if should_close:
            self.send_header('Connection', 'close')
        self.close_connection = should_close
        self.end_headers()
        self.sent_headers = True

    def _start_response(self, http_status, headers, exc_info=None):
        code, msg = http_status.split(None, 1)
        code = int(code)
        self.saved_status = http_status
        bad_headers = ('connection', 'transfer-encoding')
        self.saved_headers = [ h for h in headers \
                               if h[0].lower() not in bad_headers ]
        return self._write

    def _write(self, data):
        if not self.saved_status:
            raise AssertionError("data written before start_response() called")
        elif not self.sent_headers:
            self.send_headers()
        if self.length is not None:
            if len(data) > self.length:
                raise AssertionError("Content-length header sent, but more bytes than specified are being written.")
            self.length = self.length - len(data)
        self.wfile.write(data)
        self.wfile.flush()

def create_server(ui, repo):
    use_threads = True

    def openlog(opt, default):
        if opt and opt != '-':
            return open(opt, 'w')
        return default

    address = ui.config("web", "address", "")
    port = int(ui.config("web", "port", 8000))
    use_ipv6 = ui.configbool("web", "ipv6")
    webdir_conf = ui.config("web", "webdir_conf")
    accesslog = openlog(ui.config("web", "accesslog", "-"), sys.stdout)
    errorlog = openlog(ui.config("web", "errorlog", "-"), sys.stderr)

    if use_threads:
        try:
            from threading import activeCount
        except ImportError:
            use_threads = False

    if use_threads:
        _mixin = SocketServer.ThreadingMixIn
    else:
        if hasattr(os, "fork"):
            _mixin = SocketServer.ForkingMixIn
        else:
            class _mixin: pass

    class MercurialHTTPServer(object, _mixin, BaseHTTPServer.HTTPServer):
        def __init__(self, *args, **kargs):
            BaseHTTPServer.HTTPServer.__init__(self, *args, **kargs)
            self.accesslog = accesslog
            self.errorlog = errorlog
            self.repo = repo
            self.webdir_conf = webdir_conf
            self.webdirmaker = hgwebdir
            self.repoviewmaker = hgweb
            self.reqmaker = wsgiapplication(self.make_handler)

        def make_handler(self):
            if self.webdir_conf:
                hgwebobj = self.webdirmaker(self.webdir_conf)
            elif self.repo is not None:
                hgwebobj = self.repoviewmaker(repo.__class__(repo.ui,
                                                             repo.origroot))
            else:
                raise hg.RepoError(_('no repo found'))
            return hgwebobj

    class IPv6HTTPServer(MercurialHTTPServer):
        address_family = getattr(socket, 'AF_INET6', None)

        def __init__(self, *args, **kwargs):
            if self.address_family is None:
                raise hg.RepoError(_('IPv6 not available on this system'))
            super(IPv6HTTPServer, self).__init__(*args, **kwargs)

    if use_ipv6:
        return IPv6HTTPServer((address, port), _hgwebhandler)
    else:
        return MercurialHTTPServer((address, port), _hgwebhandler)
