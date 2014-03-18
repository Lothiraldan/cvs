# bundle2.py - generic container format to transmit arbitrary data.
#
# Copyright 2013 Facebook, Inc.
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.
"""Handling of the new bundle2 format

The goal of bundle2 is to act as an atomically packet to transmit a set of
payloads in an application agnostic way. It consist in a sequence of "parts"
that will be handed to and processed by the application layer.


General format architecture
===========================

The format is architectured as follow

 - magic string
 - stream level parameters
 - payload parts (any number)
 - end of stream marker.

The current implementation is limited to empty bundle.

Details on the Binary format
============================

All numbers are unsigned and big endian.

stream level parameters
------------------------

Binary format is as follow

:params size: (16 bits integer)

  The total number of Bytes used by the parameters

  Currently force to 0.

:params value: arbitrary number of Bytes

  A blob of `params size` containing the serialized version of all stream level
  parameters.

  Currently always empty.


Payload part
------------------------

Binary format is as follow

:header size: (16 bits inter)

  The total number of Bytes used by the part headers. When the header is empty
  (size = 0) this is interpreted as the end of stream marker.

  Currently forced to 0 in the current state of the implementation
"""

_magicstring = 'HG20'

class bundle20(object):
    """represent an outgoing bundle2 container

    People will eventually be able to add param and parts to this object and
    generated a stream from it."""

    def __init__(self):
        self._params = []
        self._parts = []

    def getchunks(self):
        yield _magicstring
        # no support for any param yet
        # to be obviously fixed soon.
        assert not self._params
        yield '\0\0'
        # no support for parts
        # to be obviously fixed soon.
        assert not self._parts
        yield '\0\0'
