import Dibbler
from sys import argv
import PyLucene,config,string
	

class EmailSearchFrontend(Dibbler.HTTPPlugin):
    _form = '''<html><body><h3>Email Search </h3>
               <form action='/'>
               Query: <input type='text' name='query' size='20'>
               <input type='submit' value='Search'></form>
               <pre>%s</pre></body></html>'''

    def onHome(self, query=None):
        if query:
            result = self.getQueryResults(query)
        else:
            result = ""
        self.writeOKHeaders('text/html')
        self.write(self._form % result)

    def onShutdown(self):
        self.writeOKHeaders('text/html')
        self.write("<html><body><p>OK.</p></body></html>")
        self.close()
        sys.exit()
        
        
        
    def onViewemail(self,querytxt):
        analyzer = PyLucene.StandardAnalyzer()
        searcher = PyLucene.IndexSearcher(config.DB_PATH)
        
        query = PyLucene.TermQuery( PyLucene.Term( 'id', querytxt ) )
        hits = searcher.search(query)

        len = hits.length()
        
        resultText=''
        
        if len <1:
            result='no results'
        
        else:
            docCount=0
            for docCount in range(len):
                resultText=resultText+'%s' % hits.doc(docCount).get('all').encode( "utf-8" )
                
            result =resultText
                
            
        self.writeOKHeaders('text/html')
        self.write(self._form % result)
        
        

    def getQueryResults(self,querytxt):
        analyzer = PyLucene.StandardAnalyzer()
        searcher = PyLucene.IndexSearcher(config.DB_PATH)
        

        query = PyLucene.QueryParser.parse(querytxt, 'all', analyzer)

        hits = searcher.search(query)

        len = hits.length()
        
        if len <1:
            return 'no results'
        
        resultText='We found : %s results.<br/>' % len
        
        
        docCount=0
        
        for docCount in range(len):
            resultText=resultText+'From: %s Subject:%s <a href="ViewEmail?querytxt=%s">view</a> </br>' % (hits.doc(docCount).get('from').encode( "utf-8" ),
                                                                                                          hits.doc(docCount).get('subject').encode( "utf-8" ),
                                                                                                          hits.doc(docCount).get('id').encode( "utf-8" ) )
                
        return resultText
        
        
    def stripAngleBrackets(self, address):
        """
        Strip the leading & trailing <> from an address.  Handy for
        getting FROM: addresses.
        """
        
        print address
        
        if '<' in address:
            start = string.index(address, '<') + 1
            end = string.index(address, '>')
            return address[start:end]
        else:
            return address
        
        
        
        




