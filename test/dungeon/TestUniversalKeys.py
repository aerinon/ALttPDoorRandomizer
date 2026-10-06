import logging
import unittest

import Main
from BaseClasses import CollectionState
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestUniversalKeys(unittest.TestCase):
    """With universal keys and the experimental key logic, key doors need a key shop, except Hyrule Castle's doors in
    standard, which use the escape's own keys."""

    def setUp(self):
        self.original = Main.fill_prizes

    def tearDown(self):
        Main.fill_prizes = self.original

    def generate_until_prizes(self, mode, seed):
        def stop(world, attempts=15):
            raise Stop(world)

        Main.fill_prizes = stop
        argv = ['--door_shuffle', 'basic', '--intensity', '1', '--dungeon_shuffle_algorithm', 'experimental',
                '--key_logic_algorithm', 'experimental', '--retro', '--shuffle', 'vanilla', '--mode', mode,
                '--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]
        logging.disable(logging.WARNING)
        try:
            with self.assertRaises(Stop) as stopped:
                Main.main(parse_cli(argv), seed=seed, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)
        return stopped.exception.args[0]

    def test_standard_prizes_reachable_with_all_items(self):
        # each dungeon's key logic used to require its own small key, which universal keys never provide
        world = self.generate_until_prizes('standard', 192564694)
        state = world.get_all_state(keys=True)
        for loc in world.get_locations():
            if loc.name.endswith(' - Prize'):
                with self.subTest(location=loc.name):
                    self.assertTrue(state.can_reach(loc, None, 1))

    def test_escape_key_doors_match_key_drops(self):
        # universal keys aren't logical items, so a key door beyond the escape's key drops could never be opened
        world = self.generate_until_prizes('standard', 192564694)
        builder = world.dungeon_layouts[1]['Hyrule Castle']
        self.assertEqual(builder.key_drop_cnt, len(builder.key_door_proposal))
        state = world.get_all_state(keys=True)
        for region in builder.master_sector.regions:
            with self.subTest(region=region.name):
                self.assertTrue(state.can_reach(region, None, 1))

    def test_key_doors_need_a_key_shop(self):
        # the shop rule used to be skipped on the experimental key logic path
        for mode in ('open', 'standard'):
            world = self.generate_until_prizes(mode, 1)
            state = world.get_all_state(keys=True)
            state.can_buy_unlimited = lambda item, player: False
            for d_name, layout in world.key_layout[1].items():
                if mode == 'standard' and d_name == 'Hyrule Castle':
                    continue
                for door in layout.flat_prop:
                    with self.subTest(mode=mode, door=door.name):
                        self.assertFalse(door.entrance.access_rule(state))


if __name__ == '__main__':
    unittest.main()
