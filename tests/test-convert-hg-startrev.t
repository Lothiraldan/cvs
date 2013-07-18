
  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > graphlog =
  > convert =
  > [convert]
  > hg.saverev = yes
  > EOF

  $ glog()
  > {
  >     hg -R "$1" glog --template '{rev} "{desc}" files: {files}\n'
  > }

  $ hg init source
  $ cd source

  $ echo a > a
  $ echo b > b
  $ echo f > f
  $ hg ci -d '0 0' -qAm '0: add a b f'
  $ echo c > c
  $ hg move f d
  $ hg ci -d '1 0' -qAm '1: add c, move f to d'
  $ hg copy a e
  $ echo b >> b
  $ hg ci -d '2 0' -qAm '2: copy e from a, change b'
  $ hg up -C 0
  2 files updated, 0 files merged, 3 files removed, 0 files unresolved
  $ echo a >> a
  $ hg ci -d '3 0' -qAm '3: change a'
  $ hg merge
  merging a and e to e
  3 files updated, 1 files merged, 1 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -d '4 0' -qAm '4: merge 2 and 3'
  $ echo a >> a
  $ hg ci -d '5 0' -qAm '5: change a'
  $ cd ..

Convert from null revision

  $ hg convert --config convert.hg.startrev=null source full
  initializing destination full repository
  scanning source...
  sorting...
  converting...
  5 0: add a b f
  4 1: add c, move f to d
  3 2: copy e from a, change b
  2 3: change a
  1 4: merge 2 and 3
  0 5: change a

  $ glog full
  o  5 "5: change a" files: a
  |
  o    4 "4: merge 2 and 3" files: e f
  |\
  | o  3 "3: change a" files: a
  | |
  o |  2 "2: copy e from a, change b" files: b e
  | |
  o |  1 "1: add c, move f to d" files: c d f
  |/
  o  0 "0: add a b f" files: a b f
  
  $ rm -Rf full

Convert from zero revision

  $ hg convert --config convert.hg.startrev=0 source full
  initializing destination full repository
  scanning source...
  sorting...
  converting...
  5 0: add a b f
  4 1: add c, move f to d
  3 2: copy e from a, change b
  2 3: change a
  1 4: merge 2 and 3
  0 5: change a

  $ glog full
  o  5 "5: change a" files: a
  |
  o    4 "4: merge 2 and 3" files: e f
  |\
  | o  3 "3: change a" files: a
  | |
  o |  2 "2: copy e from a, change b" files: b e
  | |
  o |  1 "1: add c, move f to d" files: c d f
  |/
  o  0 "0: add a b f" files: a b f
  
Convert from merge parent

  $ hg convert --config convert.hg.startrev=1 source conv1
  initializing destination conv1 repository
  scanning source...
  sorting...
  converting...
  3 1: add c, move f to d
  2 2: copy e from a, change b
  1 4: merge 2 and 3
  0 5: change a

  $ glog conv1
  o  3 "5: change a" files: a
  |
  o  2 "4: merge 2 and 3" files: a e
  |
  o  1 "2: copy e from a, change b" files: b e
  |
  o  0 "1: add c, move f to d" files: a b c d
  
  $ cd conv1
  $ hg up -q

Check copy preservation

  $ hg log --follow --copies e
  changeset:   2:60633ee11cfa
  user:        test
  date:        Thu Jan 01 00:00:04 1970 +0000
  summary:     4: merge 2 and 3
  
  changeset:   1:d56e8baefff8
  user:        test
  date:        Thu Jan 01 00:00:02 1970 +0000
  summary:     2: copy e from a, change b
  
Check copy removal on missing parent

  $ hg log --follow --copies d
  changeset:   0:23c3be426dce
  user:        test
  date:        Thu Jan 01 00:00:01 1970 +0000
  summary:     1: add c, move f to d
  
  $ hg cat -r tip a b
  a
  a
  a
  b
  b
  $ hg -q verify
  $ cd ..

Convert from merge

  $ hg convert --config convert.hg.startrev=4 source conv4
  initializing destination conv4 repository
  scanning source...
  sorting...
  converting...
  1 4: merge 2 and 3
  0 5: change a
  $ glog conv4
  o  1 "5: change a" files: a
  |
  o  0 "4: merge 2 and 3" files: a b c d e
  
  $ cd conv4
  $ hg up -C
  5 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg cat -r tip a b
  a
  a
  a
  b
  b
  $ hg -q verify
  $ cd ..
