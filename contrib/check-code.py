#!/usr/bin/env python
#
# check-code - a style and portability checker for Mercurial
#
# Copyright 2005-2007 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

import sys, re, glob

def repquote(m):
    t = re.sub(r"\S", "x", m.group(2))
    return m.group(1) + t + m.group(1)

def repcomment(m):
    return m.group(1) + "#" * len(m.group(2))

def repccomment(m):
    t = re.sub(r"((?<=\n) )|\S", "x", m.group(2))
    return m.group(1) + t + "*/"

def repcallspaces(m):
    t = re.sub(r"\n\s+", "\n", m.group(2))
    return m.group(1) + t

def repinclude(m):
    return m.group(1) + "<foo>"

def rephere(m):
    t = re.sub(r"\S", "x", m.group(2))
    return m.group(1) + t


testpats = [
    (r'(pushd|popd)', "don't use pushd|popd, use cd"),
    (r'\W\$?\(\([^\)]*\)\)', "don't use (()) or $(()), use expr"),
    (r'^function', "don't use 'function', use old style"),
    (r'grep.*-q', "don't use grep -q, redirect to /dev/null"),
    (r'echo.*\\n', "don't use 'echo \n', use printf"),
    (r'^diff.*-\w*N', "don't use diff -N"),
    (r'(^| )wc[^|]*$', "filter wc output"),
    (r'head -c', "don't use head -c, use dd"),
    (r'ls.*-\w*R', "don't use ls -R, use find"),
    (r'printf.*\\\d\d\d', "don't use printf \NNN, use python"),
    (r'printf.*\\x', "don't use printf \\x, use python"),
    (r'\$\(.*\)', "don't use $(expr), use `expr`"),
    (r'rm -rf \*', "don't use naked rm -rf, target a directory"),
    (r'(^|\|\s*)grep (-\w\s+)*[^|]*[(|]\w',
     "use egrep for extended grep syntax"),
    (r'/bin/', "don't use explicit paths for tools"),
    (r'\$PWD', "don't use $PWD, use `pwd`"),
    (r'[^\n]\Z', "no trailing newline"),
]

testfilters = [
    (r"( *)(#([^\n]*\S)?)", repcomment),
    (r"<<(\S+)((.|\n)*?\n\1)", rephere),
]

pypats = [
    (r'^\s*\t', "don't use tabs"),
    (r'(\S\s+|^\s+)\n', "trailing whitespace"),
    (r'\w,\w', "missing whitespace after ,"),
    (r'\w[+/*\-<>]\w', "missing whitespace in expression"),
    (r'^\s+\w+=\w+[^,)]$', "missing whitespace in assignment"),
    (r'.{85}', "line too long"),
    (r'[^\n]\Z', "no trailing newline"),
#    (r'^\s+[^_ ][^_. ]+_[^_]+\s*=', "don't use underbars in identifiers"),
#    (r'\w*[a-z][A-Z]\w*\s*=', "don't use camelcase in identifiers"),
    (r'^\s*(if|while|def|class|except|try)\s[^[]*:\s*[^\]#\s]+',
     "linebreak after :"),
    (r'class\s[^(]:', "old-style class, use class foo(object)"),
    (r'^\s+except\(', "except isn't a function"),
#    (r'class\s[A-Z][^\(]*\((?!Exception)',
#     "don't capitalize non-exception classes"),
#    (r'in range\(', "use xrange"),
#    (r'^\s*print\s+', "avoid using print in core and extensions"),
    (r'[\x80-\xff]', "non-ASCII character literal"),
    (r'("\')\.format\(', "str.format() not available in Python 2.4"),
    (r'^\s*with\s+', "with not available in Python 2.4"),
    (r'if\s.*\selse', "if ... else form not available in Python 2.4"),
    (r'([\(\[]\s\S)|(\S\s[\)\]])', "gratuitous whitespace in () or []"),
#    (r'\s\s=', "gratuitous whitespace before ="),
    (r'\S(\+=|-=|!=|<>|<=|>=|<<=|>>=)\S', "missing whitespace around operator")
]

pyfilters = [
    (r"""(''')(([^']|\\'|'{1,2}(?!'))*)'''""", repquote),
    (r'''(""")(([^"]|\\"|"{1,2}(?!"))*)"""''', repquote),
    (r'''(?<!")(")(([^"\n]|\\")+)"(?!")''', repquote),
    (r"""(?<!')(')(([^'\n]|\\')+)'(?!')""", repquote),
    (r"( *)(#([^\n]*\S)?)", repcomment),
]

cpats = [
    (r'//', "don't use //-style comments"),
    (r'^  ', "don't use spaces to indent"),
    (r'\S\t', "don't use tabs except for indent"),
    (r'(\S\s+|^\s+)\n', "trailing whitespace"),
    (r'.{85}', "line too long"),
    (r'(while|if|do|for)\(', "use space after while/if/do/for"),
    (r'return\(', "return is not a function"),
    (r' ;', "no space before ;"),
    (r'\w+\* \w+', "use int *foo, not int* foo"),
    (r'\([^\)]+\) \w+', "use (int)foo, not (int) foo"),
    (r'\S+ (\+\+|--)', "use foo++, not foo ++"),
    (r'\w,\w', "missing whitespace after ,"),
    (r'\w[+/*]\w', "missing whitespace in expression"),
    (r'^#\s+\w', "use #foo, not # foo"),
    (r'[^\n]\Z', "no trailing newline"),
]

cfilters = [
    (r'(/\*)(((\*(?!/))|[^*])*)\*/', repccomment),
    (r'''(?<!")(")(([^"]|\\")+"(?!"))''', repquote),
    (r'''(#\s*include\s+<)([^>]+)>''', repinclude),
    (r'(\()([^)]+\))', repcallspaces),
]

checks = [
    ('python', r'.*\.(py|cgi)$', pyfilters, pypats),
    ('test script', r'(.*/)?test-[^.~]*$', testfilters, testpats),
    ('c', r'.*\.c$', cfilters, cpats),
]

if len(sys.argv) == 1:
    check = glob.glob("*")
else:
    check = sys.argv[1:]

for f in check:
    for name, match, filters, pats in checks:
        fc = 0
        if not re.match(match, f):
            continue
        pre = post = open(f).read()
        for p, r in filters:
            post = re.sub(p, r, post)
        # print post # uncomment to show filtered version
        z = enumerate(zip(pre.splitlines(), post.splitlines(True)))
        for n, l in z:
            lc = 0
            for p, msg in pats:
                if re.search(p, l[1]):
                    if not lc:
                        print "%s:%d:" % (f, n + 1)
                        print " > %s" % l[0]
                    print " %s" % msg
                    lc += 1
                    fc += 1
            if fc == 15:
                print " (too many errors, giving up)"
                break
        break
