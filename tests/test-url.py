#!/usr/bin/env python

def check(a, b):
    if a != b:
        print (a, b)

def cert(cn):
    return dict(subject=((('commonName', cn),),))

from mercurial.url import _verifycert

# Test non-wildcard certificates
check(_verifycert(cert('example.com'), 'example.com'),
      None)
check(_verifycert(cert('example.com'), 'www.example.com'),
      'certificate is for example.com')
check(_verifycert(cert('www.example.com'), 'example.com'),
      'certificate is for www.example.com')

# Test wildcard certificates
check(_verifycert(cert('*.example.com'), 'www.example.com'),
      None)
check(_verifycert(cert('*.example.com'), 'example.com'),
      'certificate is for *.example.com')
check(_verifycert(cert('*.example.com'), 'w.w.example.com'),
      'certificate is for *.example.com')

# Avoid some pitfalls
check(_verifycert(cert('*.foo'), 'foo'),
      'certificate is for *.foo')
check(_verifycert(cert('*o'), 'foo'),
      'certificate is for *o')

import time
lastyear = time.gmtime().tm_year - 1
nextyear = time.gmtime().tm_year + 1
check(_verifycert({'notAfter': 'May  9 00:00:00 %s GMT' % lastyear},
                  'example.com'),
      'certificate expired May  9 00:00:00 %s GMT' % lastyear)
check(_verifycert({'notBefore': 'May  9 00:00:00 %s GMT' % nextyear},
                  'example.com'),
      'certificate not valid before May  9 00:00:00 %s GMT' % nextyear)
check(_verifycert({'notAfter': 'Sep 29 15:29:48 %s GMT' % nextyear,
                   'subject': ()},
                  'example.com'),
      'no commonName found in certificate')
check(_verifycert(None, 'example.com'),
      'no certificate received')
