#!/usr/bin/python
# -*- coding: utf-8 -*-
import MySQLdb
import os
import sys

db = MySQLdb.connect(host="sql-s1", read_default_file="/home/alexz/.my.cnf")
c = db.cursor()

# SETUP DONE
# GETTING CATEGORY LIST
print "Getting category list"
query = 'SELECT page_title FROM enwiki_p.page INNER JOIN enwiki_p.categorylinks ON cl_from=page_id WHERE page_namespace=14 AND cl_to=%s';
try:
	os.remove('../catlist.txt')
except:
	pass

f = open('../catlist.txt', 'ab')

catstodo = ['Wikipedia_requested_photographs']
catsdone = []

f.write(catstodo[0]+'\n')

print "Getting cats"
while True:
	try:
		cat = catstodo.pop()
	except:
		break
	#print "Getting subcats for %s" % (cat)
	l = c.execute(query, (cat))
	catsdone.append(cat)
	if l == 0:
		continue
	cats = c.fetchall()
	for cat in cats:
		if not cat in catsdone and not cat in catstodo and not 'requested_map' in cat[0].lower():
			catstodo.append(cat)
			f.write(cat[0] + '\n')
	if len( catstodo) == 0:
		break
f.close()

# CATEGORY LIST DONE
# GET TITLES
print "Getting titles"
c.execute("""CREATE TABLE IF NOT EXISTS u_alexz.catpages_tmp (
  `title` varchar(255) NOT NULL,
  UNIQUE KEY `title` (`title`)
) ENGINE=InnoDB;
""")
c.execute("TRUNCATE TABLE u_alexz.catpages_tmp")

insquery = """INSERT IGNORE INTO u_alexz.catpages_tmp (title)
SELECT enwiki_p.page.page_title FROM enwiki_p.page
JOIN enwiki_p.categorylinks ON enwiki_p.page.page_id=enwiki_p.categorylinks.cl_from
WHERE enwiki_p.page.page_namespace=1 AND enwiki_p.categorylinks.cl_to=%s"""

f = open('../catlist.txt', 'rb')

lines = f.read()
lines = lines.splitlines()

for cat in lines:
	#print "Getting pages in %s" % (cat)
	c.execute("START TRANSACTION")
	c.execute(insquery, (cat))
	c.execute("COMMIT")

del lines
f.close()

# TITLES DONE
# JOIN AGAINST TEMPLATELINKS
print "Doing join"

joinquery = """SELECT u_alexz.catpages_tmp.title, AsBinary(u_dispenser_p.coord_enwiki.gc_location) FROM u_alexz.catpages_tmp
JOIN enwiki_p.page ON enwiki_p.page.page_title = u_alexz.catpages_tmp.title
JOIN u_dispenser_p.coord_enwiki ON u_dispenser_p.coord_enwiki.gc_from=enwiki_p.page.page_id
WHERE enwiki_p.templatelinks.tl_namespace=10 AND enwiki_p.page.page_namespace=0
AND u_dispenser_p.coord_enwiki.gc_primary=1"""

c.execute(joinquery)
requested = set(c.fetchall())

print "Getting pages w/ no images"
noimages = """SELECT page_title, AsBinary(u_dispenser_p.coord_enwiki.gc_location) FROM enwiki_p.page 
JOIN u_dispenser_p.coord_enwiki ON u_dispenser_p.coord_enwiki.gc_from=enwiki_p.page.page_id 
WHERE page_namespace=0 AND page_is_redirect=0 AND 
(SELECT il_to FROM enwiki_p.imagelinks WHERE il_from=page_id LIMIT 1) IS NULL 
AND u_dispenser_p.coord_enwiki.gc_primary=1
"""

c.execute(noimages)
noimg = set(c.fetchall())

print "Getting pages w/ no jpgs"
nojpgs = """SELECT page_title, AsBinary(u_dispenser_p.coord_enwiki.gc_location) FROM enwiki_p.page 
JOIN u_dispenser_p.coord_enwiki ON u_dispenser_p.coord_enwiki.gc_from=enwiki_p.page.page_id 
WHERE page_namespace=0 AND page_is_redirect=0 AND 
(SELECT il_to FROM enwiki_p.imagelinks WHERE il_from=page_id AND (il_to LIKE "%\.jpg" OR il_to LIKE "%\.jpeg") LIMIT 1) IS NULL 
AND u_dispenser_p.coord_enwiki.gc_primary=1
"""

c.execute(nojpgs)
nojpg = set(c.fetchall())

requestonly = requested.difference(noimg)
noimageonly = noimg.difference(requested)
nojpgonly = nojpg.difference(requested)
requestAndNoimg = requested.intersection(noimg) # This is also equivalent to being in all 3 categories, since if an article has no image, then it also has no jpg
requestAndNojpg = requested.intersection(nojpg)
# There is no point in doing nojpgAndNoimg, since if a page has no images, then it has no jpgs
del nojpg
del noimg
del requested

# JOIN DONE
# POPULATE MAIN TABLE COPY
print "Making temp table"
db2 = MySQLdb.connect(db='u_alexz', host="sql", read_default_file="/home/alexz/.my.cnf")
c2 = db2.cursor()
insquery2 = """INSERT IGNORE INTO u_alexz.photocoords_2 (title, coordinate, reqphoto) VALUES (%s, PointFromWKB(%s), 1)"""
insquery3 = """INSERT IGNORE INTO u_alexz.photocoords_2 (title, coordinate, noimg) VALUES (%s, PointFromWKB(%s), 1)"""
insquery4 = """INSERT IGNORE INTO u_alexz.photocoords_2 (title, coordinate, nojpg) VALUES (%s, PointFromWKB(%s), 1)"""
insquery5 = """INSERT IGNORE INTO u_alexz.photocoords_2 (title, coordinate, reqphoto, nojpg) VALUES (%s, PointFromWKB(%s), 1, 1)"""
insquery6 = """INSERT IGNORE INTO u_alexz.photocoords_2 (title, coordinate, reqphoto, noimg, nojpg) VALUES (%s, PointFromWKB(%s), 1, 1, 1)"""

try:
	c2.execute("START TRANSACTION")
	c2.execute("DROP TABLE photocoords_2")
	c2.execute("COMMIT")
except:
	pass

c2.execute("START TRANSACTION")
c2.execute(""" CREATE TABLE IF NOT EXISTS `photocoords_2` (
  `title` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT NULL,
  `coordinate` point NOT NULL,
  `reqphoto` tinyint(1) DEFAULT '0',
  `noimg` tinyint(1) DEFAULT '0',
  `nojpg` tinyint(1) DEFAULT '0',
  UNIQUE KEY `title` (`title`),
  SPATIAL KEY `coordinate` (`coordinate`)
) ENGINE=MyISAM""")
c2.execute("COMMIT")

c2.execute("START TRANSACTION")
c2.execute("TRUNCATE TABLE photocoords_2")
c2.execute("COMMIT")

c2.execute("START TRANSACTION")
for entry in requestonly:
		c2.execute(insquery2, (entry[0], entry[1]))
c2.execute("COMMIT")
del requestonly
c2.execute("START TRANSACTION")
for entry in noimageonly:
		c2.execute(insquery3, (entry[0], entry[1]))
c2.execute("COMMIT")
del noimageonly
c2.execute("START TRANSACTION")
for entry in nojpgonly:
		c2.execute(insquery4, (entry[0], entry[1]))
c2.execute("COMMIT")
del nojpgonly
c2.execute("START TRANSACTION")
for entry in requestAndNojpg:
		c2.execute(insquery5, (entry[0], entry[1]))
c2.execute("COMMIT")
del requestAndNojpg
c2.execute("START TRANSACTION")
for entry in requestAndNoimg:
		c2.execute(insquery6, (entry[0], entry[1]))
c2.execute("COMMIT")
del requestAndNoimg

# MAIN TABLE POPULATED
# MOVE TABLES
print "Moving tables"
db2 = MySQLdb.connect(db='u_alexz', host="sql", read_default_file="/home/alexz/.my.cnf")
c2 = db2.cursor()
db = MySQLdb.connect(host="sql-s1", read_default_file="/home/alexz/.my.cnf")
c = db.cursor()
try:
	c2.execute("START TRANSACTION")
	c2.execute("DROP TABLE photocoords")
	c2.execute("COMMIT")
except:
	pass

c2.execute("START TRANSACTION")
c2.execute("""CREATE TABLE IF NOT EXISTS `photocoords` (
  `title` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT NULL,
  `coordinate` point NOT NULL,
  `reqphoto` tinyint(1) DEFAULT '0',
  `noimg` tinyint(1) DEFAULT '0',
  `nojpg` tinyint(1) DEFAULT '0',
  SPATIAL KEY `coordinate` (`coordinate`)
) ENGINE=MyISAM""")
c2.execute("COMMIT")

c2.execute("START TRANSACTION")
c2.execute("INSERT INTO `photocoords` SELECT * FROM `photocoords_2`")
c2.execute("COMMIT")

c2.execute("START TRANSACTION")
c2.execute("DROP TABLE `photocoords_2`")
c2.execute("COMMIT")

# TABLES MOVED
# CLEANUP
c.execute("START TRANSACTION")
c.execute("DROP TABLE u_alexz.catpages_tmp")
c.execute("COMMIT")

db.close()
db2.close()
