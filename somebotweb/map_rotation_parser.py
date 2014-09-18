from bs4 import BeautifulSoup as bs
import requests
from redis import Redis

def get_maps(url='http://www.reddit.com/r/TagPro/wiki/index', tagid='wiki_current_rotation', tags=['']):
	'''
	Parse table of maps from reddit's tagpro index, unless otherwise chosen (although this will break)
	'''

	r = requests.get(url)
	soup = bs(r.text)

	# Grab the header with the tagid we want, this will let us find the unlabeled table
	header = soup.findAll('h3', {'id':tagid})[0]

	table = header.find_next_sibling('table')
	# Find all cells in the table that aren't in the header
	maps = table.findAll('td')

	parsed_maps = []
	for m in maps:
		# We want the map name and the map url, so we'll grab ones with text
		# The table goes "row of images, row of links w/ names, row of images"
		if m.text:
			name = m.text
			url = m.find('a').get('href')
			name = name.title().replace('Motw', 'MOTW')
			parsed_maps.append( {'name':name, 'url':url, 'tags':tags})

	# Sort so the MOTWs are at the top of the list so they get the most exposure
	parsed_maps.sort(key=lambda x: 'motw' not in x.get('name').lower())
	return parsed_maps

if __name__ == "__main__":
	maps = get_maps(tags=['current'])
	maps.extend(get_maps(tagid='wiki_retired_maps', tags=['retired']))
	print maps