###
# Copyright (c) 2013, S Teppin
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import requests
import os.path
import psycopg2



class TagproTestMap(callbacks.Plugin):
    """This plugin allows you to create test games from irc.
    Use the "test" command to create a new game."""
    threaded = True

    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        self.conn = psycopg2.connect("dbname=tagpro user=steppin")
        self.cur = self.conn.cursor()

    def die(self):
        self.cur.close()
        self.conn.close()

    def listmaps(self, irc, msg, args, search_string):
        """[search_string]

        Searches for maps whose names are similar to search_string or that were submitted during week search_string.
        """

        if search_string:
            esc_search_string = search_string.replace('=', '==').replace('%', '=%').replace('_', '=_')
            self.cur.execute("SELECT name FROM maps WHERE tag = %s OR name ILIKE %s ESCAPE '=' ORDER BY name", (search_string, '%' + esc_search_string + '%'))
        else:
            if ircutils.isChannel(msg.args[0]):
                irc.reply('Please use a private message to browse the full list.  Alternatively, provide a search string or week number, or visit http://tagpro.imgur.com')
                return
            self.cur.execute("SELECT name FROM maps ORDER BY name")

        count = self.cur.rowcount
        if count > 0:
            maps = ', '.join(row[0] for row in self.cur.fetchall())
            resp = '{} result{}: {}'.format(count, 's' if count > 1 else '', maps)
        else:
            resp = ('Sorry, I cannot find "{}".').format(search_string)

        irc.reply(resp)
    listmaps = wrap(listmaps, [optional('text')])

    def test(self, irc, msg, args, mapname):
        """<mapname>

        Creates a test game with <mapname>.
        """

        # TODO: configure a map directory
        name = mapname
        self.cur.execute("SELECT tag, comment, author FROM maps WHERE name = %s", (name,))
        result = self.cur.fetchone()
        if not result:
            self.cur.execute("SELECT name, similarity(name, %s) as sml FROM maps WHERE name %% %s ORDER BY sml DESC, name LIMIT 5", (name, name))
            # TODO(step): there should be a way to avoid this count
            # check (be more pythonic)
            count = self.cur.rowcount
            if count > 0:
                fuzzies = ', '.join(row[0] for row in self.cur.fetchall())
                resp = 'Sorry, I cannot find "{}" in my brain!  Did you mean one of these: {} ?'.format(name, fuzzies)
            else:
                resp = ('Sorry, I cannot find "{}" in my brain!').format(name)

            #irc.error('I cannot find the map "{}" in my brain!'.format(name))
            irc.reply(resp)
            return
        (tag, mapid, author) = result
        mapdir = os.path.join('/home/steppin/tagpro/maps', tag)
        layout = os.path.join(mapdir, mapid + '.png')
        logic = os.path.join(mapdir, mapid + '.json')
        url = 'http://tagpro-maptest.koalabeast.com/testmap'
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
            irc.reply("I tried to upload the map but I had trouble reaching the server!")
            return
        #print r.content
        testurl = r.url
        if testurl == 'http://tagpro-maptest.koalabeast.com/testmap':
            irc.reply("I tried to upload the map but the server didn't like it.  Ask my owner to give me better debug output :(")
        else:
            #irc.reply('{} ({} by {})'.format(testurl, name, author))
            irc.reply('{} ({})'.format(testurl, name))

    test = wrap(test, ['text'])

    def preview(self, irc, msg, args, mapname):
        """<mapname>

        Returns a link to the preview for mapname>.
        """

        # TODO: configure a map directory
        name = mapname
        self.cur.execute("SELECT preview, author FROM maps WHERE name = %s", (name,))
        result = self.cur.fetchone()
        if not result:
            irc.error('I cannot find the map "{}" in my brain!'.format(name))
            return
        (preview_id, author) = result
        if not preview_id:
            irc.reply("Sorry, I don't have a preview for that map.")
            return
        imgur_url = 'http://imgur.com/'
        preview_url = imgur_url + preview_id + '.png'
        #irc.reply('{} ({} by {})'.format(preview_url, mapname, author))
        irc.reply('{} ({})'.format(preview_url, mapname))

    preview = wrap(preview, ['text'])


Class = TagproTestMap

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
