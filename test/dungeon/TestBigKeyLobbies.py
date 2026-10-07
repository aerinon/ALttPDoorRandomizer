import unittest
from types import SimpleNamespace

from source.dungeon.DungeonStitcherV2 import bk_shuffle_lobbies_allowed, find_portal_candidates


def world(bigkeyshuffle=False, pottery='none'):
    return SimpleNamespace(bigkeyshuffle={1: bigkeyshuffle}, pottery={1: pottery}, door_type_mode={1: 'original'})


class TestBigKeyLobbies(unittest.TestCase):
    """A split builder may use a bk_shuffle_req lobby (e.g. Desert Tiles 2 SE), as Transitivity's valid_portal allows."""

    def test_split_builder(self):
        self.assertTrue(bk_shuffle_lobbies_allowed(SimpleNamespace(split_flag=True), world(), 1))
        self.assertFalse(bk_shuffle_lobbies_allowed(SimpleNamespace(split_flag=False), world(), 1))
        self.assertTrue(bk_shuffle_lobbies_allowed(SimpleNamespace(split_flag=False), world(bigkeyshuffle=True), 1))

    def test_candidates(self):
        tiles = SimpleNamespace(name='Desert Tiles 2 SE', blocked=False, bk_shuffle_req=True, deadEnd=False,
                                passage=True, standard_restricted=False, rupee_bow_restricted=False)
        split = bk_shuffle_lobbies_allowed(SimpleNamespace(split_flag=True), world(), 1)
        whole = bk_shuffle_lobbies_allowed(SimpleNamespace(split_flag=False), world(), 1)
        others = [SimpleNamespace(name='other', blocked=False, bk_shuffle_req=False, deadEnd=False, passage=True,
                                  standard_restricted=False, rupee_bow_restricted=False)]
        self.assertIn(tiles, find_portal_candidates([tiles] + others, False, bk_shuffle=split))
        self.assertNotIn(tiles, find_portal_candidates([tiles] + others, False, bk_shuffle=whole))


if __name__ == '__main__':
    unittest.main()
