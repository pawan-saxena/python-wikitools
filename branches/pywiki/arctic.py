# coding=utf-8

"""Script used to generate list of pages for WP:ARCTIC"""

import xmlreader
import MySQLdb
import re
import coords
import sys

def main():
	# These three should find any of the standard Coor[d] templates
	p = re.compile("\{\{\s*coor[^\|]*?\s*\|\s*((\d{1,2}\s*\|\s*){1,3}[NS])", re.I|re.S) # Things like {{coord|12|34|12|N|45|33|45|W|display=inline,title}}
	q = re.compile("\{\{\s*coor[^\|]*?\s*\|\s*((\d{1,2}\s*\|\s*){0,2}(\d{1,3}\.\d+\s*\|\s*){1}[NS])", re.I|re.S) # {{coord|12|34.25|N|45|33.45|W|display=inline,title}} or anything with decimals
	r = re.compile("\{\{\s*coor[^\|]*?\s*\|\s*(\-?(\d{1,2}\.\d+){1})\s*\|\s*", re.I|re.S) # Decimal only, no NS
	# Stupid deprecated templates
	s = re.compile("\{\{\s*(Geolinks|Mapit)[^\|]*?\s*\|\s*(\-?(\d{1,3}\.\d+){1})\s*\|\s*", re.I|re.S)
	# Infoboxes, based on Infobox Settlement, this is probably where we'll have problems
	latd = re.compile("(latd|lat_degrees|lat_d|lat_deg|latdeg)\s*\=\s*(\-?(\d{1,2})(\.\d+)?)", re.I|re.S)
	latm = re.compile("(latm|lat_minutes|lat_m|lat_min|latmin)\s*\=\s*((\d{1,2})(\.\d+)?)", re.I|re.S)
	lats = re.compile("(lats|lat_seconds|lat_s|lat_sec|latsec)\s*\=\s*((\d{1,2})(\.\d+)?)", re.I|re.S)
	latNS = re.compile("(latNS|lat_direction|lat_NS)\s*\=\s*([NS])")
	#Some other infoboxes use this
	t = re.compile("(latitude|lat)\s*=\s*(\-?(\d{1,2})(\.\d+)?)\s*[^º°]", re.I|re.S)
	# Just in case
	u = re.compile("(\-?(\d{1,2})(\.\d+)?)\s*[º°]\s*(((\d{1,2})(\.\d+)?)\s*\')?\s*(((\d{1,2})(\.\d+)?)\s*\")?\s*([NS])?", re.I|re.S)
	db = MySQLdb.connect(host="localhost", user="user", passwd="pswrd", db="stats")
	cursor = db.cursor()
	cursor.execute("SELECT DISTINCT pageid FROM links")
	pageids = cursor.fetchall()
	pagelist = []
	total = 0
	checked = 0
	for id in pageids:
		pagelist.append(str(id[0]))
	dump = xmlreader.XmlDump("dump.xml")
	pages = dump.parse()
	for item in pages:
		try:
			total +=1
			id = str(item.id)
			if pagelist.count(id) == 0:
				continue
			checked+=1
			print str(checked)+"/"+str(total)+": " + id
			text = item.text
			title = item.title
			lat = ''
			if p.search(text):
				res = p.search(text)
				lat = res.group(1)
			elif q.search(text):
				res = q.search(text)
				lat = res.group(1)
			elif r.search(text):
				res = r.search(text)
				lat = res.group(1)
			elif s.search(text):
				res = s.search(text)
				lat = res.group(2)
			elif latd.search(text):
				lat = latd.search(text).group(2)
				if latm.search(text):
					lat += '|' +latm.search(text).group(2)
				if lats.search(text):
					lat += '|' +lats.search(text).group(2)
				if latNS.search(text):
					lat += '|' +latNS.search(text).group(2)
			elif t.search(text):
				res = t.search(text)
				lat = res.group(2)
			elif u.search(text):
				res = u.search(text)
				lat = res.group(1)
				try:
					lat += '|' + res.group(4)
				except TypeError:
					pass
				try:
					lat += '|' + res.group(8)
				except TypeError:
					pass
				try:
					lat += '|' + res.group(12)
				except TypeError:
					pass
			else:
				error = "Unable to find coords"
				cursor.execute("INSERT INTO errors2 (error_desc, error_title) VALUES (%s, %s);", (error, title) )
				continue
			latC = coords.coords(lat)
			if latC.isGood():
				cursor.execute("INSERT INTO coords2 (coords_title, coords_lat) VALUES (%s, %s);", (title, latC.lat) )
		except coords.BadInput:
			error = "Unable to parse coords"
			cursor.execute("INSERT INTO errors2 (error_desc, error_title, error_lat) VALUES (%s, %s, %s);", (error, title, lat) )
		except coords.BadDirection:
			error = "Seems to have direction other than N/S"
			cursor.execute("INSERT INTO errors2 (error_desc, error_title, error_lat) VALUES (%s, %s, %s);", (error, title, lat) )
		except coords.BadData:
			error = "Latitude out of range"
			cursor.execute("INSERT INTO errors2 (error_desc, error_title, error_lat) VALUES (%s, %s, %s);", (error, title, lat) )
		except UnicodeEncodeError:
			error = "Encoding error"
			cursor.execute("INSERT INTO errors2 (error_desc, error_title) VALUES (%s, %s);", (error, id) )
		except KeyboardInterrupt:
			sys.exit("Exiting")
		except:
			cursor.execute("INSERT INTO errors2 (error_desc) VALUES (%s);", (str(sys.exc_info()[0])) )
			
if __name__ == '__main__':
    try:
        main()
    finally:
		sys.exit("Exiting")