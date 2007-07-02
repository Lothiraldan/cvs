import os
from mercurial import hg, ui, commands

u = ui.ui()

repo = hg.repository(u, 'test1', create=1)
os.chdir('test1')
repo = hg.repository(u, '.') # FIXME: can't lock repo without doing this

# create 'foo' with fixed time stamp
f = file('foo', 'w')
f.write('foo\n')
f.close()
os.utime('foo', (1000, 1000))

# add+commit 'foo'
repo.add(['foo'])
repo.commit(text='commit1', date="0 0")

print "workingfilectx.date =", repo.workingctx().filectx('foo').date()
