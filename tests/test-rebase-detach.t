  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > rebase=
  > 
  > [alias]
  > tglog = log -G --template "{rev}: '{desc}'\n"
  > 
  > [extensions]
  > drawdag=$TESTDIR/drawdag.py
  > EOF

Rebasing D onto B detaching from C (one commit):

  $ hg init a1
  $ cd a1

  $ hg debugdrawdag <<EOF
  > D
  > |
  > C B
  > |/
  > A
  > EOF
  $ hg phase --force --secret D

  $ hg rebase -s D -d B
  rebasing 3:e7b3f00ed42e "D" (D tip)
  saved backup bundle to $TESTTMP/a1/.hg/strip-backup/e7b3f00ed42e-6f368371-rebase.hg (glob)

  $ hg log -G --template "{rev}:{phase} '{desc}' {branches}\n"
  o  3:secret 'D'
  |
  | o  2:draft 'C'
  | |
  o |  1:draft 'B'
  |/
  o  0:draft 'A'
  
  $ hg manifest --rev tip
  A
  B
  D

  $ cd ..


Rebasing D onto B detaching from C (two commits):

  $ hg init a2
  $ cd a2

  $ hg debugdrawdag <<EOF
  > E
  > |
  > D
  > |
  > C B
  > |/
  > A
  > EOF

  $ hg rebase -s D -d B
  rebasing 3:e7b3f00ed42e "D" (D)
  rebasing 4:69a34c08022a "E" (E tip)
  saved backup bundle to $TESTTMP/a2/.hg/strip-backup/e7b3f00ed42e-a2ec7cea-rebase.hg (glob)

  $ hg tglog
  o  4: 'E'
  |
  o  3: 'D'
  |
  | o  2: 'C'
  | |
  o |  1: 'B'
  |/
  o  0: 'A'
  
  $ hg manifest --rev tip
  A
  B
  D
  E

  $ cd ..

Rebasing C onto B using detach (same as not using it):

  $ hg init a3
  $ cd a3

  $ hg debugdrawdag <<EOF
  > D
  > |
  > C B
  > |/
  > A
  > EOF

  $ hg rebase -s C -d B
  rebasing 2:dc0947a82db8 "C" (C)
  rebasing 3:e7b3f00ed42e "D" (D tip)
  saved backup bundle to $TESTTMP/a3/.hg/strip-backup/dc0947a82db8-b8481714-rebase.hg (glob)

  $ hg tglog
  o  3: 'D'
  |
  o  2: 'C'
  |
  o  1: 'B'
  |
  o  0: 'A'
  
  $ hg manifest --rev tip
  A
  B
  C
  D

  $ cd ..


Rebasing D onto B detaching from C and collapsing:

  $ hg init a4
  $ cd a4

  $ hg debugdrawdag <<EOF
  > E
  > |
  > D
  > |
  > C B
  > |/
  > A
  > EOF
  $ hg phase --force --secret E

  $ hg rebase --collapse -s D -d B
  rebasing 3:e7b3f00ed42e "D" (D)
  rebasing 4:69a34c08022a "E" (E tip)
  saved backup bundle to $TESTTMP/a4/.hg/strip-backup/e7b3f00ed42e-a2ec7cea-rebase.hg (glob)

  $ hg  log -G --template "{rev}:{phase} '{desc}' {branches}\n"
  o  3:secret 'Collapsed revision
  |  * D
  |  * E'
  | o  2:draft 'C'
  | |
  o |  1:draft 'B'
  |/
  o  0:draft 'A'
  
  $ hg manifest --rev tip
  A
  B
  D
  E

  $ cd ..

Rebasing across null as ancestor
  $ hg init a5
  $ cd a5

  $ hg debugdrawdag <<EOF
  > E
  > |
  > D
  > |
  > C
  > |
  > A B
  > EOF

  $ hg rebase -s C -d B
  rebasing 2:dc0947a82db8 "C" (C)
  rebasing 3:e7b3f00ed42e "D" (D)
  rebasing 4:69a34c08022a "E" (E tip)
  saved backup bundle to $TESTTMP/a5/.hg/strip-backup/dc0947a82db8-3eefec98-rebase.hg (glob)

  $ hg tglog
  o  4: 'E'
  |
  o  3: 'D'
  |
  o  2: 'C'
  |
  o  1: 'B'
  
  o  0: 'A'
  
  $ hg rebase -d 1 -s 3
  rebasing 3:e9153d36a1af "D"
  rebasing 4:e3d0c70d606d "E" (tip)
  saved backup bundle to $TESTTMP/a5/.hg/strip-backup/e9153d36a1af-db7388ed-rebase.hg (glob)
  $ hg tglog
  o  4: 'E'
  |
  o  3: 'D'
  |
  | o  2: 'C'
  |/
  o  1: 'B'
  
  o  0: 'A'
  
  $ cd ..

Verify that target is not selected as external rev (issue3085)

  $ hg init a6
  $ cd a6

  $ hg debugdrawdag <<EOF
  > H
  > | G
  > |/|
  > F E
  > |/
  > A
  > EOF
  $ hg up -q G

  $ echo "I" >> E
  $ hg ci -m "I"
  $ hg tag --local I
  $ hg merge H
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -m "Merge"
  $ echo "J" >> F
  $ hg ci -m "J"
  $ hg tglog
  @  7: 'J'
  |
  o    6: 'Merge'
  |\
  | o  5: 'I'
  | |
  o |  4: 'H'
  | |
  | o  3: 'G'
  |/|
  o |  2: 'F'
  | |
  | o  1: 'E'
  |/
  o  0: 'A'
  
  $ hg rebase -s I -d H --collapse --config ui.merge=internal:other
  rebasing 5:b92d164ad3cb "I" (I)
  rebasing 6:0cfbc7e8faaf "Merge"
  rebasing 7:c6aaf0d259c0 "J" (tip)
  saved backup bundle to $TESTTMP/a6/.hg/strip-backup/b92d164ad3cb-88fd7ab7-rebase.hg (glob)

  $ hg tglog
  @  5: 'Collapsed revision
  |  * I
  |  * Merge
  |  * J'
  o  4: 'H'
  |
  | o  3: 'G'
  |/|
  o |  2: 'F'
  | |
  | o  1: 'E'
  |/
  o  0: 'A'
  

  $ hg log --rev tip
  changeset:   5:65079693dac4
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     Collapsed revision
  

  $ cd ..

Ensure --continue restores a correct state (issue3046) and phase:
  $ hg init a7
  $ cd a7

  $ hg debugdrawdag <<EOF
  > C B
  > |/
  > A
  > EOF
  $ hg up -q C
  $ echo 'B2' > B
  $ hg ci -A -m 'B2'
  adding B
  $ hg phase --force --secret .
  $ hg rebase -s . -d B --config ui.merge=internal:fail
  rebasing 3:17b4880d2402 "B2" (tip)
  merging B
  warning: conflicts while merging B! (edit, then use 'hg resolve --mark')
  unresolved conflicts (see hg resolve, then hg rebase --continue)
  [1]
  $ hg resolve --all -t internal:local
  (no more unresolved files)
  continue: hg rebase --continue
  $ hg rebase -c
  rebasing 3:17b4880d2402 "B2" (tip)
  note: rebase of 3:17b4880d2402 created no changes to commit
  saved backup bundle to $TESTTMP/a7/.hg/strip-backup/17b4880d2402-1ae1f6cc-rebase.hg (glob)
  $ hg  log -G --template "{rev}:{phase} '{desc}' {branches}\n"
  o  2:draft 'C'
  |
  | @  1:draft 'B'
  |/
  o  0:draft 'A'
  

  $ cd ..
