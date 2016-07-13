#require serve ssl

Proper https client requires the built-in ssl from Python 2.6.

Make server certificates:

  $ CERTSDIR="$TESTDIR/sslcerts"
  $ cat "$CERTSDIR/priv.pem" "$CERTSDIR/pub.pem" >> server.pem
  $ PRIV=`pwd`/server.pem
  $ cat "$CERTSDIR/priv.pem" "$CERTSDIR/pub-not-yet.pem" > server-not-yet.pem
  $ cat "$CERTSDIR/priv.pem" "$CERTSDIR/pub-expired.pem" > server-expired.pem

  $ hg init test
  $ cd test
  $ echo foo>foo
  $ mkdir foo.d foo.d/bAr.hg.d foo.d/baR.d.hg
  $ echo foo>foo.d/foo
  $ echo bar>foo.d/bAr.hg.d/BaR
  $ echo bar>foo.d/baR.d.hg/bAR
  $ hg commit -A -m 1
  adding foo
  adding foo.d/bAr.hg.d/BaR
  adding foo.d/baR.d.hg/bAR
  adding foo.d/foo
  $ hg serve -p $HGPORT -d --pid-file=../hg0.pid --certificate=$PRIV
  $ cat ../hg0.pid >> $DAEMON_PIDS

cacert not found

  $ hg in --config web.cacerts=no-such.pem https://localhost:$HGPORT/
  abort: could not find web.cacerts: no-such.pem
  [255]

Test server address cannot be reused

#if windows
  $ hg serve -p $HGPORT --certificate=$PRIV 2>&1
  abort: cannot start server at ':$HGPORT':
  [255]
#else
  $ hg serve -p $HGPORT --certificate=$PRIV 2>&1
  abort: cannot start server at ':$HGPORT': Address already in use
  [255]
#endif
  $ cd ..

Our test cert is not signed by a trusted CA. It should fail to verify if
we are able to load CA certs.

#if sslcontext defaultcacerts no-defaultcacertsloaded
  $ hg clone https://localhost:$HGPORT/ copy-pull
  (an attempt was made to load CA certificates but none were loaded; see https://mercurial-scm.org/wiki/SecureConnections for how to configure Mercurial to avoid this error)
  abort: error: *certificate verify failed* (glob)
  [255]
#endif

#if no-sslcontext defaultcacerts
  $ hg clone https://localhost:$HGPORT/ copy-pull
  (using CA certificates from *; if you see this message, your Mercurial install is not properly configured; see https://mercurial-scm.org/wiki/SecureConnections for how to configure Mercurial to avoid this message) (glob) (?)
  abort: error: *certificate verify failed* (glob)
  [255]
#endif

#if no-sslcontext windows
  $ hg clone https://localhost:$HGPORT/ copy-pull
  (unable to load Windows CA certificates; see https://mercurial-scm.org/wiki/SecureConnections for how to configure Mercurial to avoid this message)
  abort: error: *certificate verify failed* (glob)
  [255]
#endif

#if no-sslcontext osx
  $ hg clone https://localhost:$HGPORT/ copy-pull
  (unable to load CA certificates; see https://mercurial-scm.org/wiki/SecureConnections for how to configure Mercurial to avoid this message)
  abort: localhost certificate error: no certificate received
  (set hostsecurity.localhost:certfingerprints=sha256:20:de:b3:ad:b4:cd:a5:42:f0:74:41:1c:a2:70:1e:da:6e:c0:5c:16:9e:e7:22:0f:f1:b7:e5:6e:e4:92:af:7e config setting or use --insecure to connect insecurely)
  [255]
#endif

#if defaultcacertsloaded
  $ hg clone https://localhost:$HGPORT/ copy-pull
  (using CA certificates from *; if you see this message, your Mercurial install is not properly configured; see https://mercurial-scm.org/wiki/SecureConnections for how to configure Mercurial to avoid this message) (glob) (?)
  abort: error: *certificate verify failed* (glob)
  [255]
#endif

#if no-defaultcacerts
  $ hg clone https://localhost:$HGPORT/ copy-pull
  (unable to load * certificates; see https://mercurial-scm.org/wiki/SecureConnections for how to configure Mercurial to avoid this message) (glob) (?)
  abort: localhost certificate error: no certificate received
  (set hostsecurity.localhost:certfingerprints=sha256:20:de:b3:ad:b4:cd:a5:42:f0:74:41:1c:a2:70:1e:da:6e:c0:5c:16:9e:e7:22:0f:f1:b7:e5:6e:e4:92:af:7e config setting or use --insecure to connect insecurely)
  [255]
#endif

Specifying a per-host certificate file that doesn't exist will abort

  $ hg --config hostsecurity.localhost:verifycertsfile=/does/not/exist clone https://localhost:$HGPORT/
  abort: path specified by hostsecurity.localhost:verifycertsfile does not exist: /does/not/exist
  [255]

A malformed per-host certificate file will raise an error

  $ echo baddata > badca.pem
#if sslcontext
  $ hg --config hostsecurity.localhost:verifycertsfile=badca.pem clone https://localhost:$HGPORT/
  abort: error loading CA file badca.pem: * (glob)
  (file is empty or malformed?)
  [255]
#else
  $ hg --config hostsecurity.localhost:verifycertsfile=badca.pem clone https://localhost:$HGPORT/
  abort: error: * (glob)
  [255]
#endif

A per-host certificate mismatching the server will fail verification

(modern ssl is able to discern whether the loaded cert is a CA cert)
#if sslcontext
  $ hg --config hostsecurity.localhost:verifycertsfile="$CERTSDIR/client-cert.pem" clone https://localhost:$HGPORT/
  (an attempt was made to load CA certificates but none were loaded; see https://mercurial-scm.org/wiki/SecureConnections for how to configure Mercurial to avoid this error)
  abort: error: *certificate verify failed* (glob)
  [255]
#else
  $ hg --config hostsecurity.localhost:verifycertsfile="$CERTSDIR/client-cert.pem" clone https://localhost:$HGPORT/
  abort: error: *certificate verify failed* (glob)
  [255]
#endif

A per-host certificate matching the server's cert will be accepted

  $ hg --config hostsecurity.localhost:verifycertsfile="$CERTSDIR/pub.pem" clone -U https://localhost:$HGPORT/ perhostgood1
  requesting all changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 4 changes to 4 files

A per-host certificate with multiple certs and one matching will be accepted

  $ cat "$CERTSDIR/client-cert.pem" "$CERTSDIR/pub.pem" > perhost.pem
  $ hg --config hostsecurity.localhost:verifycertsfile=perhost.pem clone -U https://localhost:$HGPORT/ perhostgood2
  requesting all changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 4 changes to 4 files

Defining both per-host certificate and a fingerprint will print a warning

  $ hg --config hostsecurity.localhost:verifycertsfile="$CERTSDIR/pub.pem" --config hostsecurity.localhost:fingerprints=sha1:ecd87cd6b386d04fc1b8b41c9d8f5e168eef1c03 clone -U https://localhost:$HGPORT/ caandfingerwarning
  (hostsecurity.localhost:verifycertsfile ignored when host fingerprints defined; using host fingerprints for verification)
  requesting all changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 4 changes to 4 files

  $ DISABLECACERTS="--config devel.disableloaddefaultcerts=true"

Inability to verify peer certificate will result in abort

  $ hg clone https://localhost:$HGPORT/ copy-pull $DISABLECACERTS
  abort: unable to verify security of localhost (no loaded CA certificates); refusing to connect
  (see https://mercurial-scm.org/wiki/SecureConnections for how to configure Mercurial to avoid this error or set hostsecurity.localhost:fingerprints=sha256:20:de:b3:ad:b4:cd:a5:42:f0:74:41:1c:a2:70:1e:da:6e:c0:5c:16:9e:e7:22:0f:f1:b7:e5:6e:e4:92:af:7e to trust this server)
  [255]

  $ hg clone --insecure https://localhost:$HGPORT/ copy-pull
  warning: connection security to localhost is disabled per current settings; communication is susceptible to eavesdropping and tampering
  requesting all changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 4 changes to 4 files
  updating to branch default
  4 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg verify -R copy-pull
  checking changesets
  checking manifests
  crosschecking files in changesets and manifests
  checking files
  4 files, 1 changesets, 4 total revisions
  $ cd test
  $ echo bar > bar
  $ hg commit -A -d '1 0' -m 2
  adding bar
  $ cd ..

pull without cacert

  $ cd copy-pull
  $ echo '[hooks]' >> .hg/hgrc
  $ echo "changegroup = printenv.py changegroup" >> .hg/hgrc
  $ hg pull $DISABLECACERTS
  pulling from https://localhost:$HGPORT/
  abort: unable to verify security of localhost (no loaded CA certificates); refusing to connect
  (see https://mercurial-scm.org/wiki/SecureConnections for how to configure Mercurial to avoid this error or set hostsecurity.localhost:fingerprints=sha256:20:de:b3:ad:b4:cd:a5:42:f0:74:41:1c:a2:70:1e:da:6e:c0:5c:16:9e:e7:22:0f:f1:b7:e5:6e:e4:92:af:7e to trust this server)
  [255]

  $ hg pull --insecure
  pulling from https://localhost:$HGPORT/
  warning: connection security to localhost is disabled per current settings; communication is susceptible to eavesdropping and tampering
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files
  changegroup hook: HG_NODE=5fed3813f7f5e1824344fdc9cf8f63bb662c292d HG_NODE_LAST=5fed3813f7f5e1824344fdc9cf8f63bb662c292d HG_SOURCE=pull HG_TXNID=TXN:* HG_URL=https://localhost:$HGPORT/ (glob)
  (run 'hg update' to get a working copy)
  $ cd ..

cacert configured in local repo

  $ cp copy-pull/.hg/hgrc copy-pull/.hg/hgrc.bu
  $ echo "[web]" >> copy-pull/.hg/hgrc
  $ echo "cacerts=$CERTSDIR/pub.pem" >> copy-pull/.hg/hgrc
  $ hg -R copy-pull pull --traceback
  pulling from https://localhost:$HGPORT/
  searching for changes
  no changes found
  $ mv copy-pull/.hg/hgrc.bu copy-pull/.hg/hgrc

cacert configured globally, also testing expansion of environment
variables in the filename

  $ echo "[web]" >> $HGRCPATH
  $ echo 'cacerts=$P/pub.pem' >> $HGRCPATH
  $ P="$CERTSDIR" hg -R copy-pull pull
  pulling from https://localhost:$HGPORT/
  searching for changes
  no changes found
  $ P="$CERTSDIR" hg -R copy-pull pull --insecure
  pulling from https://localhost:$HGPORT/
  warning: connection security to localhost is disabled per current settings; communication is susceptible to eavesdropping and tampering
  searching for changes
  no changes found

empty cacert file

  $ touch emptycafile

#if sslcontext
  $ hg --config web.cacerts=emptycafile -R copy-pull pull
  pulling from https://localhost:$HGPORT/
  abort: error loading CA file emptycafile: * (glob)
  (file is empty or malformed?)
  [255]
#else
  $ hg --config web.cacerts=emptycafile -R copy-pull pull
  pulling from https://localhost:$HGPORT/
  abort: error: * (glob)
  [255]
#endif

cacert mismatch

  $ hg -R copy-pull pull --config web.cacerts="$CERTSDIR/pub.pem" \
  > https://127.0.0.1:$HGPORT/
  pulling from https://127.0.0.1:$HGPORT/ (glob)
  abort: 127.0.0.1 certificate error: certificate is for localhost (glob)
  (set hostsecurity.127.0.0.1:certfingerprints=sha256:20:de:b3:ad:b4:cd:a5:42:f0:74:41:1c:a2:70:1e:da:6e:c0:5c:16:9e:e7:22:0f:f1:b7:e5:6e:e4:92:af:7e config setting or use --insecure to connect insecurely) (glob)
  [255]
  $ hg -R copy-pull pull --config web.cacerts="$CERTSDIR/pub.pem" \
  > https://127.0.0.1:$HGPORT/ --insecure
  pulling from https://127.0.0.1:$HGPORT/ (glob)
  warning: connection security to 127.0.0.1 is disabled per current settings; communication is susceptible to eavesdropping and tampering (glob)
  searching for changes
  no changes found
  $ hg -R copy-pull pull --config web.cacerts="$CERTSDIR/pub-other.pem"
  pulling from https://localhost:$HGPORT/
  abort: error: *certificate verify failed* (glob)
  [255]
  $ hg -R copy-pull pull --config web.cacerts="$CERTSDIR/pub-other.pem" \
  > --insecure
  pulling from https://localhost:$HGPORT/
  warning: connection security to localhost is disabled per current settings; communication is susceptible to eavesdropping and tampering
  searching for changes
  no changes found

Test server cert which isn't valid yet

  $ hg serve -R test -p $HGPORT1 -d --pid-file=hg1.pid --certificate=server-not-yet.pem
  $ cat hg1.pid >> $DAEMON_PIDS
  $ hg -R copy-pull pull --config web.cacerts="$CERTSDIR/pub-not-yet.pem" \
  > https://localhost:$HGPORT1/
  pulling from https://localhost:$HGPORT1/
  abort: error: *certificate verify failed* (glob)
  [255]

Test server cert which no longer is valid

  $ hg serve -R test -p $HGPORT2 -d --pid-file=hg2.pid --certificate=server-expired.pem
  $ cat hg2.pid >> $DAEMON_PIDS
  $ hg -R copy-pull pull --config web.cacerts="$CERTSDIR/pub-expired.pem" \
  > https://localhost:$HGPORT2/
  pulling from https://localhost:$HGPORT2/
  abort: error: *certificate verify failed* (glob)
  [255]

Fingerprints

- works without cacerts (hostkeyfingerprints)
  $ hg -R copy-pull id https://localhost:$HGPORT/ --insecure --config hostfingerprints.localhost=ec:d8:7c:d6:b3:86:d0:4f:c1:b8:b4:1c:9d:8f:5e:16:8e:ef:1c:03
  5fed3813f7f5

- works without cacerts (hostsecurity)
  $ hg -R copy-pull id https://localhost:$HGPORT/ --config hostsecurity.localhost:fingerprints=sha1:ecd87cd6b386d04fc1b8b41c9d8f5e168eef1c03
  5fed3813f7f5

  $ hg -R copy-pull id https://localhost:$HGPORT/ --config hostsecurity.localhost:fingerprints=sha256:20:de:b3:ad:b4:cd:a5:42:f0:74:41:1c:a2:70:1e:da:6e:c0:5c:16:9e:e7:22:0f:f1:b7:e5:6e:e4:92:af:7e
  5fed3813f7f5

- multiple fingerprints specified and first matches
  $ hg --config 'hostfingerprints.localhost=ecd87cd6b386d04fc1b8b41c9d8f5e168eef1c03, deadbeefdeadbeefdeadbeefdeadbeefdeadbeef' -R copy-pull id https://localhost:$HGPORT/ --insecure
  5fed3813f7f5

  $ hg --config 'hostsecurity.localhost:fingerprints=sha1:ecd87cd6b386d04fc1b8b41c9d8f5e168eef1c03, sha1:deadbeefdeadbeefdeadbeefdeadbeefdeadbeef' -R copy-pull id https://localhost:$HGPORT/
  5fed3813f7f5

- multiple fingerprints specified and last matches
  $ hg --config 'hostfingerprints.localhost=deadbeefdeadbeefdeadbeefdeadbeefdeadbeef, ecd87cd6b386d04fc1b8b41c9d8f5e168eef1c03' -R copy-pull id https://localhost:$HGPORT/ --insecure
  5fed3813f7f5

  $ hg --config 'hostsecurity.localhost:fingerprints=sha1:deadbeefdeadbeefdeadbeefdeadbeefdeadbeef, sha1:ecd87cd6b386d04fc1b8b41c9d8f5e168eef1c03' -R copy-pull id https://localhost:$HGPORT/
  5fed3813f7f5

- multiple fingerprints specified and none match

  $ hg --config 'hostfingerprints.localhost=deadbeefdeadbeefdeadbeefdeadbeefdeadbeef, aeadbeefdeadbeefdeadbeefdeadbeefdeadbeef' -R copy-pull id https://localhost:$HGPORT/ --insecure
  abort: certificate for localhost has unexpected fingerprint ec:d8:7c:d6:b3:86:d0:4f:c1:b8:b4:1c:9d:8f:5e:16:8e:ef:1c:03
  (check hostfingerprint configuration)
  [255]

  $ hg --config 'hostsecurity.localhost:fingerprints=sha1:deadbeefdeadbeefdeadbeefdeadbeefdeadbeef, sha1:aeadbeefdeadbeefdeadbeefdeadbeefdeadbeef' -R copy-pull id https://localhost:$HGPORT/
  abort: certificate for localhost has unexpected fingerprint sha1:ec:d8:7c:d6:b3:86:d0:4f:c1:b8:b4:1c:9d:8f:5e:16:8e:ef:1c:03
  (check hostsecurity configuration)
  [255]

- fails when cert doesn't match hostname (port is ignored)
  $ hg -R copy-pull id https://localhost:$HGPORT1/ --config hostfingerprints.localhost=ecd87cd6b386d04fc1b8b41c9d8f5e168eef1c03
  abort: certificate for localhost has unexpected fingerprint f4:2f:5a:0c:3e:52:5b:db:e7:24:a8:32:1d:18:97:6d:69:b5:87:84
  (check hostfingerprint configuration)
  [255]


- ignores that certificate doesn't match hostname
  $ hg -R copy-pull id https://127.0.0.1:$HGPORT/ --config hostfingerprints.127.0.0.1=ecd87cd6b386d04fc1b8b41c9d8f5e168eef1c03
  5fed3813f7f5

HGPORT1 is reused below for tinyproxy tests. Kill that server.
  $ killdaemons.py hg1.pid

Prepare for connecting through proxy

  $ tinyproxy.py $HGPORT1 localhost >proxy.log </dev/null 2>&1 &
  $ while [ ! -f proxy.pid ]; do sleep 0; done
  $ cat proxy.pid >> $DAEMON_PIDS

  $ echo "[http_proxy]" >> copy-pull/.hg/hgrc
  $ echo "always=True" >> copy-pull/.hg/hgrc
  $ echo "[hostfingerprints]" >> copy-pull/.hg/hgrc
  $ echo "localhost =" >> copy-pull/.hg/hgrc

Test unvalidated https through proxy

  $ http_proxy=http://localhost:$HGPORT1/ hg -R copy-pull pull --insecure --traceback
  pulling from https://localhost:$HGPORT/
  warning: connection security to localhost is disabled per current settings; communication is susceptible to eavesdropping and tampering
  searching for changes
  no changes found

Test https with cacert and fingerprint through proxy

  $ http_proxy=http://localhost:$HGPORT1/ hg -R copy-pull pull \
  > --config web.cacerts="$CERTSDIR/pub.pem"
  pulling from https://localhost:$HGPORT/
  searching for changes
  no changes found
  $ http_proxy=http://localhost:$HGPORT1/ hg -R copy-pull pull https://127.0.0.1:$HGPORT/ --config hostfingerprints.127.0.0.1=ecd87cd6b386d04fc1b8b41c9d8f5e168eef1c03
  pulling from https://127.0.0.1:$HGPORT/ (glob)
  searching for changes
  no changes found

Test https with cert problems through proxy

  $ http_proxy=http://localhost:$HGPORT1/ hg -R copy-pull pull \
  > --config web.cacerts="$CERTSDIR/pub-other.pem"
  pulling from https://localhost:$HGPORT/
  abort: error: *certificate verify failed* (glob)
  [255]
  $ http_proxy=http://localhost:$HGPORT1/ hg -R copy-pull pull \
  > --config web.cacerts="$CERTSDIR/pub-expired.pem" https://localhost:$HGPORT2/
  pulling from https://localhost:$HGPORT2/
  abort: error: *certificate verify failed* (glob)
  [255]


  $ killdaemons.py hg0.pid

#if sslcontext

Start patched hgweb that requires client certificates:

  $ cat << EOT > reqclientcert.py
  > import ssl
  > from mercurial.hgweb import server
  > class _httprequesthandlersslclientcert(server._httprequesthandlerssl):
  >     @staticmethod
  >     def preparehttpserver(httpserver, ssl_cert):
  >         sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
  >         sslcontext.verify_mode = ssl.CERT_REQUIRED
  >         sslcontext.load_cert_chain(ssl_cert)
  >         # verify clients by server certificate
  >         sslcontext.load_verify_locations(ssl_cert)
  >         httpserver.socket = sslcontext.wrap_socket(httpserver.socket,
  >                                                    server_side=True)
  > server._httprequesthandlerssl = _httprequesthandlersslclientcert
  > EOT
  $ cd test
  $ hg serve -p $HGPORT -d --pid-file=../hg0.pid --certificate=$PRIV \
  > --config extensions.reqclientcert=../reqclientcert.py
  $ cat ../hg0.pid >> $DAEMON_PIDS
  $ cd ..

without client certificate:

  $ P="$CERTSDIR" hg id https://localhost:$HGPORT/
  abort: error: *handshake failure* (glob)
  [255]

with client certificate:

  $ cat << EOT >> $HGRCPATH
  > [auth]
  > l.prefix = localhost
  > l.cert = $CERTSDIR/client-cert.pem
  > l.key = $CERTSDIR/client-key.pem
  > EOT

  $ P="$CERTSDIR" hg id https://localhost:$HGPORT/ \
  > --config auth.l.key="$CERTSDIR/client-key-decrypted.pem"
  5fed3813f7f5

  $ printf '1234\n' | env P="$CERTSDIR" hg id https://localhost:$HGPORT/ \
  > --config ui.interactive=True --config ui.nontty=True
  passphrase for */client-key.pem: 5fed3813f7f5 (glob)

  $ env P="$CERTSDIR" hg id https://localhost:$HGPORT/
  abort: error: * (glob)
  [255]

#endif
