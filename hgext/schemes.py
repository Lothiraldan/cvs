# Copyright 2009, Alexander Solovyov <piranha@piranha.org.ua>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

"""extend schemes with shortcuts to repository swarms

This extension allows you to specify shortcuts for parent URLs with a
lot of repositories to act like a scheme, for example::

  [schemes]
  py = http://code.python.org/hg/

After that you can use it like::

  hg clone py://trunk/

Additionally there is support for some more complex schemas, for
example used by Google Code::

  [schemes]
  gcode = http://{1}.googlecode.com/hg/

The syntax is taken from Mercurial templates, and you have unlimited
number of variables, starting with ``{1}`` and continuing with
``{2}``, ``{3}`` and so on. This variables will receive parts of URL
supplied, split by ``/``. Anything not specified as ``{part}`` will be
just appended to an URL.

For convenience, the extension adds these schemes by default::

  [schemes]
  py = http://hg.python.org/
  bb = https://bitbucket.org/
  bb+ssh = ssh://hg@bitbucket.org/
  gcode = https://{1}.googlecode.com/hg/
  kiln = https://{1}.kilnhg.com/Repo/

You can override a predefined scheme by defining a new scheme with the
same name.
"""
from __future__ import absolute_import

import os
import re

from mercurial.i18n import _
from mercurial import (
    error,
    extensions,
    hg,
    pycompat,
    registrar,
    templater,
    util,
)

cmdtable = {}
command = registrar.command(cmdtable)
# Note for extension authors: ONLY specify testedwith = 'ships-with-hg-core' for
# extensions which SHIP WITH MERCURIAL. Non-mainline extensions should
# be specifying the version(s) of Mercurial they are tested with, or
# leave the attribute unspecified.
testedwith = 'ships-with-hg-core'

_partre = re.compile(br'\{(\d+)\}')

class ShortRepository(object):
    def __init__(self, url, scheme, templater):
        self.scheme = scheme
        self.templater = templater
        self.url = url
        try:
            self.parts = max(map(int, _partre.findall(self.url)))
        except ValueError:
            self.parts = 0

    def __repr__(self):
        return '<ShortRepository: %s>' % self.scheme

    def instance(self, ui, url, create):
        url = self.resolve(url)
        return hg._peerlookup(url).instance(ui, url, create)

    def resolve(self, url):
        # Should this use the util.url class, or is manual parsing better?
        try:
            url = url.split('://', 1)[1]
        except IndexError:
            raise error.Abort(_("no '://' in scheme url '%s'") % url)
        parts = url.split('/', self.parts)
        if len(parts) > self.parts:
            tail = parts[-1]
            parts = parts[:-1]
        else:
            tail = ''
        context = dict((str(i + 1), v) for i, v in enumerate(parts))
        return ''.join(self.templater.process(self.url, context)) + tail

def hasdriveletter(orig, path):
    if path:
        for scheme in schemes:
            if path.startswith(scheme + ':'):
                return False
    return orig(path)

schemes = {
    'py': 'http://hg.python.org/',
    'bb': 'https://bitbucket.org/',
    'bb+ssh': 'ssh://hg@bitbucket.org/',
    'gcode': 'https://{1}.googlecode.com/hg/',
    'kiln': 'https://{1}.kilnhg.com/Repo/'
    }

def extsetup(ui):
    schemes.update(dict(ui.configitems('schemes')))
    t = templater.engine(lambda x: x)
    for scheme, url in schemes.items():
        if (pycompat.osname == 'nt' and len(scheme) == 1 and scheme.isalpha()
            and os.path.exists('%s:\\' % scheme)):
            raise error.Abort(_('custom scheme %s:// conflicts with drive '
                               'letter %s:\\\n') % (scheme, scheme.upper()))
        hg.schemes[scheme] = ShortRepository(url, scheme, t)

    extensions.wrapfunction(util, 'hasdriveletter', hasdriveletter)

@command('debugexpandscheme', norepo=True)
def expandscheme(ui, url, **opts):
    """given a repo path, provide the scheme-expanded path
    """
    repo = hg._peerlookup(url)
    if isinstance(repo, ShortRepository):
        url = repo.resolve(url)
    ui.write(url + '\n')
