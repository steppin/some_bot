import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import requests
import os.path
import psycopg2
from random import shuffle


class TagproTestMap(callbacks.Plugin):
    """This plugin allows you to create test games from irc.
    Use the "test" command to create a new game.
    """
    threaded = True

    def __init__(self, irc):
        self.__parent = super(TagproTestMap, self)
        self.__parent.__init__(irc)
        # TODO: better exception and better way to do defaults?
        try:
            db_name = self.registryValue('dbName')
        except:
            db_name = 'dbname=somebot'
        self.db = TagproTestMapDb(db_name)

    def die(self):
        callbacks.Plugin.die(self)
        self.db.conn.close()

    def listmaps(self, irc, msg, args, search_string):
        """[search_string]

        Searches for maps whose names are similar to search_string or that were submitted during week search_string.
        """
        if search_string:
            map_results = self.db.search_map_names(search_string)
        else:
            if ircutils.isChannel(msg.args[0]):
                irc.reply('Please use a private message to browse the full list.  Alternatively, provide a search string or week number, or visit http://maps.jukejuice.com')
                return
            map_results = self.db.get_all_map_names()

        if map_results:
            num_map_results = len(map_results)
            maps = ', '.join(map_results)
            resp = '{} result{}: {}'.format(num_map_results, 's' if num_map_results > 1 else '', maps)
        else:
            resp = ('Sorry, I cannot find "{}".').format(search_string)

        irc.reply(resp)

    listmaps = wrap(listmaps, [optional('text')])

    # TODO: move this to utils outside both irc and somebotweb and have
    # them both use it?
    def __test(self, irc, msg, args, mapname, url) :
        """<mapname>

        Creates a test game with <mapname>.

        Returns true iff it couldn't open the map because of the server
        """

        # TODO: configure a map directory
        name = mapname
        best_map = self.db.get_best_map(name)
        if not best_map:
            map_results = self.db.fuzzy_search(name)
            if map_results:
                fuzzies = ', '.join(map_results)
                resp = 'Sorry, I cannot find "{}" in my brain!  Did you mean one of these: {} ?'.format(name, fuzzies)
            else:
                resp = ('Sorry, I cannot find "{}" in my brain!').format(name)

            #irc.error('I cannot find the map "{}" in my brain!'.format(name))
            irc.reply(resp)
            return
        (mapid, author) = best_map
        mapdir = '/home/somebot/tagpro/maps'
        layout = os.path.join(mapdir, '{}.png'.format(mapid))
        logic = os.path.join(mapdir, '{}.json'.format(mapid))
        try:
            files = {'logic': open(logic, 'rb'), 'layout': open(layout, 'rb')}
        except IOError:
            irc.error('I cannot find that map!')
            return
        try:
            r = requests.post(url, files=files)
        except requests.ConnectionError as e:
            # TODO(step): log or print to stderr instead
            print e
            irc.reply("I tried to upload the map but I had trouble reaching the server ("+url+")!")
            return True
        testurl = r.url
        if testurl == url:
            if 'all testing games are full at the moment' in r.content:
                irc.reply("Sorry, all testing games are full at the moment!");
            else:
                print layout, logic, url, r.content, r.status_code
                irc.reply("I tried to upload the map but the server ("+url+") didn't like it.  Ask my owner to give me better debug output :(")
            return True
        else:
            irc.reply('{} ({})'.format(testurl, name))

    def test(self, irc, msg, args, mapname):
        """<mapname>

        Creates a test game with <mapname>.
        """

        url = 'http://tagpro-maptest.koalabeast.com/testmap'
        self.__test(irc, msg, args, mapname, url)

    test = wrap(test, ['text'])

    def testeu(self, irc, msg, args, mapname):
        """<mapname>

        Creates a test game with <mapname> on a european server.
        """
        # TODO: remove justletme.be -- no longer running
        urls = ['http://maptest.newcompte.fr/testmap', 'http://justletme.be:8080/testmap']
        shuffle(urls)
        for url in urls:
            if not self.__test(irc, msg, args, mapname, url):
                return
            else:
                irc.reply("Trying another server..")
        url = 'http://tagpro-maptest.koalabeast.com/testmap'
        self.__test(irc, msg, args, mapname, url)

    testeu = wrap(testeu, ['text'])


    def preview(self, irc, msg, args, mapname):
        """<mapname>

        Returns a link to the preview for mapname>.
        """

        # TODO: configure a map directory
        name = mapname
        best_map = self.db.get_best_map(name)
        if not best_map:
            irc.error('I cannot find the map "{}" in my brain!'.format(name))
            return
        (preview_id, author) = best_map
        if not preview_id:
            irc.reply("Sorry, I don't have a preview for that map.")
            return
        preview_url = 'http://maps.jukejuice.com/show/{}'.format(preview_id)
        irc.reply('{} ({})'.format(preview_url, mapname))

    preview = wrap(preview, ['text'])


class TagproTestMapDb(object):
    def __init__(self, db_string):
        self.conn = psycopg2.connect(db_string)

    def get_all_map_names(self):
        # TODO: psycopg2 added support for with at some point; move to using that idiom instead
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT mapname FROM map ORDER BY mapname")
            # TODO: some better way?  gen instead?
            return [row[0] for row in cur.fetchall()]
        finally:
            cur.close()

    def search_map_names(self, search_string):
        esc_search_string = search_string.replace('=', '==').replace('%', '=%').replace('_', '=_')
        cur = self.conn.cursor()
        try:
           cur.execute("SELECT mapname FROM map WHERE mapname ILIKE %s ESCAPE '=' ORDER BY mapname", ('%' + esc_search_string + '%',))
           return [row[0] for row in cur.fetchall()]
        finally:
           cur.close()

    def get_best_map(self, name):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT id, author FROM map WHERE lower(mapname) = lower(%s)", (name,))
            return cur.fetchone()
        finally:
            cur.close()

    def fuzzy_search(self, name):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT mapname, similarity(mapname, %s) as sml FROM map WHERE mapname %% %s ORDER BY sml DESC, mapname LIMIT 5", (name, name))
            return [row[0] for row in cur.fetchall()]
        finally:
            cur.close()

Class = TagproTestMap
