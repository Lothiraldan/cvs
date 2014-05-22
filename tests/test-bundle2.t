
Create an extension to test bundle2 API

  $ cat > bundle2.py << EOF
  > """A small extension to test bundle2 implementation
  > 
  > Current bundle2 implementation is far too limited to be used in any core
  > code. We still need to be able to test it while it grow up.
  > """
  > 
  > try:
  >     import msvcrt
  >     msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
  >     msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
  >     msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
  > except ImportError:
  >     pass
  > 
  > import sys
  > from mercurial import cmdutil
  > from mercurial import util
  > from mercurial import bundle2
  > from mercurial import scmutil
  > from mercurial import discovery
  > from mercurial import changegroup
  > from mercurial import error
  > cmdtable = {}
  > command = cmdutil.command(cmdtable)
  > 
  > ELEPHANTSSONG = """Patali Dirapata, Cromda Cromda Ripalo, Pata Pata, Ko Ko Ko
  > Bokoro Dipoulito, Rondi Rondi Pepino, Pata Pata, Ko Ko Ko
  > Emana Karassoli, Loucra Loucra Ponponto, Pata Pata, Ko Ko Ko."""
  > assert len(ELEPHANTSSONG) == 178 # future test say 178 bytes, trust it.
  > 
  > @bundle2.parthandler('test:song')
  > def songhandler(op, part):
  >     """handle a "test:song" bundle2 part, printing the lyrics on stdin"""
  >     op.ui.write('The choir starts singing:\n')
  >     verses = 0
  >     for line in part.read().split('\n'):
  >         op.ui.write('    %s\n' % line)
  >         verses += 1
  >     op.records.add('song', {'verses': verses})
  > 
  > @bundle2.parthandler('test:ping')
  > def pinghandler(op, part):
  >     op.ui.write('received ping request (id %i)\n' % part.id)
  >     if op.reply is not None and 'ping-pong' in op.reply.capabilities:
  >         op.ui.write_err('replying to ping request (id %i)\n' % part.id)
  >         op.reply.newpart('test:pong', [('in-reply-to', str(part.id))])
  > 
  > @bundle2.parthandler('test:debugreply')
  > def debugreply(op, part):
  >     """print data about the capacity of the bundle reply"""
  >     if op.reply is None:
  >         op.ui.write('debugreply: no reply\n')
  >     else:
  >         op.ui.write('debugreply: capabilities:\n')
  >         for cap in sorted(op.reply.capabilities):
  >             op.ui.write('debugreply:     %r\n' % cap)
  >             for val in op.reply.capabilities[cap]:
  >                 op.ui.write('debugreply:         %r\n' % val)
  > 
  > @command('bundle2',
  >          [('', 'param', [], 'stream level parameter'),
  >           ('', 'unknown', False, 'include an unknown mandatory part in the bundle'),
  >           ('', 'parts', False, 'include some arbitrary parts to the bundle'),
  >           ('', 'reply', False, 'produce a reply bundle'),
  >           ('', 'pushrace', False, 'includes a check:head part with unknown nodes'),
  >           ('r', 'rev', [], 'includes those changeset in the bundle'),],
  >          '[OUTPUTFILE]')
  > def cmdbundle2(ui, repo, path=None, **opts):
  >     """write a bundle2 container on standard ouput"""
  >     bundler = bundle2.bundle20(ui)
  >     for p in opts['param']:
  >         p = p.split('=', 1)
  >         try:
  >             bundler.addparam(*p)
  >         except ValueError, exc:
  >             raise util.Abort('%s' % exc)
  > 
  >     if opts['reply']:
  >         capsstring = 'ping-pong\nelephants=babar,celeste\ncity%3D%21=celeste%2Cville'
  >         bundler.newpart('b2x:replycaps', data=capsstring)
  > 
  >     if opts['pushrace']:
  >         # also serve to test the assignement of data outside of init
  >         part = bundler.newpart('b2x:check:heads')
  >         part.data = '01234567890123456789'
  > 
  >     revs = opts['rev']
  >     if 'rev' in opts:
  >         revs = scmutil.revrange(repo, opts['rev'])
  >         if revs:
  >             # very crude version of a changegroup part creation
  >             bundled = repo.revs('%ld::%ld', revs, revs)
  >             headmissing = [c.node() for c in repo.set('heads(%ld)', revs)]
  >             headcommon  = [c.node() for c in repo.set('parents(%ld) - %ld', revs, revs)]
  >             outgoing = discovery.outgoing(repo.changelog, headcommon, headmissing)
  >             cg = changegroup.getlocalbundle(repo, 'test:bundle2', outgoing, None)
  >             bundler.newpart('b2x:changegroup', data=cg.getchunks())
  > 
  >     if opts['parts']:
  >        bundler.newpart('test:empty')
  >        # add a second one to make sure we handle multiple parts
  >        bundler.newpart('test:empty')
  >        bundler.newpart('test:song', data=ELEPHANTSSONG)
  >        bundler.newpart('test:debugreply')
  >        bundler.newpart('test:math',
  >                                  [('pi', '3.14'), ('e', '2.72')],
  >                                  [('cooking', 'raw')],
  >                                  '42')
  >     if opts['unknown']:
  >        bundler.newpart('test:UNKNOWN', data='some random content')
  >     if opts['parts']:
  >        bundler.newpart('test:ping')
  > 
  >     if path is None:
  >        file = sys.stdout
  >     else:
  >         file = open(path, 'w')
  > 
  >     for chunk in bundler.getchunks():
  >         file.write(chunk)
  > 
  > @command('unbundle2', [], '')
  > def cmdunbundle2(ui, repo, replypath=None):
  >     """process a bundle2 stream from stdin on the current repo"""
  >     try:
  >         tr = None
  >         lock = repo.lock()
  >         tr = repo.transaction('processbundle')
  >         try:
  >             unbundler = bundle2.unbundle20(ui, sys.stdin)
  >             op = bundle2.processbundle(repo, unbundler, lambda: tr)
  >             tr.close()
  >         except KeyError, exc:
  >             raise util.Abort('missing support for %s' % exc)
  >         except error.PushRaced, exc:
  >             raise util.Abort('push race: %s' % exc)
  >     finally:
  >         if tr is not None:
  >             tr.release()
  >         lock.release()
  >         remains = sys.stdin.read()
  >         ui.write('%i unread bytes\n' % len(remains))
  >     if op.records['song']:
  >         totalverses = sum(r['verses'] for r in op.records['song'])
  >         ui.write('%i total verses sung\n' % totalverses)
  >     for rec in op.records['changegroup']:
  >         ui.write('addchangegroup return: %i\n' % rec['return'])
  >     if op.reply is not None and replypath is not None:
  >         file = open(replypath, 'w')
  >         for chunk in op.reply.getchunks():
  >             file.write(chunk)
  > 
  > @command('statbundle2', [], '')
  > def cmdstatbundle2(ui, repo):
  >     """print statistic on the bundle2 container read from stdin"""
  >     unbundler = bundle2.unbundle20(ui, sys.stdin)
  >     try:
  >         params = unbundler.params
  >     except KeyError, exc:
  >        raise util.Abort('unknown parameters: %s' % exc)
  >     ui.write('options count: %i\n' % len(params))
  >     for key in sorted(params):
  >         ui.write('- %s\n' % key)
  >         value = params[key]
  >         if value is not None:
  >             ui.write('    %s\n' % value)
  >     count = 0
  >     for p in unbundler.iterparts():
  >         count += 1
  >         ui.write('  :%s:\n' % p.type)
  >         ui.write('    mandatory: %i\n' % len(p.mandatoryparams))
  >         ui.write('    advisory: %i\n' % len(p.advisoryparams))
  >         ui.write('    payload: %i bytes\n' % len(p.read()))
  >     ui.write('parts count:   %i\n' % count)
  > EOF
  $ cat >> $HGRCPATH << EOF
  > [extensions]
  > bundle2=$TESTTMP/bundle2.py
  > [experimental]
  > bundle2-exp=True
  > [ui]
  > ssh=python "$TESTDIR/dummyssh"
  > [web]
  > push_ssl = false
  > allow_push = *
  > EOF

The extension requires a repo (currently unused)

  $ hg init main
  $ cd main
  $ touch a
  $ hg add a
  $ hg commit -m 'a'


Empty bundle
=================

- no option
- no parts

Test bundling

  $ hg bundle2
  HG2X\x00\x00\x00\x00 (no-eol) (esc)

Test unbundling

  $ hg bundle2 | hg statbundle2
  options count: 0
  parts count:   0

Test old style bundle are detected and refused

  $ hg bundle --all ../bundle.hg
  1 changesets found
  $ hg statbundle2 < ../bundle.hg
  abort: unknown bundle version 10
  [255]

Test parameters
=================

- some options
- no parts

advisory parameters, no value
-------------------------------

Simplest possible parameters form

Test generation simple option

  $ hg bundle2 --param 'caution'
  HG2X\x00\x07caution\x00\x00 (no-eol) (esc)

Test unbundling

  $ hg bundle2 --param 'caution' | hg statbundle2
  options count: 1
  - caution
  parts count:   0

Test generation multiple option

  $ hg bundle2 --param 'caution' --param 'meal'
  HG2X\x00\x0ccaution meal\x00\x00 (no-eol) (esc)

Test unbundling

  $ hg bundle2 --param 'caution' --param 'meal' | hg statbundle2
  options count: 2
  - caution
  - meal
  parts count:   0

advisory parameters, with value
-------------------------------

Test generation

  $ hg bundle2 --param 'caution' --param 'meal=vegan' --param 'elephants'
  HG2X\x00\x1ccaution meal=vegan elephants\x00\x00 (no-eol) (esc)

Test unbundling

  $ hg bundle2 --param 'caution' --param 'meal=vegan' --param 'elephants' | hg statbundle2
  options count: 3
  - caution
  - elephants
  - meal
      vegan
  parts count:   0

parameter with special char in value
---------------------------------------------------

Test generation

  $ hg bundle2 --param 'e|! 7/=babar%#==tutu' --param simple
  HG2X\x00)e%7C%21%207/=babar%25%23%3D%3Dtutu simple\x00\x00 (no-eol) (esc)

Test unbundling

  $ hg bundle2 --param 'e|! 7/=babar%#==tutu' --param simple | hg statbundle2
  options count: 2
  - e|! 7/
      babar%#==tutu
  - simple
  parts count:   0

Test unknown mandatory option
---------------------------------------------------

  $ hg bundle2 --param 'Gravity' | hg statbundle2
  abort: unknown parameters: 'Gravity'
  [255]

Test debug output
---------------------------------------------------

bundling debug

  $ hg bundle2 --debug --param 'e|! 7/=babar%#==tutu' --param simple ../out.hg2
  start emission of HG2X stream
  bundle parameter: e%7C%21%207/=babar%25%23%3D%3Dtutu simple
  start of parts
  end of bundle

file content is ok

  $ cat ../out.hg2
  HG2X\x00)e%7C%21%207/=babar%25%23%3D%3Dtutu simple\x00\x00 (no-eol) (esc)

unbundling debug

  $ hg statbundle2 --debug < ../out.hg2
  start processing of HG2X stream
  reading bundle2 stream parameters
  ignoring unknown parameter 'e|! 7/'
  ignoring unknown parameter 'simple'
  options count: 2
  - e|! 7/
      babar%#==tutu
  - simple
  start extraction of bundle2 parts
  part header size: 0
  end of bundle2 stream
  parts count:   0


Test buggy input
---------------------------------------------------

empty parameter name

  $ hg bundle2 --param '' --quiet
  abort: empty parameter name
  [255]

bad parameter name

  $ hg bundle2 --param 42babar
  abort: non letter first character: '42babar'
  [255]


Test part
=================

  $ hg bundle2 --parts ../parts.hg2 --debug
  start emission of HG2X stream
  bundle parameter: 
  start of parts
  bundle part: "test:empty"
  bundle part: "test:empty"
  bundle part: "test:song"
  bundle part: "test:debugreply"
  bundle part: "test:math"
  bundle part: "test:ping"
  end of bundle

  $ cat ../parts.hg2
  HG2X\x00\x00\x00\x11 (esc)
  test:empty\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x11 (esc)
  test:empty\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x10	test:song\x00\x00\x00\x02\x00\x00\x00\x00\x00\xb2Patali Dirapata, Cromda Cromda Ripalo, Pata Pata, Ko Ko Ko (esc)
  Bokoro Dipoulito, Rondi Rondi Pepino, Pata Pata, Ko Ko Ko
  Emana Karassoli, Loucra Loucra Ponponto, Pata Pata, Ko Ko Ko.\x00\x00\x00\x00\x00\x16\x0ftest:debugreply\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00+	test:math\x00\x00\x00\x04\x02\x01\x02\x04\x01\x04\x07\x03pi3.14e2.72cookingraw\x00\x00\x00\x0242\x00\x00\x00\x00\x00\x10	test:ping\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00 (no-eol) (esc)


  $ hg statbundle2 < ../parts.hg2
  options count: 0
    :test:empty:
      mandatory: 0
      advisory: 0
      payload: 0 bytes
    :test:empty:
      mandatory: 0
      advisory: 0
      payload: 0 bytes
    :test:song:
      mandatory: 0
      advisory: 0
      payload: 178 bytes
    :test:debugreply:
      mandatory: 0
      advisory: 0
      payload: 0 bytes
    :test:math:
      mandatory: 2
      advisory: 1
      payload: 2 bytes
    :test:ping:
      mandatory: 0
      advisory: 0
      payload: 0 bytes
  parts count:   6

  $ hg statbundle2 --debug < ../parts.hg2
  start processing of HG2X stream
  reading bundle2 stream parameters
  options count: 0
  start extraction of bundle2 parts
  part header size: 17
  part type: "test:empty"
  part id: "0"
  part parameters: 0
    :test:empty:
      mandatory: 0
      advisory: 0
  payload chunk size: 0
      payload: 0 bytes
  part header size: 17
  part type: "test:empty"
  part id: "1"
  part parameters: 0
    :test:empty:
      mandatory: 0
      advisory: 0
  payload chunk size: 0
      payload: 0 bytes
  part header size: 16
  part type: "test:song"
  part id: "2"
  part parameters: 0
    :test:song:
      mandatory: 0
      advisory: 0
  payload chunk size: 178
  payload chunk size: 0
      payload: 178 bytes
  part header size: 22
  part type: "test:debugreply"
  part id: "3"
  part parameters: 0
    :test:debugreply:
      mandatory: 0
      advisory: 0
  payload chunk size: 0
      payload: 0 bytes
  part header size: 43
  part type: "test:math"
  part id: "4"
  part parameters: 3
    :test:math:
      mandatory: 2
      advisory: 1
  payload chunk size: 2
  payload chunk size: 0
      payload: 2 bytes
  part header size: 16
  part type: "test:ping"
  part id: "5"
  part parameters: 0
    :test:ping:
      mandatory: 0
      advisory: 0
  payload chunk size: 0
      payload: 0 bytes
  part header size: 0
  end of bundle2 stream
  parts count:   6

Test actual unbundling of test part
=======================================

Process the bundle

  $ hg unbundle2 --debug < ../parts.hg2
  start processing of HG2X stream
  reading bundle2 stream parameters
  start extraction of bundle2 parts
  part header size: 17
  part type: "test:empty"
  part id: "0"
  part parameters: 0
  ignoring unknown advisory part 'test:empty'
  payload chunk size: 0
  part header size: 17
  part type: "test:empty"
  part id: "1"
  part parameters: 0
  ignoring unknown advisory part 'test:empty'
  payload chunk size: 0
  part header size: 16
  part type: "test:song"
  part id: "2"
  part parameters: 0
  found a handler for part 'test:song'
  The choir starts singing:
  payload chunk size: 178
  payload chunk size: 0
      Patali Dirapata, Cromda Cromda Ripalo, Pata Pata, Ko Ko Ko
      Bokoro Dipoulito, Rondi Rondi Pepino, Pata Pata, Ko Ko Ko
      Emana Karassoli, Loucra Loucra Ponponto, Pata Pata, Ko Ko Ko.
  part header size: 22
  part type: "test:debugreply"
  part id: "3"
  part parameters: 0
  found a handler for part 'test:debugreply'
  debugreply: no reply
  payload chunk size: 0
  part header size: 43
  part type: "test:math"
  part id: "4"
  part parameters: 3
  ignoring unknown advisory part 'test:math'
  payload chunk size: 2
  payload chunk size: 0
  part header size: 16
  part type: "test:ping"
  part id: "5"
  part parameters: 0
  found a handler for part 'test:ping'
  received ping request (id 5)
  payload chunk size: 0
  part header size: 0
  end of bundle2 stream
  0 unread bytes
  3 total verses sung

Unbundle with an unknown mandatory part
(should abort)

  $ hg bundle2 --parts --unknown ../unknown.hg2

  $ hg unbundle2 < ../unknown.hg2
  The choir starts singing:
      Patali Dirapata, Cromda Cromda Ripalo, Pata Pata, Ko Ko Ko
      Bokoro Dipoulito, Rondi Rondi Pepino, Pata Pata, Ko Ko Ko
      Emana Karassoli, Loucra Loucra Ponponto, Pata Pata, Ko Ko Ko.
  debugreply: no reply
  0 unread bytes
  abort: missing support for 'test:unknown'
  [255]

unbundle with a reply

  $ hg bundle2 --parts --reply ../parts-reply.hg2
  $ hg unbundle2 ../reply.hg2 < ../parts-reply.hg2
  0 unread bytes
  3 total verses sung

The reply is a bundle

  $ cat ../reply.hg2
  HG2X\x00\x00\x00\x1f (esc)
  b2x:output\x00\x00\x00\x00\x00\x01\x0b\x01in-reply-to3\x00\x00\x00\xd9The choir starts singing: (esc)
      Patali Dirapata, Cromda Cromda Ripalo, Pata Pata, Ko Ko Ko
      Bokoro Dipoulito, Rondi Rondi Pepino, Pata Pata, Ko Ko Ko
      Emana Karassoli, Loucra Loucra Ponponto, Pata Pata, Ko Ko Ko.
  \x00\x00\x00\x00\x00\x1f (esc)
  b2x:output\x00\x00\x00\x01\x00\x01\x0b\x01in-reply-to4\x00\x00\x00\xc9debugreply: capabilities: (esc)
  debugreply:     'city=!'
  debugreply:         'celeste,ville'
  debugreply:     'elephants'
  debugreply:         'babar'
  debugreply:         'celeste'
  debugreply:     'ping-pong'
  \x00\x00\x00\x00\x00\x1e	test:pong\x00\x00\x00\x02\x01\x00\x0b\x01in-reply-to6\x00\x00\x00\x00\x00\x1f (esc)
  b2x:output\x00\x00\x00\x03\x00\x01\x0b\x01in-reply-to6\x00\x00\x00=received ping request (id 6) (esc)
  replying to ping request (id 6)
  \x00\x00\x00\x00\x00\x00 (no-eol) (esc)

The reply is valid

  $ hg statbundle2 < ../reply.hg2
  options count: 0
    :b2x:output:
      mandatory: 0
      advisory: 1
      payload: 217 bytes
    :b2x:output:
      mandatory: 0
      advisory: 1
      payload: 201 bytes
    :test:pong:
      mandatory: 1
      advisory: 0
      payload: 0 bytes
    :b2x:output:
      mandatory: 0
      advisory: 1
      payload: 61 bytes
  parts count:   4

Unbundle the reply to get the output:

  $ hg unbundle2 < ../reply.hg2
  remote: The choir starts singing:
  remote:     Patali Dirapata, Cromda Cromda Ripalo, Pata Pata, Ko Ko Ko
  remote:     Bokoro Dipoulito, Rondi Rondi Pepino, Pata Pata, Ko Ko Ko
  remote:     Emana Karassoli, Loucra Loucra Ponponto, Pata Pata, Ko Ko Ko.
  remote: debugreply: capabilities:
  remote: debugreply:     'city=!'
  remote: debugreply:         'celeste,ville'
  remote: debugreply:     'elephants'
  remote: debugreply:         'babar'
  remote: debugreply:         'celeste'
  remote: debugreply:     'ping-pong'
  remote: received ping request (id 6)
  remote: replying to ping request (id 6)
  0 unread bytes

Test push race detection

  $ hg bundle2 --pushrace ../part-race.hg2

  $ hg unbundle2 < ../part-race.hg2
  0 unread bytes
  abort: push race: repository changed while pushing - please try again
  [255]

Support for changegroup
===================================

  $ hg unbundle $TESTDIR/bundles/rebase.hg
  adding changesets
  adding manifests
  adding file changes
  added 8 changesets with 7 changes to 7 files (+3 heads)
  (run 'hg heads' to see heads, 'hg merge' to merge)

  $ hg log -G
  o  changeset:   8:02de42196ebe
  |  tag:         tip
  |  parent:      6:24b6387c8c8c
  |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  |  date:        Sat Apr 30 15:24:48 2011 +0200
  |  summary:     H
  |
  | o  changeset:   7:eea13746799a
  |/|  parent:      6:24b6387c8c8c
  | |  parent:      5:9520eea781bc
  | |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  | |  date:        Sat Apr 30 15:24:48 2011 +0200
  | |  summary:     G
  | |
  o |  changeset:   6:24b6387c8c8c
  | |  parent:      1:cd010b8cd998
  | |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  | |  date:        Sat Apr 30 15:24:48 2011 +0200
  | |  summary:     F
  | |
  | o  changeset:   5:9520eea781bc
  |/   parent:      1:cd010b8cd998
  |    user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  |    date:        Sat Apr 30 15:24:48 2011 +0200
  |    summary:     E
  |
  | o  changeset:   4:32af7686d403
  | |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  | |  date:        Sat Apr 30 15:24:48 2011 +0200
  | |  summary:     D
  | |
  | o  changeset:   3:5fddd98957c8
  | |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  | |  date:        Sat Apr 30 15:24:48 2011 +0200
  | |  summary:     C
  | |
  | o  changeset:   2:42ccdea3bb16
  |/   user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  |    date:        Sat Apr 30 15:24:48 2011 +0200
  |    summary:     B
  |
  o  changeset:   1:cd010b8cd998
     parent:      -1:000000000000
     user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
     date:        Sat Apr 30 15:24:48 2011 +0200
     summary:     A
  
  @  changeset:   0:3903775176ed
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  

  $ hg bundle2 --debug --rev '8+7+5+4' ../rev.hg2
  4 changesets found
  list of changesets:
  32af7686d403cf45b5d95f2d70cebea587ac806a
  9520eea781bcca16c1e15acc0ba14335a0e8e5ba
  eea13746799a9e0bfd88f29d3c2e9dc9389f524f
  02de42196ebee42ef284b6780a87cdc96e8eaab6
  start emission of HG2X stream
  bundle parameter: 
  start of parts
  bundle part: "b2x:changegroup"
  bundling: 1/4 changesets (25.00%)
  bundling: 2/4 changesets (50.00%)
  bundling: 3/4 changesets (75.00%)
  bundling: 4/4 changesets (100.00%)
  bundling: 1/4 manifests (25.00%)
  bundling: 2/4 manifests (50.00%)
  bundling: 3/4 manifests (75.00%)
  bundling: 4/4 manifests (100.00%)
  bundling: D 1/3 files (33.33%)
  bundling: E 2/3 files (66.67%)
  bundling: H 3/3 files (100.00%)
  end of bundle

  $ cat ../rev.hg2
  HG2X\x00\x00\x00\x16\x0fb2x:changegroup\x00\x00\x00\x00\x00\x00\x00\x00\x06\x13\x00\x00\x00\xa42\xafv\x86\xd4\x03\xcfE\xb5\xd9_-p\xce\xbe\xa5\x87\xac\x80j_\xdd\xd9\x89W\xc8\xa5JMCm\xfe\x1d\xa9\xd8\x7f!\xa1\xb9{\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x002\xafv\x86\xd4\x03\xcfE\xb5\xd9_-p\xce\xbe\xa5\x87\xac\x80j\x00\x00\x00\x00\x00\x00\x00)\x00\x00\x00)6e1f4c47ecb533ffd0c8e52cdc88afb6cd39e20c (esc)
  \x00\x00\x00f\x00\x00\x00h\x00\x00\x00\x02D (esc)
  \x00\x00\x00i\x00\x00\x00j\x00\x00\x00\x01D\x00\x00\x00\xa4\x95 \xee\xa7\x81\xbc\xca\x16\xc1\xe1Z\xcc\x0b\xa1C5\xa0\xe8\xe5\xba\xcd\x01\x0b\x8c\xd9\x98\xf3\x98\x1aZ\x81\x15\xf9O\x8d\xa4\xabP`\x89\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x95 \xee\xa7\x81\xbc\xca\x16\xc1\xe1Z\xcc\x0b\xa1C5\xa0\xe8\xe5\xba\x00\x00\x00\x00\x00\x00\x00)\x00\x00\x00)4dece9c826f69490507b98c6383a3009b295837d (esc)
  \x00\x00\x00f\x00\x00\x00h\x00\x00\x00\x02E (esc)
  \x00\x00\x00i\x00\x00\x00j\x00\x00\x00\x01E\x00\x00\x00\xa2\xee\xa17Fy\x9a\x9e\x0b\xfd\x88\xf2\x9d<.\x9d\xc98\x9fRO$\xb68|\x8c\x8c\xae7\x17\x88\x80\xf3\xfa\x95\xde\xd3\xcb\x1c\xf7\x85\x95 \xee\xa7\x81\xbc\xca\x16\xc1\xe1Z\xcc\x0b\xa1C5\xa0\xe8\xe5\xba\xee\xa17Fy\x9a\x9e\x0b\xfd\x88\xf2\x9d<.\x9d\xc98\x9fRO\x00\x00\x00\x00\x00\x00\x00)\x00\x00\x00)365b93d57fdf4814e2b5911d6bacff2b12014441 (esc)
  \x00\x00\x00f\x00\x00\x00h\x00\x00\x00\x00\x00\x00\x00i\x00\x00\x00j\x00\x00\x00\x01G\x00\x00\x00\xa4\x02\xdeB\x19n\xbe\xe4.\xf2\x84\xb6x (esc)
  \x87\xcd\xc9n\x8e\xaa\xb6$\xb68|\x8c\x8c\xae7\x17\x88\x80\xf3\xfa\x95\xde\xd3\xcb\x1c\xf7\x85\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\xdeB\x19n\xbe\xe4.\xf2\x84\xb6x (esc)
  \x87\xcd\xc9n\x8e\xaa\xb6\x00\x00\x00\x00\x00\x00\x00)\x00\x00\x00)8bee48edc7318541fc0013ee41b089276a8c24bf (esc)
  \x00\x00\x00f\x00\x00\x00f\x00\x00\x00\x02H (esc)
  \x00\x00\x00g\x00\x00\x00h\x00\x00\x00\x01H\x00\x00\x00\x00\x00\x00\x00\x8bn\x1fLG\xec\xb53\xff\xd0\xc8\xe5,\xdc\x88\xaf\xb6\xcd9\xe2\x0cf\xa5\xa0\x18\x17\xfd\xf5#\x9c'8\x02\xb5\xb7a\x8d\x05\x1c\x89\xe4\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x002\xafv\x86\xd4\x03\xcfE\xb5\xd9_-p\xce\xbe\xa5\x87\xac\x80j\x00\x00\x00\x81\x00\x00\x00\x81\x00\x00\x00+D\x00c3f1ca2924c16a19b0656a84900e504e5b0aec2d (esc)
  \x00\x00\x00\x8bM\xec\xe9\xc8&\xf6\x94\x90P{\x98\xc68:0	\xb2\x95\x83}\x00}\x8c\x9d\x88\x84\x13%\xf5\xc6\xb0cq\xb3[N\x8a+\x1a\x83\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x95 \xee\xa7\x81\xbc\xca\x16\xc1\xe1Z\xcc\x0b\xa1C5\xa0\xe8\xe5\xba\x00\x00\x00+\x00\x00\x00\xac\x00\x00\x00+E\x009c6fd0350a6c0d0c49d4a9c5017cf07043f54e58 (esc)
  \x00\x00\x00\x8b6[\x93\xd5\x7f\xdfH\x14\xe2\xb5\x91\x1dk\xac\xff+\x12\x01DA(\xa5\x84\xc6^\xf1!\xf8\x9e\xb6j\xb7\xd0\xbc\x15=\x80\x99\xe7\xceM\xec\xe9\xc8&\xf6\x94\x90P{\x98\xc68:0	\xb2\x95\x83}\xee\xa17Fy\x9a\x9e\x0b\xfd\x88\xf2\x9d<.\x9d\xc98\x9fRO\x00\x00\x00V\x00\x00\x00V\x00\x00\x00+F\x0022bfcfd62a21a3287edbd4d656218d0f525ed76a (esc)
  \x00\x00\x00\x97\x8b\xeeH\xed\xc71\x85A\xfc\x00\x13\xeeA\xb0\x89'j\x8c$\xbf(\xa5\x84\xc6^\xf1!\xf8\x9e\xb6j\xb7\xd0\xbc\x15=\x80\x99\xe7\xce\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\xdeB\x19n\xbe\xe4.\xf2\x84\xb6x (esc)
  \x87\xcd\xc9n\x8e\xaa\xb6\x00\x00\x00+\x00\x00\x00V\x00\x00\x00\x00\x00\x00\x00\x81\x00\x00\x00\x81\x00\x00\x00+H\x008500189e74a9e0475e822093bc7db0d631aeb0b4 (esc)
  \x00\x00\x00\x00\x00\x00\x00\x05D\x00\x00\x00b\xc3\xf1\xca)$\xc1j\x19\xb0ej\x84\x90\x0ePN[ (esc)
  \xec-\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x002\xafv\x86\xd4\x03\xcfE\xb5\xd9_-p\xce\xbe\xa5\x87\xac\x80j\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02D (esc)
  \x00\x00\x00\x00\x00\x00\x00\x05E\x00\x00\x00b\x9co\xd05 (esc)
  l\r (no-eol) (esc)
  \x0cI\xd4\xa9\xc5\x01|\xf0pC\xf5NX\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x95 \xee\xa7\x81\xbc\xca\x16\xc1\xe1Z\xcc\x0b\xa1C5\xa0\xe8\xe5\xba\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02E (esc)
  \x00\x00\x00\x00\x00\x00\x00\x05H\x00\x00\x00b\x85\x00\x18\x9et\xa9\xe0G^\x82 \x93\xbc}\xb0\xd61\xae\xb0\xb4\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\xdeB\x19n\xbe\xe4.\xf2\x84\xb6x (esc)
  \x87\xcd\xc9n\x8e\xaa\xb6\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02H (esc)
  \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 (no-eol) (esc)

  $ hg unbundle2 < ../rev.hg2
  adding changesets
  adding manifests
  adding file changes
  added 0 changesets with 0 changes to 3 files
  0 unread bytes
  addchangegroup return: 1

with reply

  $ hg bundle2 --rev '8+7+5+4' --reply ../rev-rr.hg2
  $ hg unbundle2 ../rev-reply.hg2 < ../rev-rr.hg2
  0 unread bytes
  addchangegroup return: 1

  $ cat ../rev-reply.hg2
  HG2X\x00\x00\x003\x15b2x:reply:changegroup\x00\x00\x00\x00\x00\x02\x0b\x01\x06\x01in-reply-to1return1\x00\x00\x00\x00\x00\x1f (esc)
  b2x:output\x00\x00\x00\x01\x00\x01\x0b\x01in-reply-to1\x00\x00\x00dadding changesets (esc)
  adding manifests
  adding file changes
  added 0 changesets with 0 changes to 3 files
  \x00\x00\x00\x00\x00\x00 (no-eol) (esc)

Real world exchange
=====================


clone --pull

  $ cd ..
  $ hg clone main other --pull --rev 9520eea781bc
  adding changesets
  adding manifests
  adding file changes
  added 2 changesets with 2 changes to 2 files
  updating to branch default
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg -R other log -G
  @  changeset:   1:9520eea781bc
  |  tag:         tip
  |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  |  date:        Sat Apr 30 15:24:48 2011 +0200
  |  summary:     E
  |
  o  changeset:   0:cd010b8cd998
     user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
     date:        Sat Apr 30 15:24:48 2011 +0200
     summary:     A
  

pull

  $ hg -R other pull -r 24b6387c8c8c
  pulling from $TESTTMP/main (glob)
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files (+1 heads)
  (run 'hg heads' to see heads, 'hg merge' to merge)

pull empty

  $ hg -R other pull -r 24b6387c8c8c
  pulling from $TESTTMP/main (glob)
  no changes found

push

  $ hg -R main push other --rev eea13746799a
  pushing to other
  searching for changes
  remote: adding changesets
  remote: adding manifests
  remote: adding file changes
  remote: added 1 changesets with 0 changes to 0 files (-1 heads)

pull over ssh

  $ hg -R other pull ssh://user@dummy/main -r 02de42196ebe --traceback
  pulling from ssh://user@dummy/main
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files (+1 heads)
  (run 'hg heads' to see heads, 'hg merge' to merge)

pull over http

  $ hg -R main serve -p $HGPORT -d --pid-file=main.pid -E main-error.log
  $ cat main.pid >> $DAEMON_PIDS

  $ hg -R other pull http://localhost:$HGPORT/ -r 42ccdea3bb16
  pulling from http://localhost:$HGPORT/
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files (+1 heads)
  (run 'hg heads .' to see heads, 'hg merge' to merge)
  $ cat main-error.log

push over ssh

  $ hg -R main push ssh://user@dummy/other -r 5fddd98957c8
  pushing to ssh://user@dummy/other
  searching for changes
  remote: adding changesets
  remote: adding manifests
  remote: adding file changes
  remote: added 1 changesets with 1 changes to 1 files

push over http

  $ hg -R other serve -p $HGPORT2 -d --pid-file=other.pid -E other-error.log
  $ cat other.pid >> $DAEMON_PIDS

  $ hg -R main push http://localhost:$HGPORT2/ -r 32af7686d403
  pushing to http://localhost:$HGPORT2/
  searching for changes
  remote: adding changesets
  remote: adding manifests
  remote: adding file changes
  remote: added 1 changesets with 1 changes to 1 files
  $ cat other-error.log

Check final content.

  $ hg -R other log -G
  o  changeset:   7:32af7686d403
  |  tag:         tip
  |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  |  date:        Sat Apr 30 15:24:48 2011 +0200
  |  summary:     D
  |
  o  changeset:   6:5fddd98957c8
  |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  |  date:        Sat Apr 30 15:24:48 2011 +0200
  |  summary:     C
  |
  o  changeset:   5:42ccdea3bb16
  |  parent:      0:cd010b8cd998
  |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  |  date:        Sat Apr 30 15:24:48 2011 +0200
  |  summary:     B
  |
  | o  changeset:   4:02de42196ebe
  | |  parent:      2:24b6387c8c8c
  | |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  | |  date:        Sat Apr 30 15:24:48 2011 +0200
  | |  summary:     H
  | |
  | | o  changeset:   3:eea13746799a
  | |/|  parent:      2:24b6387c8c8c
  | | |  parent:      1:9520eea781bc
  | | |  user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  | | |  date:        Sat Apr 30 15:24:48 2011 +0200
  | | |  summary:     G
  | | |
  | o |  changeset:   2:24b6387c8c8c
  |/ /   parent:      0:cd010b8cd998
  | |    user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  | |    date:        Sat Apr 30 15:24:48 2011 +0200
  | |    summary:     F
  | |
  | @  changeset:   1:9520eea781bc
  |/   user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
  |    date:        Sat Apr 30 15:24:48 2011 +0200
  |    summary:     E
  |
  o  changeset:   0:cd010b8cd998
     user:        Nicolas Dumazet <nicdumz.commits@gmail.com>
     date:        Sat Apr 30 15:24:48 2011 +0200
     summary:     A
  

Error Handling
==============

Check that errors are properly returned to the client during push.

Setting up

  $ cat > failpush.py << EOF
  > """A small extension that makes push fails when using bundle2
  > 
  > used to test error handling in bundle2
  > """
  > 
  > from mercurial import util
  > from mercurial import bundle2
  > from mercurial import exchange
  > from mercurial import extensions
  > 
  > def _pushbundle2failpart(orig, pushop, bundler):
  >     extradata = orig(pushop, bundler)
  >     reason = pushop.ui.config('failpush', 'reason', None)
  >     part = None
  >     if reason == 'abort':
  >         bundler.newpart('test:abort')
  >     if reason == 'unknown':
  >         bundler.newpart('TEST:UNKNOWN')
  >     if reason == 'race':
  >         # 20 Bytes of crap
  >         bundler.newpart('b2x:check:heads', data='01234567890123456789')
  >     return extradata
  > 
  > @bundle2.parthandler("test:abort")
  > def handleabort(op, part):
  >     raise util.Abort('Abandon ship!', hint="don't panic")
  > 
  > def uisetup(ui):
  >     extensions.wrapfunction(exchange, '_pushbundle2extraparts', _pushbundle2failpart)
  > 
  > EOF

  $ cd main
  $ hg up tip
  3 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ echo 'I' > I
  $ hg add I
  $ hg ci -m 'I'
  $ hg id
  e7ec4e813ba6 tip
  $ cd ..

  $ cat << EOF >> $HGRCPATH
  > [extensions]
  > failpush=$TESTTMP/failpush.py
  > EOF

  $ "$TESTDIR/killdaemons.py" $DAEMON_PIDS
  $ hg -R other serve -p $HGPORT2 -d --pid-file=other.pid -E other-error.log
  $ cat other.pid >> $DAEMON_PIDS

Doing the actual push: Abort error

  $ cat << EOF >> $HGRCPATH
  > [failpush]
  > reason = abort
  > EOF

  $ hg -R main push other -r e7ec4e813ba6
  pushing to other
  searching for changes
  abort: Abandon ship!
  (don't panic)
  [255]

  $ hg -R main push ssh://user@dummy/other -r e7ec4e813ba6
  pushing to ssh://user@dummy/other
  searching for changes
  abort: Abandon ship!
  (don't panic)
  [255]

  $ hg -R main push http://localhost:$HGPORT2/ -r e7ec4e813ba6
  pushing to http://localhost:$HGPORT2/
  searching for changes
  abort: Abandon ship!
  (don't panic)
  [255]


Doing the actual push: unknown mandatory parts

  $ cat << EOF >> $HGRCPATH
  > [failpush]
  > reason = unknown
  > EOF

  $ hg -R main push other -r e7ec4e813ba6
  pushing to other
  searching for changes
  abort: missing support for 'test:unknown'
  [255]

  $ hg -R main push ssh://user@dummy/other -r e7ec4e813ba6
  pushing to ssh://user@dummy/other
  searching for changes
  abort: missing support for "'test:unknown'"
  [255]

  $ hg -R main push http://localhost:$HGPORT2/ -r e7ec4e813ba6
  pushing to http://localhost:$HGPORT2/
  searching for changes
  abort: missing support for "'test:unknown'"
  [255]

Doing the actual push: race

  $ cat << EOF >> $HGRCPATH
  > [failpush]
  > reason = race
  > EOF

  $ hg -R main push other -r e7ec4e813ba6
  pushing to other
  searching for changes
  abort: push failed:
  'repository changed while pushing - please try again'
  [255]

  $ hg -R main push ssh://user@dummy/other -r e7ec4e813ba6
  pushing to ssh://user@dummy/other
  searching for changes
  abort: push failed:
  'repository changed while pushing - please try again'
  [255]

  $ hg -R main push http://localhost:$HGPORT2/ -r e7ec4e813ba6
  pushing to http://localhost:$HGPORT2/
  searching for changes
  abort: push failed:
  'repository changed while pushing - please try again'
  [255]

Doing the actual push: hook abort

  $ cat << EOF >> $HGRCPATH
  > [failpush]
  > reason =
  > [hooks]
  > b2x-pretransactionclose.failpush = false
  > EOF

  $ "$TESTDIR/killdaemons.py" $DAEMON_PIDS
  $ hg -R other serve -p $HGPORT2 -d --pid-file=other.pid -E other-error.log
  $ cat other.pid >> $DAEMON_PIDS

  $ hg -R main push other -r e7ec4e813ba6
  pushing to other
  searching for changes
  transaction abort!
  rollback completed
  abort: b2x-pretransactionclose.failpush hook exited with status 1
  [255]

  $ hg -R main push ssh://user@dummy/other -r e7ec4e813ba6
  pushing to ssh://user@dummy/other
  searching for changes
  abort: b2x-pretransactionclose.failpush hook exited with status 1
  remote: transaction abort!
  remote: rollback completed
  [255]

  $ hg -R main push http://localhost:$HGPORT2/ -r e7ec4e813ba6
  pushing to http://localhost:$HGPORT2/
  searching for changes
  abort: b2x-pretransactionclose.failpush hook exited with status 1
  [255]


