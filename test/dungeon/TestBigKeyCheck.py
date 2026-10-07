import unittest
from unittest import mock

import source.dungeon.DungeonStitcherV2 as stitcher
from source.dungeon.DungeonGenTransitivity import BigKeyCheck
from test.dungeon.transitivity_harness import DUNGEONS, capture_sectors, make_builder, sectors_by_dungeon, timed_check


class TestBigKeyCheck(unittest.TestCase):
    """Where big keys matter, the stitcher crosses no big key door until it has found a location that could hold the
    big key, so Transitivity must reject a layout that reaches no such location before a big key door."""

    def test_rejected_without_a_location_before_big_key_doors(self):
        sectors, flags = capture_sectors(3)
        grouped = sectors_by_dungeon(sectors)
        checked = 0
        for name in DUNGEONS:
            builder, sector_list = make_builder(name), grouped[name]
            if BigKeyCheck.create(builder, sector_list, flags) is None or BigKeyCheck.create(builder, sector_list, flags).special:
                continue
            checked += 1
            with self.subTest(dungeon=name):
                self.assertTrue(timed_check(builder, sector_list, flags, limit=120)[0])
                with mock.patch.object(stitcher, 'count_locations_exclude_big_chest', return_value=0):
                    self.assertFalse(timed_check(make_builder(name), sector_list, flags, limit=120)[0])
        self.assertGreater(checked, 0)

    def test_not_applied_to_split_builders(self):
        sectors, flags = capture_sectors(3)
        grouped = sectors_by_dungeon(sectors)
        split = make_builder('Eastern Palace')
        split.split_flag = True
        self.assertIsNone(BigKeyCheck.create(split, grouped['Eastern Palace'], flags))


if __name__ == '__main__':
    unittest.main()
