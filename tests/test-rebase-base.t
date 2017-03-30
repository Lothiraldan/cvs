  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > rebase=
  > drawdag=$TESTDIR/drawdag.py
  > 
  > [phases]
  > publish=False
  > 
  > [alias]
  > tglog = log -G --template "{rev}: {desc}"
  > EOF

  $ rebasewithdag() {
  >   N=`$PYTHON -c "print($N+1)"`
  >   hg init repo$N && cd repo$N
  >   hg debugdrawdag
  >   hg rebase "$@" > _rebasetmp
  >   r=$?
  >   grep -v 'saved backup bundle' _rebasetmp
  >   [ $r -eq 0 ] && hg tglog
  >   cd ..
  >   return $r
  > }

Single branching point, without merge:

  $ rebasewithdag -b D -d Z <<'EOS'
  >     D E
  >     |/
  > Z B C   # C: branching point, E should be picked
  >  \|/    # B should not be picked
  >   A
  >   |
  >   R
  > EOS
  rebasing 3:d6003a550c2c "C" (C)
  rebasing 5:4526cf523425 "D" (D)
  rebasing 6:b296604d9846 "E" (E tip)
  o  6: E
  |
  | o  5: D
  |/
  o  4: C
  |
  o  3: Z
  |
  | o  2: B
  |/
  o  1: A
  |
  o  0: R
  
Multiple branching points caused by selecting a single merge changeset:

  $ rebasewithdag -b E -d Z <<'EOS'
  >     E
  >    /|
  >   B C D  # B, C: multiple branching points
  >   | |/   # D should not be picked
  > Z | /
  >  \|/
  >   A
  >   |
  >   R
  > EOS
  rebasing 2:c1e6b162678d "B" (B)
  rebasing 3:d6003a550c2c "C" (C)
  rebasing 6:5251e0cb7302 "E" (E tip)
  o    6: E
  |\
  | o  5: C
  | |
  o |  4: B
  |/
  o  3: Z
  |
  | o  2: D
  |/
  o  1: A
  |
  o  0: R
  
Rebase should not extend the "--base" revset using "descendants":

  $ rebasewithdag -b B -d Z <<'EOS'
  >     E
  >    /|
  > Z B C  # descendants(B) = B+E. With E, C will be included incorrectly
  >  \|/
  >   A
  >   |
  >   R
  > EOS
  rebasing 2:c1e6b162678d "B" (B)
  rebasing 5:5251e0cb7302 "E" (E tip)
  o    5: E
  |\
  | o  4: B
  | |
  | o  3: Z
  | |
  o |  2: C
  |/
  o  1: A
  |
  o  0: R
  
Rebase should not simplify the "--base" revset using "roots":

  $ rebasewithdag -b B+E -d Z <<'EOS'
  >     E
  >    /|
  > Z B C  # roots(B+E) = B. Without E, C will be missed incorrectly
  >  \|/
  >   A
  >   |
  >   R
  > EOS
  rebasing 2:c1e6b162678d "B" (B)
  rebasing 3:d6003a550c2c "C" (C)
  rebasing 5:5251e0cb7302 "E" (E tip)
  o    5: E
  |\
  | o  4: C
  | |
  o |  3: B
  |/
  o  2: Z
  |
  o  1: A
  |
  o  0: R
  
The destination is one of the two branching points of a merge:

  $ rebasewithdag -b F -d Z <<'EOS'
  >     F
  >    / \
  >   E   D
  >  /   /
  > Z   C
  >  \ /
  >   B
  >   |
  >   A
  > EOS
  nothing to rebase
  [1]

Multiple branching points caused by multiple bases (issue5420):

  $ rebasewithdag -b E1+E2+C2+B1 -d Z <<'EOS'
  >   Z    E2
  >   |   /
  >   F E1 C2
  >   |/  /
  >   E C1 B2
  >   |/  /
  >   C B1
  >   |/
  >   B
  >   |
  >   A
  >   |
  >   R
  > EOS
  rebasing 3:a113dbaa660a "B1" (B1)
  rebasing 5:06ce7b1cc8c2 "B2" (B2)
  rebasing 6:0ac98cce32d3 "C1" (C1)
  rebasing 8:781512f5e33d "C2" (C2)
  rebasing 9:428d8c18f641 "E1" (E1)
  rebasing 11:e1bf82f6b6df "E2" (E2)
  o  12: E2
  |
  o  11: E1
  |
  | o  10: C2
  | |
  | o  9: C1
  |/
  | o  8: B2
  | |
  | o  7: B1
  |/
  o  6: Z
  |
  o  5: F
  |
  o  4: E
  |
  o  3: C
  |
  o  2: B
  |
  o  1: A
  |
  o  0: R
  
Multiple branching points with multiple merges:

  $ rebasewithdag -b G+P -d Z <<'EOS'
  > G   H   P
  > |\ /|   |\
  > F E D   M N
  >  \|/|  /| |\
  > Z C B I J K L
  >  \|/  |/  |/
  >   A   A   A
  > EOS
  rebasing 2:dc0947a82db8 "C" (C)
  rebasing 8:215e7b0814e1 "D" (D)
  rebasing 9:03ca77807e91 "E" (E)
  rebasing 10:afc707c82df0 "F" (F)
  rebasing 13:018caa673317 "G" (G)
  rebasing 14:4f710fbd68cb "H" (H)
  rebasing 3:08ebfeb61bac "I" (I)
  rebasing 4:a0a5005cec67 "J" (J)
  rebasing 5:83780307a7e8 "K" (K)
  rebasing 6:e131637a1cb6 "L" (L)
  rebasing 11:d6fe3d11d95d "M" (M)
  rebasing 12:fa1e02269063 "N" (N)
  rebasing 15:448b1a498430 "P" (P tip)
  o    15: P
  |\
  | o    14: N
  | |\
  o \ \    13: M
  |\ \ \
  | | | o  12: L
  | | | |
  | | o |  11: K
  | | |/
  | o /  10: J
  | |/
  o /  9: I
  |/
  | o    8: H
  | |\
  | | | o  7: G
  | | |/|
  | | | o  6: F
  | | | |
  | | o |  5: E
  | | |/
  | o |  4: D
  | |\|
  +---o  3: C
  | |
  o |  2: Z
  | |
  | o  1: B
  |/
  o  0: A
  
Slightly more complex merge case (mentioned in https://www.mercurial-scm.org/pipermail/mercurial-devel/2016-November/091074.html):

  $ rebasewithdag -b A3+B3 -d Z <<'EOF'
  > Z     C1    A3     B3
  > |    /     / \    / \
  > M3 C0     A1  A2 B1  B2
  > | /       |   |  |   |
  > M2        M1  C1 C1  M3
  > |
  > M1
  > |
  > M0
  > EOF
  rebasing 4:8817fae53c94 "C0" (C0)
  rebasing 6:06ca5dfe3b5b "B2" (B2)
  rebasing 7:73508237b032 "C1" (C1)
  rebasing 9:fdb955e2faed "A2" (A2)
  rebasing 11:1b2f368c3cb5 "A3" (A3)
  rebasing 10:0a33b0519128 "B1" (B1)
  rebasing 12:bd6a37b5b67a "B3" (B3 tip)
  o    12: B3
  |\
  | o  11: B1
  | |
  | | o    10: A3
  | | |\
  | +---o  9: A2
  | | |
  | o |  8: C1
  | | |
  o | |  7: B2
  | | |
  | o |  6: C0
  |/ /
  o |  5: Z
  | |
  o |  4: M3
  | |
  o |  3: M2
  | |
  | o  2: A1
  |/
  o  1: M1
  |
  o  0: M0
  
Mixed rebasable and non-rebasable bases (unresolved, issue5422):

  $ rebasewithdag -b C+D -d B <<'EOS'
  >   D
  >  /
  > B C
  > |/
  > A
  > EOS
  nothing to rebase
  [1]

Disconnected graph:

  $ rebasewithdag -b B -d Z <<'EOS'
  >   B
  >   |
  > Z A
  > EOS
  nothing to rebase from 112478962961 to 48b9aae0607f
  [1]

Multiple roots. Roots are ancestors of dest:

  $ rebasewithdag -b B+D -d Z <<'EOF'
  > D Z B
  >  \|\|
  >   C A
  > EOF
  rebasing 2:112478962961 "B" (B)
  rebasing 3:b70f76719894 "D" (D)
  o  4: D
  |
  | o  3: B
  |/
  o    2: Z
  |\
  | o  1: C
  |
  o  0: A
  
Multiple roots. One root is not an ancestor of dest:

  $ rebasewithdag -b B+D -d Z <<'EOF'
  > Z B D
  >  \|\|
  >   A C
  > EOF
  nothing to rebase from 86d01f49c0d9+b70f76719894 to 262e37e34f63
  [1]

Multiple roots. One root is not an ancestor of dest. Select using a merge:

  $ rebasewithdag -b E -d Z <<'EOF'
  >   E
  >   |\
  > Z B D
  >  \|\|
  >   A C
  > EOF
  rebasing 2:86d01f49c0d9 "B" (B)
  rebasing 5:539a0ff83ea9 "E" (E tip)
  o    5: E
  |\
  | o    4: B
  | |\
  | | o  3: Z
  | | |
  o | |  2: D
  |/ /
  o /  1: C
   /
  o  0: A
  
Multiple roots. Two children share two parents while dest has only one parent:

  $ rebasewithdag -b B+D -d Z <<'EOF'
  > Z B D
  >  \|\|\
  >   A C A
  > EOF
  rebasing 2:86d01f49c0d9 "B" (B)
  rebasing 3:b7df2ca01aa8 "D" (D)
  o    4: D
  |\
  +---o  3: B
  | |/
  | o  2: Z
  | |
  o |  1: C
   /
  o  0: A
  
