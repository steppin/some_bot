import os

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_oauthlib.client import OAuth

app = Flask(__name__)
app.config.from_pyfile('config.py')
app.config.from_pyfile('secret.py')
app.config.from_envvar('SOMEBOT_CFG', silent=True)

app.config.update(
    UPLOAD_DIR=os.path.join(app.static_folder, 'maps'),
    PREVIEW_DIR=os.path.join(app.static_folder, 'previews'),
    THUMB_DIR=os.path.join(app.static_folder, 'thumbs'),
)

if not app.debug:
    # configure logging
    import logging
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    app.logger.addHandler(stream_handler)

app.logger.info('Using database: {}'.format(app.config.get('SQLALCHEMY_DATABASE_URI')))


oauth = OAuth(app)
google = oauth.remote_app(
    'google',
    consumer_key=app.config.get('GOOGLE_ID'),
    consumer_secret=app.config.get('GOOGLE_SECRET'),
    request_token_params={
        'scope': 'https://www.googleapis.com/auth/userinfo.email'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

db = SQLAlchemy(app)

# TODO: is there a better place for us to init the db?
import models
db.create_all()
db.session.commit()

import views