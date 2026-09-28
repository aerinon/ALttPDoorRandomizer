import logging
import unittest

import Main
from BaseClasses import RegionType
from CLI import parse_cli
from source.classes.BabelFish import BabelFish

SEEDS = range(1, 13)


class _AfterEntranceShuffle(Exception):
    pass


def hyrule_castle_world(shuffle, mode, doors, seed):
    """The world Hyrule Castle's south exit leads to, right after entrance shuffle."""
    original = Main.link_entrances_new

    def stop_after(world, player):
        original(world, player)
        raise _AfterEntranceShuffle(world)

    argv = ['--shuffle', shuffle, '--mode', mode, '--door_shuffle', doors, '--suppress_rom', '--spoiler', 'none',
            '--seed', str(seed)] + (['--intensity', '1'] if doors != 'vanilla' else [])
    Main.link_entrances_new = stop_after
    logging.disable(logging.WARNING)
    try:
        Main.main(parse_cli(argv), seed=seed, fish=BabelFish(lang='en'))
    except _AfterEntranceShuffle as stop:
        world = stop.args[0]
        return world.get_entrance('Hyrule Castle Exit (South)', 1).connected_region.type
    finally:
        Main.link_entrances_new = original
        logging.disable(logging.NOTSET)
    raise AssertionError('entrance shuffle did not run')


class TestHyruleCastlePlacement(unittest.TestCase):
    """Hyrule Castle may take a dark world dungeon slot only without door shuffle, and only when Sanctuary, kept in
    Hyrule Castle's world by the linked drop shuffle, still has a drop spot there."""

    def worlds(self, shuffle, mode, doors):
        return {hyrule_castle_world(shuffle, mode, doors, seed) for seed in SEEDS}

    def test_inverted_simple_keeps_hyrule_castle_in_the_light_world(self):
        # inverted has no dark world linked drop for Sanctuary (its Pyramid drop is at Hyrule Castle)
        self.assertEqual({RegionType.LightWorld}, self.worlds('simple', 'inverted', 'vanilla'))

    def test_inverted_simple_seed_that_had_no_sanctuary_spot(self):
        # formerly StopIteration in do_holes_and_linked_drops
        self.assertEqual(RegionType.LightWorld, hyrule_castle_world('simple', 'inverted', 'basic', 547780107))

    def test_door_shuffle_keeps_hyrule_castle_in_the_light_world(self):
        self.assertEqual({RegionType.LightWorld}, self.worlds('simple', 'open', 'basic'))

    def test_open_simple_without_door_shuffle_may_use_the_dark_world(self):
        # the dark world has the Pyramid drop for Sanctuary
        self.assertIn(RegionType.DarkWorld, self.worlds('simple', 'open', 'vanilla'))

    def test_vanilla_holes_do_not_restrict_hyrule_castle(self):
        # dungeonssimple leaves the drops vanilla, so Sanctuary needs no drop spot in Hyrule Castle's world
        self.assertIn(RegionType.DarkWorld, self.worlds('dungeonssimple', 'inverted', 'vanilla'))


if __name__ == '__main__':
    unittest.main()
