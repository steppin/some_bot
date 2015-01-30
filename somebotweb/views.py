import os
import time
import requests
import simplejson as json
from functools import wraps
import datetime

from . import app, db, google
from .models import User, Map, Comment, Vote
from PIL import Image, ImageOps
from flask import request, g, redirect, url_for, abort, render_template, send_from_directory, jsonify, session, flash, render_template_string
from werkzeug import secure_filename
from sqlalchemy import or_

import previewer
import config

@app.template_filter()
def timesince(dt, default="just now"):
    """
    Shamelessly stolen from flask's snippets
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    """

    now = datetime.datetime.utcnow()
    diff = now - dt
    
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )
    for period, singular, plural in periods:        
        if period:
            return "%d %s" % (period, singular if period == 1 else plural)
    return default

@app.before_request
def lookup_current_user():
    g.user = None
    if 'google_oauth' in session:
        g.user = session['google_oauth']
        g.email = session['email']
        g.userid = session['id']
        user = get_user_from_db(userid=g.userid)
        g.username = user.username

# TODO: probably no point in having separate templates for each error here...
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def page_not_found(e):
    return render_template('500.html'), 500

def add_map_to_db(mapname, author, description, userid=-1, status=None):
    '''
    Add a map to the sqlalchemy db object
    INPUT: mapname, author, description
    OUTPUT: mapid string

    #TODO: Make mapid consistent - it's not handled well right now
    # Sometimes integers are used (looking in db), sometimes strings (filenames)
    '''
    m = Map(mapname, author, description, status=status, userid=userid)
    db.session.add(m)
    db.session.commit()
    if userid > 0:
        m.vote(userid)
    print "New map -> [%s] %s by %s" %(m.id, mapname, author)
    return m

def delete_map_from_db(mapid, user):
    map_ = Map.query.filter_by(id=mapid).first()
    if map_ and user:
        currentuser = g.userid
        if currentuser == user.id and map_.userid == user.id:
            print "Deleting map", mapid
            Comment.query.filter_by(mapid=mapid).delete()
            Vote.query.filter_by(mapid=mapid).delete()
            m = Map.query.filter_by(id=mapid).first()
            if m.is_primary_version:
                if m.parent_id:
                    p = get_map_by_id(m.parent_id)
                    p.is_primary_version = 1
                    db.session.add(p)
            db.session.delete(m)
            db.session.commit()
            return True
        return False
    return False

def add_map(layout, logic, userid=-1):
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

    if userid > 0:
        user = get_user_from_db(userid=userid)
        author = user.username
        texture_pack = user.texture_pack
    else:
        author = logic_data.get('info', {}).get('author', 'No author')
        texture_pack = "Vanilla"


    mapname = logic_data.get('info', {}).get('name', 'No name')
    description = logic_data.get('info', {}).get('description', 'No description')
    pam = add_map_to_db(mapname, author, description, userid=userid)
    mapid = str(pam.id)



    layoutpath = os.path.join(app.config['UPLOAD_DIR'], mapid+'.png')
    layout.save(layoutpath)
    pam.layoutpath = layoutpath
    logicpath = os.path.join(app.config['UPLOAD_DIR'], mapid+'.json')
    with open(logicpath, "wb") as f:
        f.write( json.dumps(logic_data, logicpath))

    generate_preview(mapid, texture_pack)
    generate_thumb(mapid)

    # TODO check if map actually was inserted correctly
    return mapid


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


def generate_preview(mapid, texture="Vanilla"):
    '''
    INPUT: mapid
    OUTPUT: None

    Generate a preview from the logic and json files given by
    mapid.png and mapid.json in the app's upload directory.

    Uses some_bot's previewer script to create preview
    '''
    layout = os.path.join(app.config['UPLOAD_DIR'], mapid + '.png')
    logic = os.path.join(app.config['UPLOAD_DIR'], mapid + '.json')
    map_ = previewer.plot(layout, logic, texture)
    preview = map_.draw()
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


def recent_maps(page=0, page_size=18):
    '''
    Get recent maps from the database
    INPUT: All optional - author, page_size (number of entries), and offset for pagination
    OUTPUT: Map objects ordered by upload_time descending
    '''
    query = Map.query.filter_by(is_primary_version=1)
    total = query.count()
    maps = query.order_by("upload_time desc").offset(page_size*page).limit(page_size).all()
    pages = None
    if total > page_size:
        pages = paginate(page, 9, total/page_size+2)
    return maps, pages


def get_test_link(mapid, zone='us'):
    '''
    INPUT: map id (primary key of db)
    INPUT: zone (two-letter identifier for the server)
    OUTPUT: test url from test server

    Given a map name, grabs logic and layout data from the app's config folders,
    sends post request to test server and returns test url server responds with
    '''
    test_server = app.config['TEST_SERVERS'][zone]['url'] + 'testmap'
    layout = os.path.join(app.config['UPLOAD_DIR'], str(mapid) + '.png')
    logic = os.path.join(app.config['UPLOAD_DIR'], str(mapid) + '.json')
    file_data = {'logic':open(logic).read(), 'layout':open(layout).read()}

    r = requests.post(test_server, files=file_data)
    return r.url


def get_map_by_id(mapid):
    return Map.query.filter_by(id=mapid).first()

@app.route("/save/<int:mapid>", methods=['GET'])
def save_map(mapid):
    user = get_user_from_db(userid=g.get("userid", -1))
    return render_template("showmap.html", user=user, map=get_map_by_id(mapid))


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
    if request.method == "POST":
        layout = request.files.get("layout", None)
        logic = request.files.get("logic", None)
        generate_test = request.args.get("generate_testlink", False)

        # Handle upload by dropzone, not sure how to specify filenames with dropzone
        # it sends just a list of files
        if not logic and not layout:
            for f in request.files.itervalues():
                if os.path.splitext(f.filename)[1].lower() == '.json':
                    logic = f
                elif os.path.splitext(f.filename)[1].lower() == '.png':
                    layout = f

        if layout and logic:
            mapid = add_map(layout, logic,userid=g.get('userid', -1))
            success = mapid >= 0
            if success:
                if generate_test:
                    test_url = get_test_link(mapid)
                    return jsonify(testurl=test_url, success=success)
                else:
                    save_url = url_for('save_map', mapid=mapid)
                    return jsonify(saveurl=save_url, success=success)
        json_error_response = jsonify(error="Map upload failed!")
        json_error_response.status_code = 400
        return json_error_response
    else:
        # TODO: not sure we really want to do this...
        return render_template("upload.html", map={})


def paginate(page, page_size, total_pages):
    # Create a range of pages given by
    # the current page, the page_size and the total number of pages
    # [1, 2, 3, ..., page_size]
    # [6, 7, 8, ... 6+page_size]
    # [7, 8, 9, ... min(7+page_size, total_pages))]
    start = max(1, page-page_size/2+1)
    stop = min( max(page+page_size/2+2, page_size), total_pages)
    return range(start, stop)
    '''
    if page < page_size/2:
        return range(1,min(page_size, total_pages))
    else:
        return range(page-page_size/2+1, min(page+page_size/2+2, total_pages))
    '''

@app.route("/feedback")
@google.authorized_handler
def toggle_feedback(resp):
    status = None
    mapid = request.args.get("mapid", 0)
    if mapid:
        m = get_map_by_id(mapid)
        if m.userid == g.userid:
            status = m.toggle_feedback()
            db.session.add(m)
            db.session.commit()
    return jsonify(feedback_status=status)

@app.route('/mymaps', methods=['GET', 'POST'])
@google.authorized_handler
def listmaps(resp):
    user = User.query.filter_by(id=g.get('userid')).first()
    if request.method == "POST":
        username = request.form.get('username')
        test_server = request.form.get('test_server')
        texture_pack = request.form.get('texture_pack')
        if username and username != user.username:
            user.username = username
        if test_server != user.test_server:
            user.test_server = test_server
        if texture_pack != user.texture_pack:
            user.texture_pack = texture_pack
        db.session.commit()

    user = User.query.filter_by(id=g.get('userid')).first()
    maps = Map.query.filter_by(userid=g.get('userid')).order_by("upload_time desc").all()
    textures = os.listdir(previewer.RESOURCE_DIR)
    test_servers = config.TEST_SERVERS
    return render_template('showmaps.html', profile=True,  user=user, maps=maps, textures=textures, servers=test_servers)

@app.route("/vote")
@google.authorized_handler
def vote(resp):
    mapid = request.args.get("mapid", -1)
    userid = request.args.get("userid", -1)
    if userid > 0 and mapid > 0:
        m = Map.query.filter_by(id=mapid).first()
        vote_status = m.vote(userid)
        return jsonify(vote_status=vote_status)
    else:
        return jsonify(vote_status=False)

@app.route("/set_primary")
@google.authorized_handler
def set_primary(resp):
    mapid = request.args.get("mapid", -1)
    m = get_map_by_id(mapid)
    status = False
    if m.userid == g.userid:
        status = m.set_primary()
    return jsonify(primary_status=status)

@app.route('/', methods=['GET'])
def index():
    '''
    If a GET request is given to /, return recent maps
    '''
    page = request.args.get("page", 1)
    try:
        page = int(page)
        if page <= 0:
            page = 1
    except:
        page = 1
    maps, pages = recent_maps(page=(page-1))
    user = get_user_from_db(userid=g.get('userid'))
    return render_template('showmaps.html', maps=maps, user=user, paginate=(pages), pages=pages, current_page=page, active_page='index')

@app.route('/login')
def login():
    return google.authorize(callback=url_for('authorized', _external=True))

@app.route('/logout')
def logout():
    session.pop('google_oauth', None)
    return redirect(url_for('index'))

def update_username(userid, username):
    print "Updating user...", userid, username
    if User.query.filter_by(username=username).count() == 0:
        user = User.query.filter_by(id=userid).first()
        user.username = username
        db.session.merge(user)
        db.session.commit()
        return True
    return False

def add_user_to_db(email):
    u = User(email=email, username=None)
    db.session.add(u)
    db.session.commit()
    print "New User -> [%s] %s %s" %(u.id, u.username, u.email)
    return u

def get_user_from_db(email=None, userid=None):
    user = {}
    if email:
        return User.query.filter_by(email=email).first()
    if userid > 0:
        return User.query.filter_by(id=userid).first()
    return user

@app.route('/login/authorized')
@google.authorized_handler
def authorized(resp):
    if resp is None:
        # TODO: this seems stupid; render it on some page...
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    # TODO: apparently resp can be an OAuthException (we should handle
    # that)
    session['google_oauth'] = resp
    try:
        email = google.get('userinfo').data['email']
    except KeyError:
        email = None

    if email:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = add_user_to_db(email)
        else:
            user = get_user_from_db(email)
        session['id'] = user.id
        session['email'] = user.email

    return redirect(url_for('index'))


@google.tokengetter
def get_google_oauth_token():
    if 'google_oauth' in session:
        resp = session['google_oauth']
        return (resp['access_token'], '')


@app.route('/show/<int:mapid>')
def show_map(mapid):
    '''
    Show a single map given by mapid
    '''
    user = {}
    if g.get("userid") > 0:
        user = get_user_from_db(userid=g.get("userid"))
        m = Map.query.filter_by(id=mapid).first()
        if m.userid == user.id:
            m.newcomments = 0
            db.session.add(m)
            db.session.commit()
    return render_template('showmap.html', user=user, map=get_map_by_id(mapid), comments=get_comments(mapid))

@app.route('/delete')
def delete_map():
    mapid = request.args.get("mapid")
    user = get_user_from_db(email=g.email)
    status = delete_map_from_db(mapid, user)
    return jsonify(delete_status=status)

def get_json_by_id(mapid):
    '''
    Return JSON mapdata from given mapid
    INPUT: mapid (integer)
    OUTPUT: Map JSON
    '''
    m = Map.query.get_or_404(mapid)
    return m

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_comments(mapid):
    comments = Comment.query.filter_by(mapid=mapid).order_by('time desc').all()
    return comments

def render_comments(mapid):
    comments = get_comments(mapid)
    template = '''
    {% for comment in comments %}
        <li class="list-group-item" style="word-break: break-all;">{{comment.time|timesince}}&nbsp;<b>{{ comment.username }}</b> - {{comment.text}}</li>
    {% endfor %}'''
    return render_template_string(template, comments=comments)

@app.route("/comment", methods=['GET', 'POST'])
@login_required
def insert_comment():
    text = request.args.get("text", "")
    if text and g.get('userid', None):
        userid = g.get("userid", None)
        mapid = request.args.get("mapid", -1)
        username = g.get('username')
        print "New comment: ", mapid, userid, text
        c = Comment(mapid, userid, username, text)
        c.alert_map()
        db.session.add(c)
        db.session.commit()
    return jsonify({'comments':render_comments(mapid)})

@app.route("/maptest/<int:mapid>", defaults={'zone': 'us'})
@app.route("/maptest/<int:mapid>/", defaults={'zone': 'us'})
@app.route("/maptest/<int:mapid>/<zone>")
def test_map(mapid, zone):
    if mapid:
        showurl = url_for('save_map', mapid=mapid)
        testurl = get_test_link(mapid, zone)
        increment_test(mapid)
        if testurl:
            return redirect(testurl)
        else:
            # TODO: do something smarter
            return abort(404)
    else:
        return abort(404)


@app.route("/m/<mapname>")
def get_map_by_mapname(mapname):
    m = search_db(mapname=mapname)
    if m:
        return render_template("showmap.html", map=m)
    else:
        return redirect(url_for('index'))


@app.route("/a/<author>")
def return_maps_by_author(author):
    page = request.args.get("page", 1)
    try:
        page = int(page)
        if page <= 0:
            page = 1
    except:
        page = 1
    maps, pages = search_db(author=author)
    if not maps:
        maps = recent_maps()
    user = get_user_from_db(userid=g.get("userid", -1))
    return render_template('showmaps.html', maps=maps, user=user, paginate=pages, pages=pages, current_page=page)


@app.route("/a/<author>/<mapname>")
def return_map_by_author(author, mapname):
    if author and mapname:
        m = search_db(author=author, mapname=mapname)
        if m:
            return render_template("showmap.html", map=m)
    else:
        maps = recent_maps()
        return render_template('showmaps.html', maps=maps_data)


@app.route("/s/<status>")
def get_maps_by_status(status):
    page = request.args.get("page", 1)
    try:
        page = int(page)
        if page <= 0:
            page = 1
    except:
        page = 1
    maps, pages = search_db(status=status, page=(page-1))
    return render_template('showmaps.html', maps=maps, paginate=(pages), pages=pages, current_page=page, active_page=status)


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
    mapname = request.args.get("mapname", mapid)
    filetype = request.args.get("type", None)
    if mapid and filetype and mapname:
        if filetype == "png":
            return send_from_directory(app.config['UPLOAD_DIR'], secure_filename(mapid + '.png'), as_attachment=True, attachment_filename=secure_filename(mapname+".png"))
        elif filetype == "json":
            return send_from_directory(app.config['UPLOAD_DIR'], secure_filename(mapid + '.json'), as_attachment=True, attachment_filename=secure_filename(mapname+".json"))
        else:
            return abort(404)
    else:
        return abort(404)


def search_db(query=None, mapname=None, author=None, status=None, userid=None, page=0, page_size=30, order="upload_time desc"):
    '''
    Search the sqlachemy db object database
    INPUT: query or mapname and author
    OUTPUT: Map objects that match the search criteria

    #TODO: Spruce this up. Add page_size and offset for pagination
    '''
    maps = []

    if userid:
        maps = Map.query.filter_by(userid=userid)
    elif author and mapname:
        maps = Map.query.filter(Map.author.ilike(author)).filter(Map.mapname.ilike(mapname)).first()
        return maps
    elif author and not mapname:
        maps = Map.query.filter(Map.author.ilike(author))
    elif mapname and not author:
        maps = Map.query.filter(Map.mapname.ilike(mapname))
    elif status:
        maps = Map.query.filter_by(status=status)
    elif query:
        querystring = "%"+query +"%"
        maps = Map.query.filter(or_(Map.author.ilike(querystring), Map.mapname.ilike(querystring)))

    maps = maps.filter_by(is_primary_version=1)

    total = maps.count()
    maps = maps.order_by(order).offset(page_size*page).limit(page_size).all()
    pages = []
    if total > page_size:
        pages = paginate(page, 9, total/page_size+2)
    return maps, pages


def get_data_from_maps(maps):
    '''
    INPUT: list of Map objects
    OUTPUT: list of JSON objects
    '''
    for m in maps:
        yield m



@app.route("/search")
def search():
    '''
    Search the database with query from request
    If no query is specified, return recent_maps
    This is so when you search something, then delete the search,
    recent_maps are returned
    standalone tells whether to render the whole page (base.html + showmaps.html)
    or just render showmaps.html (for 'instant' searching)
    '''
    query = request.args.get("query", "")
    page = request.args.get("page", 1)
    standalone = request.args.get("standalone", False)

    try:
        page = int(page)
        if page <= 0:
            page = 1
    except:
        page = 1

    if query:
        maps, pages = search_db(query=query, page=(page-1))
    else:
        maps, pages = recent_maps()



    if standalone:
        data = render_template('showmaps.html', maps=maps, standalone=True, paginate=(pages), pages=pages, current_page=page, query=query)
        return jsonify(success=True, html=data)
    else:
        return render_template('showmaps.html', maps=maps, paginate=(pages), pages=pages, current_page=page, query=query)

def url_for_other_page(page, query=None):
    args = request.view_args.copy()
    args['page'] = page
    args['query'] = query
    return url_for(request.endpoint, **args)
app.jinja_env.globals['url_for_other_page'] = url_for_other_page

def has_voted(mapid, userid):
    m = Map.query.filter_by(id=mapid).first().has_voted(userid)
    if m:
        return "voted"
    else:
        return ""
app.jinja_env.globals['has_voted'] = has_voted