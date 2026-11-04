import logging
import tempfile
import unittest
from unittest import mock

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
from source.overworld.EntranceShuffle2 import Inverted_Bomb_Shop_Options


class Stop(Exception):
    pass


class TestInvertedBombShopPlacement(unittest.TestCase):
    """Inverted entrance shuffle puts the bomb shop only where the big bomb can reach the pyramid."""

    def bomb_shop_entrance(self, shuffle, seed):
        placed = {}
        original = Main.link_entrances_new

        def stop(world, player):
            original(world, player)
            placed['entrance'] = world.get_region('Big Bomb Shop', player).entrances[0].name
            raise Stop

        with tempfile.TemporaryDirectory() as out, mock.patch.object(Main, 'link_entrances_new', stop):
            try:
                Main.main(parse_cli(['--mode', 'inverted', '--shuffle', shuffle, '--suppress_rom', '--spoiler', 'none',
                                     '--outputpath', out, '--seed', str(seed)]), seed=seed, fish=BabelFish(lang='en'))
            except Stop:
                pass
        return placed['entrance']

    def test_bomb_shop_options(self):
        logging.disable(logging.WARNING)
        try:
            for shuffle in ('full', 'crossed', 'insanity', 'swapped'):
                for seed in range(1, 31):
                    with self.subTest(shuffle=shuffle, seed=seed):
                        self.assertIn(self.bomb_shop_entrance(shuffle, seed), Inverted_Bomb_Shop_Options)
        finally:
            logging.disable(logging.NOTSET)


if __name__ == '__main__':
    unittest.main()
