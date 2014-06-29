  $ branchcache=.hg/cache/branch2

  $ listbranchcaches() {
  >    for f in .hg/cache/branch2*;
  >       do echo === $f ===;
  >       cat $f;
  >     done;
  > }
  $ purgebranchcaches() {
  >     rm .hg/cache/branch2*
  > }

  $ hg init t
  $ cd t

  $ hg branches
  $ echo foo > a
  $ hg add a
  $ hg ci -m "initial"
  $ hg branch foo
  marked working directory as branch foo
  (branches are permanent and global, did you want a bookmark?)
  $ hg branch
  foo
  $ hg ci -m "add branch name"
  $ hg branch bar
  marked working directory as branch bar
  (branches are permanent and global, did you want a bookmark?)
  $ hg ci -m "change branch name"

Branch shadowing:

  $ hg branch default
  abort: a branch of the same name already exists
  (use 'hg update' to switch to it)
  [255]

  $ hg branch -f default
  marked working directory as branch default
  (branches are permanent and global, did you want a bookmark?)

  $ hg ci -m "clear branch name"
  created new head

There should be only one default branch head

  $ hg heads .
  changeset:   3:1c28f494dae6
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     clear branch name
  

  $ hg co foo
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg branch
  foo
  $ echo bleah > a
  $ hg ci -m "modify a branch"

  $ hg merge default
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)

  $ hg branch
  foo
  $ hg ci -m "merge"

  $ hg log
  changeset:   5:530046499edf
  branch:      foo
  tag:         tip
  parent:      4:adf1a74a7f7b
  parent:      3:1c28f494dae6
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     merge
  
  changeset:   4:adf1a74a7f7b
  branch:      foo
  parent:      1:6c0e42da283a
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     modify a branch
  
  changeset:   3:1c28f494dae6
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     clear branch name
  
  changeset:   2:c21617b13b22
  branch:      bar
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     change branch name
  
  changeset:   1:6c0e42da283a
  branch:      foo
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     add branch name
  
  changeset:   0:db01e8ea3388
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     initial
  
  $ hg branches
  foo                            5:530046499edf
  default                        3:1c28f494dae6 (inactive)
  bar                            2:c21617b13b22 (inactive)

  $ hg branches -q
  foo
  default
  bar

Test for invalid branch cache:

  $ hg rollback
  repository tip rolled back to revision 4 (undo commit)
  working directory now based on revisions 4 and 3

  $ cp ${branchcache}-served .hg/bc-invalid

  $ hg log -r foo
  changeset:   4:adf1a74a7f7b
  branch:      foo
  tag:         tip
  parent:      1:6c0e42da283a
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     modify a branch
  
  $ cp .hg/bc-invalid $branchcache

  $ hg --debug log -r foo
  changeset:   4:adf1a74a7f7b4cd193d12992f5d0d6a004ed21d6
  branch:      foo
  tag:         tip
  phase:       draft
  parent:      1:6c0e42da283a56b5edc5b4fadb491365ec7f5fa8
  parent:      -1:0000000000000000000000000000000000000000
  manifest:    1:8c342a37dfba0b3d3ce073562a00d8a813c54ffe
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  files:       a
  extra:       branch=foo
  description:
  modify a branch
  
  
  $ purgebranchcaches
  $ echo corrupted > $branchcache

  $ hg log -qr foo
  4:adf1a74a7f7b

  $ listbranchcaches
  === .hg/cache/branch2 ===
  corrupted
  === .hg/cache/branch2-served ===
  adf1a74a7f7b4cd193d12992f5d0d6a004ed21d6 4
  c21617b13b220988e7a2e26290fbe4325ffa7139 o bar
  1c28f494dae69a2f8fc815059d257eccf3fcfe75 o default
  adf1a74a7f7b4cd193d12992f5d0d6a004ed21d6 o foo

Push should update the branch cache:

  $ hg init ../target

Pushing just rev 0:

  $ hg push -qr 0 ../target

  $ (cd ../target/; listbranchcaches)
  === .hg/cache/branch2-base ===
  db01e8ea3388fd3c7c94e1436ea2bd6a53d581c5 0
  db01e8ea3388fd3c7c94e1436ea2bd6a53d581c5 o default

Pushing everything:

  $ hg push -qf ../target

  $ (cd ../target/; listbranchcaches)
  === .hg/cache/branch2-base ===
  adf1a74a7f7b4cd193d12992f5d0d6a004ed21d6 4
  c21617b13b220988e7a2e26290fbe4325ffa7139 o bar
  1c28f494dae69a2f8fc815059d257eccf3fcfe75 o default
  adf1a74a7f7b4cd193d12992f5d0d6a004ed21d6 o foo

Update with no arguments: tipmost revision of the current branch:

  $ hg up -q -C 0
  $ hg up -q
  $ hg id
  1c28f494dae6

  $ hg up -q 1
  $ hg up -q
  $ hg id
  adf1a74a7f7b (foo) tip

  $ hg branch foobar
  marked working directory as branch foobar
  (branches are permanent and global, did you want a bookmark?)

  $ hg up
  abort: branch foobar not found
  [255]

Fast-forward merge:

  $ hg branch ff
  marked working directory as branch ff
  (branches are permanent and global, did you want a bookmark?)

  $ echo ff > ff
  $ hg ci -Am'fast forward'
  adding ff

  $ hg up foo
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved

  $ hg merge ff
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)

  $ hg branch
  foo
  $ hg commit -m'Merge ff into foo'
  $ hg parents
  changeset:   6:185ffbfefa30
  branch:      foo
  tag:         tip
  parent:      4:adf1a74a7f7b
  parent:      5:1a3c27dc5e11
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     Merge ff into foo
  
  $ hg manifest
  a
  ff


Test merging, add 3 default heads and one test head:

  $ cd ..
  $ hg init merges
  $ cd merges
  $ echo a > a
  $ hg ci -Ama
  adding a

  $ echo b > b
  $ hg ci -Amb
  adding b

  $ hg up 0
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ echo c > c
  $ hg ci -Amc
  adding c
  created new head

  $ hg up 0
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ echo d > d
  $ hg ci -Amd
  adding d
  created new head

  $ hg up 0
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  $ hg branch test
  marked working directory as branch test
  (branches are permanent and global, did you want a bookmark?)
  $ echo e >> e
  $ hg ci -Ame
  adding e

  $ hg log
  changeset:   4:3a1e01ed1df4
  branch:      test
  tag:         tip
  parent:      0:cb9a9f314b8b
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     e
  
  changeset:   3:980f7dc84c29
  parent:      0:cb9a9f314b8b
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     d
  
  changeset:   2:d36c0562f908
  parent:      0:cb9a9f314b8b
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     c
  
  changeset:   1:d2ae7f538514
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     b
  
  changeset:   0:cb9a9f314b8b
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     a
  
Implicit merge with test branch as parent:

  $ hg merge
  abort: branch 'test' has one head - please merge with an explicit rev
  (run 'hg heads' to see all heads)
  [255]
  $ hg up -C default
  1 files updated, 0 files merged, 1 files removed, 0 files unresolved

Implicit merge with default branch as parent:

  $ hg merge
  abort: branch 'default' has 3 heads - please merge with an explicit rev
  (run 'hg heads .' to see heads)
  [255]

3 branch heads, explicit merge required:

  $ hg merge 2
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  $ hg ci -m merge

2 branch heads, implicit merge works:

  $ hg merge
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)

  $ cd ..
