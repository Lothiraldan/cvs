# cmdutil.py - help for command processing in mercurial
#
# Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from node import *
from i18n import _
import os, sys, mdiff, bdiff, util, templater, patch

revrangesep = ':'

def revpair(repo, revs):
    '''return pair of nodes, given list of revisions. second item can
    be None, meaning use working dir.'''

    def revfix(repo, val, defval):
        if not val and val != 0 and defval is not None:
            val = defval
        return repo.lookup(val)

    if not revs:
        return repo.dirstate.parents()[0], None
    end = None
    if len(revs) == 1:
        if revrangesep in revs[0]:
            start, end = revs[0].split(revrangesep, 1)
            start = revfix(repo, start, 0)
            end = revfix(repo, end, repo.changelog.count() - 1)
        else:
            start = revfix(repo, revs[0], None)
    elif len(revs) == 2:
        if revrangesep in revs[0] or revrangesep in revs[1]:
            raise util.Abort(_('too many revisions specified'))
        start = revfix(repo, revs[0], None)
        end = revfix(repo, revs[1], None)
    else:
        raise util.Abort(_('too many revisions specified'))
    return start, end

def revrange(repo, revs):
    """Yield revision as strings from a list of revision specifications."""

    def revfix(repo, val, defval):
        if not val and val != 0 and defval is not None:
            return defval
        return repo.changelog.rev(repo.lookup(val))

    seen, l = {}, []
    for spec in revs:
        if revrangesep in spec:
            start, end = spec.split(revrangesep, 1)
            start = revfix(repo, start, 0)
            end = revfix(repo, end, repo.changelog.count() - 1)
            step = start > end and -1 or 1
            for rev in xrange(start, end+step, step):
                if rev in seen:
                    continue
                seen[rev] = 1
                l.append(rev)
        else:
            rev = revfix(repo, spec, None)
            if rev in seen:
                continue
            seen[rev] = 1
            l.append(rev)

    return l

def make_filename(repo, pat, node,
                  total=None, seqno=None, revwidth=None, pathname=None):
    node_expander = {
        'H': lambda: hex(node),
        'R': lambda: str(repo.changelog.rev(node)),
        'h': lambda: short(node),
        }
    expander = {
        '%': lambda: '%',
        'b': lambda: os.path.basename(repo.root),
        }

    try:
        if node:
            expander.update(node_expander)
        if node and revwidth is not None:
            expander['r'] = (lambda:
                    str(repo.changelog.rev(node)).zfill(revwidth))
        if total is not None:
            expander['N'] = lambda: str(total)
        if seqno is not None:
            expander['n'] = lambda: str(seqno)
        if total is not None and seqno is not None:
            expander['n'] = lambda: str(seqno).zfill(len(str(total)))
        if pathname is not None:
            expander['s'] = lambda: os.path.basename(pathname)
            expander['d'] = lambda: os.path.dirname(pathname) or '.'
            expander['p'] = lambda: pathname

        newname = []
        patlen = len(pat)
        i = 0
        while i < patlen:
            c = pat[i]
            if c == '%':
                i += 1
                c = pat[i]
                c = expander[c]()
            newname.append(c)
            i += 1
        return ''.join(newname)
    except KeyError, inst:
        raise util.Abort(_("invalid format spec '%%%s' in output file name") %
                         inst.args[0])

def make_file(repo, pat, node=None,
              total=None, seqno=None, revwidth=None, mode='wb', pathname=None):
    if not pat or pat == '-':
        return 'w' in mode and sys.stdout or sys.stdin
    if hasattr(pat, 'write') and 'w' in mode:
        return pat
    if hasattr(pat, 'read') and 'r' in mode:
        return pat
    return open(make_filename(repo, pat, node, total, seqno, revwidth,
                              pathname),
                mode)

def matchpats(repo, pats=[], opts={}, globbed=False, default=None):
    cwd = repo.getcwd()
    return util.cmdmatcher(repo.root, cwd, pats or [], opts.get('include'),
                           opts.get('exclude'), globbed=globbed,
                           default=default)

def walk(repo, pats=[], opts={}, node=None, badmatch=None, globbed=False,
         default=None):
    files, matchfn, anypats = matchpats(repo, pats, opts, globbed=globbed,
                                        default=default)
    exact = dict.fromkeys(files)
    for src, fn in repo.walk(node=node, files=files, match=matchfn,
                             badmatch=badmatch):
        yield src, fn, util.pathto(repo.root, repo.getcwd(), fn), fn in exact

def findrenames(repo, added=None, removed=None, threshold=0.5):
    '''find renamed files -- yields (before, after, score) tuples'''
    if added is None or removed is None:
        added, removed = repo.status()[1:3]
    ctx = repo.changectx()
    for a in added:
        aa = repo.wread(a)
        bestname, bestscore = None, threshold
        for r in removed:
            rr = ctx.filectx(r).data()

            # bdiff.blocks() returns blocks of matching lines
            # count the number of bytes in each
            equal = 0
            alines = mdiff.splitnewlines(aa)
            matches = bdiff.blocks(aa, rr)
            for x1,x2,y1,y2 in matches:
                for line in alines[x1:x2]:
                    equal += len(line)

            myscore = equal*2.0 / (len(aa)+len(rr))
            if myscore >= bestscore:
                bestname, bestscore = r, myscore
        if bestname:
            yield bestname, a, bestscore

def addremove(repo, pats=[], opts={}, wlock=None, dry_run=None,
              similarity=None):
    if dry_run is None:
        dry_run = opts.get('dry_run')
    if similarity is None:
        similarity = float(opts.get('similarity') or 0)
    add, remove = [], []
    mapping = {}
    for src, abs, rel, exact in walk(repo, pats, opts):
        if src == 'f' and repo.dirstate.state(abs) == '?':
            add.append(abs)
            mapping[abs] = rel, exact
            if repo.ui.verbose or not exact:
                repo.ui.status(_('adding %s\n') % ((pats and rel) or abs))
        islink = os.path.islink(rel)
        if repo.dirstate.state(abs) != 'r' and not islink and not os.path.exists(rel):
            remove.append(abs)
            mapping[abs] = rel, exact
            if repo.ui.verbose or not exact:
                repo.ui.status(_('removing %s\n') % ((pats and rel) or abs))
    if not dry_run:
        repo.add(add, wlock=wlock)
        repo.remove(remove, wlock=wlock)
    if similarity > 0:
        for old, new, score in findrenames(repo, add, remove, similarity):
            oldrel, oldexact = mapping[old]
            newrel, newexact = mapping[new]
            if repo.ui.verbose or not oldexact or not newexact:
                repo.ui.status(_('recording removal of %s as rename to %s '
                                 '(%d%% similar)\n') %
                               (oldrel, newrel, score * 100))
            if not dry_run:
                repo.copy(old, new, wlock=wlock)

def service(opts, parentfn=None, initfn=None, runfn=None):
    '''Run a command as a service.'''

    if opts['daemon'] and not opts['daemon_pipefds']:
        rfd, wfd = os.pipe()
        args = sys.argv[:]
        args.append('--daemon-pipefds=%d,%d' % (rfd, wfd))
        pid = os.spawnvp(os.P_NOWAIT | getattr(os, 'P_DETACH', 0),
                         args[0], args)
        os.close(wfd)
        os.read(rfd, 1)
        if parentfn:
            return parentfn(pid)
        else:
            os._exit(0)

    if initfn:
        initfn()

    if opts['pid_file']:
        fp = open(opts['pid_file'], 'w')
        fp.write(str(os.getpid()) + '\n')
        fp.close()

    if opts['daemon_pipefds']:
        rfd, wfd = [int(x) for x in opts['daemon_pipefds'].split(',')]
        os.close(rfd)
        try:
            os.setsid()
        except AttributeError:
            pass
        os.write(wfd, 'y')
        os.close(wfd)
        sys.stdout.flush()
        sys.stderr.flush()
        fd = os.open(util.nulldev, os.O_RDWR)
        if fd != 0: os.dup2(fd, 0)
        if fd != 1: os.dup2(fd, 1)
        if fd != 2: os.dup2(fd, 2)
        if fd not in (0, 1, 2): os.close(fd)

    if runfn:
        return runfn()

class changeset_printer(object):
    '''show changeset information when templating not requested.'''

    def __init__(self, ui, repo, patch, buffered):
        self.ui = ui
        self.repo = repo
        self.buffered = buffered
        self.patch = patch
        self.header = {}
        self.hunk = {}
        self.lastheader = None

    def flush(self, rev):
        if rev in self.header:
            h = self.header[rev]
            if h != self.lastheader:
                self.lastheader = h
                self.ui.write(h)
            del self.header[rev]
        if rev in self.hunk:
            self.ui.write(self.hunk[rev])
            del self.hunk[rev]
            return 1
        return 0

    def show(self, rev=0, changenode=None, copies=(), **props):
        if self.buffered:
            self.ui.pushbuffer()
            self._show(rev, changenode, copies, props)
            self.hunk[rev] = self.ui.popbuffer()
        else:
            self._show(rev, changenode, copies, props)

    def _show(self, rev, changenode, copies, props):
        '''show a single changeset or file revision'''
        log = self.repo.changelog
        if changenode is None:
            changenode = log.node(rev)
        elif not rev:
            rev = log.rev(changenode)

        if self.ui.quiet:
            self.ui.write("%d:%s\n" % (rev, short(changenode)))
            return

        changes = log.read(changenode)
        date = util.datestr(changes[2])
        extra = changes[5]
        branch = extra.get("branch")

        hexfunc = self.ui.debugflag and hex or short

        parents = log.parentrevs(rev)
        if not self.ui.debugflag:
            if parents[1] == nullrev:
                if parents[0] >= rev - 1:
                    parents = []
                else:
                    parents = [parents[0]]
        parents = [(p, hexfunc(log.node(p))) for p in parents]

        self.ui.write(_("changeset:   %d:%s\n") % (rev, hexfunc(changenode)))

        # don't show the default branch name
        if branch != 'default':
            branch = util.tolocal(branch)
            self.ui.write(_("branch:      %s\n") % branch)
        for tag in self.repo.nodetags(changenode):
            self.ui.write(_("tag:         %s\n") % tag)
        for parent in parents:
            self.ui.write(_("parent:      %d:%s\n") % parent)

        if self.ui.debugflag:
            self.ui.write(_("manifest:    %d:%s\n") %
                          (self.repo.manifest.rev(changes[0]), hex(changes[0])))
        self.ui.write(_("user:        %s\n") % changes[1])
        self.ui.write(_("date:        %s\n") % date)

        if self.ui.debugflag:
            files = self.repo.status(log.parents(changenode)[0], changenode)[:3]
            for key, value in zip([_("files:"), _("files+:"), _("files-:")],
                                  files):
                if value:
                    self.ui.write("%-12s %s\n" % (key, " ".join(value)))
        elif changes[3] and self.ui.verbose:
            self.ui.write(_("files:       %s\n") % " ".join(changes[3]))
        if copies and self.ui.verbose:
            copies = ['%s (%s)' % c for c in copies]
            self.ui.write(_("copies:      %s\n") % ' '.join(copies))

        if extra and self.ui.debugflag:
            extraitems = extra.items()
            extraitems.sort()
            for key, value in extraitems:
                self.ui.write(_("extra:       %s=%s\n")
                              % (key, value.encode('string_escape')))

        description = changes[4].strip()
        if description:
            if self.ui.verbose:
                self.ui.write(_("description:\n"))
                self.ui.write(description)
                self.ui.write("\n\n")
            else:
                self.ui.write(_("summary:     %s\n") %
                              description.splitlines()[0])
        self.ui.write("\n")

        self.showpatch(changenode)

    def showpatch(self, node):
        if self.patch:
            prev = self.repo.changelog.parents(node)[0]
            patch.diff(self.repo, prev, node, match=self.patch, fp=self.ui)
            self.ui.write("\n")

class changeset_templater(changeset_printer):
    '''format changeset information.'''

    def __init__(self, ui, repo, patch, mapfile, buffered):
        changeset_printer.__init__(self, ui, repo, patch, buffered)
        filters = templater.common_filters.copy()
        filters['formatnode'] = (ui.debugflag and (lambda x: x)
                                 or (lambda x: x[:12]))
        self.t = templater.templater(mapfile, filters,
                                     cache={
                                         'parent': '{rev}:{node|formatnode} ',
                                         'manifest': '{rev}:{node|formatnode}',
                                         'filecopy': '{name} ({source})'})

    def use_template(self, t):
        '''set template string to use'''
        self.t.cache['changeset'] = t

    def _show(self, rev, changenode, copies, props):
        '''show a single changeset or file revision'''
        log = self.repo.changelog
        if changenode is None:
            changenode = log.node(rev)
        elif not rev:
            rev = log.rev(changenode)

        changes = log.read(changenode)

        def showlist(name, values, plural=None, **args):
            '''expand set of values.
            name is name of key in template map.
            values is list of strings or dicts.
            plural is plural of name, if not simply name + 's'.

            expansion works like this, given name 'foo'.

            if values is empty, expand 'no_foos'.

            if 'foo' not in template map, return values as a string,
            joined by space.

            expand 'start_foos'.

            for each value, expand 'foo'. if 'last_foo' in template
            map, expand it instead of 'foo' for last key.

            expand 'end_foos'.
            '''
            if plural: names = plural
            else: names = name + 's'
            if not values:
                noname = 'no_' + names
                if noname in self.t:
                    yield self.t(noname, **args)
                return
            if name not in self.t:
                if isinstance(values[0], str):
                    yield ' '.join(values)
                else:
                    for v in values:
                        yield dict(v, **args)
                return
            startname = 'start_' + names
            if startname in self.t:
                yield self.t(startname, **args)
            vargs = args.copy()
            def one(v, tag=name):
                try:
                    vargs.update(v)
                except (AttributeError, ValueError):
                    try:
                        for a, b in v:
                            vargs[a] = b
                    except ValueError:
                        vargs[name] = v
                return self.t(tag, **vargs)
            lastname = 'last_' + name
            if lastname in self.t:
                last = values.pop()
            else:
                last = None
            for v in values:
                yield one(v)
            if last is not None:
                yield one(last, tag=lastname)
            endname = 'end_' + names
            if endname in self.t:
                yield self.t(endname, **args)

        def showbranches(**args):
            branch = changes[5].get("branch")
            if branch != 'default':
                branch = util.tolocal(branch)
                return showlist('branch', [branch], plural='branches', **args)

        def showparents(**args):
            parents = [[('rev', log.rev(p)), ('node', hex(p))]
                       for p in log.parents(changenode)
                       if self.ui.debugflag or p != nullid]
            if (not self.ui.debugflag and len(parents) == 1 and
                parents[0][0][1] == rev - 1):
                return
            return showlist('parent', parents, **args)

        def showtags(**args):
            return showlist('tag', self.repo.nodetags(changenode), **args)

        def showextras(**args):
            extras = changes[5].items()
            extras.sort()
            for key, value in extras:
                args = args.copy()
                args.update(dict(key=key, value=value))
                yield self.t('extra', **args)

        def showcopies(**args):
            c = [{'name': x[0], 'source': x[1]} for x in copies]
            return showlist('file_copy', c, plural='file_copies', **args)

        if self.ui.debugflag:
            files = self.repo.status(log.parents(changenode)[0], changenode)[:3]
            def showfiles(**args):
                return showlist('file', files[0], **args)
            def showadds(**args):
                return showlist('file_add', files[1], **args)
            def showdels(**args):
                return showlist('file_del', files[2], **args)
            def showmanifest(**args):
                args = args.copy()
                args.update(dict(rev=self.repo.manifest.rev(changes[0]),
                                 node=hex(changes[0])))
                return self.t('manifest', **args)
        else:
            def showfiles(**args):
                return showlist('file', changes[3], **args)
            showadds = ''
            showdels = ''
            showmanifest = ''

        defprops = {
            'author': changes[1],
            'branches': showbranches,
            'date': changes[2],
            'desc': changes[4],
            'file_adds': showadds,
            'file_dels': showdels,
            'files': showfiles,
            'file_copies': showcopies,
            'manifest': showmanifest,
            'node': hex(changenode),
            'parents': showparents,
            'rev': rev,
            'tags': showtags,
            'extras': showextras,
            }
        props = props.copy()
        props.update(defprops)

        try:
            if self.ui.debugflag and 'header_debug' in self.t:
                key = 'header_debug'
            elif self.ui.quiet and 'header_quiet' in self.t:
                key = 'header_quiet'
            elif self.ui.verbose and 'header_verbose' in self.t:
                key = 'header_verbose'
            elif 'header' in self.t:
                key = 'header'
            else:
                key = ''
            if key:
                h = templater.stringify(self.t(key, **props))
                if self.buffered:
                    self.header[rev] = h
                else:
                    self.ui.write(h)
            if self.ui.debugflag and 'changeset_debug' in self.t:
                key = 'changeset_debug'
            elif self.ui.quiet and 'changeset_quiet' in self.t:
                key = 'changeset_quiet'
            elif self.ui.verbose and 'changeset_verbose' in self.t:
                key = 'changeset_verbose'
            else:
                key = 'changeset'
            self.ui.write(templater.stringify(self.t(key, **props)))
            self.showpatch(changenode)
        except KeyError, inst:
            raise util.Abort(_("%s: no key named '%s'") % (self.t.mapfile,
                                                           inst.args[0]))
        except SyntaxError, inst:
            raise util.Abort(_('%s: %s') % (self.t.mapfile, inst.args[0]))

def show_changeset(ui, repo, opts, buffered=False, matchfn=False):
    """show one changeset using template or regular display.

    Display format will be the first non-empty hit of:
    1. option 'template'
    2. option 'style'
    3. [ui] setting 'logtemplate'
    4. [ui] setting 'style'
    If all of these values are either the unset or the empty string,
    regular display via changeset_printer() is done.
    """
    # options
    patch = False
    if opts.get('patch'):
        patch = matchfn or util.always

    tmpl = opts.get('template')
    mapfile = None
    if tmpl:
        tmpl = templater.parsestring(tmpl, quoted=False)
    else:
        mapfile = opts.get('style')
        # ui settings
        if not mapfile:
            tmpl = ui.config('ui', 'logtemplate')
            if tmpl:
                tmpl = templater.parsestring(tmpl)
            else:
                mapfile = ui.config('ui', 'style')

    if tmpl or mapfile:
        if mapfile:
            if not os.path.split(mapfile)[0]:
                mapname = (templater.templatepath('map-cmdline.' + mapfile)
                           or templater.templatepath(mapfile))
                if mapname: mapfile = mapname
        try:
            t = changeset_templater(ui, repo, patch, mapfile, buffered)
        except SyntaxError, inst:
            raise util.Abort(inst.args[0])
        if tmpl: t.use_template(tmpl)
        return t
    return changeset_printer(ui, repo, patch, buffered)

def finddate(ui, repo, date):
    """Find the tipmost changeset that matches the given date spec"""
    df = util.matchdate(date + " to " + date)
    get = util.cachefunc(lambda r: repo.changectx(r).changeset())
    changeiter, matchfn = walkchangerevs(ui, repo, [], get, {'rev':None})
    results = {}
    for st, rev, fns in changeiter:
        if st == 'add':
            d = get(rev)[2]
            if df(d[0]):
                results[rev] = d
        elif st == 'iter':
            if rev in results:
                ui.status("Found revision %s from %s\n" %
                          (rev, util.datestr(results[rev])))
                return str(rev)

    raise util.Abort(_("revision matching date not found"))

def walkchangerevs(ui, repo, pats, change, opts):
    '''Iterate over files and the revs they changed in.

    Callers most commonly need to iterate backwards over the history
    it is interested in.  Doing so has awful (quadratic-looking)
    performance, so we use iterators in a "windowed" way.

    We walk a window of revisions in the desired order.  Within the
    window, we first walk forwards to gather data, then in the desired
    order (usually backwards) to display it.

    This function returns an (iterator, matchfn) tuple. The iterator
    yields 3-tuples. They will be of one of the following forms:

    "window", incrementing, lastrev: stepping through a window,
    positive if walking forwards through revs, last rev in the
    sequence iterated over - use to reset state for the current window

    "add", rev, fns: out-of-order traversal of the given file names
    fns, which changed during revision rev - use to gather data for
    possible display

    "iter", rev, None: in-order traversal of the revs earlier iterated
    over with "add" - use to display data'''

    def increasing_windows(start, end, windowsize=8, sizelimit=512):
        if start < end:
            while start < end:
                yield start, min(windowsize, end-start)
                start += windowsize
                if windowsize < sizelimit:
                    windowsize *= 2
        else:
            while start > end:
                yield start, min(windowsize, start-end-1)
                start -= windowsize
                if windowsize < sizelimit:
                    windowsize *= 2

    files, matchfn, anypats = matchpats(repo, pats, opts)
    follow = opts.get('follow') or opts.get('follow_first')

    if repo.changelog.count() == 0:
        return [], matchfn

    if follow:
        defrange = '%s:0' % repo.changectx().rev()
    else:
        defrange = 'tip:0'
    revs = revrange(repo, opts['rev'] or [defrange])
    wanted = {}
    slowpath = anypats or opts.get('removed')
    fncache = {}

    if not slowpath and not files:
        # No files, no patterns.  Display all revs.
        wanted = dict.fromkeys(revs)
    copies = []
    if not slowpath:
        # Only files, no patterns.  Check the history of each file.
        def filerevgen(filelog, node):
            cl_count = repo.changelog.count()
            if node is None:
                last = filelog.count() - 1
            else:
                last = filelog.rev(node)
            for i, window in increasing_windows(last, nullrev):
                revs = []
                for j in xrange(i - window, i + 1):
                    n = filelog.node(j)
                    revs.append((filelog.linkrev(n),
                                 follow and filelog.renamed(n)))
                revs.reverse()
                for rev in revs:
                    # only yield rev for which we have the changelog, it can
                    # happen while doing "hg log" during a pull or commit
                    if rev[0] < cl_count:
                        yield rev
        def iterfiles():
            for filename in files:
                yield filename, None
            for filename_node in copies:
                yield filename_node
        minrev, maxrev = min(revs), max(revs)
        for file_, node in iterfiles():
            filelog = repo.file(file_)
            # A zero count may be a directory or deleted file, so
            # try to find matching entries on the slow path.
            if filelog.count() == 0:
                slowpath = True
                break
            for rev, copied in filerevgen(filelog, node):
                if rev <= maxrev:
                    if rev < minrev:
                        break
                    fncache.setdefault(rev, [])
                    fncache[rev].append(file_)
                    wanted[rev] = 1
                    if follow and copied:
                        copies.append(copied)
    if slowpath:
        if follow:
            raise util.Abort(_('can only follow copies/renames for explicit '
                               'file names'))

        # The slow path checks files modified in every changeset.
        def changerevgen():
            for i, window in increasing_windows(repo.changelog.count()-1,
                                                nullrev):
                for j in xrange(i - window, i + 1):
                    yield j, change(j)[3]

        for rev, changefiles in changerevgen():
            matches = filter(matchfn, changefiles)
            if matches:
                fncache[rev] = matches
                wanted[rev] = 1

    class followfilter:
        def __init__(self, onlyfirst=False):
            self.startrev = nullrev
            self.roots = []
            self.onlyfirst = onlyfirst

        def match(self, rev):
            def realparents(rev):
                if self.onlyfirst:
                    return repo.changelog.parentrevs(rev)[0:1]
                else:
                    return filter(lambda x: x != nullrev,
                                  repo.changelog.parentrevs(rev))

            if self.startrev == nullrev:
                self.startrev = rev
                return True

            if rev > self.startrev:
                # forward: all descendants
                if not self.roots:
                    self.roots.append(self.startrev)
                for parent in realparents(rev):
                    if parent in self.roots:
                        self.roots.append(rev)
                        return True
            else:
                # backwards: all parents
                if not self.roots:
                    self.roots.extend(realparents(self.startrev))
                if rev in self.roots:
                    self.roots.remove(rev)
                    self.roots.extend(realparents(rev))
                    return True

            return False

    # it might be worthwhile to do this in the iterator if the rev range
    # is descending and the prune args are all within that range
    for rev in opts.get('prune', ()):
        rev = repo.changelog.rev(repo.lookup(rev))
        ff = followfilter()
        stop = min(revs[0], revs[-1])
        for x in xrange(rev, stop-1, -1):
            if ff.match(x) and x in wanted:
                del wanted[x]

    def iterate():
        if follow and not files:
            ff = followfilter(onlyfirst=opts.get('follow_first'))
            def want(rev):
                if ff.match(rev) and rev in wanted:
                    return True
                return False
        else:
            def want(rev):
                return rev in wanted

        for i, window in increasing_windows(0, len(revs)):
            yield 'window', revs[0] < revs[-1], revs[-1]
            nrevs = [rev for rev in revs[i:i+window] if want(rev)]
            srevs = list(nrevs)
            srevs.sort()
            for rev in srevs:
                fns = fncache.get(rev)
                if not fns:
                    def fns_generator():
                        for f in change(rev)[3]:
                            if matchfn(f):
                                yield f
                    fns = fns_generator()
                yield 'add', rev, fns
            for rev in nrevs:
                yield 'iter', rev, None
    return iterate(), matchfn
