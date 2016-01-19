  $ cat << EOF >> $HGRCPATH
  > [format]
  > usegeneraldelta=yes
  > EOF

Set up repo

  $ hg --config experimental.treemanifest=True init repo
  $ cd repo

Requirements get set on init

  $ grep treemanifest .hg/requires
  treemanifest

Without directories, looks like any other repo

  $ echo 0 > a
  $ echo 0 > b
  $ hg ci -Aqm initial
  $ hg debugdata -m 0
  a\x00362fef284ce2ca02aecc8de6d5e8a1c3af0556fe (esc)
  b\x00362fef284ce2ca02aecc8de6d5e8a1c3af0556fe (esc)

Submanifest is stored in separate revlog

  $ mkdir dir1
  $ echo 1 > dir1/a
  $ echo 1 > dir1/b
  $ echo 1 > e
  $ hg ci -Aqm 'add dir1'
  $ hg debugdata -m 1
  a\x00362fef284ce2ca02aecc8de6d5e8a1c3af0556fe (esc)
  b\x00362fef284ce2ca02aecc8de6d5e8a1c3af0556fe (esc)
  dir1\x008b3ffd73f901e83304c83d33132c8e774ceac44et (esc)
  e\x00b8e02f6433738021a065f94175c7cd23db5f05be (esc)
  $ hg debugdata --dir dir1 0
  a\x00b8e02f6433738021a065f94175c7cd23db5f05be (esc)
  b\x00b8e02f6433738021a065f94175c7cd23db5f05be (esc)

Can add nested directories

  $ mkdir dir1/dir1
  $ echo 2 > dir1/dir1/a
  $ echo 2 > dir1/dir1/b
  $ mkdir dir1/dir2
  $ echo 2 > dir1/dir2/a
  $ echo 2 > dir1/dir2/b
  $ hg ci -Aqm 'add dir1/dir1'
  $ hg files -r .
  a
  b
  dir1/a (glob)
  dir1/b (glob)
  dir1/dir1/a (glob)
  dir1/dir1/b (glob)
  dir1/dir2/a (glob)
  dir1/dir2/b (glob)
  e

Revision is not created for unchanged directory

  $ mkdir dir2
  $ echo 3 > dir2/a
  $ hg add dir2
  adding dir2/a (glob)
  $ hg debugindex --dir dir1 > before
  $ hg ci -qm 'add dir2'
  $ hg debugindex --dir dir1 > after
  $ diff before after
  $ rm before after

Removing directory does not create an revlog entry

  $ hg rm dir1/dir1
  removing dir1/dir1/a (glob)
  removing dir1/dir1/b (glob)
  $ hg debugindex --dir dir1/dir1 > before
  $ hg ci -qm 'remove dir1/dir1'
  $ hg debugindex --dir dir1/dir1 > after
  $ diff before after
  $ rm before after

Check that hg files (calls treemanifest.walk()) works
without loading all directory revlogs

  $ hg co 'desc("add dir2")'
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ mv .hg/store/meta/dir2 .hg/store/meta/dir2-backup
  $ hg files -r . dir1
  dir1/a (glob)
  dir1/b (glob)
  dir1/dir1/a (glob)
  dir1/dir1/b (glob)
  dir1/dir2/a (glob)
  dir1/dir2/b (glob)

Check that status between revisions works (calls treemanifest.matches())
without loading all directory revlogs

  $ hg status --rev 'desc("add dir1")' --rev . dir1
  A dir1/dir1/a
  A dir1/dir1/b
  A dir1/dir2/a
  A dir1/dir2/b
  $ mv .hg/store/meta/dir2-backup .hg/store/meta/dir2

Merge creates 2-parent revision of directory revlog

  $ echo 5 > dir1/a
  $ hg ci -Aqm 'modify dir1/a'
  $ hg co '.^'
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo 6 > dir1/b
  $ hg ci -Aqm 'modify dir1/b'
  $ hg merge 'desc("modify dir1/a")'
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -m 'conflict-free merge involving dir1/'
  $ cat dir1/a
  5
  $ cat dir1/b
  6
  $ hg debugindex --dir dir1
     rev    offset  length  delta linkrev nodeid       p1           p2
       0         0      54     -1       1 8b3ffd73f901 000000000000 000000000000
       1        54      68      0       2 68e9d057c5a8 8b3ffd73f901 000000000000
       2       122      12      1       4 4698198d2624 68e9d057c5a8 000000000000
       3       134      55      1       5 44844058ccce 68e9d057c5a8 000000000000
       4       189      55      1       6 bf3d9b744927 68e9d057c5a8 000000000000
       5       244      55      4       7 dde7c0af2a03 bf3d9b744927 44844058ccce

Merge keeping directory from parent 1 does not create revlog entry. (Note that
dir1's manifest does change, but only because dir1/a's filelog changes.)

  $ hg co 'desc("add dir2")'
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo 8 > dir2/a
  $ hg ci -m 'modify dir2/a'
  created new head

  $ hg debugindex --dir dir2 > before
  $ hg merge 'desc("modify dir1/a")'
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg revert -r 'desc("modify dir2/a")' .
  reverting dir1/a (glob)
  $ hg ci -m 'merge, keeping parent 1'
  $ hg debugindex --dir dir2 > after
  $ diff before after
  $ rm before after

Merge keeping directory from parent 2 does not create revlog entry. (Note that
dir2's manifest does change, but only because dir2/a's filelog changes.)

  $ hg co 'desc("modify dir2/a")'
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg debugindex --dir dir1 > before
  $ hg merge 'desc("modify dir1/a")'
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg revert -r 'desc("modify dir1/a")' .
  reverting dir2/a (glob)
  $ hg ci -m 'merge, keeping parent 2'
  created new head
  $ hg debugindex --dir dir1 > after
  $ diff before after
  $ rm before after

Create flat source repo for tests with mixed flat/tree manifests

  $ cd ..
  $ hg init repo-flat
  $ cd repo-flat

Create a few commits with flat manifest

  $ echo 0 > a
  $ echo 0 > b
  $ echo 0 > e
  $ for d in dir1 dir1/dir1 dir1/dir2 dir2
  > do
  >   mkdir $d
  >   echo 0 > $d/a
  >   echo 0 > $d/b
  > done
  $ hg ci -Aqm initial

  $ echo 1 > a
  $ echo 1 > dir1/a
  $ echo 1 > dir1/dir1/a
  $ hg ci -Aqm 'modify on branch 1'

  $ hg co 0
  3 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo 2 > b
  $ echo 2 > dir1/b
  $ echo 2 > dir1/dir1/b
  $ hg ci -Aqm 'modify on branch 2'

  $ hg merge 1
  3 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -m 'merge of flat manifests to new flat manifest'

Create clone with tree manifests enabled

  $ cd ..
  $ hg clone --pull --config experimental.treemanifest=1 repo-flat repo-mixed
  requesting all changes
  adding changesets
  adding manifests
  adding file changes
  added 4 changesets with 17 changes to 11 files
  updating to branch default
  11 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd repo-mixed
  $ test -f .hg/store/meta
  [1]
  $ grep treemanifest .hg/requires
  treemanifest

Commit should store revlog per directory

  $ hg co 1
  3 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo 3 > a
  $ echo 3 > dir1/a
  $ echo 3 > dir1/dir1/a
  $ hg ci -m 'first tree'
  created new head
  $ find .hg/store/meta | sort
  .hg/store/meta
  .hg/store/meta/dir1
  .hg/store/meta/dir1/00manifest.i
  .hg/store/meta/dir1/dir1
  .hg/store/meta/dir1/dir1/00manifest.i
  .hg/store/meta/dir1/dir2
  .hg/store/meta/dir1/dir2/00manifest.i
  .hg/store/meta/dir2
  .hg/store/meta/dir2/00manifest.i

Merge of two trees

  $ hg co 2
  6 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg merge 1
  3 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -m 'merge of flat manifests to new tree manifest'
  created new head
  $ hg diff -r 3

Parent of tree root manifest should be flat manifest, and two for merge

  $ hg debugindex -m
     rev    offset  length  delta linkrev nodeid       p1           p2
       0         0      80     -1       0 40536115ed9e 000000000000 000000000000
       1        80      83      0       1 f3376063c255 40536115ed9e 000000000000
       2       163      89      0       2 5d9b9da231a2 40536115ed9e 000000000000
       3       252      83      2       3 d17d663cbd8a 5d9b9da231a2 f3376063c255
       4       335     124      1       4 51e32a8c60ee f3376063c255 000000000000
       5       459     126      2       5 cc5baa78b230 5d9b9da231a2 f3376063c255


Status across flat/tree boundary should work

  $ hg status --rev '.^' --rev .
  M a
  M dir1/a
  M dir1/dir1/a


Turning off treemanifest config has no effect

  $ hg debugindex .hg/store/meta/dir1/00manifest.i
     rev    offset  length  delta linkrev nodeid       p1           p2
       0         0     127     -1       4 064927a0648a 000000000000 000000000000
       1       127     111      0       5 25ecb8cb8618 000000000000 000000000000
  $ echo 2 > dir1/a
  $ hg --config experimental.treemanifest=False ci -qm 'modify dir1/a'
  $ hg debugindex .hg/store/meta/dir1/00manifest.i
     rev    offset  length  delta linkrev nodeid       p1           p2
       0         0     127     -1       4 064927a0648a 000000000000 000000000000
       1       127     111      0       5 25ecb8cb8618 000000000000 000000000000
       2       238      55      1       6 5b16163a30c6 25ecb8cb8618 000000000000

Stripping and recovering changes should work

  $ hg st --change tip
  M dir1/a
  $ hg --config extensions.strip= strip tip
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/repo-mixed/.hg/strip-backup/51cfd7b1e13b-78a2f3ed-backup.hg (glob)
  $ hg unbundle -q .hg/strip-backup/*
  $ hg st --change tip
  M dir1/a

Shelving and unshelving should work

  $ echo foo >> dir1/a
  $ hg --config extensions.shelve= shelve
  shelved as default
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg --config extensions.shelve= unshelve
  unshelving change 'default'
  $ hg diff --nodates
  diff -r 708a273da119 dir1/a
  --- a/dir1/a
  +++ b/dir1/a
  @@ -1,1 +1,2 @@
   1
  +foo

Create deeper repo with tree manifests.

  $ cd ..
  $ hg --config experimental.treemanifest=True init deeprepo
  $ cd deeprepo

  $ mkdir a
  $ mkdir b
  $ mkdir b/bar
  $ mkdir b/bar/orange
  $ mkdir b/bar/orange/fly
  $ mkdir b/foo
  $ mkdir b/foo/apple
  $ mkdir b/foo/apple/bees

  $ touch a/one.txt
  $ touch a/two.txt
  $ touch b/bar/fruits.txt
  $ touch b/bar/orange/fly/gnat.py
  $ touch b/bar/orange/fly/housefly.txt
  $ touch b/foo/apple/bees/flower.py
  $ touch c.txt
  $ touch d.py

  $ hg ci -Aqm 'initial'

We'll see that visitdir works by removing some treemanifest revlogs and running
the files command with various parameters.

Test files from the root.

  $ hg files -r .
  a/one.txt (glob)
  a/two.txt (glob)
  b/bar/fruits.txt (glob)
  b/bar/orange/fly/gnat.py (glob)
  b/bar/orange/fly/housefly.txt (glob)
  b/foo/apple/bees/flower.py (glob)
  c.txt
  d.py

Excludes with a glob should not exclude everything from the glob's root

  $ hg files -r . -X 'b/fo?' b
  b/bar/fruits.txt (glob)
  b/bar/orange/fly/gnat.py (glob)
  b/bar/orange/fly/housefly.txt (glob)

Test files for a subdirectory.

  $ mv .hg/store/meta/a oldmf
  $ hg files -r . b
  b/bar/fruits.txt (glob)
  b/bar/orange/fly/gnat.py (glob)
  b/bar/orange/fly/housefly.txt (glob)
  b/foo/apple/bees/flower.py (glob)
  $ mv oldmf .hg/store/meta/a

Test files with just includes and excludes.

  $ mv .hg/store/meta/a oldmf
  $ mv .hg/store/meta/b/bar/orange/fly oldmf2
  $ mv .hg/store/meta/b/foo/apple/bees oldmf3
  $ hg files -r . -I path:b/bar -X path:b/bar/orange/fly -I path:b/foo -X path:b/foo/apple/bees
  b/bar/fruits.txt (glob)
  $ mv oldmf .hg/store/meta/a
  $ mv oldmf2 .hg/store/meta/b/bar/orange/fly
  $ mv oldmf3 .hg/store/meta/b/foo/apple/bees

Test files for a subdirectory, excluding a directory within it.

  $ mv .hg/store/meta/a oldmf
  $ mv .hg/store/meta/b/foo oldmf2
  $ hg files -r . -X path:b/foo b
  b/bar/fruits.txt (glob)
  b/bar/orange/fly/gnat.py (glob)
  b/bar/orange/fly/housefly.txt (glob)
  $ mv oldmf .hg/store/meta/a
  $ mv oldmf2 .hg/store/meta/b/foo

Test files for a sub directory, including only a directory within it, and
including an unrelated directory.

  $ mv .hg/store/meta/a oldmf
  $ mv .hg/store/meta/b/foo oldmf2
  $ hg files -r . -I path:b/bar/orange -I path:a b
  b/bar/orange/fly/gnat.py (glob)
  b/bar/orange/fly/housefly.txt (glob)
  $ mv oldmf .hg/store/meta/a
  $ mv oldmf2 .hg/store/meta/b/foo

Test files for a pattern, including a directory, and excluding a directory
within that.

  $ mv .hg/store/meta/a oldmf
  $ mv .hg/store/meta/b/foo oldmf2
  $ mv .hg/store/meta/b/bar/orange oldmf3
  $ hg files -r . glob:**.txt -I path:b/bar -X path:b/bar/orange
  b/bar/fruits.txt (glob)
  $ mv oldmf .hg/store/meta/a
  $ mv oldmf2 .hg/store/meta/b/foo
  $ mv oldmf3 .hg/store/meta/b/bar/orange

Add some more changes to the deep repo
  $ echo narf >> b/bar/fruits.txt
  $ hg ci -m narf
  $ echo troz >> b/bar/orange/fly/gnat.py
  $ hg ci -m troz

Test cloning a treemanifest repo over http.
  $ hg serve -p $HGPORT -d --pid-file=hg.pid --errorlog=errors.log
  $ cat hg.pid >> $DAEMON_PIDS
  $ cd ..
We can clone even with the knob turned off and we'll get a treemanifest repo.
  $ hg clone --config experimental.treemanifest=False \
  >   --config experimental.changegroup3=True \
  >   http://localhost:$HGPORT deepclone
  requesting all changes
  adding changesets
  adding manifests
  adding file changes
  added 3 changesets with 10 changes to 8 files
  updating to branch default
  8 files updated, 0 files merged, 0 files removed, 0 files unresolved
No server errors.
  $ cat deeprepo/errors.log
requires got updated to include treemanifest
  $ cat deepclone/.hg/requires | grep treemanifest
  treemanifest
Tree manifest revlogs exist.
  $ find deepclone/.hg/store/meta | sort
  deepclone/.hg/store/meta
  deepclone/.hg/store/meta/a
  deepclone/.hg/store/meta/a/00manifest.i
  deepclone/.hg/store/meta/b
  deepclone/.hg/store/meta/b/00manifest.i
  deepclone/.hg/store/meta/b/bar
  deepclone/.hg/store/meta/b/bar/00manifest.i
  deepclone/.hg/store/meta/b/bar/orange
  deepclone/.hg/store/meta/b/bar/orange/00manifest.i
  deepclone/.hg/store/meta/b/bar/orange/fly
  deepclone/.hg/store/meta/b/bar/orange/fly/00manifest.i
  deepclone/.hg/store/meta/b/foo
  deepclone/.hg/store/meta/b/foo/00manifest.i
  deepclone/.hg/store/meta/b/foo/apple
  deepclone/.hg/store/meta/b/foo/apple/00manifest.i
  deepclone/.hg/store/meta/b/foo/apple/bees
  deepclone/.hg/store/meta/b/foo/apple/bees/00manifest.i
Verify passes.
  $ cd deepclone
  $ hg verify
  checking changesets
  checking manifests
  crosschecking files in changesets and manifests
  checking files
  8 files, 3 changesets, 10 total revisions
  $ cd ..
