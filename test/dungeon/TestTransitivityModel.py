import unittest
from unittest import mock

import source.dungeon.DungeonGenTransitivity as transitivity
import source.dungeon.TransitivityModel as model
from test.dungeon.transitivity_harness import capture_sectors, make_builder, hard_timeout, DUNGEONS


@unittest.skipUnless(model.available(), 'clingo not installed')
class TestTransitivityModel(unittest.TestCase):
    """The model is the final say when the search reaches its budget, so its verdict must match the search's own:
    every vanilla dungeon (and the vanilla pairs that take the search longest) is solvable with a wiring the engine
    accepts, and a dungeon cut in two by removing the sector that joins it has no solution."""

    @classmethod
    def setUpClass(cls):
        cls.pools = {}
        for intensity, mode in ((3, 'open'), (3, 'standard'), (4, 'open')):
            sectors, flags = capture_sectors(intensity, mode=mode)
            grouped = {}
            for s in sectors:
                dungeon = next((r.dungeon for r in s.regions if r.dungeon), None)
                if dungeon:
                    grouped.setdefault(dungeon.name, []).append(s)
            cls.pools[(intensity, mode)] = (grouped, flags)

    def decide(self, name, sector_list, flags):
        """The verdict with the model deciding from the start, as at the budget."""
        with hard_timeout(60), mock.patch.object(transitivity, 'MODEL_BUDGET', 0):
            return transitivity.do_transitivity_check(make_builder(name), sector_list, flags)

    def test_vanilla_dungeons_are_solvable(self):
        for key in ((3, 'open'), (3, 'standard')):
            grouped, flags = self.pools[key]
            for name in DUNGEONS:
                with self.subTest(pool=key, dungeon=name):
                    self.assertTrue(self.decide(name, grouped[name], flags))

    def test_slow_vanilla_pairs_are_solvable(self):
        grouped, flags = self.pools[(4, 'open')]
        for a, b in (('Eastern Palace', 'Ice Palace'), ('Ice Palace', 'Skull Woods')):
            with self.subTest(pair=(a, b)):
                self.assertTrue(self.decide(a, grouped[a] + grouped[b], flags))

    def test_a_dungeon_cut_in_two_has_no_solution(self):
        grouped, flags = self.pools[(3, 'open')]
        for name, cut in (('Eastern Palace', 'Eastern Compass Room'), ('Palace of Darkness', 'PoD Fairy Pool')):
            with self.subTest(dungeon=name, without=cut):
                rest = [s for s in grouped[name] if s.sector_key() != cut]
                self.assertEqual(len(grouped[name]) - 1, len(rest))
                self.assertFalse(self.decide(name, rest, flags))
                with mock.patch.object(transitivity, 'MODEL_BUDGET', transitivity.ITERATION_CAP):
                    self.assertFalse(transitivity.do_transitivity_check(make_builder(name), rest, flags),
                                     'the search agrees')


if __name__ == '__main__':
    unittest.main()
