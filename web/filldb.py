import sqlite3
import simplejson as json
import os
import time
import glob

import previewer

OUTPUT_MAPDIR = os.path.abspath("./static/maps/")

def connect_db(dbname):
    rv = sqlite3.connect(dbname)
    rv.row_factory = sqlite3.Row
    return rv

def get_db(dbname='maps.db'):
	return connect_db(dbname)

def add_map_to_db(mapname, author, description):
	db = get_db()
	insert_time = time.time()
	db.execute('insert into maps (mapname, upload_time, times_tested, last_tested) values (?, ?, 0, 0)', [mapname, insert_time])
	db.commit()
	cur = db.execute("select id from maps where upload_time = (?)", [insert_time])
	mapid = cur.fetchall()[0][0]
	print "ID: %s Mapname: %s Author: %s" %(mapid, mapname, author)
	db.execute("insert into search (docid, mapname, author, description) values (?, ?, ?, ?)", [mapid, mapname, author, description])
	db.commit()
	return str(mapid)

def write_files(mapid, jsonpath, pngpath):
	outjson = os.path.join(OUTPUT_MAPDIR, str(mapid)+'.json')
	outpng = os.path.join(OUTPUT_MAPDIR, str(mapid)+'.png')
	with open(outpng, 'wb') as f:
		f.write(open(pngpath).read())
	with open(outjson, 'wb') as f:
		f.write(open(jsonpath).read())

def find_maps(mapdir):
	mapdir = os.path.expanduser(mapdir)
	start = time.time()
	successes, failures = 0,0
	maps = glob.glob(mapdir+os.sep+"*.json")

	print "Total maps: %s" %len(maps)

	for index, jsonpath in enumerate(glob.glob(mapdir+"*.json")):
		root = os.path.splitext(jsonpath)[0]
		pngpath = root+".png"
		if os.path.isfile(pngpath):
			try:
				logic_data = json.loads(open(jsonpath).read())
				mapname = logic_data.get('info', {}).get('name')
				author = logic_data.get('info', {}).get('author')
				description = logic_data.get('info', {}).get('description')
				if mapname:
					mapid = add_map_to_db(mapname, author, description)
					print "Added %s:%s to database..." %(mapname, author)
					if mapid:
						write_files(mapid, jsonpath, pngpath)
						successes += 1
				else:
					failures += 1
			except:
				failures += 1
				pass
		else:
			failures += 1

		print "[%s] Successes: %s Failures %s" %(index, successes, failures)
		
	end = time.time()

if __name__ == "__main__":
	import sys
	if len(sys.argv) == 2:
		mapdir = sys.argv[1]
		find_maps(mapdir)
	else:
		print "Usage: python filldb.py MAPDIR"
		exit()
