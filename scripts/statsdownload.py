# -*- coding: utf-8 -*-
import urllib, datetime, re, httplib, os, calendar, sys
from time import sleep

def main():
	day = (datetime.datetime.now()-datetime.timedelta(6)).day
	year = (datetime.datetime.now()-datetime.timedelta(6)).year
	month = (datetime.datetime.now()-datetime.timedelta(6)).month
	cal = calendar.monthcalendar(year+1, month)
	week = []
	for row in cal:
		if day in row:
			week = row
	numfiles = 24 * (7 - week.count(0))
	if cal.index(week) == 1 and cal[0].count(0) != 0:
		numfiles += 24 * (7 - cal[0].count(0))
		day = 1
	else:
		day = week[0]
	files = 0
	if month < 10:
		month =  "0" + str(month)
	else:
		month = str(month)
	logMsg("Month is: " + month)
	logMsg("Day is: " + str(day))
	sleep(3)
	# month = "01" # Override settings
	# day = 1
	# year = 2009
	# numfiles = 24*31
	# files=0	
	hour = 0
	try:
		while True:
			if day < 10:
				sday = "0"+str(day)
			else:
				sday = str(day)
			if hour < 10:
				shour = "0"+str(hour)
			else:
				shour = str(hour)
			datapage = str(year)+month+sday+"-"+shour+"0000"
			url = "http://dammit.lt/wikistats/pagecounts-"+datapage+".gz"
			downloadPage(url)
			hour+=1
			if hour == 24:
				l = open("DownloadLog.txt", 'ab')
				l.write("%s-%d downloaded\n" % (month, day))
				l.close()
				day+=1
				hour=0
			files+=1
			if files == numfiles:
				break
	except:
		import webbrowser, traceback
		f = open("AAA_DOWNLOAD_ERROR.log", "wb")
		traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2], None, f)
		f.close()
		webbrowser.open("AAA_DOWNLOAD_ERROR.log")

def downloadPage(url):
	logMsg("Downloading "+url)
	conn = httplib.HTTPConnection('dammit.lt')
	testurl = url.split('http://dammit.lt')[1]
	conn.request('HEAD', testurl)
	r1 = conn.getresponse()
	if r1.status == 404 or r1.status == 500:
		url = re.sub("-(\d{2})0000", r"- \1 0001", url)
		url = re.sub(" ", "", url)
		testurl = url.split('http://dammit.lt')[1]
		conn = httplib.HTTPConnection('dammit.lt')
		conn.request('HEAD', testurl)
		r1 = conn.getresponse()
		if r1.status == 404 or r1.status == 500:
			logMsg("Warning: "+url+" seems to be missing")
			return
	conn.close()
	filename = url.split('http://dammit.lt/wikistats/')[1]
	fileloc = "Q:/stats/downloading/"+filename
	f = open(fileloc, 'wb')
	f.close()
	page = urllib.urlretrieve(url, fileloc)
	os.rename("Q:/stats/downloading/"+filename, "Q:/stats/statspages/"+filename)
	
	
def logMsg(msg):
	f = open("PopLogFile.txt", 'ab')
	f.write(str(msg)+"\n")
	f.close()
	
if __name__ == '__main__':
	main()