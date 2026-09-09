from source.overworld.EntranceShuffle2 import Inverted_Bomb_Shop_Options
from Rules import set_inverted_big_bomb_rules
from test.inverted.TestInverted import TestInverted


class TestInvertedBombRules(TestInverted):

    invalid_entrances = ['Desert Palace Entrance (East)', 'Spectacle Rock Cave', 'Spectacle Rock Cave (Bottom)', 'Pyramid Fairy']

    def connect_bomb_shop(self, entrance_name):
        entrance = self.world.get_entrance(entrance_name, 1)
        bomb_shop = self.world.get_region('Big Bomb Shop', 1)
        if entrance.connected_region is not None and entrance in entrance.connected_region.entrances:
            entrance.connected_region.entrances.remove(entrance)
        bomb_shop.entrances = []
        entrance.connect(bomb_shop)
        return entrance

    def disconnect(self, entrance):
        entrance.connected_region.entrances.remove(entrance)
        entrance.connected_region = None

    #TODO: Just making sure I haven't missed an entrance.  It would be good to test the rules make sense as well.
    def testInvertedBombRulesAreComplete(self):
        for entrance_name in Inverted_Bomb_Shop_Options:
            with self.subTest(entrance=entrance_name):
                entrance = self.connect_bomb_shop(entrance_name)
                set_inverted_big_bomb_rules(self.world, 1)
                self.disconnect(entrance)

    def testInvalidEntrancesAreNotUsed(self):
        for invalid_entrance in self.invalid_entrances:
            self.assertNotIn(invalid_entrance, Inverted_Bomb_Shop_Options)

    def testInvalidEntrances(self):
        for entrance_name in self.invalid_entrances[:3]:
            with self.subTest(entrance=entrance_name):
                entrance = self.connect_bomb_shop(entrance_name)
                with self.assertRaises(Exception):
                    set_inverted_big_bomb_rules(self.world, 1)
                self.disconnect(entrance)
