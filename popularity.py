# coding=utf-8

""" Script to generate popularity statistics for Wikiprojects """

import wikipedia
import re
import pagegenerators
import simplejson
import datetime
import MySQLdb
import time
import locale
import urllib
import sys
import projectlister
import calendar

def main():
	projectlist = projectlister.getList()
	if (len(sys.argv) != 2 and len(sys.argv) != 4) or sys.argv[1] == "h" or sys.argv[1] == "help":
		print "arg 1 = project (for categories), quotes may be necessary - Case Sensitive OR abbrev for previous projects"
		print "arg 2 = project abbrev, for db table"
		print "arg 3 = list page, where to save the list"
		print projectlist.keys()
		quit()
	if projectlist.has_key(sys.argv[1]):
		project = projectlist[sys.argv[1]][0]
		projectabbrv = projectlist[sys.argv[1]][1]
		listpage = projectlist[sys.argv[1]][2]
	elif len(sys.argv) == 4:
		project = sys.argv[1]
		projectabbrv = sys.argv[2]
		listpage = sys.argv[3]
		projectlist[projectabbrv] = [project, projectabbrv, listpage]
		f = open("projectlister.py", "w")
		f.write("def getList():\n	return "+str(projectlist))
		f.close()
	else:
		print "Bad args, try 'popularity.py help' for help"
		quit()
	site = wikipedia.getSite()
	db = MySQLdb.connect(host="localhost", user="user", passwd="password")
	cursor = db.cursor()
	cursor.execute('SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO"')
	cursor.execute("USE `stats`")
	cursor.execute("CREATE TABLE IF NOT EXISTS `"+projectabbrv+"` (`title` varchar(255) collate utf8_bin NOT NULL, `hits` int(10) NOT NULL, `assess` varchar(15) collate utf8_bin NOT NULL, FULLTEXT KEY `title` (`title`)) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_bin;")
	cursor.execute("TRUNCATE TABLE `"+projectabbrv+"`")
	articletypes = {'unassessed':'{{unassessed-Class}}', 'image':'{{image-Class}}', 'template':'{{template-Class}}', 'category':'{{category-Class}}', 'disambig':'{{disambig-Class}}', 'portal':'{{portal-Class}}', 'list':'{{list-Class}}', 'redirect':'{{redirect-Class}}', 'non-article':'{{NA-Class}}', 'blank':'{{NA-Class}}', 'stub':'{{stub-Class}}', 'start':'{{start-Class}}', 'C':'{{C-Class}}', 'B':'{{B-Class}}', 'GA':'{{GA-Class}}', 'A':'{{A-Class}}', 'FL':'{{FL-Class}}', 'FA':'{{FA-Class}}'} # This should cover most instances, some projects have some odd ones
	counter = 0
	month = (datetime.datetime.now() - datetime.timedelta(25)).month
	if month < 10:
		month =  "0" + str(month)
	else:
		month = str(month)
	print "Month is: " + month
	time.sleep(3)
	year = str((datetime.datetime.now() - datetime.timedelta(25)).year)
	urlbase = "http://stats.grok.se/json/en/"+year+month+"/"
	errorcount = 0
	errorlist = []
	for type in articletypes.keys():
		print "Starting: " + type
		if type == "unassessed":
			category = "Category:Unassessed "+project+" articles"
		elif type == "non-article":
			category = "Category:Non-article "+project+" pages"
		elif type == "blank":
			category = "Category:"+project+" pages"
		else:
			category = "Category:"+type+"-Class "+project+" articles"
		catpage = wikipedia.Page(site, category)
		if not catpage.exists():
			continue
		print ("Doing "+category.title())
		gen = getCat(category)
		for page in pagegenerators.PreloadingGenerator(gen, pageNumber = 500):
			if not page.isTalkPage():
				continue
			realtitle = page.toggleTalkPage()
			try:
				cursor = db.cursor()
				query = 'SELECT * FROM `'+projectabbrv+'` WHERE title = "'+realtitle.urlname()+'"'
				if cursor.execute(query) == 1L:
					continue
				url = urlbase+realtitle.urlname()
				info = urllib.urlopen(url)
				rankdata = simplejson.loads(info.read())
				hits = str(rankdata['total_views'])
				query = "INSERT INTO `"+projectabbrv+"` (title, hits, assess) VALUES( '"+realtitle.urlname()+"', "+hits+", '"+type+"' )"
				cursor.execute(query)
				counter+=1
				if counter == 8:
					time.sleep(3) # So we don't kill Henrik's server
					counter = 0
			except:
				print("Error on:"+realtitle.urlname())
				errorcount+=1
				errorlist.append(realtitle.urlname())
				print sys.exc_info()[0]
				print sys.exc_info()[1]
				print sys.exc_info()[2]
	if errorcount != 0:
		test = raw_input(str(errorcount)+' errors occured, manual input required, press Y to restart, anything else to continue: ')
		db = MySQLdb.connect(host="localhost", user="user", passwd="password") # In case we lose the connection
		cursor = db.cursor()
		cursor.execute("USE `stats`")
		if test == "Y" or test == "y":
			main()
			quit()
		for title in errorlist:
			print title
			hits = raw_input("Hits: ")
			assess = raw_input("Assess: ")
			cursor = db.cursor()
			query = 'SELECT * FROM `'+projectabbrv+'` WHERE title = "'+title+'"'
			if cursor.execute(query) == 1L:
				continue
			query = "INSERT INTO `"+projectabbrv+"` (title, hits, assess) VALUES( '"+title+"', "+hits+", '"+assess+"' )"
			cursor.execute(query)
	cursor = db.cursor()
	cursor.execute("SELECT COUNT(*) FROM `"+projectabbrv+"`")
	pagecount = int(cursor.fetchone()[0])
	if pagecount*1/8 > 2500:
		limit = "2500"
		headerlimit = "the top 2500 pages"
	elif pagecount <= 500:
		limit = "2500"
		headerlimit = "all "+pagecount+" pages"
	else:
		limit = str(pagecount*1/8)
		headerlimit = "approximately the top 12.5% (1/8) pages"
	numdays = calendar.monthrange(int(year), int(month))[1]
	target = wikipedia.Page(site, listpage)
	if not target.exists() or 1==1: # TEMPORARY OVERRIDE
		header = "This is a list of "+headerlimit+" ordered by number of views in "+calendar.month_name[int(month)]+" in the scope of the "+project+" WikiProject.\n\nThe data comes from http://stats.grok.se/, a site operated by [[User:Henrik|Henrik]], with data published by [[User:Midom|Domas Mituzas]] from Wikimedia's [[Squid (software)|squid]] server logs. For more information, or for a copy of the full data for all pages, leave a message on [[User talk:Mr.Z-man|this talk page]].\n\n==List==\n<!-- Changes made to this section will be overwritten on the next update. Do not change the name of this section. -->\nPeriod: "+year+"-"+month+"-01 &mdash; "+year+"-"+month+"-"+str(numdays)+" (UTC)\n\n"
	else:
		target = wikipedia.Page(site, listpage+"#List")
		if not target.exists():
			print "Error: List section does not exist"
			raw_input("Rename section and press Enter to continue")
		header = "== List ==\n<!-- Changes made to this section will be overwritten on the next update. Do not change the name of this section. -->\nPeriod: "+year+"-"+month+"-01 &mdash; "+year+"-"+month+"-"+str(numdays)+" (UTC)\n\n"
	table = header + '{| class="wikitable sortable" style="text-align: right;"\n'
	table+= '! Rank\n! Page\n! Views\n! Views (per day average)\n! Assessment\n'
	print "Table started"
	cursor.execute("SELECT title, hits, assess FROM `"+projectabbrv+"` ORDER BY hits DESC LIMIT "+limit+"" )
	print "Query executed"
	result = cursor.fetchall()
	rank = 0
	print "Beginning loop"
	for record in result:
		rank+=1
		page = wikipedia.Page(site, record[0])
		hits = locale.format("%.*f", (0,record[1]), True) # This formats the numbers with comma-thousand separators, not sure how
		avg = locale.format("%.*f", (0, record[1]/numdays ), True)
		assess = record[2]
		template = articletypes[assess]
		table+= "|-\n"
		table+= "| " + locale.format("%.*f", (0,rank), True) + "\n"
		table+= "| style='text-align: left;' | [[:" + page.title() + "]]\n"
		table+= "| " + hits + "\n"
		table+= "| " + avg + "\n"
		table+= "| " + template + "\n"
		if rank/100 == rank/100.0:
			print rank
	print "Finishing table"
	table += "|}"
	print "Saving"
	target.put(table, comment="Popularity stats for "+project+" project", nobot = True)

def getCat(template):
    site = wikipedia.getSite()
    data = {}
    counter = 0
    eicont = False
    if not site.apipath():
    	gen = wikipedia.Page(site, page).getReferences(False, True, True)
    	for page in gen:
            yield page
        return
    while True:
      predata = {'action': 'query',
          'query': 'list',
          'list': 'categorymembers',
          'cmtitle': template,
          'cmlimit': '5000',
          'format': 'json'}
      if eicont != False:
        predata['cmcontinue'] = eicont
      #print u'Getting references to [[' + template + u']]'
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
        for page in data['query']['categorymembers']:
          counter+=1
          if counter == int(counter/5000)*5000:
            print counter
          yield wikipedia.Page(site,wikipedia.html2unicode(page['title']))
      except TypeError,KeyError:
        return
      try:
        eicont = data['query-continue']['categorymembers']['cmcontinue']
      except:
        break     
		
if __name__ == '__main__':
    try:
        main()
    finally:
        wikipedia.stopme()