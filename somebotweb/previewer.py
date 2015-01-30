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
import glob

from PIL import Image, ImageDraw

TILE_SIZE = 40
SIZE_LIMIT = 100*100
RESOURCE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'resources'))

WALLS = ["45", "135", "225", "315", "wall"]

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
    (255, 255, 0): "speedpad",
    (255, 128, 0): "bomb",
    (220, 186, 186): "red_tile",
    (187, 184, 221): "blue_tile",
    (202, 192, 0): "portaloff",
    (155, 0,  0): "redball",
    (0, 0, 155): "blueball",
    (255, 115, 115): "speedpad_red",
    (115, 115, 255): "speedpad_blue",
    (185, 0, 0): "red_endzone",
    (25, 0, 148): "blue_endzone",
    (128, 112, 64): "45",
    (64, 128, 80): "135",
    (64, 80, 128): "225",
    (128, 64, 112): "315"
}

def resource(filepath=None, texture="Vanilla", sprite_dir=False):
    if sprite_dir:
        sprite_path = os.path.join(RESOURCE_DIR, texture, "sprites")
        if not os.path.isdir(sprite_path):
            os.mkdir( os.path.join(RESOURCE_DIR, texture, "sprites") )
        return sprite_path
    return os.path.join(RESOURCE_DIR, texture, filepath)

def init_textures():
    for texture in os.listdir(RESOURCE_DIR):
        path = os.path.join(RESOURCE_DIR, texture)
        dissect(path)

def dissect(texture='Vanilla', write_dir=True):
    '''Input tiles.png of texture pack and return dictionary of PIL objects of sprites
    w/ appropriate names
    DOES NOT UTILIZE V2 GRAPHICS AND ALL OF TEXTURE PACK'''
    # IF len(TUPLE) == 4 COMBINES CORNERS FOR SAKE OF SIMPLICITY
    # CORDS GO (TOPRIGHT, TOPLEFT, BOTTOM LEFT, BOTTOM RIGHT)
    tiles = Image.open(resource("tiles.png", texture=texture))
    speedpad = Image.open(resource('speedpad.png', texture=texture))
    speedpad_blue = Image.open(resource('speedpadblue.png', texture=texture))
    speedpad_red = Image.open(resource('speedpadred.png', texture=texture))
    portal = Image.open(resource('portal.png', texture=texture))
    sprite_dir = resource(sprite_dir=True, texture=texture)

    crop_cords = {
        'speedpad':(0, 0, speedpad),
        'speedpad_blue':(0, 0, speedpad_blue),
        'speedpad_red':(0, 0, speedpad_red),
        'spike': (12,0),
        'redball': (14,0),
        'blueball': (15,0),
        'bomb': (12,1),
        'yellowflag': (13,1),
        'redflag': (14,1),
        'blueflag': (15,1),
        'gate': (12,3),
        'on_gate': (13,3),
        'red_gate': (14,3),
        'blue_gate': (15,3),
        'floor': (13,4),
        'red_tile': (14,4),
        'blue_tile': (15,4),
        'red_endzone': (14,5),
        'blue_endzone': (15,5),
        'button': (13,6),
        'topspeed': (12,7),
        'portal':(0,0, portal),
        # THIS IS WHERE IT GETS UGLY
        '135': ((0,0),(7,5),(7,5),(3,5)),
        '135U': (3,5),
        '135L': (7,5),
        '135UL': (11,9),
        '225': ((4,5),(11,0),(8,5),(8,5)),
        '225U': (8,5),
        '225R': (4,5),
        '225UR': (0,9),
        '315': ((9,0),(9,0),(2,4),(4,6)),
        '315R': (4,6),
        '315D': (0,1),
        '315RD': (0,8),
        '45': ((2,0),(2,0),(7,6),(9,4)),
        '45D': (11,1),
        '45L': (7,6),
        '45DL': (11,8),
        'wall': ((4,3),(7,3),(4,10),(7,10)),
        'wallD': ((4,3),(7,3),(7,3),(4,3)),
        'wallDL': (7,3),
        'wallL': (11,7),
        'wallR': (0,7),
        'wallRD': (4,3),
        'wallRDL': (1,7),
        'wallRL': (3,10),
        'wallU': ((10,8),(1,8),(4,10),(7,10)),
        'wallUD': (0,5),
        'wallUDL': (7,9),
        'wallUL': (4,10),
        'wallUR': (7,10),
        'wallURD': (4,9),
        'wallURDL': ((5,9),(6,9),(6,9),(5,9)),
        'wallURL': ((5,9),(6,9),(3,10),(3,10)),
    }
    sprites = {}
    floor = tiles.crop((13*40,4*40,(13+1)*40,(4+1)*40))
    for k, v in crop_cords.items():
        im = floor.copy()
        x_off = v[0]
        y_off = v[1]
        if len(v) == 2:
            spr = tiles.crop((x_off*40,y_off*40,(x_off+1)*40,(y_off+1)*40))
            im.paste(spr, (0,0),mask=spr)
            sprites[k] = im
        elif len(v) == 3:
            spr = v[2].crop((x_off*40,y_off*40,(x_off+1)*40,(y_off+1)*40))
            im.paste(spr, (0,0),mask=spr)
            sprites[k] = im
        elif len(v) == 4:
        # IF len(TUPLE) == 4 COMBINES 20 PIXEL CORNERS FOR SAKE OF SIMPLICITY
            # CORDS GO (TOPRIGHT, TOPLEFT, BOTTOM LEFT, BOTTOM RIGHT)
            corners = [(0,0),(20,0),(20,20),(0,20)]
            for c in range(len(v)):
                x_off = v[c][0]
                y_off = v[c][1]
                spr = tiles.crop(
                (x_off*40+corners[c][0] ,y_off*40+corners[c][1],
                (x_off)*40+corners[c][0]+20,(y_off)*40+corners[c][1]+20))
                im.paste(spr, (corners[c][0],corners[c][1]),mask=spr)
            sprites[k] = im
    sprites['black'] = Image.new("RGB", (40,40), "black")

    if write_dir:
        os.chdir(sprite_dir)
        for k,v in sprites.iteritems():
            v.convert("RGB").save(k+".png", "PNG")
    else:
        return sprites

class plot():
    def __init__(self, pngpath, jsonpath, texture="Vanilla"):
        sprite_list = os.listdir(resource(texture=texture, sprite_dir=True))
        self.sprites = {pic: Image.open(os.path.join(resource(texture=texture, sprite_dir=True), pic)) for pic in sprite_list}

        if 'http' in pngpath:
            png_handle = cStringIO.StringIO(urllib.urlopen(pngpath).read())
            png = Image.open(png_handle)
        else:
            png = Image.open(pngpath)

        if png.mode != 'RGB':
            png = png.convert('RGB')

        self.png = png
        self.max_x, self.max_y = self.png.size
        self.fails = 0
        if self.max_x * self.max_y > SIZE_LIMIT:
            error_msg = "Image '{}' is too large. Limit is {} px, but it is {}x{}.".format(
                pngpath, SIZE_LIMIT, self.max_x, self.max_y)
            raise ValueError(error_msg)
        self.pixels = png.load()
        self.cords = self.map_cords()
        if 'http' in jsonpath:
            json_file = urllib.urlopen(jsonpath)
            self.json = load(json_file)
        else:
            with open(jsonpath) as fp:
                self.json = json.load(fp)

    def __str__(self):
        return """Map Name: {}
        Map Author: {}
        Map Height: {}
        Map Width: {}
        Tile Number: {}
        Preview Height: {}
        Preview Width: {}
        Failed Displays: {}
        """.format(self.json["info"]["name"], self.json["info"]["author"],
        self.max_y, self.max_x, self.max_x*self.max_y, self.max_y*40, self.max_x*40, self.fails)

    def map_cords(self):
        return {(w,h): rgbs[self.pixels[w,h]] for w in range(self.max_x) for h in range(self.max_y)}

    def adj_walls(self, x, y, paste):
        corr_adj = {
            "U": [(128, 112, 64), (128, 64, 112), (120, 120, 120)],
            "R": [(128, 112, 64), (64, 128, 80), (120, 120, 120)],
            "D": [(64, 128, 80), (64, 80, 128), (120, 120, 120)],
            "L": [(64, 80, 128), (128, 64, 112), (120, 120, 120)]
        }
        wall_excep = [('31','45'),('13','45'),('13,22'),('22','31')]
        adj = paste
        # If within boundaries
            # If wall dir corresponds
                # Exclude wall type duplicates 
                    # Add dir string
        if y != 0:
            if self.pixels[x,y-1] in corr_adj["U"]:
                if adj[:2] not in wall_excep[0]:
                    adj += "U"
        if x != self.max_x-1:
            if self.pixels[x+1,y] in corr_adj["R"]:
                if adj[:2] not in wall_excep[1]:
                    adj += "R"
        if y != self.max_y-1:
            if self.pixels[x,y+1] in corr_adj["D"]:
                if adj[:2] not in wall_excep[2]:
                    adj += "D"
        if x != 0:
            if self.pixels[x-1,y] in corr_adj["L"]:
                if adj[:2] not in wall_excep[3]:
                    adj += "L"
        return adj
        
    def draw(self):
        img = Image.new("RGB", (self.max_x*40,self.max_y*40), "white")
        for item in self.cords:
            paste = self.cords[item]
            if paste == 'gate':
                cord_key = "%d,%d" % (item[0], item[1])
                if cord_key in self.json['fields']:
                    if self.json['fields'][cord_key]['defaultState'] != 'off':
                        paste = self.json['fields'][cord_key]['defaultState']+"_gate"
            if paste == 'portaloff':
                cord_key = "%d,%d" % (item[0], item[1])
                try:
                    if "destination" in self.json['portals'][cord_key]:
                        paste = "portal"
                except KeyError:
                    pass
            if paste in WALLS:
                paste = self.adj_walls(item[0], item[1], paste)

            if paste+'.png' in self.sprites:
                img.paste(self.sprites[paste+'.png'],(item[0]*TILE_SIZE,item[1]*TILE_SIZE))
            else:
                self.fails += 1
        # Add all marsballs specified in json
        if 'marsballs' in self.json:
            for mars in range(len(self.json['marsballs'])):
                img.paste(self.sprites['marsball.png'],(self.json['marsballs'][mars]['x']*TILE_SIZE, self.json['marsballs'][mars]['y']*TILE_SIZE))

        temp = cStringIO.StringIO()
        img.save(temp, "PNG")
        return temp

def main():
    if len(sys.argv) < 3:
        usage()
        return 1

    png_path = sys.argv[1]
    json_path = sys.argv[2]
    splats = sys.argv[3] if len(sys.argv) > 3 else None
    map_ = plot(png_path, json_path)
    preview = map_.draw()
    with open("%s_preview.png"%(png_path.split(".png")[0]), "wb") as f:
        f.write(preview.getvalue())


if '__main__' == __name__:
    status = main()
    sys.exit(status)
