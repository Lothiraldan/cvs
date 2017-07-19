  $ HGMERGE=true; export HGMERGE

init

  $ hg init repo
  $ cd repo

commit

  $ echo 'a' > a
  $ hg ci -A -m test -u nobody -d '1 0'
  adding a

annotate -c

  $ hg annotate -c a
  8435f90966e4: a

annotate -cl

  $ hg annotate -cl a
  8435f90966e4:1: a

annotate -d

  $ hg annotate -d a
  Thu Jan 01 00:00:01 1970 +0000: a

annotate -n

  $ hg annotate -n a
  0: a

annotate -nl

  $ hg annotate -nl a
  0:1: a

annotate -u

  $ hg annotate -u a
  nobody: a

annotate -cdnu

  $ hg annotate -cdnu a
  nobody 0 8435f90966e4 Thu Jan 01 00:00:01 1970 +0000: a

annotate -cdnul

  $ hg annotate -cdnul a
  nobody 0 8435f90966e4 Thu Jan 01 00:00:01 1970 +0000:1: a

annotate (JSON)

  $ hg annotate -Tjson a
  [
   {
    "abspath": "a",
    "lines": [{"line": "a\n", "rev": 0}],
    "path": "a"
   }
  ]

  $ hg annotate -Tjson -cdfnul a
  [
   {
    "abspath": "a",
    "lines": [{"date": [1.0, 0], "file": "a", "line": "a\n", "line_number": 1, "node": "8435f90966e442695d2ded29fdade2bac5ad8065", "rev": 0, "user": "nobody"}],
    "path": "a"
   }
  ]

  $ cat <<EOF >>a
  > a
  > a
  > EOF
  $ hg ci -ma1 -d '1 0'
  $ hg cp a b
  $ hg ci -mb -d '1 0'
  $ cat <<EOF >> b
  > b4
  > b5
  > b6
  > EOF
  $ hg ci -mb2 -d '2 0'

annotate multiple files (JSON)

  $ hg annotate -Tjson a b
  [
   {
    "abspath": "a",
    "lines": [{"line": "a\n", "rev": 0}, {"line": "a\n", "rev": 1}, {"line": "a\n", "rev": 1}],
    "path": "a"
   },
   {
    "abspath": "b",
    "lines": [{"line": "a\n", "rev": 0}, {"line": "a\n", "rev": 1}, {"line": "a\n", "rev": 1}, {"line": "b4\n", "rev": 3}, {"line": "b5\n", "rev": 3}, {"line": "b6\n", "rev": 3}],
    "path": "b"
   }
  ]

annotate multiple files (template)

  $ hg annotate -T'== {abspath} ==\n{lines % "{rev}: {line}"}' a b
  == a ==
  0: a
  1: a
  1: a
  == b ==
  0: a
  1: a
  1: a
  3: b4
  3: b5
  3: b6

annotate -n b

  $ hg annotate -n b
  0: a
  1: a
  1: a
  3: b4
  3: b5
  3: b6

annotate --no-follow b

  $ hg annotate --no-follow b
  2: a
  2: a
  2: a
  3: b4
  3: b5
  3: b6

annotate -nl b

  $ hg annotate -nl b
  0:1: a
  1:2: a
  1:3: a
  3:4: b4
  3:5: b5
  3:6: b6

annotate -nf b

  $ hg annotate -nf b
  0 a: a
  1 a: a
  1 a: a
  3 b: b4
  3 b: b5
  3 b: b6

annotate -nlf b

  $ hg annotate -nlf b
  0 a:1: a
  1 a:2: a
  1 a:3: a
  3 b:4: b4
  3 b:5: b5
  3 b:6: b6

  $ hg up -C 2
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cat <<EOF >> b
  > b4
  > c
  > b5
  > EOF
  $ hg ci -mb2.1 -d '2 0'
  created new head
  $ hg merge
  merging b
  0 files updated, 1 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -mmergeb -d '3 0'

annotate after merge

  $ hg annotate -nf b
  0 a: a
  1 a: a
  1 a: a
  3 b: b4
  4 b: c
  3 b: b5

annotate after merge with -l

  $ hg annotate -nlf b
  0 a:1: a
  1 a:2: a
  1 a:3: a
  3 b:4: b4
  4 b:5: c
  3 b:5: b5

  $ hg up -C 1
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ hg cp a b
  $ cat <<EOF > b
  > a
  > z
  > a
  > EOF
  $ hg ci -mc -d '3 0'
  created new head
  $ hg merge
  merging b
  0 files updated, 1 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ cat <<EOF >> b
  > b4
  > c
  > b5
  > EOF
  $ echo d >> b
  $ hg ci -mmerge2 -d '4 0'

annotate after rename merge

  $ hg annotate -nf b
  0 a: a
  6 b: z
  1 a: a
  3 b: b4
  4 b: c
  3 b: b5
  7 b: d

annotate after rename merge with -l

  $ hg annotate -nlf b
  0 a:1: a
  6 b:2: z
  1 a:3: a
  3 b:4: b4
  4 b:5: c
  3 b:5: b5
  7 b:7: d

--skip nothing (should be the same as no --skip at all)

  $ hg annotate -nlf b --skip '1::0'
  0 a:1: a
  6 b:2: z
  1 a:3: a
  3 b:4: b4
  4 b:5: c
  3 b:5: b5
  7 b:7: d

--skip a modified line. Note a slight behavior difference in pure - this is
because the pure code comes up with slightly different deltas internally.

  $ hg annotate -nlf b --skip 6
  0 a:1: a
  1 a:2: z (no-pure !)
  0 a:1: z (pure !)
  1 a:3: a
  3 b:4: b4
  4 b:5: c
  3 b:5: b5
  7 b:7: d

--skip added lines (and test multiple skip)

  $ hg annotate -nlf b --skip 3
  0 a:1: a
  6 b:2: z
  1 a:3: a
  1 a:3: b4
  4 b:5: c
  1 a:3: b5
  7 b:7: d

  $ hg annotate -nlf b --skip 4
  0 a:1: a
  6 b:2: z
  1 a:3: a
  3 b:4: b4
  1 a:3: c
  3 b:5: b5
  7 b:7: d

  $ hg annotate -nlf b --skip 3 --skip 4
  0 a:1: a
  6 b:2: z
  1 a:3: a
  1 a:3: b4
  1 a:3: c
  1 a:3: b5
  7 b:7: d

  $ hg annotate -nlf b --skip 'merge()'
  0 a:1: a
  6 b:2: z
  1 a:3: a
  3 b:4: b4
  4 b:5: c
  3 b:5: b5
  3 b:5: d

--skip everything -- use the revision the file was introduced in

  $ hg annotate -nlf b --skip 'all()'
  0 a:1: a
  0 a:1: z
  0 a:1: a
  0 a:1: b4
  0 a:1: c
  0 a:1: b5
  0 a:1: d

Issue2807: alignment of line numbers with -l

  $ echo more >> b
  $ hg ci -mmore -d '5 0'
  $ echo more >> b
  $ hg ci -mmore -d '6 0'
  $ echo more >> b
  $ hg ci -mmore -d '7 0'
  $ hg annotate -nlf b
   0 a: 1: a
   6 b: 2: z
   1 a: 3: a
   3 b: 4: b4
   4 b: 5: c
   3 b: 5: b5
   7 b: 7: d
   8 b: 8: more
   9 b: 9: more
  10 b:10: more

linkrev vs rev

  $ hg annotate -r tip -n a
  0: a
  1: a
  1: a

linkrev vs rev with -l

  $ hg annotate -r tip -nl a
  0:1: a
  1:2: a
  1:3: a

Issue589: "undelete" sequence leads to crash

annotate was crashing when trying to --follow something

like A -> B -> A

generate ABA rename configuration

  $ echo foo > foo
  $ hg add foo
  $ hg ci -m addfoo
  $ hg rename foo bar
  $ hg ci -m renamefoo
  $ hg rename bar foo
  $ hg ci -m renamebar

annotate after ABA with follow

  $ hg annotate --follow foo
  foo: foo

missing file

  $ hg ann nosuchfile
  abort: nosuchfile: no such file in rev e9e6b4fa872f
  [255]

annotate file without '\n' on last line

  $ printf "" > c
  $ hg ci -A -m test -u nobody -d '1 0'
  adding c
  $ hg annotate c
  $ printf "a\nb" > c
  $ hg ci -m test
  $ hg annotate c
  [0-9]+: a (re)
  [0-9]+: b (re)

Issue3841: check annotation of the file of which filelog includes
merging between the revision and its ancestor

to reproduce the situation with recent Mercurial, this script uses (1)
"hg debugsetparents" to merge without ancestor check by "hg merge",
and (2) the extension to allow filelog merging between the revision
and its ancestor by overriding "repo._filecommit".

  $ cat > ../legacyrepo.py <<EOF
  > from mercurial import node, error
  > def reposetup(ui, repo):
  >     class legacyrepo(repo.__class__):
  >         def _filecommit(self, fctx, manifest1, manifest2,
  >                         linkrev, tr, changelist):
  >             fname = fctx.path()
  >             text = fctx.data()
  >             flog = self.file(fname)
  >             fparent1 = manifest1.get(fname, node.nullid)
  >             fparent2 = manifest2.get(fname, node.nullid)
  >             meta = {}
  >             copy = fctx.renamed()
  >             if copy and copy[0] != fname:
  >                 raise error.Abort('copying is not supported')
  >             if fparent2 != node.nullid:
  >                 changelist.append(fname)
  >                 return flog.add(text, meta, tr, linkrev,
  >                                 fparent1, fparent2)
  >             raise error.Abort('only merging is supported')
  >     repo.__class__ = legacyrepo
  > EOF

  $ cat > baz <<EOF
  > 1
  > 2
  > 3
  > 4
  > 5
  > EOF
  $ hg add baz
  $ hg commit -m "baz:0"

  $ cat > baz <<EOF
  > 1 baz:1
  > 2
  > 3
  > 4
  > 5
  > EOF
  $ hg commit -m "baz:1"

  $ cat > baz <<EOF
  > 1 baz:1
  > 2 baz:2
  > 3
  > 4
  > 5
  > EOF
  $ hg debugsetparents 17 17
  $ hg --config extensions.legacyrepo=../legacyrepo.py  commit -m "baz:2"
  $ hg debugindexdot .hg/store/data/baz.i
  digraph G {
  	-1 -> 0
  	0 -> 1
  	1 -> 2
  	1 -> 2
  }
  $ hg annotate baz
  17: 1 baz:1
  18: 2 baz:2
  16: 3
  16: 4
  16: 5

  $ cat > baz <<EOF
  > 1 baz:1
  > 2 baz:2
  > 3 baz:3
  > 4
  > 5
  > EOF
  $ hg commit -m "baz:3"

  $ cat > baz <<EOF
  > 1 baz:1
  > 2 baz:2
  > 3 baz:3
  > 4 baz:4
  > 5
  > EOF
  $ hg debugsetparents 19 18
  $ hg --config extensions.legacyrepo=../legacyrepo.py  commit -m "baz:4"
  $ hg debugindexdot .hg/store/data/baz.i
  digraph G {
  	-1 -> 0
  	0 -> 1
  	1 -> 2
  	1 -> 2
  	2 -> 3
  	3 -> 4
  	2 -> 4
  }
  $ hg annotate baz
  17: 1 baz:1
  18: 2 baz:2
  19: 3 baz:3
  20: 4 baz:4
  16: 5

annotate clean file

  $ hg annotate -ncr "wdir()" foo
  11 472b18db256d : foo

annotate modified file

  $ echo foofoo >> foo
  $ hg annotate -r "wdir()" foo
  11 : foo
  20+: foofoo

  $ hg annotate -cr "wdir()" foo
  472b18db256d : foo
  b6bedd5477e7+: foofoo

  $ hg annotate -ncr "wdir()" foo
  11 472b18db256d : foo
  20 b6bedd5477e7+: foofoo

  $ hg annotate --debug -ncr "wdir()" foo
  11 472b18db256d1e8282064eab4bfdaf48cbfe83cd : foo
  20 b6bedd5477e797f25e568a6402d4697f3f895a72+: foofoo

  $ hg annotate -udr "wdir()" foo
  test Thu Jan 01 00:00:00 1970 +0000: foo
  test [A-Za-z0-9:+ ]+: foofoo (re)

  $ hg annotate -ncr "wdir()" -Tjson foo
  [
   {
    "abspath": "foo",
    "lines": [{"line": "foo\n", "node": "472b18db256d1e8282064eab4bfdaf48cbfe83cd", "rev": 11}, {"line": "foofoo\n", "node": null, "rev": null}],
    "path": "foo"
   }
  ]

annotate added file

  $ echo bar > bar
  $ hg add bar
  $ hg annotate -ncr "wdir()" bar
  20 b6bedd5477e7+: bar

annotate renamed file

  $ hg rename foo renamefoo2
  $ hg annotate -ncr "wdir()" renamefoo2
  11 472b18db256d : foo
  20 b6bedd5477e7+: foofoo

annotate missing file

  $ rm baz

  $ hg annotate -ncr "wdir()" baz
  abort: $TESTTMP\repo\baz: The system cannot find the file specified (windows !)
  abort: No such file or directory: $TESTTMP/repo/baz (no-windows !)
  [255]

annotate removed file

  $ hg rm baz

  $ hg annotate -ncr "wdir()" baz
  abort: $TESTTMP\repo\baz: The system cannot find the file specified (windows !)
  abort: No such file or directory: $TESTTMP/repo/baz (no-windows !)
  [255]

  $ hg revert --all --no-backup --quiet
  $ hg id -n
  20

Test followlines() revset; we usually check both followlines(pat, range) and
followlines(pat, range, descend=True) to make sure both give the same result
when they should.

  $ echo a >> foo
  $ hg ci -m 'foo: add a'
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 3:5)'
  16: baz:0
  19: baz:3
  20: baz:4
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 3:5, startrev=20)'
  16: baz:0
  19: baz:3
  20: baz:4
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 3:5, startrev=19)'
  16: baz:0
  19: baz:3
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 3:5, startrev=19, descend=True)'
  19: baz:3
  20: baz:4
  $ printf "0\n0\n" | cat - baz > baz1
  $ mv baz1 baz
  $ hg ci -m 'added two lines with 0'
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 5:7)'
  16: baz:0
  19: baz:3
  20: baz:4
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 3:5, descend=true, startrev=19)'
  19: baz:3
  20: baz:4
  $ echo 6 >> baz
  $ hg ci -m 'added line 8'
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 5:7)'
  16: baz:0
  19: baz:3
  20: baz:4
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 3:5, startrev=19, descend=1)'
  19: baz:3
  20: baz:4
  $ sed 's/3/3+/' baz > baz.new
  $ mv baz.new baz
  $ hg ci -m 'baz:3->3+'
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 5:7, descend=0)'
  16: baz:0
  19: baz:3
  20: baz:4
  24: baz:3->3+
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 3:5, startrev=17, descend=True)'
  19: baz:3
  20: baz:4
  24: baz:3->3+
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 1:2, descend=false)'
  22: added two lines with 0

file patterns are okay
  $ hg log -T '{rev}: {desc}\n' -r 'followlines("path:baz", 1:2)'
  22: added two lines with 0

renames are followed
  $ hg mv baz qux
  $ sed 's/4/4+/' qux > qux.new
  $ mv qux.new qux
  $ hg ci -m 'qux:4->4+'
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(qux, 5:7)'
  16: baz:0
  19: baz:3
  20: baz:4
  24: baz:3->3+
  25: qux:4->4+

but are missed when following children
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 5:7, startrev=22, descend=True)'
  24: baz:3->3+

merge
  $ hg up 24 --quiet
  $ echo 7 >> baz
  $ hg ci -m 'one more line, out of line range'
  created new head
  $ sed 's/3+/3-/' baz > baz.new
  $ mv baz.new baz
  $ hg ci -m 'baz:3+->3-'
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 5:7)'
  16: baz:0
  19: baz:3
  20: baz:4
  24: baz:3->3+
  27: baz:3+->3-
  $ hg merge 25
  merging baz and qux to qux
  0 files updated, 1 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -m merge
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(qux, 5:7)'
  16: baz:0
  19: baz:3
  20: baz:4
  24: baz:3->3+
  25: qux:4->4+
  27: baz:3+->3-
  28: merge
  $ hg up 25 --quiet
  $ hg merge 27
  merging qux and baz to qux
  0 files updated, 1 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -m 'merge from other side'
  created new head
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(qux, 5:7)'
  16: baz:0
  19: baz:3
  20: baz:4
  24: baz:3->3+
  25: qux:4->4+
  27: baz:3+->3-
  29: merge from other side
  $ hg up 24 --quiet

we are missing the branch with rename when following children
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 5:7, startrev=26, descend=True)'
  27: baz:3+->3-

we follow all branches in descending direction
  $ hg up 23 --quiet
  $ sed 's/3/+3/' baz > baz.new
  $ mv baz.new baz
  $ hg ci -m 'baz:3->+3'
  created new head
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 2:5, startrev=16, descend=True)' --graph
  @  30: baz:3->+3
  :
  : o  27: baz:3+->3-
  : :
  : o  24: baz:3->3+
  :/
  o    20: baz:4
  |\
  | o  19: baz:3
  |/
  o  18: baz:2
  :
  o  16: baz:0
  |
  ~

Issue5595: on a merge changeset with different line ranges depending on
parent, be conservative and use the surrounding interval to avoid loosing
track of possible further descendants in specified range.

  $ hg up 23 --quiet
  $ hg cat baz -r 24
  0
  0
  1 baz:1
  2 baz:2
  3+ baz:3
  4 baz:4
  5
  6
  $ cat > baz << EOF
  > 0
  > 0
  > a
  > b
  > 3+ baz:3
  > 4 baz:4
  > y
  > z
  > EOF
  $ hg ci -m 'baz: mostly rewrite with some content from 24'
  created new head
  $ hg merge --tool :merge-other 24
  merging baz
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -m 'merge forgetting about baz rewrite'
  $ cat > baz << EOF
  > 0
  > 0
  > 1 baz:1
  > 2+ baz:2
  > 3+ baz:3
  > 4 baz:4
  > 5
  > 6
  > EOF
  $ hg ci -m 'baz: narrow change (2->2+)'
  $ hg log -T '{rev}: {desc}\n' -r 'followlines(baz, 3:4, startrev=20, descend=True)' --graph
  @  33: baz: narrow change (2->2+)
  |
  o    32: merge forgetting about baz rewrite
  |\
  | o  31: baz: mostly rewrite with some content from 24
  | :
  | : o  30: baz:3->+3
  | :/
  +---o  27: baz:3+->3-
  | :
  o :  24: baz:3->3+
  :/
  o    20: baz:4
  |\
  ~ ~

check error cases
  $ hg up 24 --quiet
  $ hg log -r 'followlines()'
  hg: parse error: followlines takes at least 1 positional arguments
  [255]
  $ hg log -r 'followlines(baz)'
  hg: parse error: followlines requires a line range
  [255]
  $ hg log -r 'followlines(baz, 1)'
  hg: parse error: followlines expects a line range
  [255]
  $ hg log -r 'followlines(baz, 1:2, startrev=desc("b"))'
  hg: parse error: followlines expects exactly one revision
  [255]
  $ hg log -r 'followlines("glob:*", 1:2)'
  hg: parse error: followlines expects exactly one file
  [255]
  $ hg log -r 'followlines(baz, 1:)'
  hg: parse error: line range bounds must be integers
  [255]
  $ hg log -r 'followlines(baz, :1)'
  hg: parse error: line range bounds must be integers
  [255]
  $ hg log -r 'followlines(baz, x:4)'
  hg: parse error: line range bounds must be integers
  [255]
  $ hg log -r 'followlines(baz, 5:4)'
  hg: parse error: line range must be positive
  [255]
  $ hg log -r 'followlines(baz, 0:4)'
  hg: parse error: fromline must be strictly positive
  [255]
  $ hg log -r 'followlines(baz, 2:40)'
  abort: line range exceeds file size
  [255]
  $ hg log -r 'followlines(baz, 2:4, startrev=20, descend=[1])'
  hg: parse error at 43: not a prefix: [
  [255]
  $ hg log -r 'followlines(baz, 2:4, startrev=20, descend=a)'
  hg: parse error: descend argument must be a boolean
  [255]

Test empty annotate output

  $ printf '\0' > binary
  $ touch empty
  $ hg ci -qAm 'add binary and empty files'

  $ hg annotate binary empty
  binary: binary file

  $ hg annotate -Tjson binary empty
  [
   {
    "abspath": "binary",
    "path": "binary"
   },
   {
    "abspath": "empty",
    "lines": [],
    "path": "empty"
   }
  ]

Test annotate with whitespace options

  $ cd ..
  $ hg init repo-ws
  $ cd repo-ws
  $ cat > a <<EOF
  > aa
  > 
  > b b
  > EOF
  $ hg ci -Am "adda"
  adding a
  $ sed 's/EOL$//g' > a <<EOF
  > a  a
  > 
  >  EOL
  > b  b
  > EOF
  $ hg ci -m "changea"

Annotate with no option

  $ hg annotate a
  1: a  a
  0: 
  1:  
  1: b  b

Annotate with --ignore-space-change

  $ hg annotate --ignore-space-change a
  1: a  a
  1: 
  0:  
  0: b  b

Annotate with --ignore-all-space

  $ hg annotate --ignore-all-space a
  0: a  a
  0: 
  1:  
  0: b  b

Annotate with --ignore-blank-lines (similar to no options case)

  $ hg annotate --ignore-blank-lines a
  1: a  a
  0: 
  1:  
  1: b  b

  $ cd ..

Annotate with linkrev pointing to another branch
------------------------------------------------

create history with a filerev whose linkrev points to another branch

  $ hg init branchedlinkrev
  $ cd branchedlinkrev
  $ echo A > a
  $ hg commit -Am 'contentA'
  adding a
  $ echo B >> a
  $ hg commit -m 'contentB'
  $ hg up --rev 'desc(contentA)'
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo unrelated > unrelated
  $ hg commit -Am 'unrelated'
  adding unrelated
  created new head
  $ hg graft -r 'desc(contentB)'
  grafting 1:fd27c222e3e6 "contentB"
  $ echo C >> a
  $ hg commit -m 'contentC'
  $ echo W >> a
  $ hg log -G
  @  changeset:   4:072f1e8df249
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     contentC
  |
  o  changeset:   3:ff38df03cc4b
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     contentB
  |
  o  changeset:   2:62aaf3f6fc06
  |  parent:      0:f0932f74827e
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     unrelated
  |
  | o  changeset:   1:fd27c222e3e6
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     contentB
  |
  o  changeset:   0:f0932f74827e
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     contentA
  

Annotate should list ancestor of starting revision only

  $ hg annotate a
  0: A
  3: B
  4: C

  $ hg annotate a -r 'wdir()'
  0 : A
  3 : B
  4 : C
  4+: W

Even when the starting revision is the linkrev-shadowed one:

  $ hg annotate a -r 3
  0: A
  3: B

  $ cd ..

Issue5360: Deleted chunk in p1 of a merge changeset

  $ hg init repo-5360
  $ cd repo-5360
  $ echo 1 > a
  $ hg commit -A a -m 1
  $ echo 2 >> a
  $ hg commit -m 2
  $ echo a > a
  $ hg commit -m a
  $ hg update '.^' -q
  $ echo 3 >> a
  $ hg commit -m 3 -q
  $ hg merge 2 -q
  $ cat > a << EOF
  > b
  > 1
  > 2
  > 3
  > a
  > EOF
  $ hg resolve --mark -q
  $ hg commit -m m
  $ hg annotate a
  4: b
  0: 1
  1: 2
  3: 3
  2: a

  $ cd ..
