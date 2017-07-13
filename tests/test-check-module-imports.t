#require test-repo

  $ . "$TESTDIR/helpers-testrepo.sh"
  $ import_checker="$TESTDIR"/../contrib/import-checker.py

  $ cd "$TESTDIR"/..

There are a handful of cases here that require renaming a module so it
doesn't overlap with a stdlib module name. There are also some cycles
here that we should still endeavor to fix, and some cycles will be
hidden by deduplication algorithm in the cycle detector, so fixing
these may expose other cycles.

Known-bad files are excluded by -X as some of them would produce unstable
outputs, which should be fixed later.

  $ testrepohg locate 'set:**.py or grep(r"^#!.*?python")' \
  > 'tests/**.t' \
  > -X contrib/debugshell.py \
  > -X contrib/python-zstandard/ \
  > -X contrib/win32/hgwebdir_wsgi.py \
  > -X doc/gendoc.py \
  > -X doc/hgmanpage.py \
  > -X i18n/posplit \
  > -X tests/test-hgweb-auth.py \
  > -X tests/hypothesishelpers.py \
  > -X tests/test-lock.py \
  > -X tests/test-verify-repo-operations.py \
  > -X tests/test-hook.t \
  > -X tests/test-import.t \
  > -X tests/test-imports-checker.t \
  > -X tests/test-commit-interactive.t \
  > -X tests/test-contrib-check-code.t \
  > -X tests/test-extension.t \
  > -X tests/test-hghave.t \
  > -X tests/test-hgweb-no-path-info.t \
  > -X tests/test-hgweb-no-request-uri.t \
  > -X tests/test-hgweb-non-interactive.t \
  > | sed 's-\\-/-g' | $PYTHON "$import_checker" -
