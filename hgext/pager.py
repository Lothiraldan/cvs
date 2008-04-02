# pager.py - display output using a pager
#
# Copyright 2008 David Soria Parra <dsp@php.net>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.
#
# To load the extension, add it to your .hgrc file:
#
#   [extension]
#   hgext.pager =
#
# To set the pager that should be used, set the application variable:
#
#   [pager]
#   pager = LESS='FSRX' less
#
# If no pager is set, the pager extensions uses the environment
# variable $PAGER. If neither pager.pager, nor $PAGER is set, no pager
# is used.
#
# If you notice "BROKEN PIPE" error messages, you can disable them
# by setting:
#
#   [pager]
#   quiet = True
#
# You can disable the pager for certain commands by adding them to the
# pager.ignore list:
#
#   [pager]
#   ignore = version, help, update
#
# You can also enable the pager only for certain commands using pager.attend:
#
#   [pager]
#   attend = log
#
# If pager.attend is present, pager.ignore will be ignored.
#
# To ignore global commands like 'hg version' or 'hg help', you have to specify them
# in the global .hgrc

import sys, os, signal
from mercurial import dispatch

def uisetup(ui):
    def pagecmd(ui, options, cmd, cmdfunc):
        p = ui.config("pager", "pager", os.environ.get("PAGER"))
        if p and sys.stdout.isatty():
            attend = ui.configlist('pager', 'attend')
            if (cmd in attend or
                (cmd not in ui.configlist('pager', 'ignore') and not attend)):
                sys.stderr = sys.stdout = os.popen(p, "wb")
                if ui.configbool('pager', 'quiet'):
                    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        return oldrun(ui, options, cmd, cmdfunc)

    oldrun = dispatch._runcommand
    dispatch._runcommand = pagecmd
