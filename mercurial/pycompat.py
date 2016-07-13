# pycompat.py - portability shim for python 3
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

"""Mercurial portability shim for python 3.

This contains aliases to hide python version-specific details from the core.
"""

from __future__ import absolute_import

try:
    import cPickle as pickle
    pickle.dumps
except ImportError:
    import pickle
    pickle.dumps # silence pyflakes

try:
    import httplib
    httplib.HTTPException
except ImportError:
    import http.client as httplib
    httplib.HTTPException

try:
    import SocketServer as socketserver
    socketserver.ThreadingMixIn
except ImportError:
    import socketserver
    socketserver.ThreadingMixIn

try:
    import xmlrpclib
    xmlrpclib.Transport
except ImportError:
    import xmlrpc.client as xmlrpclib
    xmlrpclib.Transport

try:
    import urlparse
    urlparse.urlparse
except ImportError:
    import urllib.parse as urlparse
    urlparse.urlparse

try:
    import cStringIO as io
    stringio = io.StringIO
except ImportError:
    import io
    stringio = io.StringIO

try:
    import Queue as _queue
    _queue.Queue
except ImportError:
    import queue as _queue
empty = _queue.Empty
queue = _queue.Queue

class _pycompatstub(object):
    pass

def _alias(alias, origin, items):
    """ populate a _pycompatstub

    copies items from origin to alias
    """
    def hgcase(item):
        return item.replace('_', '').lower()
    for item in items:
        try:
            setattr(alias, hgcase(item), getattr(origin, item))
        except AttributeError:
            pass

httpserver = _pycompatstub()
urlreq = _pycompatstub()
urlerr = _pycompatstub()
try:
    import BaseHTTPServer
    import CGIHTTPServer
    import SimpleHTTPServer
    import urllib2
    import urllib
    _alias(urlreq, urllib, (
        "addclosehook",
        "addinfourl",
        "ftpwrapper",
        "pathname2url",
        "quote",
        "splitattr",
        "splitpasswd",
        "splitport",
        "splituser",
        "unquote",
        "url2pathname",
        "urlencode",
        "urlencode",
    ))
    _alias(urlreq, urllib2, (
        "AbstractHTTPHandler",
        "BaseHandler",
        "build_opener",
        "FileHandler",
        "FTPHandler",
        "HTTPBasicAuthHandler",
        "HTTPDigestAuthHandler",
        "HTTPHandler",
        "HTTPPasswordMgrWithDefaultRealm",
        "HTTPSHandler",
        "install_opener",
        "ProxyHandler",
        "Request",
        "urlopen",
    ))
    _alias(urlerr, urllib2, (
        "HTTPError",
        "URLError",
    ))
    _alias(httpserver, BaseHTTPServer, (
        "HTTPServer",
        "BaseHTTPRequestHandler",
    ))
    _alias(httpserver, SimpleHTTPServer, (
        "SimpleHTTPRequestHandler",
    ))
    _alias(httpserver, CGIHTTPServer, (
        "CGIHTTPRequestHandler",
    ))

except ImportError:
    import urllib.request
    _alias(urlreq, urllib.request, (
        "AbstractHTTPHandler",
        "addclosehook",
        "addinfourl",
        "BaseHandler",
        "build_opener",
        "FileHandler",
        "FTPHandler",
        "ftpwrapper",
        "HTTPHandler",
        "HTTPSHandler",
        "install_opener",
        "pathname2url",
        "HTTPBasicAuthHandler",
        "HTTPDigestAuthHandler",
        "HTTPPasswordMgrWithDefaultRealm",
        "ProxyHandler",
        "quote",
        "Request",
        "splitattr",
        "splitpasswd",
        "splitport",
        "splituser",
        "unquote",
        "url2pathname",
        "urlopen",
    ))
    import urllib.error
    _alias(urlerr, urllib.error, (
        "HTTPError",
        "URLError",
    ))
    import http.server
    _alias(httpserver, http.server, (
        "HTTPServer",
        "BaseHTTPRequestHandler",
        "SimpleHTTPRequestHandler",
        "CGIHTTPRequestHandler",
    ))

try:
    xrange
except NameError:
    import builtins
    builtins.xrange = range
