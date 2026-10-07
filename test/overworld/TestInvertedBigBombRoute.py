import unittest
from types import SimpleNamespace

from BaseClasses import Entrance
from Rules import set_inverted_big_bomb_rules


class TestInvertedBigBombRoute(unittest.TestCase):
    """Every normal light world entrance the bomb shop can land on has a route to the pyramid in inverted."""

    def world_with_bomb_shop_at(self, entrance_name):
        fairy = Entrance(1, 'Pyramid Fairy')
        shop = SimpleNamespace(entrances=[SimpleNamespace(name=entrance_name)])
        return SimpleNamespace(get_region=lambda name, player: shop, get_entrance=lambda name, player: fairy), fairy

    def test_tavern_north(self):
        world, fairy = self.world_with_bomb_shop_at('Tavern North')
        set_inverted_big_bomb_rules(world, 1)

    def test_unknown_entrance_still_raises(self):
        world, fairy = self.world_with_bomb_shop_at('Nowhere In Particular')
        with self.assertRaises(Exception):
            set_inverted_big_bomb_rules(world, 1)


if __name__ == '__main__':
    unittest.main()
