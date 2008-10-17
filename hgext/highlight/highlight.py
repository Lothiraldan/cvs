# highlight extension implementation file
#
# The original module was split in an interface and an implementation
# file to defer pygments loading and speedup extension setup.

from mercurial import demandimport
demandimport.ignore.extend(['pkgutil', 'pkg_resources', '__main__',])

from mercurial import util
from mercurial.templatefilters import filters

from pygments import highlight
from pygments.util import ClassNotFound
from pygments.lexers import guess_lexer, guess_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter

SYNTAX_CSS = ('\n<link rel="stylesheet" href="{url}highlightcss" '
              'type="text/css" />')

def pygmentize(field, fctx, style, tmpl):

    # append a <link ...> to the syntax highlighting css
    old_header = ''.join(tmpl('header'))
    if SYNTAX_CSS not in old_header:
        new_header =  old_header + SYNTAX_CSS
        tmpl.cache['header'] = new_header

    text = fctx.data()
    if util.binary(text):
        return

    # avoid UnicodeDecodeError in pygments
    text = util.tolocal(text)

    # To get multi-line strings right, we can't format line-by-line
    try:
        lexer = guess_lexer_for_filename(fctx.path(), text[:1024],
                                         encoding=util._encoding)
    except (ClassNotFound, ValueError):
        try:
            lexer = guess_lexer(text[:1024], encoding=util._encoding)
        except (ClassNotFound, ValueError):
            lexer = TextLexer(encoding=util._encoding)

    formatter = HtmlFormatter(style=style, encoding=util._encoding)

    colorized = highlight(text, lexer, formatter)
    # strip wrapping div
    colorized = colorized[:colorized.find('\n</pre>')]
    colorized = colorized[colorized.find('<pre>')+5:]
    coloriter = iter(colorized.splitlines())

    filters['colorize'] = lambda x: coloriter.next()

    oldl = tmpl.cache[field]
    newl = oldl.replace('line|escape', 'line|colorize')
    tmpl.cache[field] = newl
