#!/usr/bin/python
# -*- coding: utf-8 -*-
from wikitools import *
from email.MIMENonMultipart import MIMENonMultipart
from email.MIMEText import MIMEText
import settings, datetime, re, htmlentitydefs, urllib, codecs, smtplib, sys

TFAreg = re.compile(".*?\n([^\n]*'''\[\[.*?)\|more\.\.\.\]\]'''\)", re.I|re.S)
TFAregalt = re.compile("([^\n]*'''\[\[.*?)\|more\.\.\.\]\]'''\)", re.I|re.S)
TFAtitle = re.compile("\('''\[\[(.*?)\|more\.\.\.\]\]'''")
anivreg = re.compile("'''\s?\"?\[\[(.*?)\]\][a-z]?\"?[\.\,]?\s?'''")
anivyear = re.compile("\{\{\*mp\}\}\s*\[\[(?P<year>[0-9]*)(?P<suf> AD| CE| BC| BCE)?\]\] +(&ndash;|–)")
anivpicture = re.compile("\([^\)]*?pictured\)", re.I)
quotename = re.compile("~ .*?\[\[(.*?)\]\].*")

boldtext = re.compile("'''(.*?)'''", re.DOTALL)
italic = re.compile("''(.*?)''", re.DOTALL)
pipelinks = re.compile("\[\[[^\|\]]+?\|([^\]]+?)\]\]")
links = re.compile("\[\[([^\]]+?)\]\]")
comments = re.compile("<!--.*?-->", re.DOTALL)
linebreaks = re.compile("<\s*(br|p)\s*\/?\s*>", re.I)
htmltags = re.compile(r"<\s*(span|div|p|b|i|small|s|tt|strike|u|font|sub|sup|nowiki)(?P<attribs> .*?)?>(?P<value>.*?)<\s*\/\1\s*>", re.I|re.DOTALL)
entities = re.compile("\&([^;]{3,6}?);")
displaynone = re.compile("display\: *none", re.I)

enwiki = wiki.Wiki()
enwiki.setMaxlag(70)
enquote = wiki.Wiki("http://en.wikiquote.org/w/api.php")
enwikt = wiki.Wiki("http://en.wiktionary.org/w/api.php")

def expandtemplates(text, site):
	params = {'action':'expandtemplates',
		'title':'Main Page',
		'text':text
	}
	if site == enwikt:
		params['title'] = 'Wiktionary:Main Page'
	req = api.APIRequest(site, params)
	res = req.query()
	return res['expandtemplates']['*']

def main():
	try:
		tomorrow = datetime.date.today()
		year = tomorrow.year
		day = tomorrow.day
		month = tomorrow.strftime("%B")
		TFA = "Wikipedia:Today's featured article/%s %d, %d" % (month, day, year)
		SA = "Wikipedia:Selected anniversaries/%s %d" % (month, day)
		WOTD = "Wiktionary:Word of the day/%s %d" % (month, day)
		year = year-1
		QOTD = "Wikiquote:Quote of the day/%s %d, %d" % (month, day, year)
		article = getTFA(TFA)
		anivs = getanivs(SA)
		word = getWOTD(WOTD)
		quote = getQuote(QOTD)
		mail = makeDAL(article, anivs, word, quote)
		f = codecs.open("DALtest.txt", 'wb', 'utf8')
		f.write(mail)
		f.close()
		title = article.keys()[0]
		subject = "%s %d: %s" % (month, day, title)
		sendEmail(mail, subject)
	except:
		import traceback
		traceback.print_exc()

def sendEmail(mail, subj):
	fromaddr = "mrzmanwiki@gmail.com"
	toaddr = ["daily-article-l@lists.wikimedia.org", "mrzmanwikimail@gmail.com"]
	#toaddr = ["mrzmanwikimail@gmail.com"]
	msg = MIMENonMultipart('text', 'plain')
	msg['Content-Transfer-Encoding'] = '8bit'
	msg.set_payload(mail.encode('utf8'), 'utf-8')
	msg['From'] = fromaddr
	msg['To'] = toaddr[0]
	msg['Subject'] = subj
	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.ehlo()
	server.starttls()
	server.ehlo()
	server.login(settings.email, settings.emailpass)
	body = msg.as_string()
	server.sendmail(fromaddr, toaddr[0], body, '8bitmime')
	msg['To'] = toaddr[1]
	body = msg.as_string()
	server.sendmail(fromaddr, toaddr[1], body, '8bitmime')
	server.quit()	
	
def makeDAL(article, anivs, word, quote):
	mail = unicode('', 'utf8')
	TFAtitle = article.keys()[0]
	TFAtext = breaklines(article[TFAtitle])
	linktext = preparelink(TFAtitle)
	mail += TFAtext
	mail += '\n\n'
	mail += 'Read the rest of this article:\n'
	mail += '<http://en.wikipedia.org/wiki/%s>\n\n' % (linktext)
	mail += '_______________________________\n'
	mail += "Today's selected anniversaries:\n"
	years = anivs.keys()
	years.sort()
	for aniv in years:
		mail += '\n'
		y = ''
		if aniv < 0:
			y = str(aniv * -1) + ' BC'
		else:
			y = str(aniv)
		mail += unicode(y) + ':\n\n'
		mail += breaklines(anivs[aniv]['text']) + '\n'
		linktext = preparelink(anivs[aniv]['title'])
		mail += '<http://en.wikipedia.org/wiki/%s>\n' % (linktext)
	mail += '\n'
	mail += '_____________________________\n'
	mail += "Wiktionary's word of the day:\n\n"
	wotd = word.keys()[0]
	mail += "%s (%s):\n" % (wotd.decode('utf8'), word[wotd]['type'])
	mail += breaklines(word[wotd]['definition']).replace('\n\n', '\n') + '\n'
	linktext = preparelink(wotd)
	mail += '<http://en.wiktionary.org/wiki/%s>\n\n' % (linktext)
	mail += '___________________________\n'
	mail += 'Wikiquote quote of the day:\n\n'
	name = quote.keys()[0]
	mail += breaklines(quote[name])
	mail += '\n   --'+name.decode('utf-8')+'\n'
	linktext = preparelink(name)
	mail += '<http://en.wikiquote.org/wiki/%s>\n\n\n\n' % (linktext)
	mail = mail.replace('  ', ' ')
	return mail

def preparelink(text):
	text = killFormatting(text)
	text = text.replace(' ', '_')
	return urllib.quote(text.encode('utf8'))
	
def breaklines(text):
	ret = []
	while text:
		try:
			line = ''
			for i in range(0,72):
				if text[i] == '\n':
					line = text[0:i]
					if line:
						text = text.split(line)[1]
						ret.append(line)
					break
			if not line:
				for x in range(1,72):
					index = 72-x
					if text[index] == ' ':
						line = text[0:index+1]
						text = text.split(line)[1]
						ret.append(line)
						break
		except IndexError:
			ret.append(text)
			break
	return '\n'.join(ret)		
	
def getQuote(QOTD):
	p = page.Page(enquote, QOTD)
	if not p.exists:
		raise Exception("ERROR: Quote of the day doesn't exist O_o")
	text = p.getWikiText()
	lines = text.splitlines()
	text = lines[3]
	if len(text) < 30:
		text = lines[4]
	text = text.split('| align=center |')[1]
	name = quotename.search(text).group(1)
	if '|' in name:
		name = name.split('|')[0]
	text = quotename.sub('', text)
	text = killFormatting(expandtemplates(text, enquote))
	return {name:text.strip()}
	
def getWOTD(WOTD):
	p = page.Page(enwikt, WOTD)
	if not p.exists:
		raise Exception("ERROR: Word of the day doesn't exist O_o")
	text = p.getWikiText()
	bits = text.split('|')
	word = bits[1]
	type = bits[2]
	definition = killFormatting(expandtemplates(bits[3], enwikt))
	if len(definition.splitlines()) != 1:
		totaldef = ''
		lines = definition.splitlines()
		for line in lines:
			totaldef += str(lines.index(line)+1)+". "+ line.lstrip(' #') + "\n"
		definition = totaldef
	WOTD = {word: {'type':type, 'definition':definition.strip()}}
	return WOTD
	
def getanivs(SA):
	p = page.Page(enwiki, SA)
	if not p.exists:
		raise Exception("ERROR: Selected Aniv. doesn't exist O_o")
	text = p.getWikiText()
	text = re.split('\<div style\=\"(?:margin\-left\:(?:0\.5|1)em;? ?|float\:right\;? ?){2}">', text)[1]
	text = comments.sub('', text)
	lines = text.splitlines()		
	lines2 = []
	for line in lines:
		if line.startswith('{{*mp}}'):
			lines2.append(line)
	anivs = {}
	for line in lines2:
		title = anivreg.search(line).group(1)
		if '|' in title:
			title = title.split('|')[0]
		res = anivyear.search(line)
		year = int(res.group('year'))
		mod = str(res.group('suf'))
		if 'bc' in mod.lower():
			year = year * -1
		text = anivyear.sub('', line)
		text = killFormatting(expandtemplates(text, enwiki))
		text = anivpicture.sub('', text)
		anivs[year] = {'title':title, 'text':text.strip()}	
	return anivs

def getTFA(TFA):
	p = page.Page(enwiki, TFA)
	if not p.exists:
		raise Exception("ERROR: TFA doesn't exist O_o")
	text = p.getWikiText(expandtemplates=True)
	title = TFAtitle.search(text).group(1)
	TFAtext = TFAreg.sub(r'\1', text)
	TFAtext = TFAtext.rsplit("('''", 1)[0]
	if len(TFAtext < 10):
		TFAtext = TFAregalt.sub(r'\1', text)
		TFAtext = TFAtext.rsplit("('''", 1)[0]
	pt = page.Page(enwiki, title)
	TFA = {pt.title: killFormatting(TFAtext).strip()}
	return TFA
	
def killFormatting(text):
	if not isinstance(text, unicode):
		text = text.decode('utf8')
	# Start with the easy stuff:
	text = boldtext.sub(r'\1', text)
	text = italic.sub(r'\1', text)
	text = comments.sub('', text)
	# not too hard
	text = pipelinks.sub(r'\1', text)
	text = links.sub(r'\1', text)
	# harder
	text = linebreaks.sub('\n', text)
	text = htmltags.sub(replacetags, text)
	# wtf?
	text = entities.sub(replaceEntities, text)
	return text.replace('  ', ' ')

def replacetags(matchobj):
	attribs = matchobj.group('attribs')
	if attribs and displaynone.search(attribs):
		return ''
	return matchobj.group('value')

def replaceEntities(matchobj):
	code = matchobj.group(1)
	num = 0
	if code.startswith('#x'):
		try:
			num = int(code.replace('#x', ''), 16)
		except:
			pass
	if not num and code.startswith('#'):
		try:
			num = int(code.replace('#', ''))
		except:
			pass
	try:
		num = int(htmlentitydefs.name2codepoint[code])
	except:
		pass
	try:
		return unichr(num)
	except:
		return matchobj.group(0)		

if __name__ == '__main__':
	main()
