import logging
import unittest

import ItemList
import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestTakeAnyEntrance(unittest.TestCase):
    """Take-any caves are entered from the overworld door, never from a cave's own back room."""

    def setUp(self):
        self.originals = ItemList.set_up_take_anys, ItemList.random.sample

    def tearDown(self):
        ItemList.set_up_take_anys, ItemList.random.sample = self.originals

    def test_old_man_take_any_uses_the_outside_door(self):
        # Good Bee Cave also has an entrance from its back room ('Good Bee Cave Back to Front'); when that one came
        # first, the Old Man take-any connected it and door_addresses raised KeyError
        set_up, sample = self.originals
        placed = []

        def good_bee_last(population, k):
            picks = [x for x in sample(population, k) if x != 'Good Bee Cave'][:k - 1]
            return picks + ['Good Bee Cave']  # the Old Man takes the last pick

        def record(world, player, skip_adjustments=False):
            cave = world.get_region('Good Bee Cave', player)
            cave.entrances.sort(key=lambda e: e.parent_region.is_outdoors())  # the inside entrance first
            ItemList.random.sample = good_bee_last  # random is the shared module: patch only around this call
            try:
                set_up(world, player, skip_adjustments)
            finally:
                ItemList.random.sample = sample
            placed.extend(e for r in world.dynamic_regions if r.name == 'Old Man Sword Cave' for e in r.entrances)
            raise Stop()

        ItemList.set_up_take_anys = record
        argv = ['--door_shuffle', 'vanilla', '--retro', '--shuffle', 'vanilla', '--suppress_rom', '--spoiler', 'none',
                '--seed', '1']
        logging.disable(logging.WARNING)
        try:
            with self.assertRaises(Stop):
                Main.main(parse_cli(argv), seed=1, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)
        self.assertEqual(1, len(placed))
        self.assertEqual('Good Bee Cave', placed[0].name)
        self.assertTrue(placed[0].parent_region.is_outdoors())


if __name__ == '__main__':
    unittest.main()
