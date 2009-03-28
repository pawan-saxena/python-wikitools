#!/usr/bin/python
# -*- coding: utf-8 -*-
from wikitools import *
import re
import codecs
import datetime
import settings
import os
import MySQLdb

site = wiki.Wiki()
IPs = {}
removed = set()
print "Logging in"
site.login(settings.bot, settings.botpass)
l = codecs.open('LogFile.txt', 'wb', 'utf-8')
l.close()
g = codecs.open('ErrorFile.txt','wb', 'utf-8')
g.close()
dl = codecs.open('DelLogFile.txt', 'wb', 'utf-8')
dl.close()
de = codecs.open('DelErrorFile.txt','wb', 'utf-8')
de.close()
titlewhitelist = ["Category:Wikipedians who are indefinitely blocked for spamming"]
spamcats = ['User_talk_pages_with_Uw-spam1_notices',
'User_talk_pages_with_Uw-spam2_notices',
'User_talk_pages_with_Uw-spam3_notices',
'User_talk_pages_with_Uw-spam4_notices',
'User_talk_pages_with_Uw-spam4im_notices',
'User_talk_pages_with_Uw-advert1_notices',
'User_talk_pages_with_Uw-advert2_notices',
'User_talk_pages_with_Uw-advert3_notices',
'User_talk_pages_with_Uw-advert4_notices',
'User_talk_pages_with_Uw-advert4im_notices',
'User_talk_pages_with_Uw-coi_notices',
'User_talk_pages_with_Uw-affiliate_notices',
'User_talk_pages_with_Spam-warn_notices',
'Wikipedians_who_are_indefinitely_blocked_for_link-spamming',
'Wikipedians_who_have_temporarily_been_blocked_for_link-spamming',
'Wikipedians_who_have_temporarily_been_blocked_for_advertising',
'Wikipedians_who_are_indefinitely_blocked_for_advertising',
'Wikipedians_who_are_indefinitely_blocked_for_promotional_user_names',
'Now_unused_spammer_talk_page_categories',
'Wikipedians_who_are_indefinitely_blocked_with_uw-soablock_notices',
'Wikipedians_who_are_indefinitely_blocked_for_spamming',
'Wikipedians_who_have_temporarily_been_blocked_for_spamming',
]

db = MySQLdb.connect(db='enwiki_p', host="sql-s1", read_default_file="/home/alexz/.my.cnf")
cursor = db.cursor()

def main():
	try:
		logincheck(settings.bot)
		print "Starting..."
		queries()
		handleIPs()
		deletePages()
		errorlog()
		os.remove('LogFile.txt')
		os.remove('ErrorFile.txt')
		os.remove('DelErrorFile.txt')
		os.remove('DelLogFile.txt')			
	except:
		import traceback
		traceback.print_exc()

def handleIPs():
	print "Removing IP pages"
	if not IPs:
		return
	query = "SELECT ipb_expiry FROM ipblocks WHERE ipb_address=%s AND ipb_auto=0 AND ipb_user=0"
	for IP in IPs:
		cursor.execute(query, IP)
		try:
			time = cursor.fetchone()[0]
		except:
			time = False
		if time != 'infinity':
			removePage(IPs[IP], "IP page")
		else:
			(userpage, content) = removePage(IPs[IP], "IP page", "", save=False)
			if not userpage:
				continue
			content += '\n\n[[Category:Indefinitely blocked IP addresses]]'
			try:
				userpage.edit(newtext=content, summary="Removing Temporary userpage category, adding indef blocked IPs category", minor=True, bot=True, basetime=userpage.lastedittime)
				print(userpage.title + " - Indef blocked IP")
				l = codecs.open('LogFile.txt', 'ab', 'utf-8')
				l.write('\n# [[' + userpage.title + ']] - Indef blocked IP')
				l.close()
			except api.APIError, (code, errortext):
				if code == 'protectedpage':
					reportError(userpage, "Page protected")
				else:
					reportError(userpage, errortext)	

def deletePages():
	site.login(settings.adminbot, settings.adminbotpass)
	logincheck(settings.adminbot)
	print "Deleting old pages..."
	global removed
	log = []
	ts = datetime.datetime.utcnow() - datetime.timedelta(days=30)
	ts = long(ts.strftime('%Y%m%d%H%M%S'))
	query = """SELECT page_namespace,page_title,page_id FROM page
		JOIN revision ON rev_page=page_id AND rev_id=page_latest
		JOIN categorylinks ON cl_from=page_id 
		WHERE cl_to="Temporary_Wikipedian_userpages" AND CAST(rev_timestamp AS UNSIGNED) < %s"""
	cursor.execute(query, ts)
	result = set(cursor.fetchall())
	for res in result:
		userpage = page.Page(site, title=res[1], check=False, followRedir=False, pageid=int(res[2]))
		userpage.setNamespace(res[0])
		if int(userpage.pageid) in removed:
			continue
		userpage.setPageInfo()
		try:
			print("Deleting "+ userpage.title)
		except:
			print("Deleting" + userpage.pageid)
		try:
			userpage.delete(reason="Old [[CAT:TEMP|temporary userpage]]")
			dl = codecs.open('DelLogFile.txt', 'ab', 'utf-8')
			dl.write('\n# [[' + userpage.title.decode('utf8') + ']]')
			dl.close()
		except api.APIError, e:
			reportError(userpage, "Deletion error: "+e['error']['code'], True)
		
def queries():
	print "Doing namespace check"
	query = """SELECT page_namespace,page_title,page_id FROM page 
		JOIN categorylinks ON cl_from=page_id 
		WHERE page_namespace<2 AND page_namespace>3 AND cl_to='Temporary_Wikipedian_userpages'"""
	doQuery(query, "wrong namespace")
	
	print "Getting IP addresses"
	query = """SELECT page_namespace,page_title,page_id FROM page 
		JOIN categorylinks ON cl_from=page_id 
		WHERE cl_to="Temporary_Wikipedian_userpages" 
		AND page_title RLIKE "^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$" """
	cursor.execute(query)
	while True:
		res = cursor.fetchone()
		if not res:
			 break
		userpage = page.Page(site, title=res[1], check=False, followRedir=False, pageid=int(res[2]))
		userpage.setNamespace(res[0])
		IPs[res[1]] = res
		removed.add(int(res[2]))
	
	print "Checking for {{Do not delete}}"
	query = """SELECT page_namespace,page_title,page_id FROM page 
		JOIN categorylinks ON page_id=cl_from 
		JOIN templatelinks ON page_id=tl_from 
		WHERE cl_to="Temporary_Wikipedian_userpages" AND tl_title="Do_not_delete" AND tl_namespace=10"""
	doQuery(query, "{{tl|do not delete}}")	
	query = """SELECT page1.page_namespace,page1.page_title,page1.page_id FROM page AS page1 
		JOIN categorylinks ON cl_from=page1.page_id 
		JOIN page AS page2 ON page1.page_title=page2.page_title 
		JOIN templatelinks ON tl_from=page2.page_id 
		WHERE page2.page_namespace=2 AND tl_namespace=10 AND tl_title="Do_not_delete" AND page1.page_namespace=3 AND cl_to="Temporary_Wikipedian_userpages" """
	doQuery(query, "{{tl|do not delete}} on userpage")
	
	print "Doing block checks"
	year1 = datetime.datetime.now().year
	years = '|'.join([str(year1),str(year1+1),str(year1+2),str(year1+3)])
	query = """SELECT page_namespace,page_title,page_id FROM page 
		JOIN categorylinks ON page_id=cl_from 
		JOIN user ON REPLACE(SUBSTRING_INDEX(page_title,'/',1),'_',' ')=user_name 
		JOIN ipblocks ON user_id=ipb_user 
		WHERE cl_to="Temporary_Wikipedian_userpages" AND ipb_expiry != 'infinity' AND ipb_expiry RLIKE "("""+years+""").*" """
	doQuery(query, "not indef blocked")
	
	query = """SELECT page_namespace,page_title,page_id FROM page 
		JOIN categorylinks ON page_id=cl_from 
		JOIN user ON user_name=REPLACE(SUBSTRING_INDEX(page_title,'/',1),'_',' ') 
		WHERE cl_to="Temporary_Wikipedian_userpages" 
		AND NOT EXISTS (SELECT ipb_id FROM ipblocks WHERE ipb_user=user_id)"""
	doQuery(query, "not blocked")
	
	print "Doing spam cat check"
	catlist = '"'+'","'.join(spamcats)+'"'
	query = """SELECT page_namespace,page_title,page_id FROM page
		JOIN categorylinks ON cl_from=page_id 
		WHERE cl_to="Temporary_Wikipedian_userpages" 
		AND page_id IN 
			(SELECT cl_from FROM categorylinks 
				WHERE cl_to IN ("""+catlist+"""))"""
	doQuery(query, "page in spam category")

def doQuery(query, reason):
	cursor.execute(query)
	while True:
		res = cursor.fetchone()
		if not res:
			 break
		removePage(res, reason)
		
def errorlog():
	site.login(settings.bot, settings.botpass)
	logincheck(settings.bot)
	print "Dumping error log"
	g = codecs.open('ErrorFile.txt','rb', 'utf-8')
	errordump = g.read().encode('utf8')
	errorpage = page.Page(site, "User:"+settings.bot+'/errors')
	errortext = "These are pages that the bot missed for whatever reason:\n"
	errorpage.edit(newtext = errortext + errordump, summary="Reporting errors", minor=True)
	g.close()

	print "Dumping edit log"
	l = codecs.open('LogFile.txt','rb', 'utf-8')
	logdump = l.read().encode('utf8')
	logpage = page.Page(site, "User:"+settings.bot+'/log')
	logtext = "These are pages the bot edited and why:\n"
	logpage.edit(text=logtext + logdump , summary="Edit log", minor=True)
	l.close()
	
	site.login(settings.adminbot, settings.adminbotpass)
	logincheck(settings.adminbot)
	print "Dumping deletion error log"
	de = codecs.open('DelErrorFile.txt','rb', 'utf-8')
	logdump = de.read().encode('utf8')
	logpage = page.Page(site, "User:"+settings.adminbot+'/errors')
	logtext = "These are pages deletion failed on:\n"
	logpage.edit(text=logtext + logdump , summary="Error log", minor=True)
	de.close()
	
	print "Dumping delete log"
	dl = codecs.open('DelLogFile.txt','rb', 'utf-8')
	logdump = dl.read().encode('utf8')
	logpage = page.Page(site, "User:"+settings.adminbot+'/log')
	logtext = "These are pages the bot deleted on the last run:\n"
	logpage.edit(text=logtext + logdump , summary="Log", minor=True)
	dl.close()
	
def removePage(res, reason, other=False, save=True):
	global removed
	if int(res[2]) in removed and not (res[1] in IPs and reason == "IP page"):
		return (False, False)
	userpage = page.Page(site, title=res[1], check=False, followRedir=False, pageid=int(res[2]))
	userpage.setNamespace(res[0])
	removed.add(int(res[2]))
	if userpage.title in titlewhitelist:
		return (False, False)
	if save:
		try:
			print(userpage.title + " - " + reason)
		except:
			print(userpage.pageid + " - " + reason)
		if other:
			print(other)
	text = userpage.getWikiText()
	newtext = re.sub(r'\[\[Category:Temporary Wikipedian userpages.*?\]\]', '', text)
	# TODO: these can be cut way down with regexes, but I was feeling lazy
	newtext = newtext.replace('{{legalthreatblock}}', '{{tl|Legalthreatblock}}')
	newtext = newtext.replace('{{Legalthreatblock}}', '{{tl|Legalthreatblock}}')
	newtext = newtext.replace('{{Temporary userpage}}', '')
	newtext = newtext.replace('{{Blockedimpersonator}}', '{{tl|Indefblockeduser}}')
	newtext = newtext.replace('{{Blockedtroll}}', '{{tl|Blockedtroll}}')
	newtext = newtext.replace('{{Indefblockeduser-big}}', '{{tl|Indefblockeduser-big}}')
	newtext = newtext.replace('{{Indefblockeduser}}', '{{tl|Indefblockeduser}}')
	newtext = newtext.replace('{{Indefblockuser}}', '{{tl|Indefblockuser}}')
	newtext = newtext.replace('{{Indefblock}}', '{{tl|Indefblock}}')
	newtext = newtext.replace('{{Indefblocked}}', '{{tl|Indefblocked}}')
	newtext = newtext.replace('{{Indef}}', '{{tl|Indef}}')
	newtext = newtext.replace('{{IndefBlocked}}', '{{tl|IndefBlocked}}')
	newtext = newtext.replace('{{Vpblock}}', '{{tl|Vpblock}}')
	newtext = newtext.replace('{{Pagemovevandal}}', '{{tl|Pagemovevandal}}')
	newtext = newtext.replace('{{Pageblankvandal}}', '{{tl|Pageblankvandal}}')
	newtext = newtext.replace('{{Blockedindef}}', '{{tl|Blockedindef}}')
	newtext = newtext.replace('{{Idb}}', '{{tl|Idb}}')
	newtext = newtext.replace('{{Userindef}}', '{{tl|userindef}}')
	newtext = newtext.replace('{{VOAblock}}', '{{tl|VOAblock}}')
	
	newtext = newtext.replace('{{temporary userpage}}', '')
	newtext = newtext.replace('{{blockedimpersonator}}', '{{tl|Indefblockeduser}}')
	newtext = newtext.replace('{{blockedtroll}}', '{{tl|Blockedtroll}}')
	newtext = newtext.replace('{{indefblockeduser-big}}', '{{tl|Indefblockeduser-big}}')
	newtext = newtext.replace('{{indefblockeduser}}', '{{tl|Indefblockeduser}}')
	newtext = newtext.replace('{{indefblockuser}}', '{{tl|Indefblockuser}}')
	newtext = newtext.replace('{{indefblock}}', '{{tl|Indefblock}}')
	newtext = newtext.replace('{{indefblocked}}', '{{tl|Indefblocked}}')
	newtext = newtext.replace('{{indef}}', '{{tl|Indef}}')
	newtext = newtext.replace('{{indefBlocked}}', '{{tl|IndefBlocked}}')
	newtext = newtext.replace('{{vpblock}}', '{{tl|Vpblock}}')
	newtext = newtext.replace('{{pagemovevandal}}', '{{tl|Pagemovevandal}}')
	newtext = newtext.replace('{{pageblankvandal}}', '{{tl|Pageblankvandal}}')
	newtext = newtext.replace('{{blockedindef}}', '{{tl|Blockedindef}}')
	newtext = newtext.replace('{{idb}}', '{{tl|Idb}}')
	newtext = newtext.replace('{{userindef}}', '{tl|{userindef}}')
	newtext = newtext.replace('{{vOAblock}}', '{{tl|VOAblock}}')
	if not(newtext == text):
		if not save:
			return (userpage, newtext)
		try:
			userpage.edit(newtext=newtext, summary="Removing Temporary userpage category", minor=True, bot=True, basetime=userpage.lastedittime)
			l = codecs.open('LogFile.txt', 'ab', 'utf-8')
			l.write('\n# [[' + userpage.title + ']] - ' + reason)
			l.close()
		except api.APIError, (code, errortext):
			if code == 'protectedpage':
				reportError(userpage, "Page protected")
			else:
				reportError(userpage, errortext)
	else:
		reportError(userpage, "No change detected")

def reportError(userpage, error, delete=False):
	if delete:
		g = codecs.open('DelErrorFile.txt','ab', 'utf-8')
	else:
		g = codecs.open('ErrorFile.txt','ab', 'utf-8')
	g.write('\n# [['+userpage.title+']] ' + error)
	print( "ERROR on: " + userpage.pageid)
	g.close() 
		
def logincheck(username):
	if not site.isLoggedIn(username):
		e = open('CrashErrors.txt','w')
		e.write("Not Logged in\n")
		e.close()
		quit()

if __name__ == '__main__':
	main()
