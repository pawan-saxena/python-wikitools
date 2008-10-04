# coding=utf-8

""" Used in conjunction with photolocate.py to generate list of pages needing photos """

import wikipedia
import simplejson
import MySQLdb
import time

mainlist = []
site = wikipedia.getSite()

def main():
	cat = "Category:Wikipedia requested photographs"
	subCatsRecurse(cat)
	counter = 0
	for category in mainlist:
		#getCat(category)
		counter += 1
	print counter

def subCatsRecurse(category):
	data = {}
	cmcont = False
	sleep = 5
	while True:
		predata = {'action': 'query',
		  'list': 'categorymembers',
		  'cmtitle': category,
		  'cmnamespace': '14',
		  'cmlimit': '5000',
		  'cmprop': 'title',
		  'format': 'json',
		  'maxlag': '5'}
		if cmcont != False:
			predata['cmcontinue'] = cmcont
		try:
			response, json = site.postForm(site.apipath(), predata)
		except wikipedia.ServerError, e:
			wikipedia.output(u'Warning! %s: %s' % (site, e))
			return
		try:
			data = simplejson.loads(json)
		except ValueError:
			wikipedia.output(u'Warning! %s is defined but does not exist!' % site)
			subCatsRecurse(category)
			return
		try:
			while data['error']['code'] == 'maxlag':
				print( "Sleeping for " + str(sleep) + " seconds")
				time.sleep(sleep)
				sleep+=5
				response, json = site.postForm(site.apipath(), predata)
				data = simplejson.loads(json)
		except:
			pass
		sleep = 5	
		try:
			for item in data['query']['categorymembers']:
				if mainlist.count(item['title']) == 0:
					try:
						print item['title']
					except:
						pass #meh
					mainlist.append(category)
					subCatsRecurse(item['title'])
		except TypeError,KeyError:
			return
		try:
			cmcont = data['query-continue']['categorymembers']['cmcontinue']
		except:
			break

	
def getCat(cat):
	db = MySQLdb.connect(host="localhost", user="user", passwd="password", db="stats")
	cursor = db.cursor()
	data = {}
	counter = 0
	gcmcont = False
	while True:
		predata = {'action': 'query',
		  'generator': 'categorymembers',
		  'gcmtitle': cat,
		  'gcmnamespace': '1|3|5|7|9|11|13|15|101',
		  'gcmlimit': '5000',
		  'prop': 'info',
		  'inprop': 'subjectid',
		  'indexpageids': '1',
		  'format': 'json'}
		if gcmcont != False:
			predata['gcmcontinue'] = gcmcont
		try:
			response, json = site.postForm(site.apipath(), predata)
		except wikipedia.ServerError, e:
			print cat
			wikipedia.output(u'Warning! %s: %s' % (site, e))
			return
		try:
			data = simplejson.loads(json)
		except ValueError:
			wikipedia.output(u'Warning! %s is defined but does not exist!' % site)
			print cat
			return
		if data:
			try:
				for id in data['query']['pageids']:
					try:
						title = data['query']['pages'][id]['subjectid']
						counter+=1
						if counter == int(counter/5000)*5000:
							print counter
						cursor.execute("SELECT COUNT(*) FROM reqphoto WHERE pageid = %s", (title) )
						if cursor.fetchall()[0][0] != 1L:
							cursor.execute("INSERT INTO reqphoto (pageid) VALUES (%s);", (title) )
					except:
						pass
			except TypeError,KeyError:
					wikipedia.output(u'Error')
					return
			try:
				gcmcont = data['query-continue']['categorymembers']['gcmcontinue']
			except:
				break
		else:
			break
	
if __name__ == '__main__':
    try:
        main()
    finally:
        wikipedia.stopme()