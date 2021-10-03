some_bot
========

some_bot: a tagpro helper bot

Some Bot Web
============

Environment Vars
----------------

    SOMEBOT_DB - specify the name of the postgres database to use

    SOMEBOT_CFG - specify a custom config file to override settings in config.py and secret.py

Setup
-----

1. install postgres server and create a db (default, "somebot") that your user can write to

2. create a virtual environment and

        pip install -r requirements.txt

3. create some directories

        mkdir static/{maps,previews,thumbs}  # TODO: not sure if this is needed anymore

4. create your `secret.py` by following the template in `secret.py.example`


Production notes learned the hard way
---

1. Initially `previewer.py` and any time textures are modified:

        cd somebotweb
        python -c 'import previewer; previewer.init_textures()'


Run dev server
----

**NOTE:** do not expose this to the outside world since it exposes a debug console by default!

    python manage.py runserver
