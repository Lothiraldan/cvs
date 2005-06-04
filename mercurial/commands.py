import os, re, traceback, sys, signal, time, mdiff
from mercurial import fancyopts, ui, hg

class UnknownCommand(Exception): pass

def filterfiles(filters, files):
    l = [ x for x in files if x in filters ]

    for t in filters:
        if t and t[-1] != os.sep: t += os.sep
        l += [ x for x in files if x.startswith(t) ]
    return l

def relfilter(repo, files):
    if os.getcwd() != repo.root:
        p = os.getcwd()[len(repo.root) + 1: ]
        return filterfiles(p, files)
    return files

def relpath(repo, args):
    if os.getcwd() != repo.root:
        p = os.getcwd()[len(repo.root) + 1: ]
        return [ os.path.normpath(os.path.join(p, x)) for x in args ]
    return args

def dodiff(repo, files = None, node1 = None, node2 = None):
    def date(c):
        return time.asctime(time.gmtime(float(c[2].split(' ')[0])))

    if node2:
        change = repo.changelog.read(node2)
        mmap2 = repo.manifest.read(change[0])
        (c, a, d) = repo.diffrevs(node1, node2)
        def read(f): return repo.file(f).read(mmap2[f])
        date2 = date(change)
    else:
        date2 = time.asctime()
        (c, a, d, u) = repo.diffdir(repo.root, node1)
        if not node1:
            node1 = repo.dirstate.parents()[0]
        def read(f): return file(os.path.join(repo.root, f)).read()

    change = repo.changelog.read(node1)
    mmap = repo.manifest.read(change[0])
    date1 = date(change)

    if files:
        c, a, d = map(lambda x: filterfiles(files, x), (c, a, d))

    for f in c:
        to = repo.file(f).read(mmap[f])
        tn = read(f)
        sys.stdout.write(mdiff.unidiff(to, date1, tn, date2, f))
    for f in a:
        to = ""
        tn = read(f)
        sys.stdout.write(mdiff.unidiff(to, date1, tn, date2, f))
    for f in d:
        to = repo.file(f).read(mmap[f])
        tn = ""
        sys.stdout.write(mdiff.unidiff(to, date1, tn, date2, f))
    
def help(ui, cmd=None):
    '''show help'''
    if cmd:
        try:
            i = find(cmd)
            ui.write("%s\n\n" % i[2])
            ui.write(i[0].__doc__, "\n")
        except UnknownCommand:
            ui.warn("unknown command %s", cmd)
        sys.exit(0)
    
    ui.status("""\
 hg commands:

 add [files...]        add the given files in the next commit
 addremove             add all new files, delete all missing files
 annotate [files...]   show changeset number per file line
 branch <path>         create a branch of <path> in this directory
 checkout [changeset]  checkout the latest or given changeset
 commit                commit all changes to the repository
 diff [files...]       diff working directory (or selected files)
 dump <file> [rev]     dump the latest or given revision of a file
 dumpmanifest [rev]    dump the latest or given revision of the manifest
 export <rev>          dump the changeset header and diffs for a revision
 history               show changeset history
 init                  create a new repository in this directory
 log <file>            show revision history of a single file
 merge <path>          merge changes from <path> into local repository
 recover               rollback an interrupted transaction
 remove [files...]     remove the given files in the next commit
 serve                 export the repository via HTTP
 status                show new, missing, and changed files in working dir
 tags                  show current changeset tags
 undo                  undo the last transaction
""")

def add(ui, repo, file, *files):
    '''add the specified files on the next commit'''
    repo.add(relpath(repo, (file,) + files))

def addremove(ui, repo):
    (c, a, d, u) = repo.diffdir(repo.root)
    repo.add(a)
    repo.remove(d)

def annotate(u, repo, file, *files, **ops):
    def getnode(rev):
        return hg.short(repo.changelog.node(rev))

    def getname(rev):
        try:
            return bcache[rev]
        except KeyError:
            cl = repo.changelog.read(repo.changelog.node(rev))
            name = cl[1]
            f = name.find('@')
            if f >= 0:
                name = name[:f]
            bcache[rev] = name
            return name
    
    bcache = {}
    opmap = [['user', getname], ['number', str], ['changeset', getnode]]
    if not ops['user'] and not ops['changeset']:
        ops['number'] = 1

    node = repo.dirstate.parents()[0]
    if ops['revision']:
        node = repo.changelog.lookup(ops['revision'])
    change = repo.changelog.read(node)
    mmap = repo.manifest.read(change[0])
    maxuserlen = 0
    maxchangelen = 0
    for f in relpath(repo, (file,) + files):
        lines = repo.file(f).annotate(mmap[f])
        pieces = []

        for o, f in opmap:
            if ops[o]:
                l = [ f(n) for n,t in lines ]
                m = max(map(len, l))
                pieces.append([ "%*s" % (m, x) for x in l])

        for p,l in zip(zip(*pieces), lines):
            u.write(" ".join(p) + ": " + l[1])

def branch(ui, path):
    '''branch from a local repository'''
    # this should eventually support remote repos
    os.system("cp -al %s/.hg .hg" % path)

def checkout(ui, repo, changeset=None):
    '''checkout a given changeset or the current tip'''
    (c, a, d, u) = repo.diffdir(repo.root)
    if c or a or d:
        ui.warn("aborting (outstanding changes in working directory)\n")
        sys.exit(1)

    node = repo.changelog.tip()
    if changeset:
        node = repo.lookup(changeset)
    repo.checkout(node)

def commit(ui, repo, *files):
    """commit the specified files or all outstanding changes"""
    repo.commit(relpath(repo, files))

def diff(ui, repo, *files, **opts):
    revs = []
    if opts['rev']:
        revs = map(lambda x: repo.lookup(x), opts['rev'])
    
    if len(revs) > 2:
        self.ui.warn("too many revisions to diff\n")
        sys.exit(1)

    if files:
        files = relpath(repo, files)
    else:
        files = relpath(repo, [""])

    dodiff(repo, files, *revs)

def forget(ui, repo, file, *files):
    """don't add the specified files on the next commit"""
    repo.forget(relpath(repo, (file,) + files))

def heads(ui, repo):
    '''show current repository heads'''
    for n in repo.changelog.heads():
        i = repo.changelog.rev(n)
        changes = repo.changelog.read(n)
        (p1, p2) = repo.changelog.parents(n)
        (h, h1, h2) = map(hg.hex, (n, p1, p2))
        (i1, i2) = map(repo.changelog.rev, (p1, p2))
        print "rev:      %4d:%s" % (i, h)
        print "parents:  %4d:%s" % (i1, h1)
        if i2: print "          %4d:%s" % (i2, h2)
        print "manifest: %4d:%s" % (repo.manifest.rev(changes[0]),
                                    hg.hex(changes[0]))
        print "user:", changes[1]
        print "date:", time.asctime(
            time.localtime(float(changes[2].split(' ')[0])))
        if ui.verbose: print "files:", " ".join(changes[3])
        print "description:"
        print changes[4]

def init(ui):
    """create a repository"""
    hg.repository(ui, ".", create=1)

def log(ui, repo, f):
    f = relpath(repo, [f])[0]

    r = repo.file(f)
    for i in range(r.count()):
        n = r.node(i)
        (p1, p2) = r.parents(n)
        (h, h1, h2) = map(hg.hex, (n, p1, p2))
        (i1, i2) = map(r.rev, (p1, p2))
        cr = r.linkrev(n)
        cn = hg.hex(repo.changelog.node(cr))
        print "rev:       %4d:%s" % (i, h)
        print "changeset: %4d:%s" % (cr, cn)
        print "parents:   %4d:%s" % (i1, h1)
        if i2: print "           %4d:%s" % (i2, h2)
        changes = repo.changelog.read(repo.changelog.node(cr))
        print "user: %s" % changes[1]
        print "date: %s" % time.asctime(
            time.localtime(float(changes[2].split(' ')[0])))
        print "description:"
        print changes[4].rstrip()
        print

def parents(ui, repo, node = None):
    '''show the parents of the current working dir'''
    if node:
        p = repo.changelog.parents(repo.lookup(hg.bin(node)))
    else:
        p = repo.dirstate.parents()

    for n in p:
        if n != hg.nullid:
            ui.write("%d:%s\n" % (repo.changelog.rev(n), hg.hex(n)))

def recover(ui, repo):
    repo.recover()

def remove(ui, repo, file, *files):
    """remove the specified files on the next commit"""
    repo.remove(relpath(repo, (file,) + files))

def resolve(ui, repo, node=None):
    '''merge a given node or the current tip into the working dir'''
    if not node:
        node = repo.changelog.tip()
    else:
        node = repo.lookup(node)
    repo.resolve(node)

def serve(ui, repo, **opts):
    from mercurial import hgweb
    hgweb.server(repo.root, opts["name"], opts["templates"],
                 opts["address"], opts["port"])
    
def status(ui, repo):
    '''show changed files in the working directory

    C = changed
    A = added
    R = removed
    ? = not tracked'''
    
    (c, a, d, u) = repo.diffdir(repo.root)
    (c, a, d, u) = map(lambda x: relfilter(repo, x), (c, a, d, u))

    for f in c: print "C", f
    for f in a: print "A", f
    for f in d: print "R", f
    for f in u: print "?", f

def tip(ui, repo):
    n = repo.changelog.tip()
    t = repo.changelog.rev(n)
    ui.status("%d:%s\n" % (t, hg.hex(n)))

def undo(ui, repo):
    repo.undo()

table = {
    "add": (add, [], "hg add [files]"),
    "addremove": (addremove, [], "hg addremove"),
    "ann|annotate": (annotate,
                     [('r', 'revision', '', 'revision'),
                      ('u', 'user', None, 'show user'),
                      ('n', 'number', None, 'show revision number'),
                      ('c', 'changeset', None, 'show changeset')],
                     'hg annotate [-u] [-c] [-n] [-r id] [files]'),
    "branch|clone": (branch, [], 'hg branch [path]'),
    "checkout|co": (checkout, [], 'hg checkout [changeset]'),
    "commit|ci": (commit, [], 'hg commit [files]'),
    "diff": (diff, [('r', 'rev', [], 'revision')],
             'hg diff [-r A] [-r B] [files]'),
    "forget": (forget, [], "hg forget [files]"),
    "heads": (heads, [], 'hg heads'),
    "help": (help, [], 'hg help [command]'),
    "init": (init, [], 'hg init'),
    "log": (log, [], 'hg log <file>'),
    "parents": (parents, [], 'hg parents [node]'),
    "recover": (recover, [], "hg recover"),
    "remove": (remove, [], "hg remove [files]"),
    "resolve": (resolve, [], 'hg resolve [node]'),
    "serve": (serve, [('p', 'port', 8000, 'listen port'),
                      ('a', 'address', '', 'interface address'),
                      ('n', 'name', os.getcwd(), 'repository name'),
                      ('t', 'templates', "", 'template map')],
              "hg serve [options]"),
    "status": (status, [], 'hg status'),
    "tip": (tip, [], 'hg tip'),
    "undo": (undo, [], 'hg undo'),
    }

norepo = "init branch help"

def find(cmd):
    i = None
    for e in table.keys():
        if re.match(e + "$", cmd):
            return table[e]

    raise UnknownCommand(cmd)

class SignalInterrupt(Exception): pass

def catchterm(*args):
    raise SignalInterrupt

def dispatch(args):
    options = {}
    opts = [('v', 'verbose', None, 'verbose'),
            ('d', 'debug', None, 'debug'),
            ('q', 'quiet', None, 'quiet'),
            ('y', 'noninteractive', None, 'run non-interactively'),
            ]

    args = fancyopts.fancyopts(args, opts, options,
                               'hg [options] <command> [options] [files]')

    if not args:
        cmd = "help"
    else:
        cmd, args = args[0], args[1:]

    u = ui.ui(options["verbose"], options["debug"], options["quiet"],
           not options["noninteractive"])

    # deal with unfound commands later
    i = find(cmd)

    signal.signal(signal.SIGTERM, catchterm)

    cmdoptions = {}
    args = fancyopts.fancyopts(args, i[1], cmdoptions, i[2])

    if cmd not in norepo.split():
        repo = hg.repository(ui = u)
        d = lambda: i[0](u, repo, *args, **cmdoptions)
    else:
        d = lambda: i[0](u, *args, **cmdoptions)

    try:
        d()
    except SignalInterrupt:
        u.warn("killed!\n")
    except KeyboardInterrupt:
        u.warn("interrupted!\n")
    except TypeError, inst:
        # was this an argument error?
        tb = traceback.extract_tb(sys.exc_info()[2])
        if len(tb) > 2: # no
            raise
        u.warn("%s: invalid arguments\n" % i[0].__name__)
        u.warn("syntax: %s\n" % i[2])
        sys.exit(-1)
