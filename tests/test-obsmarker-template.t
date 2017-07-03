This test file test the various templates related to obsmarkers.

Global setup
============

  $ . $TESTDIR/testlib/obsmarker-common.sh
  $ cat >> $HGRCPATH <<EOF
  > [ui]
  > interactive = true
  > [phases]
  > publish=False
  > [experimental]
  > evolution=all
  > [alias]
  > tlog = log -G -T '{node|short}\
  >     {if(predecessors, "\n  Predecessors: {predecessors}")}\
  >     {if(predecessors, "\n  semi-colon: {join(predecessors, "; ")}")}\
  >     {if(predecessors, "\n  json: {predecessors|json}")}\
  >     {if(predecessors, "\n  map: {join(predecessors % "{rev}:{node}", " ")}")}\
  >     {if(successorssets, "\n  Successors: {successorssets}")}\
  >     {if(successorssets, "\n  multi-line: {join(successorssets, "\n  multi-line: ")}")}\
  >     {if(successorssets, "\n  json: {successorssets|json}")}\n'
  > EOF

Test templates on amended commit
================================

Test setup
----------

  $ hg init $TESTTMP/templates-local-amend
  $ cd $TESTTMP/templates-local-amend
  $ mkcommit ROOT
  $ mkcommit A0
  $ echo 42 >> A0
  $ hg commit --amend -m "A1"
  $ hg commit --amend -m "A2"

  $ hg log --hidden -G
  @  changeset:   4:d004c8f274b9
  |  tag:         tip
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     A2
  |
  | x  changeset:   3:a468dc9b3633
  |/   parent:      0:ea207398892e
  |    user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A1
  |
  | x  changeset:   2:f137d23bb3e1
  | |  user:        test
  | |  date:        Thu Jan 01 00:00:00 1970 +0000
  | |  summary:     temporary amend commit for 471f378eab4c
  | |
  | x  changeset:   1:471f378eab4c
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
Check templates
---------------
  $ hg up 'desc(A0)' --hidden
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should show current revision as it is the working copy
  $ hg tlog
  o  d004c8f274b9
  |    Predecessors: 1:471f378eab4c
  |    semi-colon: 1:471f378eab4c
  |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | @  471f378eab4c
  |/     Successors: 4:d004c8f274b9
  |      multi-line: 4:d004c8f274b9
  |      json: [["d004c8f274b9ec480a47a93c10dac5eee63adb78"]]
  o  ea207398892e
  
  $ hg up 'desc(A1)' --hidden
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should show current revision as it is the working copy
  $ hg tlog
  o  d004c8f274b9
  |    Predecessors: 3:a468dc9b3633
  |    semi-colon: 3:a468dc9b3633
  |    json: ["a468dc9b36338b14fdb7825f55ce3df4e71517ad"]
  |    map: 3:a468dc9b36338b14fdb7825f55ce3df4e71517ad
  | @  a468dc9b3633
  |/     Successors: 4:d004c8f274b9
  |      multi-line: 4:d004c8f274b9
  |      json: [["d004c8f274b9ec480a47a93c10dac5eee63adb78"]]
  o  ea207398892e
  
Predecessors template should show all the predecessors as we force their display
with --hidden
  $ hg tlog --hidden
  o  d004c8f274b9
  |    Predecessors: 3:a468dc9b3633
  |    semi-colon: 3:a468dc9b3633
  |    json: ["a468dc9b36338b14fdb7825f55ce3df4e71517ad"]
  |    map: 3:a468dc9b36338b14fdb7825f55ce3df4e71517ad
  | @  a468dc9b3633
  |/     Predecessors: 1:471f378eab4c
  |      semi-colon: 1:471f378eab4c
  |      json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |      map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  |      Successors: 4:d004c8f274b9
  |      multi-line: 4:d004c8f274b9
  |      json: [["d004c8f274b9ec480a47a93c10dac5eee63adb78"]]
  | x  f137d23bb3e1
  | |
  | x  471f378eab4c
  |/     Successors: 3:a468dc9b3633
  |      multi-line: 3:a468dc9b3633
  |      json: [["a468dc9b36338b14fdb7825f55ce3df4e71517ad"]]
  o  ea207398892e
  

Predecessors template shouldn't show anything as all obsolete commit are not
visible.
  $ hg up 'desc(A2)'
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg tlog
  @  d004c8f274b9
  |
  o  ea207398892e
  
  $ hg tlog --hidden
  @  d004c8f274b9
  |    Predecessors: 3:a468dc9b3633
  |    semi-colon: 3:a468dc9b3633
  |    json: ["a468dc9b36338b14fdb7825f55ce3df4e71517ad"]
  |    map: 3:a468dc9b36338b14fdb7825f55ce3df4e71517ad
  | x  a468dc9b3633
  |/     Predecessors: 1:471f378eab4c
  |      semi-colon: 1:471f378eab4c
  |      json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |      map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  |      Successors: 4:d004c8f274b9
  |      multi-line: 4:d004c8f274b9
  |      json: [["d004c8f274b9ec480a47a93c10dac5eee63adb78"]]
  | x  f137d23bb3e1
  | |
  | x  471f378eab4c
  |/     Successors: 3:a468dc9b3633
  |      multi-line: 3:a468dc9b3633
  |      json: [["a468dc9b36338b14fdb7825f55ce3df4e71517ad"]]
  o  ea207398892e
  

Test templates with splitted commit
===================================

  $ hg init $TESTTMP/templates-local-split
  $ cd $TESTTMP/templates-local-split
  $ mkcommit ROOT
  $ echo 42 >> a
  $ echo 43 >> b
  $ hg commit -A -m "A0"
  adding a
  adding b
  $ hg log --hidden -G
  @  changeset:   1:471597cad322
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
# Simulate split
  $ hg up -r "desc(ROOT)"
  0 files updated, 0 files merged, 2 files removed, 0 files unresolved
  $ echo 42 >> a
  $ hg commit -A -m "A0"
  adding a
  created new head
  $ echo 43 >> b
  $ hg commit -A -m "A0"
  adding b
  $ hg debugobsolete `getid "1"` `getid "2"` `getid "3"`

  $ hg log --hidden -G
  @  changeset:   3:f257fde29c7a
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     A0
  |
  o  changeset:   2:337fec4d2edc
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     A0
  |
  | x  changeset:   1:471597cad322
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
Check templates
---------------

  $ hg up 'obsolete()' --hidden
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should show current revision as it is the working copy
  $ hg tlog
  o  f257fde29c7a
  |    Predecessors: 1:471597cad322
  |    semi-colon: 1:471597cad322
  |    json: ["471597cad322d1f659bb169751be9133dad92ef3"]
  |    map: 1:471597cad322d1f659bb169751be9133dad92ef3
  o  337fec4d2edc
  |    Predecessors: 1:471597cad322
  |    semi-colon: 1:471597cad322
  |    json: ["471597cad322d1f659bb169751be9133dad92ef3"]
  |    map: 1:471597cad322d1f659bb169751be9133dad92ef3
  | @  471597cad322
  |/     Successors: 2:337fec4d2edc 3:f257fde29c7a
  |      multi-line: 2:337fec4d2edc 3:f257fde29c7a
  |      json: [["337fec4d2edcf0e7a467e35f818234bc620068b5", "f257fde29c7a847c9b607f6e958656d0df0fb15c"]]
  o  ea207398892e
  
  $ hg up f257fde29c7a
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should not show a predecessor as it's not displayed in
the log
  $ hg tlog
  @  f257fde29c7a
  |
  o  337fec4d2edc
  |
  o  ea207398892e
  
Predecessors template should show both predecessors as we force their display
with --hidden
  $ hg tlog --hidden
  @  f257fde29c7a
  |    Predecessors: 1:471597cad322
  |    semi-colon: 1:471597cad322
  |    json: ["471597cad322d1f659bb169751be9133dad92ef3"]
  |    map: 1:471597cad322d1f659bb169751be9133dad92ef3
  o  337fec4d2edc
  |    Predecessors: 1:471597cad322
  |    semi-colon: 1:471597cad322
  |    json: ["471597cad322d1f659bb169751be9133dad92ef3"]
  |    map: 1:471597cad322d1f659bb169751be9133dad92ef3
  | x  471597cad322
  |/     Successors: 2:337fec4d2edc 3:f257fde29c7a
  |      multi-line: 2:337fec4d2edc 3:f257fde29c7a
  |      json: [["337fec4d2edcf0e7a467e35f818234bc620068b5", "f257fde29c7a847c9b607f6e958656d0df0fb15c"]]
  o  ea207398892e
  
Test templates with folded commit
=================================

Test setup
----------

  $ hg init $TESTTMP/templates-local-fold
  $ cd $TESTTMP/templates-local-fold
  $ mkcommit ROOT
  $ mkcommit A0
  $ mkcommit B0
  $ hg log --hidden -G
  @  changeset:   2:0dec01379d3b
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     B0
  |
  o  changeset:   1:471f378eab4c
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
Simulate a fold
  $ hg up -r "desc(ROOT)"
  0 files updated, 0 files merged, 2 files removed, 0 files unresolved
  $ echo "A0" > A0
  $ echo "B0" > B0
  $ hg commit -A -m "C0"
  adding A0
  adding B0
  created new head
  $ hg debugobsolete `getid "desc(A0)"` `getid "desc(C0)"`
  $ hg debugobsolete `getid "desc(B0)"` `getid "desc(C0)"`

  $ hg log --hidden -G
  @  changeset:   3:eb5a0daa2192
  |  tag:         tip
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     C0
  |
  | x  changeset:   2:0dec01379d3b
  | |  user:        test
  | |  date:        Thu Jan 01 00:00:00 1970 +0000
  | |  summary:     B0
  | |
  | x  changeset:   1:471f378eab4c
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
Check templates
---------------

  $ hg up 'desc(A0)' --hidden
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved

Predecessors template should show current revision as it is the working copy
  $ hg tlog
  o  eb5a0daa2192
  |    Predecessors: 1:471f378eab4c
  |    semi-colon: 1:471f378eab4c
  |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | @  471f378eab4c
  |/     Successors: 3:eb5a0daa2192
  |      multi-line: 3:eb5a0daa2192
  |      json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  o  ea207398892e
  
  $ hg up 'desc(B0)' --hidden
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should show both predecessors as they should be both
displayed
  $ hg tlog
  o  eb5a0daa2192
  |    Predecessors: 2:0dec01379d3b 1:471f378eab4c
  |    semi-colon: 2:0dec01379d3b; 1:471f378eab4c
  |    json: ["0dec01379d3be6318c470ead31b1fe7ae7cb53d5", "471f378eab4c5e25f6c77f785b27c936efb22874"]
  |    map: 2:0dec01379d3be6318c470ead31b1fe7ae7cb53d5 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | @  0dec01379d3b
  | |    Successors: 3:eb5a0daa2192
  | |    multi-line: 3:eb5a0daa2192
  | |    json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  | x  471f378eab4c
  |/     Successors: 3:eb5a0daa2192
  |      multi-line: 3:eb5a0daa2192
  |      json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  o  ea207398892e
  
  $ hg up 'desc(C0)'
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should not show predecessors as they are not displayed in
the log
  $ hg tlog
  @  eb5a0daa2192
  |
  o  ea207398892e
  
Predecessors template should show both predecessors as we force their display
with --hidden
  $ hg tlog --hidden
  @  eb5a0daa2192
  |    Predecessors: 2:0dec01379d3b 1:471f378eab4c
  |    semi-colon: 2:0dec01379d3b; 1:471f378eab4c
  |    json: ["0dec01379d3be6318c470ead31b1fe7ae7cb53d5", "471f378eab4c5e25f6c77f785b27c936efb22874"]
  |    map: 2:0dec01379d3be6318c470ead31b1fe7ae7cb53d5 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | x  0dec01379d3b
  | |    Successors: 3:eb5a0daa2192
  | |    multi-line: 3:eb5a0daa2192
  | |    json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  | x  471f378eab4c
  |/     Successors: 3:eb5a0daa2192
  |      multi-line: 3:eb5a0daa2192
  |      json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  o  ea207398892e
  

Test templates with divergence
==============================

Test setup
----------

  $ hg init $TESTTMP/templates-local-divergence
  $ cd $TESTTMP/templates-local-divergence
  $ mkcommit ROOT
  $ mkcommit A0
  $ hg commit --amend -m "A1"
  $ hg log --hidden -G
  @  changeset:   2:fdf9bde5129a
  |  tag:         tip
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     A1
  |
  | x  changeset:   1:471f378eab4c
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
  $ hg update --hidden 'desc(A0)'
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg commit --amend -m "A2"
  $ hg log --hidden -G
  @  changeset:   3:65b757b745b9
  |  tag:         tip
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  trouble:     divergent
  |  summary:     A2
  |
  | o  changeset:   2:fdf9bde5129a
  |/   parent:      0:ea207398892e
  |    user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    trouble:     divergent
  |    summary:     A1
  |
  | x  changeset:   1:471f378eab4c
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
  $ hg commit --amend -m 'A3'
  $ hg log --hidden -G
  @  changeset:   4:019fadeab383
  |  tag:         tip
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  trouble:     divergent
  |  summary:     A3
  |
  | x  changeset:   3:65b757b745b9
  |/   parent:      0:ea207398892e
  |    user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A2
  |
  | o  changeset:   2:fdf9bde5129a
  |/   parent:      0:ea207398892e
  |    user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    trouble:     divergent
  |    summary:     A1
  |
  | x  changeset:   1:471f378eab4c
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  

Check templates
---------------

  $ hg up 'desc(A0)' --hidden
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should show current revision as it is the working copy
  $ hg tlog
  o  019fadeab383
  |    Predecessors: 1:471f378eab4c
  |    semi-colon: 1:471f378eab4c
  |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | o  fdf9bde5129a
  |/     Predecessors: 1:471f378eab4c
  |      semi-colon: 1:471f378eab4c
  |      json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |      map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | @  471f378eab4c
  |/     Successors: 2:fdf9bde5129a; 4:019fadeab383
  |      multi-line: 2:fdf9bde5129a
  |      multi-line: 4:019fadeab383
  |      json: [["fdf9bde5129a28d4548fadd3f62b265cdd3b7a2e"], ["019fadeab383f6699fa83ad7bdb4d82ed2c0e5ab"]]
  o  ea207398892e
  
  $ hg up 'desc(A1)'
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should not show predecessors as they are not displayed in
the log
  $ hg tlog
  o  019fadeab383
  |
  | @  fdf9bde5129a
  |/
  o  ea207398892e
  
Predecessors template should the predecessors as we force their display with
--hidden
  $ hg tlog --hidden
  o  019fadeab383
  |    Predecessors: 3:65b757b745b9
  |    semi-colon: 3:65b757b745b9
  |    json: ["65b757b745b935093c87a2bccd877521cccffcbd"]
  |    map: 3:65b757b745b935093c87a2bccd877521cccffcbd
  | x  65b757b745b9
  |/     Predecessors: 1:471f378eab4c
  |      semi-colon: 1:471f378eab4c
  |      json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |      map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  |      Successors: 4:019fadeab383
  |      multi-line: 4:019fadeab383
  |      json: [["019fadeab383f6699fa83ad7bdb4d82ed2c0e5ab"]]
  | @  fdf9bde5129a
  |/     Predecessors: 1:471f378eab4c
  |      semi-colon: 1:471f378eab4c
  |      json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |      map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | x  471f378eab4c
  |/     Successors: 2:fdf9bde5129a; 3:65b757b745b9
  |      multi-line: 2:fdf9bde5129a
  |      multi-line: 3:65b757b745b9
  |      json: [["fdf9bde5129a28d4548fadd3f62b265cdd3b7a2e"], ["65b757b745b935093c87a2bccd877521cccffcbd"]]
  o  ea207398892e
  

Test templates with amended + folded commit
===========================================

Test setup
----------

  $ hg init $TESTTMP/templates-local-amend-fold
  $ cd $TESTTMP/templates-local-amend-fold
  $ mkcommit ROOT
  $ mkcommit A0
  $ mkcommit B0
  $ hg commit --amend -m "B1"
  $ hg log --hidden -G
  @  changeset:   3:b7ea6d14e664
  |  tag:         tip
  |  parent:      1:471f378eab4c
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     B1
  |
  | x  changeset:   2:0dec01379d3b
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     B0
  |
  o  changeset:   1:471f378eab4c
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
# Simulate a fold
  $ hg up -r "desc(ROOT)"
  0 files updated, 0 files merged, 2 files removed, 0 files unresolved
  $ echo "A0" > A0
  $ echo "B0" > B0
  $ hg commit -A -m "C0"
  adding A0
  adding B0
  created new head
  $ hg debugobsolete `getid "desc(A0)"` `getid "desc(C0)"`
  $ hg debugobsolete `getid "desc(B1)"` `getid "desc(C0)"`

  $ hg log --hidden -G
  @  changeset:   4:eb5a0daa2192
  |  tag:         tip
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     C0
  |
  | x  changeset:   3:b7ea6d14e664
  | |  parent:      1:471f378eab4c
  | |  user:        test
  | |  date:        Thu Jan 01 00:00:00 1970 +0000
  | |  summary:     B1
  | |
  | | x  changeset:   2:0dec01379d3b
  | |/   user:        test
  | |    date:        Thu Jan 01 00:00:00 1970 +0000
  | |    summary:     B0
  | |
  | x  changeset:   1:471f378eab4c
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
Check templates
---------------

  $ hg up 'desc(A0)' --hidden
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved

Predecessors template should show current revision as it is the working copy
  $ hg tlog
  o  eb5a0daa2192
  |    Predecessors: 1:471f378eab4c
  |    semi-colon: 1:471f378eab4c
  |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | @  471f378eab4c
  |/     Successors: 4:eb5a0daa2192
  |      multi-line: 4:eb5a0daa2192
  |      json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  o  ea207398892e
  
  $ hg up 'desc(B0)' --hidden
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should both predecessors as they are visible
  $ hg tlog
  o  eb5a0daa2192
  |    Predecessors: 2:0dec01379d3b 1:471f378eab4c
  |    semi-colon: 2:0dec01379d3b; 1:471f378eab4c
  |    json: ["0dec01379d3be6318c470ead31b1fe7ae7cb53d5", "471f378eab4c5e25f6c77f785b27c936efb22874"]
  |    map: 2:0dec01379d3be6318c470ead31b1fe7ae7cb53d5 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | @  0dec01379d3b
  | |    Successors: 4:eb5a0daa2192
  | |    multi-line: 4:eb5a0daa2192
  | |    json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  | x  471f378eab4c
  |/     Successors: 4:eb5a0daa2192
  |      multi-line: 4:eb5a0daa2192
  |      json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  o  ea207398892e
  
  $ hg up 'desc(B1)' --hidden
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should both predecessors as they are visible
  $ hg tlog
  o  eb5a0daa2192
  |    Predecessors: 1:471f378eab4c 3:b7ea6d14e664
  |    semi-colon: 1:471f378eab4c; 3:b7ea6d14e664
  |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874", "b7ea6d14e664bdc8922221f7992631b50da3fb07"]
  |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874 3:b7ea6d14e664bdc8922221f7992631b50da3fb07
  | @  b7ea6d14e664
  | |    Successors: 4:eb5a0daa2192
  | |    multi-line: 4:eb5a0daa2192
  | |    json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  | x  471f378eab4c
  |/     Successors: 4:eb5a0daa2192
  |      multi-line: 4:eb5a0daa2192
  |      json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  o  ea207398892e
  
  $ hg up 'desc(C0)'
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should show no predecessors as they are both non visible
  $ hg tlog
  @  eb5a0daa2192
  |
  o  ea207398892e
  
Predecessors template should show all predecessors as we force their display
with --hidden
  $ hg tlog --hidden
  @  eb5a0daa2192
  |    Predecessors: 1:471f378eab4c 3:b7ea6d14e664
  |    semi-colon: 1:471f378eab4c; 3:b7ea6d14e664
  |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874", "b7ea6d14e664bdc8922221f7992631b50da3fb07"]
  |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874 3:b7ea6d14e664bdc8922221f7992631b50da3fb07
  | x  b7ea6d14e664
  | |    Predecessors: 2:0dec01379d3b
  | |    semi-colon: 2:0dec01379d3b
  | |    json: ["0dec01379d3be6318c470ead31b1fe7ae7cb53d5"]
  | |    map: 2:0dec01379d3be6318c470ead31b1fe7ae7cb53d5
  | |    Successors: 4:eb5a0daa2192
  | |    multi-line: 4:eb5a0daa2192
  | |    json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  | | x  0dec01379d3b
  | |/     Successors: 3:b7ea6d14e664
  | |      multi-line: 3:b7ea6d14e664
  | |      json: [["b7ea6d14e664bdc8922221f7992631b50da3fb07"]]
  | x  471f378eab4c
  |/     Successors: 4:eb5a0daa2192
  |      multi-line: 4:eb5a0daa2192
  |      json: [["eb5a0daa21923bbf8caeb2c42085b9e463861fd0"]]
  o  ea207398892e
  

Test template with pushed and pulled obs markers
================================================

Test setup
----------

  $ hg init $TESTTMP/templates-local-remote-markers-1
  $ cd $TESTTMP/templates-local-remote-markers-1
  $ mkcommit ROOT
  $ mkcommit A0
  $ hg clone $TESTTMP/templates-local-remote-markers-1 $TESTTMP/templates-local-remote-markers-2
  updating to branch default
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd $TESTTMP/templates-local-remote-markers-2
  $ hg log --hidden -G
  @  changeset:   1:471f378eab4c
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
  $ cd $TESTTMP/templates-local-remote-markers-1
  $ hg commit --amend -m "A1"
  $ hg commit --amend -m "A2"
  $ hg log --hidden -G
  @  changeset:   3:7a230b46bf61
  |  tag:         tip
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     A2
  |
  | x  changeset:   2:fdf9bde5129a
  |/   parent:      0:ea207398892e
  |    user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A1
  |
  | x  changeset:   1:471f378eab4c
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
  $ cd $TESTTMP/templates-local-remote-markers-2
  $ hg pull
  pulling from $TESTTMP/templates-local-remote-markers-1 (glob)
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 0 changes to 1 files (+1 heads)
  2 new obsolescence markers
  obsoleted 1 changesets
  (run 'hg heads' to see heads, 'hg merge' to merge)
  $ hg log --hidden -G
  o  changeset:   2:7a230b46bf61
  |  tag:         tip
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     A2
  |
  | @  changeset:   1:471f378eab4c
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     A0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  

  $ hg debugobsolete
  471f378eab4c5e25f6c77f785b27c936efb22874 fdf9bde5129a28d4548fadd3f62b265cdd3b7a2e 0 (Thu Jan 01 00:00:00 1970 +0000) {'user': 'test'}
  fdf9bde5129a28d4548fadd3f62b265cdd3b7a2e 7a230b46bf61e50b30308c6cfd7bd1269ef54702 0 (Thu Jan 01 00:00:00 1970 +0000) {'user': 'test'}

Check templates
---------------

Predecessors template should show current revision as it is the working copy
  $ hg tlog
  o  7a230b46bf61
  |    Predecessors: 1:471f378eab4c
  |    semi-colon: 1:471f378eab4c
  |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | @  471f378eab4c
  |/     Successors: 2:7a230b46bf61
  |      multi-line: 2:7a230b46bf61
  |      json: [["7a230b46bf61e50b30308c6cfd7bd1269ef54702"]]
  o  ea207398892e
  
  $ hg up 'desc(A2)'
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved

Predecessors template should show no predecessors as they are non visible
  $ hg tlog
  @  7a230b46bf61
  |
  o  ea207398892e
  
Predecessors template should show all predecessors as we force their display
with --hidden
  $ hg tlog --hidden
  @  7a230b46bf61
  |    Predecessors: 1:471f378eab4c
  |    semi-colon: 1:471f378eab4c
  |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | x  471f378eab4c
  |/     Successors: 2:7a230b46bf61
  |      multi-line: 2:7a230b46bf61
  |      json: [["7a230b46bf61e50b30308c6cfd7bd1269ef54702"]]
  o  ea207398892e
  

Test template with obsmarkers cycle
===================================

Test setup
----------

  $ hg init $TESTTMP/templates-local-cycle
  $ cd $TESTTMP/templates-local-cycle
  $ mkcommit ROOT
  $ mkcommit A0
  $ mkcommit B0
  $ hg up -r 0
  0 files updated, 0 files merged, 2 files removed, 0 files unresolved
  $ mkcommit C0
  created new head

Create the cycle

  $ hg debugobsolete `getid "desc(A0)"` `getid "desc(B0)"`
  $ hg debugobsolete `getid "desc(B0)"` `getid "desc(C0)"`
  $ hg debugobsolete `getid "desc(B0)"` `getid "desc(A0)"`

Check templates
---------------

  $ hg tlog
  @  f897c6137566
  |
  o  ea207398892e
  

  $ hg up -r "desc(B0)" --hidden
  2 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ hg tlog
  o  f897c6137566
  |    Predecessors: 2:0dec01379d3b
  |    semi-colon: 2:0dec01379d3b
  |    json: ["0dec01379d3be6318c470ead31b1fe7ae7cb53d5"]
  |    map: 2:0dec01379d3be6318c470ead31b1fe7ae7cb53d5
  | @  0dec01379d3b
  | |    Predecessors: 1:471f378eab4c
  | |    semi-colon: 1:471f378eab4c
  | |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  | |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | |    Successors: 3:f897c6137566; 1:471f378eab4c
  | |    multi-line: 3:f897c6137566
  | |    multi-line: 1:471f378eab4c
  | |    json: [["f897c6137566320b081514b4c7227ecc3d384b39"], ["471f378eab4c5e25f6c77f785b27c936efb22874"]]
  | x  471f378eab4c
  |/     Predecessors: 2:0dec01379d3b
  |      semi-colon: 2:0dec01379d3b
  |      json: ["0dec01379d3be6318c470ead31b1fe7ae7cb53d5"]
  |      map: 2:0dec01379d3be6318c470ead31b1fe7ae7cb53d5
  |      Successors: 2:0dec01379d3b
  |      multi-line: 2:0dec01379d3b
  |      json: [["0dec01379d3be6318c470ead31b1fe7ae7cb53d5"]]
  o  ea207398892e
  

  $ hg up -r "desc(A0)" --hidden
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ hg tlog
  o  f897c6137566
  |    Predecessors: 1:471f378eab4c
  |    semi-colon: 1:471f378eab4c
  |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | @  471f378eab4c
  |/
  o  ea207398892e
  

  $ hg up -r "desc(ROOT)" --hidden
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ hg tlog
  o  f897c6137566
  |
  @  ea207398892e
  

  $ hg tlog --hidden
  o  f897c6137566
  |    Predecessors: 2:0dec01379d3b
  |    semi-colon: 2:0dec01379d3b
  |    json: ["0dec01379d3be6318c470ead31b1fe7ae7cb53d5"]
  |    map: 2:0dec01379d3be6318c470ead31b1fe7ae7cb53d5
  | x  0dec01379d3b
  | |    Predecessors: 1:471f378eab4c
  | |    semi-colon: 1:471f378eab4c
  | |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  | |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | |    Successors: 3:f897c6137566; 1:471f378eab4c
  | |    multi-line: 3:f897c6137566
  | |    multi-line: 1:471f378eab4c
  | |    json: [["f897c6137566320b081514b4c7227ecc3d384b39"], ["471f378eab4c5e25f6c77f785b27c936efb22874"]]
  | x  471f378eab4c
  |/     Predecessors: 2:0dec01379d3b
  |      semi-colon: 2:0dec01379d3b
  |      json: ["0dec01379d3be6318c470ead31b1fe7ae7cb53d5"]
  |      map: 2:0dec01379d3be6318c470ead31b1fe7ae7cb53d5
  |      Successors: 2:0dec01379d3b
  |      multi-line: 2:0dec01379d3b
  |      json: [["0dec01379d3be6318c470ead31b1fe7ae7cb53d5"]]
  @  ea207398892e
  
Test template with split + divergence with cycles
=================================================

  $ hg log -G
  o  changeset:   3:f897c6137566
  |  tag:         tip
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     C0
  |
  @  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
  $ hg up
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved

Create a commit with three files
  $ touch A B C
  $ hg commit -A -m "Add A,B,C" A B C

Split it
  $ hg up 3
  0 files updated, 0 files merged, 3 files removed, 0 files unresolved
  $ touch A
  $ hg commit -A -m "Add A,B,C" A
  created new head

  $ touch B
  $ hg commit -A -m "Add A,B,C" B

  $ touch C
  $ hg commit -A -m "Add A,B,C" C

  $ hg log -G
  @  changeset:   7:ba2ed02b0c9a
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     Add A,B,C
  |
  o  changeset:   6:4a004186e638
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     Add A,B,C
  |
  o  changeset:   5:dd800401bd8c
  |  parent:      3:f897c6137566
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     Add A,B,C
  |
  | o  changeset:   4:9bd10a0775e4
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     Add A,B,C
  |
  o  changeset:   3:f897c6137566
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     C0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
  $ hg debugobsolete `getid "4"` `getid "5"` `getid "6"` `getid "7"`
  $ hg log -G
  @  changeset:   7:ba2ed02b0c9a
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     Add A,B,C
  |
  o  changeset:   6:4a004186e638
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     Add A,B,C
  |
  o  changeset:   5:dd800401bd8c
  |  parent:      3:f897c6137566
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     Add A,B,C
  |
  o  changeset:   3:f897c6137566
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     C0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  
Diverge one of the splitted commit

  $ hg up 6
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ hg commit --amend -m "Add only B"

  $ hg up 6 --hidden
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg commit --amend -m "Add B only"

  $ hg log -G
  @  changeset:   9:0b997eb7ceee
  |  tag:         tip
  |  parent:      5:dd800401bd8c
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  trouble:     divergent
  |  summary:     Add B only
  |
  | o  changeset:   8:b18bc8331526
  |/   parent:      5:dd800401bd8c
  |    user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    trouble:     divergent
  |    summary:     Add only B
  |
  | o  changeset:   7:ba2ed02b0c9a
  | |  user:        test
  | |  date:        Thu Jan 01 00:00:00 1970 +0000
  | |  trouble:     unstable, divergent
  | |  summary:     Add A,B,C
  | |
  | x  changeset:   6:4a004186e638
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     Add A,B,C
  |
  o  changeset:   5:dd800401bd8c
  |  parent:      3:f897c6137566
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  trouble:     divergent
  |  summary:     Add A,B,C
  |
  o  changeset:   3:f897c6137566
  |  parent:      0:ea207398892e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     C0
  |
  o  changeset:   0:ea207398892e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     ROOT
  

Check templates
---------------

  $ hg tlog
  @  0b997eb7ceee
  |    Predecessors: 6:4a004186e638
  |    semi-colon: 6:4a004186e638
  |    json: ["4a004186e63889f20cb16434fcbd72220bd1eace"]
  |    map: 6:4a004186e63889f20cb16434fcbd72220bd1eace
  | o  b18bc8331526
  |/     Predecessors: 6:4a004186e638
  |      semi-colon: 6:4a004186e638
  |      json: ["4a004186e63889f20cb16434fcbd72220bd1eace"]
  |      map: 6:4a004186e63889f20cb16434fcbd72220bd1eace
  | o  ba2ed02b0c9a
  | |
  | x  4a004186e638
  |/     Successors: 8:b18bc8331526; 9:0b997eb7ceee
  |      multi-line: 8:b18bc8331526
  |      multi-line: 9:0b997eb7ceee
  |      json: [["b18bc8331526a22cbb1801022bd1555bf291c48b"], ["0b997eb7ceeee06200a02f8aab185979092d514e"]]
  o  dd800401bd8c
  |
  o  f897c6137566
  |
  o  ea207398892e
  
  $ hg tlog --hidden
  @  0b997eb7ceee
  |    Predecessors: 6:4a004186e638
  |    semi-colon: 6:4a004186e638
  |    json: ["4a004186e63889f20cb16434fcbd72220bd1eace"]
  |    map: 6:4a004186e63889f20cb16434fcbd72220bd1eace
  | o  b18bc8331526
  |/     Predecessors: 6:4a004186e638
  |      semi-colon: 6:4a004186e638
  |      json: ["4a004186e63889f20cb16434fcbd72220bd1eace"]
  |      map: 6:4a004186e63889f20cb16434fcbd72220bd1eace
  | o  ba2ed02b0c9a
  | |    Predecessors: 4:9bd10a0775e4
  | |    semi-colon: 4:9bd10a0775e4
  | |    json: ["9bd10a0775e478708cada5f176ec6de654359ce7"]
  | |    map: 4:9bd10a0775e478708cada5f176ec6de654359ce7
  | x  4a004186e638
  |/     Predecessors: 4:9bd10a0775e4
  |      semi-colon: 4:9bd10a0775e4
  |      json: ["9bd10a0775e478708cada5f176ec6de654359ce7"]
  |      map: 4:9bd10a0775e478708cada5f176ec6de654359ce7
  |      Successors: 8:b18bc8331526; 9:0b997eb7ceee
  |      multi-line: 8:b18bc8331526
  |      multi-line: 9:0b997eb7ceee
  |      json: [["b18bc8331526a22cbb1801022bd1555bf291c48b"], ["0b997eb7ceeee06200a02f8aab185979092d514e"]]
  o  dd800401bd8c
  |    Predecessors: 4:9bd10a0775e4
  |    semi-colon: 4:9bd10a0775e4
  |    json: ["9bd10a0775e478708cada5f176ec6de654359ce7"]
  |    map: 4:9bd10a0775e478708cada5f176ec6de654359ce7
  | x  9bd10a0775e4
  |/     Successors: 5:dd800401bd8c 6:4a004186e638 7:ba2ed02b0c9a
  |      multi-line: 5:dd800401bd8c 6:4a004186e638 7:ba2ed02b0c9a
  |      json: [["dd800401bd8c79d815329277739e433e883f784e", "4a004186e63889f20cb16434fcbd72220bd1eace", "ba2ed02b0c9a56b9fdbc4e79c7e57866984d8a1f"]]
  o  f897c6137566
  |    Predecessors: 2:0dec01379d3b
  |    semi-colon: 2:0dec01379d3b
  |    json: ["0dec01379d3be6318c470ead31b1fe7ae7cb53d5"]
  |    map: 2:0dec01379d3be6318c470ead31b1fe7ae7cb53d5
  | x  0dec01379d3b
  | |    Predecessors: 1:471f378eab4c
  | |    semi-colon: 1:471f378eab4c
  | |    json: ["471f378eab4c5e25f6c77f785b27c936efb22874"]
  | |    map: 1:471f378eab4c5e25f6c77f785b27c936efb22874
  | |    Successors: 3:f897c6137566; 1:471f378eab4c
  | |    multi-line: 3:f897c6137566
  | |    multi-line: 1:471f378eab4c
  | |    json: [["f897c6137566320b081514b4c7227ecc3d384b39"], ["471f378eab4c5e25f6c77f785b27c936efb22874"]]
  | x  471f378eab4c
  |/     Predecessors: 2:0dec01379d3b
  |      semi-colon: 2:0dec01379d3b
  |      json: ["0dec01379d3be6318c470ead31b1fe7ae7cb53d5"]
  |      map: 2:0dec01379d3be6318c470ead31b1fe7ae7cb53d5
  |      Successors: 2:0dec01379d3b
  |      multi-line: 2:0dec01379d3b
  |      json: [["0dec01379d3be6318c470ead31b1fe7ae7cb53d5"]]
  o  ea207398892e
  
  $ hg up --hidden 4
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg rebase -r 7 -d 8 --config extensions.rebase=
  rebasing 7:ba2ed02b0c9a "Add A,B,C"
  $ hg tlog
  o  eceed8f98ffc
  |    Predecessors: 4:9bd10a0775e4
  |    semi-colon: 4:9bd10a0775e4
  |    json: ["9bd10a0775e478708cada5f176ec6de654359ce7"]
  |    map: 4:9bd10a0775e478708cada5f176ec6de654359ce7
  | o  0b997eb7ceee
  | |    Predecessors: 4:9bd10a0775e4
  | |    semi-colon: 4:9bd10a0775e4
  | |    json: ["9bd10a0775e478708cada5f176ec6de654359ce7"]
  | |    map: 4:9bd10a0775e478708cada5f176ec6de654359ce7
  o |  b18bc8331526
  |/     Predecessors: 4:9bd10a0775e4
  |      semi-colon: 4:9bd10a0775e4
  |      json: ["9bd10a0775e478708cada5f176ec6de654359ce7"]
  |      map: 4:9bd10a0775e478708cada5f176ec6de654359ce7
  o  dd800401bd8c
  |    Predecessors: 4:9bd10a0775e4
  |    semi-colon: 4:9bd10a0775e4
  |    json: ["9bd10a0775e478708cada5f176ec6de654359ce7"]
  |    map: 4:9bd10a0775e478708cada5f176ec6de654359ce7
  | @  9bd10a0775e4
  |/     Successors: 5:dd800401bd8c 9:0b997eb7ceee 10:eceed8f98ffc; 5:dd800401bd8c 8:b18bc8331526 10:eceed8f98ffc
  |      multi-line: 5:dd800401bd8c 9:0b997eb7ceee 10:eceed8f98ffc
  |      multi-line: 5:dd800401bd8c 8:b18bc8331526 10:eceed8f98ffc
  |      json: [["dd800401bd8c79d815329277739e433e883f784e", "0b997eb7ceeee06200a02f8aab185979092d514e", "eceed8f98ffc4186032e29a6542ab98888ebf68d"], ["dd800401bd8c79d815329277739e433e883f784e", "b18bc8331526a22cbb1801022bd1555bf291c48b", "eceed8f98ffc4186032e29a6542ab98888ebf68d"]]
  o  f897c6137566
  |
  o  ea207398892e
  
Test templates with pruned commits
==================================

Test setup
----------

  $ hg init $TESTTMP/templates-local-prune
  $ cd $TESTTMP/templates-local-prune
  $ mkcommit ROOT
  $ mkcommit A0
  $ hg debugobsolete --record-parent `getid "."`

Check output
------------

  $ hg up "desc(A0)" --hidden
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg tlog
  @  471f378eab4c
  |
  o  ea207398892e
  
