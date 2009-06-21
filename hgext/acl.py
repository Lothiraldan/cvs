# acl.py - changeset access control for mercurial
#
# Copyright 2006 Vadim Gelfer <vadim.gelfer@gmail.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2, incorporated herein by reference.
#

'''provide simple hooks for access control

Authorization is against local user name on system where hook is run, not
committer of original changeset (since that is easy to spoof).

The acl hook is best to use if you use hgsh to set up restricted shells for
authenticated users to only push to / pull from. It's not safe if user has
interactive shell access, because they can disable the hook. It's also not
safe if remote users share one local account, because then there's no way to
tell remote users apart.

To use, configure the acl extension in hgrc like this:

  [extensions]
  hgext.acl =

  [hooks]
  pretxnchangegroup.acl = python:hgext.acl.hook

  [acl]
  sources = serve        # check if source of incoming changes in this list
                         # ("serve" == ssh or http, "push", "pull", "bundle")

Allow and deny lists have a subtree pattern (default syntax is glob) on the
left and user names on right. The deny list is checked before the allow list.

  [acl.allow]
  # if acl.allow not present, all users allowed by default
  # empty acl.allow = no users allowed
  docs/** = doc_writer
  .hgtags = release_engineer

  [acl.deny]
  # if acl.deny not present, no users denied by default
  # empty acl.deny = all users allowed
  glob pattern = user4, user5
   ** = user6
'''

from mercurial.i18n import _
from mercurial import util, match
import getpass, urllib

def buildmatch(ui, repo, user, key):
    '''return tuple of (match function, list enabled).'''
    if not ui.has_section(key):
        ui.debug(_('acl: %s not enabled\n') % key)
        return None

    pats = [pat for pat, users in ui.configitems(key)
            if user in users.replace(',', ' ').split()]
    ui.debug(_('acl: %s enabled, %d entries for user %s\n') %
             (key, len(pats), user))
    if pats:
        return match.match(repo.root, '', pats)
    return match.exact(repo.root, '', [])


def hook(ui, repo, hooktype, node=None, source=None, **kwargs):
    if hooktype != 'pretxnchangegroup':
        raise util.Abort(_('config error - hook type "%s" cannot stop '
                           'incoming changesets') % hooktype)
    if source not in ui.config('acl', 'sources', 'serve').split():
        ui.debug(_('acl: changes have source "%s" - skipping\n') % source)
        return

    user = None
    if source == 'serve' and 'url' in kwargs:
        url = kwargs['url'].split(':')
        if url[0] == 'remote' and url[1].startswith('http'):
            user = urllib.unquote(url[2])

    if user is None:
        user = getpass.getuser()

    cfg = ui.config('acl', 'config')
    if cfg:
        ui.readconfig(cfg, sections = ['acl.allow', 'acl.deny'])
    allow = buildmatch(ui, repo, user, 'acl.allow')
    deny = buildmatch(ui, repo, user, 'acl.deny')

    for rev in xrange(repo[node], len(repo)):
        ctx = repo[rev]
        for f in ctx.files():
            if deny and deny(f):
                ui.debug(_('acl: user %s denied on %s\n') % (user, f))
                raise util.Abort(_('acl: access denied for changeset %s') % ctx)
            if allow and not allow(f):
                ui.debug(_('acl: user %s not allowed on %s\n') % (user, f))
                raise util.Abort(_('acl: access denied for changeset %s') % ctx)
        ui.debug(_('acl: allowing changeset %s\n') % ctx)
