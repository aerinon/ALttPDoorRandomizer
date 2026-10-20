import logging
import unittest

import Main
from CLI import parse_cli
from KeyDoorShuffle import dungeon_bigs, dungeon_keys
from source.classes.BabelFish import BabelFish


class TestFastKeyLogic(unittest.TestCase):
    """With more than 8 key doors the experimental key logic places enough small keys before any key door to open them
    all. A spot that opens up only through a big key door counts as before them only when the big key is there too."""

    @classmethod
    def setUpClass(cls):
        argv = ['--door_shuffle', 'crossed', '--intensity', '3', '--door_type_mode', 'all',
                '--door_type_distribution', 'chaos', '--keydropshuffle', '--pottery', 'keys',
                '--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental',
                '--suppress_rom', '--spoiler', 'none', '--seed', '6']
        logging.disable(logging.WARNING)
        try:
            cls.world = Main.main(parse_cli(argv), seed=6, fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)

    def assert_small_keys_before_key_doors(self, world):
        checked = 0
        for name, logic in world.key_logic[1].items():
            if not logic.new_logic or not logic.new_logic.fast_logic:
                continue
            layout = world.key_layout[1][name]
            root = next(c for c in layout.key_counters.values() if c.used_keys == 0 and not c.big_key_opened)
            front = set(root.free_locations) | set(root.key_only_locations) | set(root.other_locations)
            big_key_front = any(l.item and l.item.name == dungeon_bigs[name] for l in front)
            if big_key_front:
                bk_root = next((c for c in layout.key_counters.values() if c.used_keys == 0 and c.big_key_opened), None)
                if bk_root:
                    front |= set(bk_root.free_locations) | set(bk_root.key_only_locations)
            keys_front = sum(1 for l in front if l.item and l.item.name == dungeon_keys[name])
            checked += 1
            with self.subTest(dungeon=name):
                self.assertGreaterEqual(keys_front, len(layout.proposal))  # spare keys may go anywhere
        self.assertGreater(checked, 0, 'seed no longer has a dungeon on the fast logic')

    def test_small_keys_before_key_doors(self):
        self.assert_small_keys_before_key_doors(self.world)

    def test_key_drops_behind_a_big_key_door_are_not_before_key_doors(self):
        # crossed, Skull Woods with 9 and 11 key doors: key drops sat behind a big key door while the big key went behind
        # small key doors; the layout picker counted them before any key door as if the big key were already in hand
        for seed, args in [(129025593, ['--door_shuffle', 'crossed', '--intensity', '1', '--shuffle', 'lean']),
                           (958163247, ['--door_shuffle', 'crossed', '--intensity', '3', '--shuffle', 'crossed',
                                        '--mode', 'inverted'])]:
            argv = args + ['--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental',
                           '--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]
            logging.disable(logging.WARNING)
            try:
                world = Main.main(parse_cli(argv), seed=seed, fish=BabelFish(lang='en'))
            finally:
                logging.disable(logging.NOTSET)
            with self.subTest(seed=seed):
                self.assert_small_keys_before_key_doors(world)

if __name__ == '__main__':
    unittest.main()
