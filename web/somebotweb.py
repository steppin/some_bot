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

'''
Things that need to be done:
    [ ] Pagination added to all map requests
    [ ] Refactoring to make everything consistent
        A map objects mapid is sometimes used as a string, sometimes an int
    [ ] Login for map ownership
    [ ] Map versioning for multiple maps of same name
    [ ] Enhanced map upload page - if things are missing, let users add them
        If there's no description, let users add it on the upload page

The current URLs that are processed

/ -> GET: return showmaps.html rendered with recent_maps
     POST: upload map to database, maybe generate testlink, maybe go to show_map page

/upload -> definitely doesn't do upload thing
/showmap?mapid=MAPID -> Render showmap.html with map given by mapid
/search?query=QUERY -> Search database for query, returning results
/a/<author> -> show maps given by author (case insensitive)
/m/<author>/<mapname> -> show map by author with mapname, selecting the first map
                         I'm not sure if this takes the lowest or the highest mapid
/download?mapname=MAPNAME&mapid=MAPID&filetype=FILETYPE ->
                        Download mapid.filetype and use mapname.filetype for download

'''

# Read configuration from the file named config.cfg
# This file contains LOCAL and DEBUG variables, 
# specifying the database URI depending on LOCAL
# This is necessary so the private database information isn't inadvertently
# added to the github repository
# TODO: Do a check so the production is always run in not-debug mode with 
# the proper database
app.config.from_pyfile('config.cfg')

db = SQLAlchemy(app)

class Map(db.Model):
    '''
    The map schema
    To make a map, we need a mapname, and author, and a description
    times_tested, last_tested and upload_time are generated when a map
    object is created
    '''

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
    Add a map to the sqlalchemy db object
    INPUT: mapname, author, description
    OUTPUT: mapid string

    #TODO: Make mapid consistent - it's not handled well right now
    # Sometimes integers are used (looking in db), sometimes strings (filenames)
    '''
    m = Map(mapname, author, description)
    db.session.add(m)
    db.session.commit()
    print "New map -> [%s] %s by %s" %(m.id, mapname, author)
    return str(m.id)

def add_map(layout, logic):
    '''
    This is the main function for adding maps to the database
    It handles all the functions necessary for taking logic and layout data

    The steps are:
    Read json data, parse mapname, author, description
    Add map to the database
    Get the mapid from the database (primary key)
    Save the logic and layout file objects to mapid.json and mapid.png
    Generate preview by passing mapid to the previewer
    Generate the thumbnail after the preview has been generated


    INPUT: layout and logic file objects (where data can be accessed with obj.read())
    OUTPUT: mapid, or -1 if the mapname or author are not present in the file

    #TODO: Return a JSON object specifying what's wrong that can be displayed
    to the user
    #TODO: Maybe make this asynchronous so the user doesn't wait on the map preview 
    being generated - some map previews can take a really long time to generate
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
    '''
    INPUT: mapid
    OUTPUT: None

    Increment the times_tested for the map given by mapid and the
    last_tested time for the map
    '''
    try:
        mapid = int(mapid)
    except:
        return False
    m = Map.query.get(mapid)
    m.last_tested = time.time()
    m.times_tested += 1
    db.session.commit()

def generate_preview(mapid):
    '''
    INPUT: mapid
    OUTPUT: None

    Generate a preview from the logic and json files given by
    mapid.png and mapid.json in the app's upload directory.

    Uses some_bot's previewer script to create preview
    '''
    layout = os.path.join(app.config['UPLOAD_DIR'], mapid + '.png')
    logic = os.path.join(app.config['UPLOAD_DIR'], mapid + '.json')
    map_ = previewer.Map(layout, logic)
    preview = map_.preview()
    with open(os.path.join(app.config['PREVIEW_DIR'], str(mapid) + '.png'), 'w') as f:
        f.write(preview.getvalue())

def generate_thumb(mapid):
    '''
    INPUT: mapid
    OUTPUT: None

    Given a mapid, get preview filed named mapid.png and generate
    a 250x250 px thumbnail.
    This will scale the preview so the longest dimension is 250 px,
    scaling the smaller dimension as necessary, and adding a black
    border around the image - consistent with some of the previews generated
    from the map editors
    '''
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
    '''
    Get recent maps from the database
    INPUT: All optional - author, page_limit (number of entries), and offset for pagination
    OUTPUT: Map objects ordered by upload_time descending
    '''
    if author:
        maps = Map.query.filter(Map.author.ilike(author)).order_by("upload_time desc").offset(offset).limit(page_limit)
    else:
        maps = Map.query.order_by("upload_time desc").offset(offset).limit(page_limit)
    return maps

def get_test_link(mapid):
    ''' 
    INPUT: map id (primary key of db)
    OUTPUT: test url from test server

    Given a map name, grabs logic and layout data from the app's config folders,
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
    '''
    This is currently not the upload url
    #TODO fix this
    '''
    mapid = request.args.get('mapid', '')
    return render_template('showmap.html', map=get_map_data_from_id(mapid))

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/', methods=['GET','POST'])
def index_or_upload():
    '''
    If a GET request is given to /, return recent maps
    If a POST request is made, grab logic and layout from 
    request (with keys logic and layout), or find png and json files
    from file[] (needed for dropzone)

    # TODO: break this apart into two separate functions (upload and index)
    '''
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
    '''
    Show a single map given by mapid
    '''
    mapid = request.args.get('mapid', '')
    return render_template('showmap.html', map=get_map_data_from_id(mapid))

def get_map_data_from_id(mapid):
    '''
    Return JSON mapdata from given mapid
    '''
    m = Map.query.get(mapid)
    return get_map_data(m)

def get_map_data(m):
    '''
    Input: map from database - given by Maps class from sqlalchemy
    Output: Map formatted in JSON
    '''
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

@app.route("/a/<author>")
def return_maps_by_author(author):
    maps = recent_maps(author=author)
    maps_data = get_data_from_maps(maps)
    return render_template('showmaps.html', maps=maps_data)

@app.route("/download")
def download():
    '''
    Download a file, parsing the mapid, mapname, and filetype from the request
    INPUT: mapid, filetype, and mapname
    OUTPUT: send_from_directory(filename) that downloads the file

    The options specified in send_from_directory change the file
    that is mapid.json -> mapname.json
    The JSON file needs the as_attachment variable set so it downloads as a json
    file, rather than a extensionless file
    '''
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
    '''
    Search the sqlachemy db object database
    INPUT: query or mapname and author
    OUTPUT: Map objects that match the search criteria
    '''
    maps = []
    if author and mapname:
        maps = Map.query.filter(Map.author.ilike(author)).filter(Map.mapname.ilike(mapname)).first()
    else:
        querystring = "%"+query +"%"
        maps = Map.query.filter(Map.author.ilike(querystring)).all()
        maps.extend(Map.query.filter(Map.mapname.ilike(querystring)).all())
    return maps

def get_data_from_maps(maps):
    '''
    INPUT: list of Map objects
    OUTPUT: list of JSON objects
    '''
    for m in maps:
        yield get_map_data(m)

@app.route("/search")
def search():
    '''
    Search the database with query from request
    If no query is specified, return recent_maps
    This is so when you search something, then delete the search,
    recent_maps are returned
    '''
    query = request.args.get("query", "")
    if query:
        maps = search_db(query=query)
    else:
        maps = recent_maps()

    maps_data = get_data_from_maps(maps)

    data = render_template('showmaps.html', maps=maps_data, standalone=True)
    # standalone renders the showmaps.html template by itself
    # having flask render the template and replacing the map div with 
    # the processed template

    return jsonify(success=True, html=data)

if __name__ == '__main__':
    app.run(debug=app.debug)
