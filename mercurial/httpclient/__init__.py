# Copyright 2010, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Improved HTTP/1.1 client library

This library contains an HTTPConnection which is similar to the one in
httplib, but has several additional features:

  * supports keepalives natively
  * uses select() to block for incoming data
  * notices when the server responds early to a request
  * implements ssl inline instead of in a different class
"""

import cStringIO
import errno
import httplib
import logging
import rfc822
import select
import socket

import socketutil

logger = logging.getLogger(__name__)

__all__ = ['HTTPConnection', 'HTTPResponse']

HTTP_VER_1_0 = 'HTTP/1.0'
HTTP_VER_1_1 = 'HTTP/1.1'

_LEN_CLOSE_IS_END = -1

OUTGOING_BUFFER_SIZE = 1 << 15
INCOMING_BUFFER_SIZE = 1 << 20

HDR_ACCEPT_ENCODING = 'accept-encoding'
HDR_CONNECTION_CTRL = 'connection'
HDR_CONTENT_LENGTH = 'content-length'
HDR_XFER_ENCODING = 'transfer-encoding'

XFER_ENCODING_CHUNKED = 'chunked'

CONNECTION_CLOSE = 'close'

EOL = '\r\n'
_END_HEADERS = EOL * 2

# Based on some searching around, 1 second seems like a reasonable
# default here.
TIMEOUT_ASSUME_CONTINUE = 1
TIMEOUT_DEFAULT = None


class HTTPResponse(object):
    """Response from an HTTP server.

    The response will continue to load as available. If you need the
    complete response before continuing, check the .complete() method.
    """
    def __init__(self, sock, timeout):
        self.sock = sock
        self.raw_response = ''
        self._body = None
        self._headers_len = 0
        self._content_len = 0
        self.headers = None
        self.will_close = False
        self.status_line = ''
        self.status = None
        self.http_version = None
        self.reason = None
        self._chunked = False
        self._chunked_done = False
        self._chunked_until_next = 0
        self._chunked_skip_bytes = 0
        self._chunked_preloaded_block = None

        self._read_location = 0
        self._eol = EOL

        self._timeout = timeout

    @property
    def _end_headers(self):
        return self._eol * 2

    def complete(self):
        """Returns true if this response is completely loaded.

        Note that if this is a connection where complete means the
        socket is closed, this will nearly always return False, even
        in cases where all the data has actually been loaded.
        """
        if self._chunked:
            return self._chunked_done
        if self._content_len == _LEN_CLOSE_IS_END:
            return False
        return self._body is not None and len(self._body) >= self._content_len

    def readline(self):
        """Read a single line from the response body.

        This may block until either a line ending is found or the
        response is complete.
        """
        eol = self._body.find('\n', self._read_location)
        while eol == -1 and not self.complete():
            self._select()
            eol = self._body.find('\n', self._read_location)
        if eol != -1:
            eol += 1
        else:
            eol = len(self._body)
        data = self._body[self._read_location:eol]
        self._read_location = eol
        return data

    def read(self, length=None):
        # if length is None, unbounded read
        while (not self.complete()  # never select on a finished read
               and (not length  # unbounded, so we wait for complete()
                    or (self._read_location + length) > len(self._body))):
            self._select()
        if not length:
            length = len(self._body) - self._read_location
        elif len(self._body) < (self._read_location + length):
            length = len(self._body) - self._read_location
        r = self._body[self._read_location:self._read_location + length]
        self._read_location += len(r)
        if self.complete() and self.will_close:
            self.sock.close()
        return r

    def _select(self):
        r, _, _ = select.select([self.sock], [], [], self._timeout)
        if not r:
            # socket was not readable. If the response is not complete
            # and we're not a _LEN_CLOSE_IS_END response, raise a timeout.
            # If we are a _LEN_CLOSE_IS_END response and we have no data,
            # raise a timeout.
            if not (self.complete() or
                    (self._content_len == _LEN_CLOSE_IS_END and self._body)):
                logger.info('timed out with timeout of %s', self._timeout)
                raise HTTPTimeoutException('timeout reading data')
            logger.info('cl: %r body: %r', self._content_len, self._body)
        try:
            data = self.sock.recv(INCOMING_BUFFER_SIZE)
            # If the socket was readable and no data was read, that
            # means the socket was closed. If this isn't a
            # _CLOSE_IS_END socket, then something is wrong if we're
            # here (we shouldn't enter _select() if the response is
            # complete), so abort.
            if not data and self._content_len != _LEN_CLOSE_IS_END:
                raise HTTPRemoteClosedError(
                    'server appears to have closed the socket mid-response')
        except socket.sslerror, e:
            if e.args[0] != socket.SSL_ERROR_WANT_READ:
                raise
            logger.debug('SSL_WANT_READ in _select, should retry later')
            return True
        logger.debug('response read %d data during _select', len(data))
        if not data:
            if self.headers and self._content_len == _LEN_CLOSE_IS_END:
                self._content_len = len(self._body)
            return False
        else:
            self._load_response(data)
            return True

    def _chunked_parsedata(self, data):
        if self._chunked_preloaded_block:
            data = self._chunked_preloaded_block + data
            self._chunked_preloaded_block = None
        while data:
            logger.debug('looping with %d data remaining', len(data))
            # Slice out anything we should skip
            if self._chunked_skip_bytes:
                if len(data) <= self._chunked_skip_bytes:
                    self._chunked_skip_bytes -= len(data)
                    data = ''
                    break
                else:
                    data = data[self._chunked_skip_bytes:]
                    self._chunked_skip_bytes = 0

            # determine how much is until the next chunk
            if self._chunked_until_next:
                amt = self._chunked_until_next
                logger.debug('reading remaining %d of existing chunk', amt)
                self._chunked_until_next = 0
                body = data
            else:
                try:
                    amt, body = data.split(self._eol, 1)
                except ValueError:
                    self._chunked_preloaded_block = data
                    logger.debug('saving %r as a preloaded block for chunked',
                                 self._chunked_preloaded_block)
                    return
                amt = int(amt, base=16)
                logger.debug('reading chunk of length %d', amt)
                if amt == 0:
                    self._chunked_done = True

            # read through end of what we have or the chunk
            self._body += body[:amt]
            if len(body) >= amt:
                data = body[amt:]
                self._chunked_skip_bytes = len(self._eol)
            else:
                self._chunked_until_next = amt - len(body)
                self._chunked_skip_bytes = 0
                data = ''

    def _load_response(self, data):
        if self._chunked:
            self._chunked_parsedata(data)
            return
        elif self._body is not None:
            self._body += data
            return

        # We haven't seen end of headers yet
        self.raw_response += data
        # This is a bogus server with bad line endings
        if self._eol not in self.raw_response:
            for bad_eol in ('\n', '\r'):
                if (bad_eol in self.raw_response
                    # verify that bad_eol is not the end of the incoming data
                    # as this could be a response line that just got
                    # split between \r and \n.
                    and (self.raw_response.index(bad_eol) <
                         (len(self.raw_response) - 1))):
                    logger.info('bogus line endings detected, '
                                'using %r for EOL', bad_eol)
                    self._eol = bad_eol
                    break
        # exit early if not at end of headers
        if self._end_headers not in self.raw_response or self.headers:
            return

        # handle 100-continue response
        hdrs, body = self.raw_response.split(self._end_headers, 1)
        http_ver, status = hdrs.split(' ', 1)
        if status.startswith('100'):
            self.raw_response = body
            logger.debug('continue seen, setting body to %r', body)
            return

        # arriving here means we should parse response headers
        # as all headers have arrived completely
        hdrs, body = self.raw_response.split(self._end_headers, 1)
        del self.raw_response
        if self._eol in hdrs:
            self.status_line, hdrs = hdrs.split(self._eol, 1)
        else:
            self.status_line = hdrs
            hdrs = ''
        # TODO HTTP < 1.0 support
        (self.http_version, self.status,
         self.reason) = self.status_line.split(' ', 2)
        self.status = int(self.status)
        if self._eol != EOL:
            hdrs = hdrs.replace(self._eol, '\r\n')
        headers = rfc822.Message(cStringIO.StringIO(hdrs))
        if HDR_CONTENT_LENGTH in headers:
            self._content_len = int(headers[HDR_CONTENT_LENGTH])
        if self.http_version == HTTP_VER_1_0:
            self.will_close = True
        elif HDR_CONNECTION_CTRL in headers:
            self.will_close = (
                headers[HDR_CONNECTION_CTRL].lower() == CONNECTION_CLOSE)
            if self._content_len == 0:
                self._content_len = _LEN_CLOSE_IS_END
        if (HDR_XFER_ENCODING in headers
            and headers[HDR_XFER_ENCODING].lower() == XFER_ENCODING_CHUNKED):
            self._body = ''
            self._chunked_parsedata(body)
            self._chunked = True
        if self._body is None:
            self._body = body
        self.headers = headers


class HTTPConnection(object):
    """Connection to a single http server.

    Supports 100-continue and keepalives natively. Uses select() for
    non-blocking socket operations.
    """
    http_version = HTTP_VER_1_1
    response_class = HTTPResponse

    def __init__(self, host, port=None, use_ssl=None, ssl_validator=None,
                 timeout=TIMEOUT_DEFAULT,
                 continue_timeout=TIMEOUT_ASSUME_CONTINUE,
                 proxy_hostport=None, **ssl_opts):
        """Create a new HTTPConnection.

        Args:
          host: The host to which we'll connect.
          port: Optional. The port over which we'll connect. Default 80 for
                non-ssl, 443 for ssl.
          use_ssl: Optional. Wether to use ssl. Defaults to False if port is
                   not 443, true if port is 443.
          ssl_validator: a function(socket) to validate the ssl cert
          timeout: Optional. Connection timeout, default is TIMEOUT_DEFAULT.
          continue_timeout: Optional. Timeout for waiting on an expected
                   "100 Continue" response. Default is TIMEOUT_ASSUME_CONTINUE.
          proxy_hostport: Optional. Tuple of (host, port) to use as an http
                       proxy for the connection. Default is to not use a proxy.
        """
        if port is None and host.count(':') == 1 or ']:' in host:
            host, port = host.rsplit(':', 1)
            port = int(port)
            if '[' in host:
                host = host[1:-1]
        if use_ssl is None and port is None:
            use_ssl = False
            port = 80
        elif use_ssl is None:
            use_ssl = (port == 443)
        elif port is None:
            port = (use_ssl and 443 or 80)
        self.port = port
        if use_ssl and not socketutil.have_ssl:
            raise Exception('ssl requested but unavailable on this Python')
        self.ssl = use_ssl
        self.ssl_opts = ssl_opts
        self._ssl_validator = ssl_validator
        self.host = host
        self.sock = None
        self._current_response = None
        self._current_response_taken = False
        if proxy_hostport is None:
            self._proxy_host = self._proxy_port = None
        else:
            self._proxy_host, self._proxy_port = proxy_hostport

        self.timeout = timeout
        self.continue_timeout = continue_timeout

    def _connect(self):
        """Connect to the host and port specified in __init__."""
        if self.sock:
            return
        if self._proxy_host is not None:
            logger.info('Connecting to http proxy %s:%s',
                        self._proxy_host, self._proxy_port)
            sock = socketutil.create_connection((self._proxy_host,
                                                 self._proxy_port))
            if self.ssl:
                # TODO proxy header support
                data = self.buildheaders('CONNECT', '%s:%d' % (self.host,
                                                               self.port),
                                         {}, HTTP_VER_1_0)
                sock.send(data)
                sock.setblocking(0)
                r = self.response_class(sock, self.timeout)
                timeout_exc = HTTPTimeoutException(
                    'Timed out waiting for CONNECT response from proxy')
                while not r.complete():
                    try:
                        if not r._select():
                            raise timeout_exc
                    except HTTPTimeoutException:
                        # This raise/except pattern looks goofy, but
                        # _select can raise the timeout as well as the
                        # loop body. I wish it wasn't this convoluted,
                        # but I don't have a better solution
                        # immediately handy.
                        raise timeout_exc
                if r.status != 200:
                    raise HTTPProxyConnectFailedException(
                        'Proxy connection failed: %d %s' % (r.status,
                                                            r.read()))
                logger.info('CONNECT (for SSL) to %s:%s via proxy succeeded.',
                            self.host, self.port)
        else:
            sock = socketutil.create_connection((self.host, self.port))
        if self.ssl:
            logger.debug('wrapping socket for ssl with options %r',
                         self.ssl_opts)
            sock = socketutil.wrap_socket(sock, **self.ssl_opts)
            if self._ssl_validator:
                self._ssl_validator(sock)
        sock.setblocking(0)
        self.sock = sock

    def buildheaders(self, method, path, headers, http_ver):
        if self.ssl and self.port == 443 or self.port == 80:
            # default port for protocol, so leave it out
            hdrhost = self.host
        else:
            # include nonstandard port in header
            if ':' in self.host:  # must be IPv6
                hdrhost = '[%s]:%d' % (self.host, self.port)
            else:
                hdrhost = '%s:%d' % (self.host, self.port)
        if self._proxy_host and not self.ssl:
            # When talking to a regular http proxy we must send the
            # full URI, but in all other cases we must not (although
            # technically RFC 2616 says servers must accept our
            # request if we screw up, experimentally few do that
            # correctly.)
            assert path[0] == '/', 'path must start with a /'
            path = 'http://%s%s' % (hdrhost, path)
        outgoing = ['%s %s %s%s' % (method, path, http_ver, EOL)]
        headers['host'] = ('Host', hdrhost)
        headers[HDR_ACCEPT_ENCODING] = (HDR_ACCEPT_ENCODING, 'identity')
        for hdr, val in headers.itervalues():
            outgoing.append('%s: %s%s' % (hdr, val, EOL))
        outgoing.append(EOL)
        return ''.join(outgoing)

    def close(self):
        """Close the connection to the server.

        This is a no-op if the connection is already closed. The
        connection may automatically close if requessted by the server
        or required by the nature of a response.
        """
        if self.sock is None:
            return
        self.sock.close()
        self.sock = None
        logger.info('closed connection to %s on %s', self.host, self.port)

    def busy(self):
        """Returns True if this connection object is currently in use.

        If a response is still pending, this will return True, even if
        the request has finished sending. In the future,
        HTTPConnection may transparently juggle multiple connections
        to the server, in which case this will be useful to detect if
        any of those connections is ready for use.
        """
        cr = self._current_response
        if cr is not None:
            if self._current_response_taken:
                if cr.will_close:
                    self.sock = None
                    self._current_response = None
                    return False
                elif cr.complete():
                    self._current_response = None
                    return False
            return True
        return False

    def request(self, method, path, body=None, headers={},
                expect_continue=False):
        """Send a request to the server.

        For increased flexibility, this does not return the response
        object. Future versions of HTTPConnection that juggle multiple
        sockets will be able to send (for example) 5 requests all at
        once, and then let the requests arrive as data is
        available. Use the `getresponse()` method to retrieve the
        response.
        """
        if self.busy():
            raise httplib.CannotSendRequest(
                'Can not send another request before '
                'current response is read!')
        self._current_response_taken = False

        logger.info('sending %s request for %s to %s on port %s',
                    method, path, self.host, self.port)
        hdrs = dict((k.lower(), (k, v)) for k, v in headers.iteritems())
        if hdrs.get('expect', ('', ''))[1].lower() == '100-continue':
            expect_continue = True
        elif expect_continue:
            hdrs['expect'] = ('Expect', '100-Continue')

        chunked = False
        if body and HDR_CONTENT_LENGTH not in hdrs:
            if getattr(body, '__len__', False):
                hdrs[HDR_CONTENT_LENGTH] = (HDR_CONTENT_LENGTH, len(body))
            elif getattr(body, 'read', False):
                hdrs[HDR_XFER_ENCODING] = (HDR_XFER_ENCODING,
                                           XFER_ENCODING_CHUNKED)
                chunked = True
            else:
                raise BadRequestData('body has no __len__() nor read()')

        self._connect()
        outgoing_headers = self.buildheaders(
            method, path, hdrs, self.http_version)
        response = None
        first = True

        def reconnect(where):
            logger.info('reconnecting during %s', where)
            self.close()
            self._connect()

        while ((outgoing_headers or body)
               and not (response and response.complete())):
            select_timeout = self.timeout
            out = outgoing_headers or body
            blocking_on_continue = False
            if expect_continue and not outgoing_headers and not (
                response and response.headers):
                logger.info(
                    'waiting up to %s seconds for'
                    ' continue response from server',
                    self.continue_timeout)
                select_timeout = self.continue_timeout
                blocking_on_continue = True
                out = False
            if out:
                w = [self.sock]
            else:
                w = []
            r, w, x = select.select([self.sock], w, [], select_timeout)
            # if we were expecting a 100 continue and it's been long
            # enough, just go ahead and assume it's ok. This is the
            # recommended behavior from the RFC.
            if r == w == x == []:
                if blocking_on_continue:
                    expect_continue = False
                    logger.info('no response to continue expectation from '
                                'server, optimistically sending request body')
                else:
                    raise HTTPTimeoutException('timeout sending data')
            # TODO exceptional conditions with select? (what are those be?)
            # TODO if the response is loading, must we finish sending at all?
            #
            # Certainly not if it's going to close the connection and/or
            # the response is already done...I think.
            was_first = first

            # incoming data
            if r:
                try:
                    try:
                        data = r[0].recv(INCOMING_BUFFER_SIZE)
                    except socket.sslerror, e:
                        if e.args[0] != socket.SSL_ERROR_WANT_READ:
                            raise
                        logger.debug(
                            'SSL_WANT_READ while sending data, retrying...')
                        continue
                    if not data:
                        logger.info('socket appears closed in read')
                        self.sock = None
                        self._current_response = None
                        # This if/elif ladder is a bit subtle,
                        # comments in each branch should help.
                        if response is not None and (
                            response.complete() or
                            response._content_len == _LEN_CLOSE_IS_END):
                            # Server responded completely and then
                            # closed the socket. We should just shut
                            # things down and let the caller get their
                            # response.
                            logger.info('Got an early response, '
                                        'aborting remaining request.')
                            break
                        elif was_first and response is None:
                            # Most likely a keepalive that got killed
                            # on the server's end. Commonly happens
                            # after getting a really large response
                            # from the server.
                            logger.info(
                                'Connection appeared closed in read on first'
                                ' request loop iteration, will retry.')
                            reconnect('read')
                            continue
                        else:
                            # We didn't just send the first data hunk,
                            # and either have a partial response or no
                            # response at all. There's really nothing
                            # meaningful we can do here.
                            raise HTTPStateError(
                                'Connection appears closed after '
                                'some request data was written, but the '
                                'response was missing or incomplete!')
                    logger.debug('read %d bytes in request()', len(data))
                    if response is None:
                        response = self.response_class(r[0], self.timeout)
                    response._load_response(data)
                    # Jump to the next select() call so we load more
                    # data if the server is still sending us content.
                    continue
                except socket.error, e:
                    if e[0] != errno.EPIPE and not was_first:
                        raise
                    if (response._content_len
                        and response._content_len != _LEN_CLOSE_IS_END):
                        outgoing_headers = sent_data + outgoing_headers
                        reconnect('read')

            # outgoing data
            if w and out:
                try:
                    if getattr(out, 'read', False):
                        data = out.read(OUTGOING_BUFFER_SIZE)
                        if not data:
                            continue
                        if len(data) < OUTGOING_BUFFER_SIZE:
                            if chunked:
                                body = '0' + EOL + EOL
                            else:
                                body = None
                        if chunked:
                            out = hex(len(data))[2:] + EOL + data + EOL
                        else:
                            out = data
                    amt = w[0].send(out)
                except socket.error, e:
                    if e[0] == socket.SSL_ERROR_WANT_WRITE and self.ssl:
                        # This means that SSL hasn't flushed its buffer into
                        # the socket yet.
                        # TODO: find a way to block on ssl flushing its buffer
                        # similar to selecting on a raw socket.
                        continue
                    elif (e[0] not in (errno.ECONNRESET, errno.EPIPE)
                          and not first):
                        raise
                    reconnect('write')
                    amt = self.sock.send(out)
                logger.debug('sent %d', amt)
                first = False
                # stash data we think we sent in case the socket breaks
                # when we read from it
                if was_first:
                    sent_data = out[:amt]
                if out is body:
                    body = out[amt:]
                else:
                    outgoing_headers = out[amt:]

        # close if the server response said to or responded before eating
        # the whole request
        if response is None:
            response = self.response_class(self.sock, self.timeout)
        complete = response.complete()
        data_left = bool(outgoing_headers or body)
        if data_left:
            logger.info('stopped sending request early, '
                         'will close the socket to be safe.')
            response.will_close = True
        if response.will_close:
            # The socket will be closed by the response, so we disown
            # the socket
            self.sock = None
        self._current_response = response

    def getresponse(self):
        if self._current_response is None:
            raise httplib.ResponseNotReady()
        r = self._current_response
        while r.headers is None:
            r._select()
        if r.will_close:
            self.sock = None
            self._current_response = None
        elif r.complete():
            self._current_response = None
        else:
            self._current_response_taken = True
        return r


class HTTPTimeoutException(httplib.HTTPException):
    """A timeout occurred while waiting on the server."""


class BadRequestData(httplib.HTTPException):
    """Request body object has neither __len__ nor read."""


class HTTPProxyConnectFailedException(httplib.HTTPException):
    """Connecting to the HTTP proxy failed."""


class HTTPStateError(httplib.HTTPException):
    """Invalid internal state encountered."""


class HTTPRemoteClosedError(httplib.HTTPException):
    """The server closed the remote socket in the middle of a response."""
# no-check-code
