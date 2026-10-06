import logging
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestVanillaKeyLogicOrder(unittest.TestCase):
    """Vanilla key logic processes every dungeon even when a delay would wait on a dungeon that waits in turn."""

    def setUp(self):
        self.original = Main.link_doors_prep

    def tearDown(self):
        Main.link_doors_prep = self.original

    def test_standard_hyrule_castle_and_agahnims_tower(self):
        # Hyrule Castle's ledge lobbies share the ledge with Agahnim's Tower, which has no origin until Hyrule Castle
        # is processed; delaying Hyrule Castle for it looped until the loop limit
        original = self.original

        def stop(world, player):
            original(world, player)
            raise Stop(world)

        Main.link_doors_prep = stop
        argv = ['--door_shuffle', 'vanilla', '--shuffle', 'vanilla', '--mode', 'standard',
                '--suppress_rom', '--spoiler', 'none', '--seed', '1']
        logging.disable(logging.WARNING)
        try:
            with self.assertRaises(Stop) as stopped:
                Main.main(parse_cli(argv), seed=1, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)
        world = stopped.exception.args[0]
        self.assertIn('Hyrule Castle', world.key_logic[1])
        self.assertIn('Agahnims Tower', world.key_logic[1])
        self.assertEqual(13, len(world.key_logic[1]))


if __name__ == '__main__':
    unittest.main()
