import unittest
from collections import defaultdict
from types import SimpleNamespace

from BaseClasses import CrystalBarrier, DoorType
from source.dungeon.DungeonGenSectorDesc import SectorDescriptor
from source.dungeon.DungeonGenerationCommon import GenerationException


class Door:
    def __init__(self, name):
        self.name = name
        self.type = DoorType.Normal

    def __repr__(self):
        return self.name


def classify(outstanding, reach):
    """Runs SectorDescriptor.classify on hand-made reachability: entry door -> doors it reaches."""
    descriptor = object.__new__(SectorDescriptor)
    descriptor.sector = SimpleNamespace(outstanding_doors=outstanding, portals=[], r_name_set={})
    descriptor.reachability = defaultdict(list)
    for entry, reached in reach.items():
        descriptor.reachability[entry] = [(d, CrystalBarrier.Null, CrystalBarrier.Null) for d in reached]
    descriptor.state_cache = {}
    descriptor.must_enter_reqs, descriptor.special_reqs, descriptor.crystal_reqs = [], [], []
    descriptor.dead_end = descriptor.is_neutral = False
    descriptor.classify()
    return descriptor.must_enter_reqs


class TestSectorClassify(unittest.TestCase):
    """Every outstanding door needs some entry that reaches it; the entries need not be the same door."""

    def test_two_entry_groups(self):
        # Ice Palace with only warps shuffled: the top doors reach the top area, and only the lower doors reach the
        # warp. No single entry reaches everything, which used to raise.
        t1, t2, b1, b2, top, warp = (Door(n) for n in ['T1', 'T2', 'B1', 'B2', 'Top', 'Warp'])
        reqs = classify([t1, t2, b1, b2, top, warp],
                        {t1: [t1, t2, top], t2: [t1, t2, top], b1: [b1, b2, warp], b2: [b1, b2, warp]})
        self.assertEqual([(t1, t2), (b1, b2)], reqs)

    def test_single_cover_unchanged(self):
        # when one set of entries covers everything left, the requirement is that set, as before
        a, b, c, d = (Door(n) for n in 'ABCD')
        reqs = classify([a, b, c, d], {a: [a, b, c, d], b: [a, b, c, d], c: [c, d], d: [d]})
        self.assertEqual([(a, b)], reqs)

    def test_unreachable_door_raises(self):
        a, b, hole = Door('A'), Door('B'), Door('Hole')
        with self.assertRaises(GenerationException):
            classify([a, b, hole], {a: [a, b], b: [a, b]})


if __name__ == '__main__':
    unittest.main()
