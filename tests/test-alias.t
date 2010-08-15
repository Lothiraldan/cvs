  $ cat >> $HGRCPATH <<EOF
  > [alias]
  > myinit = init
  > cleanstatus = status -c
  > unknown = bargle
  > ambiguous = s
  > recursive = recursive
  > nodefinition =
  > no--cwd = status --cwd elsewhere
  > no-R = status -R elsewhere
  > no--repo = status --repo elsewhere
  > no--repository = status --repository elsewhere
  > mylog = log
  > lognull = log -r null
  > shortlog = log --template '{rev} {node|short} | {date|isodate}\n'
  > dln = lognull --debug
  > nousage = rollback
  > put = export -r 0 -o "\$FOO/%R.diff"
  > echo = !echo
  > rt = root
  > 
  > [defaults]
  > mylog = -q
  > lognull = -q
  > log = -v
  > EOF


basic

  $ hg myinit alias


unknown

  $ hg unknown
  alias 'unknown' resolves to unknown command 'bargle'
  $ hg help unknown
  alias 'unknown' resolves to unknown command 'bargle'


ambiguous

  $ hg ambiguous
  alias 'ambiguous' resolves to ambiguous command 's'
  $ hg help ambiguous
  alias 'ambiguous' resolves to ambiguous command 's'


recursive

  $ hg recursive
  alias 'recursive' resolves to unknown command 'recursive'
  $ hg help recursive
  alias 'recursive' resolves to unknown command 'recursive'


no definition

  $ hg nodef
  no definition for alias 'nodefinition'
  $ hg help nodef
  no definition for alias 'nodefinition'


invalid options

  $ hg no--cwd
  error in definition for alias 'no--cwd': --cwd may only be given on the command line
  $ hg help no--cwd
  error in definition for alias 'no--cwd': --cwd may only be given on the command line
  $ hg no-R
  error in definition for alias 'no-R': -R may only be given on the command line
  $ hg help no-R
  error in definition for alias 'no-R': -R may only be given on the command line
  $ hg no--repo
  error in definition for alias 'no--repo': --repo may only be given on the command line
  $ hg help no--repo
  error in definition for alias 'no--repo': --repo may only be given on the command line
  $ hg no--repository
  error in definition for alias 'no--repository': --repository may only be given on the command line
  $ hg help no--repository
  error in definition for alias 'no--repository': --repository may only be given on the command line

  $ cd alias


no usage

  $ hg nousage
  no rollback information available

  $ echo foo > foo
  $ hg ci -Amfoo
  adding foo


with opts

  $ hg cleanst
  C foo


with opts and whitespace

  $ hg shortlog
  0 e63c23eaa88a | 1970-01-01 00:00 +0000


interaction with defaults

  $ hg mylog
  0:e63c23eaa88a
  $ hg lognull
  -1:000000000000


properly recursive

  $ hg dln
  changeset:   -1:0000000000000000000000000000000000000000
  parent:      -1:0000000000000000000000000000000000000000
  parent:      -1:0000000000000000000000000000000000000000
  manifest:    -1:0000000000000000000000000000000000000000
  user:        
  date:        Thu Jan 01 00:00:00 1970 +0000
  extra:       branch=default
  


path expanding

  $ FOO=`pwd` hg put
  $ cat 0.diff
  # HG changeset patch
  # User test
  # Date 0 0
  # Node ID e63c23eaa88ae77967edcf4ea194d31167c478b0
  # Parent  0000000000000000000000000000000000000000
  foo
  
  diff -r 000000000000 -r e63c23eaa88a foo
  --- /dev/null	Thu Jan 01 00:00:00 1970 +0000
  +++ b/foo	Thu Jan 01 00:00:00 1970 +0000
  @@ -0,0 +1,1 @@
  +foo


shell aliases

  $ hg echo foo
  foo

invalid arguments

  $ hg rt foo
  hg rt: invalid arguments
  hg rt 
  
  alias for: hg root
  
  print the root (top) of the current working directory
  
      Print the root directory of the current repository.
  
      Returns 0 on success.
  
  use "hg -v help rt" to show global options

  $ exit 0
