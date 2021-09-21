import os

from somebotweb.secret import DB_USER, DB_PWD

from collections import OrderedDict
DEBUG = False
SQLALCHEMY_DATABASE_URI = "postgresql://{}:{}@localhost:5432/{}".format(DB_USER, DB_PWD, os.environ.get("SOMEBOT_DB", "somebot"))
MAX_CONTENT_LENGTH = 512 * 1024  # 512KB
TEST_SERVERS = OrderedDict([
    ('us', {
        'url': 'https://tagpro-maptest-dallas.koalabeast.com/',
        'desc': 'Dallas (Us)',
    }),
    ('eu', {
        'url': 'https://tagpro-maptest-paris.koalabeast.com/',
        'desc': 'Paris (Fr)',
    }),
    ('au', {
        'url': 'https://tagpro-maptest-sydney.koalabeast.com/',
        'desc': 'Sydney (Au)',
    }),
])
