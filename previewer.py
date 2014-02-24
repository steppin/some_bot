#!/usr/bin/env python
"""A preview generator for tagpro."""

from __future__ import division

import sys
import json
import urllib
import cStringIO
import fractions
import itertools

from PIL import Image, ImageDraw


TILESIZE = 40


def usage():
    print >> sys.stderr, 'Usage: {} PNG JSON [SPLATS] > PREVIEW'.format(sys.argv[0])


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
    tiles = Image.open('resources/tiles.png')
    speedpad = Image.open('resources/speedpad.png')
    speedpadblue = Image.open('resources/speedpadblue.png')
    speedpadred = Image.open('resources/speedpadred.png')
    portal = Image.open('resources/portal.png')
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
        'speedpad': (255, 255, 0),
        'bomb': (255, 128, 0),
        'bluetile': (187, 184, 221),
        'redtile': (220, 186, 186),
        'speedpadred': (255, 115, 115),
        'speedpadblue': (115, 115, 255),
        'portal': (202, 192, 0),
        'bluespawn': (0, 0, 155),
        'redspawn': (155, 0, 0)
    }

    def __init__(self, pngpath, jsonpath):
        if 'http' in pngpath:
            pfile = cStringIO.StringIO(urllib.urlopen(pngpath).read())
            png = Image.open(pfile)
        else:
            png = Image.open(pngpath)
        self.png = png
        self.pixels = png.load()

        if 'http' in jsonpath:
            jfile = urllib.urlopen(jsonpath)
            j = json.load(jfile)
        else:
            with open(jsonpath) as fp:
                j = json.load(fp)
        self.json = j

    def draw(self, (x, y), (i, j), tiles, preview, drawBackground=False, source=None, draw_num_tiles=1):
        """draw square (x, y) from source on preview in spot (i, j)"""

        if drawBackground:
            im = tiles.crop((2 * TILESIZE, 2 * TILESIZE, 2 * TILESIZE + TILESIZE, 2 * TILESIZE + TILESIZE))
            # TODO(step): lol comment this so people don't curse you
            for c, d in itertools.product(xrange(i, i + draw_num_tiles), xrange(j, j + draw_num_tiles)):
                preview.paste(im, (int(c * TILESIZE), int(d * TILESIZE)))

        if not source:
            source = tiles

        x, y = x * TILESIZE, y * TILESIZE
        im = source.crop((x, y, x + draw_num_tiles * TILESIZE, y + draw_num_tiles * TILESIZE))
        preview.paste(im, (int(i * TILESIZE), int(j * TILESIZE)), im)

    def _draw_under(self):
        speedpad = self.speedpad
        speedpadred = self.speedpadred
        speedpadblue = self.speedpadblue
        portal = self.portal
        tiles = self.tiles
        preview = self.preview
        colormap = self.colormap
        pixels = self.pixels
        max_x, max_y = self.max_x, self.max_y
        draw = self.draw

        green = []
        blue = []
        red = []
        try:
            for point, state in self.json['fields'].iteritems():
                if state['defaultState'] == 'on':
                    x, y = point.split(',')
                    green.append((int(x), int(y)))
                elif state['defaultState'] == 'red':
                    x, y = point.split(',')
                    red.append((int(x), int(y)))
                elif state['defaultState'] == 'blue':
                    x, y = point.split(',')
                    blue.append((int(x), int(y)))
        except KeyError:
            pass

        portal_entrances = []
        try:
            for entrance, exit in self.json['portals'].iteritems():
                x, y = entrance.split(',')
                portal_entrances.append((int(x), int(y)))
        except KeyError:
            pass

        for i in range(max_x):
            for j in range(max_y):
                try:
                    color = pixels[i, j][:3]
                    if color == colormap['speedpad']:
                        a, b = 0, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=True, source=speedpad)
                    elif color == colormap['speedpadred']:
                        a, b = 0, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=True, source=speedpadred)
                    elif color == colormap['speedpadblue']:
                        a, b = 0, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=True, source=speedpadblue)
                    elif color == colormap['portal']:
                        if (i, j) in portal_entrances:
                            a, b = 0, 0
                        else:
                            a, b = 4, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=True, source=portal)
                    elif color == colormap['bomb']:
                        a, b = 6, 5
                        draw((a, b), (i, j), tiles, preview, drawBackground=True)
                    elif color == colormap['redtile']:
                        a, b = 3, 1
                        draw((a, b), (i, j), tiles, preview, drawBackground=True)
                    elif color == colormap['bluetile']:
                        a, b = 3, 2
                        draw((a, b), (i, j), tiles, preview, drawBackground=True)
                    elif color == colormap['spike']:
                        a, b = 2, 3
                        draw((a, b), (i, j), tiles, preview, drawBackground=True)
                    elif color == colormap['button']:
                        a, b = 2, 5
                        draw((a, b), (i, j), tiles, preview, drawBackground=True)
                    elif color == colormap['powerup']:
                        a, b = 7, 8
                        draw((a, b), (i, j), tiles, preview, drawBackground=True)
                    elif color == colormap['blueflag']:
                        a, b = 9, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=True)
                    elif color == colormap['redflag']:
                        a, b = 8, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=True)
                    elif color == colormap['tile']:
                        a, b = 2, 2
                        draw((a, b), (i, j), tiles, preview)
                    elif color == colormap['gate']:
                        if (i, j) in green:
                            a, b = 10, 2
                        elif (i, j) in red:
                            a, b = 10, 3
                        elif (i, j) in blue:
                            a, b = 10, 4
                        else:
                            a, b = 10, 1
                        draw((a, b), (i, j), tiles, preview)
                except KeyError:
                    print >> sys.stderr, "make this an error mkay"

    def _draw_splats(self, splatfile):
        im = self.preview
        with open(splatfile) as f:
            splats = json.load(f)
        radius = 10
        opacity = 64
        color = {2: (0, 0, 255, opacity), 1: (255, 0, 0, opacity)}
        shift = 10

        redsplat = Splat(color[1], radius)
        bluesplat = Splat(color[2], radius)

        for splat in splats:
            (x, y) = (splat['x'] + shift, splat['y'] + shift)
            t = splat['t']
            if t == 1:
                redsplat.paste_onto(im, (x, y))
            elif t == 2:
                bluesplat.paste_onto(im, (x, y))

    def _draw_over(self):
        speedpad = self.speedpad
        speedpadred = self.speedpadred
        speedpadblue = self.speedpadblue
        portal = self.portal
        tiles = self.tiles
        preview = self.preview
        colormap = self.colormap
        pixels = self.pixels
        max_x, max_y = self.max_x, self.max_y
        draw = self.draw
        png = self.png

        marsballs = []
        try:
            for coords in self.json['marsballs']:
                marsballs.append((int(coords['x']), int(coords['y'])))
        except KeyError:
            pass

        for i in range(max_x):
            for j in range(max_y):
                try:
                    color = pixels[i, j][:3]
                    if color == colormap['black']:
                        preview.paste((0, 0, 0, 255), (i * TILESIZE, j * TILESIZE, i * TILESIZE + TILESIZE, j * TILESIZE + TILESIZE))
                    elif color == colormap['wall']:
                        north, south, west, east = [False] * 4
                        if j > 0:
                            north = pixels[i, j - 1][:3] == colormap['wall']
                        if j < png.size[1] - 1:
                            south = pixels[i, j + 1][:3] == colormap['wall']
                        if i > 0:
                            west = pixels[i - 1, j][:3] == colormap['wall']
                        if i < png.size[0] - 1:
                            east = pixels[i + 1, j][:3] == colormap['wall']
                        if north:
                            if south:
                                if east:
                                    if west:
                                        a, b = 4, 4
                                    else:
                                        a, b = 0, 4
                                else:
                                    if west:
                                        a, b = 7, 4
                                    else:
                                        a, b = 4, 2
                            else:
                                if east:
                                    if west:
                                        a, b = 4, 8
                                    else:
                                        a, b = 2, 8
                                else:
                                    if west:
                                        a, b = 6, 8
                                    else:
                                        a, b = 0, 6
                        else:
                            if south:
                                if east:
                                    if west:
                                        a, b = 4, 0
                                    else:
                                        a, b = 2, 0
                                else:
                                    if west:
                                        a, b = 6, 0
                                    else:
                                        a, b = 0, 2
                            else:
                                if east:
                                    if west:
                                        a, b = 2, 4
                                    else:
                                        a, b = 8, 6
                                else:
                                    if west:
                                        a, b = 9, 6
                                    else:
                                        a, b = 0, 0
                        draw((a, b), (i, j), tiles, preview)
                    elif color == colormap['speedpad']:
                        a, b = 0, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=False, source=speedpad)
                    elif color == colormap['speedpadred']:
                        a, b = 0, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=False, source=speedpadred)
                    elif color == colormap['speedpadblue']:
                        a, b = 0, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=False, source=speedpadblue)
                    elif color == colormap['portal']:
                        if (i, j) in portal_entrances:
                            a, b = 0, 0
                        else:
                            a, b = 4, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=False, source=portal)
                    elif color == colormap['bomb']:
                        a, b = 6, 5
                        draw((a, b), (i, j), tiles, preview, drawBackground=False)
                    elif color == colormap['spike']:
                        a, b = 2, 3
                        draw((a, b), (i, j), tiles, preview, drawBackground=False)
                    elif color == colormap['button']:
                        a, b = 2, 5
                        draw((a, b), (i, j), tiles, preview, drawBackground=False)
                    elif color == colormap['powerup']:
                        a, b = 7, 8
                        draw((a, b), (i, j), tiles, preview, drawBackground=False)
                    elif color == colormap['blueflag']:
                        a, b = 9, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=False)
                    elif color == colormap['redflag']:
                        a, b = 8, 0
                        draw((a, b), (i, j), tiles, preview, drawBackground=False)
                except KeyError:
                    print >> sys.stderr, "make this an error mkay"

        for i, j in marsballs:
            draw((11, 0), (i - fractions.Fraction('1/2'), j - fractions.Fraction('1/2')), tiles, preview, drawBackground=False, draw_num_tiles=2)

    def preview(self, splats=None, save=None):
        self.max_x, self.max_y = max_x, max_y = self.png.size
        self.preview = Image.new('RGBA', (max_x * TILESIZE, max_y * TILESIZE))

        self._draw_under()
        if splats:
            self._draw_splats(splats)
        self._draw_over()

        if save:
            self.preview.save(save, 'PNG')

        temp = cStringIO.StringIO()
        self.preview.save(temp, 'PNG')
        return temp


def main():
    if len(sys.argv) < 3:
        usage()
        return 1

    pngpath = sys.argv[1]
    jsonpath = sys.argv[2]
    splats = sys.argv[3] if len(sys.argv) > 3 else None

    map_ = Map(pngpath, jsonpath)
    preview = map_.preview(splats=splats)

    sys.stdout.write(preview.getvalue())


if '__main__' == __name__:
    status = main()
    sys.exit(status)
