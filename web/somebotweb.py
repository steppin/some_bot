from flask import Flask, request, g, redirect, url_for, abort, render_template, send_from_directory, jsonify
from werkzeug import secure_filename
import sqlite3
import os
import json
import requests

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
    
def add_map(mapname):
    db = get_db()
    db.execute('insert into maps (mapname) values (?)', [mapname])
    db.commit()

def generate_preview(mapname):
    # TODO: need to check if the files exist
    layout = os.path.join(UPLOAD_DIR, mapname + '.png')
    logic = os.path.join(UPLOAD_DIR, mapname + '.json')
    map_ = previewer.Map(layout, logic)
    preview = map_.preview()
    # TODO: use app.config.PREVIEW_DIR instead
    with open(os.path.join(PREVIEW_DIR, mapname + '.png'), 'w') as f:
        f.write(preview.getvalue())

def generate_thumb(mapname):
    preview = os.path.join(PREVIEW_DIR, mapname + '.png')
    target_width = 400
    thumbnail = Image.open(preview)
    width, height = thumbnail.size
    target_height = target_width*float(height)/width
    thumbnail.thumbnail((target_width, target_height), Image.ANTIALIAS)
    # TODO: use app.config.THUMB_DIR instead
    thumbnail.save(os.path.join(THUMB_DIR, mapname + '.png'))

def recent_maps():
    db = get_db()
    cur = db.execute('select mapname from maps order by id desc')
    maps = cur.fetchall()
    return maps

def get_test_link(mapname):
    ''' 
    INPUT: mapname
    OUTPUT: test url from test server

    Given a map name, grabs logic and layout data from the config folders,
    sends post request to test server and returns test url server responds with
    '''
    test_server = 'http://tagpro-maptest.koalabeast.com/testmap'
    layout = os.path.join(app.config['UPLOAD_DIR'], mapname + '.png')
    logic = os.path.join(app.config['UPLOAD_DIR'], mapname + '.json')
    file_data = {'logic':open(logic).read(), 'layout':open(layout).read()}
    r = requests.post(test_server, files=file_data)
    return r.url

@app.route('/', methods=['GET','POST'])
def upload_map():
    if request.method == 'POST':
        layout, logic = None, None
        # I'm not sure if dropzone supports multiple file upload and individual names
        files = request.files.getlist('file[]')
        for f in files:
            if f.filename[-5:] == ".json":
                logic = f
            elif f.filename[-4:] == ".png":
                layout = f
        # TODO: make secure filename so people can't overwrite? secure file name
        # Generate a md5 based on map name and author?
        # Or just mapname+'_'+mapauthor
        if layout and logic:
            mapname = os.path.splitext(layout.filename)[0]
            layout.save(os.path.join(app.config['UPLOAD_DIR'], mapname + '.png'))
            logic.save(os.path.join(app.config['UPLOAD_DIR'], mapname + '.json'))
            generate_preview(mapname)
            generate_thumb(mapname)
            add_map(mapname)
            return redirect(url_for('show_map', mapname=mapname))
        else:
            abort(404)
    else:
        maps = recent_maps()
        # This is a little hacky, recent_maps() returns a sqlite row, but we need a list of mapnames
        maps_data = map(lambda x: get_map_data(x[0]), maps)
        return render_template('upload.html', maps=maps_data)

@app.route('/show')
def show_map():
    mapname = request.args.get('mapname', '')
    return render_template('showmap.html', map=get_map_data(mapname))

def get_map_data(mapname):
    json_file = os.path.join(app.config['UPLOAD_DIR'], mapname+'.json')
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


@app.route("/maptest")
def test_map():
    mapname = request.args.get('mapname', None)
    if mapname:
        testurl = get_test_link(mapname)
        return jsonify(success=True, testurl=testurl)
    else:
        return abort(404)

@app.route('/map/<mapname>')
def return_map(mapname):
    return send_from_directory(app.config['UPLOAD_DIR'], secure_filename(mapname + '.png'))

@app.route("/download")
def download():
    mapname = request.args.get("mapname", None)
    filetype = request.args.get("type", None)
    if mapname and filetype:
        if filetype == "png":
            return send_from_directory(app.config['UPLOAD_DIR'], secure_filename(mapname + '.png'))
        elif filetype == "json":
            return send_from_directory(app.config['UPLOAD_DIR'], secure_filename(mapname + '.json'))
        else:
            return abort(404)
    else:
        return abort(404)
if __name__ == '__main__':
    app.run(debug=DEBUG)
