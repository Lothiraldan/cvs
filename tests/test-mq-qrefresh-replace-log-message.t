Environment setup for MQ

  $ echo "[extensions]" >> $HGRCPATH
  $ echo "mq=" >> $HGRCPATH
  $ hg init
  $ hg qinit

Should fail if no patches applied
(this tests also that editor is not invoked if '--edit' is not
specified)

  $ hg qrefresh
  no patches applied
  [1]
  $ hg qrefresh -e
  no patches applied
  [1]
  $ hg qnew -m "First commit message" first-patch
  $ echo aaaa > file
  $ hg add file
  $ HGEDITOR=cat hg qrefresh

Should display 'First commit message'

  $ hg log -l1 --template "{desc}\n"
  First commit message

Testing changing message with -m
(this tests also that '--edit' can be used with '--message', and
that '[committemplate] changeset' definition and commit log specific
template keyword 'extramsg' work well)

  $ cat >> .hg/hgrc <<EOF
  > [committemplate]
  > changeset = HG: this is customized commit template
  >     {desc}\n\n
  >     HG: Enter commit message.  Lines beginning with 'HG:' are removed.
  >     HG: {extramsg}
  >     HG: --
  >     HG: user: {author}
  >     HG: branch '{branch}'\n{file_adds %
  >    "HG: added {file}\n"     }{file_mods %
  >    "HG: changed {file}\n"   }{file_dels %
  >    "HG: removed {file}\n"   }{if(files, "",
  >    "HG: no files changed\n")}
  > EOF

  $ echo bbbb > file
  $ HGEDITOR=cat hg qrefresh -m "Second commit message" -e
  HG: this is customized commit template
  Second commit message
  
  
  HG: Enter commit message.  Lines beginning with 'HG:' are removed.
  HG: Leave message empty to use default message.
  HG: --
  HG: user: test
  HG: branch 'default'
  HG: added file

  $ cat >> .hg/hgrc <<EOF
  > # disable customizing for subsequent tests
  > [committemplate]
  > changeset =
  > EOF

Should display 'Second commit message'

  $ hg log -l1 --template "{desc}\n"
  Second commit message

Testing changing message with -l

  $ echo "Third commit message" > logfile
  $ echo " This is the 3rd log message" >> logfile
  $ echo bbbb > file
  $ hg qrefresh -l logfile

Should display 'Third commit message\\\n This is the 3rd log message'

  $ hg log -l1 --template "{desc}\n"
  Third commit message
   This is the 3rd log message

Testing changing message with -l-

  $ hg qnew -m "First commit message" second-patch
  $ echo aaaa > file2
  $ hg add file2
  $ echo bbbb > file2
  $ (echo "Fifth commit message"; echo " This is the 5th log message") | hg qrefresh -l-

Should display 'Fifth commit message\\\n This is the 5th log message'

  $ hg log -l1 --template "{desc}\n"
  Fifth commit message
   This is the 5th log message

Test saving last-message.txt:

  $ cat > $TESTTMP/editor.sh << EOF
  > echo "==== before editing"
  > cat \$1
  > echo "===="
  > (echo; echo "test saving last-message.txt") >> \$1
  > EOF

  $ cat > $TESTTMP/commitfailure.py <<EOF
  > from mercurial import util
  > def reposetup(ui, repo):
  >     class commitfailure(repo.__class__):
  >         def commit(self, *args, **kwargs):
  >             raise util.Abort('emulating unexpected abort')
  >     repo.__class__ = commitfailure
  > EOF

  $ cat >> .hg/hgrc <<EOF
  > [extensions]
  > # this failure occurs before editor invocation
  > commitfailure = $TESTTMP/commitfailure.py
  > EOF

  $ hg qapplied
  first-patch
  second-patch
  $ hg tip --template "{files}\n"
  file2

(test that editor is not invoked before transaction starting)

  $ rm -f .hg/last-message.txt
  $ HGEDITOR="sh $TESTTMP/editor.sh" hg qrefresh -e
  refresh interrupted while patch was popped! (revert --all, qpush to recover)
  abort: emulating unexpected abort
  [255]
  $ test -f .hg/last-message.txt
  [1]

(reset applied patches and directory status)

  $ cat >> .hg/hgrc <<EOF
  > [extensions]
  > commitfailure = !
  > EOF

  $ hg qapplied
  first-patch
  $ hg status -A file2
  ? file2
  $ rm file2
  $ hg qpush -q second-patch
  now at: second-patch

(test that editor is invoked and commit message is saved into
"last-message.txt")

  $ cat >> .hg/hgrc <<EOF
  > [hooks]
  > # this failure occurs after editor invocation
  > pretxncommit.unexpectedabort = false
  > EOF

  $ rm -f .hg/last-message.txt
  $ hg status --rev "second-patch^1" -arm
  A file2
  $ HGEDITOR="sh $TESTTMP/editor.sh" hg qrefresh -e
  ==== before editing
  Fifth commit message
   This is the 5th log message
  
  
  HG: Enter commit message.  Lines beginning with 'HG:' are removed.
  HG: Leave message empty to use default message.
  HG: --
  HG: user: test
  HG: branch 'default'
  HG: added file2
  ====
  transaction abort!
  rollback completed
  note: commit message saved in .hg/last-message.txt
  refresh interrupted while patch was popped! (revert --all, qpush to recover)
  abort: pretxncommit.unexpectedabort hook exited with status 1
  [255]
  $ cat .hg/last-message.txt
  Fifth commit message
   This is the 5th log message
  
  
  
  test saving last-message.txt
