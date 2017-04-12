#require killdaemons

  $ echo "[extensions]"      >> $HGRCPATH
  $ echo "share = "          >> $HGRCPATH

prepare repo1

  $ hg init repo1
  $ cd repo1
  $ echo a > a
  $ hg commit -A -m'init'
  adding a

share it

  $ cd ..
  $ hg share repo1 repo2
  updating working directory
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved

share shouldn't have a store dir

  $ cd repo2
  $ test -d .hg/store
  [1]

Some sed versions appends newline, some don't, and some just fails

  $ cat .hg/sharedpath; echo
  $TESTTMP/repo1/.hg (glob)

trailing newline on .hg/sharedpath is ok
  $ hg tip -q
  0:d3873e73d99e
  $ echo '' >> .hg/sharedpath
  $ cat .hg/sharedpath
  $TESTTMP/repo1/.hg (glob)
  $ hg tip -q
  0:d3873e73d99e

commit in shared clone

  $ echo a >> a
  $ hg commit -m'change in shared clone'

check original

  $ cd ../repo1
  $ hg log
  changeset:   1:8af4dc49db9e
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     change in shared clone
  
  changeset:   0:d3873e73d99e
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     init
  
  $ hg update
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cat a             # should be two lines of "a"
  a
  a

commit in original

  $ echo b > b
  $ hg commit -A -m'another file'
  adding b

check in shared clone

  $ cd ../repo2
  $ hg log
  changeset:   2:c2e0ac586386
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     another file
  
  changeset:   1:8af4dc49db9e
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     change in shared clone
  
  changeset:   0:d3873e73d99e
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     init
  
  $ hg update
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cat b             # should exist with one "b"
  b

hg serve shared clone

  $ hg serve -n test -p $HGPORT -d --pid-file=hg.pid
  $ cat hg.pid >> $DAEMON_PIDS
  $ get-with-headers.py localhost:$HGPORT 'raw-file/'
  200 Script output follows
  
  
  -rw-r--r-- 4 a
  -rw-r--r-- 2 b
  
  

test unshare command

  $ hg unshare
  $ test -d .hg/store
  $ test -f .hg/sharedpath
  [1]
  $ grep shared .hg/requires
  [1]
  $ hg unshare
  abort: this is not a shared repo
  [255]

check that a change does not propagate

  $ echo b >> b
  $ hg commit -m'change in unshared'
  $ cd ../repo1
  $ hg id -r tip
  c2e0ac586386 tip

  $ cd ..


test sharing bookmarks

  $ hg share -B repo1 repo3
  updating working directory
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd repo1
  $ hg bookmark bm1
  $ hg bookmarks
   * bm1                       2:c2e0ac586386
  $ cd ../repo2
  $ hg book bm2
  $ hg bookmarks
   * bm2                       3:0e6e70d1d5f1
  $ cd ../repo3
  $ hg bookmarks
     bm1                       2:c2e0ac586386
  $ hg book bm3
  $ hg bookmarks
     bm1                       2:c2e0ac586386
   * bm3                       2:c2e0ac586386
  $ cd ../repo1
  $ hg bookmarks
   * bm1                       2:c2e0ac586386
     bm3                       2:c2e0ac586386

check whether HG_PENDING makes pending changes only in relatd
repositories visible to an external hook.

In "hg share" case, another transaction can't run in other
repositories sharing same source repository, because starting
transaction requires locking store of source repository.

Therefore, this test scenario ignores checking visibility of
.hg/bookmakrs.pending in repo2, which shares repo1 without bookmarks.

  $ cat > $TESTTMP/checkbookmarks.sh <<EOF
  > echo "@repo1"
  > hg -R "$TESTTMP/repo1" bookmarks
  > echo "@repo2"
  > hg -R "$TESTTMP/repo2" bookmarks
  > echo "@repo3"
  > hg -R "$TESTTMP/repo3" bookmarks
  > exit 1 # to avoid adding new bookmark for subsequent tests
  > EOF

  $ cd ../repo1
  $ hg --config hooks.pretxnclose="sh $TESTTMP/checkbookmarks.sh" -q book bmX
  @repo1
     bm1                       2:c2e0ac586386
     bm3                       2:c2e0ac586386
   * bmX                       2:c2e0ac586386
  @repo2
   * bm2                       3:0e6e70d1d5f1
  @repo3
     bm1                       2:c2e0ac586386
   * bm3                       2:c2e0ac586386
     bmX                       2:c2e0ac586386
  transaction abort!
  rollback completed
  abort: pretxnclose hook exited with status 1
  [255]
  $ hg book bm1

FYI, in contrast to above test, bmX is invisible in repo1 (= shared
src), because (1) HG_PENDING refers only repo3 and (2)
"bookmarks.pending" is written only into repo3.

  $ cd ../repo3
  $ hg --config hooks.pretxnclose="sh $TESTTMP/checkbookmarks.sh" -q book bmX
  @repo1
   * bm1                       2:c2e0ac586386
     bm3                       2:c2e0ac586386
  @repo2
   * bm2                       3:0e6e70d1d5f1
  @repo3
     bm1                       2:c2e0ac586386
     bm3                       2:c2e0ac586386
   * bmX                       2:c2e0ac586386
  transaction abort!
  rollback completed
  abort: pretxnclose hook exited with status 1
  [255]
  $ hg book bm3

  $ cd ../repo1

test that commits work

  $ echo 'shared bookmarks' > a
  $ hg commit -m 'testing shared bookmarks'
  $ hg bookmarks
   * bm1                       3:b87954705719
     bm3                       2:c2e0ac586386
  $ cd ../repo3
  $ hg bookmarks
     bm1                       3:b87954705719
   * bm3                       2:c2e0ac586386
  $ echo 'more shared bookmarks' > a
  $ hg commit -m 'testing shared bookmarks'
  created new head
  $ hg bookmarks
     bm1                       3:b87954705719
   * bm3                       4:62f4ded848e4
  $ cd ../repo1
  $ hg bookmarks
   * bm1                       3:b87954705719
     bm3                       4:62f4ded848e4
  $ cd ..

non largefiles repos won't enable largefiles

  $ hg share --config extensions.largefiles= repo3 sharedrepo
  updating working directory
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ [ -f sharedrepo/.hg/hgrc ]
  [1]

test pushing bookmarks works

  $ hg clone repo3 repo4
  updating to branch default
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd repo4
  $ hg boo bm4
  $ echo foo > b
  $ hg commit -m 'foo in b'
  $ hg boo
     bm1                       3:b87954705719
     bm3                       4:62f4ded848e4
   * bm4                       5:92793bfc8cad
  $ hg push -B bm4
  pushing to $TESTTMP/repo3 (glob)
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files
  exporting bookmark bm4
  $ cd ../repo1
  $ hg bookmarks
   * bm1                       3:b87954705719
     bm3                       4:62f4ded848e4
     bm4                       5:92793bfc8cad
  $ cd ../repo3
  $ hg bookmarks
     bm1                       3:b87954705719
   * bm3                       4:62f4ded848e4
     bm4                       5:92793bfc8cad
  $ cd ..

test behavior when sharing a shared repo

  $ hg share -B repo3 repo5
  updating working directory
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd repo5
  $ hg book
     bm1                       3:b87954705719
     bm3                       4:62f4ded848e4
     bm4                       5:92793bfc8cad
  $ cd ..

test what happens when an active bookmark is deleted

  $ cd repo1
  $ hg boo -d bm3
  $ hg boo
   * bm1                       3:b87954705719
     bm4                       5:92793bfc8cad
  $ cd ../repo3
  $ hg boo
     bm1                       3:b87954705719
     bm4                       5:92793bfc8cad
  $ cd ..

verify that bookmarks are not written on failed transaction

  $ cat > failpullbookmarks.py << EOF
  > """A small extension that makes bookmark pulls fail, for testing"""
  > from mercurial import extensions, exchange, error
  > def _pullbookmarks(orig, pullop):
  >     orig(pullop)
  >     raise error.HookAbort('forced failure by extension')
  > def extsetup(ui):
  >     extensions.wrapfunction(exchange, '_pullbookmarks', _pullbookmarks)
  > EOF
  $ cd repo4
  $ hg boo
     bm1                       3:b87954705719
     bm3                       4:62f4ded848e4
   * bm4                       5:92793bfc8cad
  $ cd ../repo3
  $ hg boo
     bm1                       3:b87954705719
     bm4                       5:92793bfc8cad
  $ hg --config "extensions.failpullbookmarks=$TESTTMP/failpullbookmarks.py" pull $TESTTMP/repo4
  pulling from $TESTTMP/repo4 (glob)
  searching for changes
  no changes found
  adding remote bookmark bm3
  abort: forced failure by extension
  [255]
  $ hg boo
     bm1                       3:b87954705719
     bm4                       5:92793bfc8cad
  $ hg pull $TESTTMP/repo4
  pulling from $TESTTMP/repo4 (glob)
  searching for changes
  no changes found
  adding remote bookmark bm3
  $ hg boo
     bm1                       3:b87954705719
   * bm3                       4:62f4ded848e4
     bm4                       5:92793bfc8cad
  $ cd ..

verify bookmark behavior after unshare

  $ cd repo3
  $ hg unshare
  $ hg boo
     bm1                       3:b87954705719
   * bm3                       4:62f4ded848e4
     bm4                       5:92793bfc8cad
  $ hg boo -d bm4
  $ hg boo bm5
  $ hg boo
     bm1                       3:b87954705719
     bm3                       4:62f4ded848e4
   * bm5                       4:62f4ded848e4
  $ cd ../repo1
  $ hg boo
   * bm1                       3:b87954705719
     bm3                       4:62f4ded848e4
     bm4                       5:92793bfc8cad
  $ cd ..

test shared clones using relative paths work

  $ mkdir thisdir
  $ hg init thisdir/orig
  $ hg share -U thisdir/orig thisdir/abs
  $ hg share -U --relative thisdir/abs thisdir/rel
  $ cat thisdir/rel/.hg/sharedpath
  ../../orig/.hg (no-eol) (glob)
  $ grep shared thisdir/*/.hg/requires
  thisdir/abs/.hg/requires:shared
  thisdir/rel/.hg/requires:shared
  thisdir/rel/.hg/requires:relshared

test that relative shared paths aren't relative to $PWD

  $ cd thisdir
  $ hg -R rel root
  $TESTTMP/thisdir/rel (glob)
  $ cd ..

now test that relative paths really are relative, survive across
renames and changes of PWD

  $ hg -R thisdir/abs root
  $TESTTMP/thisdir/abs (glob)
  $ hg -R thisdir/rel root
  $TESTTMP/thisdir/rel (glob)
  $ mv thisdir thatdir
  $ hg -R thatdir/abs root
  abort: .hg/sharedpath points to nonexistent directory $TESTTMP/thisdir/orig/.hg! (glob)
  [255]
  $ hg -R thatdir/rel root
  $TESTTMP/thatdir/rel (glob)

test unshare relshared repo

  $ cd thatdir/rel
  $ hg unshare
  $ test -d .hg/store
  $ test -f .hg/sharedpath
  [1]
  $ grep shared .hg/requires
  [1]
  $ hg unshare
  abort: this is not a shared repo
  [255]
  $ cd ../..

  $ rm -r thatdir

Explicitly kill daemons to let the test exit on Windows

  $ killdaemons.py

