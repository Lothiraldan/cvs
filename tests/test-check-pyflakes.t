#require test-repo pyflakes hg10

  $ . "$TESTDIR/helpers-testrepo.sh"
  $ cd "`dirname "$TESTDIR"`"

run pyflakes on all tracked files ending in .py or without a file ending
(skipping binary file random-seed)

  $ testrepohg locate 'set:**.py or grep("^#!.*python")' \
  > -X hgext/fsmonitor/pywatchman \
  > -X mercurial/pycompat.py -X contrib/python-zstandard \
  > 2>/dev/null \
  > | xargs pyflakes 2>/dev/null | "$TESTDIR/filterpyflakes.py"
  tests/filterpyflakes.py:41: undefined name 'undefinedname'
  
