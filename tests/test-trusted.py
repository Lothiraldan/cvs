#!/usr/bin/env python
# Since it's not easy to write a test that portably deals
# with files from different users/groups, we cheat a bit by
# monkey-patching some functions in the util module

import os
from mercurial import ui, util

hgrc = os.environ['HGRCPATH']

def testui(user='foo', group='bar', tusers=(), tgroups=(),
           cuser='foo', cgroup='bar'):
    # user, group => owners of the file
    # tusers, tgroups => trusted users/groups
    # cuser, cgroup => user/group of the current process

    # write a global hgrc with the list of trusted users/groups and
    # some setting so that we can be sure it was read
    f = open(hgrc, 'w')
    f.write('[paths]\n')
    f.write('global = /some/path\n\n')

    if tusers or tgroups:
        f.write('[trusted]\n')
        if tusers:
            f.write('users = %s\n' % ', '.join(tusers))
        if tgroups:
            f.write('groups = %s\n' % ', '.join(tgroups))
    f.close()

    # override the functions that give names to uids and gids
    def username(uid=None):
        if uid is None:
            return cuser
        return user
    util.username = username

    def groupname(gid=None):
        if gid is None:
            return 'bar'
        return group
    util.groupname = groupname

    # try to read everything
    #print '# File belongs to user %s, group %s' % (user, group)
    #print '# trusted users = %s; trusted groups = %s' % (tusers, tgroups)
    kind = ('different', 'same')
    who = ('', 'user', 'group', 'user and the group')
    trusted = who[(user in tusers) + 2*(group in tgroups)]
    if trusted:
        trusted = ', but we trust the ' + trusted
    print '# %s user, %s group%s' % (kind[user == cuser], kind[group == cgroup],
                                     trusted)

    parentui = ui.ui()
    u = ui.ui(parentui=parentui)
    u.readconfig('.hg/hgrc')
    for name, path in u.configitems('paths'):
        print name, '=', path
    print

    return u

os.mkdir('repo')
os.chdir('repo')
os.mkdir('.hg')
f = open('.hg/hgrc', 'w')
f.write('[paths]\n')
f.write('local = /another/path\n\n')
f.close()

#print '# Everything is run by user foo, group bar\n'

# same user, same group
testui()
# same user, different group
testui(group='def')
# different user, same group
testui(user='abc')
# ... but we trust the group
testui(user='abc', tgroups=['bar'])
# different user, different group
testui(user='abc', group='def')
# ... but we trust the user
testui(user='abc', group='def', tusers=['abc'])
# ... but we trust the group
testui(user='abc', group='def', tgroups=['def'])
# ... but we trust the user and the group
testui(user='abc', group='def', tusers=['abc'], tgroups=['def'])
# ... but we trust all users
print '# we trust all users'
testui(user='abc', group='def', tusers=['*'])
# ... but we trust all groups
print '# we trust all groups'
testui(user='abc', group='def', tgroups=['*'])
# ... but we trust the whole universe
print '# we trust all users and groups'
testui(user='abc', group='def', tusers=['*'], tgroups=['*'])
# ... check that users and groups are in different namespaces
print "# we don't get confused by users and groups with the same name"
testui(user='abc', group='def', tusers=['def'], tgroups=['abc'])
# ... lists of user names work
print "# list of user names"
testui(user='abc', group='def', tusers=['foo', 'xyz', 'abc', 'bleh'],
       tgroups=['bar', 'baz', 'qux'])
# ... lists of group names work
print "# list of group names"
testui(user='abc', group='def', tusers=['foo', 'xyz', 'bleh'],
       tgroups=['bar', 'def', 'baz', 'qux'])

print "# Can't figure out the name of the user running this process"
testui(user='abc', group='def', cuser=None)
