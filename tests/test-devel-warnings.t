
  $ cat << EOF > buggylocking.py
  > """A small extension that acquire locks in the wrong order
  > """
  > 
  > from mercurial import cmdutil
  > 
  > cmdtable = {}
  > command = cmdutil.command(cmdtable)
  > 
  > @command('buggylocking', [], '')
  > def buggylocking(ui, repo):
  >     tr = repo.transaction('buggy')
  >     lo = repo.lock()
  >     wl = repo.wlock()
  >     wl.release()
  >     lo.release()
  > 
  > @command('properlocking', [], '')
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
  > EOF

  $ cat << EOF >> $HGRCPATH
  > [extensions]
  > buggylocking=$TESTTMP/buggylocking.py
  > [devel]
  > all=1
  > EOF

  $ hg init lock-checker
  $ cd lock-checker
  $ hg buggylocking
  transaction with no lock at: $TESTTMP/buggylocking.py:11 (buggylocking)
  "wlock" acquired after "lock" at: $TESTTMP/buggylocking.py:13 (buggylocking)
  $ cat << EOF >> $HGRCPATH
  > [devel]
  > all=0
  > check-locks=1
  > EOF
  $ hg buggylocking
  transaction with no lock at: $TESTTMP/buggylocking.py:11 (buggylocking)
  "wlock" acquired after "lock" at: $TESTTMP/buggylocking.py:13 (buggylocking)
  $ hg buggylocking --traceback
  transaction with no lock at:
   */hg:* in * (glob)
   */mercurial/dispatch.py:* in run (glob)
   */mercurial/dispatch.py:* in dispatch (glob)
   */mercurial/dispatch.py:* in _runcatch (glob)
   */mercurial/dispatch.py:* in _dispatch (glob)
   */mercurial/dispatch.py:* in runcommand (glob)
   */mercurial/dispatch.py:* in _runcommand (glob)
   */mercurial/dispatch.py:* in checkargs (glob)
   */mercurial/dispatch.py:* in <lambda> (glob)
   */mercurial/util.py:* in check (glob)
   $TESTTMP/buggylocking.py:* in buggylocking (glob)
  "wlock" acquired after "lock" at:
   */hg:* in * (glob)
   */mercurial/dispatch.py:* in run (glob)
   */mercurial/dispatch.py:* in dispatch (glob)
   */mercurial/dispatch.py:* in _runcatch (glob)
   */mercurial/dispatch.py:* in _dispatch (glob)
   */mercurial/dispatch.py:* in runcommand (glob)
   */mercurial/dispatch.py:* in _runcommand (glob)
   */mercurial/dispatch.py:* in checkargs (glob)
   */mercurial/dispatch.py:* in <lambda> (glob)
   */mercurial/util.py:* in check (glob)
   $TESTTMP/buggylocking.py:* in buggylocking (glob)
  $ hg properlocking
  $ cd ..
