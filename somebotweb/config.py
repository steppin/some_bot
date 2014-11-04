import os
from somebotweb.test_servers import server_description, zone_list
DEBUG = False
SQLALCHEMY_DATABASE_URI = "postgres:///{}".format(os.environ.get("SOMEBOT_DB", "somebot"))
MAX_CONTENT_LENGTH = 512 * 1024  # 512KB
ZONE_LIST = zone_list
SERVER_DESCRIPTION = server_description
