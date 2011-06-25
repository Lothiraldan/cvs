  $ hg init t
  $ cd t
  $ echo a > a
  $ hg add a
  $ hg commit -m test
  $ rm .hg/requires
  $ hg tip
  abort: index 00changelog.i unknown format 2!
  [255]
  $ echo indoor-pool > .hg/requires
  $ hg tip
  abort: unknown repository format: requires features 'indoor-pool' (upgrade Mercurial)!
  (see http://mercurial.selenic.com/wiki/MissingRequirement for details)
  [255]
  $ echo outdoor-pool >> .hg/requires
  $ hg tip
  abort: unknown repository format: requires features 'indoor-pool', 'outdoor-pool' (upgrade Mercurial)!
  (see http://mercurial.selenic.com/wiki/MissingRequirement for details)
  [255]
  $ cd ..

Test checking between features supported locally and ones required in
another repository of push/pull/clone on localhost:

  $ mkdir supported-locally
  $ cd supported-locally

  $ hg init supported
  $ echo a > supported/a
  $ hg -R supported commit -Am '#0 at supported'
  adding a

  $ echo 'featuresetup-test' >> supported/.hg/requires
  $ cat > $TESTTMP/supported-locally/supportlocally.py <<EOF
  > from mercurial import localrepo, extensions
  > def featuresetup(ui, supported):
  >     for name, module in extensions.extensions(ui):
  >         if __name__ == module.__name__:
  >             # support specific feature locally
  >             supported |= set(['featuresetup-test'])
  >             return
  > def uisetup(ui):
  >     localrepo.localrepository.featuresetupfuncs.add(featuresetup)
  > EOF
  $ cat > supported/.hg/hgrc <<EOF
  > [extensions]
  > # enable extension locally
  > supportlocally = $TESTTMP/supported-locally/supportlocally.py
  > EOF
  $ hg -R supported status

  $ hg init push-dst
  $ hg -R supported push push-dst
  pushing to push-dst
  abort: required features are not supported in the destination: featuresetup-test
  [255]

  $ hg init pull-src
  $ hg -R pull-src pull supported
  pulling from supported
  abort: required features are not supported in the destination: featuresetup-test
  [255]

  $ hg clone supported clone-dst
  abort: unknown repository format: requires features 'featuresetup-test' (upgrade Mercurial)!
  (see http://mercurial.selenic.com/wiki/MissingRequirement for details)
  [255]
  $ hg clone --pull supported clone-dst
  abort: required features are not supported in the destination: featuresetup-test
  [255]

  $ cd ..
