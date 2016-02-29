
  $ cat > engine.py << EOF
  > 
  > from mercurial import templater
  > 
  > class mytemplater(object):
  >     def __init__(self, loader, filters, defaults):
  >         self.loader = loader
  > 
  >     def process(self, t, map):
  >         tmpl = self.loader(t)
  >         for k, v in map.iteritems():
  >             if k in ('templ', 'ctx', 'repo', 'revcache', 'cache'):
  >                 continue
  >             if hasattr(v, '__call__'):
  >                 v = v(**map)
  >             v = templater.stringify(v)
  >             tmpl = tmpl.replace('{{%s}}' % k, v)
  >         yield tmpl
  > 
  > templater.engines['my'] = mytemplater
  > EOF
  $ hg init test
  $ echo '[extensions]' > test/.hg/hgrc
  $ echo "engine = `pwd`/engine.py" >> test/.hg/hgrc
  $ cd test
  $ cat > mymap << EOF
  > changeset = my:changeset.txt
  > EOF
  $ cat > changeset.txt << EOF
  > {{rev}} {{node}} {{author}}
  > EOF
  $ hg ci -Ama
  adding changeset.txt
  adding mymap
  $ hg log --style=./mymap
  0 97e5f848f0936960273bbf75be6388cd0350a32b test

  $ cat > changeset.txt << EOF
  > {{p1rev}} {{p1node}} {{p2rev}} {{p2node}}
  > EOF
  $ hg ci -Ama
  $ hg log --style=./mymap
  0 97e5f848f0936960273bbf75be6388cd0350a32b -1 0000000000000000000000000000000000000000
  -1 0000000000000000000000000000000000000000 -1 0000000000000000000000000000000000000000

Fuzzing the unicode escaper to ensure it produces valid data

#if hypothesis

  >>> from hypothesishelpers import *
  >>> import mercurial.templatefilters as tf
  >>> import json
  >>> @check(st.text().map(lambda s: s.encode('utf-8')))
  ... def testtfescapeproducesvalidjson(text):
  ...     json.loads('"' + tf.jsonescape(text) + '"')

#endif

  $ cd ..
