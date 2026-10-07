import itertools
import unittest
from collections import Counter

from BaseClasses import DoorType
from source.dungeon.DungeonGenerationCommon import GenerationException
from test.dungeon.transitivity_harness import DUNGEONS, capture_sectors, make_builder, sectors_by_dungeon, timed_check

TIME_BUDGET = 2.0  # seconds; matches the slow-call warning threshold in DungeonGenTransitivity
ONE_WAY = (DoorType.Hole, DoorType.Warp)


class TestTerminalGroups(unittest.TestCase):

    def test_groups_and_terminals_are_one_to_one(self):
        sectors, flags = capture_sectors(4)
        grouped = sectors_by_dungeon(sectors)
        for name in DUNGEONS:
            doors = [d for s in grouped[name] for d in s.outstanding_doors]
            groups = {d.group for d in doors if d.type in ONE_WAY}
            terminals = Counter(d.name for d in doors if d.type == DoorType.Terminal)
            with self.subTest(dungeon=name):
                self.assertNotIn(None, groups, 'every Hole/Warp must belong to a group')
                self.assertEqual([], [t for t, n in terminals.items() if n > 1], 'duplicate terminal names')
                self.assertEqual(set(terminals), groups)

    def test_every_pit_source_is_in_a_sector(self):
        # a source whose region is missing from the dungeon's region list is never shuffled and is left unconnected
        sectors, flags = capture_sectors(4)
        world = sectors[0].regions[0].world
        in_sectors = {d for s in sectors for d in s.outstanding_doors}
        sources = [d for d in world.doors if d.type in ONE_WAY and d.group is not None]
        # collapsing keeps only each group's representative as an outstanding door
        self.assertEqual([], sorted(d.name for d in sources
                                    if d.dest is None and d not in in_sectors and d.group_rep not in in_sectors))

    def test_no_neutral_sector_holds_pits(self):
        # Transitivity drops neutral sectors and splices them in later; that is unverified for one-way pits
        sectors, flags = capture_sectors(4)
        for s in sectors:
            if s.descriptor.is_neutral:
                with self.subTest(sector=s.sector_key()):
                    self.assertFalse(any(d.type in ONE_WAY + (DoorType.Terminal,) for d in s.outstanding_doors))


def vanilla_cases(intensity, pairs):
    sectors, flags = capture_sectors(intensity)
    grouped = sectors_by_dungeon(sectors)
    names = itertools.combinations(DUNGEONS, 2) if pairs else [(n,) for n in DUNGEONS]
    for case in names:
        yield '+'.join(case), make_builder(case[0]), [s for n in case for s in grouped[n]], flags


class TestTransitivityVanilla(unittest.TestCase):
    """Vanilla layouts are valid, so every vanilla dungeon, and every union of two, must be transitive."""

    def check(self, intensity, pairs):
        for label, builder, sector_list, flags in vanilla_cases(intensity, pairs):
            with self.subTest(case=label, intensity=intensity):
                verdict, elapsed = timed_check(builder, sector_list, flags, limit=120)
                self.assertTrue(verdict, f'vanilla {label} must be transitive')

    def test_singles_intensity_3(self):
        self.check(3, pairs=False)

    def test_singles_intensity_4(self):
        self.check(4, pairs=False)

    def test_pairs_intensity_3(self):
        self.check(3, pairs=True)

    def test_pairs_intensity_4(self):
        self.check(4, pairs=True)


class TestTransitivitySearchBudget(unittest.TestCase):
    """Every vanilla single and pair should be decided within TIME_BUDGET."""

    @unittest.expectedFailure  # search effort: a few pairs still take over 2s at intensity 4 (plan: Open work, search effort)
    def test_vanilla_within_budget(self):
        slow = []
        for intensity in (3, 4):
            for pairs in (False, True):
                for label, builder, sector_list, flags in vanilla_cases(intensity, pairs):
                    try:
                        verdict, elapsed = timed_check(builder, sector_list, flags, limit=120)
                    except GenerationException:
                        slow.append((intensity, label, 'cap'))
                        continue
                    if elapsed >= TIME_BUDGET:
                        slow.append((intensity, label, round(elapsed, 1)))
        self.assertEqual([], slow)
