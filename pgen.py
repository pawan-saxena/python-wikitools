# coding=utf-8

""" Used to find pages with coordinates """

import wikipedia
import simplejson
import MySQLdb

def main():
	print "Doing Template:Coord"
	getLinks("Template:Coord")
	print "Doing Template:Coor URL"
	getLinks("Template:Coor URL")
	
def getLinks(template):
	db = MySQLdb.connect(host="localhost", user="user", passwd="password", db="stats")
	cursor = db.cursor()
	site = wikipedia.getSite()
	data = {}
	counter = 0
	eicont = False
	while True:
		predata = {'action': 'query',
		  'list': 'embeddedin',
		  'eititle': template,
		  'eilimit': '5000',
		  'einamespace': '0',
		  'format': 'json'}
		if eicont != False:
			predata['eicontinue'] = eicont
		try:
			response, json = site.postForm(site.apipath(), predata)
		except wikipedia.ServerError, e:
			wikipedia.output(u'Warning! %s: %s' % (site, e))
			return
		try:
			data = simplejson.loads(json)
		except ValueError:
			wikipedia.output(u'Warning! %s is defined but does not exist!' % site)
			return
		try:
			for page in data['query']['embeddedin']:
				counter+=1
				if counter == int(counter/5000)*5000:
					print counter
				cursor.execute("SELECT COUNT(*) FROM coorlinks WHERE pageid = %s", (page['pageid']))
				if cursor.fetchall()[0][0] != 1L:
					cursor.execute("INSERT INTO coorlinks (pageid) VALUES (%s);", (page['pageid']) )
		except TypeError,KeyError:
			wikipedia.output(u'Error')
			return
		try:
			eicont = data['query-continue']['embeddedin']['eicontinue']
		except:
			break 
	
	
if __name__ == '__main__':
    try:
        main()
    finally:
        wikipedia.stopme()