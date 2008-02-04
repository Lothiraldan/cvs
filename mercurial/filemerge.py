# filemerge.py - file-level merge handling for Mercurial
#
# Copyright 2006, 2007, 2008 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from node import *
from i18n import _
import util, os, tempfile, context, simplemerge, re

def _toolstr(ui, tool, part, default=None):
    return ui.config("merge-tools", tool + "." + part, default)

def _toolbool(ui, tool, part, default=False):
    return ui.configbool("merge-tools", tool + "." + part, default)

def _findtool(ui, tool):
    return util.find_exe(_toolstr(ui, tool, "executable", tool))

def _picktool(repo, ui, path, binary, symlink):
    def check(tool, pat, symlink, binary):
        tmsg = tool
        if pat:
            tmsg += " specified for " + pat
        if pat and not _findtool(ui, tool): # skip search if not matching
            ui.warn(_("couldn't find merge tool %s\n") % tmsg)
        elif symlink and not _toolbool(ui, tool, "symlink"):
            ui.warn(_("tool %s can't handle symlinks\n") % tmsg)
        elif binary and not _toolbool(ui, tool, "binary"):
            ui.warn(_("tool %s can't handle binary\n") % tmsg)
        else:
            return True
        return False

    # HGMERGE takes precedence
    if os.environ.get("HGMERGE"):
        return os.environ.get("HGMERGE")

    # then patterns
    for pattern, tool in ui.configitems("merge-patterns"):
        mf = util.matcher(repo.root, "", [pat], [], [])[1]
        if mf(path) and check(tool, pat, symlink, False):
                return tool

    # then merge tools
    tools = {}
    for k,v in ui.configitems("merge-tools"):
        t = k.split('.')[0]
        if t not in tools:
            tools[t] = int(_toolstr(ui, t, "priority", "0"))
    tools = [(-p,t) for t,p in tools.items()]
    tools.sort()
    if ui.config("ui", "merge"):
        tools.insert(0, (None, ui.config("ui", "merge"))) # highest priority
    tools.append((None, "hgmerge")) # the old default, if found
    tools.append((None, "internal:merge")) # internal merge as last resort
    for p,t in tools:
        if _findtool(ui, t) and check(t, None, symlink, binary):
            return t

def filemerge(repo, fw, fd, fo, wctx, mctx):
    """perform a 3-way merge in the working directory

    fw = original filename in the working directory
    fd = destination filename in the working directory
    fo = filename in other parent
    wctx, mctx = working and merge changecontexts
    """

    def temp(prefix, ctx):
        pre = "%s~%s." % (os.path.basename(ctx.path()), prefix)
        (fd, name) = tempfile.mkstemp(prefix=pre)
        data = repo.wwritedata(ctx.path(), ctx.data())
        f = os.fdopen(fd, "wb")
        f.write(data)
        f.close()
        return name

    def isbin(ctx):
        try:
            return util.binary(ctx.data())
        except IOError:
            return False

    fco = mctx.filectx(fo)
    if not fco.cmp(wctx.filectx(fd).data()): # files identical?
        return None

    ui = repo.ui
    fcm = wctx.filectx(fw)
    fca = fcm.ancestor(fco) or repo.filectx(fw, fileid=nullrev)
    binary = isbin(fcm) or isbin(fco) or isbin(fca)
    symlink = fcm.islink() or fco.islink()
    tool = _picktool(repo, ui, fw, binary, symlink)
    ui.debug(_("picked tool '%s' for %s (binary %s symlink %s)\n") %
               (tool, fw, binary, symlink))

    if not tool:
        tool = "internal:local"
        if ui.prompt(_(" no tool found to merge %s\n"
                       "keep (l)ocal or take (o)ther?") % fw,
                     _("[lo]"), _("l")) != _("l"):
            tool = "internal:other"
    if tool == "internal:local":
        return 0
    if tool == "internal:other":
        repo.wwrite(fd, fco.data(), fco.fileflags())
        return 0
    if tool == "internal:fail":
        return 1

    # do the actual merge
    a = repo.wjoin(fd)
    b = temp("base", fca)
    c = temp("other", fco)
    out = ""
    back = a + ".orig"
    util.copyfile(a, back)

    if fw != fo:
        repo.ui.status(_("merging %s and %s\n") % (fw, fo))
    else:
        repo.ui.status(_("merging %s\n") % fw)
    repo.ui.debug(_("my %s other %s ancestor %s\n") % (fcm, fco, fca))

    # do we attempt to simplemerge first?
    if _toolbool(ui, tool, "premerge", not (binary or symlink)):
        r = simplemerge.simplemerge(a, b, c, quiet=True)
        if not r:
            ui.debug(_(" premerge successful\n"))
            os.unlink(back)
            os.unlink(b)
            os.unlink(c)
            return 0
        util.copyfile(back, a) # restore from backup and try again

    env = dict(HG_FILE=fd,
               HG_MY_NODE=str(wctx.parents()[0]),
               HG_OTHER_NODE=str(mctx),
               HG_MY_ISLINK=fcm.islink(),
               HG_OTHER_ISLINK=fco.islink(),
               HG_BASE_ISLINK=fca.islink())

    if tool == "internal:merge":
        r = simplemerge.simplemerge(a, b, c, label=['local', 'other'])
    else:
        toolpath = _findtool(ui, tool)
        args = _toolstr(ui, tool, "args", '$local $base $other')
        if "$output" in args:
            out, a = a, back # read input from backup, write to original
        replace = dict(local=a, base=b, other=c, output=out)
        args = re.sub("\$(local|base|other|output)",
                      lambda x: '"%s"' % replace[x.group()[1:]], args)
        r = util.system(toolpath + ' ' + args, cwd=repo.root, environ=env)

    if not r and _toolbool(ui, tool, "checkconflicts"):
        if re.match("^(<<<<<<< .*|=======|>>>>>>> .*)$", fcm.data()):
            r = 1

    if r:
        repo.ui.warn(_("merging %s failed!\n") % fd)
    else:
        os.unlink(back)

    os.unlink(b)
    os.unlink(c)
    return r
