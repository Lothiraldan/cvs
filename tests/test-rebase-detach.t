  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > graphlog=
  > rebase=
  > 
  > [alias]
  > tglog = log -G --template "{rev}: '{desc}' {branches}\n"
  > EOF


  $ hg init a
  $ cd a
  $ hg unbundle $TESTDIR/bundles/rebase.hg
  adding changesets
  adding manifests
  adding file changes
  added 8 changesets with 7 changes to 7 files (+2 heads)
  (run 'hg heads' to see heads, 'hg merge' to merge)
  $ hg up tip
  3 files updated, 0 files merged, 0 files removed, 0 files unresolved

  $ cd ..


Rebasing D onto H detaching from C:

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
  
  $ hg rebase --detach -s 3 -d 7
  saved backup bundle to $TESTTMP/a1/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  7: 'D'
  |
  o  6: 'H'
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
  
  $ hg manifest
  A
  D
  F
  H

  $ cd ..


Rebasing C onto H detaching from B:

  $ hg clone -q -u . a a2
  $ cd a2

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
  
  $ hg rebase --detach -s 2 -d 7
  saved backup bundle to $TESTTMP/a2/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  7: 'D'
  |
  o  6: 'C'
  |
  o  5: 'H'
  |
  | o  4: 'G'
  |/|
  o |  3: 'F'
  | |
  | o  2: 'E'
  |/
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ hg manifest
  A
  C
  D
  F
  H

  $ cd ..


Rebasing B onto H using detach (same as not using it):

  $ hg clone -q -u . a a3
  $ cd a3

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
  
  $ hg rebase --detach -s 1 -d 7
  saved backup bundle to $TESTTMP/a3/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  7: 'D'
  |
  o  6: 'C'
  |
  o  5: 'B'
  |
  o  4: 'H'
  |
  | o  3: 'G'
  |/|
  o |  2: 'F'
  | |
  | o  1: 'E'
  |/
  o  0: 'A'
  
  $ hg manifest
  A
  B
  C
  D
  F
  H

  $ cd ..


Rebasing C onto H detaching from B and collapsing:

  $ hg clone -q -u . a a4
  $ cd a4

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
  
  $ hg rebase --detach --collapse -s 2 -d 7
  saved backup bundle to $TESTTMP/a4/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  6: 'Collapsed revision
  |  * C
  |  * D'
  o  5: 'H'
  |
  | o  4: 'G'
  |/|
  o |  3: 'F'
  | |
  | o  2: 'E'
  |/
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ hg manifest
  A
  C
  D
  F
  H

  $ cd ..

Rebasing across null as ancestor
  $ hg clone -q -U a a5

  $ cd a5

  $ echo x > x

  $ hg add x

  $ hg ci -m "extra branch"
  created new head

  $ hg tglog
  @  8: 'extra branch'
  
  o  7: 'H'
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
  
  $ hg rebase --detach -s 1 -d tip
  saved backup bundle to $TESTTMP/a5/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  8: 'D'
  |
  o  7: 'C'
  |
  o  6: 'B'
  |
  o  5: 'extra branch'
  
  o  4: 'H'
  |
  | o  3: 'G'
  |/|
  o |  2: 'F'
  | |
  | o  1: 'E'
  |/
  o  0: 'A'
  

  $ hg rebase -d 5 -s 7
  saved backup bundle to $TESTTMP/a5/.hg/strip-backup/13547172c9c0-backup.hg
  $ hg tglog
  @  8: 'D'
  |
  o  7: 'C'
  |
  | o  6: 'B'
  |/
  o  5: 'extra branch'
  
  o  4: 'H'
  |
  | o  3: 'G'
  |/|
  o |  2: 'F'
  | |
  | o  1: 'E'
  |/
  o  0: 'A'
  
  $ cd ..

Verify that target is not selected as external rev (issue3085)

  $ hg clone -q -U a a6
  $ cd a6
  $ hg up -q 6

  $ echo "I" >> E
  $ hg ci -m "I"
  $ hg merge 7
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -m "Merge"
  $ echo "J" >> F
  $ hg ci -m "J"

  $ hg rebase -s 8 -d 7 --collapse --detach --config ui.merge=internal:other
  remote changed E which local deleted
  use (c)hanged version or leave (d)eleted? c
  saved backup bundle to $TESTTMP/a6/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  8: 'Collapsed revision
  |  * I
  |  * Merge
  |  * J'
  o  7: 'H'
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
  

  $ hg parents
  changeset:   8:9472f4b1d736
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     Collapsed revision
  

  $ cd ..

Ensure --continue restores a correct state (issue3046):
  $ hg clone -q a a7
  $ cd a7
  $ hg up -q 3
  $ echo 'H2' > H
  $ hg ci -A -m 'H2'
  adding H
  $ hg rebase -s 8 -d 7 --detach --config ui.merge=internal:fail
  merging H
  warning: conflicts during merge.
  merging H failed!
  abort: unresolved conflicts (see hg resolve, then hg rebase --continue)
  [255]
  $ hg resolve --all -t internal:local
  $ hg rebase -c
  saved backup bundle to $TESTTMP/a7/.hg/strip-backup/6215fafa5447-backup.hg
  $ hg tglog
  @  8: 'H2'
  |
  o  7: 'H'
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
  

