import time
import datetime

from flask import url_for

from somebotweb import db

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column('id', db.Integer, primary_key=True)
    mapid = db.Column('mapid', db.ForeignKey('map.id'))
    userid = db.Column('userid', db.ForeignKey('users.id'))

    def __init__(self, mapid, userid):
        self.mapid = mapid
        self.userid = userid

class User(db.Model):
    __tablename__ = 'users'  # 'user' is special in postgres
    id = db.Column('id', db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True)
    email = db.Column(db.Text)
    texture_pack = db.Column(db.Text, default="Vanilla")
    test_server = db.Column(db.Text, default="us")

    def __init__(self, username, email):
        self.username = username
        self.email = email

    def is_authenticated(self):
        return True
 
    def is_active(self):
        return True
 
    def is_anonymous(self):
        return False
 
    def get_id(self):
        return unicode(self.id)
 
    def __repr__(self):
        return '<User %r>' % (self.username)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column('id', db.Integer, primary_key=True)
    mapid = db.Column(db.Integer, db.ForeignKey('map.id'))
    userid = db.Column(db.Integer, db.ForeignKey('users.id'))
    username = db.Column(db.Text)
    text = db.Column(db.Text)
    time = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, mapid, userid, username, text):
        self.mapid = mapid
        self.userid = userid
        self.username = username
        self.text = text

    def alert_map(self):
        m = Map.query.filter_by(id=self.mapid).first()
        m.newcomments = 1
        db.session.add(m)
        db.session.commit()

class Map(db.Model):
    # TODO: package instead of module
    # TODO: nicer docstrings
    '''
    The map schema
    To make a map, we need a mapname, and author, and a description
    times_tested, last_tested and upload_time are generated when a map
    object is created
    '''

    id = db.Column(db.Integer, primary_key=True)

    # TODO: make sure mapname gets indexed
    mapname = db.Column(db.Text)
    author = db.Column(db.Text)
    description = db.Column(db.Text)
    upload_time = db.Column(db.Float)
    # TODO: sql alchemdy doesn't have some date type?
    last_tested = db.Column(db.Float)
    times_tested = db.Column(db.Integer)
    status = db.Column(db.Text)
    userid = db.Column(db.Integer, db.ForeignKey('users.id'))
    votes = db.Column(db.Integer, default=0)
    newcomments = db.Column(db.Integer, default=0)

    def __init__(self, mapname, author, description, userid=-1, status=None, upload_time=None):
        self.mapname = mapname
        self.author = author
        self.description = description
        self.upload_time = upload_time or time.time()
        self.last_tested = 0
        self.times_tested = 0
        self.status = status
        self.userid = userid

    def __repr__(self):
        return "<Map [%s] %s - %s - userid: %s>" %(str(self.id), self.mapname, self.author, self.userid)

    def get_json(self):
        # TODO: this just returns a python dict, not json :/
        '''
        Input: map from database - given by Map class from sqlalchemy
        Output: Map formatted in JSON
        '''
        strid = str(self.id)

        map_data = {
            'mapid': self.id,
            'mapname': self.mapname,
            'author': self.author,
            'description': self.description,
            'status': self.status,
            'jsonurl': "/static/maps/"+strid+'.json',
            'uploaddate': time.strftime('%Y-%m-%d', time.localtime(self.upload_time)),
            'pngurl': "/static/maps/"+strid+'.png',
            'previewurl': "/static/previews/"+strid+'.png',
            'thumburl': "/static/thumbs/"+strid+'.png',
            'times_tested': self.times_tested,
            "mapurl": "/show/"+strid,
            "authorurl": url_for('return_maps_by_author', author=self.author),
            # TODO:  why mapname in here?
            # TODO: it's to name the downloaded file; we should move to
            # storing the files in directories (with name id) and then
            # keeping nice names inside.
            "pngdownload": u"/download?mapname={mapname}&type=png&mapid={mapid}".format(mapname=self.mapname, mapid=strid),
            "jsondownload": u"/download?mapname={mapname}&type=json&mapid={mapid}".format(mapname=self.mapname, mapid=strid),
            "userid": self.userid,
            "votes": self.votes,
            "newcomments": self.newcomments
            }
        return map_data

    def has_voted(self, userid):
        voted = Vote.query.filter_by(userid=userid, mapid=self.id).count()
        return False if not voted else True

    def vote(self, userid):
        already_voted = self.has_voted(userid)
        vote_status = None
        if not already_voted:
            v = Vote(self.id, userid)
            db.session.add(v)
            self.votes = self.votes + 1
            vote_status = True
        else:
            v = Vote.query.filter_by(userid=userid, mapid=self.id).first()
            db.session.delete(v)
            self.votes = self.votes - 1
            vote_status = False
        db.session.commit() # for the vote count
        return vote_status

    def color_helper(self, userid):
        if has_voted(userid):
            return "#d43f3a"
        else:
            return "#428bca"

    def clear_comment(self):
        self.newcomments = 0

db.Index('mapname_idx', db.func.lower(Map.mapname))
db.Index('mapname_trgm_idx', Map.mapname, postgresql_ops={'mapname': 'gist_trgm_ops'}, postgresql_using="gist")
