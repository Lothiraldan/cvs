# bdiff.py - Python implementation of bdiff.c
#
# Copyright 2009 Matt Mackall <mpm@selenic.com> and others
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from __future__ import absolute_import

import array
import difflib
import re
import struct

from . import policy
policynocffi = policy.policynocffi
modulepolicy = policy.policy

def splitnewlines(text):
    '''like str.splitlines, but only split on newlines.'''
    lines = [l + '\n' for l in text.split('\n')]
    if lines:
        if lines[-1] == '\n':
            lines.pop()
        else:
            lines[-1] = lines[-1][:-1]
    return lines

def _normalizeblocks(a, b, blocks):
    prev = None
    r = []
    for curr in blocks:
        if prev is None:
            prev = curr
            continue
        shift = 0

        a1, b1, l1 = prev
        a1end = a1 + l1
        b1end = b1 + l1

        a2, b2, l2 = curr
        a2end = a2 + l2
        b2end = b2 + l2
        if a1end == a2:
            while (a1end + shift < a2end and
                   a[a1end + shift] == b[b1end + shift]):
                shift += 1
        elif b1end == b2:
            while (b1end + shift < b2end and
                   a[a1end + shift] == b[b1end + shift]):
                shift += 1
        r.append((a1, b1, l1 + shift))
        prev = a2 + shift, b2 + shift, l2 - shift
    r.append(prev)
    return r

def _tostring(c):
    if type(c) is array.array:
        # this copy overhead isn't ideal
        return c.tostring()
    return str(c)

def bdiff(a, b):
    a = _tostring(a).splitlines(True)
    b = _tostring(b).splitlines(True)

    if not a:
        s = "".join(b)
        return s and (struct.pack(">lll", 0, 0, len(s)) + s)

    bin = []
    p = [0]
    for i in a: p.append(p[-1] + len(i))

    d = difflib.SequenceMatcher(None, a, b).get_matching_blocks()
    d = _normalizeblocks(a, b, d)
    la = 0
    lb = 0
    for am, bm, size in d:
        s = "".join(b[lb:bm])
        if am > la or s:
            bin.append(struct.pack(">lll", p[la], p[am], len(s)) + s)
        la = am + size
        lb = bm + size

    return "".join(bin)

def blocks(a, b):
    an = splitnewlines(a)
    bn = splitnewlines(b)
    d = difflib.SequenceMatcher(None, an, bn).get_matching_blocks()
    d = _normalizeblocks(an, bn, d)
    return [(i, i + n, j, j + n) for (i, j, n) in d]

def fixws(text, allws):
    if allws:
        text = re.sub('[ \t\r]+', '', text)
    else:
        text = re.sub('[ \t\r]+', ' ', text)
        text = text.replace(' \n', '\n')
    return text

if modulepolicy not in policynocffi:
    try:
        from _bdiff_cffi import ffi, lib
    except ImportError:
        if modulepolicy == 'cffi': # strict cffi import
            raise
    else:
        def blocks(sa, sb):
            a = ffi.new("struct bdiff_line**")
            b = ffi.new("struct bdiff_line**")
            ac = ffi.new("char[]", sa)
            bc = ffi.new("char[]", sb)
            try:
                an = lib.bdiff_splitlines(ac, len(sa), a)
                bn = lib.bdiff_splitlines(bc, len(sb), b)
                if not a[0] or not b[0]:
                    raise MemoryError
                l = ffi.new("struct bdiff_hunk*")
                count = lib.bdiff_diff(a[0], an, b[0], bn, l)
                if count < 0:
                    raise MemoryError
                rl = [None] * count
                h = l.next
                i = 0
                while h:
                    rl[i] = (h.a1, h.a2, h.b1, h.b2)
                    h = h.next
                    i += 1
            finally:
                lib.free(a[0])
                lib.free(b[0])
                lib.bdiff_freehunks(l.next)
            return rl
