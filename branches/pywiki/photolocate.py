# coding=utf-8

""" Script used to scan a db dump for pages with coordinates needing images """

import xmlreader
import MySQLdb
import re
import coords
import sys
from urllib import urlencode

def main():
	# These three should find any of the standard Coor[d] templates
	p = re.compile("\{\{\s*coor[^\|]*?\s*\|\s*((\d{1,2}\s*\|\s*){1,3}[NS])\s*\|\s*((\d{1,3}\s*\|\s*){1,3}[EW])", re.I|re.S) # Things like {{coord|12|34|12|N|45|33|45|W|display=inline,title}}
	q = re.compile("\{\{\s*coor[^\|]*?\s*\|\s*((\d{1,2}\s*\|\s*){0,2}(\d{1,3}\.\d+\s*\|\s*){1}[NS])\s*\|\s*((\d{1,3}\s*\|\s*){0,2}(\d{1,3}\.\d+\s*\|\s*){1}[EW])", re.I|re.S) # {{coord|12|34.25|N|45|33.45|W|display=inline,title}} or anything with decimals
	r = re.compile("\{\{\s*coor[^\|]*?\s*\|\s*(\-?(\d{1,2}\.\d+){1})\s*\|\s*(\-?(\d{1,3}\.\d+){1})\s*[\|\}]", re.I|re.S) # Decimal only, no NS
	# Stupid deprecated templates
	s = re.compile("\{\{\s*(Geolinks|Mapit)[^\|]*?\s*\|\s*(\-?(\d{1,2}\.\d+){1})\s*\|\s*(\-?(\d{1,3}\.\d+){1})", re.I|re.S)
	# Infoboxes, based on Infobox Settlement, this is probably where we'll have problems
	latd = re.compile("(latd|lat_degrees|lat_d|lat_deg|latdeg)\s*\=\s*(\-?(\d{1,2})(\.\d+)?)", re.I|re.S)
	latm = re.compile("(latm|lat_minutes|lat_m|lat_min|latmin)\s*\=\s*((\d{1,2})(\.\d+)?)", re.I|re.S)
	lats = re.compile("(lats|lat_seconds|lat_s|lat_sec|latsec)\s*\=\s*((\d{1,2})(\.\d+)?)", re.I|re.S)
	latNS = re.compile("(latNS|lat_direction|lat_NS)\s*\=\s*([NS])")

	longd = re.compile("(longd|long_degrees|long_d|long_deg|longdeg)\s*\=\s*(\-?(\d{1,3})(\.\d+)?)", re.I|re.S)
	longm = re.compile("(longm|long_minutes|long_m|long_min|longmin)\s*\=\s*((\d{1,2})(\.\d+)?)", re.I|re.S)
	longs = re.compile("(longs|long_seconds|long_s|long_sec|longsec)\s*\=\s*((\d{1,2})(\.\d+)?)", re.I|re.S)
	longEW = re.compile("(longEW|long_direction|long_EW)\s*\=\s*([EW])")
	#Some other infoboxes use this
	t = re.compile("(latitude|lat)\s*=\s*(\-?(\d{1,2})(\.\d+)?)\s*[^별]", re.I|re.S)
	t2 = re.compile("(longitude|long)\s*=\s*(\-?(\d{1,3})(\.\d+)?)\s*[^별]", re.I|re.S)
	# Just in case
	u = re.compile("(\-?(\d{1,2})(\.\d+)?)\s*[별]\s*(((\d{1,2})(\.\d+)?)\s*\')?\s*(((\d{1,2})(\.\d+)?)\s*\")?\s*([NS])?[\s,\.]*(\-?(\d{1,3})(\.\d+)?)\s*[별]\s*(((\d{1,2})(\.\d+)?)\s*\')?\s*(((\d{1,2})(\.\d+)?)\s*\")?\s*([EW])?", re.I|re.S)
	db = MySQLdb.connect(host="localhost", user="user", passwd="password", db="stats")
	cursor = db.cursor()
	cursor.execute("SELECT * FROM coorlinks JOIN reqphoto ON reqphoto.pageid = coorlinks.pageid")
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
			try:
				title = item.title
				tmp = urlencode({'x':title})
				urltitle = tmp[2:]
			except:
				title = id
				urltitle = id
			lat = ''
			long = ''
			if p.search(text):
				res = p.search(text)
				lat = res.group(1)
				long = res.group(3)
			elif q.search(text):
				res = q.search(text)
				lat = res.group(1)
				long = res.group(4)
			elif r.search(text):
				res = r.search(text)
				lat = res.group(1)
				long = res.group(3)
			elif s.search(text):
				res = s.search(text)
				lat = res.group(2)
				long = res.group(4)
			elif latd.search(text) and longd.search(text):
				lat = latd.search(text).group(2)
				long = longd.search(text).group(2)
				if latm.search(text):
					lat += '|' +latm.search(text).group(2)
				if lats.search(text):
					lat += '|' +lats.search(text).group(2)
				if latNS.search(text):
					lat += '|' +latNS.search(text).group(2)
				if longm.search(text):
					long += '|' +longm.search(text).group(2)
				if longs.search(text):
					long += '|' +longs.search(text).group(2)
				if longEW.search(text):
					long += '|' +longEW.search(text).group(2)
			elif t.search(text) and t2.search(text):
				res = t.search(text)
				res2 = t2.search(text)
				lat = res.group(2)
				long = res2.group(2)
			elif u.search(text):
				res = u.search(text)
				lat = res.group(1)
				long = res.group(13)
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
				try:
					long += '|' + res.group(17)
				except TypeError:
					pass
				try:
					long += '|' + res.group(21)
				except TypeError:
					pass
				try:
					long += '|' + res.group(24)
				except TypeError:
					pass
			else:
				error = "Unable to find coords"
				cursor.execute("INSERT INTO photoerrors (perror_desc, perror_title) VALUES (%s, %s);", (error, title) )
				continue
			print lat
			print long
			coordinates = coords.coords(lat, long)
			cursor.execute("INSERT INTO photocoords (pcoords_title, pcoords_lat, pcoords_long) VALUES (%s, %s, %s);", (title, coordinates.lat, coordinates.long) )
		except coords.BadInput:
			error = "Unable to parse coords"
			cursor.execute("INSERT INTO photoerrors (perror_desc, perror_title, perror_lat, perror_long) VALUES (%s, %s, %s, %s);", (error, urltitle, lat, long) )
		except coords.BadDirection:
			error = "Seems to have direction other than N/S"
			cursor.execute("INSERT INTO photoerrors (perror_desc, perror_title, perror_lat, perror_long) VALUES (%s, %s, %s, %s);", (error, urltitle, lat, long) )
		except coords.BadData:
			error = "Latitude out of range"
			cursor.execute("INSERT INTO photoerrors (perror_desc, perror_title, perror_lat, perror_long) VALUES (%s, %s, %s, %s);", (error, urltitle, lat, long) )
		except UnicodeEncodeError:
			error = "Encoding error"
			cursor.execute("INSERT INTO photoerrors (perror_desc, perror_title) VALUES (%s, %s);", (error, id) )
		except KeyboardInterrupt:
			sys.exit("Exiting")
		except:
			cursor.execute("INSERT INTO photoerrors (perror_desc) VALUES (%s);", (str(sys.exc_info()[0])) )

if __name__ == '__main__':
    try:
        main()
    finally:
		print("Exiting")