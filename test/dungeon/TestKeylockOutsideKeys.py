import logging
import unittest

import BaseClasses
import Main
from CLI import parse_cli
from KeyDoorShuffle import dungeon_keys
from source.classes.BabelFish import BabelFish
from source.dungeon.KeylockCheck import find_keylock


class TestKeylockOutsideKeys(unittest.TestCase):
    """A key outside its dungeon counts toward the keylock search only if the rest of the world can supply it without
    the dungeon's cut-off locations: a key behind an item that only the dungeon holds closes a cycle."""

    @classmethod
    def setUpClass(cls):
        argv = ['--door_shuffle', 'crossed', '--intensity', '2', '--keysanity', '--dungeon_shuffle_algorithm',
                'experimental', '--key_logic_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none',
                '--seed', '401']
        logging.disable(logging.WARNING)
        try:
            cls.world = Main.main(parse_cli(argv), seed=401, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)

    def hookshot_spots(self):
        """Locations outside dungeons reachable with everything but the Hookshot only through it."""
        world = self.world
        without, with_it = BaseClasses.CollectionState(world), BaseClasses.CollectionState(world)
        for item in world.itempool + [i for d in world.dungeons for i in d.all_items]:
            if item.player == 1 and item.name != 'Hookshot':
                without.collect(item, True)
                with_it.collect(item, True)
        with_it.collect(next(l.item for l in world.get_locations() if l.item and l.item.name == 'Hookshot'), True)
        return [l for l in world.get_locations() if l.parent_region.dungeon is None and l.item is not None
                and not l.item.advancement and not l.can_reach(without) and l.can_reach(with_it)]

    @staticmethod
    def swap(a, b):
        a.item, b.item = b.item, a.item

    def test_generated_world_has_no_keylock(self):
        for name, layout in self.world.key_layout[1].items():
            with self.subTest(dungeon=name):
                self.assertIsNone(find_keylock(layout, self.world, 1))

    def test_key_behind_an_item_only_the_dungeon_holds(self):
        world = self.world
        hookshot = next(l for l in world.get_locations() if l.item and l.item.name == 'Hookshot')
        targets = self.hookshot_spots()
        self.assertTrue(targets)
        caught = 0
        for name, layout in world.key_layout[1].items():
            counters = layout.key_counters
            if not counters or not layout.flat_prop:
                continue
            inside = {l for c in counters.values() for l in list(c.free_locations) + list(c.other_locations)}
            root = next(c for c in counters.values() if c.used_keys == 0 and not c.big_key_opened)
            behind = [l for c in counters.values() for l in c.free_locations
                      if l not in root.free_locations and l.item and not l.item.smallkey and not l.item.bigkey]
            keys = [l for l in world.get_locations() if l.item and l.item.name == dungeon_keys[name]
                    and l not in inside]
            if not behind or not keys:
                continue
            key_spot, target, cut_off = keys[0], targets[0], behind[-1]
            self.swap(key_spot, target)
            self.swap(hookshot, cut_off)
            try:
                if find_keylock(layout, world, 1):
                    caught += 1
            finally:
                self.swap(hookshot, cut_off)
                self.swap(key_spot, target)
        self.assertGreater(caught, 0)


if __name__ == '__main__':
    unittest.main()
