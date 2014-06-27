  $ hg init repo
  $ cd repo
  $ echo 123 > a
  $ echo 123 > c
  $ echo 123 > e
  $ hg add a c e
  $ hg commit -m "first" a c e

nothing changed

  $ hg revert
  abort: no files or directories specified
  (use --all to revert all files)
  [255]
  $ hg revert --all

Introduce some changes and revert them
--------------------------------------

  $ echo 123 > b

  $ hg status
  ? b
  $ echo 12 > c

  $ hg status
  M c
  ? b
  $ hg add b

  $ hg status
  M c
  A b
  $ hg rm a

  $ hg status
  M c
  A b
  R a

revert removal of a file

  $ hg revert a
  $ hg status
  M c
  A b

revert addition of a file

  $ hg revert b
  $ hg status
  M c
  ? b

revert modification of a file (--no-backup)

  $ hg revert --no-backup c
  $ hg status
  ? b

revert deletion (! status) of a added file
------------------------------------------

  $ hg add b

  $ hg status b
  A b
  $ rm b
  $ hg status b
  ! b
  $ hg revert -v b
  forgetting b
  $ hg status b
  b: * (glob)

  $ ls
  a
  c
  e

Test creation of backup (.orig) files
-------------------------------------

  $ echo z > e
  $ hg revert --all -v
  saving current version of e as e.orig
  reverting e

revert on clean file (no change)
--------------------------------

  $ hg revert a
  no changes needed to a

revert on an untracked file
---------------------------

  $ echo q > q
  $ hg revert q
  file not managed: q
  $ rm q

revert on file that does not exists
-----------------------------------

  $ hg revert notfound
  notfound: no such file in rev 334a9e57682c
  $ touch d
  $ hg add d
  $ hg rm a
  $ hg commit -m "second"
  $ echo z > z
  $ hg add z
  $ hg st
  A z
  ? e.orig

revert to another revision (--rev)
----------------------------------

  $ hg revert --all -r0
  adding a
  removing d
  forgetting z

revert explicitly to parent (--rev)
-----------------------------------

  $ hg revert --all -rtip
  forgetting a
  undeleting d
  $ rm a *.orig

revert to another revision (--rev) and exact match
--------------------------------------------------

exact match are more silent

  $ hg revert -r0 a
  $ hg st a
  A a
  $ hg rm d
  $ hg st d
  R d

should silently keep d removed

  $ hg revert -r0 d
  $ hg st d
  R d

  $ hg update -C
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved

revert of exec bit
------------------

#if execbit
  $ chmod +x c
  $ hg revert --all
  reverting c

  $ test -x c || echo non-executable
  non-executable

  $ chmod +x c
  $ hg commit -m exe

  $ chmod -x c
  $ hg revert --all
  reverting c

  $ test -x c && echo executable
  executable
#endif

  $ cd ..


Issue241: update and revert produces inconsistent repositories
--------------------------------------------------------------

  $ hg init a
  $ cd a
  $ echo a >> a
  $ hg commit -A -d '1 0' -m a
  adding a
  $ echo a >> a
  $ hg commit -d '2 0' -m a
  $ hg update 0
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ mkdir b
  $ echo b > b/b

call `hg revert` with no file specified
---------------------------------------

  $ hg revert -rtip
  abort: no files or directories specified
  (use --all to revert all files, or 'hg update 1' to update)
  [255]

call `hg revert` with --all
---------------------------

  $ hg revert --all -rtip
  reverting a


Issue332: confusing message when reverting directory
----------------------------------------------------

  $ hg ci -A -m b
  adding b/b
  created new head
  $ echo foobar > b/b
  $ mkdir newdir
  $ echo foo > newdir/newfile
  $ hg add newdir/newfile
  $ hg revert b newdir
  reverting b/b (glob)
  forgetting newdir/newfile (glob)
  $ echo foobar > b/b
  $ hg revert .
  reverting b/b (glob)


reverting a rename target should revert the source
--------------------------------------------------

  $ hg mv a newa
  $ hg revert newa
  $ hg st a newa
  ? newa

  $ cd ..

  $ hg init ignored
  $ cd ignored
  $ echo '^ignored$' > .hgignore
  $ echo '^ignoreddir$' >> .hgignore
  $ echo '^removed$' >> .hgignore

  $ mkdir ignoreddir
  $ touch ignoreddir/file
  $ touch ignoreddir/removed
  $ touch ignored
  $ touch removed

4 ignored files (we will add/commit everything)

  $ hg st -A -X .hgignore
  I ignored
  I ignoreddir/file
  I ignoreddir/removed
  I removed
  $ hg ci -qAm 'add files' ignored ignoreddir/file ignoreddir/removed removed

  $ echo >> ignored
  $ echo >> ignoreddir/file
  $ hg rm removed ignoreddir/removed

should revert ignored* and undelete *removed
--------------------------------------------

  $ hg revert -a --no-backup
  reverting ignored
  reverting ignoreddir/file (glob)
  undeleting ignoreddir/removed (glob)
  undeleting removed
  $ hg st -mardi

  $ hg up -qC
  $ echo >> ignored
  $ hg rm removed

should silently revert the named files
--------------------------------------

  $ hg revert --no-backup ignored removed
  $ hg st -mardi

Reverting copy (issue3920)
--------------------------

someone set up us the copies

  $ rm .hgignore
  $ hg update -C
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg mv ignored allyour
  $ hg copy removed base
  $ hg commit -m rename

copies and renames, you have no chance to survive make your time (issue3920)

  $ hg update '.^'
  1 files updated, 0 files merged, 2 files removed, 0 files unresolved
  $ hg revert -rtip -a
  adding allyour
  adding base
  removing ignored
  $ hg status -C
  A allyour
    ignored
  A base
    removed
  R ignored

Test revert of a file added by one side of the merge
====================================================

remove any pending change

  $ hg revert --all
  forgetting allyour
  forgetting base
  undeleting ignored
  $ hg purge --all --config extensions.purge=

Adds a new commit

  $ echo foo > newadd
  $ hg add newadd
  $ hg commit -m 'other adds'
  created new head


merge it with the other head

  $ hg merge # merge 1 into 2
  2 files updated, 0 files merged, 1 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg summary
  parent: 2:b8ec310b2d4e tip
   other adds
  parent: 1:f6180deb8fbe 
   rename
  branch: default
  commit: 2 modified, 1 removed (merge)
  update: (current)

clarifies who added what

  $ hg status
  M allyour
  M base
  R ignored
  $ hg status --change 'p1()'
  A newadd
  $ hg status --change 'p2()'
  A allyour
  A base
  R ignored

revert file added by p1() to p1() state
-----------------------------------------

  $ hg revert -r 'p1()' 'glob:newad?'
  $ hg status
  M allyour
  M base
  R ignored

revert file added by p1() to p2() state
------------------------------------------

  $ hg revert -r 'p2()' 'glob:newad?'
  removing newadd
  $ hg status
  M allyour
  M base
  R ignored
  R newadd

revert file added by p2() to p2() state
------------------------------------------

  $ hg revert -r 'p2()' 'glob:allyou?'
  $ hg status
  M allyour
  M base
  R ignored
  R newadd

revert file added by p2() to p1() state
------------------------------------------

  $ hg revert -r 'p1()' 'glob:allyou?'
  removing allyour
  $ hg status
  M base
  R allyour
  R ignored
  R newadd

Systematic behavior validation of most possible cases
=====================================================

This section tests most of the possible combinations of working directory
changes and inter-revision changes. The number of possible cases is significant
but they all have a slighly different handling. So this section commits to
generating and testing all of them to allow safe refactoring of the revert code.

A python script is used to generate a file history for each combination of
changes between, on one side the working directory and its parent and on
the other side, changes between a revert target (--rev) and working directory
parent. The three states generated are:

- a "base" revision
- a "parent" revision
- the working directory (based on "parent")

The file generated have names of the form:

 <changeset-state>_<working-copy-state>

Here, "changeset-state" conveys the state in "base" and "parent" (or the change
that happen between them), "working-copy-state" is self explanatory.

All known states are not tested yet. See inline documentation for details.
Special cases from merge and rename are not tested by this section.

There are also multiple cases where the current revert implementation is known to
slightly misbehave.

Write the python script to disk
-------------------------------

  $ cat << EOF > gen-revert-cases.py
  > # generate proper file state to test revert behavior
  > import sys
  > 
  > # content of the file in "base" and "parent"
  > ctxcontent = {
  >     # modified: file content change from base to parent
  >     'modified': ['base', 'parent'],
  > }
  > 
  > # content of file in working copy
  > wccontent = {
  >     # clean: wc content is the same as parent
  >     'clean': lambda cc: cc[1],
  > }
  > 
  > # build the combination of possible states
  > combination = []
  > for ctxkey in ctxcontent:
  >     for wckey in wccontent:
  >         filename = "%s_%s" % (ctxkey, wckey)
  >         combination.append((filename, ctxkey, wckey))
  > 
  > # make sure we have stable output
  > combination.sort()
  > 
  > # retrieve the state we must generate
  > target = sys.argv[1]
  > 
  > # compute file content
  > content = []
  > for filename, ctxkey, wckey in combination:
  >     cc = ctxcontent[ctxkey]
  >     if target == 'base':
  >         content.append((filename, cc[0]))
  >     elif target == 'parent':
  >         content.append((filename, cc[1]))
  >     elif target == 'wc':
  >         content.append((filename, wccontent[wckey](cc)))
  >     else:
  >         print >> sys.stderr, "unknown target:", target
  >         sys.exit(1)
  > 
  > # write actual content
  > for filename, data in content:
  >     f = open(filename, 'w')
  >     f.write(data + '\n')
  >     f.close()
  > EOF

Script to make a simple text version of the content
---------------------------------------------------

  $ cat << EOF >> dircontent.py
  > # generate a simple text view of the directory for easy comparison
  > import os
  > files = os.listdir('.')
  > files.sort()
  > for filename in files:
  >     if os.path.isdir(filename):
  >         continue
  >     content = open(filename).read()
  >     print '%-6s %s' % (content.strip(), filename)
  > EOF

Generate appropriate repo state
-------------------------------

  $ hg init revert-ref
  $ cd revert-ref

Generate base changeset

  $ python ../gen-revert-cases.py base
  $ hg addremove --similarity 0
  adding modified_clean
  $ hg status
  A modified_clean
  $ hg commit -m 'base'

(create a simple text version of the content)

  $ python ../dircontent.py > ../content-base.txt
  $ cat ../content-base.txt
  base   modified_clean

Create parent changeset

  $ python ../gen-revert-cases.py parent
  $ hg addremove --similarity 0
  $ hg status
  M modified_clean
  $ hg commit -m 'parent'

(create a simple text version of the content)

  $ python ../dircontent.py > ../content-parent.txt
  $ cat ../content-parent.txt
  parent modified_clean

Setup working directory

  $ python ../gen-revert-cases.py wc | cat
  $ hg addremove --similarity 0
  $ hg status

  $ hg status --rev 'desc("base")'
  M modified_clean

(create a simple text version of the content)

  $ python ../dircontent.py > ../content-wc.txt
  $ cat ../content-wc.txt
  parent modified_clean

  $ cd ..

