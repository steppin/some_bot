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

    def get_json(self):
        '''
        Input: map from database - given by Maps class from sqlalchemy
        Output: Map formatted in JSON
        '''
        strid = str(self.id)
        map_data = {
            'mapid':self.id,
            'mapname':self.mapname,
            'author':self.author,
            'description':self.description,
            'jsonurl':"/static/maps/"+strid+'.json',
            'pngurl':"/static/maps/"+strid+'.png',
            'previewurl':"/static/previews/"+strid+'.png',
            'thumburl':"/static/thumbs/"+strid+'.png',
            'times_tested':self.times_tested,
            "mapurl":"/a/%s/%s" %(self.author, self.mapname) if self.author else "/show/"+strid,
            "authorurl":url_for('return_maps_by_author', author=self.author)
            }
        return map_data


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
    return m

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
    author = logic_data.get('info', {}).get('author', "No author")
    description = logic_data.get('info', {}).get('description', "No description")
    if mapname and author:
        pam = add_map_to_db(mapname, author, description)
        mapid = str(pam.id)

        layoutpath = os.path.join(app.config['UPLOAD_DIR'], mapid+'.png')
        layout.save(layoutpath)
        pam.layoutpath = layoutpath
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
    preview_img = Image.open(preview_file)
    prex, prey = preview_img.size
    target_width = 250
    target_height = int(target_width * prey / float(prex))
    offset = (0, target_width/2 - target_height/2)
    if target_height > target_width:
        target_height = 250
        target_width = int(target_height * prex / float(prey))
        offset = (target_height/2 - target_width/2, 0)

    preview_img.thumbnail((target_width, target_height), Image.ANTIALIAS)
    centered_thumb = Image.new(preview_img.mode, size=(250,250), color=(0,0,0,255))
    centered_thumb.paste(preview_img, offset)
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
    return r.url

@app.route("/save/<int:mapid>", methods=['GET'])
def save_map(mapid):
    return render_template("showmap.html", map=get_json_by_id(mapid))

@app.route("/upload", methods=['GET', 'POST'])
def upload_map():
    '''
    Upload a map to the server
    The current process is:
    Look for files named layout and logic in the request
    If they're not there, look for a list of files names file[] (dropzone compatibility)
    If we have both a layout and a logic, save the file and generate previews, add to db, etc.
    If not, return a 404

    '''
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
        success = mapid >= 0
        if success:
            if generate_test:
                test_url = get_test_link(mapid)
                return jsonify(testurl=test_url, success=success)
            else:
                save_url = url_for('save_map', mapid=mapid)
                return jsonify(saveurl=save_url, success=success)
    else:
        abort(404)

@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
    This doesn't do anything yet
    It's here for posterity
    '''
    return render_template('login.html')

@app.route('/', methods=['GET'])
def index():
    '''
    If a GET request is given to /, return recent maps
    '''
    maps = recent_maps()
    return render_template('showmaps.html', maps=get_data_from_maps(maps))

@app.route('/show/<int:mapid>')
def show_map(mapid):
    '''
    Show a single map given by mapid
    '''
    return render_template('showmap.html', map=get_json_by_id(mapid))

def get_json_by_id(mapid):
    '''
    Return JSON mapdata from given mapid
    INPUT: mapid (integer)
    OUTPUT: Map JSON
    '''
    m = Map.query.get(mapid)
    return m.get_json()

@app.route("/maptest/<int:mapid>")
def test_map(mapid):
    if mapid:
        showurl = url_for('save_map', mapid=mapid)
        testurl = get_test_link(mapid)
        increment_test(mapid)
        if testurl:
            return jsonify(success=True, testurl=testurl, showurl=showurl)
        else:
            return jsonify(success=False, message="Couldn't generate a test url")
    else:
        return abort(404)

@app.route("/m/<mapname>")
def get_map_by_mapname(mapname):
    m = search_db(mapname=mapname)
    if m:
        return render_template("showmap.html", map=m.get_json())
    else:
        maps = recent_maps()
        maps_data = get_data_from_maps(maps)
        return redirect(url_for('index'))

@app.route("/a/<author>")
def return_maps_by_author(author):
    maps = search_db(author=author)
    if not maps:
        maps = recent_maps()
    maps_data = get_data_from_maps(maps)
    return render_template('showmaps.html', maps=maps_data)

@app.route("/a/<author>/<mapname>")
def return_map_by_author(author, mapname):
    if author and mapname:
        m = search_db(author=author, mapname=mapname)
        if m:
            return render_template("showmap.html", map=m.get_json())
    else:
        maps = recent_maps()
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

    #TODO: Spruce this up. Add page_limit and offset for pagination
    '''
    maps = []
    if author and mapname:
        maps = Map.query.filter(Map.author.ilike(author)).filter(Map.mapname.ilike(mapname)).first()
    elif author and not mapname:
        maps = Map.query.filter(Map.author.ilike(author)).all()
    elif mapname and not author:
        maps = Map.query.filter(Map.mapname.ilike(mapname)).all()
    elif query:
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
        yield m.get_json()

@app.route("/search")
def search():
    '''
    Search the database with query from request
    If no query is specified, return recent_maps
    This is so when you search something, then delete the search,
    recent_maps are returned
    '''
    query = request.args.get("query", "")
    standalone = request.args.get("standalone", False)
    if query:
        maps = search_db(query=query)
    else:
        maps = recent_maps()

    maps_data = get_data_from_maps(maps)
    # standalone renders the showmaps.html template by itself
    # having flask render the template and replacing the map div with 
    # the processed template
    if standalone:
        data = render_template('showmaps.html', maps=maps_data, standalone=True)
        return jsonify(success=True, html=data)
    else:
        return render_template('showmaps.html', maps=maps_data)


if __name__ == '__main__':
    app.run(debug=app.debug)
