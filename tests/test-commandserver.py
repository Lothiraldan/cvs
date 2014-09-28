import sys, os, cStringIO, re, shutil

sys.path.insert(0, os.path.join(os.environ['TESTDIR'], '..', 'contrib'))
from hgclient import readchannel, sep, runcommand, check

def unknowncommand(server):
    server.stdin.write('unknowncommand\n')

def hellomessage(server):
    ch, data = readchannel(server)
    # escaping python tests output not supported
    print '%c, %r' % (ch, re.sub('encoding: [a-zA-Z0-9-]+', 'encoding: ***',
                                 data))

    # run an arbitrary command to make sure the next thing the server sends
    # isn't part of the hello message
    runcommand(server, ['id'])

def checkruncommand(server):
    # hello block
    readchannel(server)

    # no args
    runcommand(server, [])

    # global options
    runcommand(server, ['id', '--quiet'])

    # make sure global options don't stick through requests
    runcommand(server, ['id'])

    # --config
    runcommand(server, ['id', '--config', 'ui.quiet=True'])

    # make sure --config doesn't stick
    runcommand(server, ['id'])

    # negative return code should be masked
    runcommand(server, ['id', '-runknown'])

def inputeof(server):
    readchannel(server)
    server.stdin.write('runcommand\n')
    # close stdin while server is waiting for input
    server.stdin.close()

    # server exits with 1 if the pipe closed while reading the command
    print 'server exit code =', server.wait()

def serverinput(server):
    readchannel(server)

    patch = """
# HG changeset patch
# User test
# Date 0 0
# Node ID c103a3dec114d882c98382d684d8af798d09d857
# Parent  0000000000000000000000000000000000000000
1

diff -r 000000000000 -r c103a3dec114 a
--- /dev/null	Thu Jan 01 00:00:00 1970 +0000
+++ b/a	Thu Jan 01 00:00:00 1970 +0000
@@ -0,0 +1,1 @@
+1
"""

    runcommand(server, ['import', '-'], input=cStringIO.StringIO(patch))
    runcommand(server, ['log'])

def cwd(server):
    """ check that --cwd doesn't persist between requests """
    readchannel(server)
    os.mkdir('foo')
    f = open('foo/bar', 'wb')
    f.write('a')
    f.close()
    runcommand(server, ['--cwd', 'foo', 'st', 'bar'])
    runcommand(server, ['st', 'foo/bar'])
    os.remove('foo/bar')

def localhgrc(server):
    """ check that local configs for the cached repo aren't inherited when -R
    is used """
    readchannel(server)

    # the cached repo local hgrc contains ui.foo=bar, so showconfig should
    # show it
    runcommand(server, ['showconfig'], outfilter=sep)

    # but not for this repo
    runcommand(server, ['init', 'foo'])
    runcommand(server, ['-R', 'foo', 'showconfig', 'ui', 'defaults'])
    shutil.rmtree('foo')

def hook(**args):
    print 'hook talking'
    print 'now try to read something: %r' % sys.stdin.read()

def hookoutput(server):
    readchannel(server)
    runcommand(server, ['--config',
                        'hooks.pre-identify=python:test-commandserver.hook',
                        'id'],
               input=cStringIO.StringIO('some input'))

def outsidechanges(server):
    readchannel(server)
    f = open('a', 'ab')
    f.write('a\n')
    f.close()
    runcommand(server, ['status'])
    os.system('hg ci -Am2')
    runcommand(server, ['tip'])
    runcommand(server, ['status'])

def bookmarks(server):
    readchannel(server)
    runcommand(server, ['bookmarks'])

    # changes .hg/bookmarks
    os.system('hg bookmark -i bm1')
    os.system('hg bookmark -i bm2')
    runcommand(server, ['bookmarks'])

    # changes .hg/bookmarks.current
    os.system('hg upd bm1 -q')
    runcommand(server, ['bookmarks'])

    runcommand(server, ['bookmarks', 'bm3'])
    f = open('a', 'ab')
    f.write('a\n')
    f.close()
    runcommand(server, ['commit', '-Amm'])
    runcommand(server, ['bookmarks'])

def tagscache(server):
    readchannel(server)
    runcommand(server, ['id', '-t', '-r', '0'])
    os.system('hg tag -r 0 foo')
    runcommand(server, ['id', '-t', '-r', '0'])

def setphase(server):
    readchannel(server)
    runcommand(server, ['phase', '-r', '.'])
    os.system('hg phase -r . -p')
    runcommand(server, ['phase', '-r', '.'])

def rollback(server):
    readchannel(server)
    runcommand(server, ['phase', '-r', '.', '-p'])
    f = open('a', 'ab')
    f.write('a\n')
    f.close()
    runcommand(server, ['commit', '-Am.'])
    runcommand(server, ['rollback'])
    runcommand(server, ['phase', '-r', '.'])

def branch(server):
    readchannel(server)
    runcommand(server, ['branch'])
    os.system('hg branch foo')
    runcommand(server, ['branch'])
    os.system('hg branch default')

def hgignore(server):
    readchannel(server)
    f = open('.hgignore', 'ab')
    f.write('')
    f.close()
    runcommand(server, ['commit', '-Am.'])
    f = open('ignored-file', 'ab')
    f.write('')
    f.close()
    f = open('.hgignore', 'ab')
    f.write('ignored-file')
    f.close()
    runcommand(server, ['status', '-i', '-u'])

def phasecacheafterstrip(server):
    readchannel(server)

    # create new head, 5:731265503d86
    runcommand(server, ['update', '-C', '0'])
    f = open('a', 'ab')
    f.write('a\n')
    f.close()
    runcommand(server, ['commit', '-Am.', 'a'])
    runcommand(server, ['log', '-Gq'])

    # make it public; draft marker moves to 4:7966c8e3734d
    runcommand(server, ['phase', '-p', '.'])
    # load _phasecache.phaseroots
    runcommand(server, ['phase', '.'], outfilter=sep)

    # strip 1::4 outside server
    os.system('hg -q --config extensions.mq= strip 1')

    # shouldn't raise "7966c8e3734d: no node!"
    runcommand(server, ['branches'])

def obsolete(server):
    readchannel(server)

    runcommand(server, ['up', 'null'])
    runcommand(server, ['phase', '-df', 'tip'])
    cmd = 'hg debugobsolete `hg log -r tip --template {node}`'
    if os.name == 'nt':
        cmd = 'sh -c "%s"' % cmd # run in sh, not cmd.exe
    os.system(cmd)
    runcommand(server, ['log', '--hidden'])
    runcommand(server, ['log'])

def mqoutsidechanges(server):
    readchannel(server)

    # load repo.mq
    runcommand(server, ['qapplied'])
    os.system('hg qnew 0.diff')
    # repo.mq should be invalidated
    runcommand(server, ['qapplied'])

    runcommand(server, ['qpop', '--all'])
    os.system('hg qqueue --create foo')
    # repo.mq should be recreated to point to new queue
    runcommand(server, ['qqueue', '--active'])

def getpass(server):
    readchannel(server)
    runcommand(server, ['debuggetpass', '--config', 'ui.interactive=True'],
               input=cStringIO.StringIO('1234\n'))

def startwithoutrepo(server):
    readchannel(server)
    runcommand(server, ['init', 'repo2'])
    runcommand(server, ['id', '-R', 'repo2'])

if __name__ == '__main__':
    os.system('hg init repo')
    os.chdir('repo')

    check(hellomessage)
    check(unknowncommand)
    check(checkruncommand)
    check(inputeof)
    check(serverinput)
    check(cwd)

    hgrc = open('.hg/hgrc', 'a')
    hgrc.write('[ui]\nfoo=bar\n')
    hgrc.close()
    check(localhgrc)
    check(hookoutput)
    check(outsidechanges)
    check(bookmarks)
    check(tagscache)
    check(setphase)
    check(rollback)
    check(branch)
    check(hgignore)
    check(phasecacheafterstrip)
    obs = open('obs.py', 'w')
    obs.write('import mercurial.obsolete\nmercurial.obsolete._enabled = True\n')
    obs.close()
    hgrc = open('.hg/hgrc', 'a')
    hgrc.write('[extensions]\nobs=obs.py\n')
    hgrc.close()
    check(obsolete)
    hgrc = open('.hg/hgrc', 'a')
    hgrc.write('[extensions]\nmq=\n')
    hgrc.close()
    check(mqoutsidechanges)
    dbg = open('dbgui.py', 'w')
    dbg.write('from mercurial import cmdutil, commands\n'
              'cmdtable = {}\n'
              'command = cmdutil.command(cmdtable)\n'
              '@command("debuggetpass", norepo=True)\n'
              'def debuggetpass(ui):\n'
              '    ui.write("%s\\n" % ui.getpass())\n')
    dbg.close()
    hgrc = open('.hg/hgrc', 'a')
    hgrc.write('[extensions]\ndbgui=dbgui.py\n')
    hgrc.close()
    check(getpass)

    os.chdir('..')
    check(hellomessage)
    check(startwithoutrepo)
