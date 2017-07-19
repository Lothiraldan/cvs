  $ hg init repo
  $ cd repo
  $ echo a > a
  $ hg add a
  $ hg commit -m test

Do we ever miss a sub-second change?:

  $ for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  >     hg co -qC 0
  >     echo b > a
  >     hg st
  > done
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a
  M a

  $ echo test > b
  $ mkdir dir1
  $ echo test > dir1/c
  $ echo test > d

  $ echo test > e
#if execbit
A directory will typically have the execute bit -- make sure it doesn't get
confused with a file with the exec bit set
  $ chmod +x e
#endif

  $ hg add b dir1 d e
  adding dir1/c (glob)
  $ hg commit -m test2

  $ cat >> $TESTTMP/dirstaterace.py << EOF
  > from mercurial import (
  >     context,
  >     extensions,
  > )
  > def extsetup():
  >     extensions.wrapfunction(context.workingctx, '_checklookup', overridechecklookup)
  > def overridechecklookup(orig, self, files):
  >     # make an update that changes the dirstate from underneath
  >     self._repo.ui.system(r"sh '$TESTTMP/dirstaterace.sh'",
  >                          cwd=self._repo.root)
  >     return orig(self, files)
  > EOF

  $ hg debugrebuilddirstate
  $ hg debugdirstate
  n   0         -1 unset               a
  n   0         -1 unset               b
  n   0         -1 unset               d
  n   0         -1 unset               dir1/c
  n   0         -1 unset               e

XXX Note that this returns M for files that got replaced by directories. This is
definitely a bug, but the fix for that is hard and the next status run is fine
anyway.

  $ cat > $TESTTMP/dirstaterace.sh <<EOF
  > rm b && rm -r dir1 && rm d && mkdir d && rm e && mkdir e
  > EOF

  $ hg status --config extensions.dirstaterace=$TESTTMP/dirstaterace.py
  M d
  M e
  ! b
  ! dir1/c
  $ hg debugdirstate
  n 644          2 * a (glob)
  n   0         -1 unset               b
  n   0         -1 unset               d
  n   0         -1 unset               dir1/c
  n   0         -1 unset               e

  $ hg status
  ! b
  ! d
  ! dir1/c
  ! e

  $ rmdir d e
  $ hg update -C -q .

Test that dirstate changes aren't written out at the end of "hg
status", if .hg/dirstate is already changed simultaneously before
acquisition of wlock in workingctx._poststatusfixup().

This avoidance is important to keep consistency of dirstate in race
condition (see issue5584 for detail).

  $ hg parents -q
  1:* (glob)

  $ hg debugrebuilddirstate
  $ hg debugdirstate
  n   0         -1 unset               a
  n   0         -1 unset               b
  n   0         -1 unset               d
  n   0         -1 unset               dir1/c
  n   0         -1 unset               e

  $ cat > $TESTTMP/dirstaterace.sh <<EOF
  > # This script assumes timetable of typical issue5584 case below:
  > #
  > # 1. "hg status" loads .hg/dirstate
  > # 2. "hg status" confirms clean-ness of FILE
  > # 3. "hg update -C 0" updates the working directory simultaneously
  > #    (FILE is removed, and FILE is dropped from .hg/dirstate)
  > # 4. "hg status" acquires wlock
  > #    (.hg/dirstate is re-loaded = no FILE entry in dirstate)
  > # 5. "hg status" marks FILE in dirstate as clean
  > #    (FILE entry is added to in-memory dirstate)
  > # 6. "hg status" writes dirstate changes into .hg/dirstate
  > #    (FILE entry is written into .hg/dirstate)
  > #
  > # To reproduce similar situation easily and certainly, #2 and #3
  > # are swapped.  "hg cat" below ensures #2 on "hg status" side.
  > 
  > hg update -q -C 0
  > hg cat -r 1 b > b
  > EOF

"hg status" below should excludes "e", of which exec flag is set, for
portability of test scenario, because unsure but missing "e" is
treated differently in _checklookup() according to runtime platform.

- "missing(!)" on POSIX, "pctx[f].cmp(self[f])" raises ENOENT
- "modified(M)" on Windows, "self.flags(f) != pctx.flags(f)" is True

  $ hg status --config extensions.dirstaterace=$TESTTMP/dirstaterace.py --debug -X path:e
  skip updating dirstate: identity mismatch
  M a
  ! d
  ! dir1/c

  $ hg parents -q
  0:* (glob)
  $ hg files
  a
  $ hg debugdirstate
  n * * * a (glob)

  $ rm b

#if fsmonitor

Create fsmonitor state.

  $ hg status
  $ f --type .hg/fsmonitor.state
  .hg/fsmonitor.state: file

Test that invalidating fsmonitor state in the middle (which doesn't require the
wlock) causes the fsmonitor update to be skipped.
hg debugrebuilddirstate ensures that the dirstaterace hook will be called, but
it also invalidates the fsmonitor state. So back it up and restore it.

  $ mv .hg/fsmonitor.state .hg/fsmonitor.state.tmp
  $ hg debugrebuilddirstate
  $ mv .hg/fsmonitor.state.tmp .hg/fsmonitor.state

  $ cat > $TESTTMP/dirstaterace.sh <<EOF
  > rm .hg/fsmonitor.state
  > EOF

  $ hg status --config extensions.dirstaterace=$TESTTMP/dirstaterace.py --debug
  skip updating fsmonitor.state: identity mismatch
  $ f .hg/fsmonitor.state
  .hg/fsmonitor.state: file not found

#endif

Set up a rebase situation for issue5581.

  $ echo c2 > a
  $ echo c2 > b
  $ hg add b
  $ hg commit -m c2
  created new head
  $ echo c3 >> a
  $ hg commit -m c3
  $ hg update 2
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo c4 >> a
  $ echo c4 >> b
  $ hg commit -m c4
  created new head

Configure a merge tool that runs status in the middle of the rebase.

  $ cat >> $TESTTMP/mergetool-race.sh << EOF
  > echo "custom merge tool"
  > printf "c2\nc3\nc4\n" > \$1
  > hg --cwd "$TESTTMP/repo" status
  > echo "custom merge tool end"
  > EOF
  $ cat >> $HGRCPATH << EOF
  > [extensions]
  > rebase =
  > [merge-tools]
  > test.executable=sh
  > test.args=$TESTTMP/mergetool-race.sh \$output
  > EOF

BROKEN: the "M b" line should not be there
  $ hg rebase -s . -d 3 --tool test
  rebasing 4:b08445fd6b2a "c4" (tip)
  merging a
  custom merge tool
  M a
  M b
  ? a.orig
  custom merge tool end
  saved backup bundle to $TESTTMP/repo/.hg/strip-backup/* (glob)

This hg status should be empty, whether or not fsmonitor is enabled (issue5581).

  $ hg status
