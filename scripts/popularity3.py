#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import cPickle as pickle
import datetime
import urllib
import httplib
import gzip
import hashlib
import MySQLdb
import sys
import projectlister
from wikitools import wiki, page
import settings
import calendar

articletypes = {'unassessed':'{{unassessed-Class}}', 'image':'{{image-Class}}',
	'template':'{{template-Class}}', 'category':'{{category-Class}}', 'disambig':'{{disambig-Class}}',
	'portal':'{{portal-Class}}', 'list':'{{list-Class}}',
	'non-article':'{{NA-Class}}', 'blank':'{{NA-Class}}', 'stub':'{{stub-Class}}', 'start':'{{start-Class}}',
	'C':'{{C-Class}}', 'B':'{{B-Class}}', 'GA':'{{GA-Class}}', 'A':'{{A-Class}}',
	'FL':'{{FL-Class}}', 'FA':'{{FA-Class}}'} # This should cover most instances, some projects have some odd ones

class HitsDict():
	def __init__(self, args={}):
		self.vals = []
		self.keydict = {}
		
	def setkeypair(self, curkey, newkey):
		if not curkey in self.keydict:
			return
		self.keydict[newkey] = self.keydict[curkey]
		
	def __getitem__(self, key):
		return self.vals[self.keydict[key]]
	
	def __setitem__(self, key, value):
		if key in self.keydict:
			self.vals[self.keydict[key]] = value
		else:
			self.vals.append(value)
			self.keydict[key] = len(self.vals)-1
		
	def __delitem__(self, key):
		return NotImplemented
	
	def __contains__(self, key):
		return key in self.keydict
	
	def keys(self):
		return self.keydict.keys()
		
	def values(self):
		return self.keydict.keys()	

# Manual run options:
# * --setup - runs setup
# * --make-tables - makes the result tables and saves them to the wiki
# * --manual=page - manually run the given datapage
	
hitcount = HitsDict()
site = wiki.Wiki()
site.login(settings.bot, settings.botpass)

def main():
	os.chdir('/home/alexz/popularity/')
	lock()
	manual = False
	if len(sys.argv[1]) > 1 and sys.argv[1].startswith('--manual'):
		manual = True
		manualfile = sys.argv[1].split('=')[1]
		try:
			dt = datetime.datetime.strptime(manualfile, 'pagecounts-%Y%m%d-%H0000.gz')
		except:
			dt = datetime.datetime.strptime(manualfile, 'pagecounts-%Y%m%d-%H0001.gz')
		dp = dt.strftime('%b%y')
	now = datetime.datetime.utcnow()
	now = now.replace(minute = 0, second=0, microsecond=0)
	todo = (now - datetime.timedelta(hours=1))
	if not manual:
		dp = todo.strftime('%b%y')
	p = open('pages/%s.dat' % dp, 'r')
	pages = pickle.load(p)
	p.close()
	for item in pages:
		hitcount[item] = 0
	del pages
	r = open('redirects/%s.dat' % dp, 'r')
	redirects = pickle.load(r)
	r.close()
	for item in redirects.keys():
		hitcount.setkeypair(redirects[item], item)
	del redirects
	if manual:
		processPage(manualfile)
		addResults(dt)
		unlock()
		return
	l = open('lastrun.dat', 'r')
	last = pickle.load(l)
	l.close()
	if (todo - last).seconds > 3600 or (todo-last).days:
		files = handleMissedRun(todo, last)
	else:
		files = [getFile(todo)]
	for f in files:
		processPage(f)
	addResults(todo)
	l = open('lastrun.dat', 'w')
	pickle.dump(todo, l, pickle.HIGHEST_PROTOCOL)
	l.close()
	unlock()
	next = todo + datetime.timedelta(hours=1)
	if next.month != todo.month:
		makeResults(todo)

def processPage(filename):	
	started = False
	hashlist = set(hitcount.keys())
	datapage = gzip.open(filename, 'rb')
	for line in datapage:
		if not line or not line.startswith('en '):
			if started:
				break
			else:
				continue
		started = True
		bits = line.split(' ')		
		key = hashlib.md5(urllib.unquote(bits[1]).replace(' ', '_')).hexdigest()
		if key in hashlist:
			hitcount[key] += int(bits[2])
	datapage.close()
	#os.remove(filename)
	
def handleMissedRun(cur, last):
	if cur.month != last.month:
		raise Exception("Missed runs span across months, do it manually!")
	hours = (cur-last).seconds/3600
	hours += (cur-last).days * 24
	files = []
	for x in range(0, hours):
		date = cur - datetime.timedelta(hours=x)
		files.append(getFile(date))
	return files
	
def getFile(date):
	page = date.strftime('pagecounts-%Y%m%d-%H0000.gz')
	altpage = date.strftime('pagecounts-%Y%m%d-%H0001.gz')
	url = "http://dammit.lt"
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
	conn = httplib.HTTPConnection('dammit.lt')
	conn.request('HEAD', testurl)
	r = conn.getresponse()
	if r.status == 404 or r.status == 500:
		conn.close()
		return False
	else:
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
	table = date.strftime('pop_%b%y')
	hits = {}
	dp = date.strftime('%b%y')
	p = open('pages/%s.dat' % dp, 'r')
	pages = pickle.load(p)
	p.close()
	c.execute("START TRANSACTION")
	for hash in pages:
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
	c.execute("COMMIT")
	db.close()
	
def lock():
	lock = open('pop.lock', 'r')
	l = lock.readline().split('\n')[0]
	if l != '0':
		os.system('ps -Fp '+l)
		raise Exception("Other process still running")
	lock = open('pop.lock', 'w')
	lock.write(str(os.getpid()))
	lock.close()
	
def unlock():	
	lock = open('pop.lock', 'w')
	lock.write('0')
	lock.close()
	
def makeResults(date):
	projectlist = projectlister.projects
	month = date.month
	year = date.year
	numdays = calendar.monthrange(year, month)[1]
	table = date.strftime('pop_%b%y')
	db = MySQLdb.connect(host="sql", db='u_alexz', read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	for project in projectlist.keys():
		listpage = projectlist[project][1]
		target = page.Page(site, listpage)
		section = 0
		if target.exists:
			section = 1
		header = "This is a list of the top 1000 (or all) pages ordered by number of views in the scope of the "+projectlist[project][0]+" Wikiproject.\n\n"
		header += "The data comes from data published by [[User:Midom|Domas Mituzas]] from Wikipedia's [[Squid (software)|squid]] server logs. "
		header += "Note that due to the use of a different program than http://stats.grok.se/ the numbers here may differ from that site. For more information, "
		header += "or for a copy of the full data for all pages, leave a message on [[User talk:Mr.Z-man|this talk page]].\n\n"
		header += "'''Note:''' This data aggregates the views for all redirects to each page.\n\n"
		header += "==List==\n<!-- Changes made to this section will be overwritten on the next update. Do not change the name of this section. -->"
		header += "\nPeriod: "+str(year)+"-"+str(month)+"-01 &mdash; "+str(year)+"-"+str(month)+"-"+str(numdays)+" (UTC)\n\n"
		if not section:
			table = header + '{| class="wikitable sortable" style="text-align: right;"\n'
		else:
			table = "==List==\n<!-- Changes made to this section will be overwritten on the next update. Do not change the name of this section. -->"
			table += "\nPeriod: "+str(year)+"-"+str(month)+"-01 &mdash; "+str(year)+"-"+str(month)+"-"+str(numdays)+" (UTC)\n\n"
			table += '{| class="wikitable sortable" style="text-align: right;"\n'
		table+= '! Rank\n! Page\n! Views\n! Views (per day average)\n! Assessment\n'
		query = "SELECT title, hits, project_assess FROM `"+table+"` WHERE project_assess LIKE \"%'"+project+"'%\" ORDER BY hits DESC LIMIT 1000"
		cursor.execute(query)
		result = cursor.fetchall()
		rank = 0
		for record in result:
			rank+=1
			hits = locale.format("%.*f", (0,record[1]), True)
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
		table += "|}"
		res = target.edit(newtext=table, summary="Popularity stats for "+projectlist[project][0]+" project", section=str(section))
		if 'new' in res['edit']:
			notifyProject(target)
			
def notifyProject(p):
	project = p.title.rsplit('/', 1)[0]
	project = page.Page(site, project)
	talk = project.toggleTalk()
	text = '\n{{subst:User:Mr.Z-man/np|%s}}' % p.title
	summary = '/* Pageview stats */ new section'
	talk.edit(appendtext=text, summary=summary)
	
def setup():
	os.chdir('/home/alexz/popularity/')
	projectlist = projectlister.projects
	makeTempTables()
	for project in projectlist.keys():
		abbrv = project
		name = projectlist[project][0]
		setupProject(name, abbrv)
	addRedirects()
	makeDataPages()
	moveTables()
	
def makeTempTables():
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	db = MySQLdb.connect(host="sql-s1", db='u_alexz', read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	cursor.execute("DROP TABLE %s" % table)
	cursor.execute("DROP TABLE redirect_map")
	query1 = """CREATE TABLE `%s` (
		`title` varchar(255) collate latin1_bin NOT NULL,
		`hash` varchar(32) NOT NULL,
		`hits` int(10) NOT NULL default '0',
		`project_assess` blob NOT NULL,
		UNIQUE KEY `title` (`title`),
		UNIQUE KEY `hash` (`hash`),
		KEY `project_asssess_hits` (`hits`,`project_assess`(767))
		) ENGINE=InnoDB ROW_FORMAT=DYNAMIC;""" % (table)
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
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	db = MySQLdb.connect(host="sql-s1", read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	projecthashes = set()
	types = ['FA', 'FL', 'A', 'GA', 'B', 'C', 'start', 'stub', 'list', 'image', 'portal', 'category', 'disambig', 'template', 'unassessed', 'blank', 'non-article']
	insertquery = 'INSERT INTO u_alexz.'+table+' (title, hash, project_assess) VALUES( %s, %s, %s )'
	updatequery = 'UPDATE u_alexz.'+table+' SET project_assess=CONCAT(project_assess,",",%s) WHERE hash=%s'
	selectquery = 'SELECT page_namespace,page_title FROM enwiki_p.page JOIN enwiki_p.categorylinks ON page_id=cl_from WHERE cl_to=%s'
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
		cursor.execute("START TRANSACTION")
		for title in pagesincat:			
			if not title[0]%2 == 1:
				continue
			realtitle = title[1].decode('utf8').encode('utf8')
			hashmd5 = hashlib.md5(realtitle).hexdigest()
			if hashmd5 in projecthashes:
				continue
			project_assess = "'%s':'%s'" % (abbrv, type)
			if hashmd5 in hashlist:
				bits = (project_assess, hashmd5)
				cursor.execute(updatequery, bits)
			else:
				hashlist.add(hashmd5)
				projecthashes.add(hashmd5)			
				bits = (realtitle, hashmd5, project_assess)
				cursor.execute(insertquery, bits)	
		cursor.execute("COMMIT")
	del projecthashes
	db.close()
	
def addRedirects():
	db = MySQLdb.connect(host="sql-s1", read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	date = datetime.datetime.utcnow()+datetime.timedelta(days=15)	
	table = date.strftime('pop_%b%y')
	query = """INSERT INTO u_alexz.redirect_map (rd_hash, target_hash)
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
	db = MySQLdb.connect(host="sql-s1", db='u_alexz', read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	dp = date.strftime('%b%y.dat')
	pages = set()
	cursor.execute('SELECT DISTINCT hash FROM '+table)
	while True:
		p = cursor.fetchone()
		if p:
			pages.add(p[0])
		else:
			break
	f = open('pages/'+dp, 'wb')
	pickle.dump(pages, f, pickle.HIGHEST_PROTOCOL)
	del pages
	f.close()
	rds = {}
	cursor.execute('SELECT DISTINCT rd_hash, target_hash FROM redirect_map')
	while True:
		row = cursor.fetchone()
		if row:
			rds[row[0]] = row[1]
		else:
			break
	f = open('redirects/'+dp, 'wb')
	pickle.dump(rds, f, pickle.HIGHEST_PROTOCOL)
	del rds
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
		
if __name__ == '__main__':
	if len(sys.argv[1]) > 1 and sys.argv[1] == '--setup':
		setup()
	elif len(sys.argv[1]) > 1 and sys.argv[1] == '--make-tables':
		month = int(raw_input('Month: '))
		year = int(raw_input('Year: '))
		d = datetime.datetime(month=month, year=year, day=1)
		makeResults(d)
	else:
		main()
	