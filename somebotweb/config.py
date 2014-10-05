import os
from collections import OrderedDict
DEBUG = False
SQLALCHEMY_DATABASE_URI = "postgres:///{}".format(os.environ.get("SOMEBOT_DB", "somebot"))
MAX_CONTENT_LENGTH = 512 * 1024  # 512KB
TEST_SERVERS = OrderedDict([
    ('us', {
        'url': 'http://tagpro-maptest.koalabeast.com/',
        'desc': 'Los Angeles',
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
