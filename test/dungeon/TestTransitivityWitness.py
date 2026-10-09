import unittest

from BaseClasses import DoorType
from source.dungeon.DungeonGenerationCommon import hanger_from_door, hook_from_door
from source.dungeon.DungeonGenTransitivity import Transitivity, TransitivitySolution, find_transitivity_solution
from test.dungeon.transitivity_harness import DUNGEONS, capture_sectors, hard_timeout, make_builder, sectors_by_dungeon
from test.dungeon.transitivity_witness import check_witness

# pairs whose plans were wrong (unreachable regions) before the fixes they are named for
REGRESSION_PAIRS = {
    3: [('Eastern Palace', 'Swamp Palace'),   # crystal back-propagation ignored barriers on the way
        ('Ice Palace', 'Misery Mire'),        # same
        ('Agahnims Tower', 'Ice Palace')],    # Ice Fairy behind a Blue-gated pit
    4: [('Ganons Tower', 'Misery Mire'),      # Either carried past a Blue barrier into GT Double Switch
        ('Eastern Palace', 'Swamp Palace')],
}


def solve(sector_list, flags, name):
    with hard_timeout(120):
        return find_transitivity_solution(make_builder(name), sector_list, flags)


class TestWitnessChecker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sectors, cls.flags = capture_sectors(4)
        cls.grouped = sectors_by_dungeon(cls.sectors)

    def eastern(self):
        solution = solve(self.grouped['Eastern Palace'], self.flags, 'Eastern Palace')
        self.assertIsNotNone(solution)
        return solution

    def test_valid_solution_has_no_problems(self):
        self.assertEqual([], check_witness(self.eastern()))

    def test_incompatible_pair_is_reported(self):
        solution = self.eastern()
        cmap = solution.state.connection_map
        a = next(x for x in cmap if hanger_from_door(x) is not None and x.type == DoorType.Normal)
        c = next(x for x in cmap if x not in (a, cmap[a]) and x.type == DoorType.Normal
                 and hanger_from_door(a) != hook_from_door(x) and hanger_from_door(x) != hook_from_door(a))
        cmap[a], cmap[c] = c, a
        self.assertTrue(any('incompatible' in p for p in check_witness(solution)))

    def test_unreached_region_is_reported(self):
        solution = self.eastern()
        solution.state.connection_map.clear()
        self.assertTrue(any('unreached region' in p for p in check_witness(solution)))

    def test_primary_portal_on_a_dead_end_is_reported(self):
        solution = self.eastern()
        cmap = solution.state.connection_map
        portal = next(d for d in cmap if d.traversal_only)  # Eastern's only portal: the stitcher's primary
        cmap[portal] = self.sectors[0].regions[0].world.get_door('GT DMs Room SW', 1)  # a dead end
        self.assertIn('no portal that may be primary has a door that is not a dead end', check_witness(solution))

    def test_shared_terminal_and_leftover_are_reported(self):
        # two different groups landing on one terminal leaves another terminal without a group
        doors = {d.name: d for s in self.grouped['Tower of Hera'] for d in s.outstanding_doors}
        sources = [d for d in doors.values() if d.type == DoorType.Hole and d.group_rep is d][:2]
        terminal = next(d for d in doors.values() if d.type == DoorType.Terminal)
        state = Transitivity([], [], [])
        for source in sources:
            state.connection_map[source] = terminal
        state.connection_map[terminal] = sources[0]
        problems = check_witness(TransitivitySolution(state, None, list(doors.values())))
        self.assertTrue(any('shared by' in p for p in problems))
        self.assertTrue(any('leftover' in p for p in problems))


class TestWitnessVanilla(unittest.TestCase):

    def check(self, intensity, cases):
        sectors, flags = capture_sectors(intensity)
        grouped = sectors_by_dungeon(sectors)
        for names in cases:
            with self.subTest(intensity=intensity, case='+'.join(names)):
                solution = solve([s for n in names for s in grouped[n]], flags, names[0])
                self.assertIsNotNone(solution, 'vanilla layouts are valid')
                self.assertEqual([], check_witness(solution))

    def test_singles_intensity_3(self):
        self.check(3, [(n,) for n in DUNGEONS])

    def test_singles_intensity_4(self):
        self.check(4, [(n,) for n in DUNGEONS])

    def test_regression_pairs_intensity_3(self):
        self.check(3, REGRESSION_PAIRS[3])

    def test_regression_pairs_intensity_4(self):
        self.check(4, REGRESSION_PAIRS[4])
