import unittest
from types import SimpleNamespace

from source.dungeon.DungeonGenLocalSearch import DoorFlags
from source.dungeon.DungeonStitcherV2 import bk_shuffle_lobbies_allowed

SETTINGS = {'trap_door_mode': 'vanilla', 'door_self_loops': False, 'decoupledoors': False, 'intensity': 1,
            'mode': 'open', 'bow_mode': 'progressive', 'door_type_mode': 'original', 'bigkeyshuffle': False,
            'pottery': 'none', 'doorShuffle': 'crossed'}


class StubWorld:
    """Per-player settings, as World keeps them."""

    def __init__(self, **settings):
        self.settings = dict(SETTINGS, **settings)

    def __getattr__(self, name):
        return {1: self.settings[name]}


class TestBigKeyShuffleFlag(unittest.TestCase):
    """Shuffled big key doors let a lobby that needs the big key hold a portal, in Transitivity (bk_shuffle_flag) and
    in the stitcher alike; door_type_mode is a per-player setting."""

    def test_big_key_door_shuffle_counts(self):
        builder = SimpleNamespace(split_flag=False)
        for mode, shuffled in [('original', False), ('big', True), ('all', True), ('chaos', True)]:
            world = StubWorld(door_type_mode=mode)
            with self.subTest(door_type_mode=mode):
                self.assertEqual(shuffled, DoorFlags().from_world(world, 1).bk_shuffle_flag)
                self.assertEqual(shuffled, bool(bk_shuffle_lobbies_allowed(builder, world, 1)))


if __name__ == '__main__':
    unittest.main()
