# color.py color output for the status and qseries commands
#
# Copyright (C) 2007 Kevin Christen <kevin.christen@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

'''colorize output from some commands

This extension modifies the status and resolve commands to add color to their
output to reflect file status, the qseries command to add color to reflect
patch status (applied, unapplied, missing), and to diff-related
commands to highlight additions, removals, diff headers, and trailing
whitespace.

Other effects in addition to color, like bold and underlined text, are
also available. Effects are rendered with the ECMA-48 SGR control
function (aka ANSI escape codes). This module also provides the
render_text function, which can be used to add effects to any text.

Default effects may be overridden from the .hgrc file::

  [color]
  status.modified = blue bold underline red_background
  status.added = green bold
  status.removed = red bold blue_background
  status.deleted = cyan bold underline
  status.unknown = magenta bold underline
  status.ignored = black bold

  # 'none' turns off all effects
  status.clean = none
  status.copied = none

  qseries.applied = blue bold underline
  qseries.unapplied = black bold
  qseries.missing = red bold

  diff.diffline = bold
  diff.extended = cyan bold
  diff.file_a = red bold
  diff.file_b = green bold
  diff.hunk = magenta
  diff.deleted = red
  diff.inserted = green
  diff.changed = white
  diff.trailingwhitespace = bold red_background

  resolve.unresolved = red bold
  resolve.resolved = green bold

  bookmarks.current = green

The color extension will try to detect whether to use ANSI codes or
Win32 console APIs, unless it is made explicit::

  [color]
  mode = ansi

Any value other than 'ansi', 'win32', or 'auto' will disable color.

'''

import os, sys

from mercurial import commands, dispatch, extensions
from mercurial.i18n import _

# start and stop parameters for effects
_effects = {'none': 0, 'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
            'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37, 'bold': 1,
            'italic': 3, 'underline': 4, 'inverse': 7,
            'black_background': 40, 'red_background': 41,
            'green_background': 42, 'yellow_background': 43,
            'blue_background': 44, 'purple_background': 45,
            'cyan_background': 46, 'white_background': 47}

_styles = {'grep.match': 'red bold',
           'diff.changed': 'white',
           'diff.deleted': 'red',
           'diff.diffline': 'bold',
           'diff.extended': 'cyan bold',
           'diff.file_a': 'red bold',
           'diff.file_b': 'green bold',
           'diff.hunk': 'magenta',
           'diff.inserted': 'green',
           'diff.trailingwhitespace': 'bold red_background',
           'diffstat.deleted': 'red',
           'diffstat.inserted': 'green',
           'log.changeset': 'yellow',
           'resolve.resolved': 'green bold',
           'resolve.unresolved': 'red bold',
           'status.added': 'green bold',
           'status.clean': 'none',
           'status.copied': 'none',
           'status.deleted': 'cyan bold underline',
           'status.ignored': 'black bold',
           'status.modified': 'blue bold',
           'status.removed': 'red bold',
           'status.unknown': 'magenta bold underline'}


def render_effects(text, effects):
    'Wrap text in commands to turn on each effect.'
    if not text:
        return text
    start = [str(_effects[e]) for e in ['none'] + effects.split()]
    start = '\033[' + ';'.join(start) + 'm'
    stop = '\033[' + str(_effects['none']) + 'm'
    return ''.join([start, text, stop])

def extstyles():
    for name, ext in extensions.extensions():
        _styles.update(getattr(ext, 'colortable', {}))

def configstyles(ui):
    for status, cfgeffects in ui.configitems('color'):
        if '.' not in status:
            continue
        cfgeffects = ui.configlist('color', status)
        if cfgeffects:
            good = []
            for e in cfgeffects:
                if e in _effects:
                    good.append(e)
                else:
                    ui.warn(_("ignoring unknown color/effect %r "
                              "(configured in color.%s)\n")
                            % (e, status))
            _styles[status] = ' '.join(good)

_buffers = None
def style(msg, label):
    effects = []
    for l in label.split():
        s = _styles.get(l, '')
        if s:
            effects.append(s)
    effects = ''.join(effects)
    if effects:
        return '\n'.join([render_effects(s, effects)
                          for s in msg.split('\n')])
    return msg

def popbuffer(orig, labeled=False):
    global _buffers
    if labeled:
        return ''.join(style(a, label) for a, label in _buffers.pop())
    return ''.join(a for a, label in _buffers.pop())

mode = 'ansi'
def write(orig, *args, **opts):
    label = opts.get('label', '')
    global _buffers
    if _buffers:
        _buffers[-1].extend([(str(a), label) for a in args])
    elif mode == 'win32':
        for a in args:
            win32print(a, orig, **opts)
    else:
        return orig(*[style(str(a), label) for a in args], **opts)

def write_err(orig, *args, **opts):
    label = opts.get('label', '')
    if mode == 'win32':
        for a in args:
            win32print(a, orig, **opts)
    else:
        return orig(*[style(str(a), label) for a in args], **opts)

def uisetup(ui):
    if ui.plain():
        return
    global mode
    mode = ui.config('color', 'mode', 'auto')
    if mode == 'auto':
        if os.name == 'nt' and 'TERM' not in os.environ:
            # looks line a cmd.exe console, use win32 API or nothing
            mode = w32effects and 'win32' or 'none'
        else:
            mode = 'ansi'
    if mode == 'win32':
        if w32effects is None:
            # only warn if color.mode is explicitly set to win32
            ui.warn(_('win32console not found, please install pywin32\n'))
            return
        _effects.update(w32effects)
    elif mode != 'ansi':
        return

    # check isatty() before anything else changes it (like pager)
    isatty = sys.__stdout__.isatty()

    def colorcmd(orig, ui_, opts, cmd, cmdfunc):
        if (opts['color'] == 'always' or
            (opts['color'] == 'auto' and (os.environ.get('TERM') != 'dumb'
                                          and isatty))):
            global _buffers
            _buffers = ui_._buffers
            extensions.wrapfunction(ui_, 'popbuffer', popbuffer)
            extensions.wrapfunction(ui_, 'write', write)
            extensions.wrapfunction(ui_, 'write_err', write_err)
            ui_.label = style
            extstyles()
            configstyles(ui)
        return orig(ui_, opts, cmd, cmdfunc)
    extensions.wrapfunction(dispatch, '_runcommand', colorcmd)

commands.globalopts.append(('', 'color', 'auto',
                            _("when to colorize (always, auto, or never)")))

try:
    import re, pywintypes
    from win32console import *

    # http://msdn.microsoft.com/en-us/library/ms682088%28VS.85%29.aspx
    w32effects = {
        'none': 0,
        'black': 0,
        'red': FOREGROUND_RED,
        'green': FOREGROUND_GREEN,
        'yellow': FOREGROUND_RED | FOREGROUND_GREEN,
        'blue': FOREGROUND_BLUE,
        'magenta': FOREGROUND_BLUE | FOREGROUND_RED,
        'cyan': FOREGROUND_BLUE | FOREGROUND_GREEN,
        'white': FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE,
        'bold': FOREGROUND_INTENSITY,
        'black_background': 0,
        'red_background': BACKGROUND_RED,
        'green_background': BACKGROUND_GREEN,
        'yellow_background': BACKGROUND_RED | BACKGROUND_GREEN,
        'blue_background': BACKGROUND_BLUE,
        'purple_background': BACKGROUND_BLUE | BACKGROUND_RED,
        'cyan_background': BACKGROUND_BLUE | BACKGROUND_GREEN,
        'white_background': BACKGROUND_RED | BACKGROUND_GREEN | BACKGROUND_BLUE,
        'bold_background': BACKGROUND_INTENSITY,
        'underline': COMMON_LVB_UNDERSCORE,     # double-byte charsets only
        'inverse': COMMON_LVB_REVERSE_VIDEO,    # double-byte charsets only
    }

    stdout = GetStdHandle(STD_OUTPUT_HANDLE)
    try:
        origattr = stdout.GetConsoleScreenBufferInfo()['Attributes']
    except pywintypes.error:
        # stdout may be defined but not support
        # GetConsoleScreenBufferInfo(), when called from subprocess or
        # redirected.
        raise ImportError()
    ansire = re.compile('\033\[([^m]*)m([^\033]*)(.*)', re.MULTILINE | re.DOTALL)

    def win32print(text, orig, **opts):
        label = opts.get('label', '')
        attr = 0

        # determine console attributes based on labels
        for l in label.split():
            style = _styles.get(l, '')
            for effect in style.split():
                attr |= w32effects[effect]

        # hack to ensure regexp finds data
        if not text.startswith('\033['):
            text = '\033[m' + text

        # Look for ANSI-like codes embedded in text
        m = re.match(ansire, text)
        while m:
            for sattr in m.group(1).split(';'):
                if sattr:
                    val = int(sattr)
                    attr = val and attr|val or 0
            stdout.SetConsoleTextAttribute(attr or origattr)
            orig(m.group(2), **opts)
            m = re.match(ansire, m.group(3))

        # Explicity reset original attributes
        stdout.SetConsoleTextAttribute(origattr)

except ImportError:
    w32effects = None
