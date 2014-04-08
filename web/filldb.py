import sqlite3
import os
import time
import glob

import simplejson as json


OUTPUT_MAPDIR = os.path.abspath("./static/maps/")


def connect_db(db_name):
    rv = sqlite3.connect(db_name)
    rv.row_factory = sqlite3.Row
    return rv


def get_db(db_name='maps.db'):
    return connect_db(db_name)


def add_map_to_db(name, author, description):
    db = get_db()
    insert_time = time.time()
    db.execute(
        'insert into maps (mapname, upload_time, times_tested, last_tested) '
        'values (?, ?, 0, 0)',
        [name, insert_time])
    db.commit()
    cur = db.execute("select id from maps where upload_time = (?)",
                     [insert_time])
    map_id = cur.fetchall()[0][0]
    print "ID: %s Mapname: %s Author: %s" % (map_id, name, author)
    db.execute(
        "insert into search (docid, mapname, author, description) "
        "values (?, ?, ?, ?)",
        [map_id, name, author, description])
    db.commit()
    return str(map_id)


def write_files(map_id, json_path, png_path):
    out_json = os.path.join(OUTPUT_MAPDIR, str(map_id) + '.json')
    out_png = os.path.join(OUTPUT_MAPDIR, str(map_id) + '.png')
    with open(out_png, 'wb') as f:
        f.write(open(png_path).read())
    with open(out_json, 'wb') as f:
        f.write(open(json_path).read())


def find_maps(map_dir):
    map_dir = os.path.expanduser(map_dir)
    successes, failures = 0, 0
    maps = glob.glob(map_dir + os.sep + "*.json")

    print "Total maps: %s" % len(maps)

    for idx, json_path in enumerate(glob.glob(map_dir + "*.json")):
        root = os.path.splitext(json_path)[0]
        pngpath = root + ".png"
        if os.path.isfile(pngpath):
            try:
                logic_data = json.load(open(json_path))
                mapname = logic_data.get('info', {}).get('name')
                author = logic_data.get('info', {}).get('author')
                description = logic_data.get('info', {}).get('description')
                if mapname:
                    mapid = add_map_to_db(mapname, author, description)
                    print "Added {}:{} to database...".format(mapname, author)
                    if mapid:
                        write_files(mapid, json_path, pngpath)
                        successes += 1
                else:
                    failures += 1
            except:  # TODO: Very broad failure.
                failures += 1
                pass
        else:
            failures += 1

        print "[{}] Successes: {} Failures {}".format(idx, successes, failures)


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2:
        mapdir = sys.argv[1]
        find_maps(mapdir)
    else:
        print "Usage: python filldb.py MAPDIR"
        exit()
