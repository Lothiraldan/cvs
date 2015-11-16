test that a commit clears the merge state.

  $ hg init repo
  $ cd repo

  $ echo foo > file1
  $ echo foo > file2
  $ hg commit -Am 'add files'
  adding file1
  adding file2

  $ echo bar >> file1
  $ echo bar >> file2
  $ hg commit -Am 'append bar to files'

create a second head with conflicting edits

  $ hg up -C 0
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo baz >> file1
  $ echo baz >> file2
  $ hg commit -Am 'append baz to files'
  created new head

create a third head with no conflicting edits
  $ hg up -qC 0
  $ echo foo > file3
  $ hg commit -Am 'add non-conflicting file'
  adding file3
  created new head

failing merge

  $ hg up -qC 2
  $ hg merge --tool=internal:fail 1
  0 files updated, 0 files merged, 0 files removed, 2 files unresolved
  use 'hg resolve' to retry unresolved file merges or 'hg update -C .' to abandon
  [1]

resolve -l should contain unresolved entries

  $ hg resolve -l
  U file1
  U file2

  $ hg resolve -l --no-status
  file1
  file2

resolving an unknown path should emit a warning, but not for -l

  $ hg resolve -m does-not-exist
  arguments do not match paths that need resolving
  $ hg resolve -l does-not-exist

don't allow marking or unmarking driver-resolved files

  $ cat > $TESTTMP/markdriver.py << EOF
  > '''mark and unmark files as driver-resolved'''
  > from mercurial import cmdutil, merge, scmutil
  > cmdtable = {}
  > command = cmdutil.command(cmdtable)
  > @command('markdriver',
  >   [('u', 'unmark', None, '')],
  >   'FILE...')
  > def markdriver(ui, repo, *pats, **opts):
  >     wlock = repo.wlock()
  >     try:
  >         ms = merge.mergestate(repo)
  >         m = scmutil.match(repo[None], pats, opts)
  >         for f in ms:
  >             if not m(f):
  >                 continue
  >             if not opts['unmark']:
  >                 ms.mark(f, 'd')
  >             else:
  >                 ms.mark(f, 'u')
  >         ms.commit()
  >     finally:
  >         wlock.release()
  > EOF
  $ hg --config extensions.markdriver=$TESTTMP/markdriver.py markdriver file1
  $ hg resolve --list
  D file1
  U file2
  $ hg resolve --mark file1
  not marking file1 as it is driver-resolved
this should not print out file1
  $ hg resolve --mark --all
  (no more unresolved files -- run "hg resolve --all" to conclude)
  $ hg resolve --mark 'glob:file*'
  (no more unresolved files -- run "hg resolve --all" to conclude)
  $ hg resolve --list
  D file1
  R file2
  $ hg resolve --unmark file1
  not unmarking file1 as it is driver-resolved
  (no more unresolved files -- run "hg resolve --all" to conclude)
  $ hg resolve --unmark --all
  $ hg resolve --list
  D file1
  U file2
  $ hg --config extensions.markdriver=$TESTTMP/markdriver.py markdriver --unmark file1
  $ hg resolve --list
  U file1
  U file2

resolve the failure

  $ echo resolved > file1
  $ hg resolve -m file1

resolve -l should show resolved file as resolved

  $ hg resolve -l
  R file1
  U file2

  $ hg resolve -l -Tjson
  [
   {
    "path": "file1",
    "status": "R"
   },
   {
    "path": "file2",
    "status": "U"
   }
  ]

resolve -m without paths should mark all resolved

  $ hg resolve -m
  (no more unresolved files)
  $ hg commit -m 'resolved'

resolve -l should be empty after commit

  $ hg resolve -l

  $ hg resolve -l -Tjson
  [
  ]

resolve --all should abort when no merge in progress

  $ hg resolve --all
  abort: resolve command not applicable when not merging
  [255]

resolve -m should abort when no merge in progress

  $ hg resolve -m
  abort: resolve command not applicable when not merging
  [255]

set up conflict-free merge

  $ hg up -qC 3
  $ hg merge 1
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)

resolve --all should do nothing in merge without conflicts
  $ hg resolve --all
  (no more unresolved files)

resolve -m should do nothing in merge without conflicts

  $ hg resolve -m
  (no more unresolved files)

get back to conflicting state

  $ hg up -qC 2
  $ hg merge --tool=internal:fail 1
  0 files updated, 0 files merged, 0 files removed, 2 files unresolved
  use 'hg resolve' to retry unresolved file merges or 'hg update -C .' to abandon
  [1]

resolve without arguments should suggest --all
  $ hg resolve
  abort: no files or directories specified
  (use --all to re-merge all unresolved files)
  [255]

resolve --all should re-merge all unresolved files
  $ hg resolve --all
  merging file1
  merging file2
  warning: conflicts while merging file1! (edit, then use 'hg resolve --mark')
  warning: conflicts while merging file2! (edit, then use 'hg resolve --mark')
  [1]
  $ cat file1.orig
  foo
  baz
  $ cat file2.orig
  foo
  baz

.orig files should exists where specified
  $ hg resolve --all --verbose --config 'ui.origbackuppath=.hg/origbackups'
  merging file1
  creating directory: $TESTTMP/repo/.hg/origbackups (glob)
  merging file2
  warning: conflicts while merging file1! (edit, then use 'hg resolve --mark')
  warning: conflicts while merging file2! (edit, then use 'hg resolve --mark')
  [1]
  $ ls .hg/origbackups
  file1.orig
  file2.orig
  $ grep '<<<' file1 > /dev/null
  $ grep '<<<' file2 > /dev/null

resolve <file> should re-merge file
  $ echo resolved > file1
  $ hg resolve -q file1
  warning: conflicts while merging file1! (edit, then use 'hg resolve --mark')
  [1]
  $ grep '<<<' file1 > /dev/null

resolve <file> should do nothing if 'file' was marked resolved
  $ echo resolved > file1
  $ hg resolve -m file1
  $ hg resolve -q file1
  $ cat file1
  resolved

test crashed merge with empty mergestate

  $ hg up -qC 1
  $ mkdir .hg/merge
  $ touch .hg/merge/state

resolve -l should be empty

  $ hg resolve -l

  $ cd ..
