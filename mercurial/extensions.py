# extensions.py - extension handling for mercurial
#
# Copyright 2005-2007 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2, incorporated herein by reference.

import imp, os
import util, cmdutil
from i18n import _

_extensions = {}
_order = []

def extensions():
    for name in _order:
        module = _extensions[name]
        if module:
            yield name, module

def find(name):
    '''return module with given extension name'''
    try:
        return _extensions[name]
    except KeyError:
        for k, v in _extensions.iteritems():
            if k.endswith('.' + name) or k.endswith('/' + name):
                return v
        raise KeyError(name)

def loadpath(path, module_name):
    module_name = module_name.replace('.', '_')
    path = os.path.expanduser(path)
    if os.path.isdir(path):
        # module/__init__.py style
        d, f = os.path.split(path.rstrip('/'))
        fd, fpath, desc = imp.find_module(f, [d])
        return imp.load_module(module_name, fd, fpath, desc)
    else:
        return imp.load_source(module_name, path)

def load(ui, name, path):
    if name.startswith('hgext.') or name.startswith('hgext/'):
        shortname = name[6:]
    else:
        shortname = name
    if shortname in _extensions:
        return
    _extensions[shortname] = None
    if path:
        # the module will be loaded in sys.modules
        # choose an unique name so that it doesn't
        # conflicts with other modules
        mod = loadpath(path, 'hgext.%s' % name)
    else:
        def importh(name):
            mod = __import__(name)
            components = name.split('.')
            for comp in components[1:]:
                mod = getattr(mod, comp)
            return mod
        try:
            mod = importh("hgext.%s" % name)
        except ImportError:
            mod = importh(name)
    _extensions[shortname] = mod
    _order.append(shortname)

    uisetup = getattr(mod, 'uisetup', None)
    if uisetup:
        uisetup(ui)

def loadall(ui):
    result = ui.configitems("extensions")
    for (name, path) in result:
        if path:
            if path[0] == '!':
                continue
        try:
            load(ui, name, path)
        except KeyboardInterrupt:
            raise
        except Exception, inst:
            if path:
                ui.warn(_("*** failed to import extension %s from %s: %s\n")
                        % (name, path, inst))
            else:
                ui.warn(_("*** failed to import extension %s: %s\n")
                        % (name, inst))
            if ui.traceback():
                return 1

def wrapcommand(table, command, wrapper):
    aliases, entry = cmdutil.findcmd(command, table)
    for alias, e in table.iteritems():
        if e is entry:
            key = alias
            break

    origfn = entry[0]
    def wrap(*args, **kwargs):
        return util.checksignature(wrapper)(
            util.checksignature(origfn), *args, **kwargs)

    wrap.__doc__ = getattr(origfn, '__doc__')
    wrap.__module__ = getattr(origfn, '__module__')

    newentry = list(entry)
    newentry[0] = wrap
    table[key] = tuple(newentry)
    return entry

def wrapfunction(container, funcname, wrapper):
    def wrap(*args, **kwargs):
        return wrapper(origfn, *args, **kwargs)

    origfn = getattr(container, funcname)
    setattr(container, funcname, wrap)
    return origfn
