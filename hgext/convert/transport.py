# -*- coding: utf-8 -*-

# Copyright (C) 2007 Daniel Holth <dholth@fastmail.fm>
# This is a stripped-down version of the original bzr-svn transport.py,
# Copyright (C) 2006 Jelmer Vernooij <jelmer@samba.org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from cStringIO import StringIO
import os
from tempfile import mktemp

from svn.core import SubversionException, Pool
import svn.ra
import svn.core

# Some older versions of the Python bindings need to be 
# explicitly initialized. But what we want to do probably
# won't work worth a darn against those libraries anyway!
svn.ra.initialize()

svn_config = svn.core.svn_config_get_config(None)


def _create_auth_baton(pool):
    """Create a Subversion authentication baton. """
    import svn.client
    # Give the client context baton a suite of authentication
    # providers.h
    providers = [
        svn.client.get_simple_provider(pool),
        svn.client.get_username_provider(pool),
        svn.client.get_ssl_client_cert_file_provider(pool),
        svn.client.get_ssl_client_cert_pw_file_provider(pool),
        svn.client.get_ssl_server_trust_file_provider(pool),
        ]
    return svn.core.svn_auth_open(providers, pool)


#    # The SVN libraries don't like trailing slashes...
#    return url.rstrip('/')


class SvnRaCallbacks(svn.ra.callbacks2_t):
    """Remote access callbacks implementation for bzr-svn."""
    def __init__(self, pool):
        svn.ra.callbacks2_t.__init__(self)
        self.auth_baton = _create_auth_baton(pool)
        self.pool = pool
    
    def open_tmp_file(self, pool):
        return mktemp(prefix='tailor-svn')

class NotBranchError(SubversionException):
    pass

class SvnRaTransport(object):
    """
    Open an ra connection to a Subversion repository.
    """
    def __init__(self, url="", ra=None):
        self.pool = Pool()
        self.svn_url = url

        # Only Subversion 1.4 has reparent()
        if ra is None or not hasattr(svn.ra, 'reparent'):
            self.callbacks = SvnRaCallbacks(self.pool)
            try:
                ver = svn.ra.version()
                try: # Older SVN bindings
                    self.ra = svn.ra.open2(self.svn_url.encode('utf8'), self.callbacks, None, svn_config, None)
                except TypeError, e:
                    self.ra = svn.ra.open2(self.svn_url.encode('utf8'), self.callbacks, svn_config, None)
            except SubversionException, (_, num):
                if num == svn.core.SVN_ERR_RA_ILLEGAL_URL:
                    raise NotBranchError(url)
                if num == svn.core.SVN_ERR_RA_LOCAL_REPOS_OPEN_FAILED:
                    raise NotBranchError(url)
                if num == svn.core.SVN_ERR_BAD_URL:
                    raise NotBranchError(url)
                raise

        else:
            self.ra = ra
            svn.ra.reparent(self.ra, self.svn_url.encode('utf8'))

    class Reporter:
        def __init__(self, (reporter, report_baton)):
            self._reporter = reporter
            self._baton = report_baton

        def set_path(self, path, revnum, start_empty, lock_token, pool=None):
            svn.ra.reporter2_invoke_set_path(self._reporter, self._baton,
                        path, revnum, start_empty, lock_token, pool)

        def delete_path(self, path, pool=None):
            svn.ra.reporter2_invoke_delete_path(self._reporter, self._baton,
                    path, pool)

        def link_path(self, path, url, revision, start_empty, lock_token,
                      pool=None):
            svn.ra.reporter2_invoke_link_path(self._reporter, self._baton,
                    path, url, revision, start_empty, lock_token,
                    pool)

        def finish_report(self, pool=None):
            svn.ra.reporter2_invoke_finish_report(self._reporter,
                    self._baton, pool)

        def abort_report(self, pool=None):
            svn.ra.reporter2_invoke_abort_report(self._reporter,
                    self._baton, pool)

    def do_update(self, revnum, path, *args, **kwargs):
        return self.Reporter(svn.ra.do_update(self.ra, revnum, path, *args, **kwargs))

    def clone(self, offset=None):
        """See Transport.clone()."""
        if offset is None:
            return self.__class__(self.base)

        return SvnRaTransport(urlutils.join(self.base, offset), ra=self.ra)
