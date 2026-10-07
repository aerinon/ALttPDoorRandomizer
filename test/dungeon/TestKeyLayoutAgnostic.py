import unittest
from types import SimpleNamespace

from source.dungeon.SmallKeyDoorShuffle import is_key_layout_agnostic


def world(mode, keyshuffle, dropshuffle='keys', pottery='keys', logic='noglitches'):
    return SimpleNamespace(mode={1: mode}, keyshuffle={1: keyshuffle}, dropshuffle={1: dropshuffle},
                           pottery={1: pottery}, logic={1: logic})


class TestKeyLayoutAgnostic(unittest.TestCase):
    """The standard escape's key layout is always checked: nothing outside it is reachable until it is done."""

    def test_wild_keys_all_shuffled(self):
        castle, eastern = SimpleNamespace(name='Hyrule Castle'), SimpleNamespace(name='Eastern Palace')
        self.assertFalse(is_key_layout_agnostic(castle, world('standard', 'wild'), 1))
        self.assertTrue(is_key_layout_agnostic(eastern, world('standard', 'wild'), 1))
        self.assertTrue(is_key_layout_agnostic(castle, world('open', 'wild'), 1))

    def test_universal_keys(self):
        castle = SimpleNamespace(name='Hyrule Castle')
        self.assertFalse(is_key_layout_agnostic(castle, world('standard', 'universal'), 1))
        self.assertTrue(is_key_layout_agnostic(castle, world('open', 'universal'), 1))

    def test_no_logic(self):
        castle = SimpleNamespace(name='Hyrule Castle')
        self.assertTrue(is_key_layout_agnostic(castle, world('standard', 'wild', logic='nologic'), 1))


if __name__ == '__main__':
    unittest.main()
