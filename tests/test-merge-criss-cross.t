Criss cross merging

  $ hg init criss-cross
  $ cd criss-cross
  $ echo '0 base' > f1
  $ echo '0 base' > f2
  $ hg ci -Aqm '0 base'

  $ echo '1 first change' > f1
  $ hg ci -m '1 first change f1'

  $ hg up -qr0
  $ echo '2 first change' > f2
  $ hg ci -qm '2 first change f2'

  $ hg merge -qr 1
  $ hg ci -m '3 merge'

  $ hg up -qr2
  $ hg merge -qr1
  $ hg ci -qm '4 merge'

  $ echo '5 second change' > f1
  $ hg ci -m '5 second change f1'

  $ hg up -r3
  note: using 0f6b37dbe527 as ancestor of adfe50279922 and cf89f02107e5
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo '6 second change' > f2
  $ hg ci -m '6 second change f2'

  $ hg log -G
  @  changeset:   6:3b08d01b0ab5
  |  tag:         tip
  |  parent:      3:cf89f02107e5
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     6 second change f2
  |
  | o  changeset:   5:adfe50279922
  | |  user:        test
  | |  date:        Thu Jan 01 00:00:00 1970 +0000
  | |  summary:     5 second change f1
  | |
  | o    changeset:   4:7d3e55501ae6
  | |\   parent:      2:40663881a6dd
  | | |  parent:      1:0f6b37dbe527
  | | |  user:        test
  | | |  date:        Thu Jan 01 00:00:00 1970 +0000
  | | |  summary:     4 merge
  | | |
  o---+  changeset:   3:cf89f02107e5
  | | |  parent:      2:40663881a6dd
  |/ /   parent:      1:0f6b37dbe527
  | |    user:        test
  | |    date:        Thu Jan 01 00:00:00 1970 +0000
  | |    summary:     3 merge
  | |
  | o  changeset:   2:40663881a6dd
  | |  parent:      0:40494bf2444c
  | |  user:        test
  | |  date:        Thu Jan 01 00:00:00 1970 +0000
  | |  summary:     2 first change f2
  | |
  o |  changeset:   1:0f6b37dbe527
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     1 first change f1
  |
  o  changeset:   0:40494bf2444c
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     0 base
  

  $ hg merge -v --debug --tool internal:dump 5
  note: using 0f6b37dbe527 as ancestor of 3b08d01b0ab5 and adfe50279922
    searching for copies back to rev 3
  resolving manifests
   branchmerge: True, force: False, partial: False
   ancestor: 0f6b37dbe527, local: 3b08d01b0ab5+, remote: adfe50279922
   f1: remote is newer -> g
   f2: versions differ -> m
    preserving f2 for resolve of f2
  getting f1
  updating: f1 1/2 files (50.00%)
  updating: f2 2/2 files (100.00%)
  picked tool 'internal:dump' for f2 (binary False symlink False)
  merging f2
  my f2@3b08d01b0ab5+ other f2@adfe50279922 ancestor f2@40494bf2444c
  1 files updated, 0 files merged, 0 files removed, 1 files unresolved
  use 'hg resolve' to retry unresolved file merges or 'hg update -C .' to abandon
  [1]

  $ head *
  ==> f1 <==
  5 second change
  
  ==> f2 <==
  6 second change
  
  ==> f2.base <==
  0 base
  
  ==> f2.local <==
  6 second change
  
  ==> f2.orig <==
  6 second change
  
  ==> f2.other <==
  2 first change

  $ cd ..
