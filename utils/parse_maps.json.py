#!/usr/bin/env python
# usage: parse_maps.json.py maps.json m M
# prints maps with weight at least m and at most M

import sys
import json


def main(argv):
    m = float(sys.argv[2])
    M = float(sys.argv[3])
    maps = json.load(open(sys.argv[1]))
    for map_ in maps:
        if m <= map_['weight'] <= M:
            print map_['name']


if __name__ == '__main__':
    main(sys.argv)
