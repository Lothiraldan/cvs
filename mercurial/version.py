# Copyright (C) 2005 by Intevation GmbH
# Author(s):
# Thomas Arendsen Hein <thomas@intevation.de>
#
# This program is free software under the GNU GPL (>=v2)
# Read the file COPYING coming with the software for details.

"""
Mercurial version
"""

import os
import os.path
import re
import time
import util

unknown_version = 'unknown'
remembered_version = False

def get_version():
    """Return version information if available."""
    try:
        from mercurial.__version__ import version
    except ImportError:
        version = unknown_version
    return version

def write_version(version):
    """Overwrite version file."""
    filename = os.path.join(os.path.dirname(__file__), '__version__.py')
    f = open(filename, 'w')
    f.write("# This file is auto-generated.\n")
    f.write("version = %r\n" % version)
    f.close()

def remember_version(version=None):
    """Store version information."""
    global remembered_version
    if not version and os.path.isdir(".hg"):
        f = os.popen("hg identify 2> %s" % util.nulldev)  # use real hg installation
        ident = f.read()[:-1]
        if not f.close() and ident:
            ids = ident.split(' ', 1)
            version = ids.pop(0)
            if version[-1] == '+':
                version = version[:-1]
                modified = True
            else:
                modified = False
            if version.isalnum() and ids:
                for tag in ids[0].split('/'):
                    # is a tag is suitable as a version number?
                    if re.match(r'^(\d+\.)+[\w.-]+$', tag):
                        version = tag
                        break
            if modified:
                version += time.strftime('+%Y%m%d')
    if version:
        remembered_version = True
        write_version(version)

def forget_version():
    """Remove version information."""
    if remembered_version:
        write_version(unknown_version)

