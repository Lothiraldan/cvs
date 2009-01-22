# help.py - help data for mercurial
#
# Copyright 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from i18n import _

helptable = (
    (["dates"], _("Date Formats"),
     _(r'''
    Some commands allow the user to specify a date:
    backout, commit, import, tag: Specify the commit date.
    log, revert, update: Select revision(s) by date.

    Many date formats are valid. Here are some examples:

    "Wed Dec 6 13:18:29 2006" (local timezone assumed)
    "Dec 6 13:18 -0600" (year assumed, time offset provided)
    "Dec 6 13:18 UTC" (UTC and GMT are aliases for +0000)
    "Dec 6" (midnight)
    "13:18" (today assumed)
    "3:39" (3:39AM assumed)
    "3:39pm" (15:39)
    "2006-12-06 13:18:29" (ISO 8601 format)
    "2006-12-6 13:18"
    "2006-12-6"
    "12-6"
    "12/6"
    "12/6/6" (Dec 6 2006)

    Lastly, there is Mercurial's internal format:

    "1165432709 0" (Wed Dec 6 13:18:29 2006 UTC)

    This is the internal representation format for dates. unixtime is
    the number of seconds since the epoch (1970-01-01 00:00 UTC). offset
    is the offset of the local timezone, in seconds west of UTC (negative
    if the timezone is east of UTC).

    The log command also accepts date ranges:

    "<{date}" - on or before a given date
    ">{date}" - on or after a given date
    "{date} to {date}" - a date range, inclusive
    "-{days}" - within a given number of days of today
    ''')),

    (["patterns"], _("File Name Patterns"),
     _(r'''
    Mercurial accepts several notations for identifying one or more
    files at a time.

    By default, Mercurial treats filenames as shell-style extended
    glob patterns.

    Alternate pattern notations must be specified explicitly.

    To use a plain path name without any pattern matching, start a
    name with "path:".  These path names must match completely, from
    the root of the current repository.

    To use an extended glob, start a name with "glob:".  Globs are
    rooted at the current directory; a glob such as "*.c" will match
    files ending in ".c" in the current directory only.

    The supported glob syntax extensions are "**" to match any string
    across path separators, and "{a,b}" to mean "a or b".

    To use a Perl/Python regular expression, start a name with "re:".
    Regexp pattern matching is anchored at the root of the repository.

    Plain examples:

    path:foo/bar   a name bar in a directory named foo in the root of
                   the repository
    path:path:name a file or directory named "path:name"

    Glob examples:

    glob:*.c       any name ending in ".c" in the current directory
    *.c            any name ending in ".c" in the current directory
    **.c           any name ending in ".c" in the current directory, or
                   any subdirectory
    foo/*.c        any name ending in ".c" in the directory foo
    foo/**.c       any name ending in ".c" in the directory foo, or any
                   subdirectory

    Regexp examples:

    re:.*\.c$      any name ending in ".c", anywhere in the repository

    ''')),

    (['environment', 'env'], _('Environment Variables'),
     _(r'''
HG::
    Path to the 'hg' executable, automatically passed when running hooks,
    extensions or external tools. If unset or empty, an executable named
    'hg' (with com/exe/bat/cmd extension on Windows) is searched.

HGEDITOR::
    This is the name of the editor to use when committing. See EDITOR.

    (deprecated, use .hgrc)

HGENCODING::
    This overrides the default locale setting detected by Mercurial.
    This setting is used to convert data including usernames,
    changeset descriptions, tag names, and branches. This setting can
    be overridden with the --encoding command-line option.

HGENCODINGMODE::
    This sets Mercurial's behavior for handling unknown characters
    while transcoding user inputs. The default is "strict", which
    causes Mercurial to abort if it can't translate a character. Other
    settings include "replace", which replaces unknown characters, and
    "ignore", which drops them. This setting can be overridden with
    the --encodingmode command-line option.

HGMERGE::
    An executable to use for resolving merge conflicts. The program
    will be executed with three arguments: local file, remote file,
    ancestor file.

    (deprecated, use .hgrc)

HGRCPATH::
    A list of files or directories to search for hgrc files.  Item
    separator is ":" on Unix, ";" on Windows.  If HGRCPATH is not set,
    platform default search path is used.  If empty, only .hg/hgrc of
    current repository is read.

    For each element in path, if a directory, all entries in directory
    ending with ".rc" are added to path.  Else, element itself is
    added to path.

HGUSER::
    This is the string used for the author of a commit.

    (deprecated, use .hgrc)

EMAIL::
    If HGUSER is not set, this will be used as the author for a commit.

LOGNAME::
    If neither HGUSER nor EMAIL is set, LOGNAME will be used (with
    '@hostname' appended) as the author value for a commit.

VISUAL::
    This is the name of the editor to use when committing. See EDITOR.

EDITOR::
    Sometimes Mercurial needs to open a text file in an editor
    for a user to modify, for example when writing commit messages.
    The editor it uses is determined by looking at the environment
    variables HGEDITOR, VISUAL and EDITOR, in that order. The first
    non-empty one is chosen. If all of them are empty, the editor
    defaults to 'vi'.

PYTHONPATH::
    This is used by Python to find imported modules and may need to be set
    appropriately if Mercurial is not installed system-wide.
    ''')),

    (['revs', 'revisions'], _('Specifying Single Revisions'),
     _(r'''
    Mercurial accepts several notations for identifying individual
    revisions.

    A plain integer is treated as a revision number. Negative
    integers are treated as offsets from the tip, with -1 denoting the
    tip.

    A 40-digit hexadecimal string is treated as a unique revision
    identifier.

    A hexadecimal string less than 40 characters long is treated as a
    unique revision identifier, and referred to as a short-form
    identifier. A short-form identifier is only valid if it is the
    prefix of one full-length identifier.

    Any other string is treated as a tag name, which is a symbolic
    name associated with a revision identifier. Tag names may not
    contain the ":" character.

    The reserved name "tip" is a special tag that always identifies
    the most recent revision.

    The reserved name "null" indicates the null revision. This is the
    revision of an empty repository, and the parent of revision 0.

    The reserved name "." indicates the working directory parent. If
    no working directory is checked out, it is equivalent to null.
    If an uncommitted merge is in progress, "." is the revision of
    the first parent.
    ''')),

    (['mrevs', 'multirevs'], _('Specifying Multiple Revisions'),
     _(r'''
    When Mercurial accepts more than one revision, they may be
    specified individually, or provided as a continuous range,
    separated by the ":" character.

    The syntax of range notation is [BEGIN]:[END], where BEGIN and END
    are revision identifiers. Both BEGIN and END are optional. If
    BEGIN is not specified, it defaults to revision number 0. If END
    is not specified, it defaults to the tip. The range ":" thus
    means "all revisions".

    If BEGIN is greater than END, revisions are treated in reverse
    order.

    A range acts as a closed interval. This means that a range of 3:5
    gives 3, 4 and 5. Similarly, a range of 4:2 gives 4, 3, and 2.
    ''')),

    (['diffs'], _('Diff Formats'),
     _(r'''
    Mercurial's default format for showing changes between two versions
    of a file is compatible with the unified format of GNU diff, which
    can be used by GNU patch and many other standard tools.

    While this standard format is often enough, it does not encode the
    following information:

     - executable status
     - copy or rename information
     - changes in binary files
     - creation or deletion of empty files

    Mercurial also supports the extended diff format from the git VCS
    which addresses these limitations. The git diff format is not
    produced by default because there are very few tools which
    understand this format.

    This means that when generating diffs from a Mercurial repository
    (e.g. with "hg export"), you should be careful about things like
    file copies and renames or other things mentioned above, because
    when applying a standard diff to a different repository, this extra
    information is lost. Mercurial's internal operations (like push and
    pull) are not affected by this, because they use an internal binary
    format for communicating changes.

    To make Mercurial produce the git extended diff format, use the
    --git option available for many commands, or set 'git = True' in the
    [diff] section of your hgrc. You do not need to set this option when
    importing diffs in this format or using them in the mq extension.
    ''')),
    (['templating'], _('Usage of templates'),
     _(r'''
    Mercurial allows you to customize output of commands through
    templates. There is command line option for that and additionally
    styles, which are simply precanned templates that someone wrote.

    You can customize output for any "log-like" command, which currently
    are: log, outgoing, incoming, tip, parents, heads and glog (if you have
    graphlog extension enabled).

    There is three styles packaged with Mercurial: default (which is
    naturally what you see by default), compact and changelog. Usage:

        > hg log -r1 --style changelog

    Template is a piece of text, where parts marked with special syntax
    are expanded, for example:

        > hg log -r1 --template "{node}\n"
        b56ce7b07c52de7d5fd79fb89701ea538af65746

    Strings in curly brackets are called keywords and that's their
    current list:

    - author: String. The unmodified author of the changeset.
    - branches: String. The name of the branch on which the changeset
          was committed. Will be empty if the branch name was default.
    - date: Date information. The date when the changeset was committed.
    - desc: String. The text of the changeset description.
    - files: List of strings. All files modified, added, or removed by
          this changeset.
    - file_adds: List of strings. Files added by this changeset.
    - file_dels: List of strings. Files removed by this changeset.
    - node: String. The changeset identification hash, as a 40-character
          hexadecimal string.
    - parents: List of strings. The parents of the changeset.
    - rev: Integer. The repository-local changeset revision number.
    - tags: List of strings. Any tags associated with the changeset.

    But "date" keyword does not produce human-readable output, what
    means that you should use a filter to process it. Filter is a
    function which modifies the result of expanding a keyword and
    Mercurial lets you specify a chain of filters:

       > hg tip --template "{date|isodate}\n"
       2008-08-21 18:22 +0000

    List of filters:

    - addbreaks: Any text. Add an XHTML "<br/>" tag before the end of
          every line except the last.
    - age: Date. Render the age of the date.
    - basename: Any text. Treat the text as a path, and return the
          basename. For example, "foo/bar/baz" becomes "baz".
    - date: Date. Render a date in a Unix date command format, but with
          timezone included: "Mon Sep 04 15:13:13 2006 0700".
    - domain: Any text. Finds the first string that looks like an email
          address, and extract just the domain component.
    - email: Any text. Extract the first string that looks like an email
          address.
    - escape: Any text. Replace the special XML/XHTML characters "&",
          "<" and ">" with XML entities.
    - fill68: Any text. Wrap the text to fit in 68 columns.
    - fill76: Any text. Wrap the text to fit in 76 columns.
    - firstline: Any text. Yield the first line of text.
    - hgdate: Date. Render the date as a pair of readable numbers:
          "1157407993 25200".
    - isodate: Date. Render the date in ISO 8601 format.
    - obfuscate: Any text. Yield the input text rendered as a sequence
          of XML entities.
    - person: Any text. Yield the text before an email address.
    - rfc822date: date keyword. Render a date using the same format used
          in email headers.
    - short: Changeset hash. Yield the short form of a changeset hash,
          i.e. a 12-byte hexadecimal string.
    - shortdate: Date. Render date like "2006-09-04".
    - strip: Any text. Strip all leading and trailing whitespace.
    - tabindent: Any text. Yield the text, with every line except the
          first starting with a tab character.
    - urlescape: Any text. Escape all "special" characters. For example,
          foo bar becomes foo%20bar.
    - user: Any text. Return the "user" portion of an email address.
    ''')),
)
