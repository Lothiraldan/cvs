  $ check_code="$TESTDIR"/../contrib/check-code.py
  $ cd "$TESTDIR"/..
  $ if hg identify -q > /dev/null; then :
  > else
  >     echo "skipped: not a Mercurial working dir" >&2
  >     exit 80
  > fi

New errors are not allowed. Warnings are strongly discouraged.

  $ hg manifest | xargs "$check_code" --warnings --nolineno --per-file=0 \
  > || false
  tests/test-serve.t:0:
   >   >        kill `cat hg.pid`
   don't use kill, use killdaemons.py
  tests/test-serve.t:0:
   >   >        kill `cat hg.pid` 2>/dev/null
   don't use kill, use killdaemons.py
  [1]
