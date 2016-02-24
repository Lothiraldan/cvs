from __future__ import print_function, absolute_import

"""Fuzz testing for operations against a Mercurial repository

This uses Hypothesis's stateful testing to generate random repository
operations and test Mercurial using them, both to see if there are any
unexpected errors and to compare different versions of it."""

import os
import sys

# These tests require Hypothesis and pytz to be installed.
# Running 'pip install hypothesis pytz' will achieve that.
# Note: This won't work if you're running Python < 2.7.
try:
    from hypothesis.extra.datetime import datetimes
except ImportError:
    sys.stderr.write("skipped: hypothesis or pytz not installed" + os.linesep)
    sys.exit(80)

# If you are running an old version of pip you may find that the enum34
# backport is not installed automatically. If so 'pip install enum34' will
# fix this problem.
try:
    import enum
    assert enum  # Silence pyflakes
except ImportError:
    sys.stderr.write("skipped: enum34 not installed" + os.linesep)
    sys.exit(80)

import binascii
from contextlib import contextmanager
import errno
import pipes
import shutil
import silenttestrunner
import subprocess

from hypothesis.errors import HypothesisException
from hypothesis.stateful import rule, RuleBasedStateMachine, Bundle
from hypothesis import settings, note, strategies as st
from hypothesis.configuration import set_hypothesis_home_dir

testdir = os.path.abspath(os.environ["TESTDIR"])

# We store Hypothesis examples here rather in the temporary test directory
# so that when rerunning a failing test this always results in refinding the
# previous failure. This directory is in .hgignore and should not be checked in
# but is useful to have for development.
set_hypothesis_home_dir(os.path.join(testdir, ".hypothesis"))

runtests = os.path.join(os.environ["RUNTESTDIR"], "run-tests.py")
testtmp = os.environ["TESTTMP"]
assert os.path.isdir(testtmp)

generatedtests = os.path.join(testdir, "hypothesis-generated")

try:
    os.makedirs(generatedtests)
except OSError:
    pass

# We write out generated .t files to a file in order to ease debugging and to
# give a starting point for turning failures Hypothesis finds into normal
# tests. In order to ensure that multiple copies of this test can be run in
# parallel we use atomic file create to ensure that we always get a unique
# name.
file_index = 0
while True:
    file_index += 1
    savefile = os.path.join(generatedtests, "test-generated-%d.t" % (
        file_index,
    ))
    try:
        os.close(os.open(savefile, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        break
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
assert os.path.exists(savefile)

hgrc = os.path.join(".hg", "hgrc")

filecharacters = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "[]^_`;=@{}~ !#$%&'()+,-"
)

files = st.text(filecharacters, min_size=1).map(lambda x: x.strip()).filter(
    bool).map(lambda s: s.encode('ascii'))

safetext = st.text(st.characters(
    min_codepoint=1, max_codepoint=127,
    blacklist_categories=('Cc', 'Cs')), min_size=1).map(
    lambda s: s.encode('utf-8')
)

@contextmanager
def acceptableerrors(*args):
    """Sometimes we know an operation we're about to perform might fail, and
    we're OK with some of the failures. In those cases this may be used as a
    context manager and will swallow expected failures, as identified by
    substrings of the error message Mercurial emits."""
    try:
        yield
    except subprocess.CalledProcessError as e:
        if not any(a in e.output for a in args):
            note(e.output)
            raise

class verifyingstatemachine(RuleBasedStateMachine):
    """This defines the set of acceptable operations on a Mercurial repository
    using Hypothesis's RuleBasedStateMachine.

    The general concept is that we manage multiple repositories inside a
    repos/ directory in our temporary test location. Some of these are freshly
    inited, some are clones of the others. Our current working directory is
    always inside one of these repositories while the tests are running.

    Hypothesis then performs a series of operations against these repositories,
    including hg commands, generating contents and editing the .hgrc file.
    If these operations fail in unexpected ways or behave differently in
    different configurations of Mercurial, the test will fail and a minimized
    .t test file will be written to the hypothesis-generated directory to
    exhibit that failure.

    Operations are defined as methods with @rule() decorators. See the
    Hypothesis documentation at
    http://hypothesis.readthedocs.org/en/release/stateful.html for more
    details."""

    # A bundle is a reusable collection of previously generated data which may
    # be provided as arguments to future operations.
    paths = Bundle('paths')
    contents = Bundle('contents')
    committimes = Bundle('committimes')

    def __init__(self):
        super(verifyingstatemachine, self).__init__()
        self.repodir = os.path.join(testtmp, "repo")
        if os.path.exists(self.repodir):
            shutil.rmtree(self.repodir)
        os.chdir(testtmp)
        self.log = []
        self.failed = False

        self.mkdirp("repo")
        self.cd("repo")
        self.hg("init")

    def teardown(self):
        """On teardown we clean up after ourselves as usual, but we also
        do some additional testing: We generate a .t file based on our test
        run using run-test.py -i to get the correct output.

        We then test it in a number of other configurations, verifying that
        each passes the same test."""
        super(verifyingstatemachine, self).teardown()
        try:
            shutil.rmtree(self.repodir)
        except OSError:
            pass
        ttest = os.linesep.join("  " + l for l in self.log)
        os.chdir(testtmp)
        path = os.path.join(testtmp, "test-generated.t")
        with open(path, 'w') as o:
            o.write(ttest + os.linesep)
        with open(os.devnull, "w") as devnull:
            rewriter = subprocess.Popen(
                [runtests, "--local", "-i", path], stdin=subprocess.PIPE,
                stdout=devnull, stderr=devnull,
            )
            rewriter.communicate("yes")
            with open(path, 'r') as i:
                ttest = i.read()

        e = None
        if not self.failed:
            try:
                output = subprocess.check_output([
                    runtests, path, "--local", "--pure"
                ], stderr=subprocess.STDOUT)
                assert "Ran 1 test" in output, output
            except subprocess.CalledProcessError as e:
                note(e.output)
            finally:
                os.unlink(path)
                try:
                    os.unlink(path + ".err")
                except OSError:
                    pass
        if self.failed or e is not None:
            with open(savefile, "wb") as o:
                o.write(ttest)
        if e is not None:
            raise e

    def execute_step(self, step):
        try:
            return super(verifyingstatemachine, self).execute_step(step)
        except (HypothesisException, KeyboardInterrupt):
            raise
        except Exception:
            self.failed = True
            raise

    # Section: Basic commands.
    def mkdirp(self, path):
        if os.path.exists(path):
            return
        self.log.append(
            "$ mkdir -p -- %s" % (pipes.quote(os.path.relpath(path)),))
        os.makedirs(path)

    def cd(self, path):
        path = os.path.relpath(path)
        if path == ".":
            return
        os.chdir(path)
        self.log.append("$ cd -- %s" % (pipes.quote(path),))

    def hg(self, *args):
        self.command("hg", *args)

    def command(self, *args):
        self.log.append("$ " + ' '.join(map(pipes.quote, args)))
        subprocess.check_output(args, stderr=subprocess.STDOUT)

    # Section: Set up basic data
    # This section has no side effects but generates data that we will want
    # to use later.
    @rule(
        target=paths,
        source=st.lists(files, min_size=1).map(lambda l: os.path.join(*l)))
    def genpath(self, source):
        return source

    @rule(
        target=committimes,
        when=datetimes(min_year=1970, max_year=2038) | st.none())
    def gentime(self, when):
        return when

    @rule(
        target=contents,
        content=st.one_of(
            st.binary(),
            st.text().map(lambda x: x.encode('utf-8'))
        ))
    def gencontent(self, content):
        return content

    @rule(target=paths, source=paths)
    def lowerpath(self, source):
        return source.lower()

    @rule(target=paths, source=paths)
    def upperpath(self, source):
        return source.upper()

    # Section: Basic path operations
    @rule(path=paths, content=contents)
    def writecontent(self, path, content):
        self.unadded_changes = True
        if os.path.isdir(path):
            return
        parent = os.path.dirname(path)
        if parent:
            try:
                self.mkdirp(parent)
            except OSError:
                # It may be the case that there is a regular file that has
                # previously been created that has the same name as an ancestor
                # of the current path. This will cause mkdirp to fail with this
                # error. We just turn this into a no-op in that case.
                return
        with open(path, 'wb') as o:
            o.write(content)
        self.log.append((
            "$ python -c 'import binascii; "
            "print(binascii.unhexlify(\"%s\"))' > %s") % (
                binascii.hexlify(content),
                pipes.quote(path),
            ))

    @rule(path=paths)
    def addpath(self, path):
        if os.path.exists(path):
            self.hg("add", "--", path)

    @rule(path=paths)
    def forgetpath(self, path):
        if os.path.exists(path):
            with acceptableerrors(
                "file is already untracked",
            ):
                self.hg("forget", "--", path)

    @rule(s=st.none() | st.integers(0, 100))
    def addremove(self, s):
        args = ["addremove"]
        if s is not None:
            args.extend(["-s", str(s)])
        self.hg(*args)

    @rule(path=paths)
    def removepath(self, path):
        if os.path.exists(path):
            with acceptableerrors(
                'file is untracked',
                'file has been marked for add',
                'file is modified',
            ):
                self.hg("remove", "--", path)

    @rule(
        message=safetext,
        amend=st.booleans(),
        when=committimes,
        addremove=st.booleans(),
        secret=st.booleans(),
        close_branch=st.booleans(),
    )
    def maybecommit(
        self, message, amend, when, addremove, secret, close_branch
    ):
        command = ["commit"]
        errors = ["nothing changed"]
        if amend:
            errors.append("cannot amend public changesets")
            command.append("--amend")
        command.append("-m" + pipes.quote(message))
        if secret:
            command.append("--secret")
        if close_branch:
            command.append("--close-branch")
            errors.append("can only close branch heads")
        if addremove:
            command.append("--addremove")
        if when is not None:
            if when.year == 1970:
                errors.append('negative date value')
            if when.year == 2038:
                errors.append('exceeds 32 bits')
            command.append("--date=%s" % (
                when.strftime('%Y-%m-%d %H:%M:%S %z'),))

        with acceptableerrors(*errors):
            self.hg(*command)

    # Section: Simple side effect free "check" operations
    @rule()
    def log(self):
        self.hg("log")

    @rule()
    def verify(self):
        self.hg("verify")

    @rule()
    def diff(self):
        self.hg("diff", "--nodates")

    @rule()
    def status(self):
        self.hg("status")

    @rule()
    def export(self):
        self.hg("export")

settings.register_profile(
    'default',  settings(
        timeout=300,
        stateful_step_count=50,
        max_examples=10,
    )
)

settings.register_profile(
    'fast',  settings(
        timeout=10,
        stateful_step_count=20,
        max_examples=5,
        min_satisfying_examples=1,
        max_shrinks=0,
    )
)

settings.load_profile(os.getenv('HYPOTHESIS_PROFILE', 'default'))

verifyingtest = verifyingstatemachine.TestCase

verifyingtest.settings = settings.default

if __name__ == '__main__':
    try:
        silenttestrunner.main(__name__)
    finally:
        # So as to prevent proliferation of useless test files, if we never
        # actually wrote a failing test we clean up after ourselves and delete
        # the file for doing so that we owned.
        if os.path.exists(savefile) and os.path.getsize(savefile) == 0:
            os.unlink(savefile)
