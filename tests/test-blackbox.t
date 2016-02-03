setup
  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > blackbox=
  > mock=$TESTDIR/mockblackbox.py
  > mq=
  > EOF
  $ hg init blackboxtest
  $ cd blackboxtest

command, exit codes, and duration

  $ echo a > a
  $ hg add a
  $ hg blackbox
  1970/01/01 00:00:00 bob (*)> add a (glob)
  1970/01/01 00:00:00 bob (*)> add a exited 0 after * seconds (glob)
  1970/01/01 00:00:00 bob (*)> blackbox (glob)

incoming change tracking

create two heads to verify that we only see one change in the log later
  $ hg commit -ma
  $ hg up null
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ echo b > b
  $ hg commit -Amb
  adding b
  created new head

clone, commit, pull
  $ hg clone . ../blackboxtest2
  updating to branch default
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo c > c
  $ hg commit -Amc
  adding c
  $ cd ../blackboxtest2
  $ hg pull
  pulling from $TESTTMP/blackboxtest (glob)
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files
  (run 'hg update' to get a working copy)
  $ hg blackbox -l 6
  1970/01/01 00:00:00 bob (*)> pull (glob)
  1970/01/01 00:00:00 bob (*)> updated served branch cache in * seconds (glob)
  1970/01/01 00:00:00 bob (*)> wrote served branch cache with 1 labels and 2 nodes (glob)
  1970/01/01 00:00:00 bob (*)> 1 incoming changes - new heads: d02f48003e62 (glob)
  1970/01/01 00:00:00 bob (*)> pull exited 0 after * seconds (glob)
  1970/01/01 00:00:00 bob (*)> blackbox -l 6 (glob)

we must not cause a failure if we cannot write to the log

  $ hg rollback
  repository tip rolled back to revision 1 (undo pull)

  $ mv .hg/blackbox.log .hg/blackbox.log-
  $ mkdir .hg/blackbox.log
  $ hg --debug incoming
  warning: cannot write to blackbox.log: * (glob)
  comparing with $TESTTMP/blackboxtest (glob)
  query 1; heads
  searching for changes
  all local heads known remotely
  changeset:   2:d02f48003e62c24e2659d97d30f2a83abe5d5d51
  tag:         tip
  phase:       draft
  parent:      1:6563da9dcf87b1949716e38ff3e3dfaa3198eb06
  parent:      -1:0000000000000000000000000000000000000000
  manifest:    2:ab9d46b053ebf45b7996f2922b9893ff4b63d892
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  files+:      c
  extra:       branch=default
  description:
  c
  
  
  $ hg pull
  pulling from $TESTTMP/blackboxtest (glob)
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files
  (run 'hg update' to get a working copy)

a failure reading from the log is fatal

  $ hg blackbox -l 3
  abort: *$TESTTMP/blackboxtest2/.hg/blackbox.log* (glob)
  [255]

  $ rmdir .hg/blackbox.log
  $ mv .hg/blackbox.log- .hg/blackbox.log

backup bundles get logged

  $ touch d
  $ hg commit -Amd
  adding d
  created new head
  $ hg strip tip
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/blackboxtest2/.hg/strip-backup/*-backup.hg (glob)
  $ hg blackbox -l 6
  1970/01/01 00:00:00 bob (*)> strip tip (glob)
  1970/01/01 00:00:00 bob (*)> saved backup bundle to $TESTTMP/blackboxtest2/.hg/strip-backup/*-backup.hg (glob)
  1970/01/01 00:00:00 bob (*)> updated base branch cache in * seconds (glob)
  1970/01/01 00:00:00 bob (*)> wrote base branch cache with 1 labels and 2 nodes (glob)
  1970/01/01 00:00:00 bob (*)> strip tip exited 0 after * seconds (glob)
  1970/01/01 00:00:00 bob (*)> blackbox -l 6 (glob)

extension and python hooks - use the eol extension for a pythonhook

  $ echo '[extensions]' >> .hg/hgrc
  $ echo 'eol=' >> .hg/hgrc
  $ echo '[hooks]' >> .hg/hgrc
  $ echo 'update = echo hooked' >> .hg/hgrc
  $ hg update
  hooked
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg blackbox -l 6
  1970/01/01 00:00:00 bob (*)> update (glob)
  1970/01/01 00:00:00 bob (*)> writing .hg/cache/tags2-visible with 0 tags (glob)
  1970/01/01 00:00:00 bob (*)> pythonhook-preupdate: hgext.eol.preupdate finished in * seconds (glob)
  1970/01/01 00:00:00 bob (*)> exthook-update: echo hooked finished in * seconds (glob)
  1970/01/01 00:00:00 bob (*)> update exited 0 after * seconds (glob)
  1970/01/01 00:00:00 bob (*)> blackbox -l 6 (glob)

log rotation

  $ echo '[blackbox]' >> .hg/hgrc
  $ echo 'maxsize = 20 b' >> .hg/hgrc
  $ echo 'maxfiles = 3' >> .hg/hgrc
  $ hg status
  $ hg status
  $ hg status
  $ hg tip -q
  2:d02f48003e62
  $ ls .hg/blackbox.log*
  .hg/blackbox.log
  .hg/blackbox.log.1
  .hg/blackbox.log.2
  $ cd ..

  $ hg init blackboxtest3
  $ cd blackboxtest3
  $ hg blackbox
  1970/01/01 00:00:00 bob (*)> blackbox (glob)
  $ mv .hg/blackbox.log .hg/blackbox.log-
  $ mkdir .hg/blackbox.log
  $ sed -e 's/\(.*test1.*\)/#\1/; s#\(.*commit2.*\)#os.rmdir(".hg/blackbox.log")\nos.rename(".hg/blackbox.log-", ".hg/blackbox.log")\n\1#' $TESTDIR/test-dispatch.py > ../test-dispatch.py
  $ python ../test-dispatch.py
  running: add foo
  result: 0
  running: commit -m commit1 -d 2000-01-01 foo
  result: None
  running: commit -m commit2 -d 2000-01-02 foo
  result: None
  running: log -r 0
  changeset:   0:0e4634943879
  user:        test
  date:        Sat Jan 01 00:00:00 2000 +0000
  summary:     commit1
  
  result: None
  running: log -r tip
  changeset:   1:45589e459b2e
  tag:         tip
  user:        test
  date:        Sun Jan 02 00:00:00 2000 +0000
  summary:     commit2
  
  result: None
  $ hg blackbox
  1970/01/01 00:00:00 bob (*)> blackbox (glob)
  1970/01/01 00:00:00 bob (*)> blackbox exited 0 after * seconds (glob)
  1970/01/01 00:00:00 bob (*)> blackbox (glob)

cleanup
  $ cd ..
