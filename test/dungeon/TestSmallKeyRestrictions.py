import logging
import unittest

import Main
from CLI import parse_cli
from Items import ItemFactory
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestSmallKeyRestrictions(unittest.TestCase):
    """Locations the experimental key logic rules out for small keys (sm_restricted) must refuse them in fill; the logic
    computed the restriction but never applied it, so fill could put a key behind the last door it opens."""

    @classmethod
    def setUpClass(cls):
        original = Main.fill_dungeons_restrictive

        def stop(world, locations):
            raise Stop(world)

        Main.fill_dungeons_restrictive = stop
        argv = ['--door_shuffle', 'crossed', '--intensity', '2', '--dungeon_shuffle_algorithm', 'experimental',
                '--key_logic_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none', '--seed', '112']
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(argv), seed=112, fish=BabelFish(lang='en'))
        except Stop as s:
            cls.world = s.args[0]
        finally:
            Main.fill_dungeons_restrictive = original
            logging.disable(logging.NOTSET)

    def test_restricted_locations_refuse_small_keys(self):
        checked = 0
        for name, logic in self.world.key_logic[1].items():
            key = ItemFactory(logic.small_key_name, 1)
            for location in logic.sm_restricted:
                checked += 1
                with self.subTest(dungeon=name, location=location.name):
                    self.assertFalse(location.item_rule(key))
        self.assertGreater(checked, 0, 'seed no longer has small key restrictions')


if __name__ == '__main__':
    unittest.main()
