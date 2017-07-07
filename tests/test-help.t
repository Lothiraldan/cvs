Short help:

  $ hg
  Mercurial Distributed SCM
  
  basic commands:
  
   add           add the specified files on the next commit
   annotate      show changeset information by line for each file
   clone         make a copy of an existing repository
   commit        commit the specified files or all outstanding changes
   diff          diff repository (or selected files)
   export        dump the header and diffs for one or more changesets
   forget        forget the specified files on the next commit
   init          create a new repository in the given directory
   log           show revision history of entire repository or files
   merge         merge another revision into working directory
   pull          pull changes from the specified source
   push          push changes to the specified destination
   remove        remove the specified files on the next commit
   serve         start stand-alone webserver
   status        show changed files in the working directory
   summary       summarize working directory state
   update        update working directory (or switch revisions)
  
  (use 'hg help' for the full list of commands or 'hg -v' for details)

  $ hg -q
   add           add the specified files on the next commit
   annotate      show changeset information by line for each file
   clone         make a copy of an existing repository
   commit        commit the specified files or all outstanding changes
   diff          diff repository (or selected files)
   export        dump the header and diffs for one or more changesets
   forget        forget the specified files on the next commit
   init          create a new repository in the given directory
   log           show revision history of entire repository or files
   merge         merge another revision into working directory
   pull          pull changes from the specified source
   push          push changes to the specified destination
   remove        remove the specified files on the next commit
   serve         start stand-alone webserver
   status        show changed files in the working directory
   summary       summarize working directory state
   update        update working directory (or switch revisions)

  $ hg help
  Mercurial Distributed SCM
  
  list of commands:
  
   add           add the specified files on the next commit
   addremove     add all new files, delete all missing files
   annotate      show changeset information by line for each file
   archive       create an unversioned archive of a repository revision
   backout       reverse effect of earlier changeset
   bisect        subdivision search of changesets
   bookmarks     create a new bookmark or list existing bookmarks
   branch        set or show the current branch name
   branches      list repository named branches
   bundle        create a bundle file
   cat           output the current or given revision of files
   clone         make a copy of an existing repository
   commit        commit the specified files or all outstanding changes
   config        show combined config settings from all hgrc files
   copy          mark files as copied for the next commit
   diff          diff repository (or selected files)
   export        dump the header and diffs for one or more changesets
   files         list tracked files
   forget        forget the specified files on the next commit
   graft         copy changes from other branches onto the current branch
   grep          search revision history for a pattern in specified files
   heads         show branch heads
   help          show help for a given topic or a help overview
   identify      identify the working directory or specified revision
   import        import an ordered set of patches
   incoming      show new changesets found in source
   init          create a new repository in the given directory
   log           show revision history of entire repository or files
   manifest      output the current or given revision of the project manifest
   merge         merge another revision into working directory
   outgoing      show changesets not found in the destination
   paths         show aliases for remote repositories
   phase         set or show the current phase name
   pull          pull changes from the specified source
   push          push changes to the specified destination
   recover       roll back an interrupted transaction
   remove        remove the specified files on the next commit
   rename        rename files; equivalent of copy + remove
   resolve       redo merges or set/view the merge status of files
   revert        restore files to their checkout state
   root          print the root (top) of the current working directory
   serve         start stand-alone webserver
   status        show changed files in the working directory
   summary       summarize working directory state
   tag           add one or more tags for the current or given revision
   tags          list repository tags
   unbundle      apply one or more bundle files
   update        update working directory (or switch revisions)
   verify        verify the integrity of the repository
   version       output version and copyright information
  
  additional help topics:
  
   bundlespec    Bundle File Formats
   color         Colorizing Outputs
   config        Configuration Files
   dates         Date Formats
   diffs         Diff Formats
   environment   Environment Variables
   extensions    Using Additional Features
   filesets      Specifying File Sets
   glossary      Glossary
   hgignore      Syntax for Mercurial Ignore Files
   hgweb         Configuring hgweb
   internals     Technical implementation topics
   merge-tools   Merge Tools
   pager         Pager Support
   patterns      File Name Patterns
   phases        Working with Phases
   revisions     Specifying Revisions
   scripting     Using Mercurial from scripts and automation
   subrepos      Subrepositories
   templating    Template Usage
   urls          URL Paths
  
  (use 'hg help -v' to show built-in aliases and global options)

  $ hg -q help
   add           add the specified files on the next commit
   addremove     add all new files, delete all missing files
   annotate      show changeset information by line for each file
   archive       create an unversioned archive of a repository revision
   backout       reverse effect of earlier changeset
   bisect        subdivision search of changesets
   bookmarks     create a new bookmark or list existing bookmarks
   branch        set or show the current branch name
   branches      list repository named branches
   bundle        create a bundle file
   cat           output the current or given revision of files
   clone         make a copy of an existing repository
   commit        commit the specified files or all outstanding changes
   config        show combined config settings from all hgrc files
   copy          mark files as copied for the next commit
   diff          diff repository (or selected files)
   export        dump the header and diffs for one or more changesets
   files         list tracked files
   forget        forget the specified files on the next commit
   graft         copy changes from other branches onto the current branch
   grep          search revision history for a pattern in specified files
   heads         show branch heads
   help          show help for a given topic or a help overview
   identify      identify the working directory or specified revision
   import        import an ordered set of patches
   incoming      show new changesets found in source
   init          create a new repository in the given directory
   log           show revision history of entire repository or files
   manifest      output the current or given revision of the project manifest
   merge         merge another revision into working directory
   outgoing      show changesets not found in the destination
   paths         show aliases for remote repositories
   phase         set or show the current phase name
   pull          pull changes from the specified source
   push          push changes to the specified destination
   recover       roll back an interrupted transaction
   remove        remove the specified files on the next commit
   rename        rename files; equivalent of copy + remove
   resolve       redo merges or set/view the merge status of files
   revert        restore files to their checkout state
   root          print the root (top) of the current working directory
   serve         start stand-alone webserver
   status        show changed files in the working directory
   summary       summarize working directory state
   tag           add one or more tags for the current or given revision
   tags          list repository tags
   unbundle      apply one or more bundle files
   update        update working directory (or switch revisions)
   verify        verify the integrity of the repository
   version       output version and copyright information
  
  additional help topics:
  
   bundlespec    Bundle File Formats
   color         Colorizing Outputs
   config        Configuration Files
   dates         Date Formats
   diffs         Diff Formats
   environment   Environment Variables
   extensions    Using Additional Features
   filesets      Specifying File Sets
   glossary      Glossary
   hgignore      Syntax for Mercurial Ignore Files
   hgweb         Configuring hgweb
   internals     Technical implementation topics
   merge-tools   Merge Tools
   pager         Pager Support
   patterns      File Name Patterns
   phases        Working with Phases
   revisions     Specifying Revisions
   scripting     Using Mercurial from scripts and automation
   subrepos      Subrepositories
   templating    Template Usage
   urls          URL Paths

Test extension help:
  $ hg help extensions --config extensions.rebase= --config extensions.children=
  Using Additional Features
  """""""""""""""""""""""""
  
      Mercurial has the ability to add new features through the use of
      extensions. Extensions may add new commands, add options to existing
      commands, change the default behavior of commands, or implement hooks.
  
      To enable the "foo" extension, either shipped with Mercurial or in the
      Python search path, create an entry for it in your configuration file,
      like this:
  
        [extensions]
        foo =
  
      You may also specify the full path to an extension:
  
        [extensions]
        myfeature = ~/.hgext/myfeature.py
  
      See 'hg help config' for more information on configuration files.
  
      Extensions are not loaded by default for a variety of reasons: they can
      increase startup overhead; they may be meant for advanced usage only; they
      may provide potentially dangerous abilities (such as letting you destroy
      or modify history); they might not be ready for prime time; or they may
      alter some usual behaviors of stock Mercurial. It is thus up to the user
      to activate extensions as needed.
  
      To explicitly disable an extension enabled in a configuration file of
      broader scope, prepend its path with !:
  
        [extensions]
        # disabling extension bar residing in /path/to/extension/bar.py
        bar = !/path/to/extension/bar.py
        # ditto, but no path was supplied for extension baz
        baz = !
  
      enabled extensions:
  
       children      command to display child changesets (DEPRECATED)
       rebase        command to move sets of revisions to a different ancestor
  
      disabled extensions:
  
       acl           hooks for controlling repository access
       blackbox      log repository events to a blackbox for debugging
       bugzilla      hooks for integrating with the Bugzilla bug tracker
       censor        erase file content at a given revision
       churn         command to display statistics about repository history
       clonebundles  advertise pre-generated bundles to seed clones
       convert       import revisions from foreign VCS repositories into
                     Mercurial
       eol           automatically manage newlines in repository files
       extdiff       command to allow external programs to compare revisions
       factotum      http authentication with factotum
       gpg           commands to sign and verify changesets
       hgk           browse the repository in a graphical way
       highlight     syntax highlighting for hgweb (requires Pygments)
       histedit      interactive history editing
       keyword       expand keywords in tracked files
       largefiles    track large binary files
       mq            manage a stack of patches
       notify        hooks for sending email push notifications
       patchbomb     command to send changesets as (a series of) patch emails
       purge         command to delete untracked files from the working
                     directory
       relink        recreates hardlinks between repository clones
       schemes       extend schemes with shortcuts to repository swarms
       share         share a common history between several working directories
       shelve        save and restore changes to the working directory
       strip         strip changesets and their descendants from history
       transplant    command to transplant changesets from another branch
       win32mbcs     allow the use of MBCS paths with problematic encodings
       zeroconf      discover and advertise repositories on the local network

Verify that extension keywords appear in help templates

  $ hg help --config extensions.transplant= templating|grep transplant > /dev/null

Test short command list with verbose option

  $ hg -v help shortlist
  Mercurial Distributed SCM
  
  basic commands:
  
   add           add the specified files on the next commit
   annotate, blame
                 show changeset information by line for each file
   clone         make a copy of an existing repository
   commit, ci    commit the specified files or all outstanding changes
   diff          diff repository (or selected files)
   export        dump the header and diffs for one or more changesets
   forget        forget the specified files on the next commit
   init          create a new repository in the given directory
   log, history  show revision history of entire repository or files
   merge         merge another revision into working directory
   pull          pull changes from the specified source
   push          push changes to the specified destination
   remove, rm    remove the specified files on the next commit
   serve         start stand-alone webserver
   status, st    show changed files in the working directory
   summary, sum  summarize working directory state
   update, up, checkout, co
                 update working directory (or switch revisions)
  
  global options ([+] can be repeated):
  
   -R --repository REPO   repository root directory or name of overlay bundle
                          file
      --cwd DIR           change working directory
   -y --noninteractive    do not prompt, automatically pick the first choice for
                          all prompts
   -q --quiet             suppress output
   -v --verbose           enable additional output
      --color TYPE        when to colorize (boolean, always, auto, never, or
                          debug)
      --config CONFIG [+] set/override config option (use 'section.name=value')
      --debug             enable debugging output
      --debugger          start debugger
      --encoding ENCODE   set the charset encoding (default: ascii)
      --encodingmode MODE set the charset encoding mode (default: strict)
      --traceback         always print a traceback on exception
      --time              time how long the command takes
      --profile           print command execution profile
      --version           output version information and exit
   -h --help              display help and exit
      --hidden            consider hidden changesets
      --pager TYPE        when to paginate (boolean, always, auto, or never)
                          (default: auto)
  
  (use 'hg help' for the full list of commands)

  $ hg add -h
  hg add [OPTION]... [FILE]...
  
  add the specified files on the next commit
  
      Schedule files to be version controlled and added to the repository.
  
      The files will be added to the repository at the next commit. To undo an
      add before that, see 'hg forget'.
  
      If no names are given, add all files to the repository (except files
      matching ".hgignore").
  
      Returns 0 if all files are successfully added.
  
  options ([+] can be repeated):
  
   -I --include PATTERN [+] include names matching the given patterns
   -X --exclude PATTERN [+] exclude names matching the given patterns
   -S --subrepos            recurse into subrepositories
   -n --dry-run             do not perform actions, just print output
  
  (some details hidden, use --verbose to show complete help)

Verbose help for add

  $ hg add -hv
  hg add [OPTION]... [FILE]...
  
  add the specified files on the next commit
  
      Schedule files to be version controlled and added to the repository.
  
      The files will be added to the repository at the next commit. To undo an
      add before that, see 'hg forget'.
  
      If no names are given, add all files to the repository (except files
      matching ".hgignore").
  
      Examples:
  
        - New (unknown) files are added automatically by 'hg add':
  
            $ ls
            foo.c
            $ hg status
            ? foo.c
            $ hg add
            adding foo.c
            $ hg status
            A foo.c
  
        - Specific files to be added can be specified:
  
            $ ls
            bar.c  foo.c
            $ hg status
            ? bar.c
            ? foo.c
            $ hg add bar.c
            $ hg status
            A bar.c
            ? foo.c
  
      Returns 0 if all files are successfully added.
  
  options ([+] can be repeated):
  
   -I --include PATTERN [+] include names matching the given patterns
   -X --exclude PATTERN [+] exclude names matching the given patterns
   -S --subrepos            recurse into subrepositories
   -n --dry-run             do not perform actions, just print output
  
  global options ([+] can be repeated):
  
   -R --repository REPO   repository root directory or name of overlay bundle
                          file
      --cwd DIR           change working directory
   -y --noninteractive    do not prompt, automatically pick the first choice for
                          all prompts
   -q --quiet             suppress output
   -v --verbose           enable additional output
      --color TYPE        when to colorize (boolean, always, auto, never, or
                          debug)
      --config CONFIG [+] set/override config option (use 'section.name=value')
      --debug             enable debugging output
      --debugger          start debugger
      --encoding ENCODE   set the charset encoding (default: ascii)
      --encodingmode MODE set the charset encoding mode (default: strict)
      --traceback         always print a traceback on exception
      --time              time how long the command takes
      --profile           print command execution profile
      --version           output version information and exit
   -h --help              display help and exit
      --hidden            consider hidden changesets
      --pager TYPE        when to paginate (boolean, always, auto, or never)
                          (default: auto)

Test the textwidth config option

  $ hg root -h  --config ui.textwidth=50
  hg root
  
  print the root (top) of the current working
  directory
  
      Print the root directory of the current
      repository.
  
      Returns 0 on success.
  
  (some details hidden, use --verbose to show
  complete help)

Test help option with version option

  $ hg add -h --version
  Mercurial Distributed SCM (version *) (glob)
  (see https://mercurial-scm.org for more information)
  
  Copyright (C) 2005-* Matt Mackall and others (glob)
  This is free software; see the source for copying conditions. There is NO
  warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

  $ hg add --skjdfks
  hg add: option --skjdfks not recognized
  hg add [OPTION]... [FILE]...
  
  add the specified files on the next commit
  
  options ([+] can be repeated):
  
   -I --include PATTERN [+] include names matching the given patterns
   -X --exclude PATTERN [+] exclude names matching the given patterns
   -S --subrepos            recurse into subrepositories
   -n --dry-run             do not perform actions, just print output
  
  (use 'hg add -h' to show more help)
  [255]

Test ambiguous command help

  $ hg help ad
  list of commands:
  
   add           add the specified files on the next commit
   addremove     add all new files, delete all missing files
  
  (use 'hg help -v ad' to show built-in aliases and global options)

Test command without options

  $ hg help verify
  hg verify
  
  verify the integrity of the repository
  
      Verify the integrity of the current repository.
  
      This will perform an extensive check of the repository's integrity,
      validating the hashes and checksums of each entry in the changelog,
      manifest, and tracked files, as well as the integrity of their crosslinks
      and indices.
  
      Please see https://mercurial-scm.org/wiki/RepositoryCorruption for more
      information about recovery from corruption of the repository.
  
      Returns 0 on success, 1 if errors are encountered.
  
  (some details hidden, use --verbose to show complete help)

  $ hg help diff
  hg diff [OPTION]... ([-c REV] | [-r REV1 [-r REV2]]) [FILE]...
  
  diff repository (or selected files)
  
      Show differences between revisions for the specified files.
  
      Differences between files are shown using the unified diff format.
  
      Note:
         'hg diff' may generate unexpected results for merges, as it will
         default to comparing against the working directory's first parent
         changeset if no revisions are specified.
  
      When two revision arguments are given, then changes are shown between
      those revisions. If only one revision is specified then that revision is
      compared to the working directory, and, when no revisions are specified,
      the working directory files are compared to its first parent.
  
      Alternatively you can specify -c/--change with a revision to see the
      changes in that changeset relative to its first parent.
  
      Without the -a/--text option, diff will avoid generating diffs of files it
      detects as binary. With -a, diff will generate a diff anyway, probably
      with undesirable results.
  
      Use the -g/--git option to generate diffs in the git extended diff format.
      For more information, read 'hg help diffs'.
  
      Returns 0 on success.
  
  options ([+] can be repeated):
  
   -r --rev REV [+]         revision
   -c --change REV          change made by revision
   -a --text                treat all files as text
   -g --git                 use git extended diff format
      --binary              generate binary diffs in git mode (default)
      --nodates             omit dates from diff headers
      --noprefix            omit a/ and b/ prefixes from filenames
   -p --show-function       show which function each change is in
      --reverse             produce a diff that undoes the changes
   -w --ignore-all-space    ignore white space when comparing lines
   -b --ignore-space-change ignore changes in the amount of white space
   -B --ignore-blank-lines  ignore changes whose lines are all blank
   -U --unified NUM         number of lines of context to show
      --stat                output diffstat-style summary of changes
      --root DIR            produce diffs relative to subdirectory
   -I --include PATTERN [+] include names matching the given patterns
   -X --exclude PATTERN [+] exclude names matching the given patterns
   -S --subrepos            recurse into subrepositories
  
  (some details hidden, use --verbose to show complete help)

  $ hg help status
  hg status [OPTION]... [FILE]...
  
  aliases: st
  
  show changed files in the working directory
  
      Show status of files in the repository. If names are given, only files
      that match are shown. Files that are clean or ignored or the source of a
      copy/move operation, are not listed unless -c/--clean, -i/--ignored,
      -C/--copies or -A/--all are given. Unless options described with "show
      only ..." are given, the options -mardu are used.
  
      Option -q/--quiet hides untracked (unknown and ignored) files unless
      explicitly requested with -u/--unknown or -i/--ignored.
  
      Note:
         'hg status' may appear to disagree with diff if permissions have
         changed or a merge has occurred. The standard diff format does not
         report permission changes and diff only reports changes relative to one
         merge parent.
  
      If one revision is given, it is used as the base revision. If two
      revisions are given, the differences between them are shown. The --change
      option can also be used as a shortcut to list the changed files of a
      revision from its first parent.
  
      The codes used to show the status of files are:
  
        M = modified
        A = added
        R = removed
        C = clean
        ! = missing (deleted by non-hg command, but still tracked)
        ? = not tracked
        I = ignored
          = origin of the previous file (with --copies)
  
      Returns 0 on success.
  
  options ([+] can be repeated):
  
   -A --all                 show status of all files
   -m --modified            show only modified files
   -a --added               show only added files
   -r --removed             show only removed files
   -d --deleted             show only deleted (but tracked) files
   -c --clean               show only files without changes
   -u --unknown             show only unknown (not tracked) files
   -i --ignored             show only ignored files
   -n --no-status           hide status prefix
   -C --copies              show source of copied files
   -0 --print0              end filenames with NUL, for use with xargs
      --rev REV [+]         show difference from revision
      --change REV          list the changed files of a revision
   -I --include PATTERN [+] include names matching the given patterns
   -X --exclude PATTERN [+] exclude names matching the given patterns
   -S --subrepos            recurse into subrepositories
  
  (some details hidden, use --verbose to show complete help)

  $ hg -q help status
  hg status [OPTION]... [FILE]...
  
  show changed files in the working directory

  $ hg help foo
  abort: no such help topic: foo
  (try 'hg help --keyword foo')
  [255]

  $ hg skjdfks
  hg: unknown command 'skjdfks'
  Mercurial Distributed SCM
  
  basic commands:
  
   add           add the specified files on the next commit
   annotate      show changeset information by line for each file
   clone         make a copy of an existing repository
   commit        commit the specified files or all outstanding changes
   diff          diff repository (or selected files)
   export        dump the header and diffs for one or more changesets
   forget        forget the specified files on the next commit
   init          create a new repository in the given directory
   log           show revision history of entire repository or files
   merge         merge another revision into working directory
   pull          pull changes from the specified source
   push          push changes to the specified destination
   remove        remove the specified files on the next commit
   serve         start stand-alone webserver
   status        show changed files in the working directory
   summary       summarize working directory state
   update        update working directory (or switch revisions)
  
  (use 'hg help' for the full list of commands or 'hg -v' for details)
  [255]

Typoed command gives suggestion
  $ hg puls
  hg: unknown command 'puls'
  (did you mean one of pull, push?)
  [255]

Not enabled extension gets suggested

  $ hg rebase
  hg: unknown command 'rebase'
  'rebase' is provided by the following extension:
  
      rebase        command to move sets of revisions to a different ancestor
  
  (use 'hg help extensions' for information on enabling extensions)
  [255]

Disabled extension gets suggested
  $ hg --config extensions.rebase=! rebase
  hg: unknown command 'rebase'
  'rebase' is provided by the following extension:
  
      rebase        command to move sets of revisions to a different ancestor
  
  (use 'hg help extensions' for information on enabling extensions)
  [255]

Make sure that we don't run afoul of the help system thinking that
this is a section and erroring out weirdly.

  $ hg .log
  hg: unknown command '.log'
  (did you mean log?)
  [255]

  $ hg log.
  hg: unknown command 'log.'
  (did you mean log?)
  [255]
  $ hg pu.lh
  hg: unknown command 'pu.lh'
  (did you mean one of pull, push?)
  [255]

  $ cat > helpext.py <<EOF
  > import os
  > from mercurial import commands, registrar
  > 
  > cmdtable = {}
  > command = registrar.command(cmdtable)
  > 
  > @command(b'nohelp',
  >     [(b'', b'longdesc', 3, b'x'*90),
  >     (b'n', b'', None, b'normal desc'),
  >     (b'', b'newline', b'', b'line1\nline2')],
  >     b'hg nohelp',
  >     norepo=True)
  > @command(b'debugoptADV', [(b'', b'aopt', None, b'option is (ADVANCED)')])
  > @command(b'debugoptDEP', [(b'', b'dopt', None, b'option is (DEPRECATED)')])
  > @command(b'debugoptEXP', [(b'', b'eopt', None, b'option is (EXPERIMENTAL)')])
  > def nohelp(ui, *args, **kwargs):
  >     pass
  > 
  > def uisetup(ui):
  >     ui.setconfig(b'alias', b'shellalias', b'!echo hi', b'helpext')
  >     ui.setconfig(b'alias', b'hgalias', b'summary', b'helpext')
  > 
  > EOF
  $ echo '[extensions]' >> $HGRCPATH
  $ echo "helpext = `pwd`/helpext.py" >> $HGRCPATH

Test for aliases

  $ hg help hgalias
  hg hgalias [--remote]
  
  alias for: hg summary
  
  summarize working directory state
  
      This generates a brief summary of the working directory state, including
      parents, branch, commit status, phase and available updates.
  
      With the --remote option, this will check the default paths for incoming
      and outgoing changes. This can be time-consuming.
  
      Returns 0 on success.
  
  defined by: helpext
  
  options:
  
    --remote check for push and pull
  
  (some details hidden, use --verbose to show complete help)

  $ hg help shellalias
  hg shellalias
  
  shell alias for:
  
    echo hi
  
  defined by: helpext
  
  (some details hidden, use --verbose to show complete help)

Test command with no help text

  $ hg help nohelp
  hg nohelp
  
  (no help text available)
  
  options:
  
      --longdesc VALUE xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                       xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (default: 3)
   -n --               normal desc
      --newline VALUE  line1 line2
  
  (some details hidden, use --verbose to show complete help)

  $ hg help -k nohelp
  Commands:
  
   nohelp hg nohelp
  
  Extension Commands:
  
   nohelp (no help text available)

Test that default list of commands omits extension commands

  $ hg help
  Mercurial Distributed SCM
  
  list of commands:
  
   add           add the specified files on the next commit
   addremove     add all new files, delete all missing files
   annotate      show changeset information by line for each file
   archive       create an unversioned archive of a repository revision
   backout       reverse effect of earlier changeset
   bisect        subdivision search of changesets
   bookmarks     create a new bookmark or list existing bookmarks
   branch        set or show the current branch name
   branches      list repository named branches
   bundle        create a bundle file
   cat           output the current or given revision of files
   clone         make a copy of an existing repository
   commit        commit the specified files or all outstanding changes
   config        show combined config settings from all hgrc files
   copy          mark files as copied for the next commit
   diff          diff repository (or selected files)
   export        dump the header and diffs for one or more changesets
   files         list tracked files
   forget        forget the specified files on the next commit
   graft         copy changes from other branches onto the current branch
   grep          search revision history for a pattern in specified files
   heads         show branch heads
   help          show help for a given topic or a help overview
   identify      identify the working directory or specified revision
   import        import an ordered set of patches
   incoming      show new changesets found in source
   init          create a new repository in the given directory
   log           show revision history of entire repository or files
   manifest      output the current or given revision of the project manifest
   merge         merge another revision into working directory
   outgoing      show changesets not found in the destination
   paths         show aliases for remote repositories
   phase         set or show the current phase name
   pull          pull changes from the specified source
   push          push changes to the specified destination
   recover       roll back an interrupted transaction
   remove        remove the specified files on the next commit
   rename        rename files; equivalent of copy + remove
   resolve       redo merges or set/view the merge status of files
   revert        restore files to their checkout state
   root          print the root (top) of the current working directory
   serve         start stand-alone webserver
   status        show changed files in the working directory
   summary       summarize working directory state
   tag           add one or more tags for the current or given revision
   tags          list repository tags
   unbundle      apply one or more bundle files
   update        update working directory (or switch revisions)
   verify        verify the integrity of the repository
   version       output version and copyright information
  
  enabled extensions:
  
   helpext       (no help text available)
  
  additional help topics:
  
   bundlespec    Bundle File Formats
   color         Colorizing Outputs
   config        Configuration Files
   dates         Date Formats
   diffs         Diff Formats
   environment   Environment Variables
   extensions    Using Additional Features
   filesets      Specifying File Sets
   glossary      Glossary
   hgignore      Syntax for Mercurial Ignore Files
   hgweb         Configuring hgweb
   internals     Technical implementation topics
   merge-tools   Merge Tools
   pager         Pager Support
   patterns      File Name Patterns
   phases        Working with Phases
   revisions     Specifying Revisions
   scripting     Using Mercurial from scripts and automation
   subrepos      Subrepositories
   templating    Template Usage
   urls          URL Paths
  
  (use 'hg help -v' to show built-in aliases and global options)


Test list of internal help commands

  $ hg help debug
  debug commands (internal and unsupported):
  
   debugancestor
                 find the ancestor revision of two revisions in a given index
   debugapplystreamclonebundle
                 apply a stream clone bundle file
   debugbuilddag
                 builds a repo with a given DAG from scratch in the current
                 empty repo
   debugbundle   lists the contents of a bundle
   debugcheckstate
                 validate the correctness of the current dirstate
   debugcolor    show available color, effects or style
   debugcommands
                 list all available commands and options
   debugcomplete
                 returns the completion list associated with the given command
   debugcreatestreamclonebundle
                 create a stream clone bundle file
   debugdag      format the changelog or an index DAG as a concise textual
                 description
   debugdata     dump the contents of a data file revision
   debugdate     parse and display a date
   debugdeltachain
                 dump information about delta chains in a revlog
   debugdirstate
                 show the contents of the current dirstate
   debugdiscovery
                 runs the changeset discovery protocol in isolation
   debugextensions
                 show information about active extensions
   debugfileset  parse and apply a fileset specification
   debugfsinfo   show information detected about current filesystem
   debuggetbundle
                 retrieves a bundle from a repo
   debugignore   display the combined ignore pattern and information about
                 ignored files
   debugindex    dump the contents of an index file
   debugindexdot
                 dump an index DAG as a graphviz dot file
   debuginstall  test Mercurial installation
   debugknown    test whether node ids are known to a repo
   debuglocks    show or modify state of locks
   debugmergestate
                 print merge state
   debugnamecomplete
                 complete "names" - tags, open branch names, bookmark names
   debugobsolete
                 create arbitrary obsolete marker
   debugoptADV   (no help text available)
   debugoptDEP   (no help text available)
   debugoptEXP   (no help text available)
   debugpathcomplete
                 complete part or all of a tracked path
   debugpickmergetool
                 examine which merge tool is chosen for specified file
   debugpushkey  access the pushkey key/value protocol
   debugpvec     (no help text available)
   debugrebuilddirstate
                 rebuild the dirstate as it would look like for the given
                 revision
   debugrebuildfncache
                 rebuild the fncache file
   debugrename   dump rename information
   debugrevlog   show data and statistics about a revlog
   debugrevspec  parse and apply a revision specification
   debugsetparents
                 manually set the parents of the current working directory
   debugsub      (no help text available)
   debugsuccessorssets
                 show set of successors for revision
   debugtemplate
                 parse and apply a template
   debugupdatecaches
                 warm all known caches in the repository
   debugupgraderepo
                 upgrade a repository to use different features
   debugwalk     show how files match on given patterns
   debugwireargs
                 (no help text available)
  
  (use 'hg help -v debug' to show built-in aliases and global options)

internals topic renders index of available sub-topics

  $ hg help internals
  Technical implementation topics
  """""""""""""""""""""""""""""""
  
      To access a subtopic, use "hg help internals.{subtopic-name}"
  
       bundles       Bundles
       censor        Censor
       changegroups  Changegroups
       requirements  Repository Requirements
       revlogs       Revision Logs
       wireprotocol  Wire Protocol

sub-topics can be accessed

  $ hg help internals.changegroups
  Changegroups
  """"""""""""
  
      Changegroups are representations of repository revlog data, specifically
      the changelog data, root/flat manifest data, treemanifest data, and
      filelogs.
  
      There are 3 versions of changegroups: "1", "2", and "3". From a high-
      level, versions "1" and "2" are almost exactly the same, with the only
      difference being an additional item in the *delta header*.  Version "3"
      adds support for revlog flags in the *delta header* and optionally
      exchanging treemanifests (enabled by setting an option on the
      "changegroup" part in the bundle2).
  
      Changegroups when not exchanging treemanifests consist of 3 logical
      segments:
  
        +---------------------------------+
        |           |          |          |
        | changeset | manifest | filelogs |
        |           |          |          |
        |           |          |          |
        +---------------------------------+
  
      When exchanging treemanifests, there are 4 logical segments:
  
        +-------------------------------------------------+
        |           |          |               |          |
        | changeset |   root   | treemanifests | filelogs |
        |           | manifest |               |          |
        |           |          |               |          |
        +-------------------------------------------------+
  
      The principle building block of each segment is a *chunk*. A *chunk* is a
      framed piece of data:
  
        +---------------------------------------+
        |           |                           |
        |  length   |           data            |
        | (4 bytes) |   (<length - 4> bytes)    |
        |           |                           |
        +---------------------------------------+
  
      All integers are big-endian signed integers. Each chunk starts with a
      32-bit integer indicating the length of the entire chunk (including the
      length field itself).
  
      There is a special case chunk that has a value of 0 for the length
      ("0x00000000"). We call this an *empty chunk*.
  
      Delta Groups
      ============
  
      A *delta group* expresses the content of a revlog as a series of deltas,
      or patches against previous revisions.
  
      Delta groups consist of 0 or more *chunks* followed by the *empty chunk*
      to signal the end of the delta group:
  
        +------------------------------------------------------------------------+
        |                |             |               |             |           |
        | chunk0 length  | chunk0 data | chunk1 length | chunk1 data |    0x0    |
        |   (4 bytes)    |  (various)  |   (4 bytes)   |  (various)  | (4 bytes) |
        |                |             |               |             |           |
        +------------------------------------------------------------------------+
  
      Each *chunk*'s data consists of the following:
  
        +---------------------------------------+
        |                        |              |
        |     delta header       |  delta data  |
        |  (various by version)  |  (various)   |
        |                        |              |
        +---------------------------------------+
  
      The *delta data* is a series of *delta*s that describe a diff from an
      existing entry (either that the recipient already has, or previously
      specified in the bundle/changegroup).
  
      The *delta header* is different between versions "1", "2", and "3" of the
      changegroup format.
  
      Version 1 (headerlen=80):
  
        +------------------------------------------------------+
        |            |             |             |             |
        |    node    |   p1 node   |   p2 node   |  link node  |
        | (20 bytes) |  (20 bytes) |  (20 bytes) |  (20 bytes) |
        |            |             |             |             |
        +------------------------------------------------------+
  
      Version 2 (headerlen=100):
  
        +------------------------------------------------------------------+
        |            |             |             |            |            |
        |    node    |   p1 node   |   p2 node   | base node  | link node  |
        | (20 bytes) |  (20 bytes) |  (20 bytes) | (20 bytes) | (20 bytes) |
        |            |             |             |            |            |
        +------------------------------------------------------------------+
  
      Version 3 (headerlen=102):
  
        +------------------------------------------------------------------------------+
        |            |             |             |            |            |           |
        |    node    |   p1 node   |   p2 node   | base node  | link node  |   flags   |
        | (20 bytes) |  (20 bytes) |  (20 bytes) | (20 bytes) | (20 bytes) | (2 bytes) |
        |            |             |             |            |            |           |
        +------------------------------------------------------------------------------+
  
      The *delta data* consists of "chunklen - 4 - headerlen" bytes, which
      contain a series of *delta*s, densely packed (no separators). These deltas
      describe a diff from an existing entry (either that the recipient already
      has, or previously specified in the bundle/changegroup). The format is
      described more fully in "hg help internals.bdiff", but briefly:
  
        +---------------------------------------------------------------+
        |              |            |            |                      |
        | start offset | end offset | new length |        content       |
        |  (4 bytes)   |  (4 bytes) |  (4 bytes) | (<new length> bytes) |
        |              |            |            |                      |
        +---------------------------------------------------------------+
  
      Please note that the length field in the delta data does *not* include
      itself.
  
      In version 1, the delta is always applied against the previous node from
      the changegroup or the first parent if this is the first entry in the
      changegroup.
  
      In version 2 and up, the delta base node is encoded in the entry in the
      changegroup. This allows the delta to be expressed against any parent,
      which can result in smaller deltas and more efficient encoding of data.
  
      Changeset Segment
      =================
  
      The *changeset segment* consists of a single *delta group* holding
      changelog data. The *empty chunk* at the end of the *delta group* denotes
      the boundary to the *manifest segment*.
  
      Manifest Segment
      ================
  
      The *manifest segment* consists of a single *delta group* holding manifest
      data. If treemanifests are in use, it contains only the manifest for the
      root directory of the repository. Otherwise, it contains the entire
      manifest data. The *empty chunk* at the end of the *delta group* denotes
      the boundary to the next segment (either the *treemanifests segment* or
      the *filelogs segment*, depending on version and the request options).
  
      Treemanifests Segment
      ---------------------
  
      The *treemanifests segment* only exists in changegroup version "3", and
      only if the 'treemanifest' param is part of the bundle2 changegroup part
      (it is not possible to use changegroup version 3 outside of bundle2).
      Aside from the filenames in the *treemanifests segment* containing a
      trailing "/" character, it behaves identically to the *filelogs segment*
      (see below). The final sub-segment is followed by an *empty chunk*
      (logically, a sub-segment with filename size 0). This denotes the boundary
      to the *filelogs segment*.
  
      Filelogs Segment
      ================
  
      The *filelogs segment* consists of multiple sub-segments, each
      corresponding to an individual file whose data is being described:
  
        +--------------------------------------------------+
        |          |          |          |     |           |
        | filelog0 | filelog1 | filelog2 | ... |    0x0    |
        |          |          |          |     | (4 bytes) |
        |          |          |          |     |           |
        +--------------------------------------------------+
  
      The final filelog sub-segment is followed by an *empty chunk* (logically,
      a sub-segment with filename size 0). This denotes the end of the segment
      and of the overall changegroup.
  
      Each filelog sub-segment consists of the following:
  
        +------------------------------------------------------+
        |                 |                      |             |
        | filename length |       filename       | delta group |
        |    (4 bytes)    | (<length - 4> bytes) |  (various)  |
        |                 |                      |             |
        +------------------------------------------------------+
  
      That is, a *chunk* consisting of the filename (not terminated or padded)
      followed by N chunks constituting the *delta group* for this file. The
      *empty chunk* at the end of each *delta group* denotes the boundary to the
      next filelog sub-segment.

Test list of commands with command with no help text

  $ hg help helpext
  helpext extension - no help text available
  
  list of commands:
  
   nohelp        (no help text available)
  
  (use 'hg help -v helpext' to show built-in aliases and global options)


test advanced, deprecated and experimental options are hidden in command help
  $ hg help debugoptADV
  hg debugoptADV
  
  (no help text available)
  
  options:
  
  (some details hidden, use --verbose to show complete help)
  $ hg help debugoptDEP
  hg debugoptDEP
  
  (no help text available)
  
  options:
  
  (some details hidden, use --verbose to show complete help)

  $ hg help debugoptEXP
  hg debugoptEXP
  
  (no help text available)
  
  options:
  
  (some details hidden, use --verbose to show complete help)

test advanced, deprecated and experimental options are shown with -v
  $ hg help -v debugoptADV | grep aopt
    --aopt option is (ADVANCED)
  $ hg help -v debugoptDEP | grep dopt
    --dopt option is (DEPRECATED)
  $ hg help -v debugoptEXP | grep eopt
    --eopt option is (EXPERIMENTAL)

#if gettext
test deprecated option is hidden with translation with untranslated description
(use many globy for not failing on changed transaction)
  $ LANGUAGE=sv hg help debugoptDEP
  hg debugoptDEP
  
  (*) (glob)
  
  options:
  
  (some details hidden, use --verbose to show complete help)
#endif

Test commands that collide with topics (issue4240)

  $ hg config -hq
  hg config [-u] [NAME]...
  
  show combined config settings from all hgrc files
  $ hg showconfig -hq
  hg config [-u] [NAME]...
  
  show combined config settings from all hgrc files

Test a help topic

  $ hg help dates
  Date Formats
  """"""""""""
  
      Some commands allow the user to specify a date, e.g.:
  
      - backout, commit, import, tag: Specify the commit date.
      - log, revert, update: Select revision(s) by date.
  
      Many date formats are valid. Here are some examples:
  
      - "Wed Dec 6 13:18:29 2006" (local timezone assumed)
      - "Dec 6 13:18 -0600" (year assumed, time offset provided)
      - "Dec 6 13:18 UTC" (UTC and GMT are aliases for +0000)
      - "Dec 6" (midnight)
      - "13:18" (today assumed)
      - "3:39" (3:39AM assumed)
      - "3:39pm" (15:39)
      - "2006-12-06 13:18:29" (ISO 8601 format)
      - "2006-12-6 13:18"
      - "2006-12-6"
      - "12-6"
      - "12/6"
      - "12/6/6" (Dec 6 2006)
      - "today" (midnight)
      - "yesterday" (midnight)
      - "now" - right now
  
      Lastly, there is Mercurial's internal format:
  
      - "1165411109 0" (Wed Dec 6 13:18:29 2006 UTC)
  
      This is the internal representation format for dates. The first number is
      the number of seconds since the epoch (1970-01-01 00:00 UTC). The second
      is the offset of the local timezone, in seconds west of UTC (negative if
      the timezone is east of UTC).
  
      The log command also accepts date ranges:
  
      - "<DATE" - at or before a given date/time
      - ">DATE" - on or after a given date/time
      - "DATE to DATE" - a date range, inclusive
      - "-DAYS" - within a given number of days of today

Test repeated config section name

  $ hg help config.host
      "http_proxy.host"
          Host name and (optional) port of the proxy server, for example
          "myproxy:8000".
  
      "smtp.host"
          Host name of mail server, e.g. "mail.example.com".
  
Unrelated trailing paragraphs shouldn't be included

  $ hg help config.extramsg | grep '^$'
  

Test capitalized section name

  $ hg help scripting.HGPLAIN > /dev/null

Help subsection:

  $ hg help config.charsets |grep "Email example:" > /dev/null
  [1]

Show nested definitions
("profiling.type"[break]"ls"[break]"stat"[break])

  $ hg help config.type | egrep '^$'|wc -l
  \s*3 (re)

Separate sections from subsections

  $ hg help config.format | egrep '^    ("|-)|^\s*$' | uniq
      "format"
      --------
  
      "usegeneraldelta"
  
      "dotencode"
  
      "usefncache"
  
      "usestore"
  
      "profiling"
      -----------
  
      "format"
  
      "progress"
      ----------
  
      "format"
  

Last item in help config.*:

  $ hg help config.`hg help config|grep '^    "'| \
  >       tail -1|sed 's![ "]*!!g'`| \
  >   grep 'hg help -c config' > /dev/null
  [1]

note to use help -c for general hg help config:

  $ hg help config |grep 'hg help -c config' > /dev/null

Test templating help

  $ hg help templating | egrep '(desc|diffstat|firstline|nonempty)  '
      desc          String. The text of the changeset description.
      diffstat      String. Statistics of changes with the following format:
      firstline     Any text. Returns the first line of text.
      nonempty      Any text. Returns '(none)' if the string is empty.

Test deprecated items

  $ hg help -v templating | grep currentbookmark
      currentbookmark
  $ hg help templating | (grep currentbookmark || true)

Test help hooks

  $ cat > helphook1.py <<EOF
  > from mercurial import help
  > 
  > def rewrite(ui, topic, doc):
  >     return doc + '\nhelphook1\n'
  > 
  > def extsetup(ui):
  >     help.addtopichook('revisions', rewrite)
  > EOF
  $ cat > helphook2.py <<EOF
  > from mercurial import help
  > 
  > def rewrite(ui, topic, doc):
  >     return doc + '\nhelphook2\n'
  > 
  > def extsetup(ui):
  >     help.addtopichook('revisions', rewrite)
  > EOF
  $ echo '[extensions]' >> $HGRCPATH
  $ echo "helphook1 = `pwd`/helphook1.py" >> $HGRCPATH
  $ echo "helphook2 = `pwd`/helphook2.py" >> $HGRCPATH
  $ hg help revsets | grep helphook
      helphook1
      helphook2

help -c should only show debug --debug

  $ hg help -c --debug|egrep debug|wc -l|egrep '^\s*0\s*$'
  [1]

help -c should only show deprecated for -v

  $ hg help -c -v|egrep DEPRECATED|wc -l|egrep '^\s*0\s*$'
  [1]

Test -s / --system

  $ hg help config.files -s windows |grep 'etc/mercurial' | \
  > wc -l | sed -e 's/ //g'
  0
  $ hg help config.files --system unix | grep 'USER' | \
  > wc -l | sed -e 's/ //g'
  0

Test -e / -c / -k combinations

  $ hg help -c|egrep '^[A-Z].*:|^ debug'
  Commands:
  $ hg help -e|egrep '^[A-Z].*:|^ debug'
  Extensions:
  $ hg help -k|egrep '^[A-Z].*:|^ debug'
  Topics:
  Commands:
  Extensions:
  Extension Commands:
  $ hg help -c schemes
  abort: no such help topic: schemes
  (try 'hg help --keyword schemes')
  [255]
  $ hg help -e schemes |head -1
  schemes extension - extend schemes with shortcuts to repository swarms
  $ hg help -c -k dates |egrep '^(Topics|Extensions|Commands):'
  Commands:
  $ hg help -e -k a |egrep '^(Topics|Extensions|Commands):'
  Extensions:
  $ hg help -e -c -k date |egrep '^(Topics|Extensions|Commands):'
  Extensions:
  Commands:
  $ hg help -c commit > /dev/null
  $ hg help -e -c commit > /dev/null
  $ hg help -e commit > /dev/null
  abort: no such help topic: commit
  (try 'hg help --keyword commit')
  [255]

Test keyword search help

  $ cat > prefixedname.py <<EOF
  > '''matched against word "clone"
  > '''
  > EOF
  $ echo '[extensions]' >> $HGRCPATH
  $ echo "dot.dot.prefixedname = `pwd`/prefixedname.py" >> $HGRCPATH
  $ hg help -k clone
  Topics:
  
   config     Configuration Files
   extensions Using Additional Features
   glossary   Glossary
   phases     Working with Phases
   subrepos   Subrepositories
   urls       URL Paths
  
  Commands:
  
   bookmarks create a new bookmark or list existing bookmarks
   clone     make a copy of an existing repository
   paths     show aliases for remote repositories
   update    update working directory (or switch revisions)
  
  Extensions:
  
   clonebundles advertise pre-generated bundles to seed clones
   prefixedname matched against word "clone"
   relink       recreates hardlinks between repository clones
  
  Extension Commands:
  
   qclone clone main and patch repository at same time

Test unfound topic

  $ hg help nonexistingtopicthatwillneverexisteverever
  abort: no such help topic: nonexistingtopicthatwillneverexisteverever
  (try 'hg help --keyword nonexistingtopicthatwillneverexisteverever')
  [255]

Test unfound keyword

  $ hg help --keyword nonexistingwordthatwillneverexisteverever
  abort: no matches
  (try 'hg help' for a list of topics)
  [255]

Test omit indicating for help

  $ cat > addverboseitems.py <<EOF
  > '''extension to test omit indicating.
  > 
  > This paragraph is never omitted (for extension)
  > 
  > .. container:: verbose
  > 
  >   This paragraph is omitted,
  >   if :hg:\`help\` is invoked without \`\`-v\`\` (for extension)
  > 
  > This paragraph is never omitted, too (for extension)
  > '''
  > 
  > from mercurial import help, commands
  > testtopic = """This paragraph is never omitted (for topic).
  > 
  > .. container:: verbose
  > 
  >   This paragraph is omitted,
  >   if :hg:\`help\` is invoked without \`\`-v\`\` (for topic)
  > 
  > This paragraph is never omitted, too (for topic)
  > """
  > def extsetup(ui):
  >     help.helptable.append((["topic-containing-verbose"],
  >                            "This is the topic to test omit indicating.",
  >                            lambda ui: testtopic))
  > EOF
  $ echo '[extensions]' >> $HGRCPATH
  $ echo "addverboseitems = `pwd`/addverboseitems.py" >> $HGRCPATH
  $ hg help addverboseitems
  addverboseitems extension - extension to test omit indicating.
  
  This paragraph is never omitted (for extension)
  
  This paragraph is never omitted, too (for extension)
  
  (some details hidden, use --verbose to show complete help)
  
  no commands defined
  $ hg help -v addverboseitems
  addverboseitems extension - extension to test omit indicating.
  
  This paragraph is never omitted (for extension)
  
  This paragraph is omitted, if 'hg help' is invoked without "-v" (for
  extension)
  
  This paragraph is never omitted, too (for extension)
  
  no commands defined
  $ hg help topic-containing-verbose
  This is the topic to test omit indicating.
  """"""""""""""""""""""""""""""""""""""""""
  
      This paragraph is never omitted (for topic).
  
      This paragraph is never omitted, too (for topic)
  
  (some details hidden, use --verbose to show complete help)
  $ hg help -v topic-containing-verbose
  This is the topic to test omit indicating.
  """"""""""""""""""""""""""""""""""""""""""
  
      This paragraph is never omitted (for topic).
  
      This paragraph is omitted, if 'hg help' is invoked without "-v" (for
      topic)
  
      This paragraph is never omitted, too (for topic)

Test section lookup

  $ hg help revset.merge
      "merge()"
        Changeset is a merge changeset.
  
  $ hg help glossary.dag
      DAG
          The repository of changesets of a distributed version control system
          (DVCS) can be described as a directed acyclic graph (DAG), consisting
          of nodes and edges, where nodes correspond to changesets and edges
          imply a parent -> child relation. This graph can be visualized by
          graphical tools such as 'hg log --graph'. In Mercurial, the DAG is
          limited by the requirement for children to have at most two parents.
  

  $ hg help hgrc.paths
      "paths"
      -------
  
      Assigns symbolic names and behavior to repositories.
  
      Options are symbolic names defining the URL or directory that is the
      location of the repository. Example:
  
        [paths]
        my_server = https://example.com/my_repo
        local_path = /home/me/repo
  
      These symbolic names can be used from the command line. To pull from
      "my_server": 'hg pull my_server'. To push to "local_path": 'hg push
      local_path'.
  
      Options containing colons (":") denote sub-options that can influence
      behavior for that specific path. Example:
  
        [paths]
        my_server = https://example.com/my_path
        my_server:pushurl = ssh://example.com/my_path
  
      The following sub-options can be defined:
  
      "pushurl"
         The URL to use for push operations. If not defined, the location
         defined by the path's main entry is used.
  
      "pushrev"
         A revset defining which revisions to push by default.
  
         When 'hg push' is executed without a "-r" argument, the revset defined
         by this sub-option is evaluated to determine what to push.
  
         For example, a value of "." will push the working directory's revision
         by default.
  
         Revsets specifying bookmarks will not result in the bookmark being
         pushed.
  
      The following special named paths exist:
  
      "default"
         The URL or directory to use when no source or remote is specified.
  
         'hg clone' will automatically define this path to the location the
         repository was cloned from.
  
      "default-push"
         (deprecated) The URL or directory for the default 'hg push' location.
         "default:pushurl" should be used instead.
  
  $ hg help glossary.mcguffin
  abort: help section not found: glossary.mcguffin
  [255]

  $ hg help glossary.mc.guffin
  abort: help section not found: glossary.mc.guffin
  [255]

  $ hg help template.files
      files         List of strings. All files modified, added, or removed by
                    this changeset.
      files(pattern)
                    All files of the current changeset matching the pattern. See
                    'hg help patterns'.

Test section lookup by translated message

str.lower() instead of encoding.lower(str) on translated message might
make message meaningless, because some encoding uses 0x41(A) - 0x5a(Z)
as the second or later byte of multi-byte character.

For example, "\x8bL\x98^" (translation of "record" in ja_JP.cp932)
contains 0x4c (L). str.lower() replaces 0x4c(L) by 0x6c(l) and this
replacement makes message meaningless.

This tests that section lookup by translated string isn't broken by
such str.lower().

  $ $PYTHON <<EOF
  > def escape(s):
  >     return ''.join('\u%x' % ord(uc) for uc in s.decode('cp932'))
  > # translation of "record" in ja_JP.cp932
  > upper = "\x8bL\x98^"
  > # str.lower()-ed section name should be treated as different one
  > lower = "\x8bl\x98^"
  > with open('ambiguous.py', 'w') as fp:
  >     fp.write("""# ambiguous section names in ja_JP.cp932
  > u'''summary of extension
  > 
  > %s
  > ----
  > 
  > Upper name should show only this message
  > 
  > %s
  > ----
  > 
  > Lower name should show only this message
  > 
  > subsequent section
  > ------------------
  > 
  > This should be hidden at 'hg help ambiguous' with section name.
  > '''
  > """ % (escape(upper), escape(lower)))
  > EOF

  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > ambiguous = ./ambiguous.py
  > EOF

  $ $PYTHON <<EOF | sh
  > upper = "\x8bL\x98^"
  > print "hg --encoding cp932 help -e ambiguous.%s" % upper
  > EOF
  \x8bL\x98^ (esc)
  ----
  
  Upper name should show only this message
  

  $ $PYTHON <<EOF | sh
  > lower = "\x8bl\x98^"
  > print "hg --encoding cp932 help -e ambiguous.%s" % lower
  > EOF
  \x8bl\x98^ (esc)
  ----
  
  Lower name should show only this message
  

  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > ambiguous = !
  > EOF

Show help content of disabled extensions

  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > ambiguous = !./ambiguous.py
  > EOF
  $ hg help -e ambiguous
  ambiguous extension - (no help text available)
  
  (use 'hg help extensions' for information on enabling extensions)

Test dynamic list of merge tools only shows up once
  $ hg help merge-tools
  Merge Tools
  """""""""""
  
      To merge files Mercurial uses merge tools.
  
      A merge tool combines two different versions of a file into a merged file.
      Merge tools are given the two files and the greatest common ancestor of
      the two file versions, so they can determine the changes made on both
      branches.
  
      Merge tools are used both for 'hg resolve', 'hg merge', 'hg update', 'hg
      backout' and in several extensions.
  
      Usually, the merge tool tries to automatically reconcile the files by
      combining all non-overlapping changes that occurred separately in the two
      different evolutions of the same initial base file. Furthermore, some
      interactive merge programs make it easier to manually resolve conflicting
      merges, either in a graphical way, or by inserting some conflict markers.
      Mercurial does not include any interactive merge programs but relies on
      external tools for that.
  
      Available merge tools
      =====================
  
      External merge tools and their properties are configured in the merge-
      tools configuration section - see hgrc(5) - but they can often just be
      named by their executable.
  
      A merge tool is generally usable if its executable can be found on the
      system and if it can handle the merge. The executable is found if it is an
      absolute or relative executable path or the name of an application in the
      executable search path. The tool is assumed to be able to handle the merge
      if it can handle symlinks if the file is a symlink, if it can handle
      binary files if the file is binary, and if a GUI is available if the tool
      requires a GUI.
  
      There are some internal merge tools which can be used. The internal merge
      tools are:
  
      ":dump"
        Creates three versions of the files to merge, containing the contents of
        local, other and base. These files can then be used to perform a merge
        manually. If the file to be merged is named "a.txt", these files will
        accordingly be named "a.txt.local", "a.txt.other" and "a.txt.base" and
        they will be placed in the same directory as "a.txt".
  
        This implies permerge. Therefore, files aren't dumped, if premerge runs
        successfully. Use :forcedump to forcibly write files out.
  
      ":fail"
        Rather than attempting to merge files that were modified on both
        branches, it marks them as unresolved. The resolve command must be used
        to resolve these conflicts.
  
      ":forcedump"
        Creates three versions of the files as same as :dump, but omits
        premerge.
  
      ":local"
        Uses the local 'p1()' version of files as the merged version.
  
      ":merge"
        Uses the internal non-interactive simple merge algorithm for merging
        files. It will fail if there are any conflicts and leave markers in the
        partially merged file. Markers will have two sections, one for each side
        of merge.
  
      ":merge-local"
        Like :merge, but resolve all conflicts non-interactively in favor of the
        local 'p1()' changes.
  
      ":merge-other"
        Like :merge, but resolve all conflicts non-interactively in favor of the
        other 'p2()' changes.
  
      ":merge3"
        Uses the internal non-interactive simple merge algorithm for merging
        files. It will fail if there are any conflicts and leave markers in the
        partially merged file. Marker will have three sections, one from each
        side of the merge and one for the base content.
  
      ":other"
        Uses the other 'p2()' version of files as the merged version.
  
      ":prompt"
        Asks the user which of the local 'p1()' or the other 'p2()' version to
        keep as the merged version.
  
      ":tagmerge"
        Uses the internal tag merge algorithm (experimental).
  
      ":union"
        Uses the internal non-interactive simple merge algorithm for merging
        files. It will use both left and right sides for conflict regions. No
        markers are inserted.
  
      Internal tools are always available and do not require a GUI but will by
      default not handle symlinks or binary files.
  
      Choosing a merge tool
      =====================
  
      Mercurial uses these rules when deciding which merge tool to use:
  
      1. If a tool has been specified with the --tool option to merge or
         resolve, it is used.  If it is the name of a tool in the merge-tools
         configuration, its configuration is used. Otherwise the specified tool
         must be executable by the shell.
      2. If the "HGMERGE" environment variable is present, its value is used and
         must be executable by the shell.
      3. If the filename of the file to be merged matches any of the patterns in
         the merge-patterns configuration section, the first usable merge tool
         corresponding to a matching pattern is used. Here, binary capabilities
         of the merge tool are not considered.
      4. If ui.merge is set it will be considered next. If the value is not the
         name of a configured tool, the specified value is used and must be
         executable by the shell. Otherwise the named tool is used if it is
         usable.
      5. If any usable merge tools are present in the merge-tools configuration
         section, the one with the highest priority is used.
      6. If a program named "hgmerge" can be found on the system, it is used -
         but it will by default not be used for symlinks and binary files.
      7. If the file to be merged is not binary and is not a symlink, then
         internal ":merge" is used.
      8. Otherwise, ":prompt" is used.
  
      Note:
         After selecting a merge program, Mercurial will by default attempt to
         merge the files using a simple merge algorithm first. Only if it
         doesn't succeed because of conflicting changes Mercurial will actually
         execute the merge program. Whether to use the simple merge algorithm
         first can be controlled by the premerge setting of the merge tool.
         Premerge is enabled by default unless the file is binary or a symlink.
  
      See the merge-tools and ui sections of hgrc(5) for details on the
      configuration of merge tools.

Compression engines listed in `hg help bundlespec`

  $ hg help bundlespec | grep gzip
          "v1" bundles can only use the "gzip", "bzip2", and "none" compression
        An algorithm that produces smaller bundles than "gzip".
        This engine will likely produce smaller bundles than "gzip" but will be
      "gzip"
        better compression than "gzip". It also frequently yields better (?)

Test usage of section marks in help documents

  $ cd "$TESTDIR"/../doc
  $ $PYTHON check-seclevel.py
  $ cd $TESTTMP

#if serve

Test the help pages in hgweb.

Dish up an empty repo; serve it cold.

  $ hg init "$TESTTMP/test"
  $ hg serve -R "$TESTTMP/test" -n test -p $HGPORT -d --pid-file=hg.pid
  $ cat hg.pid >> $DAEMON_PIDS

  $ get-with-headers.py $LOCALIP:$HGPORT "help"
  200 Script output follows
  
  <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
  <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en-US">
  <head>
  <link rel="icon" href="/static/hgicon.png" type="image/png" />
  <meta name="robots" content="index, nofollow" />
  <link rel="stylesheet" href="/static/style-paper.css" type="text/css" />
  <script type="text/javascript" src="/static/mercurial.js"></script>
  
  <title>Help: Index</title>
  </head>
  <body>
  
  <div class="container">
  <div class="menu">
  <div class="logo">
  <a href="https://mercurial-scm.org/">
  <img src="/static/hglogo.png" alt="mercurial" /></a>
  </div>
  <ul>
  <li><a href="/shortlog">log</a></li>
  <li><a href="/graph">graph</a></li>
  <li><a href="/tags">tags</a></li>
  <li><a href="/bookmarks">bookmarks</a></li>
  <li><a href="/branches">branches</a></li>
  </ul>
  <ul>
  <li class="active">help</li>
  </ul>
  </div>
  
  <div class="main">
  <h2 class="breadcrumb"><a href="/">Mercurial</a> </h2>
  
  <form class="search" action="/log">
  
  <p><input name="rev" id="search1" type="text" size="30" value="" /></p>
  <div id="hint">Find changesets by keywords (author, files, the commit message), revision
  number or hash, or <a href="/help/revsets">revset expression</a>.</div>
  </form>
  <table class="bigtable">
  <tr><td colspan="2"><h2><a name="topics" href="#topics">Topics</a></h2></td></tr>
  
  <tr><td>
  <a href="/help/bundlespec">
  bundlespec
  </a>
  </td><td>
  Bundle File Formats
  </td></tr>
  <tr><td>
  <a href="/help/color">
  color
  </a>
  </td><td>
  Colorizing Outputs
  </td></tr>
  <tr><td>
  <a href="/help/config">
  config
  </a>
  </td><td>
  Configuration Files
  </td></tr>
  <tr><td>
  <a href="/help/dates">
  dates
  </a>
  </td><td>
  Date Formats
  </td></tr>
  <tr><td>
  <a href="/help/diffs">
  diffs
  </a>
  </td><td>
  Diff Formats
  </td></tr>
  <tr><td>
  <a href="/help/environment">
  environment
  </a>
  </td><td>
  Environment Variables
  </td></tr>
  <tr><td>
  <a href="/help/extensions">
  extensions
  </a>
  </td><td>
  Using Additional Features
  </td></tr>
  <tr><td>
  <a href="/help/filesets">
  filesets
  </a>
  </td><td>
  Specifying File Sets
  </td></tr>
  <tr><td>
  <a href="/help/glossary">
  glossary
  </a>
  </td><td>
  Glossary
  </td></tr>
  <tr><td>
  <a href="/help/hgignore">
  hgignore
  </a>
  </td><td>
  Syntax for Mercurial Ignore Files
  </td></tr>
  <tr><td>
  <a href="/help/hgweb">
  hgweb
  </a>
  </td><td>
  Configuring hgweb
  </td></tr>
  <tr><td>
  <a href="/help/internals">
  internals
  </a>
  </td><td>
  Technical implementation topics
  </td></tr>
  <tr><td>
  <a href="/help/merge-tools">
  merge-tools
  </a>
  </td><td>
  Merge Tools
  </td></tr>
  <tr><td>
  <a href="/help/pager">
  pager
  </a>
  </td><td>
  Pager Support
  </td></tr>
  <tr><td>
  <a href="/help/patterns">
  patterns
  </a>
  </td><td>
  File Name Patterns
  </td></tr>
  <tr><td>
  <a href="/help/phases">
  phases
  </a>
  </td><td>
  Working with Phases
  </td></tr>
  <tr><td>
  <a href="/help/revisions">
  revisions
  </a>
  </td><td>
  Specifying Revisions
  </td></tr>
  <tr><td>
  <a href="/help/scripting">
  scripting
  </a>
  </td><td>
  Using Mercurial from scripts and automation
  </td></tr>
  <tr><td>
  <a href="/help/subrepos">
  subrepos
  </a>
  </td><td>
  Subrepositories
  </td></tr>
  <tr><td>
  <a href="/help/templating">
  templating
  </a>
  </td><td>
  Template Usage
  </td></tr>
  <tr><td>
  <a href="/help/urls">
  urls
  </a>
  </td><td>
  URL Paths
  </td></tr>
  <tr><td>
  <a href="/help/topic-containing-verbose">
  topic-containing-verbose
  </a>
  </td><td>
  This is the topic to test omit indicating.
  </td></tr>
  
  
  <tr><td colspan="2"><h2><a name="main" href="#main">Main Commands</a></h2></td></tr>
  
  <tr><td>
  <a href="/help/add">
  add
  </a>
  </td><td>
  add the specified files on the next commit
  </td></tr>
  <tr><td>
  <a href="/help/annotate">
  annotate
  </a>
  </td><td>
  show changeset information by line for each file
  </td></tr>
  <tr><td>
  <a href="/help/clone">
  clone
  </a>
  </td><td>
  make a copy of an existing repository
  </td></tr>
  <tr><td>
  <a href="/help/commit">
  commit
  </a>
  </td><td>
  commit the specified files or all outstanding changes
  </td></tr>
  <tr><td>
  <a href="/help/diff">
  diff
  </a>
  </td><td>
  diff repository (or selected files)
  </td></tr>
  <tr><td>
  <a href="/help/export">
  export
  </a>
  </td><td>
  dump the header and diffs for one or more changesets
  </td></tr>
  <tr><td>
  <a href="/help/forget">
  forget
  </a>
  </td><td>
  forget the specified files on the next commit
  </td></tr>
  <tr><td>
  <a href="/help/init">
  init
  </a>
  </td><td>
  create a new repository in the given directory
  </td></tr>
  <tr><td>
  <a href="/help/log">
  log
  </a>
  </td><td>
  show revision history of entire repository or files
  </td></tr>
  <tr><td>
  <a href="/help/merge">
  merge
  </a>
  </td><td>
  merge another revision into working directory
  </td></tr>
  <tr><td>
  <a href="/help/pull">
  pull
  </a>
  </td><td>
  pull changes from the specified source
  </td></tr>
  <tr><td>
  <a href="/help/push">
  push
  </a>
  </td><td>
  push changes to the specified destination
  </td></tr>
  <tr><td>
  <a href="/help/remove">
  remove
  </a>
  </td><td>
  remove the specified files on the next commit
  </td></tr>
  <tr><td>
  <a href="/help/serve">
  serve
  </a>
  </td><td>
  start stand-alone webserver
  </td></tr>
  <tr><td>
  <a href="/help/status">
  status
  </a>
  </td><td>
  show changed files in the working directory
  </td></tr>
  <tr><td>
  <a href="/help/summary">
  summary
  </a>
  </td><td>
  summarize working directory state
  </td></tr>
  <tr><td>
  <a href="/help/update">
  update
  </a>
  </td><td>
  update working directory (or switch revisions)
  </td></tr>
  
  
  
  <tr><td colspan="2"><h2><a name="other" href="#other">Other Commands</a></h2></td></tr>
  
  <tr><td>
  <a href="/help/addremove">
  addremove
  </a>
  </td><td>
  add all new files, delete all missing files
  </td></tr>
  <tr><td>
  <a href="/help/archive">
  archive
  </a>
  </td><td>
  create an unversioned archive of a repository revision
  </td></tr>
  <tr><td>
  <a href="/help/backout">
  backout
  </a>
  </td><td>
  reverse effect of earlier changeset
  </td></tr>
  <tr><td>
  <a href="/help/bisect">
  bisect
  </a>
  </td><td>
  subdivision search of changesets
  </td></tr>
  <tr><td>
  <a href="/help/bookmarks">
  bookmarks
  </a>
  </td><td>
  create a new bookmark or list existing bookmarks
  </td></tr>
  <tr><td>
  <a href="/help/branch">
  branch
  </a>
  </td><td>
  set or show the current branch name
  </td></tr>
  <tr><td>
  <a href="/help/branches">
  branches
  </a>
  </td><td>
  list repository named branches
  </td></tr>
  <tr><td>
  <a href="/help/bundle">
  bundle
  </a>
  </td><td>
  create a bundle file
  </td></tr>
  <tr><td>
  <a href="/help/cat">
  cat
  </a>
  </td><td>
  output the current or given revision of files
  </td></tr>
  <tr><td>
  <a href="/help/config">
  config
  </a>
  </td><td>
  show combined config settings from all hgrc files
  </td></tr>
  <tr><td>
  <a href="/help/copy">
  copy
  </a>
  </td><td>
  mark files as copied for the next commit
  </td></tr>
  <tr><td>
  <a href="/help/files">
  files
  </a>
  </td><td>
  list tracked files
  </td></tr>
  <tr><td>
  <a href="/help/graft">
  graft
  </a>
  </td><td>
  copy changes from other branches onto the current branch
  </td></tr>
  <tr><td>
  <a href="/help/grep">
  grep
  </a>
  </td><td>
  search revision history for a pattern in specified files
  </td></tr>
  <tr><td>
  <a href="/help/heads">
  heads
  </a>
  </td><td>
  show branch heads
  </td></tr>
  <tr><td>
  <a href="/help/help">
  help
  </a>
  </td><td>
  show help for a given topic or a help overview
  </td></tr>
  <tr><td>
  <a href="/help/hgalias">
  hgalias
  </a>
  </td><td>
  summarize working directory state
  </td></tr>
  <tr><td>
  <a href="/help/identify">
  identify
  </a>
  </td><td>
  identify the working directory or specified revision
  </td></tr>
  <tr><td>
  <a href="/help/import">
  import
  </a>
  </td><td>
  import an ordered set of patches
  </td></tr>
  <tr><td>
  <a href="/help/incoming">
  incoming
  </a>
  </td><td>
  show new changesets found in source
  </td></tr>
  <tr><td>
  <a href="/help/manifest">
  manifest
  </a>
  </td><td>
  output the current or given revision of the project manifest
  </td></tr>
  <tr><td>
  <a href="/help/nohelp">
  nohelp
  </a>
  </td><td>
  (no help text available)
  </td></tr>
  <tr><td>
  <a href="/help/outgoing">
  outgoing
  </a>
  </td><td>
  show changesets not found in the destination
  </td></tr>
  <tr><td>
  <a href="/help/paths">
  paths
  </a>
  </td><td>
  show aliases for remote repositories
  </td></tr>
  <tr><td>
  <a href="/help/phase">
  phase
  </a>
  </td><td>
  set or show the current phase name
  </td></tr>
  <tr><td>
  <a href="/help/recover">
  recover
  </a>
  </td><td>
  roll back an interrupted transaction
  </td></tr>
  <tr><td>
  <a href="/help/rename">
  rename
  </a>
  </td><td>
  rename files; equivalent of copy + remove
  </td></tr>
  <tr><td>
  <a href="/help/resolve">
  resolve
  </a>
  </td><td>
  redo merges or set/view the merge status of files
  </td></tr>
  <tr><td>
  <a href="/help/revert">
  revert
  </a>
  </td><td>
  restore files to their checkout state
  </td></tr>
  <tr><td>
  <a href="/help/root">
  root
  </a>
  </td><td>
  print the root (top) of the current working directory
  </td></tr>
  <tr><td>
  <a href="/help/shellalias">
  shellalias
  </a>
  </td><td>
  (no help text available)
  </td></tr>
  <tr><td>
  <a href="/help/tag">
  tag
  </a>
  </td><td>
  add one or more tags for the current or given revision
  </td></tr>
  <tr><td>
  <a href="/help/tags">
  tags
  </a>
  </td><td>
  list repository tags
  </td></tr>
  <tr><td>
  <a href="/help/unbundle">
  unbundle
  </a>
  </td><td>
  apply one or more bundle files
  </td></tr>
  <tr><td>
  <a href="/help/verify">
  verify
  </a>
  </td><td>
  verify the integrity of the repository
  </td></tr>
  <tr><td>
  <a href="/help/version">
  version
  </a>
  </td><td>
  output version and copyright information
  </td></tr>
  
  
  </table>
  </div>
  </div>
  
  
  
  </body>
  </html>
  

  $ get-with-headers.py $LOCALIP:$HGPORT "help/add"
  200 Script output follows
  
  <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
  <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en-US">
  <head>
  <link rel="icon" href="/static/hgicon.png" type="image/png" />
  <meta name="robots" content="index, nofollow" />
  <link rel="stylesheet" href="/static/style-paper.css" type="text/css" />
  <script type="text/javascript" src="/static/mercurial.js"></script>
  
  <title>Help: add</title>
  </head>
  <body>
  
  <div class="container">
  <div class="menu">
  <div class="logo">
  <a href="https://mercurial-scm.org/">
  <img src="/static/hglogo.png" alt="mercurial" /></a>
  </div>
  <ul>
  <li><a href="/shortlog">log</a></li>
  <li><a href="/graph">graph</a></li>
  <li><a href="/tags">tags</a></li>
  <li><a href="/bookmarks">bookmarks</a></li>
  <li><a href="/branches">branches</a></li>
  </ul>
  <ul>
   <li class="active"><a href="/help">help</a></li>
  </ul>
  </div>
  
  <div class="main">
  <h2 class="breadcrumb"><a href="/">Mercurial</a> </h2>
  <h3>Help: add</h3>
  
  <form class="search" action="/log">
  
  <p><input name="rev" id="search1" type="text" size="30" value="" /></p>
  <div id="hint">Find changesets by keywords (author, files, the commit message), revision
  number or hash, or <a href="/help/revsets">revset expression</a>.</div>
  </form>
  <div id="doc">
  <p>
  hg add [OPTION]... [FILE]...
  </p>
  <p>
  add the specified files on the next commit
  </p>
  <p>
  Schedule files to be version controlled and added to the
  repository.
  </p>
  <p>
  The files will be added to the repository at the next commit. To
  undo an add before that, see 'hg forget'.
  </p>
  <p>
  If no names are given, add all files to the repository (except
  files matching &quot;.hgignore&quot;).
  </p>
  <p>
  Examples:
  </p>
  <ul>
   <li> New (unknown) files are added   automatically by 'hg add':
  <pre>
  \$ ls (re)
  foo.c
  \$ hg status (re)
  ? foo.c
  \$ hg add (re)
  adding foo.c
  \$ hg status (re)
  A foo.c
  </pre>
   <li> Specific files to be added can be specified:
  <pre>
  \$ ls (re)
  bar.c  foo.c
  \$ hg status (re)
  ? bar.c
  ? foo.c
  \$ hg add bar.c (re)
  \$ hg status (re)
  A bar.c
  ? foo.c
  </pre>
  </ul>
  <p>
  Returns 0 if all files are successfully added.
  </p>
  <p>
  options ([+] can be repeated):
  </p>
  <table>
  <tr><td>-I</td>
  <td>--include PATTERN [+]</td>
  <td>include names matching the given patterns</td></tr>
  <tr><td>-X</td>
  <td>--exclude PATTERN [+]</td>
  <td>exclude names matching the given patterns</td></tr>
  <tr><td>-S</td>
  <td>--subrepos</td>
  <td>recurse into subrepositories</td></tr>
  <tr><td>-n</td>
  <td>--dry-run</td>
  <td>do not perform actions, just print output</td></tr>
  </table>
  <p>
  global options ([+] can be repeated):
  </p>
  <table>
  <tr><td>-R</td>
  <td>--repository REPO</td>
  <td>repository root directory or name of overlay bundle file</td></tr>
  <tr><td></td>
  <td>--cwd DIR</td>
  <td>change working directory</td></tr>
  <tr><td>-y</td>
  <td>--noninteractive</td>
  <td>do not prompt, automatically pick the first choice for all prompts</td></tr>
  <tr><td>-q</td>
  <td>--quiet</td>
  <td>suppress output</td></tr>
  <tr><td>-v</td>
  <td>--verbose</td>
  <td>enable additional output</td></tr>
  <tr><td></td>
  <td>--color TYPE</td>
  <td>when to colorize (boolean, always, auto, never, or debug)</td></tr>
  <tr><td></td>
  <td>--config CONFIG [+]</td>
  <td>set/override config option (use 'section.name=value')</td></tr>
  <tr><td></td>
  <td>--debug</td>
  <td>enable debugging output</td></tr>
  <tr><td></td>
  <td>--debugger</td>
  <td>start debugger</td></tr>
  <tr><td></td>
  <td>--encoding ENCODE</td>
  <td>set the charset encoding (default: ascii)</td></tr>
  <tr><td></td>
  <td>--encodingmode MODE</td>
  <td>set the charset encoding mode (default: strict)</td></tr>
  <tr><td></td>
  <td>--traceback</td>
  <td>always print a traceback on exception</td></tr>
  <tr><td></td>
  <td>--time</td>
  <td>time how long the command takes</td></tr>
  <tr><td></td>
  <td>--profile</td>
  <td>print command execution profile</td></tr>
  <tr><td></td>
  <td>--version</td>
  <td>output version information and exit</td></tr>
  <tr><td>-h</td>
  <td>--help</td>
  <td>display help and exit</td></tr>
  <tr><td></td>
  <td>--hidden</td>
  <td>consider hidden changesets</td></tr>
  <tr><td></td>
  <td>--pager TYPE</td>
  <td>when to paginate (boolean, always, auto, or never) (default: auto)</td></tr>
  </table>
  
  </div>
  </div>
  </div>
  
  
  
  </body>
  </html>
  

  $ get-with-headers.py $LOCALIP:$HGPORT "help/remove"
  200 Script output follows
  
  <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
  <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en-US">
  <head>
  <link rel="icon" href="/static/hgicon.png" type="image/png" />
  <meta name="robots" content="index, nofollow" />
  <link rel="stylesheet" href="/static/style-paper.css" type="text/css" />
  <script type="text/javascript" src="/static/mercurial.js"></script>
  
  <title>Help: remove</title>
  </head>
  <body>
  
  <div class="container">
  <div class="menu">
  <div class="logo">
  <a href="https://mercurial-scm.org/">
  <img src="/static/hglogo.png" alt="mercurial" /></a>
  </div>
  <ul>
  <li><a href="/shortlog">log</a></li>
  <li><a href="/graph">graph</a></li>
  <li><a href="/tags">tags</a></li>
  <li><a href="/bookmarks">bookmarks</a></li>
  <li><a href="/branches">branches</a></li>
  </ul>
  <ul>
   <li class="active"><a href="/help">help</a></li>
  </ul>
  </div>
  
  <div class="main">
  <h2 class="breadcrumb"><a href="/">Mercurial</a> </h2>
  <h3>Help: remove</h3>
  
  <form class="search" action="/log">
  
  <p><input name="rev" id="search1" type="text" size="30" value="" /></p>
  <div id="hint">Find changesets by keywords (author, files, the commit message), revision
  number or hash, or <a href="/help/revsets">revset expression</a>.</div>
  </form>
  <div id="doc">
  <p>
  hg remove [OPTION]... FILE...
  </p>
  <p>
  aliases: rm
  </p>
  <p>
  remove the specified files on the next commit
  </p>
  <p>
  Schedule the indicated files for removal from the current branch.
  </p>
  <p>
  This command schedules the files to be removed at the next commit.
  To undo a remove before that, see 'hg revert'. To undo added
  files, see 'hg forget'.
  </p>
  <p>
  -A/--after can be used to remove only files that have already
  been deleted, -f/--force can be used to force deletion, and -Af
  can be used to remove files from the next revision without
  deleting them from the working directory.
  </p>
  <p>
  The following table details the behavior of remove for different
  file states (columns) and option combinations (rows). The file
  states are Added [A], Clean [C], Modified [M] and Missing [!]
  (as reported by 'hg status'). The actions are Warn, Remove
  (from branch) and Delete (from disk):
  </p>
  <table>
  <tr><td>opt/state</td>
  <td>A</td>
  <td>C</td>
  <td>M</td>
  <td>!</td></tr>
  <tr><td>none</td>
  <td>W</td>
  <td>RD</td>
  <td>W</td>
  <td>R</td></tr>
  <tr><td>-f</td>
  <td>R</td>
  <td>RD</td>
  <td>RD</td>
  <td>R</td></tr>
  <tr><td>-A</td>
  <td>W</td>
  <td>W</td>
  <td>W</td>
  <td>R</td></tr>
  <tr><td>-Af</td>
  <td>R</td>
  <td>R</td>
  <td>R</td>
  <td>R</td></tr>
  </table>
  <p>
  <b>Note:</b> 
  </p>
  <p>
  'hg remove' never deletes files in Added [A] state from the
  working directory, not even if &quot;--force&quot; is specified.
  </p>
  <p>
  Returns 0 on success, 1 if any warnings encountered.
  </p>
  <p>
  options ([+] can be repeated):
  </p>
  <table>
  <tr><td>-A</td>
  <td>--after</td>
  <td>record delete for missing files</td></tr>
  <tr><td>-f</td>
  <td>--force</td>
  <td>forget added files, delete modified files</td></tr>
  <tr><td>-S</td>
  <td>--subrepos</td>
  <td>recurse into subrepositories</td></tr>
  <tr><td>-I</td>
  <td>--include PATTERN [+]</td>
  <td>include names matching the given patterns</td></tr>
  <tr><td>-X</td>
  <td>--exclude PATTERN [+]</td>
  <td>exclude names matching the given patterns</td></tr>
  </table>
  <p>
  global options ([+] can be repeated):
  </p>
  <table>
  <tr><td>-R</td>
  <td>--repository REPO</td>
  <td>repository root directory or name of overlay bundle file</td></tr>
  <tr><td></td>
  <td>--cwd DIR</td>
  <td>change working directory</td></tr>
  <tr><td>-y</td>
  <td>--noninteractive</td>
  <td>do not prompt, automatically pick the first choice for all prompts</td></tr>
  <tr><td>-q</td>
  <td>--quiet</td>
  <td>suppress output</td></tr>
  <tr><td>-v</td>
  <td>--verbose</td>
  <td>enable additional output</td></tr>
  <tr><td></td>
  <td>--color TYPE</td>
  <td>when to colorize (boolean, always, auto, never, or debug)</td></tr>
  <tr><td></td>
  <td>--config CONFIG [+]</td>
  <td>set/override config option (use 'section.name=value')</td></tr>
  <tr><td></td>
  <td>--debug</td>
  <td>enable debugging output</td></tr>
  <tr><td></td>
  <td>--debugger</td>
  <td>start debugger</td></tr>
  <tr><td></td>
  <td>--encoding ENCODE</td>
  <td>set the charset encoding (default: ascii)</td></tr>
  <tr><td></td>
  <td>--encodingmode MODE</td>
  <td>set the charset encoding mode (default: strict)</td></tr>
  <tr><td></td>
  <td>--traceback</td>
  <td>always print a traceback on exception</td></tr>
  <tr><td></td>
  <td>--time</td>
  <td>time how long the command takes</td></tr>
  <tr><td></td>
  <td>--profile</td>
  <td>print command execution profile</td></tr>
  <tr><td></td>
  <td>--version</td>
  <td>output version information and exit</td></tr>
  <tr><td>-h</td>
  <td>--help</td>
  <td>display help and exit</td></tr>
  <tr><td></td>
  <td>--hidden</td>
  <td>consider hidden changesets</td></tr>
  <tr><td></td>
  <td>--pager TYPE</td>
  <td>when to paginate (boolean, always, auto, or never) (default: auto)</td></tr>
  </table>
  
  </div>
  </div>
  </div>
  
  
  
  </body>
  </html>
  

  $ get-with-headers.py $LOCALIP:$HGPORT "help/dates"
  200 Script output follows
  
  <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
  <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en-US">
  <head>
  <link rel="icon" href="/static/hgicon.png" type="image/png" />
  <meta name="robots" content="index, nofollow" />
  <link rel="stylesheet" href="/static/style-paper.css" type="text/css" />
  <script type="text/javascript" src="/static/mercurial.js"></script>
  
  <title>Help: dates</title>
  </head>
  <body>
  
  <div class="container">
  <div class="menu">
  <div class="logo">
  <a href="https://mercurial-scm.org/">
  <img src="/static/hglogo.png" alt="mercurial" /></a>
  </div>
  <ul>
  <li><a href="/shortlog">log</a></li>
  <li><a href="/graph">graph</a></li>
  <li><a href="/tags">tags</a></li>
  <li><a href="/bookmarks">bookmarks</a></li>
  <li><a href="/branches">branches</a></li>
  </ul>
  <ul>
   <li class="active"><a href="/help">help</a></li>
  </ul>
  </div>
  
  <div class="main">
  <h2 class="breadcrumb"><a href="/">Mercurial</a> </h2>
  <h3>Help: dates</h3>
  
  <form class="search" action="/log">
  
  <p><input name="rev" id="search1" type="text" size="30" value="" /></p>
  <div id="hint">Find changesets by keywords (author, files, the commit message), revision
  number or hash, or <a href="/help/revsets">revset expression</a>.</div>
  </form>
  <div id="doc">
  <h1>Date Formats</h1>
  <p>
  Some commands allow the user to specify a date, e.g.:
  </p>
  <ul>
   <li> backout, commit, import, tag: Specify the commit date.
   <li> log, revert, update: Select revision(s) by date.
  </ul>
  <p>
  Many date formats are valid. Here are some examples:
  </p>
  <ul>
   <li> &quot;Wed Dec 6 13:18:29 2006&quot; (local timezone assumed)
   <li> &quot;Dec 6 13:18 -0600&quot; (year assumed, time offset provided)
   <li> &quot;Dec 6 13:18 UTC&quot; (UTC and GMT are aliases for +0000)
   <li> &quot;Dec 6&quot; (midnight)
   <li> &quot;13:18&quot; (today assumed)
   <li> &quot;3:39&quot; (3:39AM assumed)
   <li> &quot;3:39pm&quot; (15:39)
   <li> &quot;2006-12-06 13:18:29&quot; (ISO 8601 format)
   <li> &quot;2006-12-6 13:18&quot;
   <li> &quot;2006-12-6&quot;
   <li> &quot;12-6&quot;
   <li> &quot;12/6&quot;
   <li> &quot;12/6/6&quot; (Dec 6 2006)
   <li> &quot;today&quot; (midnight)
   <li> &quot;yesterday&quot; (midnight)
   <li> &quot;now&quot; - right now
  </ul>
  <p>
  Lastly, there is Mercurial's internal format:
  </p>
  <ul>
   <li> &quot;1165411109 0&quot; (Wed Dec 6 13:18:29 2006 UTC)
  </ul>
  <p>
  This is the internal representation format for dates. The first number
  is the number of seconds since the epoch (1970-01-01 00:00 UTC). The
  second is the offset of the local timezone, in seconds west of UTC
  (negative if the timezone is east of UTC).
  </p>
  <p>
  The log command also accepts date ranges:
  </p>
  <ul>
   <li> &quot;&lt;DATE&quot; - at or before a given date/time
   <li> &quot;&gt;DATE&quot; - on or after a given date/time
   <li> &quot;DATE to DATE&quot; - a date range, inclusive
   <li> &quot;-DAYS&quot; - within a given number of days of today
  </ul>
  
  </div>
  </div>
  </div>
  
  
  
  </body>
  </html>
  

Sub-topic indexes rendered properly

  $ get-with-headers.py $LOCALIP:$HGPORT "help/internals"
  200 Script output follows
  
  <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
  <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en-US">
  <head>
  <link rel="icon" href="/static/hgicon.png" type="image/png" />
  <meta name="robots" content="index, nofollow" />
  <link rel="stylesheet" href="/static/style-paper.css" type="text/css" />
  <script type="text/javascript" src="/static/mercurial.js"></script>
  
  <title>Help: internals</title>
  </head>
  <body>
  
  <div class="container">
  <div class="menu">
  <div class="logo">
  <a href="https://mercurial-scm.org/">
  <img src="/static/hglogo.png" alt="mercurial" /></a>
  </div>
  <ul>
  <li><a href="/shortlog">log</a></li>
  <li><a href="/graph">graph</a></li>
  <li><a href="/tags">tags</a></li>
  <li><a href="/bookmarks">bookmarks</a></li>
  <li><a href="/branches">branches</a></li>
  </ul>
  <ul>
  <li><a href="/help">help</a></li>
  </ul>
  </div>
  
  <div class="main">
  <h2 class="breadcrumb"><a href="/">Mercurial</a> </h2>
  
  <form class="search" action="/log">
  
  <p><input name="rev" id="search1" type="text" size="30" value="" /></p>
  <div id="hint">Find changesets by keywords (author, files, the commit message), revision
  number or hash, or <a href="/help/revsets">revset expression</a>.</div>
  </form>
  <table class="bigtable">
  <tr><td colspan="2"><h2><a name="topics" href="#topics">Topics</a></h2></td></tr>
  
  <tr><td>
  <a href="/help/internals.bundles">
  bundles
  </a>
  </td><td>
  Bundles
  </td></tr>
  <tr><td>
  <a href="/help/internals.censor">
  censor
  </a>
  </td><td>
  Censor
  </td></tr>
  <tr><td>
  <a href="/help/internals.changegroups">
  changegroups
  </a>
  </td><td>
  Changegroups
  </td></tr>
  <tr><td>
  <a href="/help/internals.requirements">
  requirements
  </a>
  </td><td>
  Repository Requirements
  </td></tr>
  <tr><td>
  <a href="/help/internals.revlogs">
  revlogs
  </a>
  </td><td>
  Revision Logs
  </td></tr>
  <tr><td>
  <a href="/help/internals.wireprotocol">
  wireprotocol
  </a>
  </td><td>
  Wire Protocol
  </td></tr>
  
  
  
  
  
  </table>
  </div>
  </div>
  
  
  
  </body>
  </html>
  

Sub-topic topics rendered properly

  $ get-with-headers.py $LOCALIP:$HGPORT "help/internals.changegroups"
  200 Script output follows
  
  <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
  <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en-US">
  <head>
  <link rel="icon" href="/static/hgicon.png" type="image/png" />
  <meta name="robots" content="index, nofollow" />
  <link rel="stylesheet" href="/static/style-paper.css" type="text/css" />
  <script type="text/javascript" src="/static/mercurial.js"></script>
  
  <title>Help: internals.changegroups</title>
  </head>
  <body>
  
  <div class="container">
  <div class="menu">
  <div class="logo">
  <a href="https://mercurial-scm.org/">
  <img src="/static/hglogo.png" alt="mercurial" /></a>
  </div>
  <ul>
  <li><a href="/shortlog">log</a></li>
  <li><a href="/graph">graph</a></li>
  <li><a href="/tags">tags</a></li>
  <li><a href="/bookmarks">bookmarks</a></li>
  <li><a href="/branches">branches</a></li>
  </ul>
  <ul>
   <li class="active"><a href="/help">help</a></li>
  </ul>
  </div>
  
  <div class="main">
  <h2 class="breadcrumb"><a href="/">Mercurial</a> </h2>
  <h3>Help: internals.changegroups</h3>
  
  <form class="search" action="/log">
  
  <p><input name="rev" id="search1" type="text" size="30" value="" /></p>
  <div id="hint">Find changesets by keywords (author, files, the commit message), revision
  number or hash, or <a href="/help/revsets">revset expression</a>.</div>
  </form>
  <div id="doc">
  <h1>Changegroups</h1>
  <p>
  Changegroups are representations of repository revlog data, specifically
  the changelog data, root/flat manifest data, treemanifest data, and
  filelogs.
  </p>
  <p>
  There are 3 versions of changegroups: &quot;1&quot;, &quot;2&quot;, and &quot;3&quot;. From a
  high-level, versions &quot;1&quot; and &quot;2&quot; are almost exactly the same, with the
  only difference being an additional item in the *delta header*.  Version
  &quot;3&quot; adds support for revlog flags in the *delta header* and optionally
  exchanging treemanifests (enabled by setting an option on the
  &quot;changegroup&quot; part in the bundle2).
  </p>
  <p>
  Changegroups when not exchanging treemanifests consist of 3 logical
  segments:
  </p>
  <pre>
  +---------------------------------+
  |           |          |          |
  | changeset | manifest | filelogs |
  |           |          |          |
  |           |          |          |
  +---------------------------------+
  </pre>
  <p>
  When exchanging treemanifests, there are 4 logical segments:
  </p>
  <pre>
  +-------------------------------------------------+
  |           |          |               |          |
  | changeset |   root   | treemanifests | filelogs |
  |           | manifest |               |          |
  |           |          |               |          |
  +-------------------------------------------------+
  </pre>
  <p>
  The principle building block of each segment is a *chunk*. A *chunk*
  is a framed piece of data:
  </p>
  <pre>
  +---------------------------------------+
  |           |                           |
  |  length   |           data            |
  | (4 bytes) |   (&lt;length - 4&gt; bytes)    |
  |           |                           |
  +---------------------------------------+
  </pre>
  <p>
  All integers are big-endian signed integers. Each chunk starts with a 32-bit
  integer indicating the length of the entire chunk (including the length field
  itself).
  </p>
  <p>
  There is a special case chunk that has a value of 0 for the length
  (&quot;0x00000000&quot;). We call this an *empty chunk*.
  </p>
  <h2>Delta Groups</h2>
  <p>
  A *delta group* expresses the content of a revlog as a series of deltas,
  or patches against previous revisions.
  </p>
  <p>
  Delta groups consist of 0 or more *chunks* followed by the *empty chunk*
  to signal the end of the delta group:
  </p>
  <pre>
  +------------------------------------------------------------------------+
  |                |             |               |             |           |
  | chunk0 length  | chunk0 data | chunk1 length | chunk1 data |    0x0    |
  |   (4 bytes)    |  (various)  |   (4 bytes)   |  (various)  | (4 bytes) |
  |                |             |               |             |           |
  +------------------------------------------------------------------------+
  </pre>
  <p>
  Each *chunk*'s data consists of the following:
  </p>
  <pre>
  +---------------------------------------+
  |                        |              |
  |     delta header       |  delta data  |
  |  (various by version)  |  (various)   |
  |                        |              |
  +---------------------------------------+
  </pre>
  <p>
  The *delta data* is a series of *delta*s that describe a diff from an existing
  entry (either that the recipient already has, or previously specified in the
  bundle/changegroup).
  </p>
  <p>
  The *delta header* is different between versions &quot;1&quot;, &quot;2&quot;, and
  &quot;3&quot; of the changegroup format.
  </p>
  <p>
  Version 1 (headerlen=80):
  </p>
  <pre>
  +------------------------------------------------------+
  |            |             |             |             |
  |    node    |   p1 node   |   p2 node   |  link node  |
  | (20 bytes) |  (20 bytes) |  (20 bytes) |  (20 bytes) |
  |            |             |             |             |
  +------------------------------------------------------+
  </pre>
  <p>
  Version 2 (headerlen=100):
  </p>
  <pre>
  +------------------------------------------------------------------+
  |            |             |             |            |            |
  |    node    |   p1 node   |   p2 node   | base node  | link node  |
  | (20 bytes) |  (20 bytes) |  (20 bytes) | (20 bytes) | (20 bytes) |
  |            |             |             |            |            |
  +------------------------------------------------------------------+
  </pre>
  <p>
  Version 3 (headerlen=102):
  </p>
  <pre>
  +------------------------------------------------------------------------------+
  |            |             |             |            |            |           |
  |    node    |   p1 node   |   p2 node   | base node  | link node  |   flags   |
  | (20 bytes) |  (20 bytes) |  (20 bytes) | (20 bytes) | (20 bytes) | (2 bytes) |
  |            |             |             |            |            |           |
  +------------------------------------------------------------------------------+
  </pre>
  <p>
  The *delta data* consists of &quot;chunklen - 4 - headerlen&quot; bytes, which contain a
  series of *delta*s, densely packed (no separators). These deltas describe a diff
  from an existing entry (either that the recipient already has, or previously
  specified in the bundle/changegroup). The format is described more fully in
  &quot;hg help internals.bdiff&quot;, but briefly:
  </p>
  <pre>
  +---------------------------------------------------------------+
  |              |            |            |                      |
  | start offset | end offset | new length |        content       |
  |  (4 bytes)   |  (4 bytes) |  (4 bytes) | (&lt;new length&gt; bytes) |
  |              |            |            |                      |
  +---------------------------------------------------------------+
  </pre>
  <p>
  Please note that the length field in the delta data does *not* include itself.
  </p>
  <p>
  In version 1, the delta is always applied against the previous node from
  the changegroup or the first parent if this is the first entry in the
  changegroup.
  </p>
  <p>
  In version 2 and up, the delta base node is encoded in the entry in the
  changegroup. This allows the delta to be expressed against any parent,
  which can result in smaller deltas and more efficient encoding of data.
  </p>
  <h2>Changeset Segment</h2>
  <p>
  The *changeset segment* consists of a single *delta group* holding
  changelog data. The *empty chunk* at the end of the *delta group* denotes
  the boundary to the *manifest segment*.
  </p>
  <h2>Manifest Segment</h2>
  <p>
  The *manifest segment* consists of a single *delta group* holding manifest
  data. If treemanifests are in use, it contains only the manifest for the
  root directory of the repository. Otherwise, it contains the entire
  manifest data. The *empty chunk* at the end of the *delta group* denotes
  the boundary to the next segment (either the *treemanifests segment* or the
  *filelogs segment*, depending on version and the request options).
  </p>
  <h3>Treemanifests Segment</h3>
  <p>
  The *treemanifests segment* only exists in changegroup version &quot;3&quot;, and
  only if the 'treemanifest' param is part of the bundle2 changegroup part
  (it is not possible to use changegroup version 3 outside of bundle2).
  Aside from the filenames in the *treemanifests segment* containing a
  trailing &quot;/&quot; character, it behaves identically to the *filelogs segment*
  (see below). The final sub-segment is followed by an *empty chunk* (logically,
  a sub-segment with filename size 0). This denotes the boundary to the
  *filelogs segment*.
  </p>
  <h2>Filelogs Segment</h2>
  <p>
  The *filelogs segment* consists of multiple sub-segments, each
  corresponding to an individual file whose data is being described:
  </p>
  <pre>
  +--------------------------------------------------+
  |          |          |          |     |           |
  | filelog0 | filelog1 | filelog2 | ... |    0x0    |
  |          |          |          |     | (4 bytes) |
  |          |          |          |     |           |
  +--------------------------------------------------+
  </pre>
  <p>
  The final filelog sub-segment is followed by an *empty chunk* (logically,
  a sub-segment with filename size 0). This denotes the end of the segment
  and of the overall changegroup.
  </p>
  <p>
  Each filelog sub-segment consists of the following:
  </p>
  <pre>
  +------------------------------------------------------+
  |                 |                      |             |
  | filename length |       filename       | delta group |
  |    (4 bytes)    | (&lt;length - 4&gt; bytes) |  (various)  |
  |                 |                      |             |
  +------------------------------------------------------+
  </pre>
  <p>
  That is, a *chunk* consisting of the filename (not terminated or padded)
  followed by N chunks constituting the *delta group* for this file. The
  *empty chunk* at the end of each *delta group* denotes the boundary to the
  next filelog sub-segment.
  </p>
  
  </div>
  </div>
  </div>
  
  
  
  </body>
  </html>
  

  $ killdaemons.py

#endif
