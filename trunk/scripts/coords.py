# coding=utf-8

""" Coords class used by other scripts for working with coordinates on wiki pages """

import re

a = re.compile("\s*(\-?\d{1,2}(\.\d+)?)", re.I|re.S) #Decimal only
b = re.compile("\s*(\d{1,2}\.?\d*)\s*\|\s*([NS])", re.I|re.S) # With N/S, degrees only
c = re.compile("\s*(\d{1,2})\s*\|\s*(\d{1,2}\.?\d*)\s*\|\s*([NS])", re.I|re.S) # With N/S, degrees and minutes
d = re.compile("\s*(\d{1,2})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2}\.?\d*)\s*\|\s*([NS])", re.I|re.S) # With N/S, degrees, minutes, seconds

a2 = re.compile("\s*(\-?\d{1,3}(\.\d+)?)", re.I|re.S) #Decimal only
b2 = re.compile("\s*(\d{1,3}\.?\d*)\s*\|\s*([EW])", re.I|re.S) # With E/W degrees only
c2 = re.compile("\s*(\d{1,3})\s*\|\s*(\d{1,2}\.?\d*)\s*\|\s*([EW])", re.I|re.S) # With E/W, degrees and minutes
d2 = re.compile("\s*(\d{1,3})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2}\.?\d*)\s*\|\s*([EW])", re.I|re.S) # With E/W, degrees, minutes, seconds

# Ones without N/S/E/W
f = re.compile("\s*(\d{1,2})\s*\|\s*(\d{1,2}\.?\d*)", re.I|re.S) # degrees and minutes
g = re.compile("\s*(\d{1,2})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2}\.?\d*)", re.I|re.S) # degrees, minutes, seconds

f2 = re.compile("\s*(\d{1,3})\s*\|\s*(\d{1,2}\.?\d*)", re.I|re.S) # degrees and minutes
g2 = re.compile("\s*(\d{1,3})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2}\.?\d*)", re.I|re.S) # degrees, minutes, seconds

class BadDirection(Exception):
	"""Direction something other than N or S"""
class BadInput(Exception):
	"""No regexes matched"""
class BadData(Exception):
	"""Latitude data makes no sense"""
	
class coords(object):
	def __init__(self, lat, long):
		self.lat = 0.0
		self.long = 0.0
		if d.match(lat):
			res = d.match(lat)
			deg = res.group(1)
			min = res.group(2)
			sec = res.group(3)
			dir = res.group(4)
			self.lat = convertToDec(type = "lat", nsew = dir, d = deg, m = min, s = sec)
		elif c.match(lat):
			res = c.match(lat)
			deg = res.group(1)
			min = res.group(2)
			dir = res.group(3)
			self.lat = convertToDec(type = "lat", nsew = dir, d = deg, m = min)
		elif b.match(lat):
			res = b.match(lat)
			deg = res.group(1)
			dir = res.group(2)
			self.lat = convertToDec(type = "lat", nsew = dir, d = deg)
		elif g.match(lat):
			res = g.match(lat)
			deg = res.group(1)
			min = res.group(2)
			sec = res.group(3)
			self.lat = convertToDec(type = "lat", d = deg, m = min, s = sec)
		elif f.match(lat):
			res = f.match(lat)
			deg = res.group(1)
			min = res.group(2)
			self.lat = convertToDec(type = "lat", d = deg, m = min)
		elif a.match(lat):
			res = a.match(lat)
			deg = res.group(1)
			self.lat = convertToDec(type = "lat", nsew = "N", d = deg) # If there's only 1 number, assume its got a correct +/-
		else:
			raise BadInput
		if d2.match(long):
			res = d2.match(long)
			deg = res.group(1)
			min = res.group(2)
			sec = res.group(3)
			dir = res.group(4)
			self.long = convertToDec(type = "long", nsew = dir, d = deg, m = min, s = sec)
		elif c2.match(long):
			res = c2.match(long)
			deg = res.group(1)
			min = res.group(2)
			dir = res.group(3)
			self.long = convertToDec(type = "long", nsew = dir, d = deg, m = min)
		elif b2.match(long):
			res = b2.match(long)
			deg = res.group(1)
			dir = res.group(2)
			self.long = convertToDec(type = "long", nsew = dir, d = deg)
		elif g2.match(long):
			res = g2.match(long)
			deg = res.group(1)
			min = res.group(2)
			sec = res.group(3)
			self.long = convertToDec(type = "long", d = deg, m = min, s = sec)
		elif f2.match(long):
			res = f2.match(long)
			deg = res.group(1)
			min = res.group(2)
			self.long = convertToDec(type = "long", d = deg, m = min)
		elif a2.match(long):
			res = a2.match(long)
			deg = res.group(1)
			self.long = convertToDec(type = "long", nsew = "E", d = deg)
		else:
			raise BadInput
		if abs(self.lat) > 90 or abs(self.long) > 180:
			raise BadData
			
	def isGood(self): # Used by artic script to check if lat is above arctic circle
		if self.lat > 66.560833:
			return True
		else:
			return False

def convertToDec(type, nsew = "O", d=0, m=0, s=0):
	total = float(d) # start with degrees
	total += float(m)/60.0 # minutes
	total += float(s)/3600.0 # seconds
	if type == "lat":
		if nsew == "S" or nsew == "s":
			total = total*-1.0
		elif nsew != "N" and nsew != "n":
			print nsew
			raise BadDirection
			return
	if type == "long":
		if nsew == "W" or nsew == "w":
			total = total*-1.0
		elif nsew != "E" and nsew != "e":
			raise BadDirection
			return
	return round(total, 4)

			