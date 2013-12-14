This code uses the ast module, which was new in 2.6, so we'll skip
this test on anything earlier.
  $ python -c 'import sys ; assert sys.version_info >= (2, 6)' || exit 80

Virtualenv has a habit of leaving BaseHTTPServer and other modules in
a place where the import checker is confused about their nature as
part of the stdlib. Skip the test if BaseHTTPServer's path isn't a
subpath of sys.prefix.

  $ python -c 'import sys, BaseHTTPServer; assert BaseHTTPServer.__file__.startswith(sys.prefix)' || exit 80

  $ import_checker="$TESTDIR"/../contrib/import-checker.py
Run the doctests from the import checker, and make sure
it's working correctly.
  $ TERM=dumb
  $ export TERM
  $ python -m doctest $import_checker

  $ cd "$TESTDIR"/..
  $ if hg identify -q > /dev/null 2>&1; then :
  > else
  >     echo "skipped: not a Mercurial working dir" >&2
  >     exit 80
  > fi

There are a handful of cases here that require renaming a module so it
doesn't overlap with a stdlib module name. There are also some cycles
here that we should still endeavor to fix, and some cycles will be
hidden by deduplication algorithm in the cycle detector, so fixing
these may expose other cycles.

  $ hg locate 'mercurial/**.py' | xargs python "$import_checker"
  mercurial/dispatch.py mixed stdlib and relative imports:
     commands, error, extensions, fancyopts, hg, hook, util
  mercurial/fileset.py mixed stdlib and relative imports:
     error, merge, parser, util
  mercurial/revset.py mixed stdlib and relative imports:
     discovery, error, hbisect, parser, phases, util
  mercurial/templater.py mixed stdlib and relative imports:
     config, error, parser, templatefilters, util
  mercurial/ui.py mixed stdlib and relative imports:
     config, error, formatter, scmutil, util
  Import cycle: mercurial.cmdutil -> mercurial.subrepo -> mercurial.cmdutil
  Import cycle: mercurial.repoview -> mercurial.revset -> mercurial.repoview
  Import cycle: mercurial.fileset -> mercurial.merge -> mercurial.subrepo -> mercurial.match -> mercurial.fileset
  Import cycle: mercurial.filemerge -> mercurial.match -> mercurial.fileset -> mercurial.merge -> mercurial.filemerge
