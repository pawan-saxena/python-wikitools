# -*- coding: utf-8  -*-
import API
import Wiki
import re
import time

reg = re.compile("\[\[Measure[\s_]of[\s_]a[\s_]Man[\s_]\(album\)\]\]", re.I)
reg2 = re.compile("\[\[Measure[\s_]of[\s_]a[\s_]Man[\s_]\(album\)\|", re.I)
wiki = Wiki.Wiki()
wiki.login("username", "password")
params = {'action':'query',
	'list': 'backlinks',
	'bllimit': '500',
	'bltitle': 'Measure of a Man (album)'
}
req = API.APIRequest(wiki, params)
list = req.query()
params2 = {
	'action':'query',
	'prop':'info',
	'intoken':'edit',
	'titles':'Main Page'
}
req2 = API.APIRequest(wiki, params2)
token = req2.query()
token = token['query']['pages']['15580374']['edittoken']
i = 0
for item in list['query']['backlinks']:
	page = Wiki.Page(wiki, item['title'])
	text = page.getWikiText().encode('utf-8')
	text = reg.sub("[[Measure of a Man (Clay Aiken album)]]", text)
	text = reg2.sub("[[Measure of a Man (Clay Aiken album)|", text)
	print page.title
	time.sleep(5)
	editparams = {
		'action':'edit',
		'token':token,
		'title':page.title,
		'text':text,
		'minor':'1',
		'summary':'Fixing links so [[Measure of a Man (album)]] can be retargeted'
	}
	try:
		editreq = API.APIRequest(wiki, editparams)
		result = editreq.query()
		if result.has_key('edit'):
			print result['edit']['result']
		else:	
			print result
	except:
		pass