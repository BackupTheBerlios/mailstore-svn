import PyLucene

analyzer = PyLucene.StandardAnalyzer()
searcher = PyLucene.IndexSearcher('./db')
        
query = PyLucene.QueryParser.parse('<86F4BF8C-F3B2-11D9-B8DB-000D93B753E0@asix.com.my>', 'id', analyzer)

hits = searcher.search(query)

print hits.doc(0).get('id').encode( "utf-8" )
