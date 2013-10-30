  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > graphlog=
  > rebase=
  > 
  > [phases]
  > publish=False
  > 
  > [alias]
  > tglog = log -G --template "{rev}: '{desc}' {branches}\n"
  > EOF


  $ hg init a
  $ cd a
  $ hg unbundle "$TESTDIR/bundles/rebase.hg"
  adding changesets
  adding manifests
  adding file changes
  added 8 changesets with 7 changes to 7 files (+2 heads)
  (run 'hg heads' to see heads, 'hg merge' to merge)
  $ hg up tip
  3 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd ..


Rebasing
D onto H - simple rebase:

  $ hg clone -q -u . a a1
  $ cd a1

  $ hg tglog
  @  7: 'H'
  |
  | o  6: 'G'
  |/|
  o |  5: 'F'
  | |
  | o  4: 'E'
  |/
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  | o  1: 'B'
  |/
  o  0: 'A'
  

  $ hg rebase -s 3 -d 7
  saved backup bundle to $TESTTMP/a1/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  o  7: 'D'
  |
  @  6: 'H'
  |
  | o  5: 'G'
  |/|
  o |  4: 'F'
  | |
  | o  3: 'E'
  |/
  | o  2: 'C'
  | |
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


D onto F - intermediate point:

  $ hg clone -q -u . a a2
  $ cd a2

  $ hg rebase -s 3 -d 5
  saved backup bundle to $TESTTMP/a2/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  o  7: 'D'
  |
  | @  6: 'H'
  |/
  | o  5: 'G'
  |/|
  o |  4: 'F'
  | |
  | o  3: 'E'
  |/
  | o  2: 'C'
  | |
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


E onto H - skip of G:

  $ hg clone -q -u . a a3
  $ cd a3

  $ hg rebase -s 4 -d 7
  saved backup bundle to $TESTTMP/a3/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  o  6: 'E'
  |
  @  5: 'H'
  |
  o  4: 'F'
  |
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


F onto E - rebase of a branching point (skip G):

  $ hg clone -q -u . a a4
  $ cd a4

  $ hg rebase -s 5 -d 4
  saved backup bundle to $TESTTMP/a4/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  6: 'H'
  |
  o  5: 'F'
  |
  o  4: 'E'
  |
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


G onto H - merged revision having a parent in ancestors of target:

  $ hg clone -q -u . a a5
  $ cd a5

  $ hg rebase -s 6 -d 7
  saved backup bundle to $TESTTMP/a5/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  o    7: 'G'
  |\
  | @  6: 'H'
  | |
  | o  5: 'F'
  | |
  o |  4: 'E'
  |/
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


F onto B - G maintains E as parent:

  $ hg clone -q -u . a a6
  $ cd a6

  $ hg rebase -s 5 -d 1
  saved backup bundle to $TESTTMP/a6/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  7: 'H'
  |
  | o  6: 'G'
  |/|
  o |  5: 'F'
  | |
  | o  4: 'E'
  | |
  | | o  3: 'D'
  | | |
  +---o  2: 'C'
  | |
  o |  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


These will fail (using --source):

G onto F - rebase onto an ancestor:

  $ hg clone -q -u . a a7
  $ cd a7

  $ hg rebase -s 6 -d 5
  nothing to rebase
  [1]

F onto G - rebase onto a descendant:

  $ hg rebase -s 5 -d 6
  abort: source is ancestor of destination
  [255]

G onto B - merge revision with both parents not in ancestors of target:

  $ hg rebase -s 6 -d 1
  abort: cannot use revision 6 as base, result would have 3 parents
  [255]


These will abort gracefully (using --base):

G onto G - rebase onto same changeset:

  $ hg rebase -b 6 -d 6
  nothing to rebase
  [1]

G onto F - rebase onto an ancestor:

  $ hg rebase -b 6 -d 5
  nothing to rebase
  [1]

F onto G - rebase onto a descendant:

  $ hg rebase -b 5 -d 6
  nothing to rebase
  [1]

C onto A - rebase onto an ancestor:

  $ hg rebase -d 0 -s 2
  saved backup bundle to $TESTTMP/a7/.hg/strip-backup/5fddd98957c8-backup.hg (glob)
  $ hg tglog
  o  7: 'D'
  |
  o  6: 'C'
  |
  | @  5: 'H'
  | |
  | | o  4: 'G'
  | |/|
  | o |  3: 'F'
  |/ /
  | o  2: 'E'
  |/
  | o  1: 'B'
  |/
  o  0: 'A'
  

Check rebasing public changeset

  $ hg pull --config phases.publish=True -q -r 6 . # update phase of 6
  $ hg rebase -d 0 -b 6
  nothing to rebase
  [1]
  $ hg rebase -d 5 -b 6
  abort: can't rebase immutable changeset e1c4361dd923
  (see hg help phases for details)
  [255]

  $ hg rebase -d 5 -b 6 --keep

Check rebasing mutable changeset
Source phase greater or equal to destination phase: new changeset get the phase of source:
  $ hg rebase -s9 -d0
  saved backup bundle to $TESTTMP/a7/.hg/strip-backup/2b23e52411f4-backup.hg (glob)
  $ hg log --template "{phase}\n" -r 9
  draft
  $ hg rebase -s9 -d1
  saved backup bundle to $TESTTMP/a7/.hg/strip-backup/2cb10d0cfc6c-backup.hg (glob)
  $ hg log --template "{phase}\n" -r 9
  draft
  $ hg phase --force --secret 9
  $ hg rebase -s9 -d0
  saved backup bundle to $TESTTMP/a7/.hg/strip-backup/c5b12b67163a-backup.hg (glob)
  $ hg log --template "{phase}\n" -r 9
  secret
  $ hg rebase -s9 -d1
  saved backup bundle to $TESTTMP/a7/.hg/strip-backup/2a0524f868ac-backup.hg (glob)
  $ hg log --template "{phase}\n" -r 9
  secret
Source phase lower than destination phase: new changeset get the phase of destination:
  $ hg rebase -s8 -d9
  saved backup bundle to $TESTTMP/a7/.hg/strip-backup/6d4f22462821-backup.hg (glob)
  $ hg log --template "{phase}\n" -r 'rev(9)'
  secret

  $ cd ..

Test for revset

We need a bit different graph
All destination are B

  $ hg init ah
  $ cd ah
  $ hg unbundle "$TESTDIR/bundles/rebase-revset.hg"
  adding changesets
  adding manifests
  adding file changes
  added 9 changesets with 9 changes to 9 files (+2 heads)
  (run 'hg heads' to see heads, 'hg merge' to merge)
  $ hg tglog
  o  8: 'I'
  |
  o  7: 'H'
  |
  o  6: 'G'
  |
  | o  5: 'F'
  | |
  | o  4: 'E'
  |/
  o  3: 'D'
  |
  o  2: 'C'
  |
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


Simple case with keep:

Source on have two descendant heads but ask for one

  $ hg clone -q -u . ah ah1
  $ cd ah1
  $ hg rebase -r '2::8' -d 1
  abort: can't remove original changesets with unrebased descendants
  (use --keep to keep original changesets)
  [255]
  $ hg rebase -r '2::8' -d 1 --keep
  $ hg tglog
  o  13: 'I'
  |
  o  12: 'H'
  |
  o  11: 'G'
  |
  o  10: 'D'
  |
  o  9: 'C'
  |
  | o  8: 'I'
  | |
  | o  7: 'H'
  | |
  | o  6: 'G'
  | |
  | | o  5: 'F'
  | | |
  | | o  4: 'E'
  | |/
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  o |  1: 'B'
  |/
  o  0: 'A'
  

  $ cd ..

Base on have one descendant heads we ask for but common ancestor have two

  $ hg clone -q -u . ah ah2
  $ cd ah2
  $ hg rebase -r '3::8' -d 1
  abort: can't remove original changesets with unrebased descendants
  (use --keep to keep original changesets)
  [255]
  $ hg rebase -r '3::8' -d 1 --keep
  $ hg tglog
  o  12: 'I'
  |
  o  11: 'H'
  |
  o  10: 'G'
  |
  o  9: 'D'
  |
  | o  8: 'I'
  | |
  | o  7: 'H'
  | |
  | o  6: 'G'
  | |
  | | o  5: 'F'
  | | |
  | | o  4: 'E'
  | |/
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  o |  1: 'B'
  |/
  o  0: 'A'
  

  $ cd ..

rebase subset

  $ hg clone -q -u . ah ah3
  $ cd ah3
  $ hg rebase -r '3::7' -d 1
  abort: can't remove original changesets with unrebased descendants
  (use --keep to keep original changesets)
  [255]
  $ hg rebase -r '3::7' -d 1 --keep
  $ hg tglog
  o  11: 'H'
  |
  o  10: 'G'
  |
  o  9: 'D'
  |
  | o  8: 'I'
  | |
  | o  7: 'H'
  | |
  | o  6: 'G'
  | |
  | | o  5: 'F'
  | | |
  | | o  4: 'E'
  | |/
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  o |  1: 'B'
  |/
  o  0: 'A'
  

  $ cd ..

rebase subset with multiple head

  $ hg clone -q -u . ah ah4
  $ cd ah4
  $ hg rebase -r '3::(7+5)' -d 1
  abort: can't remove original changesets with unrebased descendants
  (use --keep to keep original changesets)
  [255]
  $ hg rebase -r '3::(7+5)' -d 1 --keep
  $ hg tglog
  o  13: 'H'
  |
  o  12: 'G'
  |
  | o  11: 'F'
  | |
  | o  10: 'E'
  |/
  o  9: 'D'
  |
  | o  8: 'I'
  | |
  | o  7: 'H'
  | |
  | o  6: 'G'
  | |
  | | o  5: 'F'
  | | |
  | | o  4: 'E'
  | |/
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  o |  1: 'B'
  |/
  o  0: 'A'
  

  $ cd ..

More advanced tests

rebase on ancestor with revset

  $ hg clone -q -u . ah ah5
  $ cd ah5
  $ hg rebase -r '6::' -d 2
  saved backup bundle to $TESTTMP/ah5/.hg/strip-backup/3d8a618087a7-backup.hg (glob)
  $ hg tglog
  o  8: 'I'
  |
  o  7: 'H'
  |
  o  6: 'G'
  |
  | o  5: 'F'
  | |
  | o  4: 'E'
  | |
  | o  3: 'D'
  |/
  o  2: 'C'
  |
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


rebase with multiple root.
We rebase E and G on B
We would expect heads are I, F if it was supported

  $ hg clone -q -u . ah ah6
  $ cd ah6
  $ hg rebase -r '(4+6)::' -d 1
  saved backup bundle to $TESTTMP/ah6/.hg/strip-backup/3d8a618087a7-backup.hg (glob)
  $ hg tglog
  o  8: 'I'
  |
  o  7: 'H'
  |
  o  6: 'G'
  |
  | o  5: 'F'
  | |
  | o  4: 'E'
  |/
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  o |  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..

More complex rebase with multiple roots
each root have a different common ancestor with the destination and this is a detach

(setup)

  $ hg clone -q -u . a a8
  $ cd a8
  $ echo I > I
  $ hg add I
  $ hg commit -m I
  $ hg up 4
  1 files updated, 0 files merged, 3 files removed, 0 files unresolved
  $ echo I > J
  $ hg add J
  $ hg commit -m J
  created new head
  $ echo I > K
  $ hg add K
  $ hg commit -m K
  $ hg tglog
  @  10: 'K'
  |
  o  9: 'J'
  |
  | o  8: 'I'
  | |
  | o  7: 'H'
  | |
  +---o  6: 'G'
  | |/
  | o  5: 'F'
  | |
  o |  4: 'E'
  |/
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  | o  1: 'B'
  |/
  o  0: 'A'
  
(actual test)

  $ hg rebase --dest 'desc(G)' --rev 'desc(K) + desc(I)'
  saved backup bundle to $TESTTMP/a8/.hg/strip-backup/23a4ace37988-backup.hg (glob)
  $ hg log --rev 'children(desc(G))'
  changeset:   9:adb617877056
  parent:      6:eea13746799a
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     I
  
  changeset:   10:882431a34a0e
  tag:         tip
  parent:      6:eea13746799a
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     K
  
  $ hg tglog
  @  10: 'K'
  |
  | o  9: 'I'
  |/
  | o  8: 'J'
  | |
  | | o  7: 'H'
  | | |
  o---+  6: 'G'
  |/ /
  | o  5: 'F'
  | |
  o |  4: 'E'
  |/
  | o  3: 'D'
  | |
  | o  2: 'C'
  | |
  | o  1: 'B'
  |/
  o  0: 'A'
  
