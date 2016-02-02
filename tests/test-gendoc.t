#require docutils
#require gettext

Test document extraction

  $ HGENCODING=UTF-8
  $ export HGENCODING
  $ { echo C; ls "$TESTDIR/../i18n"/*.po | sort; } | while read PO; do
  >     LOCALE=`basename "$PO" .po`
  >     echo
  >     echo "% extracting documentation from $LOCALE"
  >     echo ".. -*- coding: utf-8 -*-" > gendoc-$LOCALE.txt
  >     echo "" >> gendoc-$LOCALE.txt
  >     LANGUAGE=$LOCALE python "$TESTDIR/../doc/gendoc.py" >> gendoc-$LOCALE.txt 2> /dev/null || exit
  > 
  >     if [ $LOCALE != C ]; then
  >         cmp -s gendoc-C.txt gendoc-$LOCALE.txt && echo '** NOTHING TRANSLATED **'
  >     fi
  > 
  >     echo "checking for parse errors"
  >     python "$TESTDIR/../doc/docchecker" gendoc-$LOCALE.txt
  >     # We call runrst without adding "--halt warning" to make it report
  >     # all errors instead of stopping on the first one.
  >     python "$TESTDIR/../doc/runrst" html gendoc-$LOCALE.txt /dev/null
  > done
  
  % extracting documentation from C
  checking for parse errors
  
  % extracting documentation from da
  checking for parse errors
  
  % extracting documentation from de
  checking for parse errors
  Die Dateien werden dem Projektarchiv beim n\xc3\xa4chsten \xc3\x9cbernehmen (commit) hinzugef\xc3\xbcgt. Um dies vorher r\xc3\xbcckg\xc3\xa4ngig zu machen, siehe:hg:`forget`. (esc)
  warning: please have a space before :hg:
  
  % extracting documentation from el
  checking for parse errors
  
  % extracting documentation from fr
  checking for parse errors
  
  % extracting documentation from it
  checking for parse errors
  
  % extracting documentation from ja
  checking for parse errors
  
  % extracting documentation from pt_BR
  checking for parse errors
  
  % extracting documentation from ro
  checking for parse errors
  
  % extracting documentation from ru
  checking for parse errors
  
  % extracting documentation from sv
  checking for parse errors
  
  % extracting documentation from zh_CN
  checking for parse errors
  
  % extracting documentation from zh_TW
  checking for parse errors
