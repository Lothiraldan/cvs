#!/usr/bin/env python
#
# run-tests.py - Run a set of tests on Mercurial
#
# Copyright 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2, incorporated herein by reference.

# Modifying this script is tricky because it has many modes:
#   - serial (default) vs parallel (-jN, N > 1)
#   - no coverage (default) vs coverage (-c, -C, -s)
#   - temp install (default) vs specific hg script (--with-hg, --local)
#   - tests are a mix of shell scripts and Python scripts
#
# If you change this script, it is recommended that you ensure you
# haven't broken it by running it in various modes with a representative
# sample of test scripts.  For example:
#
#  1) serial, no coverage, temp install:
#      ./run-tests.py test-s*
#  2) serial, no coverage, local hg:
#      ./run-tests.py --local test-s*
#  3) serial, coverage, temp install:
#      ./run-tests.py -c test-s*
#  4) serial, coverage, local hg:
#      ./run-tests.py -c --local test-s*      # unsupported
#  5) parallel, no coverage, temp install:
#      ./run-tests.py -j2 test-s*
#  6) parallel, no coverage, local hg:
#      ./run-tests.py -j2 --local test-s*
#  7) parallel, coverage, temp install:
#      ./run-tests.py -j2 -c test-s*          # currently broken
#  8) parallel, coverage, local install:
#      ./run-tests.py -j2 -c --local test-s*  # unsupported (and broken)
#  9) parallel, custom tmp dir:
#      ./run-tests.py -j2 --tmpdir /tmp/myhgtests
#
# (You could use any subset of the tests: test-s* happens to match
# enough that it's worth doing parallel runs, few enough that it
# completes fairly quickly, includes both shell and Python scripts, and
# includes some scripts that run daemon processes.)

from ConfigParser import ConfigParser
import difflib
import errno
import optparse
import os
import subprocess
import shutil
import signal
import sys
import tempfile
import time

closefds = os.name == 'posix'
def Popen4(cmd, bufsize=-1):
    p = subprocess.Popen(cmd, shell=True, bufsize=bufsize,
                         close_fds=closefds,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    p.fromchild = p.stdout
    p.tochild = p.stdin
    p.childerr = p.stderr
    return p

# reserved exit code to skip test (used by hghave)
SKIPPED_STATUS = 80
SKIPPED_PREFIX = 'skipped: '
FAILED_PREFIX  = 'hghave check failed: '
PYTHON = sys.executable

requiredtools = ["python", "diff", "grep", "unzip", "gunzip", "bunzip2", "sed"]

defaults = {
    'jobs': ('HGTEST_JOBS', 1),
    'timeout': ('HGTEST_TIMEOUT', 180),
    'port': ('HGTEST_PORT', 20059),
}

def parseargs():
    parser = optparse.OptionParser("%prog [options] [tests]")
    parser.add_option("-C", "--annotate", action="store_true",
        help="output files annotated with coverage")
    parser.add_option("--child", type="int",
        help="run as child process, summary to given fd")
    parser.add_option("-c", "--cover", action="store_true",
        help="print a test coverage report")
    parser.add_option("-f", "--first", action="store_true",
        help="exit on the first test failure")
    parser.add_option("-i", "--interactive", action="store_true",
        help="prompt to accept changed output")
    parser.add_option("-j", "--jobs", type="int",
        help="number of jobs to run in parallel"
             " (default: $%s or %d)" % defaults['jobs'])
    parser.add_option("-k", "--keywords",
        help="run tests matching keywords")
    parser.add_option("--keep-tmpdir", action="store_true",
        help="keep temporary directory after running tests")
    parser.add_option("--tmpdir", type="string",
        help="run tests in the given temporary directory"
             " (implies --keep-tmpdir)")
    parser.add_option("-d", "--debug", action="store_true",
        help="debug mode: write output of test scripts to console"
             " rather than capturing and diff'ing it (disables timeout)")
    parser.add_option("-R", "--restart", action="store_true",
        help="restart at last error")
    parser.add_option("-p", "--port", type="int",
        help="port on which servers should listen"
             " (default: $%s or %d)" % defaults['port'])
    parser.add_option("-r", "--retest", action="store_true",
        help="retest failed tests")
    parser.add_option("-s", "--cover_stdlib", action="store_true",
        help="print a test coverage report inc. standard libraries")
    parser.add_option("-S", "--noskips", action="store_true",
        help="don't report skip tests verbosely")
    parser.add_option("-t", "--timeout", type="int",
        help="kill errant tests after TIMEOUT seconds"
             " (default: $%s or %d)" % defaults['timeout'])
    parser.add_option("-v", "--verbose", action="store_true",
        help="output verbose messages")
    parser.add_option("-n", "--nodiff", action="store_true",
        help="skip showing test changes")
    parser.add_option("--with-hg", type="string",
        metavar="HG",
        help="test using specified hg script rather than a "
             "temporary installation")
    parser.add_option("--local", action="store_true",
        help="shortcut for --with-hg=<testdir>/../hg")
    parser.add_option("--pure", action="store_true",
        help="use pure Python code instead of C extensions")
    parser.add_option("-3", "--py3k-warnings", action="store_true",
        help="enable Py3k warnings on Python 2.6+")
    parser.add_option("--inotify", action="store_true",
        help="enable inotify extension when running tests")
    parser.add_option("--blacklist", action="append",
        help="skip tests listed in the specified section of "
             "the blacklist file")

    for option, default in defaults.items():
        defaults[option] = int(os.environ.get(*default))
    parser.set_defaults(**defaults)
    (options, args) = parser.parse_args()

    if options.with_hg:
        if not (os.path.isfile(options.with_hg) and
                os.access(options.with_hg, os.X_OK)):
            parser.error('--with-hg must specify an executable hg script')
        if not os.path.basename(options.with_hg) == 'hg':
            sys.stderr.write('warning: --with-hg should specify an hg script')
    if options.local:
        testdir = os.path.dirname(os.path.realpath(sys.argv[0]))
        hgbin = os.path.join(os.path.dirname(testdir), 'hg')
        if not os.access(hgbin, os.X_OK):
            parser.error('--local specified, but %r not found or not executable'
                         % hgbin)
        options.with_hg = hgbin

    options.anycoverage = (options.cover or
                           options.cover_stdlib or
                           options.annotate)

    if options.anycoverage and options.with_hg:
        # I'm not sure if this is a fundamental limitation or just a
        # bug.  But I don't want to waste people's time and energy doing
        # test runs that don't give the results they want.
        parser.error("sorry, coverage options do not work when --with-hg "
                     "or --local specified")

    global vlog
    if options.verbose:
        if options.jobs > 1 or options.child is not None:
            pid = "[%d]" % os.getpid()
        else:
            pid = None
        def vlog(*msg):
            if pid:
                print pid,
            for m in msg:
                print m,
            print
            sys.stdout.flush()
    else:
        vlog = lambda *msg: None

    if options.tmpdir:
        options.tmpdir = os.path.expanduser(options.tmpdir)

    if options.jobs < 1:
        parser.error('--jobs must be positive')
    if options.interactive and options.jobs > 1:
        print '(--interactive overrides --jobs)'
        options.jobs = 1
    if options.interactive and options.debug:
        parser.error("-i/--interactive and -d/--debug are incompatible")
    if options.debug:
        if options.timeout != defaults['timeout']:
            sys.stderr.write(
                'warning: --timeout option ignored with --debug\n')
        options.timeout = 0
    if options.py3k_warnings:
        if sys.version_info[:2] < (2, 6) or sys.version_info[:2] >= (3, 0):
            parser.error('--py3k-warnings can only be used on Python 2.6+')
    if options.blacklist:
        configparser = ConfigParser()
        configparser.read("blacklist")
        blacklist = dict()
        for section in options.blacklist:
            for (item, value) in configparser.items(section):
                blacklist["test-" + item] = section
        options.blacklist = blacklist

    return (options, args)

def rename(src, dst):
    """Like os.rename(), trade atomicity and opened files friendliness
    for existing destination support.
    """
    shutil.copy(src, dst)
    os.remove(src)

def splitnewlines(text):
    '''like str.splitlines, but only split on newlines.
    keep line endings.'''
    i = 0
    lines = []
    while True:
        n = text.find('\n', i)
        if n == -1:
            last = text[i:]
            if last:
                lines.append(last)
            return lines
        lines.append(text[i:n+1])
        i = n + 1

def parsehghaveoutput(lines):
    '''Parse hghave log lines.
    Return tuple of lists (missing, failed):
      * the missing/unknown features
      * the features for which existence check failed'''
    missing = []
    failed = []
    for line in lines:
        if line.startswith(SKIPPED_PREFIX):
            line = line.splitlines()[0]
            missing.append(line[len(SKIPPED_PREFIX):])
        elif line.startswith(FAILED_PREFIX):
            line = line.splitlines()[0]
            failed.append(line[len(FAILED_PREFIX):])

    return missing, failed

def showdiff(expected, output):
    for line in difflib.unified_diff(expected, output,
            "Expected output", "Test output"):
        sys.stdout.write(line)

def findprogram(program):
    """Search PATH for a executable program"""
    for p in os.environ.get('PATH', os.defpath).split(os.pathsep):
        name = os.path.join(p, program)
        if os.access(name, os.X_OK):
            return name
    return None

def checktools():
    # Before we go any further, check for pre-requisite tools
    # stuff from coreutils (cat, rm, etc) are not tested
    for p in requiredtools:
        if os.name == 'nt':
            p += '.exe'
        found = findprogram(p)
        if found:
            vlog("# Found prerequisite", p, "at", found)
        else:
            print "WARNING: Did not find prerequisite tool: "+p

def cleanup(options):
    if not options.keep_tmpdir:
        vlog("# Cleaning up HGTMP", HGTMP)
        shutil.rmtree(HGTMP, True)

def usecorrectpython():
    # some tests run python interpreter. they must use same
    # interpreter we use or bad things will happen.
    exedir, exename = os.path.split(sys.executable)
    if exename == 'python':
        path = findprogram('python')
        if os.path.dirname(path) == exedir:
            return
    vlog('# Making python executable in test path use correct Python')
    mypython = os.path.join(BINDIR, 'python')
    try:
        os.symlink(sys.executable, mypython)
    except AttributeError:
        # windows fallback
        shutil.copyfile(sys.executable, mypython)
        shutil.copymode(sys.executable, mypython)

def installhg(options):
    vlog("# Performing temporary installation of HG")
    installerrs = os.path.join("tests", "install.err")
    pure = options.pure and "--pure" or ""

    # Run installer in hg root
    script = os.path.realpath(sys.argv[0])
    hgroot = os.path.dirname(os.path.dirname(script))
    os.chdir(hgroot)
    nohome = '--home=""'
    if os.name == 'nt':
        # The --home="" trick works only on OS where os.sep == '/'
        # because of a distutils convert_path() fast-path. Avoid it at
        # least on Windows for now, deal with .pydistutils.cfg bugs
        # when they happen.
        nohome = ''
    cmd = ('%s setup.py %s clean --all'
           ' install --force --prefix="%s" --install-lib="%s"'
           ' --install-scripts="%s" %s >%s 2>&1'
           % (sys.executable, pure, INST, PYTHONDIR, BINDIR, nohome,
              installerrs))
    vlog("# Running", cmd)
    if os.system(cmd) == 0:
        if not options.verbose:
            os.remove(installerrs)
    else:
        f = open(installerrs)
        for line in f:
            print line,
        f.close()
        sys.exit(1)
    os.chdir(TESTDIR)

    usecorrectpython()

    vlog("# Installing dummy diffstat")
    f = open(os.path.join(BINDIR, 'diffstat'), 'w')
    f.write('#!' + sys.executable + '\n'
            'import sys\n'
            'files = 0\n'
            'for line in sys.stdin:\n'
            '    if line.startswith("diff "):\n'
            '        files += 1\n'
            'sys.stdout.write("files patched: %d\\n" % files)\n')
    f.close()
    os.chmod(os.path.join(BINDIR, 'diffstat'), 0700)

    if options.py3k_warnings and not options.anycoverage:
        vlog("# Updating hg command to enable Py3k Warnings switch")
        f = open(os.path.join(BINDIR, 'hg'), 'r')
        lines = [line.rstrip() for line in f]
        lines[0] += ' -3'
        f.close()
        f = open(os.path.join(BINDIR, 'hg'), 'w')
        for line in lines:
            f.write(line + '\n')
        f.close()

    if options.anycoverage:
        vlog("# Installing coverage wrapper")
        os.environ['COVERAGE_FILE'] = COVERAGE_FILE
        if os.path.exists(COVERAGE_FILE):
            os.unlink(COVERAGE_FILE)
        # Create a wrapper script to invoke hg via coverage.py
        os.rename(os.path.join(BINDIR, "hg"), os.path.join(BINDIR, "_hg.py"))
        f = open(os.path.join(BINDIR, 'hg'), 'w')
        f.write('#!' + sys.executable + '\n')
        f.write('import sys, os; os.execv(sys.executable, [sys.executable, '
                '"%s", "-x", "-p", "%s"] + sys.argv[1:])\n' %
                (os.path.join(TESTDIR, 'coverage.py'),
                 os.path.join(BINDIR, '_hg.py')))
        f.close()
        os.chmod(os.path.join(BINDIR, 'hg'), 0700)

def outputcoverage(options):

    vlog('# Producing coverage report')
    os.chdir(PYTHONDIR)

    def covrun(*args):
        start = sys.executable, os.path.join(TESTDIR, 'coverage.py')
        cmd = '"%s" "%s" %s' % (start[0], start[1], ' '.join(args))
        vlog('# Running: %s' % cmd)
        os.system(cmd)

    omit = [BINDIR, TESTDIR, PYTHONDIR]
    if not options.cover_stdlib:
        # Exclude as system paths (ignoring empty strings seen on win)
        omit += [x for x in sys.path if x != '']
    omit = ','.join(omit)

    covrun('-c') # combine from parallel processes
    for fn in os.listdir(TESTDIR):
        if fn.startswith('.coverage.'):
            os.unlink(os.path.join(TESTDIR, fn))

    covrun('-i', '-r', '"--omit=%s"' % omit) # report
    if options.annotate:
        adir = os.path.join(TESTDIR, 'annotated')
        if not os.path.isdir(adir):
            os.mkdir(adir)
        covrun('-i', '-a', '"--directory=%s"' % adir, '"--omit=%s"' % omit)

class Timeout(Exception):
    pass

def alarmed(signum, frame):
    raise Timeout

def run(cmd, options):
    """Run command in a sub-process, capturing the output (stdout and stderr).
    Return a tuple (exitcode, output).  output is None in debug mode."""
    # TODO: Use subprocess.Popen if we're running on Python 2.4
    if options.debug:
        proc = subprocess.Popen(cmd, shell=True)
        ret = proc.wait()
        return (ret, None)

    if os.name == 'nt' or sys.platform.startswith('java'):
        tochild, fromchild = os.popen4(cmd)
        tochild.close()
        output = fromchild.read()
        ret = fromchild.close()
        if ret == None:
            ret = 0
    else:
        proc = Popen4(cmd)
        try:
            output = ''
            proc.tochild.close()
            output = proc.fromchild.read()
            ret = proc.wait()
            if os.WIFEXITED(ret):
                ret = os.WEXITSTATUS(ret)
        except Timeout:
            vlog('# Process %d timed out - killing it' % proc.pid)
            os.kill(proc.pid, signal.SIGTERM)
            ret = proc.wait()
            if ret == 0:
                ret = signal.SIGTERM << 8
            output += ("\n### Abort: timeout after %d seconds.\n"
                       % options.timeout)
    return ret, splitnewlines(output)

def runone(options, test, skips, fails):
    '''tristate output:
    None -> skipped
    True -> passed
    False -> failed'''

    def skip(msg):
        if not options.verbose:
            skips.append((test, msg))
        else:
            print "\nSkipping %s: %s" % (test, msg)
        return None

    def fail(msg):
        fails.append((test, msg))
        if not options.nodiff:
            print "\nERROR: %s %s" % (test, msg)
        return None

    vlog("# Test", test)

    # create a fresh hgrc
    hgrc = open(HGRCPATH, 'w+')
    hgrc.write('[ui]\n')
    hgrc.write('slash = True\n')
    hgrc.write('[defaults]\n')
    hgrc.write('backout = -d "0 0"\n')
    hgrc.write('commit = -d "0 0"\n')
    hgrc.write('tag = -d "0 0"\n')
    if options.inotify:
        hgrc.write('[extensions]\n')
        hgrc.write('inotify=\n')
        hgrc.write('[inotify]\n')
        hgrc.write('pidfile=%s\n' % DAEMON_PIDS)
    hgrc.close()

    err = os.path.join(TESTDIR, test+".err")
    ref = os.path.join(TESTDIR, test+".out")
    testpath = os.path.join(TESTDIR, test)

    if os.path.exists(err):
        os.remove(err)       # Remove any previous output files

    # Make a tmp subdirectory to work in
    tmpd = os.path.join(HGTMP, test)
    os.mkdir(tmpd)
    os.chdir(tmpd)

    try:
        tf = open(testpath)
        firstline = tf.readline().rstrip()
        tf.close()
    except:
        firstline = ''
    lctest = test.lower()

    if lctest.endswith('.py') or firstline == '#!/usr/bin/env python':
        py3kswitch = options.py3k_warnings and ' -3' or ''
        cmd = '%s%s "%s"' % (PYTHON, py3kswitch, testpath)
    elif lctest.endswith('.bat'):
        # do not run batch scripts on non-windows
        if os.name != 'nt':
            return skip("batch script")
        # To reliably get the error code from batch files on WinXP,
        # the "cmd /c call" prefix is needed. Grrr
        cmd = 'cmd /c call "%s"' % testpath
    else:
        # do not run shell scripts on windows
        if os.name == 'nt':
            return skip("shell script")
        # do not try to run non-executable programs
        if not os.path.exists(testpath):
            return fail("does not exist")
        elif not os.access(testpath, os.X_OK):
            return skip("not executable")
        cmd = '"%s"' % testpath

    if options.timeout > 0:
        signal.alarm(options.timeout)

    vlog("# Running", cmd)
    ret, out = run(cmd, options)
    vlog("# Ret was:", ret)

    if options.timeout > 0:
        signal.alarm(0)

    mark = '.'

    skipped = (ret == SKIPPED_STATUS)
    # If we're not in --debug mode and reference output file exists,
    # check test output against it.
    if options.debug:
        refout = None                   # to match out == None
    elif os.path.exists(ref):
        f = open(ref, "r")
        refout = splitnewlines(f.read())
        f.close()
    else:
        refout = []

    if skipped:
        mark = 's'
        if out is None:                 # debug mode: nothing to parse
            missing = ['unknown']
            failed = None
        else:
            missing, failed = parsehghaveoutput(out)
        if not missing:
            missing = ['irrelevant']
        if failed:
            fail("hghave failed checking for %s" % failed[-1])
            skipped = False
        else:
            skip(missing[-1])
    elif out != refout:
        mark = '!'
        if ret:
            fail("output changed and returned error code %d" % ret)
        else:
            fail("output changed")
        if not options.nodiff:
            showdiff(refout, out)
        ret = 1
    elif ret:
        mark = '!'
        fail("returned error code %d" % ret)

    if not options.verbose:
        sys.stdout.write(mark)
        sys.stdout.flush()

    if ret != 0 and not skipped and not options.debug:
        # Save errors to a file for diagnosis
        f = open(err, "wb")
        for line in out:
            f.write(line)
        f.close()

    # Kill off any leftover daemon processes
    try:
        fp = open(DAEMON_PIDS)
        for line in fp:
            try:
                pid = int(line)
            except ValueError:
                continue
            try:
                os.kill(pid, 0)
                vlog('# Killing daemon process %d' % pid)
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.25)
                os.kill(pid, 0)
                vlog('# Daemon process %d is stuck - really killing it' % pid)
                os.kill(pid, signal.SIGKILL)
            except OSError, err:
                if err.errno != errno.ESRCH:
                    raise
        fp.close()
        os.unlink(DAEMON_PIDS)
    except IOError:
        pass

    os.chdir(TESTDIR)
    if not options.keep_tmpdir:
        shutil.rmtree(tmpd, True)
    if skipped:
        return None
    return ret == 0

_hgpath = None

def _gethgpath():
    """Return the path to the mercurial package that is actually found by
    the current Python interpreter."""
    global _hgpath
    if _hgpath is not None:
        return _hgpath

    cmd = '%s -c "import mercurial; print mercurial.__path__[0]"'
    pipe = os.popen(cmd % PYTHON)
    try:
        _hgpath = pipe.read().strip()
    finally:
        pipe.close()
    return _hgpath

def _checkhglib(verb):
    """Ensure that the 'mercurial' package imported by python is
    the one we expect it to be.  If not, print a warning to stderr."""
    expecthg = os.path.join(PYTHONDIR, 'mercurial')
    actualhg = _gethgpath()
    if actualhg != expecthg:
        sys.stderr.write('warning: %s with unexpected mercurial lib: %s\n'
                         '         (expected %s)\n'
                         % (verb, actualhg, expecthg))

def runchildren(options, tests):
    if INST:
        installhg(options)
        _checkhglib("Testing")

    optcopy = dict(options.__dict__)
    optcopy['jobs'] = 1
    if optcopy['with_hg'] is None:
        optcopy['with_hg'] = os.path.join(BINDIR, "hg")
    opts = []
    for opt, value in optcopy.iteritems():
        name = '--' + opt.replace('_', '-')
        if value is True:
            opts.append(name)
        elif value is not None:
            opts.append(name + '=' + str(value))

    tests.reverse()
    jobs = [[] for j in xrange(options.jobs)]
    while tests:
        for job in jobs:
            if not tests: break
            job.append(tests.pop())
    fps = {}
    for j, job in enumerate(jobs):
        if not job:
            continue
        rfd, wfd = os.pipe()
        childopts = ['--child=%d' % wfd, '--port=%d' % (options.port + j * 3)]
        childtmp = os.path.join(HGTMP, 'child%d' % j)
        childopts += ['--tmpdir', childtmp]
        cmdline = [PYTHON, sys.argv[0]] + opts + childopts + job
        vlog(' '.join(cmdline))
        fps[os.spawnvp(os.P_NOWAIT, cmdline[0], cmdline)] = os.fdopen(rfd, 'r')
        os.close(wfd)
    failures = 0
    tested, skipped, failed = 0, 0, 0
    skips = []
    fails = []
    while fps:
        pid, status = os.wait()
        fp = fps.pop(pid)
        l = fp.read().splitlines()
        test, skip, fail = map(int, l[:3])
        split = -fail or len(l)
        for s in l[3:split]:
            skips.append(s.split(" ", 1))
        for s in l[split:]:
            fails.append(s.split(" ", 1))
        tested += test
        skipped += skip
        failed += fail
        vlog('pid %d exited, status %d' % (pid, status))
        failures |= status
    print
    if not options.noskips:
        for s in skips:
            print "Skipped %s: %s" % (s[0], s[1])
    for s in fails:
        print "Failed %s: %s" % (s[0], s[1])

    _checkhglib("Tested")
    print "# Ran %d tests, %d skipped, %d failed." % (
        tested, skipped, failed)
    sys.exit(failures != 0)

def runtests(options, tests):
    global DAEMON_PIDS, HGRCPATH
    DAEMON_PIDS = os.environ["DAEMON_PIDS"] = os.path.join(HGTMP, 'daemon.pids')
    HGRCPATH = os.environ["HGRCPATH"] = os.path.join(HGTMP, '.hgrc')

    try:
        if INST:
            installhg(options)
            _checkhglib("Testing")

        if options.timeout > 0:
            try:
                signal.signal(signal.SIGALRM, alarmed)
                vlog('# Running each test with %d second timeout' %
                     options.timeout)
            except AttributeError:
                print 'WARNING: cannot run tests with timeouts'
                options.timeout = 0

        tested = 0
        failed = 0
        skipped = 0

        if options.restart:
            orig = list(tests)
            while tests:
                if os.path.exists(tests[0] + ".err"):
                    break
                tests.pop(0)
            if not tests:
                print "running all tests"
                tests = orig

        skips = []
        fails = []

        for test in tests:
            if options.blacklist:
                section = options.blacklist.get(test)
                if section is not None:
                    skips.append((test, "blacklisted (%s section)" % section))
                    skipped += 1
                    continue

            if options.retest and not os.path.exists(test + ".err"):
                skipped += 1
                continue

            if options.keywords:
                t = open(test).read().lower() + test.lower()
                for k in options.keywords.lower().split():
                    if k in t:
                        break
                else:
                    skipped +=1
                    continue

            ret = runone(options, test, skips, fails)
            if ret is None:
                skipped += 1
            elif not ret:
                if options.interactive:
                    print "Accept this change? [n] ",
                    answer = sys.stdin.readline().strip()
                    if answer.lower() in "y yes".split():
                        rename(test + ".err", test + ".out")
                        tested += 1
                        fails.pop()
                        continue
                failed += 1
                if options.first:
                    break
            tested += 1

        if options.child:
            fp = os.fdopen(options.child, 'w')
            fp.write('%d\n%d\n%d\n' % (tested, skipped, failed))
            for s in skips:
                fp.write("%s %s\n" % s)
            for s in fails:
                fp.write("%s %s\n" % s)
            fp.close()
        else:
            print
            for s in skips:
                print "Skipped %s: %s" % s
            for s in fails:
                print "Failed %s: %s" % s
            _checkhglib("Tested")
            print "# Ran %d tests, %d skipped, %d failed." % (
                tested, skipped, failed)

        if options.anycoverage:
            outputcoverage(options)
    except KeyboardInterrupt:
        failed = True
        print "\ninterrupted!"

    if failed:
        sys.exit(1)

def main():
    (options, args) = parseargs()
    if not options.child:
        os.umask(022)

        checktools()

    # Reset some environment variables to well-known values so that
    # the tests produce repeatable output.
    os.environ['LANG'] = os.environ['LC_ALL'] = os.environ['LANGUAGE'] = 'C'
    os.environ['TZ'] = 'GMT'
    os.environ["EMAIL"] = "Foo Bar <foo.bar@example.com>"
    os.environ['CDPATH'] = ''
    os.environ['COLUMNS'] = '80'

    global TESTDIR, HGTMP, INST, BINDIR, PYTHONDIR, COVERAGE_FILE
    TESTDIR = os.environ["TESTDIR"] = os.getcwd()
    if options.tmpdir:
        options.keep_tmpdir = True
        tmpdir = options.tmpdir
        if os.path.exists(tmpdir):
            # Meaning of tmpdir has changed since 1.3: we used to create
            # HGTMP inside tmpdir; now HGTMP is tmpdir.  So fail if
            # tmpdir already exists.
            sys.exit("error: temp dir %r already exists" % tmpdir)

            # Automatically removing tmpdir sounds convenient, but could
            # really annoy anyone in the habit of using "--tmpdir=/tmp"
            # or "--tmpdir=$HOME".
            #vlog("# Removing temp dir", tmpdir)
            #shutil.rmtree(tmpdir)
        os.makedirs(tmpdir)
    else:
        tmpdir = tempfile.mkdtemp('', 'hgtests.')
    HGTMP = os.environ['HGTMP'] = os.path.realpath(tmpdir)
    DAEMON_PIDS = None
    HGRCPATH = None

    os.environ["HGEDITOR"] = sys.executable + ' -c "import sys; sys.exit(0)"'
    os.environ["HGMERGE"] = "internal:merge"
    os.environ["HGUSER"]   = "test"
    os.environ["HGENCODING"] = "ascii"
    os.environ["HGENCODINGMODE"] = "strict"
    os.environ["HGPORT"] = str(options.port)
    os.environ["HGPORT1"] = str(options.port + 1)
    os.environ["HGPORT2"] = str(options.port + 2)

    if options.with_hg:
        INST = None
        BINDIR = os.path.dirname(os.path.realpath(options.with_hg))

        # This looks redundant with how Python initializes sys.path from
        # the location of the script being executed.  Needed because the
        # "hg" specified by --with-hg is not the only Python script
        # executed in the test suite that needs to import 'mercurial'
        # ... which means it's not really redundant at all.
        PYTHONDIR = BINDIR
    else:
        INST = os.path.join(HGTMP, "install")
        BINDIR = os.environ["BINDIR"] = os.path.join(INST, "bin")
        PYTHONDIR = os.path.join(INST, "lib", "python")

    os.environ["BINDIR"] = BINDIR
    os.environ["PYTHON"] = PYTHON

    if not options.child:
        path = [BINDIR] + os.environ["PATH"].split(os.pathsep)
        os.environ["PATH"] = os.pathsep.join(path)

        # Include TESTDIR in PYTHONPATH so that out-of-tree extensions
        # can run .../tests/run-tests.py test-foo where test-foo
        # adds an extension to HGRC
        pypath = [PYTHONDIR, TESTDIR]
        # We have to augment PYTHONPATH, rather than simply replacing
        # it, in case external libraries are only available via current
        # PYTHONPATH.  (In particular, the Subversion bindings on OS X
        # are in /opt/subversion.)
        oldpypath = os.environ.get('PYTHONPATH')
        if oldpypath:
            pypath.append(oldpypath)
        os.environ['PYTHONPATH'] = os.pathsep.join(pypath)

    COVERAGE_FILE = os.path.join(TESTDIR, ".coverage")

    if len(args) == 0:
        args = os.listdir(".")
        args.sort()

    tests = []
    for test in args:
        if (test.startswith("test-") and '~' not in test and
            ('.' not in test or test.endswith('.py') or
             test.endswith('.bat'))):
            tests.append(test)
    if not tests:
        print "# Ran 0 tests, 0 skipped, 0 failed."
        return

    vlog("# Using TESTDIR", TESTDIR)
    vlog("# Using HGTMP", HGTMP)
    vlog("# Using PATH", os.environ["PATH"])
    vlog("# Using PYTHONPATH", os.environ["PYTHONPATH"])

    try:
        if len(tests) > 1 and options.jobs > 1:
            runchildren(options, tests)
        else:
            runtests(options, tests)
    finally:
        cleanup(options)

main()
