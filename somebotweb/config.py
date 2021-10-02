import os
from collections import OrderedDict
DEBUG = False
SQLALCHEMY_DATABASE_URI = "postgres:///{}".format(os.environ.get("SOMEBOT_DB", "somebot"))
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
