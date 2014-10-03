import sqlite3
import json
import time

from PIL import Image

import previewer

DATABASE = "maps.db"
MAP_DIRECTORY = "~/tagpro/tagpro-maps/somebot-brains/"

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'db'):
        g.db = connect_db()
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()
    
def add_map(mapid, author=""):
    db = get_db()
    map_data = get_map_data(mapid)
    author = map_data.get("author")
    mapname = map_data.get("mapname")
    description = map_data.get("description")
    db.execute('insert into maps (mapname, author, upload_time, last_tested, times_tested) values (?, ?, ?, 0, 0)', [mapname, author, time.time()])
    db.commit()
    # TODO check if map actually was inserted correctly
    return True

def get_map_data(mapid):
    json_file = os.path.join(MAP_DIRECTORY, mapid+'.json')
    map_json = json.loads(open(json_file).read())
    map_data = {
                'mapname':mapname,
                'author':map_json.get('info',{}).get('author', "No author listed"),
                'description':map_json.get('info',{}).get('description', "No description available"),
                'jsonurl':os.path.join(app.config['UPLOAD_DIR'], mapname+'.json'),
                'pngurl':os.path.join(app.config['UPLOAD_DIR'], mapname+'.png'),
                'previewurl':os.path.join(PREVIEW_DIR, mapname + '.png'),
                'thumburl':os.path.join(THUMB_DIR, mapname+'.png')
              }
    # Some more things we might want to display
    # creation date, version, similar maps
    return map_data


def generate_preview(mapid):
    # TODO: need to check if the files exist
    layout = os.path.join(UPLOAD_DIR, mapid + '.png')
    logic = os.path.join(UPLOAD_DIR, mapid + '.json')
    map_ = previewer.Map(layout, logic)
    preview = map_.preview()
    # TODO: use app.config.PREVIEW_DIR instead
    with open(os.path.join(PREVIEW_DIR, mapid + '.png'), 'w') as f:
        f.write(preview.getvalue())
