# hook.py - hook support for mercurial
#
# Copyright 2007 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from i18n import _
import util

def _pythonhook(ui, repo, name, hname, funcname, args, throw):
    '''call python hook. hook is callable object, looked up as
    name in python module. if callable returns "true", hook
    fails, else passes. if hook raises exception, treated as
    hook failure. exception propagates if throw is "true".

    reason for "true" meaning "hook failed" is so that
    unmodified commands (e.g. mercurial.commands.update) can
    be run as hooks without wrappers to convert return values.'''

    ui.note(_("calling hook %s: %s\n") % (hname, funcname))
    obj = funcname
    if not callable(obj):
        d = funcname.rfind('.')
        if d == -1:
            raise util.Abort(_('%s hook is invalid ("%s" not in '
                               'a module)') % (hname, funcname))
        modname = funcname[:d]
        try:
            obj = __import__(modname)
        except ImportError:
            try:
                # extensions are loaded with hgext_ prefix
                obj = __import__("hgext_%s" % modname)
            except ImportError:
                raise util.Abort(_('%s hook is invalid '
                                   '(import of "%s" failed)') %
                                 (hname, modname))
        try:
            for p in funcname.split('.')[1:]:
                obj = getattr(obj, p)
        except AttributeError, err:
            raise util.Abort(_('%s hook is invalid '
                               '("%s" is not defined)') %
                             (hname, funcname))
        if not callable(obj):
            raise util.Abort(_('%s hook is invalid '
                               '("%s" is not callable)') %
                             (hname, funcname))
    try:
        r = obj(ui=ui, repo=repo, hooktype=name, **args)
    except (KeyboardInterrupt, util.SignalInterrupt):
        raise
    except Exception, exc:
        if isinstance(exc, util.Abort):
            ui.warn(_('error: %s hook failed: %s\n') %
                         (hname, exc.args[0]))
        else:
            ui.warn(_('error: %s hook raised an exception: '
                           '%s\n') % (hname, exc))
        if throw:
            raise
        ui.print_exc()
        return True
    if r:
        if throw:
            raise util.Abort(_('%s hook failed') % hname)
        ui.warn(_('warning: %s hook failed\n') % hname)
    return r

def _exthook(ui, repo, name, cmd, args, throw):
    ui.note(_("running hook %s: %s\n") % (name, cmd))
    env = dict([('HG_' + k.upper(), v) for k, v in args.iteritems()])
    r = util.system(cmd, environ=env, cwd=repo.root)
    if r:
        desc, r = util.explain_exit(r)
        if throw:
            raise util.Abort(_('%s hook %s') % (name, desc))
        ui.warn(_('warning: %s hook %s\n') % (name, desc))
    return r

def hook(ui, repo, name, throw=False, **args):
    r = False
    hooks = [(hname, cmd) for hname, cmd in ui.configitems("hooks")
             if hname.split(".", 1)[0] == name and cmd]
    hooks.sort()
    for hname, cmd in hooks:
        if callable(cmd):
            r = _pythonhook(ui, repo, name, hname, cmd, args, throw) or r
        elif cmd.startswith('python:'):
            r = _pythonhook(ui, repo, name, hname, cmd[7:].strip(),
                            args, throw) or r
        else:
            r = _exthook(ui, repo, hname, cmd, args, throw) or r
    return r

