
  $ cat << EOF > buggylocking.py
  > """A small extension that tests our developer warnings
  > """
  > 
  > from mercurial import error, registrar, repair, util
  > 
  > cmdtable = {}
  > command = registrar.command(cmdtable)
  > 
  > @command(b'buggylocking', [], '')
  > def buggylocking(ui, repo):
  >     lo = repo.lock()
  >     wl = repo.wlock()
  >     wl.release()
  >     lo.release()
  > 
  > @command(b'buggytransaction', [], '')
  > def buggylocking(ui, repo):
  >     tr = repo.transaction('buggy')
  >     # make sure we rollback the transaction as we don't want to rely on the__del__
  >     tr.release()
  > 
  > @command(b'properlocking', [], '')
  > def properlocking(ui, repo):
  >     """check that reentrance is fine"""
  >     wl = repo.wlock()
  >     lo = repo.lock()
  >     tr = repo.transaction('proper')
  >     tr2 = repo.transaction('proper')
  >     lo2 = repo.lock()
  >     wl2 = repo.wlock()
  >     wl2.release()
  >     lo2.release()
  >     tr2.close()
  >     tr.close()
  >     lo.release()
  >     wl.release()
  > 
  > @command(b'nowaitlocking', [], '')
  > def nowaitlocking(ui, repo):
  >     lo = repo.lock()
  >     wl = repo.wlock(wait=False)
  >     wl.release()
  >     lo.release()
  > 
  > @command(b'no-wlock-write', [], '')
  > def nowlockwrite(ui, repo):
  >     with repo.vfs(b'branch', 'a'):
  >         pass
  > 
  > @command(b'stripintr', [], '')
  > def stripintr(ui, repo):
  >     lo = repo.lock()
  >     tr = repo.transaction('foobar')
  >     try:
  >         repair.strip(repo.ui, repo, [repo['.'].node()])
  >     finally:
  >         lo.release()
  > @command(b'oldanddeprecated', [], '')
  > def oldanddeprecated(ui, repo):
  >     """test deprecation warning API"""
  >     def foobar(ui):
  >         ui.deprecwarn('foorbar is deprecated, go shopping', '42.1337')
  >     foobar(ui)
  > @command(b'nouiwarning', [], '')
  > def nouiwarning(ui, repo):
  >     util.nouideprecwarn('this is a test', '13.37')
  > @command(b'programmingerror', [], '')
  > def programmingerror(ui, repo):
  >     raise error.ProgrammingError('something went wrong', hint='try again')
  > EOF

  $ cat << EOF >> $HGRCPATH
  > [extensions]
  > buggylocking=$TESTTMP/buggylocking.py
  > mock=$TESTDIR/mockblackbox.py
  > blackbox=
  > [devel]
  > all-warnings=1
  > EOF

  $ hg init lock-checker
  $ cd lock-checker
  $ hg buggylocking
  devel-warn: "wlock" acquired after "lock" at: $TESTTMP/buggylocking.py:* (buggylocking) (glob)
  $ cat << EOF >> $HGRCPATH
  > [devel]
  > all=0
  > check-locks=1
  > EOF
  $ hg buggylocking
  devel-warn: "wlock" acquired after "lock" at: $TESTTMP/buggylocking.py:* (buggylocking) (glob)
  $ hg buggylocking --traceback
  devel-warn: "wlock" acquired after "lock" at:
   */hg:* in * (glob)
   */mercurial/dispatch.py:* in run (glob)
   */mercurial/dispatch.py:* in dispatch (glob)
   */mercurial/dispatch.py:* in _runcatch (glob)
   */mercurial/dispatch.py:* in _callcatch (glob)
   */mercurial/scmutil.py* in callcatch (glob)
   */mercurial/dispatch.py:* in _runcatchfunc (glob)
   */mercurial/dispatch.py:* in _dispatch (glob)
   */mercurial/dispatch.py:* in runcommand (glob)
   */mercurial/dispatch.py:* in _runcommand (glob)
   */mercurial/dispatch.py:* in <lambda> (glob)
   */mercurial/util.py:* in check (glob)
   $TESTTMP/buggylocking.py:* in buggylocking (glob)
  $ hg properlocking
  $ hg nowaitlocking

Writing without lock

  $ hg no-wlock-write
  devel-warn: write with no wlock: "branch" at: $TESTTMP/buggylocking.py:* (nowlockwrite) (glob)

Stripping from a transaction

  $ echo a > a
  $ hg add a
  $ hg commit -m a
  $ hg stripintr 2>&1 | egrep -v '^(\*\*|  )'
  Traceback (most recent call last):
  mercurial.error.ProgrammingError: cannot strip from inside a transaction

  $ hg oldanddeprecated
  devel-warn: foorbar is deprecated, go shopping
  (compatibility will be dropped after Mercurial-42.1337, update your code.) at: $TESTTMP/buggylocking.py:* (oldanddeprecated) (glob)

  $ hg oldanddeprecated --traceback
  devel-warn: foorbar is deprecated, go shopping
  (compatibility will be dropped after Mercurial-42.1337, update your code.) at:
   */hg:* in <module> (glob)
   */mercurial/dispatch.py:* in run (glob)
   */mercurial/dispatch.py:* in dispatch (glob)
   */mercurial/dispatch.py:* in _runcatch (glob)
   */mercurial/dispatch.py:* in _callcatch (glob)
   */mercurial/scmutil.py* in callcatch (glob)
   */mercurial/dispatch.py:* in _runcatchfunc (glob)
   */mercurial/dispatch.py:* in _dispatch (glob)
   */mercurial/dispatch.py:* in runcommand (glob)
   */mercurial/dispatch.py:* in _runcommand (glob)
   */mercurial/dispatch.py:* in <lambda> (glob)
   */mercurial/util.py:* in check (glob)
   $TESTTMP/buggylocking.py:* in oldanddeprecated (glob)
  $ hg blackbox -l 7
  1970/01/01 00:00:00 bob @cb9a9f314b8b07ba71012fcdbc544b5a4d82ff5b (5000)> oldanddeprecated
  1970/01/01 00:00:00 bob @cb9a9f314b8b07ba71012fcdbc544b5a4d82ff5b (5000)> devel-warn: foorbar is deprecated, go shopping
  (compatibility will be dropped after Mercurial-42.1337, update your code.) at: $TESTTMP/buggylocking.py:* (oldanddeprecated) (glob)
  1970/01/01 00:00:00 bob @cb9a9f314b8b07ba71012fcdbc544b5a4d82ff5b (5000)> oldanddeprecated exited 0 after * seconds (glob)
  1970/01/01 00:00:00 bob @cb9a9f314b8b07ba71012fcdbc544b5a4d82ff5b (5000)> oldanddeprecated --traceback
  1970/01/01 00:00:00 bob @cb9a9f314b8b07ba71012fcdbc544b5a4d82ff5b (5000)> devel-warn: foorbar is deprecated, go shopping
  (compatibility will be dropped after Mercurial-42.1337, update your code.) at:
   */hg:* in <module> (glob)
   */mercurial/dispatch.py:* in run (glob)
   */mercurial/dispatch.py:* in dispatch (glob)
   */mercurial/dispatch.py:* in _runcatch (glob)
   */mercurial/dispatch.py:* in _callcatch (glob)
   */mercurial/scmutil.py* in callcatch (glob)
   */mercurial/dispatch.py:* in _runcatchfunc (glob)
   */mercurial/dispatch.py:* in _dispatch (glob)
   */mercurial/dispatch.py:* in runcommand (glob)
   */mercurial/dispatch.py:* in _runcommand (glob)
   */mercurial/dispatch.py:* in <lambda> (glob)
   */mercurial/util.py:* in check (glob)
   $TESTTMP/buggylocking.py:* in oldanddeprecated (glob)
  1970/01/01 00:00:00 bob @cb9a9f314b8b07ba71012fcdbc544b5a4d82ff5b (5000)> oldanddeprecated --traceback exited 0 after * seconds (glob)
  1970/01/01 00:00:00 bob @cb9a9f314b8b07ba71012fcdbc544b5a4d82ff5b (5000)> blackbox -l 7

Test programming error failure:

  $ hg buggytransaction 2>&1 | egrep -v '^  '
  ** Unknown exception encountered with possibly-broken third-party extension buggylocking
  ** which supports versions unknown of Mercurial.
  ** Please disable buggylocking and try your action again.
  ** If that fixes the bug please report it to the extension author.
  ** Python * (glob)
  ** Mercurial Distributed SCM (*) (glob)
  ** Extensions loaded: * (glob)
  ** ProgrammingError: transaction requires locking
  Traceback (most recent call last):
  mercurial.error.ProgrammingError: transaction requires locking

  $ hg programmingerror 2>&1 | egrep -v '^  '
  ** Unknown exception encountered with possibly-broken third-party extension buggylocking
  ** which supports versions unknown of Mercurial.
  ** Please disable buggylocking and try your action again.
  ** If that fixes the bug please report it to the extension author.
  ** Python * (glob)
  ** Mercurial Distributed SCM (*) (glob)
  ** Extensions loaded: * (glob)
  ** ProgrammingError: something went wrong
  ** (try again)
  Traceback (most recent call last):
  mercurial.error.ProgrammingError: something went wrong

Old style deprecation warning

  $ hg nouiwarning
  $TESTTMP/buggylocking.py:*: DeprecationWarning: this is a test (glob)
  (compatibility will be dropped after Mercurial-13.37, update your code.)
    util.nouideprecwarn('this is a test', '13.37')

(disabled outside of test run)

  $ HGEMITWARNINGS= hg nouiwarning

Test warning on config option access and registration

  $ cat << EOF > ${TESTTMP}/buggyconfig.py
  > """A small extension that tests our developer warnings for config"""
  > 
  > from mercurial import registrar
  > 
  > cmdtable = {}
  > command = registrar.command(cmdtable)
  > 
  > configtable = {}
  > configitem = registrar.configitem(configtable)
  > 
  > configitem('test', 'some', default='foo')
  > # overwrite a core config
  > configitem('ui', 'quiet', default=False)
  > configitem('ui', 'interactive', default=None)
  > 
  > @command(b'buggyconfig')
  > def cmdbuggyconfig(ui, repo):
  >     repo.ui.config('ui', 'quiet', False)
  >     repo.ui.config('ui', 'interactive', None)
  >     repo.ui.config('test', 'some', 'foo')
  > EOF

  $ hg --config "extensions.buggyconfig=${TESTTMP}/buggyconfig.py" buggyconfig
  devel-warn: extension 'buggyconfig' overwrite config item 'ui.interactive' at: */mercurial/extensions.py:* (loadall) (glob)
  devel-warn: extension 'buggyconfig' overwrite config item 'ui.quiet' at: */mercurial/extensions.py:* (loadall) (glob)
  devel-warn: specifying a default value for a registered config item: 'ui.quiet' 'False' at: $TESTTMP/buggyconfig.py:* (cmdbuggyconfig) (glob)
  devel-warn: specifying a default value for a registered config item: 'ui.interactive' 'None' at: $TESTTMP/buggyconfig.py:* (cmdbuggyconfig) (glob)
  devel-warn: specifying a default value for a registered config item: 'test.some' 'foo' at: $TESTTMP/buggyconfig.py:* (cmdbuggyconfig) (glob)

  $ cd ..
