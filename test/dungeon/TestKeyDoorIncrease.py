import logging
import tempfile
import unittest
from unittest import mock

import DoorShuffle
import Main
import source.dungeon.SmallKeyDoorShuffle as sk
from CLI import parse_cli
from DoorShuffle import flatten_pair_list
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestKeyDoorIncrease(unittest.TestCase):
    """A failed key door increase leaves the dungeon's previous layout in place: the search may settle on a smaller
    layout, but used_doors records the last accepted one, so later door types must not land on applied key doors."""

    def test_failed_increase_keeps_the_recorded_layout(self):
        first, increases, found = {}, [], {}
        original_find, original_shuffle = sk.find_valid_combination, DoorShuffle.shuffle_small_key_doors_v2

        def settle_lower(builder, target, start_regions, world, player, drop_keys=True):
            if builder.name in first and target > first[builder.name]:
                increases.append(builder.name)  # every increase fails: the search settles one door lower
                return original_find(builder, target - 1, start_regions, world, player, drop_keys)
            first.setdefault(builder.name, target)
            return original_find(builder, target, start_regions, world, player, drop_keys)

        def stop(door_type_pools, used_doors, start_regions_map, all_custom, world, player):
            found['used'] = original_shuffle(door_type_pools, used_doors, start_regions_map, all_custom, world, player)
            found['world'] = world
            raise Stop

        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out, \
                    mock.patch.object(sk, 'find_valid_combination', settle_lower), \
                    mock.patch.object(DoorShuffle, 'shuffle_small_key_doors_v2', stop):
                try:
                    Main.main(parse_cli(['--door_shuffle', 'crossed', '--intensity', '2', '--door_type_mode', 'all',
                                         '--dungeon_shuffle_algorithm', 'experimental',
                                         '--key_logic_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none',
                                         '--outputpath', out, '--seed', '3']), seed=3, fish=BabelFish(lang='en'))
                except Stop:
                    pass
        finally:
            logging.disable(logging.NOTSET)
        self.assertTrue(increases, 'no key door increase was attempted')
        world = found['world']
        for name, builder in world.dungeon_layouts[1].items():
            applied = set(flatten_pair_list(builder.key_door_proposal or []))
            self.assertEqual([], sorted(d.name for d in applied - found['used']), name)


if __name__ == '__main__':
    unittest.main()
