from sys import argv
import PyLucene
	
analyzer = PyLucene.StandardAnalyzer()
#directory = PyLucene.FSDirectory_getDirectory('./chipy-index',True)
#writer = PyLucene.IndexWriter(directory,analyzer,True)
	
#doc = PyLucene.Document()
#below taken almost verbatim from the unit test
#doc.add(PyLucene.Field('title','value of testing',True,True,True))
	
#writer.addDocument(doc)
#writer.close()
	
# search

searcher = PyLucene.IndexSearcher('emailSearchPyLucene/chipy-index')
       
try:
    querytxt = argv[1]
    

    query = PyLucene.QueryParser.parse(querytxt, 'all', analyzer)
    hits = searcher.search(query)
    len = hits.length()
    print 'query text: %s' %querytxt
    print 'should be 1:%s' %len
    print 'what we matched: %s' %hits.doc(0).get('all')
    print 'score: %s' %hits.score(0)
    
    
except IndexError:
    
    doccount =0
    for doccount in range(searcher.maxDoc()):
        print searcher.doc(doccount)
	
#querytxt = 'value -testing'
#query = PyLucene.QueryParser.parse(querytxt, 'title', analyzer)
#hits = searcher.search(query)
#len = hits.length()
#print 'query text: %s' %querytxt
#print 'should be 0: %s' %len
	
#querytxt = 'value AND testing'
#query = PyLucene.QueryParser.parse(querytxt, 'title', analyzer)
#hits = searcher.search(query)
#len = hits.length()
#print 'query text: %s' %querytxt
#print 'should be 1: %s' %len
#print 'what we matched: %s' %hits.doc(0).get('title')
#print 'score: %s' %hits.score(0)
