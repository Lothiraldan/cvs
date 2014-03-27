#!/usr/bin/env python

# Measure the performance of a list of revsets against multiple revisions
# defined by parameter. Checkout one by one and run perfrevset with every
# revset in the list to benchmark its performance.
#
# - First argument is a revset of mercurial own repo to runs against.
# - Second argument is the file from which the revset array will be taken
#   If second argument is omitted read it from standard input
#
# You should run this from the root of your mercurial repository.
#
# This script also does one run of the current version of mercurial installed
# to compare performance.

import sys
from subprocess import check_call, check_output, CalledProcessError, STDOUT


def update(rev):
    """update the repo to a revision"""
    try:
        check_call(['hg', 'update', '--quiet', '--check', str(rev)])
    except CalledProcessError, exc:
        print >> sys.stderr, 'update to revision %s failed, aborting' % rev
        sys.exit(exc.returncode)

def perf(revset):
    """run benchmark for this very revset"""
    try:
        output = check_output(['./hg',
                               '--config',
                               'extensions.perf=contrib/perf.py',
                               'perfrevset',
                               revset],
                               stderr=STDOUT)
        output = output.lstrip('!') # remove useless ! in this context
        return output.strip()
    except CalledProcessError, exc:
        print >> sys.stderr, 'abort: cannot run revset benchmark'
        sys.exit(exc.returncode)

def printrevision(rev):
    """print data about a revision"""
    sys.stdout.write("Revision: ")
    sys.stdout.flush()
    check_call(['hg', 'log', '--rev', str(rev), '--template',
               '{desc|firstline}\n'])

def getrevs(spec):
    """get the list of rev matched by a revset"""
    try:
        out = check_output(['hg', 'log', '--template={rev}\n', '--rev', spec])
    except CalledProcessError, exc:
        print >> sys.stderr, "abort, can't get revision from %s" % spec
        sys.exit(exc.returncode)
    return [r for r in out.split() if r]



target_rev = sys.argv[1]

revsetsfile = sys.stdin
if len(sys.argv) > 2:
    revsetsfile = open(sys.argv[2])

revsets = [l.strip() for l in revsetsfile]

print "Revsets to benchmark"
print "----------------------------"

for idx, rset in enumerate(revsets):
    print "%i) %s" % (idx, rset)

print "----------------------------"
print


revs = getrevs(target_rev)

for r in revs:
    print "----------------------------"
    printrevision(r)
    print "----------------------------"
    update(r)
    for idx, rset in enumerate(revsets):

        print "%i)" % idx, perf(rset)
    print "----------------------------"

