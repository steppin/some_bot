###
# Copyright (c) 2013, ylambda
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
import sqlite3


class TagproPug(callbacks.Plugin):
    """"Pick-Up-Game plugin"""
    pass

    def __init__(self, irc):
        self.__parent = super(TagproPug, self)
        self.__parent.__init__(irc)
        self.conn = sqlite3.connect("pug.db")
        self.cur = self.conn.cursor()
        self.cur.execute('CREATE TABLE IF NOT EXISTS pug (hostmask varchar(255));')
        self.conn.commit()

    def die(self):
        self.cur.close()
        self.conn.close()

    def pug(self, irc, msg, args, channel):
        """<channel>

        Tell users who have `!optin` about a PUG"""

        hostmask = irc.state.nickToHostmask(msg.nick)
        self.cur.execute("SELECT hostmask FROM pug WHERE hostmask = ?;", (hostmask,))

        if not self.cur.fetchone():
            return irc.reply('You must be !optin to use !pug')

        user_masks = []
        for user in irc.state.channels[channel].users:
            user_masks.append((user, irc.state.nickToHostmask(user)))

        users = self.GetUsers(user_masks)

        if users:
            irc.reply(', '.join(users))
    pug = wrap(pug, ['inChannel'])

    def optin(self, irc, msg, args):
        """no arguments required

        Get notified of a !pug"""

        hostmask = irc.state.nickToHostmask(msg.nick)
        self.cur.execute("SELECT hostmask FROM pug WHERE hostmask = ?;", (hostmask,))
        if self.cur.fetchone():
            return irc.reply('I remember your last !optin')
        else:
            self.cur.execute("INSERT INTO pug (hostmask) VALUES (?);", (hostmask,))
            self.conn.commit()
            return irc.replySuccess()
    optin = wrap(optin)

    def optout(self, irc, msg, args):
        """no arguments required

        Stop !pug notifications"""

        hostmask = irc.state.nickToHostmask(msg.nick)
        self.cur.execute("SELECT hostmask FROM pug WHERE hostmask = ?;", (hostmask,))

        if not self.cur.fetchone():
            return
        else:
            self.cur.execute("DELETE FROM pug WHERE hostmask = ?;", (hostmask,))
            self.conn.commit()
            return irc.replySuccess()
    optout = wrap(optout)

    def GetUsers(self, user_masks):
        """ Filter through database and online users"""

        hostmasks = map(lambda x: x[1], user_masks)
        self.cur.execute("SELECT hostmask FROM pug")

        results = map(lambda x: x[0], self.cur.fetchall())
        online_masks = set(hostmasks).intersection(set(results))
        user_masks = filter(lambda x: x[1] in online_masks, user_masks)
        online_users = map(lambda x: x[0], user_masks)

        return online_users

Class = TagproPug


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
