# repo.py - repository base classes for mercurial
#
# Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>
# Copyright 2006 Vadim Gelfer <vadim.gelfer@gmail.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from i18n import _

class RepoError(Exception):
    pass

class NoCapability(RepoError):
    pass

class repository(object):
    def capable(self, name):
        '''tell whether repo supports named capability.
        return False if not supported.
        if boolean capability, return True.
        if string capability, return string.'''
        if name in self.capabilities:
            return True
        name_eq = name + '='
        for cap in self.capabilities:
            if cap.startswith(name_eq):
                return cap[len(name_eq):]
        return False

    def requirecap(self, name, purpose):
        '''raise an exception if the given capability is not present'''
        if not self.capable(name):
            raise NoCapability(_('cannot %s; remote repository does not '
                                 'support the %r capability') %
                               (purpose, name))
