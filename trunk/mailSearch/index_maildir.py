#!/usr/bin/env python2.4
#import PyLucene
from mailbox import UnixMailbox
from PyLucene import StandardAnalyzer, FSDirectory, IndexWriter
from email_loader import EmailDoc
import os,sys,datetime,email,config

# determine when (if) the last update was
lastUp = datetime.datetime(2000, 1, 1)
createNewIndex = True

quiet = False
if len(sys.argv) > 1 and sys.argv[1] in ('-q', '--quiet'):
  quiet = True

store = FSDirectory.getDirectory( config.DB_PATH, True )
writer = IndexWriter( store, StandardAnalyzer(), True )

"""
mailbox = UnixMailbox( open('chipy.mbox') )
while True:
    msg = mailbox.next()
    if msg == None: break
    writer.addDocument( EmailDoc(msg) )
"""

source=config.MAILDIR_ROOT_DIR

for root, dirs, files in os.walk(source):
    if not quiet:
      sys.stdout.write('\nindexing files in %s' % root)
      sys.stdout.flush()
    # remove hidden directories
    drm = []
    for d in dirs:
        if d[:1] == '.':
            drm.append(d)
    for d in drm:
        dirs.remove(d)
    
    for f in files:
        if f[:1] == '.': # ignore hidden files
            continue
        
        # ignore old files
        filename = os.path.join(root, f)
        if datetime.datetime.fromtimestamp(os.path.getmtime(filename)) <= lastUp:
            continue
          
        fp = open(filename) # do I need to close this myself?
        try:
            msg = email.message_from_file(fp)
            if msg == None: break
            writer.addDocument( EmailDoc(msg,filename) )
            print "indexed mail", filename            
        except email.Errors.MessageParseError:
            print 'error parsing', filename
            continue

print dir(writer)

print writer.docCount()
writer.close()
