#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb
import re
import sys

class BadDirection(Exception):
	"""Direction something other than NSEW"""

class BadData(Exception):
	"""Data out of valid range"""

def main():
	db1 = MySQLdb.connect(db='enwiki_p', host="sql-s1", read_default_file="/home/alexz/.my.cnf")
	db2 = MySQLdb.connect(db='u_alexz', host="sql", read_default_file="/home/alexz/.my.cnf")
	local = db2.cursor()
	enwiki = db1.cursor()
	test1 = re.compile("(?P<lat>(\d{1,2}_){1,3}[NS])_(?P<long>(\d{1,3}_){1,3}[EW])")
	test2 = re.compile("(?P<lat>\-?(\d{1,2}_){0,2}(\d{1,3}\.\d+_)?[NS])_(?P<long>\-?(\d{1,3}_){0,2}(\d{1,3}\.\d+_)?[EW])")
	test3 = re.compile("(?P<lat>\-?(\d{1,2}\.\d+){1})_(?P<long>\-?(\d{1,3}\.\d+){1})*_")
	elquery = "SELECT el_to FROM externallinks JOIN page ON page_id = el_from WHERE page_namespace = 0 AND page_title = %s AND el_to LIKE 'http://stable.toolserver.org/geohack/geohack.php%%' LIMIT 1"
	local.execute("SELECT title FROM photocoords_2")
	titles = local.fetchall()
	count = 0
	updatequery = "UPDATE photocoords_2 SET latitude=%s, longitude=%s WHERE title=%s"
	local.execute('START TRANSACTION')
	for t in titles:
		count += 1
		t = t[0]
		if count == 50:
			local.execute('COMMIT')
			local.execute('START TRANSACTION')
			count = 0
		rows = enwiki.execute(elquery, t)
		if not rows:
			reportError("No rows returned", title=t)
			continue
		try:
			url = enwiki.fetchone()[0]
			if test1.search(url):
				res = test1.search(url)
				lat = result2float(res.group('lat'), 'lat')
				long = result2float(res.group('long'), 'long')
			elif test2.search(url):
				res = test2.search(url)
				lat = result2float(res.group('lat'), 'lat')
				long = result2float(res.group('long'), 'long')
			elif test3.search(url):
				res = test3.search(url)
				lat = float(res.group('lat'))
				long = float(res.group('long'))
				if abs(lat) > 90:
					raise BadData(type + ' - ' + str(lat))
				if abs(long) > 180:
					raise BadData(type + ' - ' + str(long))
			else:
				reportError('Coords not found', title=t, err=url)
				continue
			local.execute(updatequery, (lat, long, t))
		except BadDirection, e:
			reportError('Unknown direction', err=e, title=t)
		except BadData, e:
			reportError('Data out of range', err=e, title=t)
		except:
			reportError('Unknown error', err=str(sys.exc_info()[1]), title=t)
	local.execute('COMMIT')
	
def reportError(msg='', err='', title=''):
	db = MySQLdb.connect(db='u_alexz', host="sql", read_default_file="/home/alexz/.my.cnf")
	c = db.cursor()
	query = "INSERT INTO photoerrors (errtext, errmsg, errtitle) VALUES(%s, %s, %s)"
	c.execute(query, (err, msg, title))
	db.close()
	
def result2float(result, type):
	d = 0
	m = 0
	s = 0
	nsew = None
	vars = ('d', 'm', 's')
	bits = result.split('_')
	last = len(bits)-1
	if bits[last].isalpha():
		nsew = bits[last].upper()
		del bits[last]
	if nsew and (len(nsew) != 1 or (nsew not in 'NS' and type == 'lat') or (nsew not in 'EW' and type == 'long')):
		raise BadDirection(nsew)
	for i in range(0, len(bits)):
		exec vars[i]+'='+str(float(bits[i]))
	total = float(d)
	total += float(m)/60.0
	total += float(s)/3600.0
	if type == "lat":
		if nsew == "S":
			total = total*-1.0
	if type == "long":
		if nsew == "W":
			total = total*-1.0
	if (type == 'lat' and abs(total) > 90) or (type == 'long' and abs(total) > 180):
		raise BadData(type + ' - ' + str(total))
	return total	
	
if __name__ == '__main__':
    main()
