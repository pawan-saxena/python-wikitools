# -*- coding: utf-8 -*-
from wikitools import *
import threading, urllib, gzip, projectlister, MySQLdb, sys, datetime, re, httplib, os, settings
from time import sleep
from calendar import monthrange
import hashlib

articletypes = {'unassessed':'{{unassessed-Class}}', 'image':'{{image-Class}}', 'template':'{{template-Class}}', 'category':'{{category-Class}}', 'disambig':'{{disambig-Class}}', 'portal':'{{portal-Class}}', 'list':'{{list-Class}}', 'redirect':'{{redirect-Class}}', 'non-article':'{{NA-Class}}', 'blank':'{{NA-Class}}', 'stub':'{{stub-Class}}', 'start':'{{start-Class}}', 'C':'{{C-Class}}', 'B':'{{B-Class}}', 'GA':'{{GA-Class}}', 'A':'{{A-Class}}', 'FL':'{{FL-Class}}', 'FA':'{{FA-Class}}'} # This should cover most instances, some projects have some odd ones

site = wiki.Wiki()
site.login(settings.bot, settings.botpass)

queryreq = []
pagelist = set()

def startup():
	projectlist = projectlister.getList()
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
	db = MySQLdb.connect(host="localhost", user=settings.dbuser, passwd=settings.dbpass)
	cursor = db.cursor()
	cursor.execute("USE `stats`")
	f = open("PopLogFile.txt", 'wb')
	f.write("")
	f.close()
	day = (datetime.datetime.now()-datetime.timedelta(1)).day
	month = datetime.datetime.now().month
	if month < 10:
		month =  "0" + str(month)
	else:
		month = str(month)
	logMsg("Month is: " + month)
	logMsg("Day is: " + str(day))
	sleep(3)
	year = str(datetime.datetime.now().year)
	if day == 1 or 1==1:
		cursor.execute("TRUNCATE TABLE `popularity`")
		threadqueue = []
		for project in projectlist.keys():
			abbrv = project
			name = projectlist[project][0]
			setupProject(name, abbrv)
	query = 'SELECT DISTINCT hash FROM popularity'
	cursor.execute(query)
	res = cursor.fetchall()
	global pagelist
	for row in res:
		pagelist.add(row[0])
	db.close()
	maxday = monthrange(int(year), int(month))[1]
	hour = 0
	if day < 10:
		sday = "0"+str(day)
	else:
		sday = str(day)
	qh = QueryThread()
	qh.start()
	while True:
		if hour < 10:
			shour = "0"+str(hour)
		else:
			shour = str(hour)
		datapage = year+month+sday+"-"+shour+"0000"
		url = "http://dammit.lt/wikistats/pagecounts-"+datapage+".gz"
		processPage(url)
		hour+=1
		if hour == 24:
			break
	sleep(10)
	qh.kill()
	while qh.isAlive():
		logMsg("Waiting for querythread to stop: "+str(len(queryreq))+" queries remaining")
		sleep(10)
			

def	processPage(url):	
	lines = 0
	count = 0
	logMsg("Downloading "+url)
	conn = httplib.HTTPConnection('dammit.lt')
	testurl = url.split('http://dammit.lt')[1]
	conn.request('HEAD', testurl)
	r1 = conn.getresponse()
	if r1.status == 404:
		url = re.sub("-(\d{2})0000", r"- \1 0001", url)
		url = re.sub(" ", "", url)
		testurl = url.split('http://dammit.lt')[1]
		conn = httplib.HTTPConnection('dammit.lt')
		conn.request('HEAD', testurl)
		r1 = conn.getresponse()
		if r1.status == 404:
			logMsg("Warning: "+url+" seems to be missing")
			return
	conn.close()
	fileloc = "C:/Python25/MediaWiki/statspages/"+url.split('http://dammit.lt/wikistats/')[1]
	f = open(fileloc, 'wb')
	f.close()
	page = urllib.urlretrieve(url, fileloc)
	logMsg("Processing "+url)
	file = open(fileloc, 'rb')
	datapage = gzip.GzipFile('', 'rb', 9, file)
	global queryreq
	for line in datapage:
		lines+=1
		if lines%50000 == 0:
			logMsg(url+ " at "+str(lines)+" lines")
		if not line or not line.startswith('en '):
			if count > 0:
				break
			else:
				continue
		bits = line.split(' ')
		key = hashlib.md5(urllib.unquote(bits[1]).replace(' ', '_').lower()).hexdigest()
		if key in pagelist:
			count+=1
			qbits = (bits[2], key)
			queryreq.append(qbits)
			if count%5000 == 0:
				logMsg(url+ " at "+str(count)+" hits")
	file.close()
	datapage.close()
	os.remove(fileloc)
	logMsg(url+ " finished")

def setupProject(project, abbrv):
	logMsg("Setting up "+project)
	db = MySQLdb.connect(host="localhost", user=settings.dbuser, passwd=settings.dbpass, use_unicode=True, charset='utf8')
	cursor = db.cursor()
	cursor.execute("USE `stats`")
	for type in articletypes.keys():
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
			pagee = realtitle.title
			hashmd5 = hashlib.md5(realtitle.title.encode('utf-8').replace(' ', '_').lower()).hexdigest()
			query = 'INSERT INTO popularity (title, hash, assess, project) VALUES( %s, %s, %s, %s )'
			bits = (pagee, hashmd5, type, abbrv)
			cursor.execute(query, bits)	
		cursor.execute("COMMIT")
	db.close()
	
def logMsg(msg):
	f = open("PopLogFile.txt", 'ab')
	f.write(str(msg))
	f.close()
	print msg

class QueryThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.kill = False
		self.ready = []

	def run(self):
		db = MySQLdb.connect(host="localhost", user=settings.dbuser, passwd=settings.dbpass)
		cursor = db.cursor()
		cursor.execute("USE stats")
		query = 'UPDATE popularity SET hits=hits+%s WHERE hash=%s'
		global queryreq
		while True:
			if queryreq:
				self.ready.append(queryreq.pop())
				if len(self.ready) == 10 or self.kill:
					cursor.execute("START TRANSACTION")
					r = len(self.ready)
					for x in range(0, r):
						cursor.execute(query, self.ready.pop())
					cursor.execute("COMMIT")
			if self.kill and self.size == 0 and not self.ready and not queryreq:
				break
				
	def kill(self):
		self.kill = True
	
if __name__ == '__main__':
	startup()

	