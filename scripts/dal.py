# -*- coding: utf-8 -*-
from wikitools import *
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import settings, datetime, re, htmlentitydefs, urllib, codecs, smtplib, sys

TFAreg = re.compile(".*?('''\[\[.*?)\|more\.\.\.\]\]'''\)", re.I|re.S)
TFAtitle = re.compile("\('''\[\[(.*?)\|more\.\.\.\]\]'''")
anivreg = re.compile("'''\s?\[\[(.*?)\]\]\s?'''")
anivyear = re.compile("\{\{\*mp\}\}\s?\[\[(\d*)\]\] &ndash;")
anivpicture = re.compile("\([^\)]*?pictured\) ", re.I)
quotename = re.compile("~ \[\[(.*?)\]\].*")

boldtext = re.compile("'''(.*?)'''")
italic = re.compile("''(.*?)''", re.U)
pipelinks = re.compile("\[\[[^\|\]]+?\|([^\]]+?)\]\]")
links = re.compile("\[\[([^\]]+?)\]\]")
comments = re.compile("<!--.*?-->")
linebreaks = re.compile("<\s*(br|p)\s*\/?\s*>", re.I)
htmltags = re.compile(r"<\s*(span|div|p|b|i|small|s|tt|strike|u|font|sub|sup|nowiki)(?: .*?)?>(.*?)<\s*\/\1\s*>", re.I)
entities = re.compile("\&([^;]{3,6}?);")

enwiki = wiki.Wiki()
enwiki.login(settings.admin, settings.adminpass)

enquote = wiki.Wiki("http://en.wikiquote.org/w/api.php")
enwikt = wiki.Wiki("http://en.wiktionary.org/w/api.php")

def main():
	try:
		tomorrow = datetime.date.today() + datetime.timedelta(days=1)
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
		import webbrowser, traceback
		f = open("AAA_DAL_ERROR.log", "wb")
		traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2], None, f)
		f.close()
		webbrowser.open("AAA_DAL_ERROR.log")

def sendEmail(mail, subj):
	fromaddr = "***"
	toaddr = ["***", "***"]
	msg = MIMEMultipart()
	msg.set_charset('utf-8')
	msg['From'] = fromaddr
	msg['To'] = toaddr[0]
	msg['Cc'] = toaddr[1]
	msg['Subject'] = subj
	msg.attach(MIMEText(mail.encode('utf-8'), 'plain', 'utf-8'))
	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.ehlo()
	server.starttls()
	server.ehlo()
	server.login(settings.email, settings.emailpass)
	body = msg.as_string()
	server.sendmail(fromaddr, toaddr, body)
	server.quit()	
	
def makeDAL(article, anivs, word, quote):
	mail = unicode('', 'utf8')
	TFAtitle = article.keys()[0]
	TFAtext = article[TFAtitle]
	linktext = urllib.quote(TFAtitle.replace(' ', '_'))
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
		mail += unicode(aniv) + ':\n\n'
		mail += anivs[aniv]['text'] + '\n'
		linktext = urllib.quote(anivs[aniv]['title'].replace(' ', '_'))
		mail += '<http://en.wikipedia.org/wiki/%s>\n' % (linktext)
	mail += '\n'
	mail += '_____________________________\n'
	mail += "Wiktionary's word of the day:\n\n"
	wotd = word.keys()[0]
	mail += "%s (%s):\n" % (wotd, word[wotd]['type'])
	mail += word[wotd]['definition'] + '\n'
	linktext = urllib.quote(wotd.replace(' ', '_'))
	mail += '<http://en.wiktionary.org/wiki/%s>\n\n' % (linktext)
	mail += '___________________________\n'
	mail += 'Wikiquote quote of the day:\n\n'
	name = quote.keys()[0]
	mail += quote[name]
	mail += '   --'+name.decode('utf-8')+'\n'
	linktext = urllib.quote(name.replace(' ', '_'))
	mail += '<http://en.wikiquote.org/wiki/%s>\n\n\n\n' % (linktext)
	return mail
	
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
	text = killFormatting(text)
	return {name:text.strip()}
	
def getWOTD(WOTD):
	p = page.Page(enwikt, WOTD)
	if not p.exists:
		raise Exception("ERROR: Word of the day doesn't exist O_o")
	text = p.getWikiText()
	bits = text.split('|')
	word = bits[1]
	type = bits[2]
	definition = killFormatting(bits[3])
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
	text = text.split('<div style="float:right;margin-left:0.5em">')[1]
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
		year = int(anivyear.search(line).group(1))
		text = anivyear.sub('', line)
		text = killFormatting(text)
		text = anivpicture.sub('', text)
		anivs[year] = {'title':title, 'text':text.strip()}	
	return anivs

def getTFA(TFA):
	p = page.Page(enwiki, TFA)
	if not p.exists:
		raise Exception("ERROR: TFA doesn't exist O_o")
	text = p.getWikiText(expandtemplates=True)
	title = TFAtitle.search(text).group(1)
	text = TFAreg.sub(r'\1', text)
	text = text.rsplit("('''", 1)[0]
	TFA = {title: killFormatting(text).strip()}
	return TFA
	
def killFormatting(text):
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
	text = htmltags.sub(r'\2', text)
	# wtf?
	text = entities.sub(replaceEntities, text)
	return text.replace('  ', ' ')

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