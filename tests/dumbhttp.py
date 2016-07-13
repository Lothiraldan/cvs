#!/usr/bin/env python

from __future__ import absolute_import

"""
Small and dumb HTTP server for use in tests.
"""

import optparse
import signal
import sys

from mercurial import (
    cmdutil,
    util,
)

httpserver = util.httpserver
OptionParser = optparse.OptionParser

class simplehttpservice(object):
    def __init__(self, host, port):
        self.address = (host, port)
    def init(self):
        self.httpd = httpserver.httpserver(
            self.address, httpserver.simplehttprequesthandler)
    def run(self):
        self.httpd.serve_forever()

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-p', '--port', dest='port', type='int', default=8000,
        help='TCP port to listen on', metavar='PORT')
    parser.add_option('-H', '--host', dest='host', default='localhost',
        help='hostname or IP to listen on', metavar='HOST')
    parser.add_option('--pid', dest='pid',
        help='file name where the PID of the server is stored')
    parser.add_option('-f', '--foreground', dest='foreground',
        action='store_true',
        help='do not start the HTTP server in the background')
    parser.add_option('--daemon-postexec', action='append')

    (options, args) = parser.parse_args()

    signal.signal(signal.SIGTERM, lambda x, y: sys.exit(0))

    if options.foreground and options.pid:
        parser.error("options --pid and --foreground are mutually exclusive")

    opts = {'pid_file': options.pid,
            'daemon': not options.foreground,
            'daemon_postexec': options.daemon_postexec}
    service = simplehttpservice(options.host, options.port)
    cmdutil.service(opts, initfn=service.init, runfn=service.run,
                    runargs=[sys.executable, __file__] + sys.argv[1:])
