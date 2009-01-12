# -*- coding: utf-8 -*-
import urllib, datetime, re, httplib, os
from time import sleep

def main():
	day = (datetime.datetime.now()-datetime.timedelta(1)).day
	month = datetime.datetime.now().month
	if month < 10:
		month =  "0" + str(month)
	else:
		month = str(month)
	logMsg("Month is: " + month)
	logMsg("Day is: " + str(day))
	sleep(3)
	year = str(datetime.datetime.now().year)
	hour = 0
	if day < 10:
		sday = "0"+str(day)
	else:
		sday = str(day)
	while True:
		if hour < 10:
			shour = "0"+str(hour)
		else:
			shour = str(hour)
		datapage = year+month+sday+"-"+shour+"0000"
		url = "http://dammit.lt/wikistats/pagecounts-"+datapage+".gz"
		downloadPage(url)
		hour+=1
		if hour == 24:
			break

def downloadPage(url):
	logMsg("Downloading "+url)
	conn = httplib.HTTPConnection('dammit.lt')
	testurl = url.split('http://dammit.lt')[1]
	conn.request('HEAD', testurl)
	r1 = conn.getresponse()
	if r1.status == 404:
		url = re.sub("-(\d{2})0000", r"- \1 0001", url)
		url = re.sub(" ", "", url)
		testurl = url.split('http://dammit.lt')[1]
		conn = httplib.HTTPConnection('dammit.lt')
		conn.request('HEAD', testurl)
		r1 = conn.getresponse()
		if r1.status == 404:
			logMsg("Warning: "+url+" seems to be missing")
			return
	conn.close()
	filename = url.split('http://dammit.lt/wikistats/')[1]
	fileloc = "C:/Python25/MediaWiki/downloading/"+filename
	f = open(fileloc, 'wb')
	f.close()
	page = urllib.urlretrieve(url, fileloc)
	os.rename("C:\\Python25\\MediaWiki\\downloading\\"+filename, "C:\\Python25\\MediaWiki\\statspages\\"+filename)
	
	
def logMsg(msg):
	f = open("PopLogFile.txt", 'ab')
	f.write(str(msg))
	f.close()
	print msg
	
if __name__ == '__main__':
	main()