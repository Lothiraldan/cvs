#require test-repo

  $ cd "$TESTDIR"/..

  $ hg files 'set:(**.py)' | xargs python contrib/check-py3-compat.py
  contrib/casesmash.py not using absolute_import
  contrib/check-code.py not using absolute_import
  contrib/check-code.py requires print_function
  contrib/check-config.py not using absolute_import
  contrib/check-config.py requires print_function
  contrib/debugcmdserver.py not using absolute_import
  contrib/debugcmdserver.py requires print_function
  contrib/debugshell.py not using absolute_import
  contrib/fixpax.py not using absolute_import
  contrib/fixpax.py requires print_function
  contrib/hgclient.py not using absolute_import
  contrib/hgclient.py requires print_function
  contrib/hgfixes/__init__.py not using absolute_import
  contrib/hgfixes/fix_bytes.py not using absolute_import
  contrib/hgfixes/fix_bytesmod.py not using absolute_import
  contrib/hgfixes/fix_leftover_imports.py not using absolute_import
  contrib/import-checker.py not using absolute_import
  contrib/import-checker.py requires print_function
  contrib/memory.py not using absolute_import
  contrib/perf.py not using absolute_import
  contrib/python-hook-examples.py not using absolute_import
  contrib/revsetbenchmarks.py not using absolute_import
  contrib/revsetbenchmarks.py requires print_function
  contrib/showstack.py not using absolute_import
  contrib/synthrepo.py not using absolute_import
  contrib/win32/hgwebdir_wsgi.py not using absolute_import
  doc/check-seclevel.py not using absolute_import
  doc/gendoc.py not using absolute_import
  doc/hgmanpage.py not using absolute_import
  hgext/__init__.py not using absolute_import
  hgext/acl.py not using absolute_import
  hgext/blackbox.py not using absolute_import
  hgext/bugzilla.py not using absolute_import
  hgext/censor.py not using absolute_import
  hgext/children.py not using absolute_import
  hgext/churn.py not using absolute_import
  hgext/clonebundles.py not using absolute_import
  hgext/color.py not using absolute_import
  hgext/convert/__init__.py not using absolute_import
  hgext/convert/bzr.py not using absolute_import
  hgext/convert/common.py not using absolute_import
  hgext/convert/convcmd.py not using absolute_import
  hgext/convert/cvs.py not using absolute_import
  hgext/convert/cvsps.py not using absolute_import
  hgext/convert/darcs.py not using absolute_import
  hgext/convert/filemap.py not using absolute_import
  hgext/convert/git.py not using absolute_import
  hgext/convert/gnuarch.py not using absolute_import
  hgext/convert/hg.py not using absolute_import
  hgext/convert/monotone.py not using absolute_import
  hgext/convert/p4.py not using absolute_import
  hgext/convert/subversion.py not using absolute_import
  hgext/convert/transport.py not using absolute_import
  hgext/eol.py not using absolute_import
  hgext/extdiff.py not using absolute_import
  hgext/factotum.py not using absolute_import
  hgext/fetch.py not using absolute_import
  hgext/gpg.py not using absolute_import
  hgext/graphlog.py not using absolute_import
  hgext/hgcia.py not using absolute_import
  hgext/hgk.py not using absolute_import
  hgext/highlight/__init__.py not using absolute_import
  hgext/highlight/highlight.py not using absolute_import
  hgext/histedit.py not using absolute_import
  hgext/keyword.py not using absolute_import
  hgext/largefiles/__init__.py not using absolute_import
  hgext/largefiles/basestore.py not using absolute_import
  hgext/largefiles/lfcommands.py not using absolute_import
  hgext/largefiles/lfutil.py not using absolute_import
  hgext/largefiles/localstore.py not using absolute_import
  hgext/largefiles/overrides.py not using absolute_import
  hgext/largefiles/proto.py not using absolute_import
  hgext/largefiles/remotestore.py not using absolute_import
  hgext/largefiles/reposetup.py not using absolute_import
  hgext/largefiles/uisetup.py not using absolute_import
  hgext/largefiles/wirestore.py not using absolute_import
  hgext/mq.py not using absolute_import
  hgext/notify.py not using absolute_import
  hgext/pager.py not using absolute_import
  hgext/patchbomb.py not using absolute_import
  hgext/purge.py not using absolute_import
  hgext/rebase.py not using absolute_import
  hgext/record.py not using absolute_import
  hgext/relink.py not using absolute_import
  hgext/schemes.py not using absolute_import
  hgext/share.py not using absolute_import
  hgext/shelve.py not using absolute_import
  hgext/strip.py not using absolute_import
  hgext/transplant.py not using absolute_import
  hgext/win32mbcs.py not using absolute_import
  hgext/win32text.py not using absolute_import
  hgext/zeroconf/Zeroconf.py not using absolute_import
  hgext/zeroconf/Zeroconf.py requires print_function
  hgext/zeroconf/__init__.py not using absolute_import
  i18n/check-translation.py not using absolute_import
  i18n/polib.py not using absolute_import
  mercurial/byterange.py not using absolute_import
  mercurial/cmdutil.py not using absolute_import
  mercurial/commands.py not using absolute_import
  mercurial/commandserver.py not using absolute_import
  mercurial/context.py not using absolute_import
  mercurial/destutil.py not using absolute_import
  mercurial/dirstate.py not using absolute_import
  mercurial/dispatch.py requires print_function
  mercurial/encoding.py not using absolute_import
  mercurial/exchange.py not using absolute_import
  mercurial/help.py not using absolute_import
  mercurial/httpclient/__init__.py not using absolute_import
  mercurial/httpclient/_readers.py not using absolute_import
  mercurial/httpclient/socketutil.py not using absolute_import
  mercurial/httpconnection.py not using absolute_import
  mercurial/keepalive.py not using absolute_import
  mercurial/keepalive.py requires print_function
  mercurial/localrepo.py not using absolute_import
  mercurial/lsprof.py requires print_function
  mercurial/lsprofcalltree.py not using absolute_import
  mercurial/lsprofcalltree.py requires print_function
  mercurial/mail.py requires print_function
  mercurial/manifest.py not using absolute_import
  mercurial/mdiff.py not using absolute_import
  mercurial/obsolete.py not using absolute_import
  mercurial/patch.py not using absolute_import
  mercurial/pure/__init__.py not using absolute_import
  mercurial/pure/base85.py not using absolute_import
  mercurial/pure/bdiff.py not using absolute_import
  mercurial/pure/diffhelpers.py not using absolute_import
  mercurial/pure/mpatch.py not using absolute_import
  mercurial/pure/osutil.py not using absolute_import
  mercurial/pure/parsers.py not using absolute_import
  mercurial/pvec.py not using absolute_import
  mercurial/py3kcompat.py not using absolute_import
  mercurial/revlog.py not using absolute_import
  mercurial/scmposix.py not using absolute_import
  mercurial/scmutil.py not using absolute_import
  mercurial/scmwindows.py not using absolute_import
  mercurial/similar.py not using absolute_import
  mercurial/store.py not using absolute_import
  mercurial/util.py not using absolute_import
  mercurial/windows.py not using absolute_import
  setup.py not using absolute_import
  tests/fakepatchtime.py not using absolute_import
  tests/filterpyflakes.py not using absolute_import
  tests/filterpyflakes.py requires print_function
  tests/generate-working-copy-states.py not using absolute_import
  tests/generate-working-copy-states.py requires print_function
  tests/get-with-headers.py not using absolute_import
  tests/get-with-headers.py requires print_function
  tests/heredoctest.py not using absolute_import
  tests/heredoctest.py requires print_function
  tests/hghave.py not using absolute_import
  tests/hgweberror.py not using absolute_import
  tests/hypothesishelpers.py not using absolute_import
  tests/hypothesishelpers.py requires print_function
  tests/killdaemons.py not using absolute_import
  tests/md5sum.py not using absolute_import
  tests/mockblackbox.py not using absolute_import
  tests/printenv.py not using absolute_import
  tests/readlink.py not using absolute_import
  tests/readlink.py requires print_function
  tests/revlog-formatv0.py not using absolute_import
  tests/run-tests.py not using absolute_import
  tests/seq.py not using absolute_import
  tests/seq.py requires print_function
  tests/silenttestrunner.py not using absolute_import
  tests/silenttestrunner.py requires print_function
  tests/sitecustomize.py not using absolute_import
  tests/svn-safe-append.py not using absolute_import
  tests/svnxml.py not using absolute_import
  tests/test-ancestor.py requires print_function
  tests/test-atomictempfile.py not using absolute_import
  tests/test-batching.py not using absolute_import
  tests/test-batching.py requires print_function
  tests/test-bdiff.py not using absolute_import
  tests/test-bdiff.py requires print_function
  tests/test-context.py not using absolute_import
  tests/test-context.py requires print_function
  tests/test-demandimport.py not using absolute_import
  tests/test-demandimport.py requires print_function
  tests/test-dispatch.py not using absolute_import
  tests/test-dispatch.py requires print_function
  tests/test-doctest.py not using absolute_import
  tests/test-duplicateoptions.py not using absolute_import
  tests/test-duplicateoptions.py requires print_function
  tests/test-filecache.py not using absolute_import
  tests/test-filecache.py requires print_function
  tests/test-filelog.py not using absolute_import
  tests/test-filelog.py requires print_function
  tests/test-hg-parseurl.py not using absolute_import
  tests/test-hg-parseurl.py requires print_function
  tests/test-hgweb-auth.py not using absolute_import
  tests/test-hgweb-auth.py requires print_function
  tests/test-hgwebdir-paths.py not using absolute_import
  tests/test-hybridencode.py not using absolute_import
  tests/test-hybridencode.py requires print_function
  tests/test-lrucachedict.py not using absolute_import
  tests/test-lrucachedict.py requires print_function
  tests/test-manifest.py not using absolute_import
  tests/test-minirst.py not using absolute_import
  tests/test-minirst.py requires print_function
  tests/test-parseindex2.py not using absolute_import
  tests/test-parseindex2.py requires print_function
  tests/test-pathencode.py not using absolute_import
  tests/test-pathencode.py requires print_function
  tests/test-propertycache.py not using absolute_import
  tests/test-propertycache.py requires print_function
  tests/test-revlog-ancestry.py not using absolute_import
  tests/test-revlog-ancestry.py requires print_function
  tests/test-run-tests.py not using absolute_import
  tests/test-simplemerge.py not using absolute_import
  tests/test-status-inprocess.py not using absolute_import
  tests/test-status-inprocess.py requires print_function
  tests/test-symlink-os-yes-fs-no.py not using absolute_import
  tests/test-trusted.py not using absolute_import
  tests/test-trusted.py requires print_function
  tests/test-ui-color.py not using absolute_import
  tests/test-ui-color.py requires print_function
  tests/test-ui-config.py not using absolute_import
  tests/test-ui-config.py requires print_function
  tests/test-ui-verbosity.py not using absolute_import
  tests/test-ui-verbosity.py requires print_function
  tests/test-url.py not using absolute_import
  tests/test-url.py requires print_function
  tests/test-walkrepo.py not using absolute_import
  tests/test-walkrepo.py requires print_function
  tests/test-wireproto.py not using absolute_import
  tests/test-wireproto.py requires print_function
  tests/tinyproxy.py not using absolute_import
  tests/tinyproxy.py requires print_function
