Simple commands:

  $ echo foo
  foo
  $ printf 'oh no'
  oh no (no-eol)
  $ printf 'bar\nbaz\n' | cat
  bar
  baz

Multi-line command:

  $ foo() {
  >     echo bar
  > }
  $ foo
  bar

Return codes before inline python:

  $ sh -c 'exit 1'
  [1]

Doctest commands:

  >>> print 'foo'
  foo
  $ echo interleaved
  interleaved
  >>> for c in 'xyz':
  ...     print c
  x
  y
  z
  >>> print
  

Regular expressions:

  $ echo foobarbaz
  foobar.* (re)
  $ echo barbazquux
  .*quux.* (re)

Globs:

  $ printf '* \\foobarbaz {10}\n'
  \* \\fo?bar* {10} (glob)

Literal match ending in " (re)":

  $ echo 'foo (re)'
  foo (re)

Windows: \r\n is handled like \n and can be escaped:

#if windows
  $ printf 'crlf\r\ncr\r\tcrlf\r\ncrcrlf\r\r\n'
  crlf
  cr\r (no-eol) (esc)
  \tcrlf (esc)
  crcrlf\r (esc)
#endif

Combining esc with other markups - and handling lines ending with \r instead of \n:

  $ printf 'foo/bar\r'
  foo/bar\r (no-eol) (glob) (esc)
#if windows
  $ printf 'foo\\bar\r'
  foo/bar\r (no-eol) (glob) (esc)
#endif
  $ printf 'foo/bar\rfoo/bar\r'
  foo.bar\r \(no-eol\) (re) (esc)
  foo.bar\r \(no-eol\) (re)

testing hghave

  $ "$TESTDIR/hghave" true
  $ "$TESTDIR/hghave" false
  skipped: missing feature: nail clipper
  [1]
  $ "$TESTDIR/hghave" no-true
  skipped: system supports yak shaving
  [1]
  $ "$TESTDIR/hghave" no-false

Conditional sections based on hghave:

#if true
  $ echo tested
  tested
#else
  $ echo skipped
#endif

#if false
  $ echo skipped
#else
  $ echo tested
  tested
#endif

#if no-false
  $ echo tested
  tested
#else
  $ echo skipped
#endif

#if no-true
  $ echo skipped
#else
  $ echo tested
  tested
#endif

Exit code:

  $ (exit 1)
  [1]
