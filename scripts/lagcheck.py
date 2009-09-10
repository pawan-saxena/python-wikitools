#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import os.path

def main():
	query = 'SELECT UNIX_TIMESTAMP() - UNIX_TIMESTAMP(rc_timestamp) FROM recentchanges ORDER BY rc_timestamp DESC LIMIT 1'
	try:
		db = MySQLdb.connect(db='enwiki_p', host="sql-s1", read_default_file="/home/alexz/.my.cnf")
		cursor = db.cursor()
		cursor.execute(query)
		serverup('s1')
		replag = cursor.fetchone()[0]
		if replag > 300:
			highlag('s1')
		else:
			nolag('s1')
	except:
		serverdown('s1')
		
	try:
		db = MySQLdb.connect(db='dewiki_p', host="sql-s2", read_default_file="/home/alexz/.my.cnf")
		cursor = db.cursor()
		cursor.execute(query)
		serverup('s2')
		replag = cursor.fetchone()[0]
		if replag > 300:
			highlag('s2')
		else:
			nolag('s2')
	except:
		serverdown('s2')
		
	try:
		db = MySQLdb.connect(db='frwiki_p', host="sql-s3", read_default_file="/home/alexz/.my.cnf")
		cursor = db.cursor()
		cursor.execute(query)
		serverup('s3')
		replag = cursor.fetchone()[0]
		if replag > 300:
			highlag('s3')
		else:
			nolag('s3')
	except:
		serverdown('s3')
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
	if os.path.getsize('/home/alexz/public_html/messages/'+server) is 0:
		f = open('/home/alexz/public_html/messages/'+server, 'wb')
		f.write('Due to a server error, this tool may not function fully')
		f.close()

def serverup(server):
	f = open('/home/alexz/public_html/messages/'+server, 'rb')
	if f.read() == 'Due to a server error, this tool may not function fully':
		f.close()
		f = open('/home/alexz/public_html/messages/'+server, 'wb')
		f.write('')
	f.close()		

if __name__ == "__main__":
	main()
