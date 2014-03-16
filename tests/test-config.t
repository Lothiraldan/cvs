hide outer repo
  $ hg init

Invalid syntax: no value

  $ cat > .hg/hgrc << EOF
  > novaluekey
  > EOF
  $ hg showconfig
  hg: parse error at $TESTTMP/.hg/hgrc:1: novaluekey
  [255]

Invalid syntax: no key

  $ cat > .hg/hgrc << EOF
  > =nokeyvalue
  > EOF
  $ hg showconfig
  hg: parse error at $TESTTMP/.hg/hgrc:1: =nokeyvalue
  [255]

Test hint about invalid syntax from leading white space

  $ cat > .hg/hgrc << EOF
  >  key=value
  > EOF
  $ hg showconfig
  hg: parse error at $TESTTMP/.hg/hgrc:1:  key=value
  unexpected leading whitespace
  [255]

  $ cat > .hg/hgrc << EOF
  >  [section]
  > key=value
  > EOF
  $ hg showconfig
  hg: parse error at $TESTTMP/.hg/hgrc:1:  [section]
  unexpected leading whitespace
  [255]

Reset hgrc

  $ echo > .hg/hgrc

Test case sensitive configuration

  $ echo '[Section]' >> $HGRCPATH
  $ echo 'KeY = Case Sensitive' >> $HGRCPATH
  $ echo 'key = lower case' >> $HGRCPATH

  $ hg showconfig Section
  Section.KeY=Case Sensitive
  Section.key=lower case

Test "%unset"

  $ cat >> $HGRCPATH <<EOF
  > [unsettest]
  > local-hgrcpath = should be unset (HGRCPATH)
  > %unset local-hgrcpath
  > 
  > global = should be unset (HGRCPATH)
  > 
  > both = should be unset (HGRCPATH)
  > 
  > set-after-unset = should be unset (HGRCPATH)
  > EOF

  $ cat >> .hg/hgrc <<EOF
  > [unsettest]
  > local-hgrc = should be unset (.hg/hgrc)
  > %unset local-hgrc
  > 
  > %unset global
  > 
  > both = should be unset (.hg/hgrc)
  > %unset both
  > 
  > set-after-unset = should be unset (.hg/hgrc)
  > %unset set-after-unset
  > set-after-unset = should be set (.hg/hgrc)
  > EOF

  $ hg showconfig unsettest
  unsettest.set-after-unset=should be set (.hg/hgrc)
