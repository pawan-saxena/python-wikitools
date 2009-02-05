# -*- coding: utf-8 -*-
from wikitools import *
import threading, urllib, gzip, projectlister, MySQLdb, sys, datetime, re, os, settings, hashlib, calendar, locale
from time import sleep

articletypes = {'unassessed':'{{unassessed-Class}}', 'image':'{{image-Class}}',
	'template':'{{template-Class}}', 'category':'{{category-Class}}', 'disambig':'{{disambig-Class}}',
	'portal':'{{portal-Class}}', 'list':'{{list-Class}}', 'redirect':'{{redirect-Class}}',
	'non-article':'{{NA-Class}}', 'blank':'{{NA-Class}}', 'stub':'{{stub-Class}}', 'start':'{{start-Class}}',
	'C':'{{C-Class}}', 'B':'{{B-Class}}', 'GA':'{{GA-Class}}', 'A':'{{A-Class}}',
	'FL':'{{FL-Class}}', 'FA':'{{FA-Class}}'} # This should cover most instances, some projects have some odd ones

site = wiki.Wiki()
site.login(settings.bot, settings.botpass)
queryreq = []
pagelist = set()
kill = threading.Event()

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
		copyquery = "INSERT INTO popularity_copy SELECT * FROM popularity"
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
		# week=[]  # Override settings
		# cal=[[]]
		# day=1
		# year=2009
		# numfiles = 24*31
		if cal.index(week) == 1 and cal[0].count(0) != 0 or 1==1:
			numfiles += 24 * (7 - cal[0].count(0))
			day = 1
			cursor.execute("TRUNCATE TABLE `popularity`")
			for project in projectlist.keys():
				abbrv = project
				name = projectlist[project][0]
				setupProject(name, abbrv)
		else:
			day = week[0]
		query = 'SELECT DISTINCT hash FROM popularity'
		cursor.execute(query)
		res = cursor.fetchall()
		global pagelist
		for row in res:
			pagelist.add(row[0])
		db.close()
		qh = QueryThread()
		qh.start()
		count = 0
		while True:
			if not os.listdir("Q:/stats/statspages"):
				logMsg("No files ready")
				sleep(10)
			else:
				f = os.listdir("Q:/stats/statspages")[0]
				os.rename("Q:/stats/statspages/"+f, "Q:/stats/inprogress/"+f)
				processPage("Q:/stats/inprogress/"+f)
				count+=1
				if count == numfiles:
					break
		global queryreq 
		logMsg( len(queryreq))
		sleep(10)
		kill.set()
		while qh.isAlive():
			logMsg("Waiting for querythread to stop: "+str(len(queryreq))+" queries remaining")
			sleep(10)
		month = 1
		year = 2009
		if month < 10:
			month =  "0" + str(month)
		else:
			month = str(month)
		if numfiles < 24*7: #there's prolly a better way to do this
			for project in projectlist.keys():
				logMsg("Making table for "+projectlist[project][1])
				query = "SELECT COUNT(*) FROM `popularity` WHERE `project` = %s"
				bits = (project)
				cursor.execute(query, bits)
				pagecount = int(cursor.fetchone()[0])
				limit = "1000"
				if pagecount > 1000:
					headerlimit = "the top 1000 pages"
				else:
					headerlimit = "all "+str(pagecount)+" pages"
				numdays = calendar.monthrange(int(year), int(month))[1]
				listpage = projectlist[project][1]
				target = page.Page(site, listpage)
				header = "This is a list of "+headerlimit+" ordered by number of views in "+calendar.month_name[int(month)]+" in the scope of the "+projectlist[project][0]+" Wikiproject.\n\n"
				header += "The data comes from data published by [[User:Midom|Domas Mituzas]] from Wikipedia's [[Squid (software)|squid]] server logs. "
				header += "Note that due to the use of a different program than http://stats.grok.se/ the numbers here may differ from that site. On average the numbers here are 3-6% higher. For more information, "
				header += "or for a copy of the full data for all pages, leave a message on [[User talk:Mr.Z-man|this talk page]].\n\n"
				header += "==List==\n<!-- Changes made to this section will be overwritten on the next update. Do not change the name of this section. -->"
				header += "\nPeriod: "+str(year)+"-"+str(month)+"-01 &mdash; "+str(year)+"-"+str(month)+"-"+str(numdays)+" (UTC)\n\n"
				table = header + '{| class="wikitable sortable" style="text-align: right;"\n'
				table+= '! Rank\n! Page\n! Views\n! Views (per day average)\n! Assessment\n'
				logMsg( "Table started")
				query = 'SELECT title, hits, assess FROM `popularity` WHERE `project` = %s ORDER BY hits DESC LIMIT %s'
				bits = (project, int(limit))
				cursor.execute(query, bits)
				logMsg( "Query executed")
				result = cursor.fetchall()
				rank = 0
				logMsg( "Beginning loop")
				for record in result:
					rank+=1
					hits = locale.format("%.*f", (0,record[1]), True) # This formats the numbers with comma-thousand separators, its magic or something
					avg = locale.format("%.*f", (0, record[1]/numdays ), True)
					assess = record[2]
					template = articletypes[assess]
					table+= "|-\n"
					table+= "| " + locale.format("%.*f", (0,rank), True) + "\n"
					table+= "| style='text-align: left;' | [[:" + record[0] + "]]\n"
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
				

def processPage(fileloc):	
	lines = 0
	count = 0
	logMsg("Processing "+fileloc)
	file = open(fileloc, 'rb')
	datapage = gzip.GzipFile('', 'rb', 9, file)
	global queryreq
	for line in datapage:
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
				logMsg(fileloc+ " at "+str(count)+" hits")
	file.close()
	datapage.close()
	os.remove(fileloc)
	logMsg(fileloc+ " finished")

def setupProject(project, abbrv):
	logMsg("Setting up "+project)
	hashlist = set()
	db = MySQLdb.connect(host="localhost", user=settings.dbuser, passwd=settings.dbpass, use_unicode=True, charset='utf8')
	cursor = db.cursor()
	cursor.execute("USE `stats`")
	types = ['FA', 'FL', 'A', 'GA', 'B', 'C', 'start', 'stub', 'list', 'image', 'portal', 'category', 'disambig', 'template', 'unassessed', 'blank', 'redirect', 'non-article']
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
			pagee = realtitle.title
			hashmd5 = hashlib.md5(realtitle.title.encode('utf-8').replace(' ', '_').lower()).hexdigest()
			if hashmd5 in hashlist:
				continue
			hashlist.add(hashmd5)
			query = 'INSERT INTO popularity (title, hash, assess, project) VALUES( %s, %s, %s, %s )'
			bits = (pagee, hashmd5, type, abbrv)
			cursor.execute(query, bits)	
		cursor.execute("COMMIT")
	db.close()
	
def logMsg(msg):
	f = open("PopLogFile.txt", 'ab')
	f.write(str(msg)+"\n")
	f.close()

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
				if len(self.ready) == 25 or (kill.isSet() and len(queryreq) == 0):
					cursor.execute("START TRANSACTION")
					r = len(self.ready)
					for x in range(0, r):
						cursor.execute(query, self.ready.pop())
					cursor.execute("COMMIT")
			if kill.isSet() and not self.ready and not queryreq:
				break
	
if __name__ == '__main__':
	startup()
	