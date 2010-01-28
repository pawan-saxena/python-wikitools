#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import datetime
import urllib
import httplib
import MySQLdb
from MySQLdb import cursors
import sys
from wikitools import wiki, page
import settings
import calendar
import subprocess
import time
import locale

class ProjectLister(object):

	__slots__ = ('projects')
	
	def __init__(self):
		db = MySQLdb.connect(host="sql", read_default_file="/home/alexz/.my.cnf", db='u_alexz')
		cursor = db.cursor()
		cursor.execute('SELECT * FROM project_config')
		res = cursor.fetchall()
		self.projects = {}
		for item in res:
			self.projects[item[0]] = Project(item)
		db.close()
			
class Project(object):

	__slots__ = ('abbrv', 'name', 'cat_name', 'listpage', 'limit', 'month_added')

	def __init__(self, row):
		self.abbrv = row[0]
		self.name = row[1]
		self.cat_name = row[2]
		self.listpage = row[3]
		self.limit = row[4]
		self.month_added = row[5]

articletypes = {'unassessed':'{{unassessed-Class}}', 'file':'{{File-Class}}',
	'template':'{{template-Class}}', 'category':'{{category-Class}}', 'disambig':'{{disambig-Class}}',
	'portal':'{{portal-Class}}', 'list':'{{list-Class}}', 'image':'{{File-Class}}',
	'non-article':'{{NA-Class}}', 'blank':'{{NA-Class}}', 'stub':'{{stub-Class}}', 'start':'{{start-Class}}',
	'C':'{{C-Class}}', 'B':'{{B-Class}}', 'GA':'{{GA-Class}}', 'A':'{{A-Class}}',
	'FL':'{{FL-Class}}', 'FA':'{{FA-Class}}'} # This should cover most instances, some projects have some odd ones

importancetemplates = {'Top':'{{Top-importance}}', 'High':'{{High-importance}}', 'Mid':'{{Mid-importance}}',
	'Low':'{{Low-importance}}', 'Bottom':'{{Bottom-importance}}', 'No':'{{No-importance}}', 'NA':'{{NA-importance}}',
	'Unknown':'{{-importance}}', None:'{{-importance}}' }
	
# Manual run options:
# * --setup - runs setup
# * --make-tables - makes the result tables and saves them to the wiki
# * --manual=page - manually run the given datapage
	
hitcount = {}

def main():
	os.chdir('/home/alexz/popularity/')
	lock()
	manual = False
	if len(sys.argv) > 1 and sys.argv[1].startswith('--manual'):
		manual = True
		manualfile = sys.argv[1].split('=')[1]
		try:
			dt = datetime.datetime.strptime(manualfile, 'pagecounts-%Y%m%d-%H0000.gz')
		except:
			dt = datetime.datetime.strptime(manualfile, 'pagecounts-%Y%m%d-%H0001.gz')
		lists = (dt-datetime.timedelta(hours=1)).strftime('.%b%y')
	todo = datetime.datetime.utcnow()
	todo = todo.replace(minute = 0, second=0, microsecond=0)
	if manual:
		processPage(manualfile, lists)
		addResults(dt)
		unlock()
		return
	lists = (todo-datetime.timedelta(hours=1)).strftime('.%b%y')
	db = MySQLdb.connect(host="sql", read_default_file="/home/alexz/.my.cnf", db='u_alexz')
	c = db.cursor()
	c.execute('SELECT last FROM last_run')
	last = c.fetchone()[0]
	db.close()
	if (todo - last).seconds > 3600 or (todo-last).days:
		files = handleMissedRun(todo, last)
	else:
		files = [getFile(todo)]
	for f in files:
		processPage(f, lists)
	addResults(todo)
	db = MySQLdb.connect(host="sql", read_default_file="/home/alexz/.my.cnf", db='u_alexz')
	c = db.cursor()
	datestring = todo.isoformat(' ')
	c.execute('UPDATE last_run SET last="'+datestring+'" WHERE 1')
	unlock()
	next = todo + datetime.timedelta(hours=1)
	if next.day == 1 and next.hour == 1:
		makeResults()

def processPage(filename, lists):
	pages = 0
	redirpage = 0
	while True:
		pages+=1
		redirpage+=1
		try:
			os.stat('pagelist'+lists+'.'+str(pages))
			pagelist = 'pagelist'+lists+'.'+str(pages)
		except OSError:
			pagelist = '/dev/null/'
		try:
			os.stat('redirs'+lists+'.'+str(pages))
			redirs = 'redirs'+lists+'.'+str(pages)
		except OSError:
			redirs = '/dev/null/'
		if pagelist == '/dev/null/' and redirs == '/dev/null/':
			break
		proc = subprocess.Popen(['/home/alexz/scripts/processpage', filename, pagelist, redirs], stdout=subprocess.PIPE)
		out = proc.stdout
		while True:
			line = out.readline()
			if not line:
				if proc.poll() is not None:
					break
				else:
					time.sleep(0.01)
					continue
			(title, hits) = line.rstrip('\n').split(' | ', 1)
			if title in hitcount:
				hitcount[title] += int(hits)		
			else:
				hitcount[title] = int(hits)
	os.remove(filename)
	
def handleMissedRun(cur, last):
	print "Run missed"
	if cur.month != last.month:
		raise Exception("Missed runs span across months, do it manually!")
	hours = (cur-last).seconds/3600
	hours += (cur-last).days * 24
	files = []
	for x in range(0, hours):
		date = cur - datetime.timedelta(hours=x)
		files.append(getFile(date))
	print repr(files)
	return files
	
def getFile(date):
	page = date.strftime('pagecounts-%Y%m%d-%H0000.gz')
	url = "http://mituzas.lt"
	main = "/wikistats/"
	if checkExist(main+page):
		url += main + page
		filename = page
		urllib.urlretrieve(url, filename)
		return filename
	start = date.strftime('pagecounts-%Y%m%d-%H')
	end = '.gz'
	pos = 3
	for x in range(12):
		m = '1' if x < 8 else '2'
		mid = ''
		for y in range(4):
			if x > 3 and y == 1:
				mid+= '5'
			elif y == pos:
				mid+= m
			else:
				mid+= '0'
		if checkExist(main+start+mid+end):
			url += main+start+mid+end
			filename = start+mid+end
			break
		pos-=1
		if pos < 0:
			pos = 3
	else:
		unlock()
		raise Exception("File doesn't exist: "+str(date))
	urllib.urlretrieve(url, filename)
	return filename
		
def checkExist(testurl):
	conn = httplib.HTTPConnection('mituzas.lt')
	conn.request('HEAD', testurl)
	r = conn.getresponse()
	if r.status == 404 or r.status == 500:
		conn.close()
		return False
	else:
		cl = int(r.getheader('content-length'))
		if cl < 26214400: #25 MB
			return False
		conn.close()
		return True
		
def addResults(date):
	global hitcount
	def doQuery(titlelist):
		cond = "'"+"','".join([MySQLdb.escape_string(t) for t in titlelist])+"'"
		q = query % (table, group, cond)
		c.execute(q)
	query = "UPDATE %s SET hits=hits+%d WHERE title IN (%s)"
	db = MySQLdb.connect(host="sql", read_default_file="/home/alexz/.my.cnf", db='u_alexz')
	c = db.cursor()
	if date.day == 1 and date.hour == 0:
		date = date-datetime.timedelta(hours=1)
	table = date.strftime('pop_%b%y')
	hits = {}
	for title in hitcount:
		hc = hitcount[title]
		if hc == 0:
			continue 
		if hc in hits:
			hits[hc].append(title)
		else:
			hits[hc] = [title]
	del hitcount
	for group in hits:
		while len(hits[group]) > 2500:
			titles = hits[group][0:2500]
			doQuery(titles)
			del hits[group][0:2500]
		doQuery(hits[group])
	db.close()
	
def lock():
	f = open('pop.lock', 'r')
	l = f.readline().split('\n')[0]
	if l != '0':
		os.system('ps -Fp '+l)
		raise Exception("Other process still running")
	f = open('pop.lock', 'w')
	f.write(str(os.getpid()))
	f.close()
	
def unlock():	
	f = open('pop.lock', 'w')
	f.write('0')
	f.close()
	
def makeResults(date=None):
	site = wiki.Wiki()
	site.login(settings.bot, settings.botpass)
	site.setMaxlag(15)
	lister = ProjectLister()
	projects = lister.projects
	if not date:
		date = datetime.date.today()
		date = date-datetime.timedelta(days=20)
		date = date.replace(day=1)
	month = date.month
	year = date.year
	numdays = calendar.monthrange(year, month)[1]
	dbtable = date.strftime('pop_%b%y')
	db = MySQLdb.connect(host="sql", db='u_alexz', read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	for proj in projects.keys():
		diff = projects[proj].month_added - date
		if diff.days > 0: # The project was added after we started collecting data for this month
			continue
		target = page.Page(site, projects[proj].listpage, namespace=4)
		section = 0
		if target.exists:
			section = 1
		limit = projects[proj].limit
		header = "This is a list of the top pages ordered by number of views in the scope of "+projects[proj].name+".\n\n"
		header += "The data comes from data extracted from Wikipedia's [[Squid (software)|squid]] server logs. "
		header += "Note that due to the use of a different program than http://stats.grok.se/ the numbers here may differ from that site. For more information, "
		header += "leave a message on [[User talk:Mr.Z-man|this talk page]].\n\n"
		header += "You can view more results using the [[tools:~alexz/pop/|toolserver tool]].\n\n"
		header += "'''Note:''' This data aggregates the views for all redirects to each page.\n\n"
		header += "==List==\n<!-- Changes made to this section will be overwritten on the next update. Do not change the name of this section. -->"
		header += "\nPeriod: "+str(year)+"-"+str(month).zfill(2)+"-01 &mdash; "+str(year)+"-"+str(month).zfill(2)+"-"+str(numdays)+" (UTC)\n\n"
		if not section:
			table = header + '{| class="wikitable sortable" style="text-align: right;"\n'
		else:
			table = "==List==\n<!-- Changes made to this section will be overwritten on the next update. Do not change the name of this section. -->"
			table += "\nPeriod: "+str(year)+"-"+str(month).zfill(2)+"-01 &mdash; "+str(year)+"-"+str(month).zfill(2)+"-"+str(numdays)+" (UTC)\n\n"
			table += '{| class="wikitable sortable" style="text-align: right;"\n'
		query = "SELECT title, hits, project_assess FROM `"+dbtable+"` WHERE MATCH(project_assess) AGAINST (\"'"+proj+"':\") ORDER BY hits DESC LIMIT "+str(limit)
		cursor.execute(query)
		result = cursor.fetchall()
		test = result[0][2]
		imprt_test = eval('{'+test+'}')
		useImportance = True
		if imprt_test[proj][1] is None:
			useImportance = False
		table+= '! Rank\n! Page\n! Views\n! Views (per day average)\n! Assessment\n'
		if useImportance:
			table+= '! Importance\n'
		rank = 0
		for record in result:
			rank+=1
			hits = locale.format("%.*f", (0,record[1]), True)
			avg = locale.format("%.*f", (0, record[1]/numdays ), True)					
			project_assess = eval('{'+record[2]+'}')
			assess = project_assess[proj][0]
			template = articletypes[assess]
			table+= "|-\n"
			table+= "| " + locale.format("%.*f", (0,rank), True) + "\n"
			table+= "| style='text-align: left;' | [[:" + record[0].replace('_', ' ') + "]]\n"
			table+= "| " + hits + "\n"
			table+= "| " + avg + "\n"
			table+= "| " + template + "\n"
			if useImportance:
				imp = project_assess[proj][1]
				tem = importancetemplates[imp]
				table+= "| " + tem + "\n"
		table += "|}"
		res = target.edit(newtext=table, summary="Popularity stats for "+projects[proj].name, section=str(section))
		if 'new' in res['edit']:
			notifyProject(projects[proj].name, projects[proj].listpage, site)
			
def notifyProject(proj, listpage, site):
	p = page.Page(site, proj, namespace=4)
	talk = p.toggleTalk()
	text = '\n{{subst:User:Mr.Z-man/np|%s|%s}}' % (proj, listpage)
	summary = 'Pageview stats'
	talk.edit(text=text, summary=summary, section='new')
	
def setup():
	os.chdir('/home/alexz/popularity/')
	lister = ProjectLister()
	projectlist = lister.projects
	makeTempTables()
	for project in projectlist.keys():
		abbrv = project
		name = projectlist[project].cat_name
		setupProject(name, abbrv)
	getBLPs()
	addRedirects()
	makeDataPages()
	moveTables()
	
def makeTempTables():
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	db = MySQLdb.connect(host="sql-s1", db='u_alexz', read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	try:
		cursor.execute("DROP TABLE %s" % table)
	except:
		pass
	try:
		cursor.execute("DROP TABLE redirect_map")
	except:
		pass
		
	query1 = """CREATE TABLE `%s` (
		`title` varchar(255) collate latin1_bin NOT NULL,
		`hits` int(10) NOT NULL DEFAULT '0',
		`project_assess` text NOT NULL,
		UNIQUE KEY `title` (`title`),
		KEY `hits` (`hits`),
		FULLTEXT KEY `project_asssess` (`project_assess`)
		) ENGINE=MyISAM ROW_FORMAT=DYNAMIC""" % (table)
	query2 = """CREATE TABLE `redirect_map` (
		`from_title` varchar(255) NOT NULL,
		`to_title` varchar(255) NOT NULL,
		PRIMARY KEY  (`to_title`)
		) ENGINE=InnoDB;"""
	cursor.execute("START TRANSACTION")
	cursor.execute(query1)
	cursor.execute(query2)
	cursor.execute("COMMIT")
	db.close()
	
titlelist = set()
def setupProject(project, abbrv):
	site = wiki.Wiki()
	site.login(settings.bot, settings.botpass)
	site.setMaxlag(-1)
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	db = MySQLdb.connect(host="sql-s1", read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	projecttitles = set()
	project = project.replace(' ', '_')
	types = ['FA', 'FL', 'A', 'GA', 'B', 'C', 'start', 'stub', 'list', 'image', 'portal', 'category', 'disambig', 'template', 'unassessed', 'blank', 'non-article']
	insertquery = 'INSERT INTO u_alexz.'+table+' (title, project_assess) VALUES( %s, %s )'
	updatequery = 'UPDATE u_alexz.'+table+' SET project_assess=CONCAT(project_assess,",",%s) WHERE title=%s'
	selectquery = """SELECT page_namespace-1, page_title, SUBSTRING_INDEX(clB.cl_to, '-', 1) FROM enwiki_p.page 
		JOIN enwiki_p.categorylinks AS clA ON page_id=clA.cl_from 
		LEFT JOIN enwiki_p.categorylinks AS clB ON page_id=clB.cl_from AND clB.cl_to LIKE "%%-importance_"""+project+"""_articles"
		WHERE clA.cl_to=%s AND page_is_redirect=0 """
	for type in types:
		if type == "unassessed":
			cat = "Category:Unassessed "+project+" articles"
		elif type == "non-article":
			cat = "Category:Non-article "+project+" pages"
		elif type == "blank":
			cat = "Category:"+project+" pages"
		else:
			cat = "Category:"+type+"-Class "+project+" articles"
		catpage = page.Page(site, cat)
		if not catpage.exists:
			continue
		catpage.setNamespace(0)
		catname = catpage.title.replace(' ', '_')
		cursor.execute(selectquery, (catname))
		pagesincat = cursor.fetchall()
		for title in pagesincat:			
			if not title[0]%2 == 0:
				continue
			realtitle = title[1].decode('utf8').encode('utf8')
			if title[0] != 0:
				p = page.Page(site, realtitle, check=False, namespace=title[0])
				realtitle = p.title.encode('utf8')
			if realtitle in projecttitles:
				continue
			if title[2] is None:
				project_assess = "'%s':('%s',None)" % (abbrv, type)
			else:
				project_assess = "'%s':('%s','%s')" % (abbrv, type, title[2])
			projecttitles.add(realtitle)
			if realtitle in titlelist:
				bits = (project_assess, realtitle)
				cursor.execute(updatequery, bits)
			else:
				titlelist.add(realtitle)
				bits = (realtitle, project_assess)
				cursor.execute(insertquery, bits)	
	del projecttitles
	db.close()
	
def getBLPs():
	site = wiki.Wiki()
	site.login(settings.bot, settings.botpass)
	site.setMaxlag(-1)
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	db = MySQLdb.connect(host="sql-s1", read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	insertquery = 'INSERT INTO u_alexz.'+table+' (title, project_assess) VALUES( %s, %s )'
	updatequery = 'UPDATE u_alexz.'+table+' SET project_assess=CONCAT(project_assess,",",%s) WHERE title=%s'
	selectquery = """SELECT page_title FROM enwiki_p.page 
		JOIN enwiki_p.categorylinks ON page_id=cl_from 
		WHERE cl_to='Living_people' AND page_namespace=0 AND page_is_redirect=0 """
	cursor.execute(selectquery, (catname))
	pagesincat = cursor.fetchall()
	project_assess = "wpblp':(None,None)"
	for title in pagesincat:			
		realtitle = title[0].decode('utf8').encode('utf8')
		if realtitle in titlelist:
			bits = (project_assess, realtitle)
			cursor.execute(updatequery, bits)
		else:
			titlelist.add(realtitle)
			bits = (realtitle, project_assess)
			cursor.execute(insertquery, bits)	
	db.close()	
	
def addRedirects():
	db = MySQLdb.connect(host="sql-s1", read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	query = """INSERT IGNORE INTO u_alexz.redirect_map (from_title, to_title)
		SELECT DISTINCT(enwiki_p.page.page_title), u_alexz.%(table)s.title
		FROM u_alexz.%(table)s
		INNER JOIN (enwiki_p.redirect, enwiki_p.page)
		ON (u_alexz.%(table)s.title=enwiki_p.redirect.rd_title AND enwiki_p.redirect.rd_from=enwiki_p.page.page_id)
		WHERE rd_namespace=0""" % {'table':table}
	cursor.execute("START TRANSACTION")
	cursor.execute(query)
	cursor.execute("COMMIT")
	db.close()	
	
def makeDataPages():
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	lists = date.strftime('.%b%y')
	db = MySQLdb.connect(host="sql-s1", db='u_alexz', read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor(cursors.SSCursor)
	f = open('pagelist'+lists+'.1', 'ab')
	cursor.execute('SELECT title FROM '+table)
	count = 0
	listnum = 1
	while True:
		p = cursor.fetchone()
		if p:
			f.write(p[0]+"\n")
			count+=1
			if count == 1000000:
				count = 0
				listnum +=1
				f.close()
				f = open('pagelist'+lists+'.'+str(listnum), 'ab')
		else:
			break
	f.close()
	cursor.close()
	cursor = db.cursor(cursors.SSCursor)
	cursor.execute('SELECT from_title, to_title FROM redirect_map')
	f = open('redirs'+lists+'.1', 'ab')
	count = 0
	listnum = 1
	while True:
		row = cursor.fetchone()
		if row:
			f.write('%s|%s\n' % (row[0], row[1]))
			count+=1
			if count == 500000:
				count = 0
				listnum +=1
				f.close()
				f = open('redirs'+lists+'.'+str(listnum), 'ab')
		else:
			break
	f.close()
	cursor.close()
	
def moveTables():
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	db = MySQLdb.connect(host="sql-s1", db='u_alexz', read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	cmd = 'mysqldump -h sql-s1 --quick u_alexz %s > dump.sql' % table
	os.system(cmd)
	cmd = 'mysql -h sql u_alexz < dump.sql'
	os.system(cmd)
	os.remove('dump.sql')
	cursor.execute('START TRANSACTION')
	cursor.execute('DROP TABLE '+table)
	cursor.execute('DROP TABLE redirect_map')
	cursor.execute('COMMIT')	
	db2 = MySQLdb.connect(host="sql", db='u_alexz', read_default_file="/home/alexz/.my.cnf")
	c2 = db2.cursor()
		
if __name__ == '__main__':
	if len(sys.argv) > 1 and sys.argv[1] == '--setup':
		setup()
	elif len(sys.argv) > 1 and sys.argv[1] == '--make-tables':
		month = int(raw_input('Month: '))
		year = int(raw_input('Year: '))
		d = datetime.date(month=month, year=year, day=1)
		makeResults(d)
	else:
		main()
	
