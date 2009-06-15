#!/usr/bin/python
# -*- coding: utf-8 -*-
from ircbot import SingleServerIRCBot
from wikitools import *
import settings
import threading
import time
import sys
import MySQLdb
import urllib
import os
import traceback
import re

connections = {}

site = wiki.Wiki()
site.setMaxlag(120)
site.login(settings.bot, settings.botpass)
AIV = page.Page(site, 'Wikipedia:Administrator intervention against vandalism/TB2')


class timedTracker(dict):
	def __init__(self, args={}, expiry=300):
		dict.__init__(self, args)
		self.expiry = expiry
		self.times = set()
		self.times = set([(item, int(time.time())) for item in self.keys()])
		
	def __purgeExpired(self):
		checktime = int(time.time())-self.expiry
		removed = set([item for item in self.times if item[1] < checktime])
		self.times.difference_update(removed)
		[dict.__delitem__(self, item[0]) for item in removed]
		
	def __getitem__(self, key):
		self.__purgeExpired()
		if not key in self:
			return 0
		return dict.__getitem__(self, key)
	
	def __setitem__(self, key, value):
		self.__purgeExpired()
		if not key in self:
			self.times.add((key, int(time.time())))
		return dict.__setitem__(self, key, value)
	
	def __delitem__(self, key):
		self.times = set([item for item in self.times if item[0] != key])
		self.__purgeExpired()
		return dict.__delitem__(self, key)
	
	def __contains__(self, key):
		self.__purgeExpired()
		return dict.__contains__(self, key)
	
	def __repr__(self):
		self.__purgeExpired()
		return dict.__repr__(self)
		
	def __str__(self):
		self.__purgeExpired()
		return dict.__str__(self)
	
	def keys(self):
		self.__purgeExpired()
		return dict.keys(self)
	
class CommandBot(SingleServerIRCBot):

	def __init__(self, channel, nickname, server, port=6667):
		SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
		self.channel = channel

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")
		raise KillException
		return

	def on_welcome(self, c, e):
		global connections
		c.privmsg("NickServ", "identify "+settings.ircpass)
		time.sleep(3)
		c.join(self.channel)
		connections['command'] = c
		return

	def on_pubmsg(self, c, e):
		user = e.source()
		if e.arguments()[0] == '&restart' and '@wikimedia/Mr.Z-man' in user:
			sys.exit()
		return

class BotRunnerThread(threading.Thread):
	def __init__(self, bot):
		threading.Thread.__init__(self)
		self.bot = bot
		
	def run(self):
		self.bot.start()
		
immediate = set() 
vandalism = set()
def main():
	global connections
	getLists()
	if not immediate or not vandalism:
		raise Exception("Lists not initialised")
	listcheck = time.time()
	Cchannel = "#wikipedia-en-abuse-log"
	Cserver = "chat.eu.freenode.net"
	nickname = "MrZ-bot"
	cbot = CommandBot(Cchannel, nickname, Cserver)
	cThread = BotRunnerThread(cbot)
	cThread.daemon = True
	cThread.start()
	while len(connections) != 1:
		pass
	IRCut = timedTracker() # user tracker for IRC
	AIVut = timedTracker() # user tracker for AIV
	IRCreported = timedTracker(expiry=60)
	AIVreported = timedTracker(expiry=600)
	titles = timedTracker() # this only reports to IRC for now
	query = """SELECT afl_user_text,afl_action,afl_id,afl_namespace,afl_title,afl_filter,afl_timestamp
	FROM abuse_filter_log WHERE afl_id>%s ORDER BY afl_id DESC"""
	db = MySQLdb.connect(db='enwiki_p', host="sql-s1", read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	cursor.execute('SELECT afl_id FROM abuse_filter_log ORDER BY afl_id DESC LIMIT 1')
	lastid = cursor.fetchone()[0]
	while True:
		if time.time() > listcheck+300:
			getLists()
			listcheck = time.time()
		cursor.execute(query, lastid)
		res = cursor.fetchall()
		attempts = []
		for row in res:
			logid = row[2]
			# I'm not sure if this is still necessary. Is this actually possible?
			if logid <= lastid:
				continue
			# Set readable-ish var names from query result
			action = row[1]
			ns = row[3]
			t = row[4]
			filter = row[5]
			ts = row[6]
			u = user.User(site, row[0], check=False)
			username = u.name.encode('utf8')
			# Check against 'immediate' list before doing anything
			if filter in immediate and not username in AIVreported:
				reportUser(u, filter=filter, hit=logid)
				AIVreported[username] = 1
			# Prevent multiple hits from the same edit attempt
			if (username, ts) in attempts:
				continue
			attempts.append((username, ts))
			# IRC reporting checks
			IRCut[username]+=1
			# 5 hits in 5 mins
			if IRCut[username] == 5 and not username in IRCreported:
				connections['command'].privmsg("#wikipedia-en-abuse-log", 
				"!alert - [[User:%s]] has tripped 5 filters within the last 5 minutes: "\
				"http://en.wikipedia.org/wiki/Special:AbuseLog?wpSearchUser=%s"\
				%(username, urllib.quote(username)))
				del IRCut[username]
				IRCreported[username] = 1
			# Hits on pagemoves
			if action == 'move':
				connections['command'].privmsg("#wikipedia-en-abuse-log", 
				"!alert - [[User:%s]] has tripped a filter doing a pagemove"\
				": http://en.wikipedia.org/wiki/Special:AbuseLog?details=%s"\
				%(username, str(logid)))
			# Frequent hits on one article, would be nice if there was somewhere this could
			# be reported on-wiki
			titles[(ns,t)]+=1
			if titles[(ns,t)] == 10 and not (ns,t) in IRCreported:
				p = page.Page(site, t, check=False, followRedir=False)
				p.setNamespace(ns)
				connections['command'].privmsg("#wikipedia-en-abuse-log", 
				"!alert - 10 filters in the last 5 minutes have been tripped on [[%s]]: "\
				"http://en.wikipedia.org/wiki/Special:AbuseLog?wpSearchTitle=%s"\
				%(p.title.encode('utf8'), p.urltitle))
				del titles[(ns,t)]
				IRCreported[(ns,t)] = 1
			# AIV reporting - check if the filter is in one of the lists
			if filter not in vandalism.union(immediate):
				continue
			AIVut[username]+=1			
			# 10 hits in 5 minutes
			if AIVut[username] == 10 and not username in AIVreported:
				del AIVut[username]
				reportUser(u)
				AIVreported[username] = 1
		if res:
			lastid = res[0][2]
		time.sleep(1.5)

def reportUser(u, filter=None, hit=None):
	username = u.name.encode('utf8')
	if filter:
		reason = "Tripped [[Special:AbuseFilter/%(f)d|filter %(f)d]] "\
		"([{{fullurl:Special:AbuseLog|details=%(h)d}} details])."\
		% {'f':filter, 'h':hit}
	else:
		reason = "Tripped 10 abuse filters in the last 5 minutes: "\
		"([{{fullurl:Special:AbuseLog|wpSearchUser=%s}} details])."\
		% (urllib.quote(username))
	editsum = "Reporting [[Special:Contributions/%s]]" % (username)
	if u.isIP:
		line = "\n* {{IPvandal|%s}} - " % (username)
	else:
		line = "\n* {{Vandal|%s}} - " % (username)
	line += reason+" ~~~~"
	AIV.edit(appendtext=line, summary=editsum)

def getLists():
	lists = page.Page(site, "User:Mr.Z-bot/filters.js", check=False)
	cont = lists.getWikiText(force=True)
	lines = cont.splitlines()
	for line in lines:
		if line.startswith('#') or not line:
			continue
		if line.startswith('immediate') or line.startswith('vandalism'):
			(type, filters) = line.split('=')
			type = type.strip()
			filters = validateFilterList(filters, type)
			if not filters:
				connections['command'].privmsg("#wikipedia-en-abuse-log", 
				"Syntax error detected in filter list page - [[User:Mr.Z-bot/filters.js]]")
			
validate = re.compile('^[0-9, ]*?$')
def validateFilterList(filters, type):
	global immediate, vandalism
	if not validate.match(filters):
		return False
	elif not type in ('immediate', 'vandalism'):
		return False
	else:
		prev = eval(type)
		try:
			exec( type + ' = set([' + filters + '])', locals(), globals())
		except:
			exec( type + ' = ' + repr(prev), locals(), globals())
			return False
		if not isinstance(eval(type), set):
			exec( type + ' = ' + repr(prev), locals(), globals())
			return False
		return True
		
if __name__ == "__main__":
	try:
		main()
	except:
		f = open('/home/alexz/afbot.err', 'ab')
		traceback.print_exc(None, f)
		f.close()
		sys.exit()
	finally:
		try:
			os.remove('/home/alexz/phoenix-afbot.out')
		except:
			pass
		try:
			os.remove('/home/alexz/phoenix-afbot.pid')
		except:
			pass
			
