#!/usr/bin/python
# -*- coding: utf-8 -*-
import MySQLdb
import os

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

while True:
	try:
		cat = catstodo.pop()
	except:
		print catstodo
		break
	print "Getting subcats for %s" % (cat)
	l = c.execute(query, (cat))
	catsdone.append(cat)
	if l == 0:
		continue
	cats = c.fetchall()
	for cat in cats:
		if not cat in catsdone and not cat in catstodo:
			catstodo.append(cat)
			f.write(cat[0] + '\n')
	if len( catstodo) == 0:
		break
f.close()

# CATEGORY LIST DONE
# GET TITLES
print "Getting titles"
c.execute("""CREATE TABLE IF NOT EXISTS u_alexz.catpages_tmp (
  `pageid` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  PRIMARY KEY  (`pageid`)
) ENGINE=InnoDB;
""")
c.execute("TRUNCATE TABLE u_alexz.catpages_tmp")

insquery = """INSERT IGNORE INTO u_alexz.catpages_tmp (pageid, title)
SELECT enwiki_p.page.page_title FROM enwiki_p.page
JOIN enwiki_p.categorylinks ON enwiki_p.page.page_id=enwiki_p.categorylinks.cl_from
WHERE enwiki_p.page.page_namespace=1 AND enwiki_p.categorylinks.cl_to=%s"""

f = open('../catlist.txt', 'rb')

lines = f.read()
lines = lines.splitlines()

for cat in lines:
	print "Getting pages in %s" % (cat)
	c.execute(insquery, (cat))

del lines
f.close()

# TITLES DONE
# JOIN AGAINST TEMPLATELINKS
print "Doing join"

joinquery = """SELECT u_alexz.catpages_tmp.title FROM u_alexz.catpages_tmp
JOIN enwiki_p.page ON enwiki_p.page.page_title = u_alexz.catpages_tmp.title
JOIN enwiki_p.templatelinks ON enwiki_p.templatelinks.tl_from=enwiki_p.page.page_id
WHERE enwiki_p.templatelinks.tl_namespace=10 AND enwiki_p.page.page_namespace=0
AND enwiki_p.templatelinks.tl_title in ("Coord", "Coor_URL")"""

c.execute(joinquery)
pages = set(c.fetchall())

# JOIN DONE
# POPULATE MAIN TABLE COPY
print "Making temp table"
db2 = MySQLdb.connect(db='u_alexz', host="sql", read_default_file="/home/alexz/.my.cnf")
c2 = db2.cursor()
insquery2 = """INSERT INTO u_alexz.photocoords_2 (title) VALUES (%s)"""

c2.execute("START TRANSACTION")
c2.execute("""CREATE TABLE IF NOT EXISTS `photocoords_2` (
  `title` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin,
  `latitude` float DEFAULT NULL,
  `longitude` float DEFAULT NULL,
  KEY `lat_long` (`latitude`,`longitude`),
  KEY `title` (`title`)
) ENGINE=InnoDB""")
c2.execute("COMMIT")

c2.execute("START TRANSACTION")
c2.execute("TRUNCATE TABLE photocoords_2")
c2.execute("COMMIT")

c2.execute("START TRANSACTION")
for entry in pages:
	c2.execute(insquery2, (entry[0]))
c2.execute("COMMIT")

# MAIN TABLE POPULATED
# GET COORDINATES
print "Getting coordinates"
c2.execute("START TRANSACTION")
c2.execute("TRUNCATE TABLE photoerrors")
c2.execute("COMMIT")
import photolocate
photolocate.main()

# GOT COORDINATES
# MOVE TABLES
print "Moving tables"
c2.execute("START TRANSACTION")
c2.execute("DROP TABLE photocoords")
c2.execute("COMMIT")

c2.execute("START TRANSACTION")
c2.execute("""CREATE TABLE IF NOT EXISTS `photocoords_2` (
  `title` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin,
  `latitude` float DEFAULT NULL,
  `longitude` float DEFAULT NULL,
  KEY `lat_long` (`latitude`,`longitude`),
) ENGINE=InnoDB""")
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
