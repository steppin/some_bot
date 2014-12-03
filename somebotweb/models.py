import time
import datetime

from flask import url_for

from somebotweb import db

class User(db.Model):
    __tablename__ = 'users'  # 'user' is special in postgres
    id = db.Column('id', db.Integer, primary_key=True)
    # TODO: Reconsider using Text and instead use String?  Probably some performance differences and ability to index blah blah blah
    username = db.Column(db.Text, unique=True)
    email = db.Column(db.Text)

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
        return '<User %r>' % (self.name)

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
            }
        return map_data


db.Index('mapname_idx', db.func.lower(Map.mapname))
db.Index('mapname_trgm_idx', Map.mapname, postgresql_ops={'mapname': 'gist_trgm_ops'}, postgresql_using="gist")
