import logging
import unittest

import Main
from CLI import parse_cli
from KeyDoorShuffle import dungeon_keys
from source.classes.BabelFish import BabelFish
from source.dungeon.KeylockCheck import find_keylock


class TestKeylockCheck(unittest.TestCase):
    """Experimental key logic gets an exhaustive keylock check after fill: every key-door opening order is searched
    with the keys where fill put them."""

    @classmethod
    def setUpClass(cls):
        argv = ['--door_shuffle', 'crossed', '--intensity', '2', '--dungeon_shuffle_algorithm', 'experimental',
                '--key_logic_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none', '--seed', '120']
        logging.disable(logging.WARNING)
        try:
            cls.world = Main.main(parse_cli(argv), seed=120, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)

    def test_generated_world_has_no_keylock(self):
        for name, layout in self.world.key_layout[1].items():
            with self.subTest(dungeon=name):
                self.assertIsNone(find_keylock(layout, self.world, 1))

    def test_keys_moved_behind_their_doors_are_caught(self):
        world, moved = self.world, 0
        for name, layout in self.world.key_layout[1].items():
            root = next(c for c in layout.key_counters.values() if c.used_keys == 0 and not c.big_key_opened)
            if not any(d in layout.flat_prop for d in root.child_doors):
                continue
            small_key = dungeon_keys[name]
            front = set(root.free_locations) | set(root.key_only_locations) | set(root.other_locations)
            keys = [l for l in world.get_locations() if l.item and l.item.name == small_key]
            behind = [l for c in layout.key_counters.values() for l in c.free_locations
                      if l not in front and l.item and not l.item.smallkey and not l.item.bigkey]
            behind = list(dict.fromkeys(behind))
            inside = {l for c in layout.key_counters.values()
                      for l in list(c.free_locations) + list(c.key_only_locations) + list(c.other_locations)}
            if any(l not in inside for l in keys) or len(behind) <= len(keys):
                continue  # keys outside the dungeon, or no room to hide them all with an item still behind
            swaps = list(zip(keys, behind))
            for key_spot, spot in swaps:
                key_spot.item, spot.item = spot.item, key_spot.item
            try:
                with self.subTest(dungeon=name):
                    self.assertIsNotNone(find_keylock(layout, world, 1))
                moved += 1
            finally:
                for key_spot, spot in swaps:
                    key_spot.item, spot.item = spot.item, key_spot.item
        self.assertGreater(moved, 0)


if __name__ == '__main__':
    unittest.main()
