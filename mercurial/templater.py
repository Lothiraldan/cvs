# templater.py - template expansion for output
#
# Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

import re
from demandload import demandload
from i18n import gettext as _
from node import *
demandload(globals(), "cStringIO cgi re sys os time urllib util textwrap")

esctable = {
    '\\': '\\',
    'r': '\r',
    't': '\t',
    'n': '\n',
    'v': '\v',
    }

def parsestring(s, quoted=True):
    '''parse a string using simple c-like syntax.
    string must be in quotes if quoted is True.'''
    fp = cStringIO.StringIO()
    if quoted:
        first = s[0]
        if len(s) < 2: raise SyntaxError(_('string too short'))
        if first not in "'\"": raise SyntaxError(_('invalid quote'))
        if s[-1] != first: raise SyntaxError(_('unmatched quotes'))
        s = s[1:-1]
    escape = False
    for c in s:
        if escape:
            fp.write(esctable.get(c, c))
            escape = False
        elif c == '\\': escape = True
        elif quoted and c == first: raise SyntaxError(_('string ends early'))
        else: fp.write(c)
    if escape: raise SyntaxError(_('unterminated escape'))
    return fp.getvalue()

class templater(object):
    '''template expansion engine.

    template expansion works like this. a map file contains key=value
    pairs. if value is quoted, it is treated as string. otherwise, it
    is treated as name of template file.

    templater is asked to expand a key in map. it looks up key, and
    looks for atrings like this: {foo}. it expands {foo} by looking up
    foo in map, and substituting it. expansion is recursive: it stops
    when there is no more {foo} to replace.

    expansion also allows formatting and filtering.

    format uses key to expand each item in list. syntax is
    {key%format}.

    filter uses function to transform value. syntax is
    {key|filter1|filter2|...}.'''

    def __init__(self, mapfile, filters={}, defaults={}, cache={}):
        '''set up template engine.
        mapfile is name of file to read map definitions from.
        filters is dict of functions. each transforms a value into another.
        defaults is dict of default map definitions.'''
        self.mapfile = mapfile or 'template'
        self.cache = cache.copy()
        self.map = {}
        self.base = (mapfile and os.path.dirname(mapfile)) or ''
        self.filters = filters
        self.defaults = defaults

        if not mapfile:
            return
        i = 0
        for l in file(mapfile):
            l = l.strip()
            i += 1
            if not l or l[0] in '#;': continue
            m = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$', l)
            if m:
                key, val = m.groups()
                if val[0] in "'\"":
                    try:
                        self.cache[key] = parsestring(val)
                    except SyntaxError, inst:
                        raise SyntaxError('%s:%s: %s' %
                                          (mapfile, i, inst.args[0]))
                else:
                    self.map[key] = os.path.join(self.base, val)
            else:
                raise SyntaxError(_("%s:%s: parse error") % (mapfile, i))

    def __contains__(self, key):
        return key in self.cache

    def __call__(self, t, **map):
        '''perform expansion.
        t is name of map element to expand.
        map is added elements to use during expansion.'''
        m = self.defaults.copy()
        m.update(map)
        try:
            tmpl = self.cache[t]
        except KeyError:
            try:
                tmpl = self.cache[t] = file(self.map[t]).read()
            except IOError, inst:
                raise IOError(inst.args[0], _('template file %s: %s') %
                              (self.map[t], inst.args[1]))
        return self.template(tmpl, self.filters, **m)

    template_re = re.compile(r"[#{]([a-zA-Z_][a-zA-Z0-9_]*)"
                             r"((%[a-zA-Z_][a-zA-Z0-9_]*)*)"
                             r"((\|[a-zA-Z_][a-zA-Z0-9_]*)*)[#}]")

    def template(self, tmpl, filters={}, **map):
        lm = map.copy()
        while tmpl:
            m = self.template_re.search(tmpl)
            if m:
                start, end = m.span(0)
                s, e = tmpl[start], tmpl[end - 1]
                key = m.group(1)
                if ((s == '#' and e != '#') or (s == '{' and e != '}')):
                    raise SyntaxError(_("'%s'/'%s' mismatch expanding '%s'") %
                                      (s, e, key))
                if start:
                    yield tmpl[:start]
                v = map.get(key, "")
                v = callable(v) and v(**map) or v

                format = m.group(2)
                fl = m.group(4)

                if format:
                    q = v.__iter__
                    for i in q():
                        lm.update(i)
                        yield self(format[1:], **lm)

                    v = ""

                elif fl:
                    for f in fl.split("|")[1:]:
                        v = filters[f](v)

                yield v
                tmpl = tmpl[end:]
            else:
                yield tmpl
                break

agescales = [("second", 1),
             ("minute", 60),
             ("hour", 3600),
             ("day", 3600 * 24),
             ("week", 3600 * 24 * 7),
             ("month", 3600 * 24 * 30),
             ("year", 3600 * 24 * 365)]

agescales.reverse()

def age(date):
    '''turn a (timestamp, tzoff) tuple into an age string.'''

    def plural(t, c):
        if c == 1:
            return t
        return t + "s"
    def fmt(t, c):
        return "%d %s" % (c, plural(t, c))

    now = time.time()
    then = date[0]
    delta = max(1, int(now - then))

    for t, s in agescales:
        n = delta / s
        if n >= 2 or s == 1:
            return fmt(t, n)

def stringify(thing):
    '''turn nested template iterator into string.'''
    cs = cStringIO.StringIO()
    def walk(things):
        for t in things:
            if hasattr(t, '__iter__'):
                walk(t)
            else:
                cs.write(t)
    walk(thing)
    return cs.getvalue()

para_re = re.compile('(\n\n|\n\\s*[-*]\\s*)', re.M)
space_re = re.compile(r'  +')

def fill(text, width):
    '''fill many paragraphs.'''
    def findparas():
        start = 0
        while True:
            m = para_re.search(text, start)
            if not m:
                w = len(text)
                while w > start and text[w-1].isspace(): w -= 1
                yield text[start:w], text[w:]
                break
            yield text[start:m.start(0)], m.group(1)
            start = m.end(1)

    fp = cStringIO.StringIO()
    for para, rest in findparas():
        fp.write(space_re.sub(' ', textwrap.fill(para, width)))
        fp.write(rest)
    return fp.getvalue()

def isodate(date):
    '''turn a (timestamp, tzoff) tuple into an iso 8631 date and time.'''
    return util.datestr(date, format='%Y-%m-%d %H:%M')

def nl2br(text):
    '''replace raw newlines with xhtml line breaks.'''
    return text.replace('\n', '<br/>\n')

def obfuscate(text):
    return ''.join(['&#%d;' % ord(c) for c in text])

def domain(author):
    '''get domain of author, or empty string if none.'''
    f = author.find('@')
    if f == -1: return ''
    author = author[f+1:]
    f = author.find('>')
    if f >= 0: author = author[:f]
    return author

def email(author):
    '''get email of author.'''
    r = author.find('>')
    if r == -1: r = None
    return author[author.find('<')+1:r]

def person(author):
    '''get name of author, or else username.'''
    f = author.find('<')
    if f == -1: return util.shortuser(author)
    return author[:f].rstrip()

def shortdate(date):
    '''turn (timestamp, tzoff) tuple into iso 8631 date.'''
    return util.datestr(date, format='%Y-%m-%d', timezone=False)

def indent(text, prefix):
    '''indent each non-empty line of text after first with prefix.'''
    fp = cStringIO.StringIO()
    lines = text.splitlines()
    num_lines = len(lines)
    for i in xrange(num_lines):
        l = lines[i]
        if i and l.strip(): fp.write(prefix)
        fp.write(l)
        if i < num_lines - 1 or text.endswith('\n'):
            fp.write('\n')
    return fp.getvalue()

common_filters = {
    "addbreaks": nl2br,
    "age": age,
    "date": lambda x: util.datestr(x),
    "domain": domain,
    "email": email,
    "escape": lambda x: cgi.escape(x, True),
    "fill68": lambda x: fill(x, width=68),
    "fill76": lambda x: fill(x, width=76),
    "firstline": lambda x: x.splitlines(1)[0].rstrip('\r\n'),
    "tabindent": lambda x: indent(x, '\t'),
    "isodate": isodate,
    "obfuscate": obfuscate,
    "permissions": lambda x: x and "-rwxr-xr-x" or "-rw-r--r--",
    "person": person,
    "rfc822date": lambda x: util.datestr(x, "%a, %d %b %Y %H:%M:%S"),
    "short": lambda x: x[:12],
    "shortdate": shortdate,
    "stringify": stringify,
    "strip": lambda x: x.strip(),
    "urlescape": lambda x: urllib.quote(x),
    "user": lambda x: util.shortuser(x),
    }

def templatepath(name=None):
    '''return location of template file or directory (if no name).
    returns None if not found.'''

    # executable version (py2exe) doesn't support __file__
    if hasattr(sys, 'frozen'):
        module = sys.executable
    else:
        module = __file__
    for f in 'templates', '../templates':
        fl = f.split('/')
        if name: fl.append(name)
        p = os.path.join(os.path.dirname(module), *fl)
        if (name and os.path.exists(p)) or os.path.isdir(p):
            return os.path.normpath(p)

class changeset_templater(object):
    '''format changeset information.'''

    def __init__(self, ui, repo, mapfile, dest=None):
        self.t = templater(mapfile, common_filters,
                           cache={'parent': '{rev}:{node|short} ',
                                  'manifest': '{rev}:{node|short}'})
        self.ui = ui
        self.dest = dest
        self.repo = repo

    def use_template(self, t):
        '''set template string to use'''
        self.t.cache['changeset'] = t

    def write(self, thing, header=False):
        '''write expanded template.
        uses in-order recursive traverse of iterators.'''
        dest = self.dest or self.ui
        for t in thing:
            if hasattr(t, '__iter__'):
                self.write(t, header=header)
            elif header:
                dest.write_header(t)
            else:
                dest.write(t)

    def write_header(self, thing):
        self.write(thing, header=True)

    def show(self, rev=0, changenode=None, brinfo=None):
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

        if brinfo:
            def showbranches(**args):
                if changenode in brinfo:
                    for x in showlist('branch', brinfo[changenode],
                                      plural='branches', **args):
                        yield x
        else:
            showbranches = ''

        if self.ui.debugflag:
            def showmanifest(**args):
                args = args.copy()
                args.update(dict(rev=self.repo.manifest.rev(changes[0]),
                                 node=hex(changes[0])))
                yield self.t('manifest', **args)
        else:
            showmanifest = ''

        def showparents(**args):
            parents = [[('rev', log.rev(p)), ('node', hex(p))]
                       for p in log.parents(changenode)
                       if self.ui.debugflag or p != nullid]
            if (not self.ui.debugflag and len(parents) == 1 and
                parents[0][0][1] == rev - 1):
                return
            for x in showlist('parent', parents, **args):
                yield x

        def showtags(**args):
            for x in showlist('tag', self.repo.nodetags(changenode), **args):
                yield x

        if self.ui.debugflag:
            files = self.repo.changes(log.parents(changenode)[0], changenode)
            def showfiles(**args):
                for x in showlist('file', files[0], **args): yield x
            def showadds(**args):
                for x in showlist('file_add', files[1], **args): yield x
            def showdels(**args):
                for x in showlist('file_del', files[2], **args): yield x
        else:
            def showfiles(**args):
                for x in showlist('file', changes[3], **args): yield x
            showadds = ''
            showdels = ''

        props = {
            'author': changes[1],
            'branches': showbranches,
            'date': changes[2],
            'desc': changes[4],
            'file_adds': showadds,
            'file_dels': showdels,
            'files': showfiles,
            'manifest': showmanifest,
            'node': hex(changenode),
            'parents': showparents,
            'rev': rev,
            'tags': showtags,
            }

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
                self.write_header(self.t(key, **props))
            if self.ui.debugflag and 'changeset_debug' in self.t:
                key = 'changeset_debug'
            elif self.ui.quiet and 'changeset_quiet' in self.t:
                key = 'changeset_quiet'
            elif self.ui.verbose and 'changeset_verbose' in self.t:
                key = 'changeset_verbose'
            else:
                key = 'changeset'
            self.write(self.t(key, **props))
        except KeyError, inst:
            raise util.Abort(_("%s: no key named '%s'") % (self.t.mapfile,
                                                           inst.args[0]))
        except SyntaxError, inst:
            raise util.Abort(_('%s: %s') % (self.t.mapfile, inst.args[0]))
