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
import json
import urllib
from operator import itemgetter


koala = 'http://tagpro-{0}.koalabeast.com'
koalaservers = ['origin', 'pi', 'centra', 'sphere', 'chord', 'diameter', 'maptest', 'sector']
jj = 'http://{0}.jukejuice.com'
jjservers = ['tangent'] # ['secant']
servers = [(server, koala.format(server)) for server in koalaservers] + [(server, jj.format(server)) for server in jjservers]

url = '{}/stats'


class TagproStats(callbacks.Plugin):
    """This plugin shows stats about current TagPro games.
    Use the "online" command to create a new game."""
    threaded = True

    @staticmethod
    def format_server(server, players, games):
        return '{server}: {players} player{plural_players} in {games} game{plural_games}'.format(server=ircutils.bold(server), players=players, games=games, plural_players='' if players == 1 else 's', plural_games='' if games == 1 else 's')

    def online(self, irc, msg, args):
        """takes no arguments

        Shows stats for current TagPro games.
        """

        stats = []
        for (server, host) in servers:
            statsurl = url.format(host)
            try:
                j = urllib.urlopen(statsurl)
                s = json.load(j)
            except Exception as e:
                s = {'players': '?', 'games': '?'}
            stats.append((server, s['players'], s['games']))

        totals = [sum(x for x in xs if x != '?') for xs in zip(*stats)[1:3]]
        totalmsg = self.format_server('total', *totals)
        statsmsg = ' | '.join(self.format_server(*s) for s in sorted(stats, key=itemgetter(1), reverse=True))
        msg = '[{}] {}'.format(totalmsg, statsmsg)
        irc.reply(msg)
    online = wrap(online)


Class = TagproStats


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
