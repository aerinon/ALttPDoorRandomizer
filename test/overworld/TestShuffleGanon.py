import logging
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestShuffleGanon(unittest.TestCase):
    """With Ganon's Tower and the Pyramid Hole left out of the shuffle, the Pyramid Hole keeps its vanilla drop."""

    def setUp(self):
        self.original = Main.link_entrances_new

    def tearDown(self):
        Main.link_entrances_new = self.original

    def test_pyramid_hole_stays_vanilla(self):
        # shuffle_ganon is a per-player dict; testing the dict itself was always truthy, so the hole was shuffled anyway
        original = self.original

        def stop(world, player):
            original(world, player)
            raise Stop(world)

        Main.link_entrances_new = stop
        for seed in (3, 4, 5):  # each shuffled the hole before the fix
            argv = ['--shuffle', 'full', '--shuffleganon', '--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]
            logging.disable(logging.WARNING)
            try:
                with self.assertRaises(Stop) as stopped:
                    Main.main(parse_cli(argv), seed=seed, fish=BabelFish(lang='en'))
            finally:
                logging.disable(logging.NOTSET)
            world = stopped.exception.args[0]
            with self.subTest(seed=seed):
                self.assertFalse(world.shuffle_ganon[1])
                self.assertEqual('Pyramid', world.get_entrance('Pyramid Hole', 1).connected_region.name)


if __name__ == '__main__':
    unittest.main()
