#require git

  $ echo "[core]" >> $HOME/.gitconfig
  $ echo "autocrlf = false" >> $HOME/.gitconfig
  $ echo "[core]" >> $HOME/.gitconfig
  $ echo "autocrlf = false" >> $HOME/.gitconfig
  $ echo "[extensions]" >> $HGRCPATH
  $ echo "convert=" >> $HGRCPATH
  $ GIT_AUTHOR_NAME='test'; export GIT_AUTHOR_NAME
  $ GIT_AUTHOR_EMAIL='test@example.org'; export GIT_AUTHOR_EMAIL
  $ GIT_AUTHOR_DATE="2007-01-01 00:00:00 +0000"; export GIT_AUTHOR_DATE
  $ GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"; export GIT_COMMITTER_NAME
  $ GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"; export GIT_COMMITTER_EMAIL
  $ GIT_COMMITTER_DATE="$GIT_AUTHOR_DATE"; export GIT_COMMITTER_DATE
  $ INVALIDID1=afd12345af
  $ INVALIDID2=28173x36ddd1e67bf7098d541130558ef5534a86
  $ VALIDID1=39b3d83f9a69a9ba4ebb111461071a0af0027357
  $ VALIDID2=8dd6476bd09d9c7776355dc454dafe38efaec5da
  $ count=10
  $ commit()
  > {
  >     GIT_AUTHOR_DATE="2007-01-01 00:00:$count +0000"
  >     GIT_COMMITTER_DATE="$GIT_AUTHOR_DATE"
  >     git commit "$@" >/dev/null 2>/dev/null || echo "git commit error"
  >     count=`expr $count + 1`
  > }
  $ mkdir git-repo
  $ cd git-repo
  $ git init-db >/dev/null 2>/dev/null
  $ echo a > a
  $ mkdir d
  $ echo b > d/b
  $ git add a d
  $ commit -a -m t1

Remove the directory, then try to replace it with a file
(issue 754)

  $ git rm -f d/b
  rm 'd/b'
  $ commit -m t2
  $ echo d > d
  $ git add d
  $ commit -m t3
  $ echo b >> a
  $ commit -a -m t4.1
  $ git checkout -b other HEAD~ >/dev/null 2>/dev/null
  $ echo c > a
  $ echo a >> a
  $ commit -a -m t4.2
  $ git checkout master >/dev/null 2>/dev/null
  $ git pull --no-commit . other > /dev/null 2>/dev/null
  $ commit -m 'Merge branch other'
  $ cd ..
  $ hg convert --datesort git-repo
  assuming destination git-repo-hg
  initializing destination git-repo-hg repository
  scanning source...
  sorting...
  converting...
  5 t1
  4 t2
  3 t3
  2 t4.1
  1 t4.2
  0 Merge branch other
  updating bookmarks
  $ hg up -q -R git-repo-hg
  $ hg -R git-repo-hg tip -v
  changeset:   5:c78094926be2
  bookmark:    master
  tag:         tip
  parent:      3:f5f5cb45432b
  parent:      4:4e174f80c67c
  user:        test <test@example.org>
  date:        Mon Jan 01 00:00:15 2007 +0000
  files:       a
  description:
  Merge branch other
  
  
  $ count=10
  $ mkdir git-repo2
  $ cd git-repo2
  $ git init-db >/dev/null 2>/dev/null
  $ echo foo > foo
  $ git add foo
  $ commit -a -m 'add foo'
  $ echo >> foo
  $ commit -a -m 'change foo'
  $ git checkout -b Bar HEAD~ >/dev/null 2>/dev/null
  $ echo quux >> quux
  $ git add quux
  $ commit -a -m 'add quux'
  $ echo bar > bar
  $ git add bar
  $ commit -a -m 'add bar'
  $ git checkout -b Baz HEAD~ >/dev/null 2>/dev/null
  $ echo baz > baz
  $ git add baz
  $ commit -a -m 'add baz'
  $ git checkout master >/dev/null 2>/dev/null
  $ git pull --no-commit . Bar Baz > /dev/null 2>/dev/null
  $ commit -m 'Octopus merge'
  $ echo bar >> bar
  $ commit -a -m 'change bar'
  $ git checkout -b Foo HEAD~ >/dev/null 2>/dev/null
  $ echo >> foo
  $ commit -a -m 'change foo'
  $ git checkout master >/dev/null 2>/dev/null
  $ git pull --no-commit -s ours . Foo > /dev/null 2>/dev/null
  $ commit -m 'Discard change to foo'
  $ cd ..
  $ glog()
  > {
  >     hg log -G --template '{rev} "{desc|firstline}" files: {files}\n' "$@"
  > }
  $ splitrepo()
  > {
  >     msg="$1"
  >     files="$2"
  >     opts=$3
  >     echo "% $files: $msg"
  >     prefix=`echo "$files" | sed -e 's/ /-/g'`
  >     fmap="$prefix.fmap"
  >     repo="$prefix.repo"
  >     for i in $files; do
  >         echo "include $i" >> "$fmap"
  >     done
  >     hg -q convert $opts --filemap "$fmap" --datesort git-repo2 "$repo"
  >     hg up -q -R "$repo"
  >     glog -R "$repo"
  >     hg -R "$repo" manifest --debug
  > }

full conversion

  $ hg -q convert --datesort git-repo2 fullrepo
  $ hg up -q -R fullrepo
  $ glog -R fullrepo
  @    9 "Discard change to foo" files: foo
  |\
  | o  8 "change foo" files: foo
  | |
  o |  7 "change bar" files: bar
  |/
  o    6 "(octopus merge fixup)" files:
  |\
  | o    5 "Octopus merge" files: baz
  | |\
  o | |  4 "add baz" files: baz
  | | |
  +---o  3 "add bar" files: bar
  | |
  o |  2 "add quux" files: quux
  | |
  | o  1 "change foo" files: foo
  |/
  o  0 "add foo" files: foo
  
  $ hg -R fullrepo manifest --debug
  245a3b8bc653999c2b22cdabd517ccb47aecafdf 644   bar
  354ae8da6e890359ef49ade27b68bbc361f3ca88 644   baz
  9277c9cc8dd4576fc01a17939b4351e5ada93466 644   foo
  88dfeab657e8cf2cef3dec67b914f49791ae76b1 644   quux
  $ splitrepo 'octopus merge' 'foo bar baz'
  % foo bar baz: octopus merge
  @    8 "Discard change to foo" files: foo
  |\
  | o  7 "change foo" files: foo
  | |
  o |  6 "change bar" files: bar
  |/
  o    5 "(octopus merge fixup)" files:
  |\
  | o    4 "Octopus merge" files: baz
  | |\
  o | |  3 "add baz" files: baz
  | | |
  +---o  2 "add bar" files: bar
  | |
  | o  1 "change foo" files: foo
  |/
  o  0 "add foo" files: foo
  
  245a3b8bc653999c2b22cdabd517ccb47aecafdf 644   bar
  354ae8da6e890359ef49ade27b68bbc361f3ca88 644   baz
  9277c9cc8dd4576fc01a17939b4351e5ada93466 644   foo
  $ splitrepo 'only some parents of an octopus merge; "discard" a head' 'foo baz quux'
  % foo baz quux: only some parents of an octopus merge; "discard" a head
  @  6 "Discard change to foo" files: foo
  |
  o  5 "change foo" files: foo
  |
  o    4 "Octopus merge" files:
  |\
  | o  3 "add baz" files: baz
  | |
  | o  2 "add quux" files: quux
  | |
  o |  1 "change foo" files: foo
  |/
  o  0 "add foo" files: foo
  
  354ae8da6e890359ef49ade27b68bbc361f3ca88 644   baz
  9277c9cc8dd4576fc01a17939b4351e5ada93466 644   foo
  88dfeab657e8cf2cef3dec67b914f49791ae76b1 644   quux

test binary conversion (issue 1359)

  $ mkdir git-repo3
  $ cd git-repo3
  $ git init-db >/dev/null 2>/dev/null
  $ python -c 'file("b", "wb").write("".join([chr(i) for i in range(256)])*16)'
  $ git add b
  $ commit -a -m addbinary
  $ cd ..

convert binary file

  $ hg convert git-repo3 git-repo3-hg
  initializing destination git-repo3-hg repository
  scanning source...
  sorting...
  converting...
  0 addbinary
  updating bookmarks
  $ cd git-repo3-hg
  $ hg up -C
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ python -c 'print len(file("b", "rb").read())'
  4096
  $ cd ..

test author vs committer

  $ mkdir git-repo4
  $ cd git-repo4
  $ git init-db >/dev/null 2>/dev/null
  $ echo >> foo
  $ git add foo
  $ commit -a -m addfoo
  $ echo >> foo
  $ GIT_AUTHOR_NAME="nottest"
  $ commit -a -m addfoo2
  $ cd ..

convert author committer

  $ hg convert git-repo4 git-repo4-hg
  initializing destination git-repo4-hg repository
  scanning source...
  sorting...
  converting...
  1 addfoo
  0 addfoo2
  updating bookmarks
  $ hg -R git-repo4-hg log -v
  changeset:   1:d63e967f93da
  bookmark:    master
  tag:         tip
  user:        nottest <test@example.org>
  date:        Mon Jan 01 00:00:21 2007 +0000
  files:       foo
  description:
  addfoo2
  
  committer: test <test@example.org>
  
  
  changeset:   0:0735477b0224
  user:        test <test@example.org>
  date:        Mon Jan 01 00:00:20 2007 +0000
  files:       foo
  description:
  addfoo
  
  

--sourceorder should fail

  $ hg convert --sourcesort git-repo4 git-repo4-sourcesort-hg
  initializing destination git-repo4-sourcesort-hg repository
  abort: --sourcesort is not supported by this data source
  [255]

test sub modules

  $ mkdir git-repo5
  $ cd git-repo5
  $ git init-db >/dev/null 2>/dev/null
  $ echo 'sub' >> foo
  $ git add foo
  $ commit -a -m 'addfoo'
  $ BASE=`pwd`
  $ cd ..
  $ mkdir git-repo6
  $ cd git-repo6
  $ git init-db >/dev/null 2>/dev/null
  $ git submodule add ${BASE} >/dev/null 2>/dev/null
  $ commit -a -m 'addsubmodule' >/dev/null 2>/dev/null
  $ cd ..

test invalid splicemap1

  $ cat > splicemap <<EOF
  > $VALIDID1
  > EOF
  $ hg convert --splicemap splicemap git-repo2 git-repo2-splicemap1-hg
  initializing destination git-repo2-splicemap1-hg repository
  abort: syntax error in splicemap(1): child parent1[,parent2] expected
  [255]

test invalid splicemap2

  $ cat > splicemap <<EOF
  > $VALIDID1 $VALIDID2, $VALIDID2, $VALIDID2
  > EOF
  $ hg convert --splicemap splicemap git-repo2 git-repo2-splicemap2-hg
  initializing destination git-repo2-splicemap2-hg repository
  abort: syntax error in splicemap(1): child parent1[,parent2] expected
  [255]

test invalid splicemap3

  $ cat > splicemap <<EOF
  > $INVALIDID1 $INVALIDID2
  > EOF
  $ hg convert --splicemap splicemap git-repo2 git-repo2-splicemap3-hg
  initializing destination git-repo2-splicemap3-hg repository
  abort: splicemap entry afd12345af is not a valid revision identifier
  [255]

convert sub modules
  $ hg convert git-repo6 git-repo6-hg
  initializing destination git-repo6-hg repository
  scanning source...
  sorting...
  converting...
  0 addsubmodule
  updating bookmarks
  $ hg -R git-repo6-hg log -v
  changeset:   0:* (glob)
  bookmark:    master
  tag:         tip
  user:        nottest <test@example.org>
  date:        Mon Jan 01 00:00:23 2007 +0000
  files:       .hgsub .hgsubstate
  description:
  addsubmodule
  
  committer: test <test@example.org>
  
  

  $ cd git-repo6-hg
  $ hg up >/dev/null 2>/dev/null
  $ cat .hgsubstate
  * git-repo5 (glob)
  $ cd git-repo5
  $ cat foo
  sub

  $ cd ../..

convert the revision removing '.gitmodules' itself (and related
submodules)

  $ cd git-repo6
  $ git rm .gitmodules
  rm '.gitmodules'
  $ git rm --cached git-repo5
  rm 'git-repo5'
  $ commit -a -m 'remove .gitmodules and submodule git-repo5'
  $ cd ..

  $ hg convert -q git-repo6 git-repo6-hg
  $ hg -R git-repo6-hg tip -T "{desc|firstline}\n"
  remove .gitmodules and submodule git-repo5
  $ hg -R git-repo6-hg tip -T "{file_dels}\n"
  .hgsub .hgsubstate

damaged git repository tests:
In case the hard-coded hashes change, the following commands can be used to
list the hashes and their corresponding types in the repository:
cd git-repo4/.git/objects
find . -type f | cut -c 3- | sed 's_/__' | xargs -n 1 -t git cat-file -t
cd ../../..

damage git repository by renaming a commit object
  $ COMMIT_OBJ=1c/0ce3c5886f83a1d78a7b517cdff5cf9ca17bdd
  $ mv git-repo4/.git/objects/$COMMIT_OBJ git-repo4/.git/objects/$COMMIT_OBJ.tmp
  $ hg convert git-repo4 git-repo4-broken-hg 2>&1 | grep 'abort:'
  abort: cannot read tags from git-repo4/.git
  $ mv git-repo4/.git/objects/$COMMIT_OBJ.tmp git-repo4/.git/objects/$COMMIT_OBJ
damage git repository by renaming a blob object

  $ BLOB_OBJ=8b/137891791fe96927ad78e64b0aad7bded08bdc
  $ mv git-repo4/.git/objects/$BLOB_OBJ git-repo4/.git/objects/$BLOB_OBJ.tmp
  $ hg convert git-repo4 git-repo4-broken-hg 2>&1 | grep 'abort:'
  abort: cannot read 'blob' object at 8b137891791fe96927ad78e64b0aad7bded08bdc
  $ mv git-repo4/.git/objects/$BLOB_OBJ.tmp git-repo4/.git/objects/$BLOB_OBJ
damage git repository by renaming a tree object

  $ TREE_OBJ=72/49f083d2a63a41cc737764a86981eb5f3e4635
  $ mv git-repo4/.git/objects/$TREE_OBJ git-repo4/.git/objects/$TREE_OBJ.tmp
  $ hg convert git-repo4 git-repo4-broken-hg 2>&1 | grep 'abort:'
  abort: cannot read changes in 1c0ce3c5886f83a1d78a7b517cdff5cf9ca17bdd
