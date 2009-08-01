#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import cPickle as pickle
import datetime
import urllib
import httplib
import hashlib
import MySQLdb
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
	l = open('lastrun.dat', 'r')
	last = pickle.load(l)
	l.close()
	if (todo - last).seconds > 3600 or (todo-last).days:
		files = handleMissedRun(todo, last)
	else:
		files = [getFile(todo)]
	for f in files:
		processPage(f, lists)
	addResults(todo)
	l = open('lastrun.dat', 'w')
	pickle.dump(todo, l, pickle.HIGHEST_PROTOCOL)
	l.close()
	unlock()
	next = todo + datetime.timedelta(hours=1)
	if next.day == 1 and next.hour == 1:
		makeResults()

def processPage(filename, lists):
	proc = subprocess.Popen(['/home/alexz/scripts/processpage', filename, 'pagelist'+lists, 'redirs'+lists], stdout=subprocess.PIPE)
	out = proc.stdout
	while True:
		line = out.readline()
		if not line:
			if proc.poll() is not None:
				break
			else:
				time.sleep(0.1)
				continue
		(hash, hits) = line.rstrip('\n').split(' - ', 1)
		if hash in hitcount:
			hitcount[hash] += int(hits)		
		else:
			hitcount[hash] = int(hits)
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
	altpage = date.strftime('pagecounts-%Y%m%d-%H0001.gz')
	url = "http://mituzas.lt"
	main = "/wikistats/"
	archive = "/wikistats/archive/%d/%s/" % (date.year, str(date.month).zfill(2))
	if checkExist(main+page):
		url += main + page
		filename = page
	elif checkExist(main+altpage):
		url += main + altpage
		filename = altpage
	elif checkExist(archive+page):
		url += archive + page
		filename = page
	elif checkExist(archive+altpage):
		url += archive + altpage
		filename = altpage
	else:
		raise Exception("File doesn't exist")
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
	def doQuery(hashlist):
		cond = ','.join([repr(h) for h in hashlist])
		q = query % (table, group, cond)
		c.execute(q)
	query = "UPDATE %s SET hits=hits+%d WHERE hash IN (%s)"
	db = MySQLdb.connect(host="sql", read_default_file="/home/alexz/.my.cnf", db='u_alexz')
	c = db.cursor()
	c.execute("SET autocommit=0")
	if date.day == 1 and date.hour == 0:
		date = date-datetime.timedelta(hours=1)
	table = date.strftime('pop_%b%y')
	hits = {}
	for hash in hitcount:
		hc = hitcount[hash]
		if hc == 0:
			continue 
		if hc in hits:
			hits[hc].append(hash)
		else:
			hits[hc] = [hash]
	del hitcount
	for group in hits:
		while len(hits[group]) > 1000:
			hashes = hits[group][0:1000]
			doQuery(hashes)
			del hits[group][0:1000]
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
	talk = proj.toggleTalk()
	text = '\n{{subst:User:Mr.Z-man/np|%s|%s}}' % (proj, listpage)
	summary = 'Pageview stats'
	talk.edit(appendtext=text, summary=summary, section='new')
	
def setup():
	os.chdir('/home/alexz/popularity/')
	lister = ProjectLister()
	projectlist = lister.projects
	makeTempTables()
	for project in projectlist.keys():
		abbrv = project
		name = projectlist[project].cat_name
		setupProject(name, abbrv)
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
		`hash` varchar(32) NOT NULL,
		`hits` int(10) NOT NULL DEFAULT '0',
		`project_assess` text NOT NULL,
		UNIQUE KEY `title` (`title`),
		UNIQUE KEY `hash` (`hash`),
		KEY `hits` (`hits`),
		FULLTEXT KEY `project_asssess` (`project_assess`)
		) ENGINE=MyISAM ROW_FORMAT=DYNAMIC""" % (table)
	query2 = """CREATE TABLE `redirect_map` (
		`target_hash` varchar(32) NOT NULL,
		`rd_hash` varchar(32) NOT NULL,
		PRIMARY KEY  (`rd_hash`)
		) ENGINE=InnoDB;"""
	cursor.execute("START TRANSACTION")
	cursor.execute(query1)
	cursor.execute(query2)
	cursor.execute("COMMIT")
	db.close()
	
hashlist = set()
def setupProject(project, abbrv):
	site = wiki.Wiki()
	site.login(settings.bot, settings.botpass)
	site.setMaxlag(-1)
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	db = MySQLdb.connect(host="sql-s1", read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	projecthashes = set()
	project = project.replace(' ', '_')
	types = ['FA', 'FL', 'A', 'GA', 'B', 'C', 'start', 'stub', 'list', 'image', 'portal', 'category', 'disambig', 'template', 'unassessed', 'blank', 'non-article']
	insertquery = 'INSERT INTO u_alexz.'+table+' (title, hash, project_assess) VALUES( %s, %s, %s )'
	updatequery = 'UPDATE u_alexz.'+table+' SET project_assess=CONCAT(project_assess,",",%s) WHERE hash=%s'
	selectquery = """SELECT page_namespace-1, page_title, SUBSTRING_INDEX(clB.cl_to, '-', 1) FROM enwiki_p.page 
		JOIN enwiki_p.categorylinks AS clA ON page_id=clA.cl_from 
		LEFT JOIN enwiki_p.categorylinks AS clB ON page_id=clB.cl_from AND clB.cl_to LIKE "%%-importance_"""+project+"""_articles"
		WHERE clA.cl_to=%s """
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
			hashmd5 = hashlib.md5(realtitle).hexdigest()
			if hashmd5 in projecthashes:
				continue
			if title[2] is None:
				project_assess = "'%s':('%s',None)" % (abbrv, type)
			else:
				project_assess = "'%s':('%s','%s')" % (abbrv, type, title[2])
			if hashmd5 in hashlist:
				bits = (project_assess, hashmd5)
				cursor.execute(updatequery, bits)
			else:
				hashlist.add(hashmd5)
				projecthashes.add(hashmd5)			
				bits = (realtitle, hashmd5, project_assess)
				cursor.execute(insertquery, bits)	
	del projecthashes
	db.close()
	
def addRedirects():
	db = MySQLdb.connect(host="sql-s1", read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	query = """INSERT IGNORE INTO u_alexz.redirect_map (rd_hash, target_hash)
		SELECT DISTINCT(MD5(enwiki_p.page.page_title)), u_alexz.%(table)s.hash
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
	cursor = db.cursor()
	f = open('pagelist'+lists, 'ab')
	cursor.execute('SELECT DISTINCT hash FROM '+table)
	while True:
		p = cursor.fetchone()
		if p:
			f.write(p[0]+"\n")
		else:
			break
	f.close()
	cursor.execute('SELECT DISTINCT rd_hash, target_hash FROM redirect_map')
	f = open('redirs'+lists, 'ab')
	while True:
		row = cursor.fetchone()
		if row:
			f.write('%s=%s\n' % (row[0], row[1]))
		else:
			break
	f.close()
	
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
	c2.execute('ALTER TABLE '+table+' DROP INDEX title')
		
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
	
