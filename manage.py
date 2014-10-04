import json
import os.path

from flask.ext.script import Manager

from somebotweb import app, db
from somebotweb.views import generate_preview, generate_thumb, add_map_to_db


manager = Manager(app)


@manager.command
def add_map(layout, logic, status=None):
    # TODO: really need to refactor things so that we don't depend on
    # save() but until then we're just copying the logic from views.py
    # which is not ideal.
    layout = open(layout)
    logic = open(logic)

    logic_data = json.loads(logic.read())
    mapname = logic_data.get('info', {}).get('name', 'No name')
    author = logic_data.get('info', {}).get('author', 'No author')
    description = logic_data.get('info', {}).get('description', 'No description')
    pam = add_map_to_db(mapname, author, description, status)
    mapid = str(pam.id)

    layoutpath = os.path.join(app.config['UPLOAD_DIR'], mapid+'.png')
    with open(layoutpath, "wb") as f:
        f.write(layout.read())
    pam.layoutpath = layoutpath
    logicpath = os.path.join(app.config['UPLOAD_DIR'], mapid+'.json')
    # TODO: views should really be using .save()... and we should probabyl just use shutil here...
    with open(logicpath, "wb") as f:
        f.write( json.dumps(logic_data, logicpath))

    generate_preview(mapid)
    generate_thumb(mapid)

    print 'new map id: {}'.format(mapid)


if __name__ == '__main__':
    manager.run()
