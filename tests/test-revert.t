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

should keep d removed

  $ hg revert -r0 d
  no changes needed to d
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
but they all have a slightly different handling. So this section commits to
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

Write the python script to disk
-------------------------------

  $ cat << EOF > gen-revert-cases.py
  > # generate proper file state to test revert behavior
  > import sys
  > import os
  > 
  > # content of the file in "base" and "parent"
  > # None means no file at all
  > ctxcontent = {
  >     # clean: no change from base to parent
  >     'clean': ['base', 'base'],
  >     # modified: file content change from base to parent
  >     'modified': ['base', 'parent'],
  >     # added: file is missing from base and added in parent
  >     'added': [None, 'parent'],
  >     # removed: file exist in base but is removed from parent
  >     'removed': ['base', None],
  >     # file exist neither in base not in parent
  >     'missing': [None, None],
  > }
  > 
  > # content of file in working copy
  > wccontent = {
  >     # clean: wc content is the same as parent
  >     'clean': lambda cc: cc[1],
  >     # revert: wc content is the same as base
  >     'revert': lambda cc: cc[0],
  >     # wc: file exist with a content different from base and parent
  >     'wc': lambda cc: 'wc',
  >     # removed: file is missing and marked as untracked
  >     'removed': lambda cc: None,
  >     # deleted: file is recorded as tracked but missing
  >     #          rely on file deletion outside of this script
  >     'deleted': lambda cc:'TOBEDELETED',
  > }
  > # untracked-X is a version of X where the file is not tracked (? unknown)
  > wccontent['untracked-clean'] = wccontent['clean']
  > wccontent['untracked-revert'] = wccontent['revert']
  > wccontent['untracked-wc'] = wccontent['wc']
  > 
  > # build the combination of possible states
  > combination = []
  > for ctxkey, ctxvalue in ctxcontent.iteritems():
  >     for wckey in wccontent:
  >         if (ctxvalue[0] == ctxvalue[1] and 'revert' in wckey):
  >             continue
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
  >     if target == 'filelist':
  >         print filename
  >     elif target == 'base':
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
  >     if data is not None:
  >         f = open(filename, 'w')
  >         f.write(data + '\n')
  >         f.close()
  >     elif os.path.exists(filename):
  >        os.remove(filename)
  > EOF

check list of planned files

  $ python gen-revert-cases.py filelist
  added_clean
  added_deleted
  added_removed
  added_revert
  added_untracked-clean
  added_untracked-revert
  added_untracked-wc
  added_wc
  clean_clean
  clean_deleted
  clean_removed
  clean_untracked-clean
  clean_untracked-wc
  clean_wc
  missing_clean
  missing_deleted
  missing_removed
  missing_untracked-clean
  missing_untracked-wc
  missing_wc
  modified_clean
  modified_deleted
  modified_removed
  modified_revert
  modified_untracked-clean
  modified_untracked-revert
  modified_untracked-wc
  modified_wc
  removed_clean
  removed_deleted
  removed_removed
  removed_revert
  removed_untracked-clean
  removed_untracked-revert
  removed_untracked-wc
  removed_wc

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
  adding clean_clean
  adding clean_deleted
  adding clean_removed
  adding clean_untracked-clean
  adding clean_untracked-wc
  adding clean_wc
  adding modified_clean
  adding modified_deleted
  adding modified_removed
  adding modified_revert
  adding modified_untracked-clean
  adding modified_untracked-revert
  adding modified_untracked-wc
  adding modified_wc
  adding removed_clean
  adding removed_deleted
  adding removed_removed
  adding removed_revert
  adding removed_untracked-clean
  adding removed_untracked-revert
  adding removed_untracked-wc
  adding removed_wc
  $ hg status
  A clean_clean
  A clean_deleted
  A clean_removed
  A clean_untracked-clean
  A clean_untracked-wc
  A clean_wc
  A modified_clean
  A modified_deleted
  A modified_removed
  A modified_revert
  A modified_untracked-clean
  A modified_untracked-revert
  A modified_untracked-wc
  A modified_wc
  A removed_clean
  A removed_deleted
  A removed_removed
  A removed_revert
  A removed_untracked-clean
  A removed_untracked-revert
  A removed_untracked-wc
  A removed_wc
  $ hg commit -m 'base'

(create a simple text version of the content)

  $ python ../dircontent.py > ../content-base.txt
  $ cat ../content-base.txt
  base   clean_clean
  base   clean_deleted
  base   clean_removed
  base   clean_untracked-clean
  base   clean_untracked-wc
  base   clean_wc
  base   modified_clean
  base   modified_deleted
  base   modified_removed
  base   modified_revert
  base   modified_untracked-clean
  base   modified_untracked-revert
  base   modified_untracked-wc
  base   modified_wc
  base   removed_clean
  base   removed_deleted
  base   removed_removed
  base   removed_revert
  base   removed_untracked-clean
  base   removed_untracked-revert
  base   removed_untracked-wc
  base   removed_wc

Create parent changeset

  $ python ../gen-revert-cases.py parent
  $ hg addremove --similarity 0
  adding added_clean
  adding added_deleted
  adding added_removed
  adding added_revert
  adding added_untracked-clean
  adding added_untracked-revert
  adding added_untracked-wc
  adding added_wc
  removing removed_clean
  removing removed_deleted
  removing removed_removed
  removing removed_revert
  removing removed_untracked-clean
  removing removed_untracked-revert
  removing removed_untracked-wc
  removing removed_wc
  $ hg status
  M modified_clean
  M modified_deleted
  M modified_removed
  M modified_revert
  M modified_untracked-clean
  M modified_untracked-revert
  M modified_untracked-wc
  M modified_wc
  A added_clean
  A added_deleted
  A added_removed
  A added_revert
  A added_untracked-clean
  A added_untracked-revert
  A added_untracked-wc
  A added_wc
  R removed_clean
  R removed_deleted
  R removed_removed
  R removed_revert
  R removed_untracked-clean
  R removed_untracked-revert
  R removed_untracked-wc
  R removed_wc
  $ hg commit -m 'parent'

(create a simple text version of the content)

  $ python ../dircontent.py > ../content-parent.txt
  $ cat ../content-parent.txt
  parent added_clean
  parent added_deleted
  parent added_removed
  parent added_revert
  parent added_untracked-clean
  parent added_untracked-revert
  parent added_untracked-wc
  parent added_wc
  base   clean_clean
  base   clean_deleted
  base   clean_removed
  base   clean_untracked-clean
  base   clean_untracked-wc
  base   clean_wc
  parent modified_clean
  parent modified_deleted
  parent modified_removed
  parent modified_revert
  parent modified_untracked-clean
  parent modified_untracked-revert
  parent modified_untracked-wc
  parent modified_wc

Setup working directory

  $ python ../gen-revert-cases.py wc
  $ hg addremove --similarity 0
  removing added_removed
  removing added_revert
  removing added_untracked-revert
  removing clean_removed
  adding missing_deleted
  adding missing_untracked-wc
  adding missing_wc
  removing modified_removed
  adding removed_deleted
  adding removed_revert
  adding removed_untracked-revert
  adding removed_untracked-wc
  adding removed_wc
  $ hg forget *untracked*
  $ rm *deleted*
  $ hg status
  M added_wc
  M clean_wc
  M modified_revert
  M modified_wc
  A missing_wc
  A removed_revert
  A removed_wc
  R added_removed
  R added_revert
  R added_untracked-clean
  R added_untracked-revert
  R added_untracked-wc
  R clean_removed
  R clean_untracked-clean
  R clean_untracked-wc
  R modified_removed
  R modified_untracked-clean
  R modified_untracked-revert
  R modified_untracked-wc
  ! added_deleted
  ! clean_deleted
  ! missing_deleted
  ! modified_deleted
  ! removed_deleted
  ? missing_untracked-wc
  ? removed_untracked-revert
  ? removed_untracked-wc

  $ hg status --rev 'desc("base")'
  M clean_wc
  M modified_clean
  M modified_wc
  M removed_wc
  A added_clean
  A added_wc
  A missing_wc
  R clean_removed
  R clean_untracked-clean
  R clean_untracked-wc
  R modified_removed
  R modified_untracked-clean
  R modified_untracked-revert
  R modified_untracked-wc
  R removed_clean
  R removed_deleted
  R removed_removed
  R removed_untracked-clean
  R removed_untracked-revert
  R removed_untracked-wc
  ! added_deleted
  ! clean_deleted
  ! missing_deleted
  ! modified_deleted
  ! removed_deleted
  ? missing_untracked-wc

(create a simple text version of the content)

  $ python ../dircontent.py > ../content-wc.txt
  $ cat ../content-wc.txt
  parent added_clean
  parent added_untracked-clean
  wc     added_untracked-wc
  wc     added_wc
  base   clean_clean
  base   clean_untracked-clean
  wc     clean_untracked-wc
  wc     clean_wc
  wc     missing_untracked-wc
  wc     missing_wc
  parent modified_clean
  base   modified_revert
  parent modified_untracked-clean
  base   modified_untracked-revert
  wc     modified_untracked-wc
  wc     modified_wc
  base   removed_revert
  base   removed_untracked-revert
  wc     removed_untracked-wc
  wc     removed_wc

  $ cd ..

Test revert --all to parent content
-----------------------------------

(setup from reference repo)

  $ cp -r revert-ref revert-parent-all
  $ cd revert-parent-all

check revert output

  $ hg revert --all
  reverting added_deleted
  undeleting added_removed
  undeleting added_revert
  undeleting added_untracked-clean
  undeleting added_untracked-revert
  undeleting added_untracked-wc
  reverting added_wc
  reverting clean_deleted
  undeleting clean_removed
  undeleting clean_untracked-clean
  undeleting clean_untracked-wc
  reverting clean_wc
  forgetting missing_deleted
  forgetting missing_wc
  reverting modified_deleted
  undeleting modified_removed
  reverting modified_revert
  undeleting modified_untracked-clean
  undeleting modified_untracked-revert
  undeleting modified_untracked-wc
  reverting modified_wc
  forgetting removed_deleted
  forgetting removed_revert
  forgetting removed_wc

Compare resulting directory with revert target.

The diff is filtered to include change only. The only difference should be
additional `.orig` backup file when applicable.

  $ python ../dircontent.py > ../content-parent-all.txt
  $ cd ..
  $ diff -U 0 -- content-parent.txt content-parent-all.txt | grep _
  +wc     added_untracked-wc.orig
  +wc     added_wc.orig
  +wc     clean_untracked-wc.orig
  +wc     clean_wc.orig
  +wc     missing_untracked-wc
  +wc     missing_wc
  +base   modified_revert.orig
  +base   modified_untracked-revert.orig
  +wc     modified_untracked-wc.orig
  +wc     modified_wc.orig
  +base   removed_revert
  +base   removed_untracked-revert
  +wc     removed_untracked-wc
  +wc     removed_wc

Test revert --all to "base" content
-----------------------------------

(setup from reference repo)

  $ cp -r revert-ref revert-base-all
  $ cd revert-base-all

check revert output

  $ hg revert --all --rev 'desc(base)'
  removing added_clean
  removing added_deleted
  removing added_wc
  reverting clean_deleted
  undeleting clean_removed
  undeleting clean_untracked-clean
  undeleting clean_untracked-wc
  reverting clean_wc
  forgetting missing_deleted
  forgetting missing_wc
  reverting modified_clean
  reverting modified_deleted
  undeleting modified_removed
  undeleting modified_untracked-clean
  undeleting modified_untracked-revert
  undeleting modified_untracked-wc
  reverting modified_wc
  adding removed_clean
  reverting removed_deleted
  adding removed_removed
  adding removed_untracked-clean
  adding removed_untracked-revert
  adding removed_untracked-wc
  reverting removed_wc

Compare resulting directory with revert target.

The diff is filtered to include change only. The only difference should be
additional `.orig` backup file when applicable.

  $ python ../dircontent.py > ../content-base-all.txt
  $ cd ..
  $ diff -U 0 -- content-base.txt content-base-all.txt | grep _
  +parent added_untracked-clean
  +wc     added_untracked-wc
  +wc     added_wc.orig
  +wc     clean_untracked-wc.orig
  +wc     clean_wc.orig
  +wc     missing_untracked-wc
  +wc     missing_wc
  +parent modified_untracked-clean.orig
  +wc     modified_untracked-wc.orig
  +wc     modified_wc.orig
  +wc     removed_untracked-wc.orig
  +wc     removed_wc.orig

Test revert to parent content with explicit file name
-----------------------------------------------------

(setup from reference repo)

  $ cp -r revert-ref revert-parent-explicit
  $ cd revert-parent-explicit

revert all files individually and check the output
(output is expected to be different than in the --all case)

  $ for file in `python ../gen-revert-cases.py filelist`; do
  >   echo '### revert for:' $file;
  >   hg revert $file;
  >   echo
  > done
  ### revert for: added_clean
  no changes needed to added_clean
  
  ### revert for: added_deleted
  
  ### revert for: added_removed
  
  ### revert for: added_revert
  
  ### revert for: added_untracked-clean
  
  ### revert for: added_untracked-revert
  
  ### revert for: added_untracked-wc
  
  ### revert for: added_wc
  
  ### revert for: clean_clean
  no changes needed to clean_clean
  
  ### revert for: clean_deleted
  
  ### revert for: clean_removed
  
  ### revert for: clean_untracked-clean
  
  ### revert for: clean_untracked-wc
  
  ### revert for: clean_wc
  
  ### revert for: missing_clean
  missing_clean: no such file in rev * (glob)
  
  ### revert for: missing_deleted
  
  ### revert for: missing_removed
  missing_removed: no such file in rev * (glob)
  
  ### revert for: missing_untracked-clean
  missing_untracked-clean: no such file in rev * (glob)
  
  ### revert for: missing_untracked-wc
  file not managed: missing_untracked-wc
  
  ### revert for: missing_wc
  
  ### revert for: modified_clean
  no changes needed to modified_clean
  
  ### revert for: modified_deleted
  
  ### revert for: modified_removed
  
  ### revert for: modified_revert
  
  ### revert for: modified_untracked-clean
  
  ### revert for: modified_untracked-revert
  
  ### revert for: modified_untracked-wc
  
  ### revert for: modified_wc
  
  ### revert for: removed_clean
  removed_clean: no such file in rev * (glob)
  
  ### revert for: removed_deleted
  
  ### revert for: removed_removed
  removed_removed: no such file in rev * (glob)
  
  ### revert for: removed_revert
  
  ### revert for: removed_untracked-clean
  removed_untracked-clean: no such file in rev * (glob)
  
  ### revert for: removed_untracked-revert
  file not managed: removed_untracked-revert
  
  ### revert for: removed_untracked-wc
  file not managed: removed_untracked-wc
  
  ### revert for: removed_wc
  

check resulting directory against the --all run
(There should be no difference)

  $ python ../dircontent.py > ../content-parent-explicit.txt
  $ cd ..
  $ diff -U 0 -- content-parent-all.txt content-parent-explicit.txt | grep _
  [1]

Test revert to "base" content with explicit file name
-----------------------------------------------------

(setup from reference repo)

  $ cp -r revert-ref revert-base-explicit
  $ cd revert-base-explicit

revert all files individually and check the output
(output is expected to be different than in the --all case)

  $ for file in `python ../gen-revert-cases.py filelist`; do
  >   echo '### revert for:' $file;
  >   hg revert $file --rev 'desc(base)';
  >   echo
  > done
  ### revert for: added_clean
  
  ### revert for: added_deleted
  
  ### revert for: added_removed
  no changes needed to added_removed
  
  ### revert for: added_revert
  no changes needed to added_revert
  
  ### revert for: added_untracked-clean
  no changes needed to added_untracked-clean
  
  ### revert for: added_untracked-revert
  no changes needed to added_untracked-revert
  
  ### revert for: added_untracked-wc
  no changes needed to added_untracked-wc
  
  ### revert for: added_wc
  
  ### revert for: clean_clean
  no changes needed to clean_clean
  
  ### revert for: clean_deleted
  
  ### revert for: clean_removed
  
  ### revert for: clean_untracked-clean
  
  ### revert for: clean_untracked-wc
  
  ### revert for: clean_wc
  
  ### revert for: missing_clean
  missing_clean: no such file in rev * (glob)
  
  ### revert for: missing_deleted
  
  ### revert for: missing_removed
  missing_removed: no such file in rev * (glob)
  
  ### revert for: missing_untracked-clean
  missing_untracked-clean: no such file in rev * (glob)
  
  ### revert for: missing_untracked-wc
  file not managed: missing_untracked-wc
  
  ### revert for: missing_wc
  
  ### revert for: modified_clean
  
  ### revert for: modified_deleted
  
  ### revert for: modified_removed
  
  ### revert for: modified_revert
  no changes needed to modified_revert
  
  ### revert for: modified_untracked-clean
  
  ### revert for: modified_untracked-revert
  
  ### revert for: modified_untracked-wc
  
  ### revert for: modified_wc
  
  ### revert for: removed_clean
  
  ### revert for: removed_deleted
  
  ### revert for: removed_removed
  
  ### revert for: removed_revert
  no changes needed to removed_revert
  
  ### revert for: removed_untracked-clean
  
  ### revert for: removed_untracked-revert
  
  ### revert for: removed_untracked-wc
  
  ### revert for: removed_wc
  

check resulting directory against the --all run
(There should be no difference)

  $ python ../dircontent.py > ../content-base-explicit.txt
  $ cd ..
  $ diff -U 0 -- content-base-all.txt content-base-explicit.txt | grep _
  [1]
