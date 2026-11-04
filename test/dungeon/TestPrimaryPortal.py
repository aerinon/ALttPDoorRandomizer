import unittest

import RaceRandom as random

from source.dungeon.DungeonGenTransitivity import find_transitivity_solution
from source.dungeon.DungeonGenerationCommon import GenerationException
from source.dungeon.DungeonStitcherV2 import choose_primary_portal, link_portal_candidate
from test.dungeon.transitivity_harness import capture_sectors, make_builder, hard_timeout

# Hyrule Castle's builder in crossed intensity 4, seed 8, when the stitcher assigns its first portal
SEED_8_HC = [['Hyrule Castle South Portal'], ['Hyrule Castle West Portal'], ['Hyrule Castle East Portal'],
             ['Sanctuary Portal'], ['Sewers Drop Portal'],
             ['GT Firesnake Room', 'GT Firesnake Room Ledge', 'GT Warp Maze - Rail Choice'], ['TR Lava Escape'],
             ['TR Roller Room'], ['Mire Lone Warp', 'Mire Spike Barrier', 'Mire Square Rail'], ['Ice Lonely Freezor'],
             ['Ice Hookshot Balcony', 'Ice Hookshot Ledge', 'Ice Spikeball'],
             ['Ice Conveyor', 'Ice Conveyor - Crystal', 'Ice Stalfos Hint'], ['Ice Jelly Key', 'Ice Lobby'],
             ['PoD Dark Maze'], ['Eastern Attic Start'],
             ['Hera Back', 'Hera Back - Ranged Crystal', 'Hera Down Stairs Landing',
              'Hera Down Stairs Landing - Ranged Crystal', 'Hera Front', 'Hera Front - Crystal', 'Hera Lobby',
              'Hera Lobby - Crystal', 'Hera Up Stairs Landing', 'Hera Up Stairs Landing - Ranged Crystal'],
             ['GT Warp Maze - Main Rails'],
             ['Swamp Basement Shallows', 'Swamp Drain Left', 'Swamp Drain Right', 'Swamp Flooded Room',
              'Swamp Flooded Spot'],
             ['Desert Map Room', 'Desert North Hall']]


class TestPrimaryPortal(unittest.TestCase):
    """The stitcher gives its primary portal, picked from the portals that may be primary, a door that is not a dead
    end; the other portals may take dead ends."""

    @classmethod
    def setUpClass(cls):
        cls.sectors, cls.flags = capture_sectors(4)
        cls.world = cls.sectors[0].regions[0].world

    def solvable(self, sector_list, pins=None):
        with hard_timeout(120):
            return find_transitivity_solution(make_builder('Hyrule Castle'), sector_list, self.flags, pins) is not None

    def by_key(self, keys):
        by_key = {s.sector_key(): s for s in self.sectors}
        return [by_key[k] for k in keys]

    def test_some_portal_that_may_be_primary_needs_a_door_that_is_not_a_dead_end(self):
        self.assertFalse(self.solvable(self.by_key(['Hyrule Castle South Portal', 'GT DMs Room'])))
        self.assertFalse(self.solvable(self.by_key(['Hyrule Castle South Portal', 'Hyrule Castle West Portal',
                                                    'GT DMs Room', 'GT Petting Zoo'])))

    def test_the_other_portals_may_take_dead_ends(self):
        self.assertTrue(self.solvable(self.by_key(['Hyrule Castle South Portal', 'Hyrule Castle West Portal',
                                                   'GT DMs Room', 'Eastern Boss'])))

    def test_a_linked_primary_lets_the_remaining_portals_take_dead_ends(self):
        sectors, flags = capture_sectors(4, seed=101)  # captures are cached: a seed no other test shares, as linking changes sectors
        by_key = {s.sector_key(): s for s in sectors}
        builder = make_builder('Hyrule Castle')
        builder.sectors = [by_key[k] for k in ['Hyrule Castle South Portal', 'Hyrule Castle West Portal',
                                                 'GT DMs Room', 'Eastern Boss']]
        world = sectors[0].regions[0].world
        south = next(p for s in builder.sectors for p in s.portals if p.name == 'Hyrule Castle South')
        master_door_list = [d for s in builder.sectors for d in s.outstanding_doors if d.portalAble]
        link_portal_candidate(builder, world.get_door('Eastern Boss SE', 1), [], master_door_list, south, flags)
        with hard_timeout(120):
            self.assertIsNotNone(find_transitivity_solution(
                builder, builder.sectors, flags, [(world.get_door('GT DMs Room SW', 1), world.get_door('Enter HC (West)', 1))]))

    def test_pinning_a_portal_from_the_plan_keeps_the_set_solvable(self):
        by_regions = {frozenset(r.name for r in s.regions): s for s in self.sectors}
        chosen = [by_regions[frozenset(regions)] for regions in SEED_8_HC]
        door = lambda name: self.world.get_door(name, 1)
        lava_escape = door('TR Lava Escape SE')
        lava_escape.portalAble = False  # LocalSearch's per-seed portal choice in seed 8
        try:
            self.assertTrue(self.solvable(chosen))
            self.assertTrue(self.solvable(chosen, [(door('Hera Lobby S'), door('Enter HC (East)'))]))
        finally:
            lava_escape.portalAble = True


class TestChoosePrimaryPortal(unittest.TestCase):
    """The stitcher tries the portals that may be primary in random order and keeps the first it can assign."""

    def test_falls_through_to_a_portal_that_can_be_assigned(self):
        for seed in range(10):
            random.seed(seed)
            tried = []
            chosen = choose_primary_portal(['a', 'b', 'c'], lambda p: tried.append(p) or p == 'c', 'Some Dungeon')
            self.assertEqual('c', chosen)
            self.assertEqual(sorted(tried), sorted(set(tried)))  # none tried twice

    def test_raises_when_no_portal_can_be_assigned(self):
        with self.assertRaises(GenerationException):
            choose_primary_portal(['a', 'b'], lambda p: False, 'Some Dungeon')


if __name__ == '__main__':
    unittest.main()
