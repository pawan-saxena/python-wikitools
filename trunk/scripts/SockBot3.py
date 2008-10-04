# coding=utf-8
import API
import Wiki
import re
import codecs
import sys
import simplejson
import urllib
import datetime
import socket
import time
site = Wiki.Wiki()
site.login("username", "password")
def main():
	try:
		skip = 0
		if not site.isLoggedIn("username"): # Make sure we're logged in before doing anything else
			e = open('C:\Users\Alex\Desktop\CrashErrors.txt','w')
			e.write("\Not Logged in\n")
			e.close()
			quit()
		gen = getCat('Category:Temporary Wikipedian userpages')
		q = re.compile("expiry=\"([^\"]*)\"") # Regex used for getting block expiry
		userlist = ''
		isfirst = True
		pagelist = {}
		p = re.compile("(User|User_talk):(.*?)\/.*")
	except:
		e = open('C:\Users\Alex\Desktop\CrashErrors.txt','w')
		e.write("\nSetup Error\n")
		e.close()
		quit()
	for page in pagegenerators.PreloadingGenerator(gen, pageNumber = 500):
		try:
			if page.namespace() != 2 and page.namespace() != 3: # Namespace check, only user (talk) should be in the cat
				removePage(page, "wrong namespace", "")
				skip = 1
			if skip != 1:
				templates = page.templates()
				for j in templates:
					if j == "Do not delete":
						removePage(page, "{{tl|do not delete}}", "")
						skip = 1
						break
			if skip != 1:
				if page.title().find('/') != -1:
					username = p.sub(r'\2', page.title() )
				else:
					username = page.title()
					if page.namespace() == 2:
						username = username.replace( "User:", "", 1)
					if page.namespace() == 3:
						username = username.replace( "User talk:", "", 1)
					if isfirst:
						userlist = username
						pagelist[username] = page
						isfirst = False
					else:
						userlist+= "|" + username
						fulluserlist.append(username)
						pagelist[username] = page


						print "Getting block info for 250 users"
						predata = urllib.urlencode({'action': 'query', 'list': 'blocks', 'format': 'json', 'bkusers': userlist, 'bklimit':'500' }) #For some reason the POST isn't working, may just use a GET, need to check URL character limit first
						print predata
						try:
							stuff = urllib.urlopen('http://en.wikipedia.org/w/api.php', predata)
							json = stuff.read()
							print json
						except wikipedia.ServerError:
							print "Server error"
							return
						try:
							data = simplejson.loads(json)
						except ValueError:
							wikipedia.output(u'Warning! %s is defined but does not exist!' % site)
							return
						try:
							for entry in data['query']['blocks']:
								blockeduserlist.append(entry['user'])
								if not entry['expiry'] == "infinity":
										date = entry['expiry']
										year = re.search("\d\d\d\d", date).group(0)
										month = re.search("\d\d\d\d-(\d\d)-(\d\d)", date).group(1)
										day = re.search("\d\d\d\d-(\d\d)-(\d\d)", date).group(2)
										date = datetime.date(int(year), int(month), int(day))
										diff = date - date.today()
										if diff.days < 1000:
											page = wikipedia.Page(site, pagelist[entry['user']])
											removePage(page, "not indef blocked", date)
							for user in fulluserlist:
								if blockeduserlist.count(user) == 0:
									removePage(user, "not blocked", "")
						except:
							print "Error"
			skip = 0
		except:
			e = open('C:\Users\Alex\Desktop\CrashErrors.txt','w')
			e.write("\nFilter Error\n"+ page.urlname())
			e.close()
	try:
		g = open('ErrorFile.txt','r')
		errordump = g.read()
		errorpage = wikipedia.Page(site, 'User:Mr.Z-bot/errors')
		errortext = "These are pages that the bot missed for whatever reason:\n"
		errorpage.put(errortext + errordump, comment="Reporting error")
		g.close()
	except:
		e = open('C:\Users\Alex\Desktop\CrashErrors.txt','w')
		e.write("\nError dump Error\n")
		e.close()
	try:
		l = open('LogFile.txt','r')
		logdump = l.read()
		logpage = wikipedia.Page(site, 'User:Mr.Z-bot/log')
		logtext = logpage.get()
		date = datetime.date(2000, 12, 12)
		if date.today().day == 1:
			logtext = "These are pages the bot edited and why:\n"
		logpage.put(logtext + logdump , comment="Edit log")
		l.close()
	except:
		e = open('C:\Users\Alex\Desktop\CrashErrors.txt','w')
		e.write("\Log dump Error\n")
		e.close()
		
def removePage(page, reason, other):
	g = codecs.open('ErrorFile.txt','w', 'utf-8')
	l = codecs.open('LogFile.txt', 'w', 'utf-8')
	print( page.title() + " - " + reason)
	print( other)
	try:
		if page.canBeEdited():
			text = page.get()
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
					#page.put(newtext, comment="Removing Temporary userpage category", force=True)
					l.write('\n')
					l.write('# [[' + page.title() + ']] — ' + reason + ' ~~~~~')
				except SpamfilterError:
					g.write('\n')
					g.write('# [['+page.title()+']]  Spam filter error')
					print( "ERROR on: " + page.title())
			else:
				g.write('\n')
				g.write('# [['+page.title()+']]  No change detected')
				print( "ERROR on: " + page.title())
		else:
			g.write('\n')
			g.write('# [['+page.title()+']]  Page protected')
			print( "ERROR on: " + page.title())
	except:
		e = open('C:\Users\Alex\Desktop\CrashErrors.txt','w')
		e.write("\nEdit Error\n"+ page.urlname())
		e.close()
	g.close()

def getCat(cat):   
	cmcont = False
	while True:
		predata = {'action': 'query',
			'query': 'list',
			'list': 'categorymembers',
			'cmtitle': cat,
			'cmlimit': '5000',
			'format': 'json'}
		if cmcont != False:
			predata['cmcontinue'] = cmcont
		try:
			req = API.APIRequest(site, predata)
			data = req.query(False)
		try:
			for page in data['query']['categorymembers']:
				counter+=1
			if counter == int(counter/5000)*5000:
				print counter
				yield Wiki.Page(site, page['title'], False, False)
		try:
			cmcont = data['query-continue']['categorymembers']['cmcontinue']
		except:
			break     
 
if __name__ == '__main__':
    try:
        main()
    finally:
        wikipedia.stopme()
