#require test-repo

  $ cd "$TESTDIR"/..

New errors are not allowed. Warnings are strongly discouraged.

  $ hg files "set:(**.py or **.txt) - tests/**" | sed 's|\\|/|g' |
  >   xargs python contrib/check-config.py
  undocumented: convert.svn.debugsvnlog (bool) [True]
