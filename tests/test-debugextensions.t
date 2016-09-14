  $ hg debugextensions

  $ debugpath=`pwd`/extwithoutinfos.py

  $ cat > extwithoutinfos.py <<EOF
  > EOF
  $ cat > extwithinfos.py <<EOF
  > testedwith = '3.0 3.1 3.2.1'
  > buglink = 'https://example.org/bts'
  > EOF

  $ cat >> $HGRCPATH <<EOF
  > [extensions]
  > color=
  > histedit=
  > patchbomb=
  > rebase=
  > mq=
  > ext1 = $debugpath
  > ext2 = `pwd`/extwithinfos.py
  > EOF

  $ hg debugextensions
  color
  ext1 (untested!)
  ext2 (3.2.1!)
  histedit
  mq
  patchbomb
  rebase

  $ hg debugextensions -v
  color
    location: */hgext/color.py* (glob)
    bundled: yes
  ext1
    location: */extwithoutinfos.py* (glob)
    bundled: no
  ext2
    location: */extwithinfos.py* (glob)
    bundled: no
    tested with: 3.0 3.1 3.2.1
    bug reporting: https://example.org/bts
  histedit
    location: */hgext/histedit.py* (glob)
    bundled: yes
  mq
    location: */hgext/mq.py* (glob)
    bundled: yes
  patchbomb
    location: */hgext/patchbomb.py* (glob)
    bundled: yes
  rebase
    location: */hgext/rebase.py* (glob)
    bundled: yes

  $ hg debugextensions -Tjson | sed 's|\\\\|/|g'
  [
   {
    "buglink": "",
    "bundled": true,
    "name": "color",
    "source": "*/hgext/color.py*", (glob)
    "testedwith": []
   },
   {
    "buglink": "",
    "bundled": false,
    "name": "ext1",
    "source": "*/extwithoutinfos.py*", (glob)
    "testedwith": []
   },
   {
    "buglink": "https://example.org/bts",
    "bundled": false,
    "name": "ext2",
    "source": "*/extwithinfos.py*", (glob)
    "testedwith": ["3.0", "3.1", "3.2.1"]
   },
   {
    "buglink": "",
    "bundled": true,
    "name": "histedit",
    "source": "*/hgext/histedit.py*", (glob)
    "testedwith": []
   },
   {
    "buglink": "",
    "bundled": true,
    "name": "mq",
    "source": "*/hgext/mq.py*", (glob)
    "testedwith": []
   },
   {
    "buglink": "",
    "bundled": true,
    "name": "patchbomb",
    "source": "*/hgext/patchbomb.py*", (glob)
    "testedwith": []
   },
   {
    "buglink": "",
    "bundled": true,
    "name": "rebase",
    "source": "*/hgext/rebase.py*", (glob)
    "testedwith": []
   }
  ]

  $ hg debugextensions -T '{ifcontains("3.1", testedwith, "{name}\n")}'
  ext2
  $ hg debugextensions \
  > -T '{ifcontains("3.2", testedwith, "no substring match: {name}\n")}'
