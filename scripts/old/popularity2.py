# -*- coding: utf-8 -*-
from wikitools import *
import urllib, gzip, MySQLdb
import projectlister, settings
import sys, os, locale, traceback
import datetime, time, calendar
import re, hashlib, math

articletypes = {'unassessed':'{{unassessed-Class}}', 'image':'{{image-Class}}',
	'template':'{{template-Class}}', 'category':'{{category-Class}}', 'disambig':'{{disambig-Class}}',
	'portal':'{{portal-Class}}', 'list':'{{list-Class}}',
	'non-article':'{{NA-Class}}', 'blank':'{{NA-Class}}', 'stub':'{{stub-Class}}', 'start':'{{start-Class}}',
	'C':'{{C-Class}}', 'B':'{{B-Class}}', 'GA':'{{GA-Class}}', 'A':'{{A-Class}}',
	'FL':'{{FL-Class}}', 'FA':'{{FA-Class}}'} # This should cover most instances, some projects have some odd ones

site = wiki.Wiki()
site.login(settings.bot, settings.botpass)

hashlist = set()

def startup():
	projectlist = projectlister.projects
	if len(sys.argv) == 2 and (sys.argv[1] == "h" or sys.argv[1] == "help"):
		print "arg 1 = project (for categories), quotes may be necessary - Case Sensitive"
		print "arg 2 = project abbrev, for db table"
		print "arg 3 = list page, where to save the list"
		print projectlist.keys()
		quit()
	elif len(sys.argv) == 4:
		project = sys.argv[1]
		projectabbrv = sys.argv[2]
		listpage = sys.argv[3]
		projectlist[projectabbrv] = [project, listpage]
		f = open("projectlister.py", "rb")
		content = f.read()
		f = open("projectlister.py", "wb")
		content = content.replace('\n}', "\n	'"+projectabbrv+"': ['"+project+"', '"+listpage+"'],\n}")
		f.write(content)
		f.close()
	elif len(sys.argv) == 1:
		main(projectlist)
	else:
		print "Bad args, try 'popularity.py help' for help"
		quit()
		
def main(projectlist):
	try:
		f = open("PopLogFile.txt", 'wb')
		f.write("")
		f.close()
		db = MySQLdb.connect(host="localhost", user=settings.dbuser, passwd=settings.dbpass, use_unicode=True, charset='utf8')
		cursor = db.cursor()
		cursor.execute("USE `stats`")
		cursor.execute("TRUNCATE TABLE `popularity_copy`")
		cursor.execute(copyquery)
		day = (datetime.datetime.now()-datetime.timedelta(6)).day
		year = (datetime.datetime.now()-datetime.timedelta(6)).year
		month = (datetime.datetime.now()-datetime.timedelta(6)).month
		cal = calendar.monthcalendar(year+1, month)
		week = []
		for row in cal:
			if day in row:
				week = row
		numfiles = 24 * (7 - week.count(0))
		# week=[]  # Override settings
		# cal=[[]]
		# day=1
		# year=2009
		# numfiles = 28*24
		if (cal.index(week) == 1 and cal[0].count(0) != 0) or (cal[0].count(0) == 0 and cal.index(week) == 0):# or 1==1:
			if (cal.index(week) == 1 and cal[0].count(0) != 0):
				numfiles += 24 * (7 - cal[0].count(0))
			day = 1
			cursor.execute("TRUNCATE TABLE `popularity`")
			cursor.execute("TRUNCATE TABLE `redirect_map`")
			for project in projectlist.keys():
				abbrv = project
				name = projectlist[project][0]
				setupProject(name, abbrv)
			addRedirects()
		else:
			day = week[0]
		print numfiles
		pages = {}
		redirects = {}
		query = 'SELECT DISTINCT hash FROM popularity'
		cursor.execute(query)
		res = cursor.fetchall()
		for row in res:
			pages[row[0]] = 0
		query = 'SELECT DISTINCT rd_hash, target_hash FROM redirect_map'
		cursor.execute(query)
		res = cursor.fetchall()
		for row in res:
			redirects[row[0]] = row[1]
		del res
		db.close()
		count = 0
		while True:
			if not os.listdir("Q:/stats/statspages"):
				logMsg("No files ready")
				time.sleep(10)
			else:
				f = os.listdir("Q:/stats/statspages")[0]
				os.rename("Q:/stats/statspages/"+f, "Q:/stats/inprogress/"+f)
				pages = processPage("Q:/stats/inprogress/"+f, pages, redirects)
				count+=1
				if count == numfiles:
					break
		logMsg("Adding results to table")
		doQueries(pages)
		month = 2
		year = 2009
		if month < 10:
			month =  "0" + str(month)
		else:
			month = str(month)
		if 1==1 or numfiles < 24*7: #there's prolly a better way to do this
			numdays = calendar.monthrange(int(year), int(month))[1]
			for project in projectlist.keys():
				logMsg("Making table for "+projectlist[project][1])
				query = "SELECT COUNT(*) FROM popularity WHERE project_assess LIKE \"%'{0}'%\"".format(project)
				cursor.execute(query)
				pagecount = int(cursor.fetchone()[0])
				limit = "1000"
				if pagecount > 1000:
					headerlimit = "the top 1000 pages"
				else:
					headerlimit = "all "+str(pagecount)+" pages"
				listpage = projectlist[project][1]
				target = page.Page(site, listpage)				
				header = "This is a list of "+headerlimit+" ordered by number of views in the scope of the "+projectlist[project][0]+" Wikiproject.\n\n"
				header += "The data comes from data published by [[User:Midom|Domas Mituzas]] from Wikipedia's [[Squid (software)|squid]] server logs. "
				header += "Note that due to the use of a different program than http://stats.grok.se/ the numbers here may differ from that site. For more information, "
				header += "or for a copy of the full data for all pages, leave a message on [[User talk:Mr.Z-man|this talk page]].\n\n"
				header += "'''Note:''' This data aggregates the views for all redirects to each page.\n\n"
				header += "==List==\n<!-- Changes made to this section will be overwritten on the next update. Do not change the name of this section. -->"
				header += "\nPeriod: "+str(year)+"-"+str(month)+"-01 &mdash; "+str(year)+"-"+str(month)+"-"+str(numdays)+" (UTC)\n\n"
				table = header + '{| class="wikitable sortable" style="text-align: right;"\n'
				table+= '! Rank\n! Page\n! Views\n! Views (per day average)\n! Assessment\n'
				logMsg("Table started")
				query = "SELECT title, hits, project_assess FROM `popularity` WHERE project_assess LIKE \"%'{0}'%\" ORDER BY hits DESC LIMIT {1}".format(project, limit)
				cursor.execute(query)
				logMsg("Query executed")
				result = cursor.fetchall()
				rank = 0
				logMsg("Beginning loop")
				for record in result:
					rank+=1
					hits = locale.format("%.*f", (0,record[1]), True) # This formats the numbers with comma-thousand separators, its magic or something
					avg = locale.format("%.*f", (0, record[1]/numdays ), True)					
					exec 'project_assess = {'+record[2]+'}'					
					assess = project_assess[project]
					template = articletypes[assess]
					table+= "|-\n"
					table+= "| " + locale.format("%.*f", (0,rank), True) + "\n"
					table+= "| style='text-align: left;' | [[:" + record[0].replace('_', ' ') + "]]\n"
					table+= "| " + hits + "\n"
					table+= "| " + avg + "\n"
					table+= "| " + template + "\n"
					if rank/100 == rank/100.0:
						logMsg( rank)
				logMsg("Finishing table")
				table += "|}"
				logMsg( "Saving")
				target.edit(newtext=table, summary="Popularity stats for "+projectlist[project][0]+" project")
	except:
		import webbrowser, traceback
		f = open("AAA_POP2_ERROR.log", "wb")
		traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2], None, f)
		f.close()
		webbrowser.open("AAA_POP2_ERROR.log")
				

def processPage(fileloc, pages, redirects):	
	lines = 0
	count = 0
	rds = set(redirects.keys())
	pagelist = set(pages.keys())
	logMsg("Processing "+fileloc)
	file = open(fileloc, 'rb')
	datapage = gzip.GzipFile('', 'rb', 9, file)
	for line in datapage:
		if not line or not line.startswith('en '):
			if count > 0:
				break
			else:
				continue
		bits = line.split(' ')
		key = hashlib.md5(urllib.unquote(bits[1]).replace(' ', '_')).hexdigest()
		if key in pagelist:
			count+=1
			pages[key] += int(bits[2])
			if count%5000 == 0:
				logMsg(fileloc+ " at "+str(count)+" hits")
		elif key in rds:
			count+=1
			pages[redirects[key]] += int(bits[2])
			if count%5000 == 0:
				logMsg(fileloc+ " at "+str(count)+" hits")
	file.close()
	datapage.close()
	os.remove(fileloc)
	logMsg(fileloc+ " finished")
	return pages

def setupProject(project, abbrv):
	logMsg("Setting up "+project)
	db = MySQLdb.connect(host="localhost", user=settings.dbuser, passwd=settings.dbpass, use_unicode=True, charset='utf8')
	cursor = db.cursor()
	cursor.execute("USE `stats`")
	projecthashes = set()
	types = ['FA', 'FL', 'A', 'GA', 'B', 'C', 'start', 'stub', 'list', 'image', 'portal', 'category', 'disambig', 'template', 'unassessed', 'blank', 'non-article']
	insertquery = 'INSERT INTO popularity (title, hash, project_assess) VALUES( %s, %s, %s )'
	updatequery = 'UPDATE popularity SET project_assess=CONCAT(project_assess,",",%s) WHERE hash=%s'
	for type in types:
		if type == "unassessed":
			cat = "Category:Unassessed "+project+" articles"
		elif type == "non-article":
			cat = "Category:Non-article "+project+" pages"
		elif type == "blank":
			cat = "Category:"+project+" pages"
		else:
			cat = "Category:"+type+"-Class "+project+" articles"
		catpage = category.Category(site, cat)
		if not catpage.exists:
			continue
		cursor.execute("START TRANSACTION")
		for title in catpage.getAllMembersGen():
			if not title.isTalk():
				continue
			realtitle = title.toggleTalk(False, False)
			pagee = realtitle.title.replace(' ', '_')
			hashmd5 = hashlib.md5(realtitle.title.encode('utf-8').replace(' ', '_')).hexdigest()
			if hashmd5 in projecthashes:
				continue
			project_assess = "'%s':'%s'" % (abbrv, type)
			if hashmd5 in hashlist:
				bits = (project_assess, hashmd5)
				cursor.execute(updatequery, bits)
			else:
				hashlist.add(hashmd5)
				projecthashes.add(hashmd5)			
				bits = (pagee, hashmd5, project_assess)
				cursor.execute(insertquery, bits)	
		cursor.execute("COMMIT")
	del projecthashes
	db.close()
	
def addRedirects():
	logMsg("Adding redirects")
	db = MySQLdb.connect(host="localhost", user=settings.dbuser, passwd=settings.dbpass, use_unicode=True, charset='utf8')
	cursor = db.cursor()
	cursor.execute("USE `stats`")
	query = """INSERT INTO redirect_map (rd_hash, target_hash)
SELECT DISTINCT(MD5(page.page_title)), popularity.hash
FROM popularity
INNER JOIN (redirect, page)
ON (popularity.title=redirect.rd_title AND redirect.rd_from=page.page_id)
WHERE rd_namespace=0"""
	cursor.execute("START TRANSACTION")
	cursor.execute(query)
	cursor.execute("COMMIT")
	db.close()	
		
def logMsg(msg):
	print str(msg)
	f = open("PopLogFile.txt", 'ab')
	f.write(str(msg)+"\n")
	f.close()

def doQueries(pages):
	query = 'UPDATE popularity SET hits=hits+%s WHERE hash=%s'
	db = MySQLdb.connect(host="localhost", user=settings.dbuser, passwd=settings.dbpass)
	pagelist = [hash for hash in pages.keys() if pages[hash] != 0]
	pagelist.sort()
	cursor = db.cursor()
	cursor.execute("USE stats")
	cursor.execute("SET autocommit=0")
	cursor.execute("START TRANSACTION")
	for entry in pagelist:
		cursor.execute(query, (pages[entry], entry))
	cursor.execute("COMMIT")
	db.close()	
		
if __name__ == '__main__':
	startup()
