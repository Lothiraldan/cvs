  (see "hg help phases" for details)
  $ touch .hg/patches/2.diff
  abort: patch "2.diff" already exists
  [255]
  3.diff
  $ rm .hg/patches/2.diff
  popping 3.diff
  popping 2.diff
  $ hg qdel 3.diff
  $ hg qdel -k 2.diff
  $ hg qimport -e 2.diff
  adding 2.diff to series file
  $ hg qdel -k 2.diff
  $ hg qimport -e --name this-name-is-better 2.diff
  renaming 2.diff to this-name-is-better
  $ "$TESTDIR/killdaemons.py" $DAEMON_PIDS