# __init__.py - inotify-based status acceleration for Linux
#
# Copyright 2006, 2007, 2008 Bryan O'Sullivan <bos@serpentine.com>
# Copyright 2007, 2008 Brendan Cully <brendan@kublai.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2, incorporated herein by reference.

'''inotify-based status acceleration for Linux systems
'''

# todo: socket permissions

from mercurial.i18n import _
from mercurial import cmdutil, util
import os, server
from weakref import proxy
from client import client, QueryFailed

def serve(ui, repo, **opts):
    '''start an inotify server for this repository'''
    timeout = opts.get('timeout')
    if timeout:
        timeout = float(timeout) * 1e3

    class service:
        def init(self):
            try:
                self.master = server.master(ui, repo, timeout)
            except server.AlreadyStartedException, inst:
                raise util.Abort(str(inst))

        def run(self):
            try:
                self.master.run()
            finally:
                self.master.shutdown()

    service = service()
    cmdutil.service(opts, initfn=service.init, runfn=service.run)

def reposetup(ui, repo):
    if not hasattr(repo, 'dirstate'):
        return

    # XXX: weakref until hg stops relying on __del__
    repo = proxy(repo)

    class inotifydirstate(repo.dirstate.__class__):
        # Set to True if we're the inotify server, so we don't attempt
        # to recurse.
        inotifyserver = False

        def status(self, match, ignored, clean, unknown=True):
            files = match.files()
            if '.' in files:
                files = []
            if not ignored and not self.inotifyserver:
                cli = client(ui, repo)
                try:
                    result = cli.statusquery(files, match, False,
                                            clean, unknown)
                except QueryFailed, instr:
                    ui.debug(str(instr))
                    pass
                else:
                    if ui.config('inotify', 'debug'):
                        r2 = super(inotifydirstate, self).status(
                            match, False, clean, unknown)
                        for c,a,b in zip('LMARDUIC', result, r2):
                            for f in a:
                                if f not in b:
                                    ui.warn('*** inotify: %s +%s\n' % (c, f))
                            for f in b:
                                if f not in a:
                                    ui.warn('*** inotify: %s -%s\n' % (c, f))
                        result = r2
                    return result
            return super(inotifydirstate, self).status(
                match, ignored, clean, unknown)

    repo.dirstate.__class__ = inotifydirstate

cmdtable = {
    '^inserve':
    (serve,
     [('d', 'daemon', None, _('run server in background')),
      ('', 'daemon-pipefds', '', _('used internally by daemon mode')),
      ('t', 'idle-timeout', '', _('minutes to sit idle before exiting')),
      ('', 'pid-file', '', _('name of file to write process ID to'))],
     _('hg inserve [OPT]...')),
    }
