import logging
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


ESCAPE_KEY_SPOTS = ['Secret Passage', 'Hyrule Castle - Boomerang Chest', 'Hyrule Castle - Map Chest',
                    "Hyrule Castle - Zelda's Chest", 'Sewers - Dark Cross']


class TestStandardEscapeUniversal(unittest.TestCase):
    """Standard, vanilla doors, universal keys: the escape has one key door more than its key drops, and the item pool
    puts a universal key in one of ESCAPE_KEY_SPOTS for it. The experimental key logic must count that key."""

    @classmethod
    def setUpClass(cls):
        argv = ['--door_shuffle', 'vanilla', '--retro', '--shuffle', 'vanilla', '--mode', 'standard',
                '--key_logic_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none', '--seed', '1']
        original = Main.fill_prizes

        def stop(world, *rest, **kwargs):
            raise Stop(world)

        Main.fill_prizes = stop
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(argv), seed=1, fish=BabelFish(lang='en'))
            raise AssertionError('generation finished without reaching the prize fill')
        except Stop as s:
            cls.world = s.args[0]
        finally:
            Main.fill_prizes = original
            logging.disable(logging.NOTSET)

    def test_escape_completes_wherever_the_universal_key_lies(self):
        world = self.world
        placed = next(world.get_location(n, 1) for n in ESCAPE_KEY_SPOTS
                      if world.get_location(n, 1).item and world.get_location(n, 1).item.name == 'Small Key (Universal)')
        key = placed.item
        for name in ESCAPE_KEY_SPOTS:
            spot = world.get_location(name, 1)
            previous = spot.item
            placed.item, spot.item = previous if spot != placed else key, key
            try:
                with self.subTest(spot=name):
                    state = world.get_all_state(keys=True)
                    self.assertTrue(world.get_location('Zelda Drop Off', 1).can_reach(state))
            finally:
                spot.item, placed.item = previous, key
