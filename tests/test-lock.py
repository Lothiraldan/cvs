from __future__ import absolute_import

import os
import silenttestrunner
import tempfile
import unittest

from mercurial import (
    lock,
    scmutil,
)

testlockname = 'testlock'

class teststate(object):
    def __init__(self, testcase):
        self._testcase = testcase
        self._acquirecalled = False
        self._releasecalled = False
        self._postreleasecalled = False
        d = tempfile.mkdtemp(dir=os.getcwd())
        self.vfs = scmutil.vfs(d, audit=False)

    def makelock(self, *args, **kwargs):
        l = lock.lock(self.vfs, testlockname, releasefn=self.releasefn,
                      acquirefn=self.acquirefn, *args, **kwargs)
        l.postrelease.append(self.postreleasefn)
        return l

    def acquirefn(self):
        self._acquirecalled = True

    def releasefn(self):
        self._releasecalled = True

    def postreleasefn(self):
        self._postreleasecalled = True

    def assertacquirecalled(self, called):
        self._testcase.assertEqual(
            self._acquirecalled, called,
            'expected acquire to be %s but was actually %s' % (
                self._tocalled(called),
                self._tocalled(self._acquirecalled),
            ))

    def resetacquirefn(self):
        self._acquirecalled = False

    def assertreleasecalled(self, called):
        self._testcase.assertEqual(
            self._releasecalled, called,
            'expected release to be %s but was actually %s' % (
                self._tocalled(called),
                self._tocalled(self._releasecalled),
            ))

    def assertpostreleasecalled(self, called):
        self._testcase.assertEqual(
            self._postreleasecalled, called,
            'expected postrelease to be %s but was actually %s' % (
                self._tocalled(called),
                self._tocalled(self._postreleasecalled),
            ))

    def assertlockexists(self, exists):
        actual = self.vfs.lexists(testlockname)
        self._testcase.assertEqual(
            actual, exists,
            'expected lock to %s but actually did %s' % (
                self._toexists(exists),
                self._toexists(actual),
            ))

    def _tocalled(self, called):
        if called:
            return 'called'
        else:
            return 'not called'

    def _toexists(self, exists):
        if exists:
            return 'exists'
        else:
            return 'not exists'

class testlock(unittest.TestCase):
    def testlock(self):
        state = teststate(self)
        lock = state.makelock()
        state.assertacquirecalled(True)
        lock.release()
        state.assertreleasecalled(True)
        state.assertpostreleasecalled(True)
        state.assertlockexists(False)

    def testrecursivelock(self):
        state = teststate(self)
        lock = state.makelock()
        state.assertacquirecalled(True)

        state.resetacquirefn()
        lock.lock()
        # recursive lock should not call acquirefn again
        state.assertacquirecalled(False)

        lock.release() # brings lock refcount down from 2 to 1
        state.assertreleasecalled(False)
        state.assertpostreleasecalled(False)
        state.assertlockexists(True)

        lock.release() # releases the lock
        state.assertreleasecalled(True)
        state.assertpostreleasecalled(True)
        state.assertlockexists(False)

    def testlockfork(self):
        state = teststate(self)
        lock = state.makelock()
        state.assertacquirecalled(True)
        lock.lock()
        # fake a fork
        lock.pid += 1
        lock.release()
        state.assertreleasecalled(False)
        state.assertpostreleasecalled(False)
        state.assertlockexists(True)

        # release the actual lock
        lock.pid -= 1
        lock.release()
        state.assertreleasecalled(True)
        state.assertpostreleasecalled(True)
        state.assertlockexists(False)

if __name__ == '__main__':
    silenttestrunner.main(__name__)
