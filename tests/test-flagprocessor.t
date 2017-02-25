# Create server
  $ hg init server
  $ cd server
  $ cat >> .hg/hgrc << EOF
  > [extensions]
  > extension=$TESTDIR/flagprocessorext.py
  > EOF
  $ cd ../

# Clone server and enable extensions
  $ hg clone -q server client
  $ cd client
  $ cat >> .hg/hgrc << EOF
  > [extensions]
  > extension=$TESTDIR/flagprocessorext.py
  > EOF

# Commit file that will trigger the noop extension
  $ echo '[NOOP]' > noop
  $ hg commit -Aqm "noop"

# Commit file that will trigger the base64 extension
  $ echo '[BASE64]' > base64
  $ hg commit -Aqm 'base64'

# Commit file that will trigger the gzip extension
  $ echo '[GZIP]' > gzip
  $ hg commit -Aqm 'gzip'

# Commit file that will trigger noop and base64
  $ echo '[NOOP][BASE64]' > noop-base64
  $ hg commit -Aqm 'noop+base64'

# Commit file that will trigger noop and gzip
  $ echo '[NOOP][GZIP]' > noop-gzip
  $ hg commit -Aqm 'noop+gzip'

# Commit file that will trigger base64 and gzip
  $ echo '[BASE64][GZIP]' > base64-gzip
  $ hg commit -Aqm 'base64+gzip'

# Commit file that will trigger base64, gzip and noop
  $ echo '[BASE64][GZIP][NOOP]' > base64-gzip-noop
  $ hg commit -Aqm 'base64+gzip+noop'

# TEST: ensure the revision data is consistent
  $ hg cat noop
  [NOOP]
  $ hg debugdata noop 0
  [NOOP]

  $ hg cat -r . base64
  [BASE64]
  $ hg debugdata base64 0
  W0JBU0U2NF0K (no-eol)

  $ hg cat -r . gzip
  [GZIP]
  $ hg debugdata gzip 0
  x\x9c\x8bv\x8f\xf2\x0c\x88\xe5\x02\x00\x08\xc8\x01\xfd (no-eol) (esc)

  $ hg cat -r . noop-base64
  [NOOP][BASE64]
  $ hg debugdata noop-base64 0
  W05PT1BdW0JBU0U2NF0K (no-eol)

  $ hg cat -r . noop-gzip
  [NOOP][GZIP]
  $ hg debugdata noop-gzip 0
  x\x9c\x8b\xf6\xf3\xf7\x0f\x88\x8dv\x8f\xf2\x0c\x88\xe5\x02\x00\x1dH\x03\xf1 (no-eol) (esc)

  $ hg cat -r . base64-gzip
  [BASE64][GZIP]
  $ hg debugdata base64-gzip 0
  eJyLdnIMdjUziY12j/IMiOUCACLBBDo= (no-eol)

  $ hg cat -r . base64-gzip-noop
  [BASE64][GZIP][NOOP]
  $ hg debugdata base64-gzip-noop 0
  eJyLdnIMdjUziY12j/IMiI328/cPiOUCAESjBi4= (no-eol)

# Push to the server
  $ hg push
  pushing to $TESTTMP/server (glob)
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 7 changesets with 7 changes to 7 files

# Initialize new client (not cloning) and setup extension
  $ cd ..
  $ hg init client2
  $ cd client2
  $ cat >> .hg/hgrc << EOF
  > [paths]
  > default = $TESTTMP/server
  > [extensions]
  > extension=$TESTDIR/flagprocessorext.py
  > EOF

# Pull from server and update to latest revision
  $ hg pull default
  pulling from $TESTTMP/server (glob)
  requesting all changes
  adding changesets
  adding manifests
  adding file changes
  added 7 changesets with 7 changes to 7 files
  (run 'hg update' to get a working copy)
  $ hg update
  7 files updated, 0 files merged, 0 files removed, 0 files unresolved

# TEST: ensure the revision data is consistent
  $ hg cat noop
  [NOOP]
  $ hg debugdata noop 0
  [NOOP]

  $ hg cat -r . base64
  [BASE64]
  $ hg debugdata base64 0
  W0JBU0U2NF0K (no-eol)

  $ hg cat -r . gzip
  [GZIP]
  $ hg debugdata gzip 0
  x\x9c\x8bv\x8f\xf2\x0c\x88\xe5\x02\x00\x08\xc8\x01\xfd (no-eol) (esc)

  $ hg cat -r . noop-base64
  [NOOP][BASE64]
  $ hg debugdata noop-base64 0
  W05PT1BdW0JBU0U2NF0K (no-eol)

  $ hg cat -r . noop-gzip
  [NOOP][GZIP]
  $ hg debugdata noop-gzip 0
  x\x9c\x8b\xf6\xf3\xf7\x0f\x88\x8dv\x8f\xf2\x0c\x88\xe5\x02\x00\x1dH\x03\xf1 (no-eol) (esc)

  $ hg cat -r . base64-gzip
  [BASE64][GZIP]
  $ hg debugdata base64-gzip 0
  eJyLdnIMdjUziY12j/IMiOUCACLBBDo= (no-eol)

  $ hg cat -r . base64-gzip-noop
  [BASE64][GZIP][NOOP]
  $ hg debugdata base64-gzip-noop 0
  eJyLdnIMdjUziY12j/IMiI328/cPiOUCAESjBi4= (no-eol)

# TEST: ensure a missing processor is handled
  $ echo '[FAIL][BASE64][GZIP][NOOP]' > fail-base64-gzip-noop
  $ hg commit -Aqm 'fail+base64+gzip+noop'
  abort: missing processor for flag '0x1'!
  [255]

# TEST: ensure we cannot register several flag processors on the same flag
  $ cat >> .hg/hgrc << EOF
  > [extensions]
  > extension=$TESTDIR/flagprocessorext.py
  > duplicate=$TESTDIR/flagprocessorext.py
  > EOF
  $ echo 'this should fail' > file
  $ hg commit -Aqm 'add file'
  abort: cannot register multiple processors on flag '0x8'.
  [255]
