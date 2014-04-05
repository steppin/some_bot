# -*- coding: utf8 -*-

from flask import Flask, request, g, redirect, url_for, abort, render_template, send_from_directory, jsonify
from werkzeug import secure_filename

from flask.ext.sqlalchemy import SQLAlchemy
import flask.ext.whooshalchemy as whooshalchemy

import sqlite3
import os
import simplejson as json
import requests
import time

from PIL import Image

#from map_schema import db, Map


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

app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://maps:maptesting@localhost/maps"
app.config["WHOOSH_BASE"] = "postgresql://maps:maptesting@localhost/search"

db = SQLAlchemy(app)

class Map(db.Model):
    __searchable__ = ["author", "mapname", "description"]

    id = db.Column(db.Integer, primary_key=True)
    mapname = db.Column(db.Text)
    author = db.Column(db.Text)
    description = db.Column(db.Text)
    upload_time = db.Column(db.Float)
    last_tested = db.Column(db.Float)
    times_tested = db.Column(db.Integer)

    def __init__(self, mapname, author, description):
        self.mapname = mapname
        self.author = author
        self.description = description
        self.upload_time = time.time()
        self.last_tested = 0
        self.times_tested = 0

    def __repr__(self):
        return "<Map [%s] %s - %s>" %(str(self.id), self.mapname, self.author)

def add_map_to_db(mapname, author, description, commit=True):
    '''
    Add map to search and maps db
    search is a full text search table that only accepts text (except for rowid)
    maps is the table for data about maps (upload time, how many times tested, last tested)

    Returns the ID of the map that is inserted.
    '''
    m = Map(mapname, author, description)
    db.session.add(m)
    if commit:
        db.commit()
    print "New map -> [%s] %s by %s" %(m.id, mapname, author)
    return str(m.id)

def add_map(layout, logic):
    '''
    mapid = add_map(layout, logic)

    Given logic and layout data, parses logic to get mapname and layout
    saves logic and layout, generates previews and thumbs, adds map to database
    '''
    logic_data = json.loads(logic.read())
    mapname = logic_data.get('info', {}).get('name')
    author = logic_data.get('info', {}).get('author')
    description = logic_data.get('info', {}).get('description')

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
    try:
        mapid = int(mapid)
    except:
        return False
    m = Map.query.get(mapid)
    m.last_tested = time.time()
    m.times_tested += 1
    db.session.commit()

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

def recent_maps(author=None, page_limit=100, offset=0):
    if author:
        maps = Map.query.filter_by(author=author).offset(offset).limit(page_limit)
    else:
        maps = Map.query.offset(offset).limit(page_limit)
    return maps

def get_test_link(mapid):
    ''' 
    INPUT: map id (primary key of db)
    OUTPUT: test url from test server

    Given a map name, grabs logic and layout data from the config folders,
    sends post request to test server and returns test url server responds with
    '''
    test_server = 'http://tagpro-maptest.koalabeast.com/testmap'
    layout = os.path.join(app.config['UPLOAD_DIR'], str(mapid) + '.png')
    logic = os.path.join(app.config['UPLOAD_DIR'], str(mapid) + '.json')
    file_data = {'logic':open(logic).read(), 'layout':open(layout).read()}

    r = requests.post(test_server, files=file_data)
    increment_test(mapid)

    return r.url

@app.route("/upload", methods=['GET', 'POST'])
def save_map():
    mapid = request.args.get('mapid', '')
    return render_template('upload.html', map=get_map_data_from_id(mapid))

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/', methods=['GET','POST'])
def upload_map():
    if request.method == 'POST':
        layout = request.files.get("layout", None)
        logic = request.files.get("logic", None)
        generate_test = request.args.get("generate_testlink", False)

        # Handle upload by dropzone, not sure how to specify filenames with dropzone
        # it sends just a list of files
        if not logic and not layout:
            files = request.files.getlist('file[]')
            for f in files:
                if f.filename[-5:] == ".json":
                    logic = f
                elif f.filename[-4:] == ".png":
                    layout = f

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
        maps_data = get_data_from_maps(maps)
        return render_template('showmaps.html', maps=maps_data)



@app.route('/show')
def show_map():
    mapid = request.args.get('mapid', '')
    return render_template('showmap.html', map=get_map_data_from_id(mapid))

def get_map_data_from_id(mapid):
    m = Map.query.get(mapid)
    return get_map_data(m)

def get_map_data(m):
    map_data = {
                'mapid':m.id,
                'mapname':m.mapname,
                'author':m.author,
                'description':m.description,
                'jsonurl':os.path.join(app.config['UPLOAD_DIR'], str(m.id)+'.json'),
                'pngurl':os.path.join(app.config['UPLOAD_DIR'], str(m.id)+'.png'),
                'previewurl':os.path.join(PREVIEW_DIR, str(m.id)+'.png'),
                'thumburl':os.path.join(THUMB_DIR, str(m.id)+'.png')
              }
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
    return send_from_directory(app.config['UPLOAD_DIR'], secure_filename(str(mapid)+'.png'), attachment_filename=secure_filename(str(filename))+".png")

@app.route("/author/<author>")
def return_maps_by_author(author):
    maps = recent_maps(author=author)
    maps_data = get_data_from_maps(maps)
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

def search_db(query):
    maps = Map.query.whoosh_search(query)
    return maps

def get_data_from_maps(maps):
    for m in maps:
        yield get_map_data(m)

@app.route("/search")
def search():
    query = request.args.get("query", "")
    print query
    if query:
        maps = search_db(query)
    else:
        maps = recent_maps()

    maps_data = get_data_from_maps(maps)
    data = render_template('showmaps.html', maps=maps_data, standalone=True)
    return jsonify(success=True, html=data)

if __name__ == '__main__':
    app.run(debug=DEBUG)
