#!/usr/bin/python
# -*- coding: utf-8 -*-
import MySQLdb

class ProjectLister(object):

	__slots__ = ('projects')
	
	def __init__(self):
		db = MySQLdb.connect(host="sql", read_default_file="/home/alexz/.my.cnf", db='u_alexz')
		cursor = self.db.cursor()
		cursor.execute('SELECT * FROM project_config')
		res = cursor.fetchall()
		self.projects = {}
		for item in res:
			self.projects[item[0]] = Project(item)
			
class Project(object):

	__slots__ = ('abbrv', 'name', 'cat_name', 'listpage', 'limit')

	def __init__(self, row):
		self.abbrv = row[0]
		self.name = row[1]
		self.cat_name = row[2]
		self.listpage = row[3]
		self.limit = row[4]
