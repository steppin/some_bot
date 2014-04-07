# -*- coding: utf8 -*-

from flask import Flask, request, g, redirect, url_for, abort, render_template, send_from_directory, jsonify
from werkzeug import secure_filename

from flask.ext.sqlalchemy import SQLAlchemy

import sqlite3
import os
import simplejson as json
import requests
import time

from PIL import Image, ImageOps

import previewer

# TODO:
# * check filetypes, size limits, basically a tagpromaplint

app = Flask(__name__)

BASE_DIR = app.root_path

app.config.from_pyfile('config.cfg')

db = SQLAlchemy(app)

class Map(db.Model):
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
    db.session.commit()
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
        mapid = add_map_to_db(mapname, author, description)
        mapid = str(mapid)
        layoutpath = os.path.join(app.config['UPLOAD_DIR'], mapid+'.png')
        layout.save(layoutpath)
        
        logicpath = os.path.join(app.config['UPLOAD_DIR'], mapid+'.json')
        with open(logicpath, "wb") as f:
            f.write( json.dumps(logic_data, logicpath))

        generate_preview(mapid)
        generate_thumb(mapid)
        print "Map added successfully"
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
    with open(os.path.join(app.config['PREVIEW_DIR'], str(mapid) + '.png'), 'w') as f:
        f.write(preview.getvalue())
    print "Created preview successfully"

def generate_thumb(mapid):
    preview_file = os.path.join(app.config['PREVIEW_DIR'], str(mapid) + '.png')
    preview = Image.open(preview_file)
    prex, prey = preview.size
    target_width = 250
    target_height = int(target_width * prey / float(prex))
    offset = (0, target_width/2 - target_height/2)
    if target_height > target_width:
        target_height = 250
        target_width = int(target_height * prex / float(prey))
        offset = (target_height/2 - target_width/2, 0)

    preview.thumbnail((target_width, target_height), Image.ANTIALIAS)
    centered_thumb = Image.new(preview.mode, size=(250,250), color=(0,0,0,255))
    centered_thumb.paste(preview, offset)
    centered_thumb.save(os.path.join(app.config['THUMB_DIR'], str(mapid) + '.png'))

def recent_maps(author=None, page_limit=100, offset=0):
    if author:
        maps = Map.query.filter_by(author=author).offset(offset).limit(page_limit)
    else:
        maps = Map.query.order_by("upload_time desc").offset(offset).limit(page_limit)
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
    return render_template('showmap.html', map=get_map_data_from_id(mapid))

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
                return redirect(testurl)
            success = mapid >= 0
            if success:
                return redirect(saveurl)
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
                #'jsonurl':url_for(app.config['UPLOAD_DIR'], filename=str(m.id)+'.json'),
                #'pngurl':url_for(app.config['UPLOAD_DIR'], filename=str(m.id)+'.png'),
                #'previewurl':url_for(app.config['PREVIEW_DIR'], filename=str(m.id)+'.png'),
                #'thumburl':url_for(THUMB_DIR, filename=str(m.id)+'.png'),
                'times_tested':str(m.times_tested),
              }
    return map_data

@app.route("/maptest")
def test_map():
    mapid = request.args.get('mapid', None)
    if mapid:
        showurl = url_for('save_map', mapid=mapid)
        testurl = get_test_link(mapid)
        print "Testurl: ", testurl
        return jsonify(success=True, testurl=testurl, showurl=showurl)
    else:
        return abort(404)

@app.route("/m/<author>/<mapname>")
def return_author_map(author, mapname):
    m = search_db(author=author, mapname=mapname)
    if m:
        map_data = get_map_data(m)
        return render_template("showmap.html", map=map_data)
    else:
        maps = recent_maps()
        maps_data = get_data_from_maps(maps)
        return render_template('showmaps.html', maps=maps_data)

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

def search_db(query=None, mapname=None, author=None):
    maps = []
    if author and mapname:
        maps = Map.query.filter(Map.author.ilike(author)).filter(Map.mapname.ilike(mapname)).first()
    else:
        querystring = "%"+query +"%"
        maps = Map.query.filter(Map.author.ilike(querystring)).all()
        maps.extend(Map.query.filter(Map.mapname.ilike(querystring)).all())
    return maps

def get_data_from_maps(maps):
    for m in maps:
        yield get_map_data(m)

@app.route("/search")
def search():
    query = request.args.get("query", "")
    if query:
        maps = search_db(query=query)
    else:
        maps = recent_maps()

    maps_data = get_data_from_maps(maps)
    data = render_template('showmaps.html', maps=maps_data, standalone=True)
    return jsonify(success=True, html=data)

if __name__ == '__main__':
    app.run(debug=app.debug)
