import time
import datetime

from flask import url_for

from somebotweb import db

from sqlalchemy.orm import relationship, backref

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column('id', db.Integer, primary_key=True)
    mapid = db.Column('mapid', db.ForeignKey('maps.id'))
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
    mapid = db.Column(db.Integer, db.ForeignKey('maps.id'))
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
    __tablename__ = 'maps'
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
    upload_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    # TODO: sql alchemdy doesn't have some date type?
    last_tested = db.Column(db.Float)
    times_tested = db.Column(db.Integer)
    status = db.Column(db.Text)
    userid = db.Column(db.Integer, db.ForeignKey('users.id'))
    votes = db.Column(db.Integer, default=0)
    newcomments = db.Column(db.Integer, default=0)
    feedback_allowed = db.Column(db.Integer, default=1)
    is_primary_version = db.Column(db.Integer, default=1)
    remixes = relationship("Map")
    parent_id = db.Column(db.Integer, db.ForeignKey('maps.id'))
    version = db.Column(db.Integer, default=1)

    def __init__(self, mapname, author, description, userid=-1, status=None, upload_time=None):
        self.mapname = mapname
        self.author = author
        self.description = description
        self.last_tested = 0
        self.times_tested = 0
        self.status = status
        if userid > 0:
            self.userid = userid
            self.is_primary_version = 1
        if(author != "Anonymous" and mapname != "Untitled" and userid>0):
            query = Map.query.filter_by(mapname=mapname, author=author, userid=self.userid)
            if query.count() > 0:
                print query.all()
                parent = query.order_by("upload_time desc").first()
                print "There are previous versions of this"
                print "Pv: ", parent.version
                print "parent id: ", parent.parent_id

                self.version = parent.version+1
                parent.is_primary_version = 0
                self.parent_id = parent.id

            maps = query.all()
            for m in maps:
                if m.is_primary_version:
                    m.is_primary_version = 0
                    db.session.add(m)
            if len(maps) > 0:
                db.session.commit()
            self.is_primary_version = 1

    def __repr__(self):
        return "<Map [%s] %s - %s - userid: %s>" %(str(self.id), self.mapname, self.author, self.userid)

    def has_voted(self, userid):
        voted = Vote.query.filter_by(userid=userid, mapid=self.id).count()
        return False if not voted else True

    def vote(self, userid):
        already_voted = self.has_voted(userid)
        vote_status = None
        if self.votes is None: self.votes = 0
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

    def versions(self):
        if(self.mapname != "Untitled" and self.author != "Anonymous"):
            versions = Map.query.filter_by(mapname=self.mapname, author=self.author, userid=self.userid).order_by("upload_time asc").all()
            return reversed(zip(range(1,100), versions))
        else:
            return []

    def set_primary(self):
        if self.is_primary_version:
            return True
        else:
            maps = Map.query.filter_by(userid=self.userid, mapname=self.mapname, author=self.author, is_primary_version=1).all()
            for m in maps:
                print m, m.version, m.is_primary_version
                m.is_primary_version = 0
                db.session.add(m)
            self.is_primary_version = 1
            db.session.add(self)
            db.session.commit()
            return True

    def toggle_feedback(self):
        status = None
        if self.feedback_allowed:
            self.feedback_allowed = 0
            status = False
        else:
            self.feedback_allowed = 1
            status = True
        return status


db.Index('mapname_idx', db.func.lower(Map.mapname))
db.Index('mapname_trgm_idx', Map.mapname, postgresql_ops={'mapname': 'gist_trgm_ops'}, postgresql_using="gist")
