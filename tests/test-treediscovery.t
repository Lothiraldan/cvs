Tests discovery against servers without getbundle support:

  $ CAP=getbundle
  $ . "$TESTDIR/notcapable"
  $ cat >> $HGRCPATH <<EOF
  > [ui]
  > logtemplate="{rev} {node|short}: {desc} {branches}\n"
  > [extensions]
  > graphlog=
  > EOF

Setup HTTP server control:

  $ export remote=http://localhost:$HGPORT/
  $ start() {
  >   echo '[web]' > $1/.hg/hgrc
  >   echo 'push_ssl = false' >> $1/.hg/hgrc
  >   echo 'allow_push = *' >> $1/.hg/hgrc
  >   hg serve -R $1 -p $HGPORT -d --pid-file=hg.pid -E errors.log
  >   cat hg.pid >> $DAEMON_PIDS
  > }
  $ stop() {
  >   "$TESTDIR/killdaemons.py"
  > }

Both are empty:

  $ hg init empty1
  $ hg init empty2
  $ start empty2
  $ hg incoming -R empty1 $remote
  comparing with http://localhost:$HGPORT/
  no changes found
  [1]
  $ hg outgoing -R empty1 $remote
  comparing with http://localhost:$HGPORT/
  no changes found
  [1]
  $ hg pull -R empty1 $remote
  pulling from http://localhost:$HGPORT/
  no changes found
  $ hg push -R empty1 $remote
  pushing to http://localhost:$HGPORT/
  no changes found
  $ stop

Base repo:

  $ hg init main
  $ cd main
  $ hg debugbuilddag -mo '+2:tbase @name1 +3:thead1 <tbase @name2 +4:thead2 @both /thead1 +2:tmaintip'
  $ hg glog
  o  11 a19bfa7e7328: r11 both
  |
  o  10 8b6bad1512e1: r10 both
  |
  o    9 025829e08038: r9 both
  |\
  | o  8 d8f638ac69e9: r8 name2
  | |
  | o  7 b6b4d315a2ac: r7 name2
  | |
  | o  6 6c6f5d5f3c11: r6 name2
  | |
  | o  5 70314b29987d: r5 name2
  | |
  o |  4 e71dbbc70e03: r4 name1
  | |
  o |  3 2c8d5d5ec612: r3 name1
  | |
  o |  2 a7892891da29: r2 name1
  |/
  o  1 0019a3b924fd: r1
  |
  o  0 d57206cc072a: r0
  
  $ cd ..
  $ start main

Full clone:

  $ hg clone main full
  updating to branch default
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd full
  $ hg incoming $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  no changes found
  [1]
  $ hg outgoing $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  no changes found
  [1]
  $ hg pull $remote
  pulling from http://localhost:$HGPORT/
  searching for changes
  no changes found
  $ hg push $remote
  pushing to http://localhost:$HGPORT/
  searching for changes
  no changes found
  $ cd ..

Local is empty:

  $ cd empty1
  $ hg incoming $remote
  comparing with http://localhost:$HGPORT/
  0 d57206cc072a: r0 
  1 0019a3b924fd: r1 
  2 a7892891da29: r2 name1
  3 2c8d5d5ec612: r3 name1
  4 e71dbbc70e03: r4 name1
  5 70314b29987d: r5 name2
  6 6c6f5d5f3c11: r6 name2
  7 b6b4d315a2ac: r7 name2
  8 d8f638ac69e9: r8 name2
  9 025829e08038: r9 both
  10 8b6bad1512e1: r10 both
  11 a19bfa7e7328: r11 both
  $ hg outgoing $remote
  comparing with http://localhost:$HGPORT/
  no changes found
  [1]
  $ hg push $remote
  pushing to http://localhost:$HGPORT/
  no changes found
  $ hg pull $remote
  pulling from http://localhost:$HGPORT/
  requesting all changes
  adding changesets
  adding manifests
  adding file changes
  added 12 changesets with 24 changes to 2 files
  (run 'hg update' to get a working copy)
  $ hg incoming $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  no changes found
  [1]
  $ cd ..

Local is subset:

  $ hg clone main subset --rev name2 ; cd subset
  adding changesets
  adding manifests
  adding file changes
  added 6 changesets with 12 changes to 2 files
  updating to branch name2
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg incoming $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  6 a7892891da29: r2 name1
  7 2c8d5d5ec612: r3 name1
  8 e71dbbc70e03: r4 name1
  9 025829e08038: r9 both
  10 8b6bad1512e1: r10 both
  11 a19bfa7e7328: r11 both
  $ hg outgoing $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  no changes found
  [1]
  $ hg push $remote
  pushing to http://localhost:$HGPORT/
  searching for changes
  no changes found
  $ hg pull $remote
  pulling from http://localhost:$HGPORT/
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 6 changesets with 12 changes to 2 files
  (run 'hg update' to get a working copy)
  $ hg incoming $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  no changes found
  [1]
  $ cd ..

Remote is empty:

  $ stop ; start empty2
  $ cd main
  $ hg incoming $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  no changes found
  [1]
  $ hg outgoing $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  0 d57206cc072a: r0 
  1 0019a3b924fd: r1 
  2 a7892891da29: r2 name1
  3 2c8d5d5ec612: r3 name1
  4 e71dbbc70e03: r4 name1
  5 70314b29987d: r5 name2
  6 6c6f5d5f3c11: r6 name2
  7 b6b4d315a2ac: r7 name2
  8 d8f638ac69e9: r8 name2
  9 025829e08038: r9 both
  10 8b6bad1512e1: r10 both
  11 a19bfa7e7328: r11 both
  $ hg pull $remote
  pulling from http://localhost:$HGPORT/
  searching for changes
  no changes found
  $ hg push $remote
  pushing to http://localhost:$HGPORT/
  searching for changes
  remote: adding changesets
  remote: adding manifests
  remote: adding file changes
  remote: added 12 changesets with 24 changes to 2 files
  $ hg outgoing $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  no changes found
  [1]
  $ cd ..

Local is superset:

  $ stop
  $ hg clone main subset2 --rev name2
  adding changesets
  adding manifests
  adding file changes
  added 6 changesets with 12 changes to 2 files
  updating to branch name2
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ start subset2
  $ cd main
  $ hg incoming $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  no changes found
  [1]
  $ hg outgoing $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  2 a7892891da29: r2 name1
  3 2c8d5d5ec612: r3 name1
  4 e71dbbc70e03: r4 name1
  9 025829e08038: r9 both
  10 8b6bad1512e1: r10 both
  11 a19bfa7e7328: r11 both
  $ hg pull $remote
  pulling from http://localhost:$HGPORT/
  searching for changes
  no changes found
  $ hg push $remote
  pushing to http://localhost:$HGPORT/
  searching for changes
  abort: push creates new remote branches: both, name1!
  (use 'hg push --new-branch' to create new remote branches)
  [255]
  $ hg push $remote --new-branch
  pushing to http://localhost:$HGPORT/
  searching for changes
  remote: adding changesets
  remote: adding manifests
  remote: adding file changes
  remote: added 6 changesets with 12 changes to 2 files
  $ hg outgoing $remote
  comparing with http://localhost:$HGPORT/
  searching for changes
  no changes found
  [1]
  $ cd ..

  $ stop

