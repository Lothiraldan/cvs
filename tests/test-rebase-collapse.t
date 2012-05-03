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
  > tglogp = log -G --template "{rev}:{phase} '{desc}' {branches}\n"
  > EOF

Create repo a:

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
  
  $ cd ..


Rebasing B onto H and collapsing changesets with different phases:


  $ hg clone -q -u 3 a a1
  $ cd a1

  $ hg phase --force --secret 3

  $ hg rebase --collapse --keepbranches
  saved backup bundle to $TESTTMP/a1/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglogp
  @  5:secret 'Collapsed revision
  |  * B
  |  * C
  |  * D'
  o  4:draft 'H'
  |
  | o  3:draft 'G'
  |/|
  o |  2:draft 'F'
  | |
  | o  1:draft 'E'
  |/
  o  0:draft 'A'
  
  $ hg manifest
  A
  B
  C
  D
  F
  H

  $ cd ..


Rebasing E onto H:

  $ hg clone -q -u . a a2
  $ cd a2

  $ hg phase --force --secret 6
  $ hg rebase --source 4 --collapse
  saved backup bundle to $TESTTMP/a2/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  6: 'Collapsed revision
  |  * E
  |  * G'
  o  5: 'H'
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
  
  $ hg manifest
  A
  E
  F
  H

  $ cd ..

Rebasing G onto H with custom message:

  $ hg clone -q -u . a a3
  $ cd a3

  $ hg rebase --base 6 -m 'custom message'
  abort: message can only be specified with collapse
  [255]

  $ hg rebase --source 4 --collapse -m 'custom message'
  saved backup bundle to $TESTTMP/a3/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  6: 'custom message'
  |
  o  5: 'H'
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
  
  $ hg manifest
  A
  E
  F
  H

  $ cd ..

Create repo b:

  $ hg init b
  $ cd b

  $ echo A > A
  $ hg ci -Am A
  adding A
  $ echo B > B
  $ hg ci -Am B
  adding B

  $ hg up -q 0

  $ echo C > C
  $ hg ci -Am C
  adding C
  created new head

  $ hg merge
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)

  $ echo D > D
  $ hg ci -Am D
  adding D

  $ hg up -q 1

  $ echo E > E
  $ hg ci -Am E
  adding E
  created new head

  $ echo F > F
  $ hg ci -Am F
  adding F

  $ hg merge
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -m G

  $ hg up -q 0

  $ echo H > H
  $ hg ci -Am H
  adding H
  created new head

  $ hg tglog
  @  7: 'H'
  |
  | o    6: 'G'
  | |\
  | | o  5: 'F'
  | | |
  | | o  4: 'E'
  | | |
  | o |  3: 'D'
  | |\|
  | o |  2: 'C'
  |/ /
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


Rebase and collapse - more than one external (fail):

  $ hg clone -q -u . b b1
  $ cd b1

  $ hg rebase -s 2 --collapse
  abort: unable to collapse, there is more than one external parent
  [255]

Rebase and collapse - E onto H:

  $ hg rebase -s 4 --collapse
  saved backup bundle to $TESTTMP/b1/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @    5: 'Collapsed revision
  |\   * E
  | |  * F
  | |  * G'
  | o  4: 'H'
  | |
  o |    3: 'D'
  |\ \
  | o |  2: 'C'
  | |/
  o /  1: 'B'
  |/
  o  0: 'A'
  
  $ hg manifest
  A
  B
  C
  D
  E
  F
  H

  $ cd ..


Create repo c:

  $ hg init c
  $ cd c

  $ echo A > A
  $ hg ci -Am A
  adding A
  $ echo B > B
  $ hg ci -Am B
  adding B

  $ hg up -q 0

  $ echo C > C
  $ hg ci -Am C
  adding C
  created new head

  $ hg merge
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)

  $ echo D > D
  $ hg ci -Am D
  adding D

  $ hg up -q 1

  $ echo E > E
  $ hg ci -Am E
  adding E
  created new head
  $ echo F > E
  $ hg ci -m 'F'

  $ echo G > G
  $ hg ci -Am G
  adding G

  $ hg merge
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)

  $ hg ci -m H

  $ hg up -q 0

  $ echo I > I
  $ hg ci -Am I
  adding I
  created new head

  $ hg tglog
  @  8: 'I'
  |
  | o    7: 'H'
  | |\
  | | o  6: 'G'
  | | |
  | | o  5: 'F'
  | | |
  | | o  4: 'E'
  | | |
  | o |  3: 'D'
  | |\|
  | o |  2: 'C'
  |/ /
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


Rebase and collapse - E onto I:

  $ hg clone -q -u . c c1
  $ cd c1

  $ hg rebase -s 4 --collapse
  merging E
  saved backup bundle to $TESTTMP/c1/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @    5: 'Collapsed revision
  |\   * E
  | |  * F
  | |  * G
  | |  * H'
  | o  4: 'I'
  | |
  o |    3: 'D'
  |\ \
  | o |  2: 'C'
  | |/
  o /  1: 'B'
  |/
  o  0: 'A'
  
  $ hg manifest
  A
  B
  C
  D
  E
  G
  I

  $ cat E
  F

  $ cd ..


Create repo d:

  $ hg init d
  $ cd d

  $ echo A > A
  $ hg ci -Am A
  adding A
  $ echo B > B
  $ hg ci -Am B
  adding B
  $ echo C > C
  $ hg ci -Am C
  adding C

  $ hg up -q 1

  $ echo D > D
  $ hg ci -Am D
  adding D
  created new head
  $ hg merge
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)

  $ hg ci -m E

  $ hg up -q 0

  $ echo F > F
  $ hg ci -Am F
  adding F
  created new head

  $ hg tglog
  @  5: 'F'
  |
  | o    4: 'E'
  | |\
  | | o  3: 'D'
  | | |
  | o |  2: 'C'
  | |/
  | o  1: 'B'
  |/
  o  0: 'A'
  
  $ cd ..


Rebase and collapse - B onto F:

  $ hg clone -q -u . d d1
  $ cd d1

  $ hg rebase -s 1 --collapse
  saved backup bundle to $TESTTMP/d1/.hg/strip-backup/*-backup.hg (glob)

  $ hg tglog
  @  2: 'Collapsed revision
  |  * B
  |  * C
  |  * D
  |  * E'
  o  1: 'F'
  |
  o  0: 'A'
  
  $ hg manifest
  A
  B
  C
  D
  F

Interactions between collapse and keepbranches
  $ cd ..
  $ hg init e
  $ cd e
  $ echo 'a' > a
  $ hg ci -Am 'A'
  adding a

  $ hg branch '1'
  marked working directory as branch 1
  (branches are permanent and global, did you want a bookmark?)
  $ echo 'b' > b
  $ hg ci -Am 'B'
  adding b

  $ hg branch '2'
  marked working directory as branch 2
  (branches are permanent and global, did you want a bookmark?)
  $ echo 'c' > c
  $ hg ci -Am 'C'
  adding c

  $ hg up -q 0
  $ echo 'd' > d
  $ hg ci -Am 'D'
  adding d

  $ hg tglog
  @  3: 'D'
  |
  | o  2: 'C' 2
  | |
  | o  1: 'B' 1
  |/
  o  0: 'A'
  
  $ hg rebase --keepbranches --collapse -s 1 -d 3
  abort: cannot collapse multiple named branches
  [255]

  $ repeatchange() {
  >   hg checkout $1
  >   hg cp d z
  >   echo blah >> z
  >   hg commit -Am "$2" --user "$3"
  > }
  $ repeatchange 3 "E" "user1"
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ repeatchange 3 "E" "user2"
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  created new head
  $ hg tglog
  @  5: 'E'
  |
  | o  4: 'E'
  |/
  o  3: 'D'
  |
  | o  2: 'C' 2
  | |
  | o  1: 'B' 1
  |/
  o  0: 'A'
  
  $ hg rebase -s 5 -d 4
  saved backup bundle to $TESTTMP/e/.hg/strip-backup/*-backup.hg (glob)
  $ hg tglog
  @  4: 'E'
  |
  o  3: 'D'
  |
  | o  2: 'C' 2
  | |
  | o  1: 'B' 1
  |/
  o  0: 'A'
  
  $ hg export tip
  # HG changeset patch
  # User user1
  # Date 0 0
  # Node ID f338eb3c2c7cc5b5915676a2376ba7ac558c5213
  # Parent  41acb9dca9eb976e84cd21fcb756b4afa5a35c09
  E
  
  diff -r 41acb9dca9eb -r f338eb3c2c7c z
  --- /dev/null	Thu Jan 01 00:00:00 1970 +0000
  +++ b/z	Thu Jan 01 00:00:00 1970 +0000
  @@ -0,0 +1,2 @@
  +d
  +blah

  $ cd ..

Rebase, collapse and copies

  $ hg init copies
  $ cd copies
  $ hg unbundle "$TESTDIR/bundles/renames.hg"
  adding changesets
  adding manifests
  adding file changes
  added 4 changesets with 11 changes to 7 files (+1 heads)
  (run 'hg heads' to see heads, 'hg merge' to merge)
  $ hg up -q tip
  $ hg tglog
  @  3: 'move2'
  |
  o  2: 'move1'
  |
  | o  1: 'change'
  |/
  o  0: 'add'
  
  $ hg rebase --collapse -d 1
  merging a and d to d
  merging b and e to e
  merging c and f to f
  merging e and g to g
  merging f and c to c
  saved backup bundle to $TESTTMP/copies/.hg/strip-backup/*-backup.hg (glob)
  $ hg st
  $ hg st --copies --change .
  A d
    a
  A g
    b
  R b
  $ cat c
  c
  c
  $ cat d
  a
  a
  $ cat g
  b
  b
  $ hg log -r . --template "{file_copies}\n"
  d (a)g (b)

Test collapsing a middle revision in-place

  $ hg tglog
  @  2: 'Collapsed revision
  |  * move1
  |  * move2'
  o  1: 'change'
  |
  o  0: 'add'
  
  $ hg rebase --collapse -r 1 -d 0
  abort: can't remove original changesets with unrebased descendants
  (use --keep to keep original changesets)
  [255]

Test collapsing in place

  $ hg rebase --collapse -b . -d 0
  saved backup bundle to $TESTTMP/copies/.hg/strip-backup/1352765a01d4-backup.hg
  $ hg st --change . --copies
  M a
  M c
  A d
    a
  A g
    b
  R b
  $ cat a
  a
  a
  $ cat c
  c
  c
  $ cat d
  a
  a
  $ cat g
  b
  b
  $ cd ..
