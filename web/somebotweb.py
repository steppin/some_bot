from flask import Flask, request, g, redirect, url_for, abort, render_template, send_from_directory, jsonify
from werkzeug import secure_filename
import sqlite3
import os
import simplejson as json
import requests
import time

from PIL import Image

import previewer

# TODO:
# * check filetypes, size limits, basically a tagpromaplint

app = Flask(__name__)
DEBUG = True

# TODO: use a nice path here;
# http://flask.pocoo.org/docs/config/#instance-folders
BASE_DIR = app.root_path
UPLOAD_DIR = os.path.join(BASE_DIR, 'static/maps')
PREVIEW_DIR = os.path.join(BASE_DIR, 'static/previews')
THUMB_DIR = os.path.join(BASE_DIR, 'static/thumbs')
DATABASE = os.path.join(BASE_DIR, 'maps.db')

app.config.from_object(__name__)

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

def add_map_to_db(mapname, author):
    db = get_db()
    uptime = time.time()
    db.execute('insert into maps (mapname, author, upload_time, last_tested, times_tested) values (?, ?, ?, 0, 0)', [mapname, author, uptime])
    db.commit()
    mapid = db.execute("select id from maps where upload_time = ?", [uptime])
    mapid = str(mapid.fetchall()[0][0])
    print "New map -> [%s] %s by %s" %(mapid, mapname, author)
    return mapid

def add_map(layout, logic):
    '''
    mapid = add_map(layout, logic)

    Given logic and layout data, parses logic to get mapname and layout
    saves logic and layout, generates previews and thumbs, adds map to database
    '''
    logic_data = json.loads(logic.read())
    mapname = logic_data.get('info', {}).get('name')
    author = logic_data.get('info', {}).get('author')

    if mapname and author:

        mapid = add_map_to_db(mapname, author)

        layoutpath = os.path.join(app.config['UPLOAD_DIR'], mapid+'.png')
        layout.save(layoutpath)
        
        logicpath = os.path.join(app.config['UPLOAD_DIR'], mapid+'.json')
        with open(logicpath, "wb") as f:
            f.write( json.dumps(logic_data, logicpath))

        generate_preview(mapid)
        generate_thumb(mapid)

        # TODO check if map actually was inserted correctly
        return mapid

    else:
        return -1


def increment_test(mapid):
    db = get_db()
    db.execute('update maps set last_tested=(?) where id=(?)', [time.time(), mapid])
    db.execute('update maps set times_tested=times_tested+1 where id=(?)', [mapid])
    db.commit()

def generate_preview(mapid):
    # TODO: need to check if the files exist
    layout = os.path.join(app.config['UPLOAD_DIR'], mapid + '.png')
    logic = os.path.join(app.config['UPLOAD_DIR'], mapid + '.json')
    map_ = previewer.Map(layout, logic)
    preview = map_.preview()
    # TODO: use app.config.PREVIEW_DIR instead
    with open(os.path.join(PREVIEW_DIR, mapid + '.png'), 'w') as f:
        f.write(preview.getvalue())

def generate_thumb(mapid):
    preview = os.path.join(PREVIEW_DIR, mapid + '.png')
    target_width = 400
    thumbnail = Image.open(preview)
    width, height = thumbnail.size
    target_height = target_width*float(height)/width
    thumbnail.thumbnail((target_width, target_height), Image.ANTIALIAS)
    # TODO: use app.config.THUMB_DIR instead
    thumbnail.save(os.path.join(THUMB_DIR, mapid + '.png'))

def recent_maps(author=None):
    db = get_db()
    if author:
        cur = db.execute('select id from maps where author like (?) order by upload_time desc', [author])
    else:
        cur = db.execute('select id from maps order by upload_time desc')
    maps = cur.fetchall()
    return maps

def get_test_link(mapid):
    ''' 
    INPUT: map id (primary key of db)
    OUTPUT: test url from test server

    Given a map name, grabs logic and layout data from the config folders,
    sends post request to test server and returns test url server responds with
    '''
    test_server = 'http://tagpro-maptest.koalabeast.com/testmap'
    layout = os.path.join(app.config['UPLOAD_DIR'], mapid + '.png')
    logic = os.path.join(app.config['UPLOAD_DIR'], mapid + '.json')
    file_data = {'logic':open(logic).read(), 'layout':open(layout).read()}

    r = requests.post(test_server, files=file_data)
    increment_test(mapid)

    return r.url

@app.route("/upload", methods=['GET', 'POST'])
def save_map():
    mapid = request.args.get('mapid', '')
    return render_template('upload.html', map=get_map_data(mapid))

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/', methods=['GET','POST'])
def upload_map():
    if request.method == 'POST':
        layout = request.files.get("layout", None)
        logic = request.files.get("logic", None)
        generate_test = request.args.get("generate_testlink", False)

        # Handle upload by dropzone, not sure how to specify filenames
        if not logic and not layout:
            files = request.files.getlist('file[]')
            for f in files:
                if f.filename[-5:] == ".json":
                    logic = f
                elif f.filename[-4:] == ".png":
                    layout = f

        # TODO: make secure filename so people can't overwrite? secure file name
        if layout and logic:
            mapid = add_map(layout, logic)
            saveurl = url_for('save_map', mapid=mapid)
            testurl = None
            if generate_test:
                testurl = get_test_link(mapid)
            success = mapid >= 0
            return jsonify(success=success, saveurl=saveurl, testurl=testurl)
        else:
            abort(404)
    else:
        author = request.args.get("author", None)
        maps = recent_maps(author=author)
        # This is a little hacky, recent_maps() returns a sqlite row, but we need a list of mapnames
        maps_data = map(lambda x: get_map_data(str(x[0])), maps)
        return render_template('showmaps.html', maps=maps_data)

@app.route('/show')
def show_map():
    mapid = request.args.get('mapid', '')
    return render_template('showmap.html', map=get_map_data(mapid))

def get_map_data(mapid):
    json_file = os.path.join(app.config['UPLOAD_DIR'], mapid+'.json')
    map_json = json.loads(open(json_file).read())
    map_data = {
                'mapid':mapid,
                'mapname':map_json.get('info',{}).get('name', "No name listed"),
                'author':map_json.get('info',{}).get('author', "No author listed"),
                'description':map_json.get('info',{}).get('description', "No description available"),
                'jsonurl':os.path.join(app.config['UPLOAD_DIR'], mapid+'.json'),
                'pngurl':os.path.join(app.config['UPLOAD_DIR'], mapid+'.png'),
                'previewurl':os.path.join(PREVIEW_DIR, mapid+'.png'),
                'thumburl':os.path.join(THUMB_DIR, mapid+'.png')
              }
    # Some more things we might want to display
    # creation date, version, similar maps
    return map_data

@app.route("/maptest")
def test_map():
    mapid = request.args.get('mapid', None)
    if mapid:
        showurl = url_for('save_map', mapid=mapid)
        testurl = get_test_link(mapid)
        return jsonify(success=True, testurl=testurl, showurl=showurl)
    else:
        return abort(404)

@app.route('/map/<mapid>')
def return_map(mapid):
    filename = get_mapname_from_id(mapid)
    return send_from_directory(app.config['UPLOAD_DIR'], secure_filename(mapid + '.png'), attachment_filename=secure_filename(filename)+".png")

@app.route("/author/<author>")
def return_maps_by_author(author):
    maps = recent_maps(author=author)
    maps_data = map(lambda x: get_map_data(str(x[0])), maps)
    return render_template('showmaps.html', maps=maps_data)

@app.route("/download")
def download():
    mapid = request.args.get("mapid", "")
    mapname = request.args.get("mapname", "")
    filetype = request.args.get("type", None)
    if mapid and filetype and mapname:
        if filetype == "png":
            return send_from_directory(app.config['UPLOAD_DIR'], secure_filename(mapid + '.png'), attachment_filename=secure_filename(mapname+".png"))
        elif filetype == "json":
            return send_from_directory(app.config['UPLOAD_DIR'], secure_filename(mapid + '.json'), as_attachment=True, attachment_filename=secure_filename(mapname+".json"))
        else:
            return abort(404)
    else:
        return abort(404)

if __name__ == '__main__':
    app.run(debug=DEBUG)
