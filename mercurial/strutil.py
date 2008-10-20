# strutil.py - string utilities for Mercurial
#
# Copyright 2006 Vadim Gelfer <vadim.gelfer@gmail.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

def findall(haystack, needle, start=0, end=None):
    if end is None:
        end = len(haystack)
    if end < 0:
        end += len(haystack)
    if start < 0:
        start += len(haystack)
    while start < end:
        c = haystack.find(needle, start, end)
        if c == -1:
            break
        yield c
        start = c + 1

def rfindall(haystack, needle, start=0, end=None):
    if end is None:
        end = len(haystack)
    if end < 0:
        end += len(haystack)
    if start < 0:
        start += len(haystack)
    while end >= 0:
        c = haystack.rfind(needle, start, end)
        if c == -1:
            break
        yield c
        end = c - 1

def rsplit(s, sep=None, maxsplit=-1):
    try:
        return s.rsplit(sep, maxsplit)
    except AttributeError:
        return  [chunk[::-1] for chunk in
                 s[::-1].split(sep, maxsplit)[::-1]]
