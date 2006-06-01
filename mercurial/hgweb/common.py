# hgweb.py - web interface to a mercurial repository
#
# Copyright 21 May 2005 - (c) 2005 Jake Edge <jake@edge2.net>
# Copyright 2005 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

import os, mimetypes
import os.path

def get_mtime(repo_path):
    hg_path = os.path.join(repo_path, ".hg")
    cl_path = os.path.join(hg_path, "00changelog.i")
    if os.path.exists(os.path.join(cl_path)):
        return os.stat(cl_path).st_mtime
    else:
        return os.stat(hg_path).st_mtime

def staticfile(directory, fname):
    """return a file inside directory with guessed content-type header

    fname always uses '/' as directory separator and isn't allowed to
    contain unusual path components.
    Content-type is guessed using the mimetypes module.
    Return an empty string if fname is illegal or file not found.

    """
    parts = fname.split('/')
    path = directory
    for part in parts:
        if (part in ('', os.curdir, os.pardir) or
            os.sep in part or os.altsep is not None and os.altsep in part):
            return ""
        path = os.path.join(path, part)
    try:
        os.stat(path)
        ct = mimetypes.guess_type(path)[0] or "text/plain"
        return "Content-type: %s\n\n%s" % (ct, file(path).read())
    except (TypeError, OSError):
        # illegal fname or unreadable file
        return ""
