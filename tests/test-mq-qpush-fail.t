Test that qpush cleans things up if it doesn't complete

  $ echo "[extensions]" >> $HGRCPATH
  $ echo "mq=" >> $HGRCPATH
  $ hg init repo
  $ cd repo
  $ echo foo > foo
  $ hg ci -Am 'add foo'
  adding foo
  $ touch untracked-file
  $ echo 'syntax: glob' > .hgignore
  $ echo '.hgignore' >> .hgignore
  $ hg qinit

test qpush on empty series

  $ hg qpush
  no patches in series
  $ hg qnew patch1
  $ echo >> foo
  $ hg qrefresh -m 'patch 1'
  $ hg qnew patch2
  $ echo bar > bar
  $ hg add bar
  $ hg qrefresh -m 'patch 2'
  $ hg qnew --config 'mq.plain=true' bad-patch
  $ echo >> foo
  $ hg qrefresh
  $ hg qpop -a
  popping bad-patch
  popping patch2
  popping patch1
  patch queue now empty
  $ python -c 'print "\xe9"' > message
  $ cat .hg/patches/bad-patch >> message
  $ mv message .hg/patches/bad-patch
  $ hg qpush -a && echo 'qpush succeded?!'
  applying patch1
  applying patch2
  applying bad-patch
  transaction abort!
  rollback completed
  cleaning up working directory...done
  abort: decoding near '\xe9': 'ascii' codec can't decode byte 0xe9 in position 0: ordinal not in range(128)! (esc)
  [255]
  $ hg parents
  changeset:   0:bbd179dfa0a7
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     add foo
  

test corrupt status file
  $ hg qpush
  applying patch1
  now at: patch1
  $ cp .hg/patches/status .hg/patches/status.orig
  $ hg qpop
  popping patch1
  patch queue now empty
  $ cp .hg/patches/status.orig .hg/patches/status
  $ hg qpush
  mq status file refers to unknown node * (glob)
  abort: working directory revision is not qtip
  [255]
  $ rm .hg/patches/status .hg/patches/status.orig


bar should be gone; other unknown/ignored files should still be around

  $ hg status -A
  ? untracked-file
  I .hgignore
  C foo

preparing qpush of a missing patch

  $ hg qpop -a
  no patches applied
  $ hg qpush
  applying patch1
  now at: patch1
  $ rm .hg/patches/patch2

now we expect the push to fail, but it should NOT complain about patch1

  $ hg qpush
  applying patch2
  unable to read patch2
  now at: patch1
  [1]

preparing qpush of missing patch with no patch applied

  $ hg qpop -a
  popping patch1
  patch queue now empty
  $ rm .hg/patches/patch1

qpush should fail the same way as below

  $ hg qpush
  applying patch1
  unable to read patch1
  [1]

Test qpush to a patch below the currently applied patch.

  $ hg qq -c guardedseriesorder
  $ hg qnew a
  $ hg qguard +block
  $ hg qnew b
  $ hg qnew c

  $ hg qpop -a
  popping c
  popping b
  popping a
  patch queue now empty

try to push and pop while a is guarded

  $ hg qpush a
  cannot push 'a' - guarded by '+block'
  [1]
  $ hg qpush -a
  applying b
  patch b is empty
  applying c
  patch c is empty
  now at: c

now try it when a is unguarded, and we're at the top of the queue
  $ hg qsel block
  number of guarded, applied patches has changed from 1 to 0
  $ hg qpush b
  abort: cannot push to a previous patch: b
  [255]
  $ hg qpush a
  abort: cannot push to a previous patch: a
  [255]

and now we try it one more time with a unguarded, while we're not at the top of the queue

  $ hg qpop b
  popping c
  now at: b
  $ hg qpush a
  abort: cannot push to a previous patch: a
  [255]

test qpop --force and backup files

  $ hg qpop -a
  popping b
  patch queue now empty
  $ hg qq --create force
  $ echo a > a
  $ echo b > b
  $ echo c > c
  $ hg ci -Am add a b c
  $ echo a >> a
  $ hg rm b
  $ hg rm c
  $ hg qnew p1
  $ echo a >> a
  $ echo bb > b
  $ hg add b
  $ echo cc > c
  $ hg add c
  $ hg qpop --force --verbose
  saving current version of a as a.orig
  saving current version of b as b.orig
  saving current version of c as c.orig
  popping p1
  patch queue now empty
  $ hg st
  ? a.orig
  ? b.orig
  ? c.orig
  ? untracked-file
  $ cat a.orig
  a
  a
  a
  $ cat b.orig
  bb
  $ cat c.orig
  cc

test qpush --force and backup files

  $ echo a >> a
  $ hg qnew p2
  $ echo b >> b
  $ echo d > d
  $ echo e > e
  $ hg add d e
  $ hg rm c
  $ hg qnew p3
  $ hg qpop -a
  popping p3
  popping p2
  patch queue now empty
  $ echo a >> a
  $ echo b1 >> b
  $ echo d1 > d
  $ hg add d
  $ echo e1 > e
  $ hg qpush -a --force --verbose
  applying p2
  saving current version of a as a.orig
  patching file a
  a
  applying p3
  saving current version of b as b.orig
  saving current version of d as d.orig
  patching file b
  patching file c
  patching file d
  file d already exists
  1 out of 1 hunks FAILED -- saving rejects to file d.rej
  patching file e
  file e already exists
  1 out of 1 hunks FAILED -- saving rejects to file e.rej
  patch failed to apply
  b
  patch failed, rejects left in working dir
  errors during apply, please fix and refresh p3
  [2]
  $ cat a.orig
  a
  a
  $ cat b.orig
  b
  b1
  $ cat d.orig
  d1
