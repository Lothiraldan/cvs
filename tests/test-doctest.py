# this is hack to make sure no escape characters are inserted into the output
import os; del os.environ['TERM'] 
import doctest

import mercurial.changelog
# test doctest from changelog

doctest.testmod(mercurial.changelog)

import mercurial.httprepo
doctest.testmod(mercurial.httprepo)

import mercurial.util
doctest.testmod(mercurial.util)
