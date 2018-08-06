#!/usr/bin/python

"""
Library for NCBI eutils API helper functions
Author: Jim

*** Eutils Docs ***
https://www.ncbi.nlm.nih.gov/books/NBK25501/
https://www.ncbi.nlm.nih.gov/books/NBK3827/#pubmedhelp.How_do_I_search_by_journal_na

*** PubMed Central Docs *** (this module is not using these yet)
https://www.ncbi.nlm.nih.gov/pmc/tools/developers/
https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/
https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/
https://www.ncbi.nlm.nih.gov/pmc/tools/ftp/

Eutils XML DTD links
**** Pubmed ***
Version 1.0 and 2.0 efetch output (same dtd):
    https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_180601.dtd

Version 1.0 esummary output:
    https://eutils.ncbi.nlm.nih.gov/eutils/dtd/20041029/esummary-v1.dtd

Version 2.0 esummary output:
    https://eutils.ncbi.nlm.nih.gov/eutils/dtd/20160808/esummary_pubmed.dtd

**** PMC ***
Version 1.0 and 2.0 efetch output (same dtd:
    https://dtd.nlm.nih.gov/ncbi/pmc/articleset/nlm-articleset-2.0.dtd

Version 1.0 esummary output:
    https://eutils.ncbi.nlm.nih.gov/eutils/dtd/20041029/esummary-v1.dtd

Version 2.0 esummary output:
    https://eutils.ncbi.nlm.nih.gov/eutils/dtd/20160609/esummary_pmc.dtd
"""
import sys
import xml.dom.minidom as minidom	# try to use things in python 2.4
#import xml.etree.ElementTree as et
#import json
import simpleURLLib as surl
# -------------------------
	# should get from env
EUTILS_API_KEY = '93420e6fa0a8dcf419d7a62e185706572e08'

EUTILS_BASE   = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'

ESEARCH_BASE  = EUTILS_BASE + 'esearch.fcgi?&api_key=' + EUTILS_API_KEY
EPOST_BASE    = EUTILS_BASE + 'epost.fcgi'	# APIkey must be in post params

EFETCH_BASE   = EUTILS_BASE + 'efetch.fcgi?&api_key='  + EUTILS_API_KEY
ESUMMARY_BASE = EUTILS_BASE + 'esummary.fcgi?&api_key=' + EUTILS_API_KEY

	# not used. Should implement functions for this. Is this correct URL?
ID_CONVERTER_URL = ESEARCH_BASE + '&db=pubmed&term=%s[lid]'

USEHISTORY = "&usehistory=y"		# eutils param for history
# -------------------------

def getWebenv(root,	# minidom root of xml output a eutils
	    ):
    """ Parse out the webenv and query_key params from eutils XML output
    """
    			# I'm no dom expert, maybe there's a better way?
    query_key = root.getElementsByTagName("QueryKey")[0].childNodes[0].data
    webenv    = root.getElementsByTagName("WebEnv")[0].childNodes[0].data

    return webenv, query_key
# -------------------------

def codeWebenvURLParams(webenv,
			query_key,
	    ):
    """ Return webenv and query_key coded as eutils URL params
    """
    return "&webenv=%s&query_key=%s" % (webenv, query_key)
# -------------------------

def doSearch(db,		# eutils db name (pubmed, PMC, ...)
	    queryString,	# esearch query string
	    URLReader=surl.ThrottledURLReader(),
	    debug=False,
    ):
    """ do a eutils.esearch & leave result set on the eutils history server.
	Return count and webenv/query_key (as URL params) on history server.
    """
    # do search, save results in eutils history - get search output in xml
    url = ESEARCH_BASE + "%s&db=%s&term=%s&retmode=%s" % \
					(USEHISTORY, db, queryString,'xml')
    if debug: sys.stderr.write( "Esearch URL:\n%s\n" % url)

    outputX = URLReader.readURL(url) 
    if debug: sys.stderr.write( "Output from Esearch:\n%s\n" % outputX)

    xmlDoc = minidom.parseString(outputX)

    count = int(xmlDoc.getElementsByTagName("Count")[0].childNodes[0].data)

    # get webenv params
    webenv, query_key = getWebenv(xmlDoc)
    webenvURLParams = codeWebenvURLParams(webenv, query_key)

    return count, webenvURLParams
# -------------------------

def doPost(db,			# eutils db name (pubmed, PMC, ...)
	    ids,		# list of IDs to post and get fetch for
	    URLReader=surl.ThrottledURLReader(),
	    debug=False,
    ):
    """ do a eutils.post and return webenv/query_key as eutils URL params
    """
    # build params for post
    idParams = ','.join( map(lambda x: str(x).strip(), ids)  )
    params = "api_key=%s&db=%s&id=%s" %(EUTILS_API_KEY, db, idParams)

    url = EPOST_BASE
    if debug:
	sys.stderr.write( "Post URL:\n%s\n" % url )
	sys.stderr.write( "Post Params: \n'%s'\n" % params)

    outputX = URLReader.readURL(url, params=params, GET=False) 
    if debug: sys.stderr.write( "Output from Epost:\n%s\n" % outputX)

    xmlDoc = minidom.parseString(outputX)

    # get webenv params
    webenv, query_key = getWebenv(xmlDoc)
    webenvURLParams = codeWebenvURLParams(webenv, query_key)

    return webenvURLParams
# -------------------------

def getResults(db,		# eutils db name (pubmed, PMC, ...)
		webenvURLParams,
		op='summary',	# 'summary' or 'fetch' output
		retmode='json',	# eutils desired output format
		version='2.0',	# eutils output version (affects json?)
		URLReader=surl.ThrottledURLReader(),
		debug=False,
    ):
    """ Do a eutils.esearch or efetch from results on history server 
	    and return results (string)
	Retmode is usually 'json' or 'xml' or 'text'. Maybe other options
	depending on the db.
	Note: for json output, eutils have a 500 record output limit,
	and you get an eutils error if you don't have &retmax
    """
    # result type
    if op == 'summary': url = ESUMMARY_BASE
    elif op == 'fetch': url = EFETCH_BASE
    else: raise Exception('Invalid SearchResults operation: %s' % str(op))

    url += webenvURLParams + \
		"&db=%s&retmode=%s&version=%s" % (db, retmode, str(version))
    if retmode == 'json': url += "&retmax=500"
    if debug: sys.stderr.write( "Summary/Fetch URL:\n%s\n" % url )

    output = URLReader.readURL(url)

    return output
# -------------------------

def getSearchResults(db,		# eutils db name (pubmed, PMC, ...)
		    queryString,	# esearch query string
		    op='summary',	# 'summary' or 'fetch' output
		    retmode='json',	# eutils desired output format
		    version='2.0',	# eutils output version (affects json?)
		    URLReader=surl.ThrottledURLReader(),
		    debug=False,
    ):
    """ Do esearch and get results as esummary or efetch.
	Return count of results, results (string), webenv/query_key as
	    eutils URL params
	Retmode is usually 'json' or 'xml' or 'text'. Maybe other options
	depending on the db.
    """
    # do search, save results in eutils history
    count, webenvURLParams = doSearch(db, queryString,
				URLReader=URLReader, debug=debug)

    # get result summary or fetch
    output = getResults(db, webenvURLParams,
				op=op, retmode=retmode, version=version,
				URLReader=URLReader, debug=debug)
    return count, output, webenvURLParams
# -------------------------

def getPostResults(db,		# eutils db name (pubmed, PMC, ...)
		    ids,	# list of IDs to post and get results for
		    op='summary',	# 'summary' or 'fetch' output
		    retmode='json',	# eutils desired output format
		    version='2.0',	# eutils output version (affects json?)
		    URLReader=surl.ThrottledURLReader(),
		    debug=False,
    ):
    """ do a eutils.post and return eutils.efetch for the results
    """
    webenvURLParams = doPost(db, ids, URLReader=URLReader, debug=debug)

    # get result summary or fetch
    output = getResults(db, webenvURLParams, op=op, retmode=retmode,
		    version=version, URLReader=URLReader, debug=debug)
    return output, webenvURLParams

# -------------------------

if __name__ == "__main__":      # test code
    URLReader = surl.ThrottledURLReader()
    query = 'Aging+Cell[TA]+AND+(2017/01/01:2017/02/01[PPDAT]+AND+foxo[TITLE})'

    print '-' * 30
    count, webenv = doSearch('pubmed',query, URLReader=URLReader, debug=False)
    print "webenv: '%s'" % webenv
    print "count: %d" % count
    print

    print '-' * 30
    count, output, webenv = getSearchResults('pubmed',query, op='summary',
		retmode='json', version='2.0', URLReader=URLReader, debug=False)
    print "output: \n%s" % output[:2000]
    print

    print '-' * 30
    count, output, webenv = getSearchResults('pmc', query, op='summary',
		retmode='xml', version='1.0', URLReader=URLReader, debug=False)
    print "output: \n%s" % output[:2000]
    print

    print '-' * 30
    count, output, webenv = getSearchResults('pmc',query, op='fetch',
		retmode='xml', version='1.0', URLReader=URLReader, debug=False)
    print "output: \n%s" % output[:2000]
    print

    ids = [28440906, 28256074, ]
    print '-' * 30
    webenv = doPost('pubmed', ids, URLReader=URLReader, debug=False)
    print "webenv: '%s'" % webenv
    print

    print '-' * 30
    output, webenv = getPostResults('pubmed', ids, op='summary',
		retmode='xml', version='2.0', URLReader=URLReader, debug=True)
    print "output: \n%s" % output[:2000]
    print

    print '-' * 30
    output, webenv = getPostResults('pubmed', ids, op='fetch',
		retmode='xml', version='2.0', URLReader=URLReader, debug=True)
    print "output: \n%s" % output[:2000]
    print
