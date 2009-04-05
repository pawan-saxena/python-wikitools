#!/usr/bin/python
# -*- coding: utf-8 -*-
from wikitools import *
import MySQLdb
import datetime
import re
import os
import settings

unref = ['Unreferenced',
'Notverifiable',
'Unsourced',
'Unverified',
'Unref',
'References',
'Uncited-article',
'Unrefart',
'Citesources',
'NR',
'No references',
'Unreferencedart',
'Unrefarticle',
'Unreferenced article',
'Unreferenced art',
'Noref',
'Norefs',
'Noreferences',
'Unrefreenced',
'Cleanup-cite',
'References needed',
'Nr',
'No refs',
'UnreferencedArticle',
'UnreferenceArticle',
'No ref']

blpunref = ['BLP unsourced',
'UnsourcedBLP',
'BLPunreferenced',
'Unreferencedblp',
'Blpunsourced',
'Unsourcedblp', 
'BLPunsourced',
'BLPUnreferenced',
'Unsourced BLP'
]

unrefs = '|'.join(unref)
blpunrefs = '|'.join(blpunref)
initial = re.compile('\{\{('+unrefs+'|article issues|articleissues|Ai|issues)', re.I)
articleissues = re.compile('\{\{(Article ?issues|Ai|issues)(?P<content>[^\}]*)\}\}', re.I)
ai2 = re.compile('([^=\n\|\s]*)\s*=\s*([^\|\n]*)', re.I)
urt = re.compile('\{\{('+unrefs+')(?:\|\s*(?:date\s*=\s*)?(?P<date>[^\}]*))?\}\}\n?', re.I)
blpurt = re.compile('\{\{('+blpunrefs+')(?:\|\s*(?:date\s*=\s*)?(?P<date>[^\}]*))?\}\}', re.I)
rmdate = re.compile('date\s*=\s*', re.I)

try:
	os.remove('blpcaterrs.txt')
except:
	pass
err = open('blpcaterrs.txt', 'ab')

site = wiki.Wiki()
site.login(settings.bot, settings.botpass)

def main():
	f = open('../wrongcats.txt', 'rb')
	count = 0
	for line in f:
		p = page.Page(site, line.rstrip("\n"))
		text = p.getWikiText()
		# Get article issues template
		ai = articleissues.search(text)
		aiinner = None
		if ai:
			aiinner = dict(ai2.findall(ai.group('content')))
			if 'unref' in aiinner:
				aiinner['unreferenced'] = aiinner['unref']
			if not 'unreferenced' in aiinner:
				ai = None
			if 'section' in aiinner:
				ai = None
		# Get the unrefernced template
		unreftemp = urt.search(text)
		if unreftemp and 'date' in unreftemp.groupdict() and 'section' in unreftemp.group('date'):
			unreftemp = None
		if len(urt.findall(text)) > 1:
			logErr("Multiple {{tl|unreferenced}} found on page", p)
			continue
		if len(articleissues.findall(text)) > 1:
			logErr("Multiple {{tl|article issues}} found on page", p)
			continue
		# Look for a BLP unsourced template
		blpunreftemp = blpurt.search(text)
		# Get the date from one of the templates
		timestamp = False
		if unreftemp and 'date' in unreftemp.groupdict():
			d = unreftemp.group('date')
			if isValidTime(d):
				timestamp = d.strip()
			elif len(d.split('|')) > 1:
				for s in d.split('|'):
					d2 = rmdate.sub('', s)
					if isValidTime(d2):
						timestamp = d2.strip()
						break
		if ai and not timestamp and 'unreferenced' in aiinner:
			if isValidTime(aiinner['unreferenced']):
				timestamp = aiinner['unreferenced'].strip()
		# Remove or add templates as necessary
		newtext = ''
		if blpunreftemp and ai and unreftemp:               # All 3
			newtext = removeFromAI(aiinner, text)
			newtext = removeUnref(newtext)
		elif blpunreftemp and not ai and unreftemp:         # BLPur and unreferenced
			newtext = removeUnref(text)
		elif blpunreftemp and ai and not unreftemp:         # BLPur and AI
			newtext = removeFromAI(aiinner, text)
		elif blpunreftemp and not ai and not unreftemp:     # Only BLPur
			continue
		elif not blpunreftemp and ai and unreftemp:         # AI and unreferenced
			newtext = removeFromAI(aiinner, text)
			newtext = removeUnref(newtext)
			newtext = addBLPUR(newtext, timestamp, aiinner)
		elif not blpunreftemp and not ai and unreftemp:     # Only unreferenced
			newtext = removeUnref(text)
			newtext = addBLPUR(newtext, timestamp, False)
		elif not blpunreftemp and ai and not unreftemp:     # Only AI
			newtext = removeFromAI(aiinner, text)
			newtext = addBLPUR(newtext, timestamp, aiinner)
		elif not blpunreftemp and not ai and not unreftemp: # Nothing
			logErr("No template found to remove", p)
			continue
		if text == newtext:
			logErr("No change made", p)
			continue
		p.edit(text=newtext, summary="Unreferenced BLP", minor=True, bot=True)
			
def isValidTime(timestamp):
	try:
		datetime.datetime.strptime(timestamp.strip(), "%B %Y")
		return True
	except:
		return False
	
def removeFromAI(aiinner, text):
	del aiinner['unreferenced']
	if 'unref' in aiinner:
		del aiinner['unref']
	newai = "{{article issues"
	for issue in aiinner.keys():
		newai += "\n| "+issue+ " = "+aiinner[issue]
	newai += "\n}}"
	text = articleissues.sub(newai, text)
	return text

def removeUnref(text):
	return urt.sub('', text)
	
def addBLPUR(text, timestamp, aiinner):
	if not timestamp:
		timestamp = datetime.datetime.now().strftime('%B %Y')
	if aiinner:
		aiinner['BLPunsourced'] = timestamp
		newai = "{{article issues"
		for issue in aiinner.keys():
			newai += "\n| "+issue+ " = "+aiinner[issue]
		newai += "\n}}"
		text = articleissues.sub(newai, text)
		return text
	else:
		template = "{{BLP unsourced|date=%s}}\n" % timestamp
		text = template+text
		return text
			
def logErr(msg, p=False):
	title = "Error"
	if p:
		title = "[[%s]]" % p.title
	err.write('; %s : %s \n' % (title, msg))		

if __name__ == "__main__":
	main()
	err.close()
