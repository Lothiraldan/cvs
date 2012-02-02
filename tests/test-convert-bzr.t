  $ "$TESTDIR/hghave" symlink execbit || exit 80

  $ . "$TESTDIR/bzr-definitions"

create and rename on the same file in the same step

  $ mkdir test-createandrename
  $ cd test-createandrename
  $ bzr init -q source
  $ cd source
  $ echo a > a
  $ echo c > c
  $ echo e > e
  $ bzr add -q a c e
  $ bzr commit -q -m 'Initial add: a, c, e'
  $ bzr mv a b
  a => b
  $ bzr mv c d
  c => d
  $ bzr mv e f
  e => f
  $ echo a2 >> a
  $ mkdir e
  $ bzr add -q a e
  $ bzr commit -q -m 'rename a into b, create a, rename c into d'
  $ cd ..
  $ hg convert source source-hg
  initializing destination source-hg repository
  scanning source...
  sorting...
  converting...
  1 Initial add: a, c, e
  0 rename a into b, create a, rename c into d
  $ glog -R source-hg
  o  1@source "rename a into b, create a, rename c into d" files: a b c d e f
  |
  o  0@source "Initial add: a, c, e" files: a c e
  

manifest

  $ hg manifest -R source-hg -r tip
  a
  b
  d
  f

test --rev option

  $ hg convert -r 1 source source-1-hg
  initializing destination source-1-hg repository
  scanning source...
  sorting...
  converting...
  0 Initial add: a, c, e
  $ glog -R source-1-hg
  o  0@source "Initial add: a, c, e" files: a c e
  

test with filemap

  $ cat > filemap <<EOF
  > exclude a
  > EOF
  $ hg convert --filemap filemap source source-filemap-hg
  initializing destination source-filemap-hg repository
  scanning source...
  sorting...
  converting...
  1 Initial add: a, c, e
  0 rename a into b, create a, rename c into d
  $ hg -R source-filemap-hg manifest -r tip
  b
  d
  f

convert from lightweight checkout

  $ bzr checkout --lightweight source source-light
  $ hg convert -s bzr source-light source-light-hg
  initializing destination source-light-hg repository
  warning: lightweight checkouts may cause conversion failures, try with a regular branch instead.
  $TESTTMP/test-createandrename/source-light does not look like a Bazaar repository
  abort: source-light: missing or unsupported repository
  [255]

extract timestamps that look just like hg's {date|isodate}:
yyyy-mm-dd HH:MM zzzz (no seconds!)
compare timestamps

  $ cd source
  $ bzr log | \
  >   sed '/timestamp/!d;s/.\{15\}\([0-9: -]\{16\}\):.. \(.[0-9]\{4\}\)/\1 \2/' \
  >   > ../bzr-timestamps
  $ cd ..
  $ hg -R source-hg log --template "{date|isodate}\n" > hg-timestamps
  $ diff -u bzr-timestamps hg-timestamps
  $ cd ..

merge

  $ mkdir test-merge
  $ cd test-merge
  $ cat > helper.py <<EOF
  > import sys
  > from bzrlib import workingtree
  > wt = workingtree.WorkingTree.open('.')
  > 
  > message, stamp = sys.argv[1:]
  > wt.commit(message, timestamp=int(stamp))
  > EOF
  $ bzr init -q source
  $ cd source
  $ echo content > a
  $ echo content2 > b
  $ bzr add -q a b
  $ bzr commit -q -m 'Initial add'
  $ cd ..
  $ bzr branch -q source source-improve
  $ cd source
  $ echo more >> a
  $ python ../helper.py 'Editing a' 100
  $ cd ../source-improve
  $ echo content3 >> b
  $ python ../helper.py 'Editing b' 200
  $ cd ../source
  $ bzr merge -q ../source-improve
  $ bzr commit -q -m 'Merged improve branch'
  $ cd ..
  $ hg convert --datesort source source-hg
  initializing destination source-hg repository
  scanning source...
  sorting...
  converting...
  3 Initial add
  2 Editing a
  1 Editing b
  0 Merged improve branch
  $ glog -R source-hg
  o    3@source "Merged improve branch" files:
  |\
  | o  2@source-improve "Editing b" files: b
  | |
  o |  1@source "Editing a" files: a
  |/
  o  0@source "Initial add" files: a b
  
  $ cd ..

symlinks and executable files

  $ mkdir test-symlinks
  $ cd test-symlinks
  $ bzr init -q source
  $ cd source
  $ touch program
  $ chmod +x program
  $ ln -s program altname
  $ mkdir d
  $ echo a > d/a
  $ ln -s a syma
  $ bzr add -q altname program syma d/a
  $ bzr commit -q -m 'Initial setup'
  $ touch newprog
  $ chmod +x newprog
  $ rm altname
  $ ln -s newprog altname
  $ chmod -x program
  $ bzr add -q newprog
  $ bzr commit -q -m 'Symlink changed, x bits changed'
  $ cd ..
  $ hg convert source source-hg
  initializing destination source-hg repository
  scanning source...
  sorting...
  converting...
  1 Initial setup
  0 Symlink changed, x bits changed
  $ manifest source-hg 0
  % manifest of 0
  644 @ altname
  644   d/a
  755 * program
  644 @ syma
  $ manifest source-hg tip
  % manifest of tip
  644 @ altname
  644   d/a
  755 * newprog
  644   program
  644 @ syma
  $ cd source-hg

test the symlinks can be recreated

  $ hg up
  5 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg cat syma; echo
  a

Multiple branches

  $ bzr init-repo -q --no-trees repo
  $ bzr init -q repo/trunk
  $ bzr co repo/trunk repo-trunk
  $ cd repo-trunk
  $ echo a > a
  $ bzr add a
  adding a
  $ bzr ci -qm adda --commit-time '2012-01-01 00:00:01 +0000'
  $ bzr switch -b branch
  Tree is up to date at revision 1.
  Switched to branch: *repo/branch/ (glob)
  $ echo b > b
  $ bzr add b
  adding b
  $ bzr ci -qm addb --commit-time '2012-01-01 00:00:02 +0000'
  $ bzr switch --force ../repo/trunk
  Updated to revision 1.
  Switched to branch: */repo/trunk/ (glob)
  $ echo a >> a
  $ bzr ci -qm changea --commit-time '2012-01-01 00:00:03 +0000'
  $ cd ..
  $ hg convert --datesort repo repo-bzr
  initializing destination repo-bzr repository
  scanning source...
  sorting...
  converting...
  2 adda
  1 addb
  0 changea
  $ (cd repo-bzr; glog)
  o  2@default "changea" files: a
  |
  | o  1@branch "addb" files: b
  |/
  o  0@default "adda" files: a
  
