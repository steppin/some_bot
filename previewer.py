import sys
import urllib
import cStringIO
from os import listdir
from json import load
from PIL import Image
map = {}
sprites = {}
WALLS = ["45", "135", "225", "315", "wall"]
fails = 0
TILE_SIZE = 40
SIZE_LIMIT = 100*100
def usage():
    print >> sys.stderr, 'Usage: {} PNG JSON [SPLATS] > PREVIEW'.format(
        sys.argv[0])
rgbs = {
	(0, 0, 0): "black",
	(120, 120, 120): "wall",
	(55, 55, 55): "spike",
	(255, 0, 0): "redflag",
	(0, 0, 255): "blueflag",
	(128, 128, 0): "yellowflag",
	(212, 212, 212): "floor",
	(0, 117, 0): "gate",
	(185, 122, 87): "button",
	(0, 255, 0): "topspeed",
	(255, 255, 0): "boost",
	(255, 128, 0): "bomb",
	(220, 186, 186): "red_speed_tile",
	(187, 184, 221): "blue_speed_tile",
	(202, 192, 0): "portaloff",
	(155, 0,  0): "redball",
	(0, 0, 155): "blueball",
	(255, 115, 115): "red_boost",
	(115, 115, 255): "blue_boost",
	(185, 0, 0): "red_endzone",
	(25, 0, 148): "blue_endzone",
	(128, 112, 64): "45",
	(64, 128, 80): "135",
	(64, 80, 128): "225",
	(128, 64, 112): "315"
}
# Er good class use?
class Map():
# Sprite directory
    sprite_list = listdir("sprites/")
    if 'Thumbs.db' in sprite_list:
        sprite_list.remove('Thumbs.db')
    for pic in sprite_list:
        sprites[pic] = Image.open("sprites/"+pic)
	# Odd Indentation Error
	def __init__(self, pngpath, jsonpath):
		if 'http' in pngpath:
			png_handle = cStringIO.StringIO(urllib.urlopen(pngpath).read())
			png = Image.open(png_handle)
		else:
			png = Image.open(pngpath)
		if png.mode != 'RGBA':
			png = png.convert('RGBA')
		self.png = png
		self.max_x, self.max_y = self.png.size
		if self.max_x * self.max_y > SIZE_LIMIT:
			error_msg = "Image '{}' is too large. Limit is {} px, but it is {}x{}.".format(
				pngpath, SIZE_LIMIT, self.max_x, self.max_y)
			raise ValueError(error_msg)
		self.pixels = png.load()
		self._preview = None
		self.portal_entrances = []
		if 'http' in jsonpath:
			json_file = urllib.urlopen(jsonpath)
			self.json = load(json_file)
		else:
			with open(jsonpath) as fp:
				self.json = load(fp)
	def adj_walls(x, y, paste):
		corr_adj = {
			"U": [(128, 112, 64), (128, 64, 112), (120, 120, 120)],
			"R": [(128, 112, 64), (64, 128, 80), (120, 120, 120)],
			"D": [(64, 128, 80), (64, 80, 128), (120, 120, 120)],
			"L": [(64, 80, 128), (128, 64, 112), (120, 120, 120)]
		}
		adj = paste
		# If within boundaries
			# If wall dir corresponds
				# Exclude wall type duplicates - Experimental 50% Success at catching odd 45s
					# Add dir string
		if y != 0:
			if pixels[x,y-1] in corr_adj["U"]:
				if ('315' and '45') not in adj:
					adj += "U"
		if x != self.max_x-1:
			if pixels[x+1,y] in corr_adj["R"]:
				if '135' not in adj:
					adj += "R"
		if y != self.max_y-1: 
			if pixels[x,y+1] in corr_adj["D"]:
				if '135' not in adj:
					adj += "D"
		if x != 0:
			if pixels[x-1,y] in corr_adj["L"]:
				if '225' and '315' not in adj:
					adj += "L"
		return adj
	def draw(pixels, data):
		img = Image.new("RGB", (self.max_x*40,self.max_y*40), "white")
		for w in range(self.max_x):
			for h in range(self.max_y):
				map[(w,h)] = rgbs[pixels[w,h]]

		for item in map:
			paste = map[item]
			if paste == 'gate':
				cord_key = "%d,%d" % (item[0], item[1])
				if cord_key in data['fields']:
					if data['fields'][cord_key]['defaultState'] != 'off':
						paste = data['fields'][cord_key]['defaultState']+"_gate"
			if paste == 'portaloff':
				cord_key = "%d,%d" % (item[0], item[1])
				try:
					if "destination" in data['portals'][cord_key]:
						paste = "portal"
				except KeyError:
					pass
			if paste in WALLS:
			    # Good Function call?
				paste = adj_walls(item[0], item[1], paste)
			if paste+'.png' in sprites:	
				img.paste(sprites[paste+'.png'],(item[0]*TILE_SIZE,item[1]*TILE_SIZE))
			else:
				fails += 1
            if 'marsballs' in data:
	            for mars in range(len(data['marsballs'])):
		        img.paste(sprites['marsball.png'],(data['marsballs'][mars]['x']*TILE_SIZE, data['marsballs'][mars]['y']*TILE_SIZE))
        # Good return?
        return img
def main():
    if len(sys.argv) < 3:
        usage()
        return 1
    # Removed anything with splats, wasn't sure if neccessary 
    png_path = sys.argv[1]
    json_path = sys.argv[2]
    # Good calls and returns?
    map_ = Map(png_path, json_path)
    preview = map_.draw(png_path, json_path) 
    sys.stdout.write(preview.getvalue())
	
if '__main__' == __name__:
    status = main()
    sys.exit(status)
