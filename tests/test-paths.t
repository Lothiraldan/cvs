  $ hg init a
  $ hg clone a b
  updating to branch default
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd a
  $ echo '[paths]' >> .hg/hgrc
  $ echo 'dupe = ../b#tip' >> .hg/hgrc
  $ echo 'expand = $SOMETHING/bar' >> .hg/hgrc
  $ hg in dupe
  comparing with $TESTTMP/b (glob)
  no changes found
  [1]
  $ cd ..
  $ hg -R a in dupe
  comparing with $TESTTMP/b (glob)
  no changes found
  [1]
  $ cd a
  $ hg paths
  dupe = $TESTTMP/b#tip (glob)
  expand = $TESTTMP/a/$SOMETHING/bar (glob)
  $ SOMETHING=foo hg paths
  dupe = $TESTTMP/b#tip (glob)
  expand = $TESTTMP/a/foo/bar (glob)
#if msys
  $ SOMETHING=//foo hg paths
  dupe = $TESTTMP/b#tip (glob)
  expand = /foo/bar
#else
  $ SOMETHING=/foo hg paths
  dupe = $TESTTMP/b#tip (glob)
  expand = /foo/bar
#endif
  $ hg paths -q
  dupe
  expand
  $ hg paths dupe
  $TESTTMP/b#tip (glob)
  $ hg paths -q dupe
  $ hg paths unknown
  not found!
  [1]
  $ hg paths -q unknown
  [1]
  $ cd ..

sub-options for an undeclared path are ignored

  $ hg init suboptions
  $ cd suboptions

  $ cat > .hg/hgrc << EOF
  > [paths]
  > path0 = https://example.com/path0
  > path1:pushurl = https://example.com/path1
  > EOF
  $ hg paths
  path0 = https://example.com/path0

unknown sub-options aren't displayed

  $ cat > .hg/hgrc << EOF
  > [paths]
  > path0 = https://example.com/path0
  > path0:foo = https://example.com/path1
  > EOF

  $ hg paths
  path0 = https://example.com/path0

:pushurl must be a URL

  $ cat > .hg/hgrc << EOF
  > [paths]
  > default = /path/to/nothing
  > default:pushurl = /not/a/url
  > EOF

  $ hg paths
  (paths.default:pushurl not a URL; ignoring)
  default = /path/to/nothing

#fragment is not allowed in :pushurl

  $ cat > .hg/hgrc << EOF
  > [paths]
  > default = https://example.com/repo
  > invalid = https://example.com/repo
  > invalid:pushurl = https://example.com/repo#branch
  > EOF

  $ hg paths
  ("#fragment" in paths.invalid:pushurl not supported; ignoring)
  default = https://example.com/repo
  invalid = https://example.com/repo
  invalid:pushurl = https://example.com/repo

  $ cd ..

'file:' disables [paths] entries for clone destination

  $ cat >> $HGRCPATH <<EOF
  > [paths]
  > gpath1 = http://hg.example.com
  > EOF

  $ hg clone a gpath1
  abort: cannot create new http repository
  [255]

  $ hg clone a file:gpath1
  updating to branch default
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd gpath1
  $ hg -q id
  000000000000

  $ cd ..
