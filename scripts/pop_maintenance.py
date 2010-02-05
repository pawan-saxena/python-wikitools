#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import csv
import sys

def rename():
	table = raw_input("Table: ")
	old = raw_input("Old name: ")
	new = raw_input("New name: ")
	inner(table, old, new)
	
def merge():
	table = raw_input("Table: ")
	mergefrom = raw_input("Merge: ")
	mergeto = raw_input("Into: ")
	inner(table, mergefrom, mergeto, True)
	
def inner(table, old, new, domerge=False):
	reader =  csv.reader(open('/home/alexz/popularity/stopwords.csv', 'rb'))
	words = reader.next()
	words = [w.strip() for w in words]
	if new in words:
		sys.exit(new+" is a MySQL stopword")
	db = MySQLdb.connect(host="sql", db='u_alexz', read_default_file="/home/alexz/.my.cnf")
	cursor = db.cursor()
	check = """SELECT COUNT(*) FROM %s WHERE project_assess LIKE "%%'%s':%%" """ % (table, old)
	if domerge:
		check+= """ AND project_assess NOT LIKE  "%%'%s':%%" """ % new
	cursor.execute(check)
	res = cursor.fetchone()
	rows = res[0]
	print str(rows), "rows to update"
	index = 0
	update = """UPDATE %s SET project_assess=REPLACE(project_assess,"%s","%s") 
	WHERE project_assess LIKE "%%'%s':%%" """ % (table, old, new, old)
	if domerge: # Ideally the redundant entries would be removed, but that would require doing 1 row at a time
		update+= """ AND project_assess NOT LIKE  "%%'%s':%%" """ % new
	update+= " LIMIT 1000"
	for x in range(0,rows/1000+1):
		start = index*1000
		finish = (index+1)*1000-1
		if finish > rows:
			finish = rows
		print "Doing rows "+str(start)+" through "+str(finish)
		index+=1
		cursor.execute(update)
	print "Done"
	

if __name__ == '__main__':
	if len(sys.argv) == 1:
		sys.exit("Need to specify merge or rename")
	if sys.argv[1] == '--merge':
		merge()
	elif sys.argv[1] == '--rename':
		rename()