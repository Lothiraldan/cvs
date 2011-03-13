"""automatically manage newlines in repository files

This extension allows you to manage the type of line endings (CRLF or
LF) that are used in the repository and in the local working
directory. That way you can get CRLF line endings on Windows and LF on
Unix/Mac, thereby letting everybody use their OS native line endings.

The extension reads its configuration from a versioned ``.hgeol``
configuration file found in the root of the working copy. The
``.hgeol`` file use the same syntax as all other Mercurial
configuration files. It uses two sections, ``[patterns]`` and
``[repository]``.

The ``[patterns]`` section specifies how line endings should be
converted between the working copy and the repository. The format is
specified by a file pattern. The first match is used, so put more
specific patterns first. The available line endings are ``LF``,
``CRLF``, and ``BIN``.

Files with the declared format of ``CRLF`` or ``LF`` are always
checked out and stored in the repository in that format and files
declared to be binary (``BIN``) are left unchanged. Additionally,
``native`` is an alias for checking out in the platform's default line
ending: ``LF`` on Unix (including Mac OS X) and ``CRLF`` on
Windows. Note that ``BIN`` (do nothing to line endings) is Mercurial's
default behaviour; it is only needed if you need to override a later,
more general pattern.

The optional ``[repository]`` section specifies the line endings to
use for files stored in the repository. It has a single setting,
``native``, which determines the storage line endings for files
declared as ``native`` in the ``[patterns]`` section. It can be set to
``LF`` or ``CRLF``. The default is ``LF``. For example, this means
that on Windows, files configured as ``native`` (``CRLF`` by default)
will be converted to ``LF`` when stored in the repository. Files
declared as ``LF``, ``CRLF``, or ``BIN`` in the ``[patterns]`` section
are always stored as-is in the repository.

Example versioned ``.hgeol`` file::

  [patterns]
  **.py = native
  **.vcproj = CRLF
  **.txt = native
  Makefile = LF
  **.jpg = BIN

  [repository]
  native = LF

.. note::
   The rules will first apply when files are touched in the working
   copy, e.g. by updating to null and back to tip to touch all files.

The extension uses an optional ``[eol]`` section in your hgrc file
(not the ``.hgeol`` file) for settings that control the overall
behavior. There are two settings:

- ``eol.native`` (default ``os.linesep``) can be set to ``LF`` or
  ``CRLF`` to override the default interpretation of ``native`` for
  checkout. This can be used with :hg:`archive` on Unix, say, to
  generate an archive where files have line endings for Windows.

- ``eol.only-consistent`` (default True) can be set to False to make
  the extension convert files with inconsistent EOLs. Inconsistent
  means that there is both ``CRLF`` and ``LF`` present in the file.
  Such files are normally not touched under the assumption that they
  have mixed EOLs on purpose.

The extension provides ``cleverencode:`` and ``cleverdecode:`` filters
like the deprecated win32text extension does. This means that you can
disable win32text and enable eol and your filters will still work. You
only need to these filters until you have prepared a ``.hgeol`` file.

The ``win32text.forbid*`` hooks provided by the win32text extension
have been unified into a single hook named ``eol.hook``. The hook will
lookup the expected line endings from the ``.hgeol`` file, which means
you must migrate to a ``.hgeol`` file first before using the hook.

See :hg:`help patterns` for more information about the glob patterns
used.
"""

from mercurial.i18n import _
from mercurial import util, config, extensions, match, error
import re, os

# Matches a lone LF, i.e., one that is not part of CRLF.
singlelf = re.compile('(^|[^\r])\n')
# Matches a single EOL which can either be a CRLF where repeated CR
# are removed or a LF. We do not care about old Machintosh files, so a
# stray CR is an error.
eolre = re.compile('\r*\n')


def inconsistenteol(data):
    return '\r\n' in data and singlelf.search(data)

def tolf(s, params, ui, **kwargs):
    """Filter to convert to LF EOLs."""
    if util.binary(s):
        return s
    if ui.configbool('eol', 'only-consistent', True) and inconsistenteol(s):
        return s
    return eolre.sub('\n', s)

def tocrlf(s, params, ui, **kwargs):
    """Filter to convert to CRLF EOLs."""
    if util.binary(s):
        return s
    if ui.configbool('eol', 'only-consistent', True) and inconsistenteol(s):
        return s
    return eolre.sub('\r\n', s)

def isbinary(s, params):
    """Filter to do nothing with the file."""
    return s

filters = {
    'to-lf': tolf,
    'to-crlf': tocrlf,
    'is-binary': isbinary,
    # The following provide backwards compatibility with win32text
    'cleverencode:': tolf,
    'cleverdecode:': tocrlf
}

class eolfile(object):
    def __init__(self, ui, root, data):
        self._decode = {'LF': 'to-lf', 'CRLF': 'to-crlf', 'BIN': 'is-binary'}
        self._encode = {'LF': 'to-lf', 'CRLF': 'to-crlf', 'BIN': 'is-binary'}

        self.cfg = config.config()
        # Our files should not be touched. The pattern must be
        # inserted first override a '** = native' pattern.
        self.cfg.set('patterns', '.hg*', 'BIN')
        # We can then parse the user's patterns.
        self.cfg.parse('.hgeol', data)

        isrepolf = self.cfg.get('repository', 'native') != 'CRLF'
        self._encode['NATIVE'] = isrepolf and 'to-lf' or 'to-crlf'
        iswdlf = ui.config('eol', 'native', os.linesep) in ('LF', '\n')
        self._decode['NATIVE'] = iswdlf and 'to-lf' or 'to-crlf'

        include = []
        exclude = []
        for pattern, style in self.cfg.items('patterns'):
            key = style.upper()
            if key == 'BIN':
                exclude.append(pattern)
            else:
                include.append(pattern)
        # This will match the files for which we need to care
        # about inconsistent newlines.
        self.match = match.match(root, '', [], include, exclude)

    def setfilters(self, ui):
        for pattern, style in self.cfg.items('patterns'):
            key = style.upper()
            try:
                ui.setconfig('decode', pattern, self._decode[key])
                ui.setconfig('encode', pattern, self._encode[key])
            except KeyError:
                ui.warn(_("ignoring unknown EOL style '%s' from %s\n")
                        % (style, self.cfg.source('patterns', pattern)))

    def checkrev(self, repo, ctx, files):
        for f in files:
            if f not in ctx:
                continue
            for pattern, style in self.cfg.items('patterns'):
                if not match.match(repo.root, '', [pattern])(f):
                    continue
                target = self._encode[style.upper()]
                data = ctx[f].data()
                if target == "to-lf" and "\r\n" in data:
                    raise util.Abort(_("%s should not have CRLF line endings")
                                     % f)
                elif target == "to-crlf" and singlelf.search(data):
                    raise util.Abort(_("%s should not have LF line endings")
                                     % f)
                # Ignore other rules for this file
                break

def parseeol(ui, repo, nodes):
    try:
        for node in nodes:
            try:
                if node is None:
                    # Cannot use workingctx.data() since it would load
                    # and cache the filters before we configure them.
                    data = repo.wfile('.hgeol').read()
                else:
                    data = repo[node]['.hgeol'].data()
                return eolfile(ui, repo.root, data)
            except (IOError, LookupError):
                pass
    except error.ParseError, inst:
        ui.warn(_("warning: ignoring .hgeol file due to parse error "
                  "at %s: %s\n") % (inst.args[1], inst.args[0]))
    return None

def hook(ui, repo, node, hooktype, **kwargs):
    """verify that files have expected EOLs"""
    files = set()
    for rev in xrange(repo[node].rev(), len(repo)):
        files.update(repo[rev].files())
    tip = repo['tip']
    eol = parseeol(ui, repo, [tip.node()])
    if eol:
        eol.checkrev(repo, tip, files)

def preupdate(ui, repo, hooktype, parent1, parent2):
    #print "preupdate for %s: %s -> %s" % (repo.root, parent1, parent2)
    repo.loadeol([parent1])
    return False

def uisetup(ui):
    ui.setconfig('hooks', 'preupdate.eol', preupdate)

def extsetup(ui):
    try:
        extensions.find('win32text')
        raise util.Abort(_("the eol extension is incompatible with the "
                           "win32text extension"))
    except KeyError:
        pass


def reposetup(ui, repo):
    uisetup(repo.ui)
    #print "reposetup for", repo.root

    if not repo.local():
        return
    for name, fn in filters.iteritems():
        repo.adddatafilter(name, fn)

    ui.setconfig('patch', 'eol', 'auto')

    class eolrepo(repo.__class__):

        def loadeol(self, nodes):
            eol = parseeol(self.ui, self, nodes)
            if eol is None:
                return None
            eol.setfilters(self.ui)
            return eol.match

        def _hgcleardirstate(self):
            self._eolfile = self.loadeol([None, 'tip'])
            if not self._eolfile:
                self._eolfile = util.never
                return

            try:
                cachemtime = os.path.getmtime(self.join("eol.cache"))
            except OSError:
                cachemtime = 0

            try:
                eolmtime = os.path.getmtime(self.wjoin(".hgeol"))
            except OSError:
                eolmtime = 0

            if eolmtime > cachemtime:
                ui.debug("eol: detected change in .hgeol\n")
                wlock = None
                try:
                    wlock = self.wlock()
                    for f in self.dirstate:
                        if self.dirstate[f] == 'n':
                            # all normal files need to be looked at
                            # again since the new .hgeol file might no
                            # longer match a file it matched before
                            self.dirstate.normallookup(f)
                    # Touch the cache to update mtime.
                    self.opener("eol.cache", "w").close()
                    wlock.release()
                except error.LockUnavailable:
                    # If we cannot lock the repository and clear the
                    # dirstate, then a commit might not see all files
                    # as modified. But if we cannot lock the
                    # repository, then we can also not make a commit,
                    # so ignore the error.
                    pass

        def commitctx(self, ctx, error=False):
            for f in sorted(ctx.added() + ctx.modified()):
                if not self._eolfile(f):
                    continue
                data = ctx[f].data()
                if util.binary(data):
                    # We should not abort here, since the user should
                    # be able to say "** = native" to automatically
                    # have all non-binary files taken care of.
                    continue
                if inconsistenteol(data):
                    raise util.Abort(_("inconsistent newline style "
                                       "in %s\n" % f))
            return super(eolrepo, self).commitctx(ctx, error)
    repo.__class__ = eolrepo
    repo._hgcleardirstate()
