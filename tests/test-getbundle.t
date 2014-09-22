  $ "$TESTDIR/hghave" serve || exit 80

= Test the getbundle() protocol function =

Create a test repository:

  $ hg init repo
  $ cd repo
  $ hg debugbuilddag -n -m '+2 :fork +5 :p1 *fork +6 :p2 /p1 :m1 +3' > /dev/null
  $ hg log -G --template '{node}\n'
  o  10c14a2cc935e1d8c31f9e98587dcf27fb08a6da
  |
  o  4801a72e5d88cb515b0c7e40fae34180f3f837f2
  |
  o  0b2f73f04880d9cb6a5cd8a757f0db0ad01e32c3
  |
  o    8365676dbab05860ce0d9110f2af51368b961bbd
  |\
  | o  5686dbbd9fc46cb806599c878d02fe1cb56b83d3
  | |
  | o  13c0170174366b441dc68e8e33757232fa744458
  | |
  | o  63476832d8ec6558cf9bbe3cbe0c757e5cf18043
  | |
  | o  700b7e19db54103633c4bf4a6a6b6d55f4d50c03
  | |
  | o  928b5f94cdb278bb536eba552de348a4e92ef24d
  | |
  | o  f34414c64173e0ecb61b25dc55e116dbbcc89bee
  | |
  | o  8931463777131cd73923e560b760061f2aa8a4bc
  | |
  o |  6621d79f61b23ec74cf4b69464343d9e0980ec8b
  | |
  o |  bac16991d12ff45f9dc43c52da1946dfadb83e80
  | |
  o |  ff42371d57168345fdf1a3aac66a51f6a45d41d2
  | |
  o |  d5f6e1ea452285324836a49d7d3c2a63cfed1d31
  | |
  o |  713346a995c363120712aed1aee7e04afd867638
  |/
  o  29a4d1f17bd3f0779ca0525bebb1cfb51067c738
  |
  o  7704483d56b2a7b5db54dcee7c62378ac629b348
  
  $ cd ..


= Test locally =

Get everything:

  $ hg debuggetbundle repo bundle
  $ hg debugbundle bundle
  7704483d56b2a7b5db54dcee7c62378ac629b348
  29a4d1f17bd3f0779ca0525bebb1cfb51067c738
  713346a995c363120712aed1aee7e04afd867638
  d5f6e1ea452285324836a49d7d3c2a63cfed1d31
  ff42371d57168345fdf1a3aac66a51f6a45d41d2
  bac16991d12ff45f9dc43c52da1946dfadb83e80
  6621d79f61b23ec74cf4b69464343d9e0980ec8b
  8931463777131cd73923e560b760061f2aa8a4bc
  f34414c64173e0ecb61b25dc55e116dbbcc89bee
  928b5f94cdb278bb536eba552de348a4e92ef24d
  700b7e19db54103633c4bf4a6a6b6d55f4d50c03
  63476832d8ec6558cf9bbe3cbe0c757e5cf18043
  13c0170174366b441dc68e8e33757232fa744458
  5686dbbd9fc46cb806599c878d02fe1cb56b83d3
  8365676dbab05860ce0d9110f2af51368b961bbd
  0b2f73f04880d9cb6a5cd8a757f0db0ad01e32c3
  4801a72e5d88cb515b0c7e40fae34180f3f837f2
  10c14a2cc935e1d8c31f9e98587dcf27fb08a6da

Get part of linear run:

  $ hg debuggetbundle repo bundle -H 4801a72e5d88cb515b0c7e40fae34180f3f837f2 -C 8365676dbab05860ce0d9110f2af51368b961bbd
  $ hg debugbundle bundle
  0b2f73f04880d9cb6a5cd8a757f0db0ad01e32c3
  4801a72e5d88cb515b0c7e40fae34180f3f837f2

Get missing branch and merge:

  $ hg debuggetbundle repo bundle -H 4801a72e5d88cb515b0c7e40fae34180f3f837f2 -C 13c0170174366b441dc68e8e33757232fa744458
  $ hg debugbundle bundle
  713346a995c363120712aed1aee7e04afd867638
  d5f6e1ea452285324836a49d7d3c2a63cfed1d31
  ff42371d57168345fdf1a3aac66a51f6a45d41d2
  bac16991d12ff45f9dc43c52da1946dfadb83e80
  6621d79f61b23ec74cf4b69464343d9e0980ec8b
  5686dbbd9fc46cb806599c878d02fe1cb56b83d3
  8365676dbab05860ce0d9110f2af51368b961bbd
  0b2f73f04880d9cb6a5cd8a757f0db0ad01e32c3
  4801a72e5d88cb515b0c7e40fae34180f3f837f2

Get from only one head:

  $ hg debuggetbundle repo bundle -H 928b5f94cdb278bb536eba552de348a4e92ef24d -C 29a4d1f17bd3f0779ca0525bebb1cfb51067c738
  $ hg debugbundle bundle
  8931463777131cd73923e560b760061f2aa8a4bc
  f34414c64173e0ecb61b25dc55e116dbbcc89bee
  928b5f94cdb278bb536eba552de348a4e92ef24d

Get parts of two branches:

  $ hg debuggetbundle repo bundle -H 13c0170174366b441dc68e8e33757232fa744458 -C 700b7e19db54103633c4bf4a6a6b6d55f4d50c03 -H bac16991d12ff45f9dc43c52da1946dfadb83e80 -C d5f6e1ea452285324836a49d7d3c2a63cfed1d31
  $ hg debugbundle bundle
  ff42371d57168345fdf1a3aac66a51f6a45d41d2
  bac16991d12ff45f9dc43c52da1946dfadb83e80
  63476832d8ec6558cf9bbe3cbe0c757e5cf18043
  13c0170174366b441dc68e8e33757232fa744458

Check that we get all needed file changes:

  $ hg debugbundle bundle --all
  format: id, p1, p2, cset, delta base, len(delta)
  
  changelog
  ff42371d57168345fdf1a3aac66a51f6a45d41d2 d5f6e1ea452285324836a49d7d3c2a63cfed1d31 0000000000000000000000000000000000000000 ff42371d57168345fdf1a3aac66a51f6a45d41d2 d5f6e1ea452285324836a49d7d3c2a63cfed1d31 99
  bac16991d12ff45f9dc43c52da1946dfadb83e80 ff42371d57168345fdf1a3aac66a51f6a45d41d2 0000000000000000000000000000000000000000 bac16991d12ff45f9dc43c52da1946dfadb83e80 ff42371d57168345fdf1a3aac66a51f6a45d41d2 99
  63476832d8ec6558cf9bbe3cbe0c757e5cf18043 700b7e19db54103633c4bf4a6a6b6d55f4d50c03 0000000000000000000000000000000000000000 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 bac16991d12ff45f9dc43c52da1946dfadb83e80 102
  13c0170174366b441dc68e8e33757232fa744458 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 0000000000000000000000000000000000000000 13c0170174366b441dc68e8e33757232fa744458 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 102
  
  manifest
  dac7984588fc4eea7acbf39693a9c1b06f5b175d 591f732a3faf1fb903815273f3c199a514a61ccb 0000000000000000000000000000000000000000 ff42371d57168345fdf1a3aac66a51f6a45d41d2 591f732a3faf1fb903815273f3c199a514a61ccb 113
  0772616e6b48a76afb6c1458e193cbb3dae2e4ff dac7984588fc4eea7acbf39693a9c1b06f5b175d 0000000000000000000000000000000000000000 bac16991d12ff45f9dc43c52da1946dfadb83e80 dac7984588fc4eea7acbf39693a9c1b06f5b175d 113
  eb498cd9af6c44108e43041e951ce829e29f6c80 bff2f4817ced57b386caf7c4e3e36a4bc9af7e93 0000000000000000000000000000000000000000 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 0772616e6b48a76afb6c1458e193cbb3dae2e4ff 295
  b15709c071ddd2d93188508ba156196ab4f19620 eb498cd9af6c44108e43041e951ce829e29f6c80 0000000000000000000000000000000000000000 13c0170174366b441dc68e8e33757232fa744458 eb498cd9af6c44108e43041e951ce829e29f6c80 114
  
  mf
  4f73f97080266ab8e0c0561ca8d0da3eaf65b695 301ca08d026bb72cb4258a9d211bdf7ca0bcd810 0000000000000000000000000000000000000000 ff42371d57168345fdf1a3aac66a51f6a45d41d2 301ca08d026bb72cb4258a9d211bdf7ca0bcd810 17
  c7b583de053293870e145f45bd2d61643563fd06 4f73f97080266ab8e0c0561ca8d0da3eaf65b695 0000000000000000000000000000000000000000 bac16991d12ff45f9dc43c52da1946dfadb83e80 4f73f97080266ab8e0c0561ca8d0da3eaf65b695 18
  266ee3c0302a5a18f1cf96817ac79a51836179e9 edc0f6b8db80d68ae6aff2b19f7e5347ab68fa63 0000000000000000000000000000000000000000 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 c7b583de053293870e145f45bd2d61643563fd06 149
  698c6a36220548cd3903ca7dada27c59aa500c52 266ee3c0302a5a18f1cf96817ac79a51836179e9 0000000000000000000000000000000000000000 13c0170174366b441dc68e8e33757232fa744458 266ee3c0302a5a18f1cf96817ac79a51836179e9 19
  
  nf11
  33fbc651630ffa7ccbebfe4eb91320a873e7291c 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 0000000000000000000000000000000000000000 16
  
  nf12
  ddce0544363f037e9fb889faca058f52dc01c0a5 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 13c0170174366b441dc68e8e33757232fa744458 0000000000000000000000000000000000000000 16
  
  nf4
  3c1407305701051cbed9f9cb9a68bdfb5997c235 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 ff42371d57168345fdf1a3aac66a51f6a45d41d2 0000000000000000000000000000000000000000 15
  
  nf5
  0dbd89c185f53a1727c54cd1ce256482fa23968e 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 bac16991d12ff45f9dc43c52da1946dfadb83e80 0000000000000000000000000000000000000000 15

Get branch and merge:

  $ hg debuggetbundle repo bundle -C 7704483d56b2a7b5db54dcee7c62378ac629b348 -H 0b2f73f04880d9cb6a5cd8a757f0db0ad01e32c3
  $ hg debugbundle bundle
  29a4d1f17bd3f0779ca0525bebb1cfb51067c738
  713346a995c363120712aed1aee7e04afd867638
  d5f6e1ea452285324836a49d7d3c2a63cfed1d31
  ff42371d57168345fdf1a3aac66a51f6a45d41d2
  bac16991d12ff45f9dc43c52da1946dfadb83e80
  6621d79f61b23ec74cf4b69464343d9e0980ec8b
  8931463777131cd73923e560b760061f2aa8a4bc
  f34414c64173e0ecb61b25dc55e116dbbcc89bee
  928b5f94cdb278bb536eba552de348a4e92ef24d
  700b7e19db54103633c4bf4a6a6b6d55f4d50c03
  63476832d8ec6558cf9bbe3cbe0c757e5cf18043
  13c0170174366b441dc68e8e33757232fa744458
  5686dbbd9fc46cb806599c878d02fe1cb56b83d3
  8365676dbab05860ce0d9110f2af51368b961bbd
  0b2f73f04880d9cb6a5cd8a757f0db0ad01e32c3


= Test via HTTP =

Get everything:

  $ hg serve -R repo -p $HGPORT -d --pid-file=hg.pid -E error.log -A access.log
  $ cat hg.pid >> $DAEMON_PIDS
  $ hg debuggetbundle http://localhost:$HGPORT/ bundle
  $ hg debugbundle bundle
  7704483d56b2a7b5db54dcee7c62378ac629b348
  29a4d1f17bd3f0779ca0525bebb1cfb51067c738
  713346a995c363120712aed1aee7e04afd867638
  d5f6e1ea452285324836a49d7d3c2a63cfed1d31
  ff42371d57168345fdf1a3aac66a51f6a45d41d2
  bac16991d12ff45f9dc43c52da1946dfadb83e80
  6621d79f61b23ec74cf4b69464343d9e0980ec8b
  8931463777131cd73923e560b760061f2aa8a4bc
  f34414c64173e0ecb61b25dc55e116dbbcc89bee
  928b5f94cdb278bb536eba552de348a4e92ef24d
  700b7e19db54103633c4bf4a6a6b6d55f4d50c03
  63476832d8ec6558cf9bbe3cbe0c757e5cf18043
  13c0170174366b441dc68e8e33757232fa744458
  5686dbbd9fc46cb806599c878d02fe1cb56b83d3
  8365676dbab05860ce0d9110f2af51368b961bbd
  0b2f73f04880d9cb6a5cd8a757f0db0ad01e32c3
  4801a72e5d88cb515b0c7e40fae34180f3f837f2
  10c14a2cc935e1d8c31f9e98587dcf27fb08a6da

Get parts of two branches:

  $ hg debuggetbundle http://localhost:$HGPORT/ bundle -H 13c0170174366b441dc68e8e33757232fa744458 -C 700b7e19db54103633c4bf4a6a6b6d55f4d50c03 -H bac16991d12ff45f9dc43c52da1946dfadb83e80 -C d5f6e1ea452285324836a49d7d3c2a63cfed1d31
  $ hg debugbundle bundle
  ff42371d57168345fdf1a3aac66a51f6a45d41d2
  bac16991d12ff45f9dc43c52da1946dfadb83e80
  63476832d8ec6558cf9bbe3cbe0c757e5cf18043
  13c0170174366b441dc68e8e33757232fa744458

Check that we get all needed file changes:

  $ hg debugbundle bundle --all
  format: id, p1, p2, cset, delta base, len(delta)
  
  changelog
  ff42371d57168345fdf1a3aac66a51f6a45d41d2 d5f6e1ea452285324836a49d7d3c2a63cfed1d31 0000000000000000000000000000000000000000 ff42371d57168345fdf1a3aac66a51f6a45d41d2 d5f6e1ea452285324836a49d7d3c2a63cfed1d31 99
  bac16991d12ff45f9dc43c52da1946dfadb83e80 ff42371d57168345fdf1a3aac66a51f6a45d41d2 0000000000000000000000000000000000000000 bac16991d12ff45f9dc43c52da1946dfadb83e80 ff42371d57168345fdf1a3aac66a51f6a45d41d2 99
  63476832d8ec6558cf9bbe3cbe0c757e5cf18043 700b7e19db54103633c4bf4a6a6b6d55f4d50c03 0000000000000000000000000000000000000000 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 bac16991d12ff45f9dc43c52da1946dfadb83e80 102
  13c0170174366b441dc68e8e33757232fa744458 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 0000000000000000000000000000000000000000 13c0170174366b441dc68e8e33757232fa744458 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 102
  
  manifest
  dac7984588fc4eea7acbf39693a9c1b06f5b175d 591f732a3faf1fb903815273f3c199a514a61ccb 0000000000000000000000000000000000000000 ff42371d57168345fdf1a3aac66a51f6a45d41d2 591f732a3faf1fb903815273f3c199a514a61ccb 113
  0772616e6b48a76afb6c1458e193cbb3dae2e4ff dac7984588fc4eea7acbf39693a9c1b06f5b175d 0000000000000000000000000000000000000000 bac16991d12ff45f9dc43c52da1946dfadb83e80 dac7984588fc4eea7acbf39693a9c1b06f5b175d 113
  eb498cd9af6c44108e43041e951ce829e29f6c80 bff2f4817ced57b386caf7c4e3e36a4bc9af7e93 0000000000000000000000000000000000000000 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 0772616e6b48a76afb6c1458e193cbb3dae2e4ff 295
  b15709c071ddd2d93188508ba156196ab4f19620 eb498cd9af6c44108e43041e951ce829e29f6c80 0000000000000000000000000000000000000000 13c0170174366b441dc68e8e33757232fa744458 eb498cd9af6c44108e43041e951ce829e29f6c80 114
  
  mf
  4f73f97080266ab8e0c0561ca8d0da3eaf65b695 301ca08d026bb72cb4258a9d211bdf7ca0bcd810 0000000000000000000000000000000000000000 ff42371d57168345fdf1a3aac66a51f6a45d41d2 301ca08d026bb72cb4258a9d211bdf7ca0bcd810 17
  c7b583de053293870e145f45bd2d61643563fd06 4f73f97080266ab8e0c0561ca8d0da3eaf65b695 0000000000000000000000000000000000000000 bac16991d12ff45f9dc43c52da1946dfadb83e80 4f73f97080266ab8e0c0561ca8d0da3eaf65b695 18
  266ee3c0302a5a18f1cf96817ac79a51836179e9 edc0f6b8db80d68ae6aff2b19f7e5347ab68fa63 0000000000000000000000000000000000000000 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 c7b583de053293870e145f45bd2d61643563fd06 149
  698c6a36220548cd3903ca7dada27c59aa500c52 266ee3c0302a5a18f1cf96817ac79a51836179e9 0000000000000000000000000000000000000000 13c0170174366b441dc68e8e33757232fa744458 266ee3c0302a5a18f1cf96817ac79a51836179e9 19
  
  nf11
  33fbc651630ffa7ccbebfe4eb91320a873e7291c 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 63476832d8ec6558cf9bbe3cbe0c757e5cf18043 0000000000000000000000000000000000000000 16
  
  nf12
  ddce0544363f037e9fb889faca058f52dc01c0a5 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 13c0170174366b441dc68e8e33757232fa744458 0000000000000000000000000000000000000000 16
  
  nf4
  3c1407305701051cbed9f9cb9a68bdfb5997c235 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 ff42371d57168345fdf1a3aac66a51f6a45d41d2 0000000000000000000000000000000000000000 15
  
  nf5
  0dbd89c185f53a1727c54cd1ce256482fa23968e 0000000000000000000000000000000000000000 0000000000000000000000000000000000000000 bac16991d12ff45f9dc43c52da1946dfadb83e80 0000000000000000000000000000000000000000 15

Verify we hit the HTTP server:

  $ cat access.log
  * - - [*] "GET /?cmd=capabilities HTTP/1.1" 200 - (glob)
  * - - [*] "GET /?cmd=getbundle HTTP/1.1" 200 - (glob)
  * - - [*] "GET /?cmd=capabilities HTTP/1.1" 200 - (glob)
  * - - [*] "GET /?cmd=getbundle HTTP/1.1" 200 - x-hgarg-1:common=700b7e19db54103633c4bf4a6a6b6d55f4d50c03+d5f6e1ea452285324836a49d7d3c2a63cfed1d31&heads=13c0170174366b441dc68e8e33757232fa744458+bac16991d12ff45f9dc43c52da1946dfadb83e80 (glob)

  $ cat error.log

