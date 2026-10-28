import unittest
from unittest import mock

import source.dungeon.DungeonStitcherV2 as stitcher
from source.dungeon.DungeonGenTransitivity import ConstraintInfo
from test.dungeon.transitivity_harness import DUNGEONS, capture_sectors, make_builder, sectors_by_dungeon, timed_check


def sector_holding(sectors, region_name):
    return next(s for s in sectors if region_name in s.region_set())


def count_skull_locations(locations, world, player):
    return sum(1 for loc in locations if loc.parent_region.name.startswith('Skull'))


def count_boss_locations(locations, world, player):
    return sum(1 for loc in locations if loc.parent_region.name == 'Skull Boss')


class TestBigKeyCheck(unittest.TestCase):
    """Where big keys matter, the stitcher crosses no big key door until it has found a location that could hold the
    big key, so Transitivity must reject a layout that reaches no such location before a big key door."""

    def test_rejected_without_a_location_before_big_key_doors(self):
        sectors, flags = capture_sectors(3)
        grouped = sectors_by_dungeon(sectors)
        checked = 0
        for name in DUNGEONS:
            builder, sector_list = make_builder(name), grouped[name]
            big_key = ConstraintInfo(builder, sector_list, [], flags).big_key
            if big_key is None or big_key.special:
                continue
            checked += 1
            with self.subTest(dungeon=name):
                self.assertTrue(timed_check(builder, sector_list, flags, limit=120)[0])
                with mock.patch.object(stitcher, 'count_locations_exclude_big_chest', return_value=0):
                    self.assertFalse(timed_check(make_builder(name), sector_list, flags, limit=120)[0])
        self.assertGreater(checked, 0)

    def test_a_moved_landing_is_not_a_way_in(self):
        sectors, flags = capture_sectors(4)
        grouped = sectors_by_dungeon(sectors)
        landing = sector_holding(grouped['Skull Woods'], 'Skull Left Drop')
        big_key = ConstraintInfo(make_builder('Ice Palace'), grouped['Ice Palace'] + [landing], [], flags).big_key
        with mock.patch.object(stitcher, 'count_locations_exclude_big_chest', side_effect=count_skull_locations):
            self.assertFalse(big_key.satisfied({}))

    def test_a_drop_portal_fall_is_a_way_in(self):
        sectors, flags = capture_sectors(4)
        grouped = sectors_by_dungeon(sectors)
        drop = sector_holding(grouped['Skull Woods'], 'Skull Pinball Drop Portal')
        boss = sector_holding(grouped['Skull Woods'], 'Skull Boss')
        big_key = ConstraintInfo(make_builder('Ice Palace'), grouped['Ice Palace'] + [drop, boss], [], flags).big_key
        world = drop.regions[0].world
        fall, terminal = world.get_door('Skull Pinball Drop Portal Fall', 1), world.get_door('Skull Boss Terminal', 1)
        with mock.patch.object(stitcher, 'count_locations_exclude_big_chest', side_effect=count_skull_locations):
            self.assertTrue(big_key.satisfied({fall: terminal, terminal: fall}))

    def test_a_gated_fall_opens_once_its_portal_lobby_is_reached(self):
        # without Skull 3, the Skull Back Drop hole opens only from the Skull 2 West lobby (a destination portal)
        sectors, flags = capture_sectors(4)
        grouped = sectors_by_dungeon(sectors)
        skull = grouped['Skull Woods']
        extra = [sector_holding(skull, name) for name in ['Skull Back Drop Drop Portal', 'Skull Boss', 'Skull X Room',
                                                          'Skull 2 West Portal']]
        big_key = ConstraintInfo(make_builder('Ice Palace'), grouped['Ice Palace'] + extra, [], flags).big_key
        world = skull[0].regions[0].world
        door = lambda name: world.get_door(name, 1)
        fall, terminal = door('Skull Back Drop Drop Portal Fall'), door('Skull Boss Terminal')
        self.assertIn(fall, [f for f, enablers in big_key.gated_drops])
        # an Ice Palace start portal's lobby is taken to be Skull Small Hall, next to the Skull 2 West lobby
        ice_portal = big_key.portals[0].door
        links = {fall: terminal, terminal: fall, ice_portal: door('Skull Small Hall ES')}
        with mock.patch.object(stitcher, 'count_locations_exclude_big_chest', side_effect=count_boss_locations):
            self.assertFalse(big_key.satisfied(links))
            portal_in = {door('Enter Skull Woods 2 (West)'): door('Skull 2 West Lobby S'),
                         door('Skull 2 West Lobby S'): door('Enter Skull Woods 2 (West)')}
            big_key.cache.clear()
            self.assertTrue(big_key.satisfied({**links, **portal_in}))

    def test_not_applied_to_split_builders(self):
        sectors, flags = capture_sectors(3)
        grouped = sectors_by_dungeon(sectors)
        split = make_builder('Eastern Palace')
        split.split_flag = True
        self.assertIsNone(ConstraintInfo(split, grouped['Eastern Palace'], [], flags).big_key)


if __name__ == '__main__':
    unittest.main()
