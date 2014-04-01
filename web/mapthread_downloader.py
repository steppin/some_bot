import requests
from bs4 import BeautifulSoup as bs
import re
import praw
import json

'''
Given a map thread, parses comments to get urls, downloads png and json data, posts data as 
request to some_bot_server to upload map data
'''

map_thread = "http://www.reddit.com/r/TagPro/comments/20usrv/monthly_map_rotation_thread_26/"

def get_json_png_urls(comments, links=None):
	if not links:
		links = []
	for index, comment in enumerate(comments):
		try:
			comment_links = re.findall(r'href="(.*?(imgur|pastebin|lpaste).*?)"', comment.body_html)
			if comment_links:
				links.append(comment_links)
			else:
				print "Couldn't find links in comment: ", comment
		except:
			if type(comment) == 'praw.objects.MoreComments':
				get_json_png_urls(comment.comments(), links)
	return links


reddit = praw.Reddit("TagPro Mapthread Parser")
comment_links = get_json_png_urls(reddit.get_submission(map_thread, comment_limit=200).comments)

total = 0
failed = 0
failed_links = []
for links in comment_links:
	# This is the 'map' level
	json_data = None
	png_data = None
	for link in links:
		# links is a list of links from each comment
		# Instead of trying to parse the comment,
		# grab the links in the comment, download the pastebin,
		# and grab the imgur link. Test the size, if it's smaller than
		# a set amount (15 kB), it's likely the png file so use it 
		url, host = link
		if host == "pastebin":
			paste_id = url.split("/")[-1].split("=")[-1]
			json_url = "http://pastebin.com/raw.php?i="+paste_id
			json_data = requests.get(json_url).text
		elif host == "lpaste":
			paste_id = url.split("/")[-1]
			json_url = "http://lpaste.net/raw/"+paste_id
			json_data = requests.get(json_url).text
		elif host == "imgur":
			# Need to get png file and not preview file
			if url[-4:].lower() != ".png":
				url += ".png"
			r = requests.get(url)
			size = r.headers['content-length']
			# Filter by image size to determine if png or preview
			if int(size) < 15000:
				png_data = r.content

	if png_data and json_data:
		json_info = json.loads(json_data)['info']
		mapname = json_info['name']
		print "Posting %s...." %(mapname)
		files = {"logic":json_data, "layout":png_data}
		r = requests.post("http://localhost:5000/", data={"mapname":mapname}, files=files)
		print "Status: ", r.status_code
		total += 1
	else:
		failed_links.append(links)
		failed += 1

print "Successfully wrote %s files... %s failed" %(total, failed)
print "Couldn't load the following urls:\n%s\n" %("\n".join(map(lambda x: "\t"+x[0], links)))
