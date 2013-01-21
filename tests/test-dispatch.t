test command parsing and dispatch

  $ hg init a
  $ cd a

Redundant options used to crash (issue436):
  $ hg -v log -v
  $ hg -v log -v x

  $ echo a > a
  $ hg ci -Ama
  adding a

Missing arg:

  $ hg cat
  hg cat: invalid arguments
  hg cat [OPTION]... FILE...
  
  output the current or given revision of files
  
  options:
  
   -o --output FORMAT       print output to file with formatted name
   -r --rev REV             print the given revision
      --decode              apply any matching decode filter
   -I --include PATTERN [+] include names matching the given patterns
   -X --exclude PATTERN [+] exclude names matching the given patterns
  
  [+] marked option can be specified multiple times
  
  use "hg help cat" to show the full help text
  [255]

[defaults]

  $ hg cat a
  a
  $ cat >> $HGRCPATH <<EOF
  > [defaults]
  > cat = -r null
  > EOF
  $ hg cat a
  a: no such file in rev 000000000000
  [1]

  $ cd "$TESTTMP"

OSError ... and with filename even when it is empty

  $ hg -R a archive ''
  abort: No such file or directory: ''
  [255]

#if no-outer-repo

No repo:

  $ hg cat
  abort: no repository found in '$TESTTMP' (.hg not found)!
  [255]

#endif
