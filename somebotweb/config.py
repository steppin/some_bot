import os

from somebotweb.secret import DB_USER, DB_PWD

from collections import OrderedDict
DEBUG = False
SQLALCHEMY_DATABASE_URI = "postgresql://{}:{}@localhost:5432/{}".format(DB_USER, DB_PWD, os.environ.get("SOMEBOT_DB", "somebot"))
MAX_CONTENT_LENGTH = 512 * 1024  # 512KB
TEST_SERVERS = OrderedDict([
    ('us', {
        'url': 'http://tagpro-maptest.koalabeast.com/',
        'desc': 'Los Angeles (US)',
    }),
    ('ca', {
        'url': 'http://maptest2.newcompte.fr/',
        'desc': 'Montreal (Ca)',
    }),
    ('eu', {
        'url': 'http://maptest.newcompte.fr/',
        'desc': 'Paris (Fr)',
    }),
    ('au', {
        'url': 'http://oceanic.newcompte.fr/',
        'desc': 'Sydney (Au)',
    }),
])
