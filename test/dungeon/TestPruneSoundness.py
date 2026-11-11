import random
import unittest
from collections import defaultdict

from source.dungeon.DungeonGenTransitivity import Transitivity, find_transitivity_solution
from test.dungeon.transitivity_harness import capture_sectors, make_builder, hard_timeout, DUNGEONS

ORDERS = 20


class TestPruneSoundness(unittest.TestCase):
    """A prune may only reject a state no completion extends. Each vanilla dungeon is solved, then its wiring is
    connected again in random orders: no prefix of a valid wiring may be pruned, and every order ends complete.
    The crystal order rule (`color_access_missed`) restricts orders on purpose, so it is left out."""

    @classmethod
    def setUpClass(cls):
        cls.pools = {}
        for mode in ('open', 'standard'):
            sectors, flags = capture_sectors(3, seed=1, mode=mode)
            grouped = defaultdict(list)
            for s in sectors:
                dungeon = next((r.dungeon for r in s.regions if r.dungeon), None)
                if dungeon:
                    grouped[dungeon.name].append(s)
            cls.pools[mode] = (grouped, flags)

    def replay_all(self, mode):
        grouped, flags = self.pools[mode]
        for name in DUNGEONS:
            with self.subTest(mode=mode, dungeon=name):
                starts = []
                original = Transitivity.find_connectable_doors

                def record(t, c_info, init=True):
                    if init:
                        starts.append((t.copy(), c_info))
                    return original(t, c_info, init)

                Transitivity.find_connectable_doors = record
                try:
                    with hard_timeout(120):
                        solution = find_transitivity_solution(make_builder(name), grouped[name], flags)
                finally:
                    Transitivity.find_connectable_doors = original
                self.assertIsNotNone(solution, 'a vanilla dungeon is solvable')
                if solution.c_info is None:
                    continue
                t0, c_info = starts[-1]
                rng = random.Random(name)
                for _ in range(ORDERS):
                    self.assertEqual('ok', replay(t0, c_info, solution.state.connection_map, rng))

    def test_open(self):
        self.replay_all('open')

    def test_standard(self):
        self.replay_all('standard')


def now_impossible_without_order_rule(t, c_info):
    original = Transitivity.color_access_missed
    Transitivity.color_access_missed = lambda self, constraint, remaining_set: False
    try:
        return t.now_impossible(c_info, set())
    finally:
        Transitivity.color_access_missed = original


def replay(t0, c_info, wiring, rng):
    """Connects the wiring's pairs in a random reachable order; reports the first prune or a bad end."""
    pairs = {frozenset(p) for p in wiring.items() if p[0] not in t0.connection_map}
    t = t0.copy()
    while pairs:
        ready = sorted((p for p in pairs if any(d in t.unconnected_doors for d in p)),
                       key=lambda q: sorted(d.name for d in q))
        if not ready:
            return 'stuck'
        p = rng.choice(ready)
        pairs.discard(p)
        a, b = sorted(p, key=lambda d: d.name)
        hook, hanger = (a, b) if a in t.unconnected_doors and (b not in t.unconnected_doors or rng.random() < .5) else (b, a)
        t = t.connect_door((hanger, hook), c_info)
        if pairs and not t.is_complete(c_info) and now_impossible_without_order_rule(t, c_info):
            return f'pruned after {sorted(d.name for d in p)}'
    return 'ok' if t.is_complete(c_info) else 'incomplete'


if __name__ == '__main__':
    unittest.main()
