# transaction.py - simple journalling scheme for mercurial
#
# This transaction scheme is intended to gracefully handle program
# errors and interruptions. More serious failures like system crashes
# can be recovered with an fsck-like tool. As the whole repository is
# effectively log-structured, this should amount to simply truncating
# anything that isn't referenced in the changelog.
#
# Copyright 2005 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

import os

class transaction:
    def __init__(self, opener, journal):
        self.opener = opener
        self.entries = []
        self.map = {}
        self.journal = journal

        # abort here if the journal already exists
        if os.path.exists(self.journal):
            raise "Journal already exists!"
        self.file = open(self.journal, "w")

    def __del__(self):
        if self.entries: self.abort()
        try: os.unlink(self.journal)
        except: pass

    def add(self, file, offset):
        if file in self.map: return
        self.entries.append((file, offset))
        self.map[file] = 1
        # add enough data to the journal to do the truncate
        self.file.write("%s\0%d\n" % (file, offset))
        self.file.flush()

    def close(self):
        self.file.close()
        self.entries = []
        os.unlink(self.journal)

    def abort(self):
        if not self.entries: return

        print "transaction abort!"

        for f, o in self.entries:
            self.opener(f, "a").truncate(o)

        self.entries = []

        print "rollback completed"
        
    def recover(self):
        for l in open(self.journal).readlines():
            f, o = l.split('\0')
            self.opener(f, "a").truncate(int(o))

