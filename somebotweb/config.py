import os

SQLALCHEMY_DATABASE_URI = "postgres:///{}".format(os.environ.get("SOMEBOT_DB", "somebot"))

UPLOAD_DIR = 'static/maps'
PREVIEW_DIR = 'static/previews'
THUMB_DIR = 'static/thumbs'
