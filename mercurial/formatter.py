# formatter.py - generic output formatting for mercurial
#
# Copyright 2012 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

"""Generic output formatting for Mercurial

The formatter provides API to show data in various ways. The following
functions should be used in place of ui.write():

- fm.write() for unconditional output
- fm.condwrite() to show some extra data conditionally in plain output
- fm.context() to provide changectx to template output
- fm.data() to provide extra data to JSON or template output
- fm.plain() to show raw text that isn't provided to JSON or template output

To show structured data (e.g. date tuples, dicts, lists), apply fm.format*()
beforehand so the data is converted to the appropriate data type. Use
fm.isplain() if you need to convert or format data conditionally which isn't
supported by the formatter API.

To build nested structure (i.e. a list of dicts), use fm.nested().

See also https://www.mercurial-scm.org/wiki/GenericTemplatingPlan

fm.condwrite() vs 'if cond:':

In most cases, use fm.condwrite() so users can selectively show the data
in template output. If it's costly to build data, use plain 'if cond:' with
fm.write().

fm.nested() vs fm.formatdict() (or fm.formatlist()):

fm.nested() should be used to form a tree structure (a list of dicts of
lists of dicts...) which can be accessed through template keywords, e.g.
"{foo % "{bar % {...}} {baz % {...}}"}". On the other hand, fm.formatdict()
exports a dict-type object to template, which can be accessed by e.g.
"{get(foo, key)}" function.

Doctest helper:

>>> def show(fn, verbose=False, **opts):
...     import sys
...     from . import ui as uimod
...     ui = uimod.ui()
...     ui.fout = sys.stdout  # redirect to doctest
...     ui.verbose = verbose
...     return fn(ui, ui.formatter(fn.__name__, opts))

Basic example:

>>> def files(ui, fm):
...     files = [('foo', 123, (0, 0)), ('bar', 456, (1, 0))]
...     for f in files:
...         fm.startitem()
...         fm.write('path', '%s', f[0])
...         fm.condwrite(ui.verbose, 'date', '  %s',
...                      fm.formatdate(f[2], '%Y-%m-%d %H:%M:%S'))
...         fm.data(size=f[1])
...         fm.plain('\\n')
...     fm.end()
>>> show(files)
foo
bar
>>> show(files, verbose=True)
foo  1970-01-01 00:00:00
bar  1970-01-01 00:00:01
>>> show(files, template='json')
[
 {
  "date": [0, 0],
  "path": "foo",
  "size": 123
 },
 {
  "date": [1, 0],
  "path": "bar",
  "size": 456
 }
]
>>> show(files, template='path: {path}\\ndate: {date|rfc3339date}\\n')
path: foo
date: 1970-01-01T00:00:00+00:00
path: bar
date: 1970-01-01T00:00:01+00:00

Nested example:

>>> def subrepos(ui, fm):
...     fm.startitem()
...     fm.write('repo', '[%s]\\n', 'baz')
...     files(ui, fm.nested('files'))
...     fm.end()
>>> show(subrepos)
[baz]
foo
bar
>>> show(subrepos, template='{repo}: {join(files % "{path}", ", ")}\\n')
baz: foo, bar
"""

from __future__ import absolute_import

import itertools
import os

from .i18n import _
from .node import (
    hex,
    short,
)

from . import (
    error,
    templatefilters,
    templatekw,
    templater,
    util,
)

pickle = util.pickle

class _nullconverter(object):
    '''convert non-primitive data types to be processed by formatter'''
    @staticmethod
    def formatdate(date, fmt):
        '''convert date tuple to appropriate format'''
        return date
    @staticmethod
    def formatdict(data, key, value, fmt, sep):
        '''convert dict or key-value pairs to appropriate dict format'''
        # use plain dict instead of util.sortdict so that data can be
        # serialized as a builtin dict in pickle output
        return dict(data)
    @staticmethod
    def formatlist(data, name, fmt, sep):
        '''convert iterable to appropriate list format'''
        return list(data)

class baseformatter(object):
    def __init__(self, ui, topic, opts, converter):
        self._ui = ui
        self._topic = topic
        self._style = opts.get("style")
        self._template = opts.get("template")
        self._converter = converter
        self._item = None
        # function to convert node to string suitable for this output
        self.hexfunc = hex
    def __enter__(self):
        return self
    def __exit__(self, exctype, excvalue, traceback):
        if exctype is None:
            self.end()
    def _showitem(self):
        '''show a formatted item once all data is collected'''
        pass
    def startitem(self):
        '''begin an item in the format list'''
        if self._item is not None:
            self._showitem()
        self._item = {}
    def formatdate(self, date, fmt='%a %b %d %H:%M:%S %Y %1%2'):
        '''convert date tuple to appropriate format'''
        return self._converter.formatdate(date, fmt)
    def formatdict(self, data, key='key', value='value', fmt='%s=%s', sep=' '):
        '''convert dict or key-value pairs to appropriate dict format'''
        return self._converter.formatdict(data, key, value, fmt, sep)
    def formatlist(self, data, name, fmt='%s', sep=' '):
        '''convert iterable to appropriate list format'''
        # name is mandatory argument for now, but it could be optional if
        # we have default template keyword, e.g. {item}
        return self._converter.formatlist(data, name, fmt, sep)
    def context(self, **ctxs):
        '''insert context objects to be used to render template keywords'''
        pass
    def data(self, **data):
        '''insert data into item that's not shown in default output'''
        self._item.update(data)
    def write(self, fields, deftext, *fielddata, **opts):
        '''do default text output while assigning data to item'''
        fieldkeys = fields.split()
        assert len(fieldkeys) == len(fielddata)
        self._item.update(zip(fieldkeys, fielddata))
    def condwrite(self, cond, fields, deftext, *fielddata, **opts):
        '''do conditional write (primarily for plain formatter)'''
        fieldkeys = fields.split()
        assert len(fieldkeys) == len(fielddata)
        self._item.update(zip(fieldkeys, fielddata))
    def plain(self, text, **opts):
        '''show raw text for non-templated mode'''
        pass
    def isplain(self):
        '''check for plain formatter usage'''
        return False
    def nested(self, field):
        '''sub formatter to store nested data in the specified field'''
        self._item[field] = data = []
        return _nestedformatter(self._ui, self._converter, data)
    def end(self):
        '''end output for the formatter'''
        if self._item is not None:
            self._showitem()

class _nestedformatter(baseformatter):
    '''build sub items and store them in the parent formatter'''
    def __init__(self, ui, converter, data):
        baseformatter.__init__(self, ui, topic='', opts={}, converter=converter)
        self._data = data
    def _showitem(self):
        self._data.append(self._item)

def _iteritems(data):
    '''iterate key-value pairs in stable order'''
    if isinstance(data, dict):
        return sorted(data.iteritems())
    return data

class _plainconverter(object):
    '''convert non-primitive data types to text'''
    @staticmethod
    def formatdate(date, fmt):
        '''stringify date tuple in the given format'''
        return util.datestr(date, fmt)
    @staticmethod
    def formatdict(data, key, value, fmt, sep):
        '''stringify key-value pairs separated by sep'''
        return sep.join(fmt % (k, v) for k, v in _iteritems(data))
    @staticmethod
    def formatlist(data, name, fmt, sep):
        '''stringify iterable separated by sep'''
        return sep.join(fmt % e for e in data)

class plainformatter(baseformatter):
    '''the default text output scheme'''
    def __init__(self, ui, topic, opts):
        baseformatter.__init__(self, ui, topic, opts, _plainconverter)
        if ui.debugflag:
            self.hexfunc = hex
        else:
            self.hexfunc = short
    def startitem(self):
        pass
    def data(self, **data):
        pass
    def write(self, fields, deftext, *fielddata, **opts):
        self._ui.write(deftext % fielddata, **opts)
    def condwrite(self, cond, fields, deftext, *fielddata, **opts):
        '''do conditional write'''
        if cond:
            self._ui.write(deftext % fielddata, **opts)
    def plain(self, text, **opts):
        self._ui.write(text, **opts)
    def isplain(self):
        return True
    def nested(self, field):
        # nested data will be directly written to ui
        return self
    def end(self):
        pass

class debugformatter(baseformatter):
    def __init__(self, ui, out, topic, opts):
        baseformatter.__init__(self, ui, topic, opts, _nullconverter)
        self._out = out
        self._out.write("%s = [\n" % self._topic)
    def _showitem(self):
        self._out.write("    " + repr(self._item) + ",\n")
    def end(self):
        baseformatter.end(self)
        self._out.write("]\n")

class pickleformatter(baseformatter):
    def __init__(self, ui, out, topic, opts):
        baseformatter.__init__(self, ui, topic, opts, _nullconverter)
        self._out = out
        self._data = []
    def _showitem(self):
        self._data.append(self._item)
    def end(self):
        baseformatter.end(self)
        self._out.write(pickle.dumps(self._data))

class jsonformatter(baseformatter):
    def __init__(self, ui, out, topic, opts):
        baseformatter.__init__(self, ui, topic, opts, _nullconverter)
        self._out = out
        self._out.write("[")
        self._first = True
    def _showitem(self):
        if self._first:
            self._first = False
        else:
            self._out.write(",")

        self._out.write("\n {\n")
        first = True
        for k, v in sorted(self._item.items()):
            if first:
                first = False
            else:
                self._out.write(",\n")
            u = templatefilters.json(v, paranoid=False)
            self._out.write('  "%s": %s' % (k, u))
        self._out.write("\n }")
    def end(self):
        baseformatter.end(self)
        self._out.write("\n]\n")

class _templateconverter(object):
    '''convert non-primitive data types to be processed by templater'''
    @staticmethod
    def formatdate(date, fmt):
        '''return date tuple'''
        return date
    @staticmethod
    def formatdict(data, key, value, fmt, sep):
        '''build object that can be evaluated as either plain string or dict'''
        data = util.sortdict(_iteritems(data))
        def f():
            yield _plainconverter.formatdict(data, key, value, fmt, sep)
        return templatekw.hybriddict(data, key=key, value=value, fmt=fmt,
                                     gen=f())
    @staticmethod
    def formatlist(data, name, fmt, sep):
        '''build object that can be evaluated as either plain string or list'''
        data = list(data)
        def f():
            yield _plainconverter.formatlist(data, name, fmt, sep)
        return templatekw.hybridlist(data, name=name, fmt=fmt, gen=f())

class templateformatter(baseformatter):
    def __init__(self, ui, out, topic, opts):
        baseformatter.__init__(self, ui, topic, opts, _templateconverter)
        self._out = out
        self._topic = topic
        self._t = gettemplater(ui, topic, opts.get('template', ''),
                               cache=templatekw.defaulttempl)
        self._counter = itertools.count()
        self._cache = {}  # for templatekw/funcs to store reusable data
    def context(self, **ctxs):
        '''insert context objects to be used to render template keywords'''
        assert all(k == 'ctx' for k in ctxs)
        self._item.update(ctxs)
    def _showitem(self):
        # TODO: add support for filectx. probably each template keyword or
        # function will have to declare dependent resources. e.g.
        # @templatekeyword(..., requires=('ctx',))
        props = {}
        if 'ctx' in self._item:
            props.update(templatekw.keywords)
        props['index'] = next(self._counter)
        # explicitly-defined fields precede templatekw
        props.update(self._item)
        if 'ctx' in self._item:
            # but template resources must be always available
            props['templ'] = self._t
            props['repo'] = props['ctx'].repo()
            props['revcache'] = {}
        g = self._t(self._topic, ui=self._ui, cache=self._cache, **props)
        self._out.write(templater.stringify(g))

def lookuptemplate(ui, topic, tmpl):
    # looks like a literal template?
    if '{' in tmpl:
        return tmpl, None

    # perhaps a stock style?
    if not os.path.split(tmpl)[0]:
        mapname = (templater.templatepath('map-cmdline.' + tmpl)
                   or templater.templatepath(tmpl))
        if mapname and os.path.isfile(mapname):
            return None, mapname

    # perhaps it's a reference to [templates]
    t = ui.config('templates', tmpl)
    if t:
        return templater.unquotestring(t), None

    if tmpl == 'list':
        ui.write(_("available styles: %s\n") % templater.stylelist())
        raise error.Abort(_("specify a template"))

    # perhaps it's a path to a map or a template
    if ('/' in tmpl or '\\' in tmpl) and os.path.isfile(tmpl):
        # is it a mapfile for a style?
        if os.path.basename(tmpl).startswith("map-"):
            return None, os.path.realpath(tmpl)
        tmpl = open(tmpl).read()
        return tmpl, None

    # constant string?
    return tmpl, None

def gettemplater(ui, topic, spec, cache=None):
    tmpl, mapfile = lookuptemplate(ui, topic, spec)
    assert not (tmpl and mapfile)
    if mapfile:
        return templater.templater.frommapfile(mapfile, cache=cache)
    return maketemplater(ui, topic, tmpl, cache=cache)

def maketemplater(ui, topic, tmpl, cache=None):
    """Create a templater from a string template 'tmpl'"""
    aliases = ui.configitems('templatealias')
    t = templater.templater(cache=cache, aliases=aliases)
    if tmpl:
        t.cache[topic] = tmpl
    return t

def formatter(ui, topic, opts):
    template = opts.get("template", "")
    if template == "json":
        return jsonformatter(ui, ui, topic, opts)
    elif template == "pickle":
        return pickleformatter(ui, ui, topic, opts)
    elif template == "debug":
        return debugformatter(ui, ui, topic, opts)
    elif template != "":
        return templateformatter(ui, ui, topic, opts)
    # developer config: ui.formatdebug
    elif ui.configbool('ui', 'formatdebug'):
        return debugformatter(ui, ui, topic, opts)
    # deprecated config: ui.formatjson
    elif ui.configbool('ui', 'formatjson'):
        return jsonformatter(ui, ui, topic, opts)
    return plainformatter(ui, topic, opts)
