import random
import unittest

from source.dungeon.DropPortals import sector_drop_portals
from source.dungeon.DungeonGenTransitivity import ConstraintInfo, find_transitivity_solution
from test.dungeon.transitivity_harness import DUNGEONS, capture_sectors, hard_timeout, make_builder, sectors_by_dungeon
from test.dungeon.transitivity_oracle import crystal_free, oracle_solvable, pairable
from test.dungeon.transitivity_witness import check_witness

CASES = 300


def differential(intensity, seed=20260923, cases=CASES):
    """Random small crossed-shaped sets: one start portal sector plus 2-5 crystal-free, non-neutral sectors, whose
    doors can all be paired by type (LocalSearch only calls Transitivity on sets that pass Balance)."""
    sectors, flags = capture_sectors(intensity)
    grouped = sectors_by_dungeon(sectors)
    portals = {n: [s for s in grouped[n] if s.portals and any(not p.destination for p in s.portals)] for n in DUNGEONS}
    pool = [s for s in sectors if not s.portals and s.outstanding_doors and crystal_free(s)
            and not s.descriptor.is_neutral
            and not sector_drop_portals(s)]  # a hole's Drop Portal stays with its owning dungeon
    rng = random.Random(seed)
    disagreements, bad_witness, skipped, verdicts = [], [], 0, {True: 0, False: 0}
    sampled = 0
    while sampled < cases:
        name = rng.choice([n for n in DUNGEONS if portals[n]])
        chosen = [rng.choice(portals[name])] + rng.sample(pool, rng.randint(2, 5))
        if not pairable([d for s in chosen for d in s.outstanding_doors]):
            continue
        sampled += 1
        expected = oracle_solvable(chosen, ConstraintInfo(make_builder(name), chosen, [], flags))
        if expected is None:
            skipped += 1
            continue
        with hard_timeout(60):
            solution = find_transitivity_solution(make_builder(name), chosen, flags)
        actual = solution is not None
        verdicts[expected] += 1
        keys = sorted(s.sector_key() for s in chosen)
        if actual != expected:
            disagreements.append((name, expected, actual, keys))
        if solution is not None:
            bad_witness.extend((name, p, keys) for p in check_witness(solution))
    return disagreements, bad_witness, skipped, verdicts


FALSE_NEGATIVE_BUDGET = 0.03  # pruning is heuristic; a wrong False only narrows randomness, a wrong True is fatal


class TestTransitivityOracle(unittest.TestCase):

    def run_differential(self, intensity):
        disagreements, bad_witness, skipped, verdicts = differential(intensity)
        self.assertLess(skipped, CASES // 4, 'oracle budget too small for these case sizes')
        self.assertGreater(verdicts[True], 0, 'no solvable cases sampled; the comparison says nothing about Trues')
        self.assertGreater(verdicts[False], 0, 'no unsolvable cases sampled; the comparison says nothing about Falses')
        self.assertEqual([], bad_witness)
        false_positives = [d for d in disagreements if not d[1]]
        false_negatives = [d for d in disagreements if d[1]]
        self.assertEqual([], false_positives)
        self.assertLessEqual(len(false_negatives), FALSE_NEGATIVE_BUDGET * verdicts[True], false_negatives)

    def test_oracle_requires_a_location_before_big_key_doors(self):
        # 72 complete layouts reach every door, but none has a location for the big key before its big key door
        sectors, flags = capture_sectors(3)
        by_key = {s.sector_key(): s for s in sectors}
        chosen = [by_key[k] for k in ['Hyrule Castle South Portal', 'Mire Cross', 'Thieves BK Corner',
                                      'Thieves Big Chest Room']]
        info = ConstraintInfo(make_builder('Hyrule Castle'), chosen, [], flags)
        self.assertIsNotNone(info.big_key)
        self.assertFalse(oracle_solvable(chosen, info))

    def test_small_sets_intensity_3(self):
        self.run_differential(3)

    def test_small_sets_intensity_4(self):
        self.run_differential(4)
