#!/usr/bin/env python
"""A preview generator for tagpro."""

from __future__ import division
import functools

import sys
import json
import urllib
import os.path
import cStringIO
import fractions
import itertools
import os


from PIL import Image, ImageDraw


TILE_SIZE = 40
SIZE_LIMIT = 100*100
RESOURCE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'resources'))


def usage():
    print >> sys.stderr, 'Usage: {} PNG JSON [SPLATS] > PREVIEW'.format(
        sys.argv[0])


def resource(f):
    return os.path.join(RESOURCE_DIR, f)

class Splat():
    def __init__(self, color, radius):
        width = height = radius * 2 + 1
        splat = Image.new("RGBA", (width, height))
        c = ImageDraw.ImageDraw(splat, "RGBA")
        (x, y) = (radius,) * 2
        c.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
        r, g, b, a = splat.split()
        self.splat = Image.merge("RGB", (r, g, b))
        self.mask = Image.merge("L", (a,))

    def paste_onto(self, im, coords):
        im.paste(self.splat, coords, self.mask)


class Map():
    tiles = Image.open(resource('tiles.png'))
    speedpad = Image.open(resource('speedpad.png'))
    speedpad_blue = Image.open(resource('speedpadblue.png'))
    speedpad_red = Image.open(resource('speedpadred.png'))
    portal = Image.open(resource('portal.png'))
    colormap = {
        'black': (0, 0, 0),
        'wall': (120, 120, 120),
        'tile': (212, 212, 212),
        'spike': (55, 55, 55),
        'button': (185, 122, 87),
        'powerup': (0, 255, 0),
        'gate': (0, 117, 0),
        'blueflag': (0, 0, 255),
        'redflag': (255, 0, 0),
        'yellowflag': (128, 128, 0),
        'blueendzone': (25, 0, 148),
        'redendzone': (185, 0, 0),
        'speedpad': (255, 255, 0),
        'bomb': (255, 128, 0),
        'bluetile': (187, 184, 221),
        'redtile': (220, 186, 186),
        'speedpadred': (255, 115, 115),
        'speedpadblue': (115, 115, 255),
        'portal': (202, 192, 0),
        'bluespawn': (0, 0, 155),
        'redspawn': (155, 0, 0),
    }
    coord_map = {colormap['speedpad']: (0, 0, speedpad),
                 colormap['speedpadred']: (0, 0, speedpad_red),
                 colormap['speedpadblue']: (0, 0, speedpad_blue),
                 colormap['bomb']: (6, 5, None),
                 colormap['redtile']: (3, 1, None),
                 colormap['bluetile']: (3, 2, None),
                 colormap['spike']: (2, 3, None),
                 colormap['button']: (2, 5, None),
                 colormap['powerup']: (7, 8, None),
                 colormap['blueflag']: (9, 0, None),
                 colormap['redflag']: (8, 0, None),
                 colormap['yellowflag']: (7, 0, None),
                 colormap['blueendzone']: (5, 2, None),
                 colormap['redendzone']: (5, 1, None),
                 colormap['redspawn']: (6, 2, None),
                 colormap['bluespawn']: (6, 3, None),
                 colormap['tile']: (2, 2, None),
                 }

    # Directions are N,S,E,W
    wall_dirs = {(True, True, True, True): (4, 4),
                 (True, True, True, False): (0, 4),
                 (True, True, False, True): (7, 4),
                 (True, True, False, False): (4, 2),
                 (True, False, True, True): (4, 8),
                 (True, False, True, False): (2, 8),
                 (True, False, False, True): (6, 8),
                 (True, False, False, False): (0, 6),
                 (False, True, True, True): (4, 0),
                 (False, True, True, False): (2, 0),
                 (False, True, False, True): (6, 0),
                 (False, True, False, False): (0, 2),
                 (False, False, True, True): (2, 4),
                 (False, False, True, False): (8, 6),
                 (False, False, False, True): (9, 6),
                 (False, False, False, False): (0, 0)}

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
                pngpath, SIZE_LIMIT, self.max_x, self.max_y
            )
            raise ValueError(error_msg)
        self.pixels = png.load()
        self._preview = None
        self.portal_entrances = []

        if 'http' in jsonpath:
            json_file = urllib.urlopen(jsonpath)
            self.json = json.load(json_file)
        else:
            with open(jsonpath) as fp:
                self.json = json.load(fp)

    def draw(self, (x, y), (i, j), tiles, preview, draw_background=False,
             source=None, draw_num_tiles=1):
        """Draws a square square size (x, y) from the source source
        onto preview at coordinates (i, j)"""

        if draw_background:
            im = tiles.crop((2 * TILE_SIZE, 2 * TILE_SIZE,
                             2 * TILE_SIZE + TILE_SIZE,
                             2 * TILE_SIZE + TILE_SIZE))

            # itertools.product simply returns all combinations from a
            # combination of iterables.
            # For a further usage look at self.all_coords, which eliminates
            # a double `for` loop and just gives us the x, y pairs we want.
            for c, d in itertools.product(xrange(i, i + draw_num_tiles),
                                          xrange(j, j + draw_num_tiles)):
                preview.paste(im, (int(c * TILE_SIZE), int(d * TILE_SIZE)))

        if not source:
            source = tiles

        x, y = x * TILE_SIZE, y * TILE_SIZE
        im = source.crop((
            x, y, x + draw_num_tiles * TILE_SIZE,
            y + draw_num_tiles * TILE_SIZE))
        preview.paste(im, (int(i * TILE_SIZE), int(j * TILE_SIZE)), im)

    @property
    def all_coords(self):
        return itertools.product(range(self.max_x), range(self.max_y))

    def _draw_under(self):
        green = []
        blue = []
        red = []
        draw = functools.partial(self.draw, tiles=self.tiles,
                                 preview=self._preview, draw_background=True)
        try:
            for point, state in self.json['fields'].iteritems():
                x, y = point.split(',')
                if state['defaultState'] == 'on':
                    l = green
                elif state['defaultState'] == 'red':
                    l = red
                elif state['defaultState'] == 'blue':
                    l = blue
                else:
                    continue
                l.append((int(x), int(y)))
        except KeyError:
            pass
        if 'portals' in self.json:
            portals = [z.split(",") for z in self.json['portals']]
            self.portal_entrances.extend((int(x), int(y)) for x, y in portals)

        for i, j in self.all_coords:
            try:
                source = None
                color = self.get_color(i, j)
                if color in self.coord_map:
                    a, b, source = self.coord_map[color]
                    draw((a, b), (i, j), source=source)
                elif color == self.colormap['portal']:
                    if (i, j) in self.portal_entrances:
                        a, b = 0, 0
                    else:
                        a, b = 4, 0
                    source = self.portal
                elif color == self.colormap['gate']:
                    if (i, j) in green:
                        a, b = 10, 2
                    elif (i, j) in red:
                        a, b = 10, 3
                    elif (i, j) in blue:
                        a, b = 10, 4
                    else:
                        a, b = 10, 1
                elif color == self.colormap['black']:
                    continue
                elif color == self.colormap['wall']:
                    continue
                else:
                    raise KeyError("Unknown RGB value {}".format(color))
                draw((a, b), (i, j), source=source)
            except KeyError as e:
                print >> sys.stderr, e

    def _draw_splats(self, splatfile):
        im = self._preview
        with open(splatfile) as f:
            splats = json.load(f)
        radius = 10
        opacity = 64
        color = {2: (0, 0, 255, opacity), 1: (255, 0, 0, opacity)}
        shift = 10

        red_splat = Splat(color[1], radius)
        blue_splat = Splat(color[2], radius)

        for splat in splats:
            x, y = splat['x'] + shift, splat['y'] + shift
            t = splat['t']
            if t == 1:
                red_splat.paste_onto(im, (x, y))
            elif t == 2:
                blue_splat.paste_onto(im, (x, y))

    def get_color(self, i, j):
        return self.pixels[i, j][:3]

    def get_wall(self, i, j):
        max_width = self.max_x - 1
        max_height = self.max_y - 1
        north, south, west, east = [False] * 4
        if j > 0:
            north = self.get_color(i, j - 1) == self.colormap[
                'wall']
        if j < max_height:
            south = self.get_color(i, j + 1) == self.colormap['wall']
        if i > 0:
            west = self.get_color(i - 1, j) == self.colormap['wall']
        if i < max_width:
            east = self.get_color(i + 1, j) == self.colormap['wall']
        return self.wall_dirs[(north, south, east, west)]

    def _draw_over(self):
        draw = functools.partial(self.draw, tiles=self.tiles,
                                 preview=self._preview, draw_background=False)
        marsballs = []
        if 'marsballs' in self.json:
            marsballs.extend((int(coordinates['x']), int(coordinates['y']))
                             for coordinates in self.json['marsballs'])

        for i, j in self.all_coords:
            try:
                source = None
                color = self.get_color(i, j)
                if color == self.colormap['wall']:
                    a, b = self.get_wall(i, j)
                elif color == self.colormap['portal']:
                    if (i, j) in self.portal_entrances:
                        a, b = 0, 0
                    else:
                        a, b = 4, 0
                    source = self.portal
                elif color in self.coord_map:
                    a, b, source = self.coord_map[color]
                elif color == self.colormap['black']:
                    self._preview.paste((0, 0, 0, 255), (
                        i * TILE_SIZE, j * TILE_SIZE, (i + 1) * TILE_SIZE,
                        (j + 1) * TILE_SIZE))
                    continue
                else:
                    raise KeyError("Unknown RGB value {}".format(color))
                draw((a, b), (i, j), source=source)
            except KeyError as e:
                print >> sys.stderr, e

        for i, j in marsballs:
            draw((11, 0),
                 (i - fractions.Fraction('1/2'), j - fractions.Fraction('1/2')),
                 draw_num_tiles=2)

    def preview(self, splats=None, save=None):
        self._preview = Image.new('RGBA', (self.max_x * TILE_SIZE,
                                           self.max_y * TILE_SIZE))

        self._draw_under()
        if splats:
            self._draw_splats(splats)
        self._draw_over()

        if save:
            self._preview.save(save, 'PNG')

        temp = cStringIO.StringIO()
        self._preview.save(temp, 'PNG')
        return temp

def preview45(png_path, json_path):
    data = json.load(open(json_path))
    png = Image.open(png_path)
    # PIL Initialization
    print "Current directory: ", os.getcwd()
    sprite_list = os.listdir("./sprites/")
    rgb_png = png.convert('RGB')
    WIDTH, HEIGHT = png.size
    img = Image.new("RGB", (WIDTH*40,HEIGHT*40), "white")
    pixels = rgb_png.load()
    # Variables / Constants
    map = {}
    sprites = {}
    WALLS = ["45", "135", "225", "315", "wall"]
    fails = 0
    # Remove Thumbs Database which is added when listdir is called
    if 'Thumbs.db' in sprite_list:
            sprite_list.remove('Thumbs.db')
     
    # Create Dictionary w/ Sprite names as keys and their respective image objects as values
    for pic in sprite_list:
            sprites[pic] = Image.open("sprites/"+pic)
     
    def adj_walls(x, y, paste):
            """Find adjacent walls to a wall when given a coordinate in image and wall type.
            Returns wall type and string of adjacent walls for correct sprite."""
            # Dictionary of walls which correspond to a direction
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
            if x != WIDTH-1:
                    if pixels[x+1,y] in corr_adj["R"]:
                            if '135' not in adj:
                                    adj += "R"
            if y != HEIGHT-1:
                    if pixels[x,y+1] in corr_adj["D"]:
                            if '135' not in adj:
                                    adj += "D"
            if x != 0:
                    if pixels[x-1,y] in corr_adj["L"]:
                            if '225' and '315' not in adj:
                                    adj += "L"
            return adj
    # Key of rgb values which correspond to correct sprite
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
    # Create dictionary of each point in rgb as key and what rgb value as value
    for w in range(WIDTH):
            for h in range(HEIGHT):
                    map[(w,h)] = rgbs[pixels[w,h]]
     
    # Determine base sprite for coordinate from its value in map.
    # If sprite is gate replace if default state of red, blue, or on.
    # If sprite is a portal replace w/ active portal if destination.
    # If sprite is wall find corresponding sprite for adjacent walls.
    # Paste sprite onto new image. Exception for odd 45s.
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
                    paste = adj_walls(item[0], item[1], paste)
            if paste+'.png' in sprites:    
                    img.paste(sprites[paste+'.png'],(item[0]*40,item[1]*40))
            else:
                    fails += 1
     
    # Add all marsballs specified in json
    if 'marsballs' in data:
            for mars in range(len(data['marsballs'])):
                    img.paste(sprites['marsball.png'],(data['marsballs'][mars]['x']*40, data['marsballs'][mars]['y']*40))
     
    # SAVE AND DISPLAY REPLACE WITH SOME_BOT FUNCTIONALITIES
    temp = cStringIO.StringIO()
    img.save(temp, "png")
    return temp

def main():
    if len(sys.argv) < 3:
        usage()
        return 1

    png_path = sys.argv[1]
    json_path = sys.argv[2]
    splats = sys.argv[3] if len(sys.argv) > 3 else None
    map_ = Map(png_path, json_path)
    preview = map_.preview(splats=splats)
    sys.stdout.write(preview.getvalue())


if '__main__' == __name__:
    status = main()
    sys.exit(status)
