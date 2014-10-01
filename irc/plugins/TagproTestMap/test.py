# These tests except a test database to be setup that include a map
# named "Colors".

from supybot.test import *
import psycopg2

TagproTestMap = plugin.loadPluginModule('TagproTestMap')
TestDB = 'dbname=somebot_test'

class TagproTestMapDbTestCase(SupyTestCase):
    def setUp(self):
        SupyTestCase.setUp(self)
        self.db = TagproTestMap.plugin.TagproTestMapDb(TestDB)

    def test_get_all_map_names(self):
        all_maps = self.db.get_all_map_names()
        self.assertIsInstance(all_maps, list)
        for map_ in all_maps:
            self.assertIsInstance(map_, str)
        self.assertIn('Colors', all_maps)

    def test_search_map_names(self):
        all_maps = self.db.search_map_names('colors')
        self.assertIsInstance(all_maps, list)
        self.assertIsInstance(all_maps[0], str)

    def test_get_best_map(self):
        best_map = self.db.get_best_map('colors')
        self.assertIsInstance(best_map, tuple)
        self.assertEqual(len(best_map), 2)

    def test_fuzzy_search(self):
        map_results = self.db.fuzzy_search('colors')
        self.assertIsInstance(map_results, list)
        self.assertIsInstance(map_results[0], str)


# TODO: test actual map testing with a mock of some sort
class TagproTestMapTestCase(PluginTestCase):
    plugins = ('TagproTestMap',)
    config = {'supybot.plugins.TagproTestMap.dbName': TestDB}

    def SetUp(self):
        PluginTestCase.setUp(self)
        #= TagproTestMap.plugin.TagproTestMapDb(TestDB)

    def test_listmaps(self):
        TagproTestMap.plugin.TagproTestMap.db = TagproTestMap.plugin.TagproTestMapDb(TestDB)

        self.assertRegexp('listmaps', '(.*,)+')

    def test_preview(self):
        TagproTestMap.plugin.TagproTestMap.db = TagproTestMap.plugin.TagproTestMapDb(TestDB)

        self.assertRegexp('preview colors', 'http://maps.jukejuice.com/show/\d*')


class TagproTestMapChannelTestCase(ChannelPluginTestCase):
    plugins = ('TagproTestMap',)
    config = {'supybot.plugins.TagproTestMap.dbName': TestDB}

    def setUp(self):
        ChannelPluginTestCase.setUp(self)

    def test_listmaps(self):
        self.assertRegexp('listmaps', 'Please use a private message.*')
