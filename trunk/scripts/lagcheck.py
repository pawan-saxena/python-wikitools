#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import os.path

def lagcheck(host, database):
	query = 'SELECT UNIX_TIMESTAMP() - UNIX_TIMESTAMP(rc_timestamp) FROM recentchanges ORDER BY rc_timestamp DESC LIMIT 1'
	try:
		db = MySQLdb.connect(db=database, host="sql-"+host, read_default_file="/home/alexz/.my.cnf")
		cursor = db.cursor()
		cursor.execute(query)
		serverup(host)
		replag = cursor.fetchone()[0]
		if replag > 300:
			highlag(host)
		else:
			nolag(host)
	except:
		serverdown(host)

def main():
	servers = [('s1', 'enwiki_p'), ('s2', 'enwiktionary_p'), ('s3', 'frwiktionary_p'), 
	('s4', 'commonswiki_p'), ('s5', 'dewiki_p'), ('s6', 'frwiki_p')]
	for s in servers:
		lagcheck(s[0], s[1])
	try:
		db = MySQLdb.connect(db='u_alexz',host="sql",read_default_file="/home/alexz/.my.cnf")
		cursor = db.cursor()
		serverup('sql')
	except:
		serverdown('sql')
		
def highlag(server):
	f = open('/home/alexz/public_html/messages/'+server+'-replag', 'wb')
	f.write('Due to high replication lag, this tool may be inaccurate')
	f.close()

def nolag(server):
	f = open('/home/alexz/public_html/messages/'+server+'-replag', 'wb')
	f.write('')
	f.close()

def serverdown(server):
	try:
		size = os.path.getsize('/home/alexz/public_html/messages/'+server)
	except OSError:
		size = 0
	if size is 0:
		f = open('/home/alexz/public_html/messages/'+server, 'wb')
		f.write('<!--serverdown-->Due to a server error, this tool may not function fully')
		f.close()

def serverup(server):
	change = False
	try:
		f = open('/home/alexz/public_html/messages/'+server, 'rb')
		if '<!--serverdown-->' in f.read():
			change = True
		f.close()
	except IOError:
		change = True		
	f = open('/home/alexz/public_html/messages/'+server, 'wb')
	f.write('')
	f.close()		

if __name__ == "__main__":
	main()
