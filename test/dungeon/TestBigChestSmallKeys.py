import unittest
from types import SimpleNamespace

from source.dungeon.NewKeyLogic import KeySphere, NewKeyLogic


class Location:
    def __init__(self, name):
        self.name = name


def sphere(code, used_keys, locations, big_key_opened=False):
    s = KeySphere(code)
    s.key_counter = SimpleNamespace(used_keys=used_keys, big_key_opened=big_key_opened)
    s.locations = set(locations)
    return s


class TestBigChestSmallKeys(unittest.TestCase):
    """A small key in a big chest can't be taken until the big key is in hand, so the worst-case reachability must not
    count it toward opening small key doors before then."""

    def setUp(self):
        self.big_chest = Location('Dungeon - Big Chest')
        self.behind = Location('Dungeon - Behind Key Door')
        root = sphere('00', 0, [self.big_chest])
        child = sphere('01', 1, [self.big_chest, self.behind])
        root.child_sphere.append(child)
        self.logic = NewKeyLogic()
        self.logic.key_spheres[0].append(root)
        self.logic.key_spheres[1].append(child)
        self.dungeon_logic = SimpleNamespace(small_key_name='Small Key (Dungeon)')

    def reach(self, big_in_hand):
        key = (0, big_in_hand, frozenset({self.big_chest.name}), None, None)
        self.logic.calculate_reachability(key, [self.big_chest], None, self.dungeon_logic, 1)
        return self.logic.can_reach_cache[key][1]

    def test_key_in_big_chest_unusable_without_big_key(self):
        self.assertNotIn(self.behind, self.reach(big_in_hand=False))

    def test_key_in_big_chest_usable_with_big_key(self):
        self.assertIn(self.behind, self.reach(big_in_hand=True))


if __name__ == '__main__':
    unittest.main()
