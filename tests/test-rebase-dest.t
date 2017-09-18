Require a destination
  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > rebase =
  > [commands]
  > rebase.requiredest = True
  > EOF
  $ hg init repo
  $ cd repo
  $ echo a >> a
  $ hg commit -qAm aa
  $ echo b >> b
  $ hg commit -qAm bb
  $ hg up ".^"
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ echo c >> c
  $ hg commit -qAm cc
  $ hg rebase
  abort: you must specify a destination
  (use: hg rebase -d REV)
  [255]
  $ hg rebase -d 1
  rebasing 2:5db65b93a12b "cc" (tip)
  saved backup bundle to $TESTTMP/repo/.hg/strip-backup/5db65b93a12b-4fb789ec-rebase.hg (glob)
  $ hg rebase -d 0 -r . -q
  $ HGPLAIN=1 hg rebase
  rebasing 2:889b0bc6a730 "cc" (tip)
  saved backup bundle to $TESTTMP/repo/.hg/strip-backup/889b0bc6a730-41ec4f81-rebase.hg (glob)
  $ hg rebase -d 0 -r . -q
  $ hg --config commands.rebase.requiredest=False rebase
  rebasing 2:279de9495438 "cc" (tip)
  saved backup bundle to $TESTTMP/repo/.hg/strip-backup/279de9495438-ab0a5128-rebase.hg (glob)

Requiring dest should not break continue or other rebase options
  $ hg up 1 -q
  $ echo d >> c
  $ hg commit -qAm dc
  $ hg log -G -T '{rev} {desc}'
  @  3 dc
  |
  | o  2 cc
  |/
  o  1 bb
  |
  o  0 aa
  
  $ hg rebase -d 2
  rebasing 3:0537f6b50def "dc" (tip)
  merging c
  warning: conflicts while merging c! (edit, then use 'hg resolve --mark')
  unresolved conflicts (see hg resolve, then hg rebase --continue)
  [1]
  $ echo d > c
  $ hg resolve --mark --all
  (no more unresolved files)
  continue: hg rebase --continue
  $ hg rebase --continue
  rebasing 3:0537f6b50def "dc" (tip)
  saved backup bundle to $TESTTMP/repo/.hg/strip-backup/0537f6b50def-be4c7386-rebase.hg (glob)

  $ cd ..

Check rebase.requiredest interaction with pull --rebase
  $ hg clone repo clone
  updating to branch default
  3 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd repo
  $ echo e > e
  $ hg commit -qAm ee
  $ cd ..
  $ cd clone
  $ echo f > f
  $ hg commit -qAm ff
  $ hg pull --rebase
  abort: rebase destination required by configuration
  (use hg pull followed by hg rebase -d DEST)
  [255]

Setup rebase with multiple destinations

  $ cd $TESTTMP

  $ cat >> $TESTTMP/maprevset.py <<EOF
  > from __future__ import absolute_import
  > from mercurial import registrar, revset, revsetlang, smartset
  > revsetpredicate = registrar.revsetpredicate()
  > cache = {}
  > @revsetpredicate('map')
  > def map(repo, subset, x):
  >     """(set, mapping)"""
  >     setarg, maparg = revsetlang.getargs(x, 2, 2, '')
  >     rset = revset.getset(repo, smartset.fullreposet(repo), setarg)
  >     mapstr = revsetlang.getstring(maparg, '')
  >     map = dict(a.split(':') for a in mapstr.split(','))
  >     rev = rset.first()
  >     desc = repo[rev].description()
  >     newdesc = map.get(desc)
  >     if newdesc == 'null':
  >         revs = [-1]
  >     else:
  >         query = revsetlang.formatspec('desc(%s)', newdesc)
  >         revs = repo.revs(query)
  >     return smartset.baseset(revs)
  > EOF

  $ cat >> $HGRCPATH <<EOF
  > [ui]
  > allowemptycommit=1
  > [extensions]
  > drawdag=$TESTDIR/drawdag.py
  > [phases]
  > publish=False
  > [alias]
  > tglog = log -G --template "{rev}: {desc} {instabilities}" -r 'sort(all(), topo)'
  > [extensions]
  > maprevset=$TESTTMP/maprevset.py
  > [experimental]
  > rebase.multidest=true
  > stabilization=all
  > EOF

  $ rebasewithdag() {
  >   N=`$PYTHON -c "print($N+1)"`
  >   hg init repo$N && cd repo$N
  >   hg debugdrawdag
  >   hg rebase "$@" > _rebasetmp
  >   r=$?
  >   grep -v 'saved backup bundle' _rebasetmp
  >   [ $r -eq 0 ] && rm -f .hg/localtags && hg tglog
  >   cd ..
  >   return $r
  > }

Destination resolves to an empty set:

  $ rebasewithdag -s B -d 'SRC - SRC' <<'EOS'
  > C
  > |
  > B
  > |
  > A
  > EOS
  nothing to rebase - empty destination
  [1]

Multiple destinations and --collapse are not compatible:

  $ rebasewithdag -s C+E -d 'SRC^^' --collapse <<'EOS'
  > C F
  > | |
  > B E
  > | |
  > A D
  > EOS
  abort: --collapse does not work with multiple destinations
  [255]

Multiple destinations cannot be used with --base:

  $ rebasewithdag -b B+E -d 'SRC^^' --collapse <<'EOS'
  > B E
  > | |
  > A D
  > EOS
  abort: unknown revision 'SRC'!
  [255]

Rebase to null should work:

  $ rebasewithdag -r A+C+D -d 'null' <<'EOS'
  > C D
  > | |
  > A B
  > EOS
  already rebased 0:426bada5c675 "A" (A)
  already rebased 2:dc0947a82db8 "C" (C)
  rebasing 3:004dc1679908 "D" (D tip)
  o  4: D
  
  o  2: C
  |
  | o  1: B
  |
  o  0: A
  
Destination resolves to multiple changesets:

  $ rebasewithdag -s B -d 'ALLSRC+SRC' <<'EOS'
  > C
  > |
  > B
  > |
  > Z
  > EOS
  abort: rebase destination for f0a671a46792 is not unique
  [255]

Destination is an ancestor of source:

  $ rebasewithdag -s B -d 'SRC' <<'EOS'
  > C
  > |
  > B
  > |
  > Z
  > EOS
  abort: source and destination form a cycle
  [255]

Switch roots:

  $ rebasewithdag -s 'all() - roots(all())' -d 'roots(all()) - ::SRC' <<'EOS'
  > C  F
  > |  |
  > B  E
  > |  |
  > A  D
  > EOS
  rebasing 2:112478962961 "B" (B)
  rebasing 4:26805aba1e60 "C" (C)
  rebasing 3:cd488e83d208 "E" (E)
  rebasing 5:0069ba24938a "F" (F tip)
  o  9: F
  |
  o  8: E
  |
  | o  7: C
  | |
  | o  6: B
  | |
  | o  1: D
  |
  o  0: A
  
Different destinations for merge changesets with a same root:

  $ rebasewithdag -s B -d '((parents(SRC)-B-A)::) - (::ALLSRC)' <<'EOS'
  > C G
  > |\|
  > | F
  > |
  > B E
  > |\|
  > A D
  > EOS
  rebasing 3:a4256619d830 "B" (B)
  rebasing 6:8e139e245220 "C" (C tip)
  o    8: C
  |\
  | o    7: B
  | |\
  o | |  5: G
  | | |
  | | o  4: E
  | | |
  o | |  2: F
   / /
  | o  1: D
  |
  o  0: A
  
Move to a previous parent:

  $ rebasewithdag -s E+F+G -d 'SRC^^' <<'EOS'
  >     H
  >     |
  >   D G
  >   |/
  >   C F
  >   |/
  >   B E  # E will be ignored, since E^^ is empty
  >   |/
  >   A
  > EOS
  rebasing 4:33441538d4aa "F" (F)
  rebasing 6:cf43ad9da869 "G" (G)
  rebasing 7:eef94f3b5f03 "H" (H tip)
  o  10: H
  |
  | o  5: D
  |/
  o  3: C
  |
  | o  9: G
  |/
  o  1: B
  |
  | o  8: F
  |/
  | o  2: E
  |/
  o  0: A
  
Source overlaps with destination:

  $ rebasewithdag -s 'B+C+D' -d 'map(SRC, "B:C,C:D")' <<'EOS'
  > B C D
  >  \|/
  >   A
  > EOS
  rebasing 2:dc0947a82db8 "C" (C)
  rebasing 1:112478962961 "B" (B)
  o  5: B
  |
  o  4: C
  |
  o  3: D
  |
  o  0: A
  
Detect cycles early:

  $ rebasewithdag -r 'all()-Z' -d 'map(SRC, "A:B,B:C,C:D,D:B")' <<'EOS'
  > A B C
  >  \|/
  >   | D
  >   |/
  >   Z
  > EOS
  abort: source and destination form a cycle
  [255]

Detect source is ancestor of dest in runtime:

  $ rebasewithdag -r 'C+B' -d 'map(SRC, "C:B,B:D")' -q <<'EOS'
  >   D
  >   |
  > B C
  >  \|
  >   A
  > EOS
  abort: source is ancestor of destination
  [255]

"Already rebased" fast path still works:

  $ rebasewithdag -r 'all()' -d 'SRC^' <<'EOS'
  >   E F
  >  /| |
  > B C D
  >  \|/
  >   A
  > EOS
  already rebased 1:112478962961 "B" (B)
  already rebased 2:dc0947a82db8 "C" (C)
  already rebased 3:b18e25de2cf5 "D" (D)
  already rebased 4:312782b8f06e "E" (E)
  already rebased 5:ad6717a6a58e "F" (F tip)
  o  5: F
  |
  o  3: D
  |
  | o    4: E
  | |\
  +---o  2: C
  | |
  | o  1: B
  |/
  o  0: A
  
Massively rewrite the DAG:

  $ rebasewithdag -r 'all()' -d 'map(SRC, "A:I,I:null,H:A,B:J,J:C,C:H,D:E,F:G,G:K,K:D,E:B")' <<'EOS'
  > D G K
  > | | |
  > C F J
  > | | |
  > B E I
  >  \| |
  >   A H
  > EOS
  rebasing 4:701514e1408d "I" (I)
  rebasing 0:426bada5c675 "A" (A)
  rebasing 1:e7050b6e5048 "H" (H)
  rebasing 5:26805aba1e60 "C" (C)
  rebasing 7:cf89f86b485b "J" (J)
  rebasing 2:112478962961 "B" (B)
  rebasing 3:7fb047a69f22 "E" (E)
  rebasing 8:f585351a92f8 "D" (D)
  rebasing 10:ae41898d7875 "K" (K tip)
  rebasing 9:711f53bbef0b "G" (G)
  rebasing 6:64a8289d2492 "F" (F)
  o  21: F
  |
  o  20: G
  |
  o  19: K
  |
  o  18: D
  |
  o  17: E
  |
  o  16: B
  |
  o  15: J
  |
  o  14: C
  |
  o  13: H
  |
  o  12: A
  |
  o  11: I
  
Resolve instability:

  $ rebasewithdag <<'EOF' -r 'orphan()-obsolete()' -d 'max((successors(max(roots(ALLSRC) & ::SRC)^)-obsolete())::)'
  >      F2
  >      |
  >    J E E2
  >    | |/
  > I2 I | E3
  >   \| |/
  >    H | G
  >    | | |
  >   B2 D F
  >    | |/         # rebase: B -> B2
  >    N C          # amend: E -> E2
  >    | |          # amend: E2 -> E3
  >    M B          # rebase: F -> F2
  >     \|          # amend: I -> I2
  >      A
  > EOF
  rebasing 16:5c432343bf59 "J" (J tip)
  rebasing 3:26805aba1e60 "C" (C)
  rebasing 6:f585351a92f8 "D" (D)
  rebasing 10:ffebc37c5d0b "E3" (E3)
  rebasing 13:fb184bcfeee8 "F2" (F2)
  rebasing 11:dc838ab4c0da "G" (G)
  o  22: G
  |
  o  21: F2
  |
  o  20: E3
  |
  o  19: D
  |
  o  18: C
  |
  o  17: J
  |
  o  15: I2
  |
  o  12: H
  |
  o  5: B2
  |
  o  4: N
  |
  o  2: M
  |
  o  0: A
  
