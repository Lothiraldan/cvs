#require svn svn-bindings

  $ filter_svn_output () {
  >     egrep -v 'Committing|Updating' | sed -e 's/done$//' || true
  > }

  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > convert =
  > [convert]
  > svn.trunk = mytrunk
  > EOF

  $ svnadmin create svn-repo
  $ SVNREPOPATH=`pwd`/svn-repo
#if windows
  $ SVNREPOURL=file:///`$PYTHON -c "import urllib, sys; sys.stdout.write(urllib.quote(sys.argv[1]))" "$SVNREPOPATH"`
#else
  $ SVNREPOURL=file://`$PYTHON -c "import urllib, sys; sys.stdout.write(urllib.quote(sys.argv[1]))" "$SVNREPOPATH"`
#endif
  $ INVALIDREVISIONID=svn:x2147622-4a9f-4db4-a8d3-13562ff547b2/proj%20B/mytrunk@1
  $ VALIDREVISIONID=svn:a2147622-4a9f-4db4-a8d3-13562ff547b2/proj%20B/mytrunk/mytrunk@1

Now test that it works with trunk/tags layout, but no branches yet.

Initial svn import

  $ mkdir projB
  $ cd projB
  $ mkdir mytrunk
  $ mkdir tags
  $ cd ..

  $ svn import -m "init projB" projB "$SVNREPOURL/proj%20B" | filter_svn_output | sort
  Adding         projB/mytrunk (glob)
  Adding         projB/tags (glob)
  Committed revision 1.

Update svn repository

  $ svn co "$SVNREPOURL/proj%20B/mytrunk" B | filter_svn_output
  Checked out revision 1.
  $ cd B
  $ echo hello > 'letter .txt'
  $ svn add 'letter .txt' | filter_svn_output
  A         letter .txt
  $ svn ci -m hello | filter_svn_output
  Adding         letter .txt
  Transmitting file data .
  Committed revision 2.

  $ svn-safe-append.py world 'letter .txt'
  $ svn ci -m world | filter_svn_output
  Sending        letter .txt
  Transmitting file data .
  Committed revision 3.

  $ svn copy -m "tag v0.1" "$SVNREPOURL/proj%20B/mytrunk" "$SVNREPOURL/proj%20B/tags/v0.1" | filter_svn_output
  Committed revision 4.

  $ svn-safe-append.py 'nice day today!' 'letter .txt'
  $ svn ci -m "nice day" | filter_svn_output
  Sending        letter .txt
  Transmitting file data .
  Committed revision 5.
  $ cd ..

Convert to hg once and also test localtimezone option

NOTE: This doesn't check all time zones -- it merely determines that
the configuration option is taking effect.

An arbitrary (U.S.) time zone is used here.  TZ=US/Hawaii is selected
since it does not use DST (unlike other U.S. time zones) and is always
a fixed difference from UTC.

  $ TZ=US/Hawaii hg convert --config convert.localtimezone=True "$SVNREPOURL/proj%20B" B-hg
  initializing destination B-hg repository
  scanning source...
  sorting...
  converting...
  3 init projB
  2 hello
  1 world
  0 nice day
  updating tags

Update svn repository again

  $ cd B
  $ svn-safe-append.py "see second letter" 'letter .txt'
  $ echo "nice to meet you" > letter2.txt
  $ svn add letter2.txt | filter_svn_output
  A         letter2.txt
  $ svn ci -m "second letter" | filter_svn_output
  Sending        letter .txt
  Adding         letter2.txt
  Transmitting file data ..
  Committed revision 6.

  $ svn copy -m "tag v0.2" "$SVNREPOURL/proj%20B/mytrunk" "$SVNREPOURL/proj%20B/tags/v0.2" | filter_svn_output
  Committed revision 7.

  $ svn-safe-append.py "blah-blah-blah" letter2.txt
  $ svn ci -m "work in progress" | filter_svn_output
  Sending        letter2.txt
  Transmitting file data .
  Committed revision 8.
  $ cd ..

  $ hg convert -s svn "$SVNREPOURL/proj%20B/non-existent-path" dest
  initializing destination dest repository
  abort: no revision found in module /proj B/non-existent-path
  [255]

########################################

Test incremental conversion

  $ TZ=US/Hawaii hg convert --config convert.localtimezone=True "$SVNREPOURL/proj%20B" B-hg
  scanning source...
  sorting...
  converting...
  1 second letter
  0 work in progress
  updating tags

  $ cd B-hg
  $ hg log -G --template '{rev} {desc|firstline} date: {date|date} files: {files}\n'
  o  7 update tags date: * +0000 files: .hgtags (glob)
  |
  o  6 work in progress date: * -1000 files: letter2.txt (glob)
  |
  o  5 second letter date: * -1000 files: letter .txt letter2.txt (glob)
  |
  o  4 update tags date: * +0000 files: .hgtags (glob)
  |
  o  3 nice day date: * -1000 files: letter .txt (glob)
  |
  o  2 world date: * -1000 files: letter .txt (glob)
  |
  o  1 hello date: * -1000 files: letter .txt (glob)
  |
  o  0 init projB date: * -1000 files: (glob)
  
  $ hg tags -q
  tip
  v0.2
  v0.1
  $ cd ..

Test filemap
  $ echo 'include letter2.txt' > filemap
  $ hg convert --filemap filemap "$SVNREPOURL/proj%20B/mytrunk" fmap
  initializing destination fmap repository
  scanning source...
  sorting...
  converting...
  5 init projB
  4 hello
  3 world
  2 nice day
  1 second letter
  0 work in progress
  $ hg -R fmap branch -q
  default
  $ hg log -G -R fmap --template '{rev} {desc|firstline} files: {files}\n'
  o  1 work in progress files: letter2.txt
  |
  o  0 second letter files: letter2.txt
  
Convert with --full adds and removes files that didn't change

  $ cd B
  $ echo >> "letter .txt"
  $ svn ci -m 'nothing' | filter_svn_output
  Sending        letter .txt
  Transmitting file data .
  Committed revision 9.
  $ cd ..

  $ echo 'rename letter2.txt letter3.txt' > filemap
  $ hg convert --filemap filemap --full "$SVNREPOURL/proj%20B/mytrunk" fmap
  scanning source...
  sorting...
  converting...
  0 nothing
  $ hg -R fmap st --change tip
  A letter .txt
  A letter3.txt
  R letter2.txt

test invalid splicemap1

  $ cat > splicemap <<EOF
  > $INVALIDREVISIONID $VALIDREVISIONID
  > EOF
  $ hg convert --splicemap splicemap "$SVNREPOURL/proj%20B/mytrunk" smap
  initializing destination smap repository
  abort: splicemap entry svn:x2147622-4a9f-4db4-a8d3-13562ff547b2/proj%20B/mytrunk@1 is not a valid revision identifier
  [255]

Test stop revision
  $ hg convert --rev 1 "$SVNREPOURL/proj%20B/mytrunk" stoprev
  initializing destination stoprev repository
  scanning source...
  sorting...
  converting...
  0 init projB
  $ hg -R stoprev branch -q
  default

Check convert_revision extra-records.
This is also the only place testing more than one extra field in a revision.

  $ cd stoprev
  $ hg tip --debug | grep extra
  extra:       branch=default
  extra:       convert_revision=svn:........-....-....-....-............/proj B/mytrunk@1 (re)
  $ cd ..

Test converting empty heads (issue3347).
Also tests getting logs directly without debugsvnlog.

  $ svnadmin create svn-empty
  $ svnadmin load -q svn-empty < "$TESTDIR/svn/empty.svndump"
  $ hg --config convert.svn.trunk= --config convert.svn.debugsvnlog=0 convert svn-empty
  assuming destination svn-empty-hg
  initializing destination svn-empty-hg repository
  scanning source...
  sorting...
  converting...
  1 init projA
  0 adddir
  $ hg --config convert.svn.trunk= convert "$SVNREPOURL/../svn-empty/trunk"
  assuming destination trunk-hg
  initializing destination trunk-hg repository
  scanning source...
  sorting...
  converting...
  1 init projA
  0 adddir

Test that a too-new repository format is properly rejected:
  $ mv svn-empty/format format
  $ echo 999 > svn-empty/format
It's important that this command explicitly specify svn, otherwise it
can have surprising side effects (like falling back to a perforce
depot that can be seen from the test environment and slurping from that.)
  $ hg convert --source-type svn svn-empty this-will-fail
  initializing destination this-will-fail repository
  file:/*/$TESTTMP/svn-empty does not look like a Subversion repository to libsvn version 1.*.* (glob)
  abort: svn-empty: missing or unsupported repository
  [255]
  $ mv format svn-empty/format
