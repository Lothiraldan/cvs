# node.py - basic nodeid manipulation for mercurial
#
# Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from __future__ import absolute_import

import binascii

nullrev = -1
nullid = "\0" * 20

# pseudo identifiers for working directory
# (they are experimental, so don't add too many dependencies on them)
wdirrev = 0x7fffffff
wdirid = "\xff" * 20

# This ugly style has a noticeable effect in manifest parsing
hex = binascii.hexlify
bin = binascii.unhexlify

def short(node):
    return hex(node[:6])
