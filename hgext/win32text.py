# win32text.py - LF <-> CRLF/CR translation utilities for Windows/Mac users
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.
#
# To perform automatic newline conversion, use:
#
# [extensions]
# hgext.win32text =
# [encode]
# ** = cleverencode:
# # or ** = macencode:
# [decode]
# ** = cleverdecode:
# # or ** = macdecode:
#
# If not doing conversion, to make sure you do not commit CRLF/CR by accident:
#
# [hooks]
# pretxncommit.crlf = python:hgext.win32text.forbidcrlf
# # or pretxncommit.cr = python:hgext.win32text.forbidcr
#
# To do the same check on a server to prevent CRLF/CR from being pushed or
# pulled:
#
# [hooks]
# pretxnchangegroup.crlf = python:hgext.win32text.forbidcrlf
# # or pretxnchangegroup.cr = python:hgext.win32text.forbidcr

from mercurial import util
from mercurial.i18n import gettext as _
from mercurial.node import bin, short
import re

# regexp for single LF without CR preceding.
re_single_lf = re.compile('(^|[^\r])\n', re.MULTILINE)

newlinestr = {'\r\n': 'CRLF', '\r': 'CR'}
filterstr = {'\r\n': 'clever', '\r': 'mac'}

def checknewline(s, newline, ui=None, repo=None, filename=None):
    # warn if already has 'newline' in repository.
    # it might cause unexpected eol conversion.
    # see issue 302:
    #   http://www.selenic.com/mercurial/bts/issue302
    if newline in s and ui and filename and repo:
        ui.warn(_('WARNING: %s already has %s line endings\n'
                  'and does not need EOL conversion by the win32text plugin.\n'
                  'Before your next commit, please reconsider your '
                  'encode/decode settings in \nMercurial.ini or %s.\n') %
                (filename, newlinestr[newline], repo.join('hgrc')))

def dumbdecode(s, cmd, **kwargs):
    checknewline(s, '\r\n', **kwargs)
    # replace single LF to CRLF
    return re_single_lf.sub('\\1\r\n', s)

def dumbencode(s, cmd):
    return s.replace('\r\n', '\n')

def macdumbdecode(s, cmd, **kwargs):
    checknewline(s, '\r', **kwargs)
    return s.replace('\n', '\r')

def macdumbencode(s, cmd):
    return s.replace('\r', '\n')

def cleverdecode(s, cmd, **kwargs):
    if util.binary(s):
        return s
    return dumbdecode(s, cmd, **kwargs)

def cleverencode(s, cmd):
    if util.binary(s):
        return s
    return dumbencode(s, cmd)

def macdecode(s, cmd, **kwargs):
    if util.binary(s):
        return s
    return macdumbdecode(s, cmd, **kwargs)

def macencode(s, cmd):
    if util.binary(s):
        return s
    return macdumbencode(s, cmd)

_filters = {
    'dumbdecode:': dumbdecode,
    'dumbencode:': dumbencode,
    'cleverdecode:': cleverdecode,
    'cleverencode:': cleverencode,
    'macdumbdecode:': macdumbdecode,
    'macdumbencode:': macdumbencode,
    'macdecode:': macdecode,
    'macencode:': macencode,
    }

def forbidcrlforcr(ui, repo, hooktype, node, newline, **kwargs):
    halt = False
    for rev in xrange(repo.changelog.rev(bin(node)), repo.changelog.count()):
        c = repo.changectx(rev)
        for f in c.files():
            if f not in c:
                continue
            data = c[f].data()
            if not util.binary(data) and newline in data:
                if not halt:
                    ui.warn(_('Attempt to commit or push text file(s) '
                              'using %s line endings\n') %
                              newlinestr[newline])
                ui.warn(_('in %s: %s\n') % (short(c.node()), f))
                halt = True
    if halt and hooktype == 'pretxnchangegroup':
        crlf = newlinestr[newline].lower()
        filter = filterstr[newline]
        ui.warn(_('\nTo prevent this mistake in your local repository,\n'
                  'add to Mercurial.ini or .hg/hgrc:\n'
                  '\n'
                  '[hooks]\n'
                  'pretxncommit.%s = python:hgext.win32text.forbid%s\n'
                  '\n'
                  'and also consider adding:\n'
                  '\n'
                  '[extensions]\n'
                  'hgext.win32text =\n'
                  '[encode]\n'
                  '** = %sencode:\n'
                  '[decode]\n'
                  '** = %sdecode:\n') % (crlf, crlf, filter, filter))
    return halt

def forbidcrlf(ui, repo, hooktype, node, **kwargs):
    return forbidcrlforcr(ui, repo, hooktype, node, '\r\n', **kwargs)

def forbidcr(ui, repo, hooktype, node, **kwargs):
    return forbidcrlforcr(ui, repo, hooktype, node, '\r', **kwargs)

def reposetup(ui, repo):
    if not repo.local():
        return
    for name, fn in _filters.iteritems():
        repo.adddatafilter(name, fn)

