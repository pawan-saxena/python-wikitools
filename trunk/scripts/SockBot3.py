# coding=utf-8
import API
import Wiki
import re
import codecs
import datetime
import time
site = Wiki.Wiki()
print "Logging in"
site.login("username", "password")
userlist = {}
q = re.compile("expiry=\"([^\"]*)\"") # Regex used for getting block expiry
basetime = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) # Instead of getting the base TS for each page, just get the start time of the script
def main():
	try:
		if not site.isLoggedIn("username"): # Make sure we're logged in before doing anything else
			e = open('CrashErrors.txt','w')
			e.write("\Not Logged in\n")
			e.close()
			quit()
	except:
		e = open('CrashErrors.txt','w')
		e.write("\Unable to determine login status\n")
		e.close()
		quit()
	print "Starting..."
	try:
		params = {'action':'query',
			'generator':'categorymembers',
			'gcmtitle':'Category:Temporary Wikipedian userpages',
			'prop':'templates',
			'tlnamespace':'10',
			'tllimit':'5000',
			'gcmlimit':'5000',
			'indexpageids':'1',
		}
		req = API.APIRequest(site, params)
		data = req.query()
	except:
		e = open('CrashErrors.txt','w')
		e.write("\Main API query error\n")
		e.close()
		quit()
	print "Starting checks..."
	if isinstance(data, list):
		for page in data:
			firstchecks(page)
	else:
		firstchecks(data)	
	blockcheck()
	errorlog()
	
def firstchecks(data):
	p = re.compile("(User|User talk):(.*?)\/.*")
	skip = False
	for pageid in data['query']['pageids']:
		try:
			page = data['query']['pages'][pageid]
			title = page['title'].encode('utf-8')
			if page['ns'] != 2 and page['ns'] != 3: # Namespace check, only user [talk] should be in the cat
				removePage(title, "wrong namespace", "")
				skip = True
			if not skip:
				for tem in templates:
					if tem == "Template:Do not delete":
						removePage(title, "{{tl|do not delete}}", "")
						skip = True
						break
			if not skip:
				if title.find('/') != -1:
					username = p.sub(r'\2', title)
				else:
					username = title
					if page.namespace() == 2:
						username = username.replace( "User:", "", 1)
					if page.namespace() == 3:
						username = username.replace( "User talk:", "", 1)
					userlist[username] = title
			skip = False
		except:
			g = codecs.open('ErrorFile.txt','w', 'utf-8')
			g.write('\n')
			g.write('# Unable to check [['+title+']]')
	
def errorlog():
	print "Dumping error log"
	try:
		g = codecs.open('ErrorFile.txt','r', 'utf-8')
		errordump = g.read()
		errorpage = Wiki.Page(site, 'User:Mr.Z-bot/errors')
		errortext = "These are pages that the bot missed for whatever reason:\n"
		errorpage.edit(newtext = errortext + errordump, summary="Reporting errors", minor=True)
		g.close()
	except:
		e = open('CrashErrors.txt','w')
		e.write("\nError dump Error\n")
		e.close()
	try:
		l = codecs.open('LogFile.txt','r', 'utf-8')
		logdump = l.read()
		logpage = Wiki.Page(site, 'User:Mr.Z-bot/log')
		logtext = "These are pages the bot edited and why:\n"
		logpage.edit(logtext + logdump , summary="Edit log", minor=True)
		l.close()
	except:
		e = open('CrashErrors.txt','w')
		e.write("\Log dump Error\n")
		e.close()
	
def blockcheck():
	print "Starting block check"
	usercounter = 0
	userstring = ''
	users = []
	for user in userlist.keys():
		userstring += user+'|'
		users.append(user)
		counter+=1
		if counter == 5000:
			getblocks(userstring, users)
			counter = 0
			userstring = ''
			users = []
	getblocks(userstring, users)
			
def getblocks(userstring, users):
	print "Getting blocks for " + str(len(users)) + " users"
	blockeduserlist = []
	userstring = re.sub('(.*)\|$', r'\1', userstring)
	predata = {'action': 'query',
		'list': 'blocks', 
		'bkusers': userstring, 
		'bklimit':'5000' } 
	req = API.APIRequest(site, predata)
	data = req.query()
	for entry in data['query']['blocks']:
		try:
			blockeduserlist.append(entry['user'])
			if not entry['expiry'] == "infinity":
					date = entry['expiry']
					year = re.search("\d\d\d\d", date).group(0)
					month = re.search("\d\d\d\d-(\d\d)-(\d\d)", date).group(1)
					day = re.search("\d\d\d\d-(\d\d)-(\d\d)", date).group(2)
					date = datetime.date(int(year), int(month), int(day))
					diff = date - date.today()
					if diff.days < 1000:
						removePage(pagelist[entry['user']], "not indef blocked", date)
		except:
			e = open('CrashErrors.txt','w')
			e.write("\BlockDate Error\n"+ page.urlname())
			e.close()
	for user in users:
		try:
			if blockeduserlist.count(user) == 0:
				removePage(pagelist[user], "not blocked", "")
		except:
			e = open('CrashErrors.txt','w')
			e.write("\BlockDate Error\n"+ page.urlname())
			e.close()
		
def removePage(pagename, reason, other):
	g = codecs.open('ErrorFile.txt','w', 'utf-8')
	l = codecs.open('LogFile.txt', 'w', 'utf-8')
	page = Wiki.Page(site, pagename)
	print( page.title + " - " + reason)
	print( other)
	try:
		text = page.getWikiText()
		newtext = re.sub(r'\[\[Category:Temporary Wikipedian userpages.*?\]\]', '', text)
		newtext = newtext.replace('{{legalthreatblock}}', '{{tl|Legalthreatblock}}')
		newtext = newtext.replace('{{Legalthreatblock}}', '{{tl|Legalthreatblock}}')
		# TODO: these can be cut way down with regexes, but I was feeling lazy
		if reason == "{{tl|do not delete}}":
			newtext = newtext.replace('{{Temporary userpage}}', '')
			newtext = newtext.replace('{{Blockedimpersonator}}', '{{Indefblockeduser|historical}}')
			newtext = newtext.replace('{{Blockedtroll}}', '{{Blockedtroll|historical}}')
			newtext = newtext.replace('{{Indefblockeduser-big}}', '{{Indefblockeduser-big|historical}}')
			newtext = newtext.replace('{{Indefblockeduser}}', '{{Indefblockeduser|historical}}')
			newtext = newtext.replace('{{Indefblockuser}}', '{{Indefblockuser|historical}}')
			newtext = newtext.replace('{{Indefblock}}', '{{Indefblock|historical}}')
			newtext = newtext.replace('{{Indefblocked}}', '{{Indefblocked|historical}}')
			newtext = newtext.replace('{{Indef}}', '{{Indef|historical}}')
			newtext = newtext.replace('{{IndefBlocked}}', '{{IndefBlocked|historical}}')
			newtext = newtext.replace('{{Vpblock}}', '{{Vpblock|historical}}')
			newtext = newtext.replace('{{Pagemovevandal}}', '{{Pagemovevandal|historical}}')
			newtext = newtext.replace('{{Pageblankvandal}}', '{{Pageblankvandal|historical}}')
			newtext = newtext.replace('{{Blockedindef}}', '{{Blockedindef|historical}}')
			newtext = newtext.replace('{{Idb}}', '{{Idb|historical}}')
			newtext = newtext.replace('{{Userindef}}', '{{userindef|historical}}')
			newtext = newtext.replace('{{VOAblock}}', '{{VOAblock|historical}}')
		
			newtext = newtext.replace('{{temporary userpage}}', '')
			newtext = newtext.replace('{{blockedimpersonator}}', '{{Indefblockeduser|historical}}')
			newtext = newtext.replace('{{blockedtroll}}', '{{Blockedtroll|historical}}')
			newtext = newtext.replace('{{indefblockeduser-big}}', '{{Indefblockeduser-big|historical}}')
			newtext = newtext.replace('{{indefblockeduser}}', '{{Indefblockeduser|historical}}')
			newtext = newtext.replace('{{indefblockuser}}', '{{Indefblockuser|historical}}')
			newtext = newtext.replace('{{indefblock}}', '{{Indefblock|historical}}')
			newtext = newtext.replace('{{indefblocked}}', '{{Indefblocked|historical}}')
			newtext = newtext.replace('{{indef}}', '{{Indef|historical}}')
			newtext = newtext.replace('{{indefBlocked}}', '{{IndefBlocked|historical}}')
			newtext = newtext.replace('{{vpblock}}', '{{Vpblock|historical}}')
			newtext = newtext.replace('{{pagemovevandal}}', '{{Pagemovevandal|historical}}')
			newtext = newtext.replace('{{pageblankvandal}}', '{{Pageblankvandal|historical}}')
			newtext = newtext.replace('{{blockedindef}}', '{{Blockedindef|historical}}')
			newtext = newtext.replace('{{idb}}', '{{Idb|historical}}')
			newtext = newtext.replace('{{userindef}}', '{{userindef|historical}}')
			newtext = newtext.replace('{{vOAblock}}', '{{VOAblock|historical}}')
		else:
			newtext = newtext.replace('{{Temporary userpage}}', '')
			newtext = newtext.replace('{{Blockedimpersonator}}', '{{Indefblockeduser|historical}}')
			newtext = newtext.replace('{{Blockedtroll}}', '{{Blockedtroll|historical}}')
			newtext = newtext.replace('{{Indefblockeduser-big}}', '{{Indefblockeduser-big|historical}}')
			newtext = newtext.replace('{{Indefblockeduser}}', '{{Indefblockeduser|historical}}')
			newtext = newtext.replace('{{Indefblockuser}}', '{{Indefblockuser|historical}}')
			newtext = newtext.replace('{{Indefblock}}', '{{Indefblock|historical}}')
			newtext = newtext.replace('{{Indefblocked}}', '{{Indefblocked|historical}}')
			newtext = newtext.replace('{{Indef}}', '{{Indef|historical}}')
			newtext = newtext.replace('{{IndefBlocked}}', '{{IndefBlocked|historical}}')
			newtext = newtext.replace('{{Vpblock}}', '{{Vpblock|historical}}')
			newtext = newtext.replace('{{Pagemovevandal}}', '{{Pagemovevandal|historical}}')
			newtext = newtext.replace('{{Pageblankvandal}}', '{{Pageblankvandal|historical}}')
			newtext = newtext.replace('{{Blockedindef}}', '{{Blockedindef|historical}}')
			newtext = newtext.replace('{{Idb}}', '{{Idb|historical}}')
			newtext = newtext.replace('{{Userindef}}', '{{userindef|historical}}')
			newtext = newtext.replace('{{VOAblock}}', '{{VOAblock|historical}}')
			
			newtext = newtext.replace('{{temporary userpage}}', '')
			newtext = newtext.replace('{{blockedimpersonator}}', '{{Indefblockeduser|historical}}')
			newtext = newtext.replace('{{blockedtroll}}', '{{Blockedtroll|historical}}')
			newtext = newtext.replace('{{indefblockeduser-big}}', '{{Indefblockeduser-big|historical}}')
			newtext = newtext.replace('{{indefblockeduser}}', '{{Indefblockeduser|historical}}')
			newtext = newtext.replace('{{indefblockuser}}', '{{Indefblockuser|historical}}')
			newtext = newtext.replace('{{indefblock}}', '{{Indefblock|historical}}')
			newtext = newtext.replace('{{indefblocked}}', '{{Indefblocked|historical}}')
			newtext = newtext.replace('{{indef}}', '{{Indef|historical}}')
			newtext = newtext.replace('{{indefBlocked}}', '{{IndefBlocked|historical}}')
			newtext = newtext.replace('{{vpblock}}', '{{Vpblock|historical}}')
			newtext = newtext.replace('{{pagemovevandal}}', '{{Pagemovevandal|historical}}')
			newtext = newtext.replace('{{pageblankvandal}}', '{{Pageblankvandal|historical}}')
			newtext = newtext.replace('{{blockedindef}}', '{{Blockedindef|historical}}')
			newtext = newtext.replace('{{idb}}', '{{Idb|historical}}')
			newtext = newtext.replace('{{userindef}}', '{{userindef|historical}}')
			newtext = newtext.replace('{{vOAblock}}', '{{VOAblock|historical}}')
		
			if not(newtext == text):
				try:
					#page.edit(newtext=newtext, summary="Removing Temporary userpage category", minor=True, bot=True, basetime=basetime)
					l.write('\n')
					l.write('# [[' + page.title + ']] — ' + reason + ' ~~~~~')
				#except SpamfilterError:
				except:
					g.write('\n')
					g.write('# [['+page.title+']]  Spam filter error')
					print( "ERROR on: " + page.title)
			else:
				g.write('\n')
				g.write('# [['+page.title+']]  No change detected')
				print( "ERROR on: " + page.title)
	except:
		e = open('CrashErrors.txt','w')
		e.write("\nEdit Error\n"+ page.title)
		e.close()
	g.close()   
 
if __name__ == '__main__':
    try:
        main()
    finally:
        quit()
