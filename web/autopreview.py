import os
import previewer
import glob
import sys
from multiprocessing import Pool
import itertools

OUT_DIR = os.path.abspath("./static/previews/")
MAP_DIR = os.path.abspath("./static/maps/")

def generate_previews(pngpath):
	file_name = os.path.splitext(pngpath)[0]
	base_name = os.path.basename(pngpath)
	jsonpath = file_name+".json"
	print file_name
	if not os.path.isfile(jsonpath):
		print "Unable to find json for %s" %base_name
		return None

	try:
		map_ = previewer.Map(pngpath, jsonpath)
		preview = map_.preview()
		with open(OUT_DIR+os.sep+base_name, 'wb') as f:
			f.write(preview.getvalue())
			print "[ ] Wrote %s successfully" %base_name
	except:
		print "[X] Problem with %s" %(pngpath)
		pass

if __name__ == "__main__":
	import sys
	if len(sys.argv) != 2:
		numprocesses = 4
	else:
		numprocesses = int(sys.argv[-1])


	png_files = glob.glob(MAP_DIR+os.sep+"*.png")
	p = Pool(numprocesses)
	p.map(generate_previews, png_files)
