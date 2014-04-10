from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
import time

app = Flask(__name__)
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
        print strid, self.mapname, self.author
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
            "mapurl":u"/a/{author}/{mapname}".format(author=self.author, mapname=self.mapname) if self.author else "/show/"+strid,
            "authorurl":url_for('return_maps_by_author', author=self.author),
            "pngdownload":u"/download?mapname={mapname}&type=png&mapid={mapid}".format(mapname=self.mapname, mapid=strid),
            "jsondownload":u"/download?mapname={mapname}&type=json&mapid={mapid}".format(mapname=self.mapname, mapid=strid),
            }
        return map_data


if __name__ == "__main__":
    import sys
    if sys.argv[-1] == "MAKEDB":
        db.drop_all()
        db.session.commit()
        db.create_all()
        db.session.commit()