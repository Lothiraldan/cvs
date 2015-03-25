Revert interactive tests
1 add and commit file f
2 add commit file folder1/g
3 add and commit file folder2/h
4 add and commit file folder1/i
5 commit change to file f
6 commit changes to files folder1/g folder2/h
7 commit changes to files folder1/g folder2/h
8 revert interactive to commit id 2 (line 3 above), check that folder1/i is removed and
9 make workdir match 7
10 run the same test than 8 from within folder1 and check same expectations

  $ cat <<EOF >> $HGRCPATH
  > [ui]
  > interactive = true
  > [extensions]
  > record =
  > EOF


  $ mkdir -p a/folder1 a/folder2
  $ cd a
  $ hg init
  >>> open('f', 'wb').write("1\n2\n3\n4\n5\n")
  $ hg add f ; hg commit -m "adding f"
  $ cat f > folder1/g ; hg add folder1/g ; hg commit -m "adding folder1/g"
  $ cat f > folder2/h ; hg add folder2/h ; hg commit -m "adding folder2/h"
  $ cat f > folder1/i ; hg add folder1/i ; hg commit -m "adding folder1/i"
  >>> open('f', 'wb').write("a\n1\n2\n3\n4\n5\nb\n")
  $ hg commit -m "modifying f"
  >>> open('folder1/g', 'wb').write("c\n1\n2\n3\n4\n5\nd\n")
  $ hg commit -m "modifying folder1/g"
  >>> open('folder2/h', 'wb').write("e\n1\n2\n3\n4\n5\nf\n")
  $ hg commit -m "modifying folder2/h"
  $ hg tip
  changeset:   6:59dd6e4ab63a
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     modifying folder2/h
  
  $ hg revert -i -r 2 --all -- << EOF
  > y
  > y
  > y
  > y
  > y
  > n
  > n
  > EOF
  reverting f
  reverting folder1/g (glob)
  removing folder1/i (glob)
  reverting folder2/h (glob)
  diff -r 89ac3d72e4a4 f
  2 hunks, 2 lines changed
  examine changes to 'f'? [Ynesfdaq?] y
  
  @@ -1,6 +1,5 @@
  -a
   1
   2
   3
   4
   5
  record change 1/6 to 'f'? [Ynesfdaq?] y
  
  @@ -2,6 +1,5 @@
   1
   2
   3
   4
   5
  -b
  record change 2/6 to 'f'? [Ynesfdaq?] y
  
  diff -r 89ac3d72e4a4 folder1/g
  2 hunks, 2 lines changed
  examine changes to 'folder1/g'? [Ynesfdaq?] y
  
  @@ -1,6 +1,5 @@
  -c
   1
   2
   3
   4
   5
  record change 3/6 to 'folder1/g'? [Ynesfdaq?] y
  
  @@ -2,6 +1,5 @@
   1
   2
   3
   4
   5
  -d
  record change 4/6 to 'folder1/g'? [Ynesfdaq?] n
  
  diff -r 89ac3d72e4a4 folder2/h
  2 hunks, 2 lines changed
  examine changes to 'folder2/h'? [Ynesfdaq?] n
  
  $ cat f
  1
  2
  3
  4
  5
  $ cat folder1/g
  1
  2
  3
  4
  5
  d
  $ cat folder2/h
  e
  1
  2
  3
  4
  5
  f
  $ hg update -C 6
  3 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg revert -i -r 2 --all -- << EOF
  > y
  > y
  > y
  > y
  > y
  > n
  > n
  > EOF
  reverting f
  reverting folder1/g (glob)
  removing folder1/i (glob)
  reverting folder2/h (glob)
  diff -r 89ac3d72e4a4 f
  2 hunks, 2 lines changed
  examine changes to 'f'? [Ynesfdaq?] y
  
  @@ -1,6 +1,5 @@
  -a
   1
   2
   3
   4
   5
  record change 1/6 to 'f'? [Ynesfdaq?] y
  
  @@ -2,6 +1,5 @@
   1
   2
   3
   4
   5
  -b
  record change 2/6 to 'f'? [Ynesfdaq?] y
  
  diff -r 89ac3d72e4a4 folder1/g
  2 hunks, 2 lines changed
  examine changes to 'folder1/g'? [Ynesfdaq?] y
  
  @@ -1,6 +1,5 @@
  -c
   1
   2
   3
   4
   5
  record change 3/6 to 'folder1/g'? [Ynesfdaq?] y
  
  @@ -2,6 +1,5 @@
   1
   2
   3
   4
   5
  -d
  record change 4/6 to 'folder1/g'? [Ynesfdaq?] n
  
  diff -r 89ac3d72e4a4 folder2/h
  2 hunks, 2 lines changed
  examine changes to 'folder2/h'? [Ynesfdaq?] n
  
  $ cat f
  1
  2
  3
  4
  5
  $ cat folder1/g
  1
  2
  3
  4
  5
  d
  $ cat folder2/h
  e
  1
  2
  3
  4
  5
  f
  $ hg st
  M f
  M folder1/g
  R folder1/i
  $ hg revert --interactive f << EOF
  > y
  > y
  > n
  > n
  > EOF
  diff -r 59dd6e4ab63a f
  2 hunks, 2 lines changed
  examine changes to 'f'? [Ynesfdaq?] y
  
  @@ -1,5 +1,6 @@
  +a
   1
   2
   3
   4
   5
  record change 1/2 to 'f'? [Ynesfdaq?] y
  
  @@ -1,5 +2,6 @@
   1
   2
   3
   4
   5
  +b
  record change 2/2 to 'f'? [Ynesfdaq?] n
  
  $ hg st
  M f
  M folder1/g
  R folder1/i
  ? f.orig
  $ cat f
  a
  1
  2
  3
  4
  5
  $ cat f.orig
  1
  2
  3
  4
  5
