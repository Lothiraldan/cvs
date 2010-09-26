
  $ cp "$TESTDIR"/printenv.py .

This test tries to exercise the ssh functionality with a dummy script

  $ cat <<EOF > dummyssh
  > import sys
  > import os
  > os.chdir(os.path.dirname(sys.argv[0]))
  > if sys.argv[1] != "user@dummy":
  >     sys.exit(-1)
  > if not os.path.exists("dummyssh"):
  >     sys.exit(-1)
  > os.environ["SSH_CLIENT"] = "127.0.0.1 1 2"
  > log = open("dummylog", "ab")
  > log.write("Got arguments")
  > for i, arg in enumerate(sys.argv[1:]):
  >     log.write(" %d:%s" % (i+1, arg))
  > log.write("\n")
  > log.close()
  > r = os.system(sys.argv[2])
  > sys.exit(bool(r))
  > EOF
  $ cat <<EOF > badhook
  > import sys
  > sys.stdout.write("KABOOM\n")
  > EOF

creating 'remote'

  $ hg init remote
  $ cd remote
  $ echo this > foo
  $ echo this > fooO
  $ hg ci -A -m "init" foo fooO
  $ echo '[server]' > .hg/hgrc
  $ echo 'uncompressed = True' >> .hg/hgrc
  $ echo '[hooks]' >> .hg/hgrc
  $ echo 'changegroup = python ../printenv.py changegroup-in-remote 0 ../dummylog' >> .hg/hgrc
  $ cd ..

repo not found error

  $ hg clone -e "python ./dummyssh" ssh://user@dummy/nonexistent local
  remote: abort: There is no Mercurial repository here (.hg not found)!
  abort: no suitable response from remote hg!
  [255]

non-existent absolute path

  $ hg clone -e "python ./dummyssh" ssh://user@dummy//$HGTMP/nonexistent local
  remote: abort: There is no Mercurial repository here (.hg not found)!
  abort: no suitable response from remote hg!
  [255]

clone remote via stream

  $ hg clone -e "python ./dummyssh" --uncompressed ssh://user@dummy/remote local-stream 2>&1 | \
  >   sed -e 's/[0-9][0-9.]*/XXX/g' -e 's/[KM]\(B\/sec\)/X\1/'
  streaming all changes
  XXX files to transfer, XXX bytes of data
  transferred XXX bytes in XXX seconds (XXX XB/sec)
  updating to branch default
  XXX files updated, XXX files merged, XXX files removed, XXX files unresolved
  $ cd local-stream
  $ hg verify
  checking changesets
  checking manifests
  crosschecking files in changesets and manifests
  checking files
  2 files, 1 changesets, 2 total revisions
  $ cd ..

clone remote via pull

  $ hg clone -e "python ./dummyssh" ssh://user@dummy/remote local
  requesting all changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 2 changes to 2 files
  updating to branch default
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved

verify

  $ cd local
  $ hg verify
  checking changesets
  checking manifests
  crosschecking files in changesets and manifests
  checking files
  2 files, 1 changesets, 2 total revisions
  $ echo '[hooks]' >> .hg/hgrc
  $ echo 'changegroup = python ../printenv.py changegroup-in-local 0 ../dummylog' >> .hg/hgrc

empty default pull

  $ hg paths
  default = ssh://user@dummy/remote
  $ hg pull -e "python ../dummyssh"
  pulling from ssh://user@dummy/remote
  searching for changes
  no changes found

local change

  $ echo bleah > foo
  $ hg ci -m "add"

updating rc

  $ echo "default-push = ssh://user@dummy/remote" >> .hg/hgrc
  $ echo "[ui]" >> .hg/hgrc
  $ echo "ssh = python ../dummyssh" >> .hg/hgrc

find outgoing

  $ hg out ssh://user@dummy/remote
  comparing with ssh://user@dummy/remote
  searching for changes
  changeset:   1:a28a9d1a809c
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     add
  

find incoming on the remote side

  $ hg incoming -R ../remote -e "python ../dummyssh" ssh://user@dummy/local
  comparing with ssh://user@dummy/local
  searching for changes
  changeset:   1:a28a9d1a809c
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     add
  

push

  $ hg push
  pushing to ssh://user@dummy/remote
  searching for changes
  remote: adding changesets
  remote: adding manifests
  remote: adding file changes
  remote: added 1 changesets with 1 changes to 1 files
  $ cd ../remote

check remote tip

  $ hg tip
  changeset:   1:a28a9d1a809c
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     add
  
  $ hg verify
  checking changesets
  checking manifests
  crosschecking files in changesets and manifests
  checking files
  2 files, 2 changesets, 3 total revisions
  $ hg cat -r tip foo
  bleah
  $ echo z > z
  $ hg ci -A -m z z
  created new head

a bad, evil hook that prints to stdout

  $ echo 'changegroup.stdout = python ../badhook' >> .hg/hgrc
  $ cd ../local
  $ echo r > r
  $ hg ci -A -m z r

push should succeed even though it has an unexpected response

  $ hg push
  pushing to ssh://user@dummy/remote
  searching for changes
  note: unsynced remote changes!
  remote: adding changesets
  remote: adding manifests
  remote: adding file changes
  remote: added 1 changesets with 1 changes to 1 files
  remote: KABOOM
  $ hg -R ../remote heads
  changeset:   3:1383141674ec
  tag:         tip
  parent:      1:a28a9d1a809c
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     z
  
  changeset:   2:6c0482d977a3
  parent:      0:1160648e36ce
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     z
  
  $ cd ..
  $ cat dummylog
  Got arguments 1:user@dummy 2:hg -R nonexistent serve --stdio
  Got arguments 1:user@dummy 2:hg -R */nonexistent serve --stdio (glob)
  Got arguments 1:user@dummy 2:hg -R remote serve --stdio
  Got arguments 1:user@dummy 2:hg -R remote serve --stdio
  Got arguments 1:user@dummy 2:hg -R remote serve --stdio
  Got arguments 1:user@dummy 2:hg -R remote serve --stdio
  Got arguments 1:user@dummy 2:hg -R local serve --stdio
  Got arguments 1:user@dummy 2:hg -R remote serve --stdio
  changegroup-in-remote hook: HG_NODE=a28a9d1a809cab7d4e2fde4bee738a9ede948b60 HG_SOURCE=serve HG_URL=remote:ssh:127.0.0.1 
  Got arguments 1:user@dummy 2:hg -R remote serve --stdio
  changegroup-in-remote hook: HG_NODE=1383141674ec756a6056f6a9097618482fe0f4a6 HG_SOURCE=serve HG_URL=remote:ssh:127.0.0.1 
