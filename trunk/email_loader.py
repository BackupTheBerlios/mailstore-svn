from PyLucene import Document, Field
from time import strptime, strftime

import sys

class EmailDoc( Document ):

    def __init__( self, msg,filename ):
        Document.__init__( self )

        sender = msg.get('from', '').decode('utf8', 'replace')

        self.add( Field.Text( 'from', sender ) )

        subject = msg.get('subject', '').decode('utf8', 'replace')
        self.add( Field.Text( 'subject', subject ) )
        
        
        id = msg.get('Message-ID', '').decode('utf8', 'replace')
        self.add( Field.Keyword( 'id', id ) )

        #date = strftime( '%Y%m%d%H%M%S', strptime(msg.get('Date', '').decode('utf8', 'replace')) )
        #self.add( Field.Keyword( 'date', date ) )

        body = []
        for part in msg.walk():
            typ = part.get_type()
            if typ and typ.lower() == "text/plain":
                try:
                    charset = part.get_charsets()[0]
                except:
                    pass
                if not charset:
                    charset = 'utf8'
                # Found the first text/plain part
                bdy = part.get_payload(decode=True)
                try:
                    bdy = bdy.decode(charset, 'replace')
                except LookupError:
                    sys.stderr.write("charset lookup error in %s\n" % filename)
                    continue
                body.append(bdy)
        
        # no body found, probably not a multipart msg
        if not body and not msg.is_multipart():
            body = [msg.get_payload().decode('utf8', 'replace')]

        if not body:
            sys.stderr.write("no body for %s\n" % filename)
        body = '\n\n'.join(body)
        
                
        self.add( Field.Text( 'body', body ) )

        
        self.add( Field.Text( 'all', sender + subject + body ) )
        

        
        
        
        


