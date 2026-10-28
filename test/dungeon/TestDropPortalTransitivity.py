import unittest
from unittest import mock

import source.dungeon.DungeonGenTransitivity as transitivity
from source.dungeon.DropPortals import drop_portal_by_region, sector_drop_portals
from source.dungeon.DungeonGenTransitivity import ConstraintInfo, ConstraintType, Transitivity, do_transitivity_check
from source.dungeon.DungeonGenTransitivity import find_transitivity_solution
from test.dungeon.transitivity_harness import capture_sectors, make_builder, sectors_by_dungeon, hard_timeout


def fall_door(world, region_name):
    return world.get_door(drop_portal_by_region[region_name].fall, 1)


def skull_sectors(intensity=4):
    sectors, flags = capture_sectors(intensity)
    return sectors_by_dungeon(sectors)['Skull Woods'], flags


def portal_sector(sectors, portal_name):
    return next(s for s in sectors if any(p.name == portal_name for p in s.portals)
                or f'{portal_name} Portal' in s.region_set())


class TestDropPortalTransitivity(unittest.TestCase):
    """At intensity 4 a hole's Drop Portal is a start (or a gated start, or a free hook) for Transitivity."""

    def test_vanilla_skull_woods_is_solvable_with_its_drops(self):
        sectors, flags = skull_sectors()
        self.assertTrue(any(sector_drop_portals(s) for s in sectors), 'drop lobbies did not unlock at intensity 4')
        with hard_timeout(120):
            solution = find_transitivity_solution(make_builder('Skull Woods'), sectors, flags)
        self.assertIsNotNone(solution)
        world = sectors[0].regions[0].world
        for name in ['Skull Pot Circle Drop Portal', 'Skull Left Drop Drop Portal', 'Skull Pinball Drop Portal',
                     'Skull Back Drop Drop Portal']:
            with self.subTest(drop=name):
                self.assertIn(fall_door(world, name), solution.state.connection_map)

    def test_gated_drop_is_a_start_when_a_start_portal_opens_its_forest(self):
        # in this capture Skull 3 is a non-destination portal (a start) leading out onto the Skull Back forest
        sectors, flags = skull_sectors()
        world = sectors[0].regions[0].world
        info = ConstraintInfo(make_builder('Skull Woods'), sectors, [], flags)
        self.assertIn(fall_door(world, 'Skull Back Drop Drop Portal'), info.drop_starts)

    def test_gated_drop_depends_on_a_destination_portal_onto_its_forest(self):
        sectors, flags = skull_sectors()
        world = sectors[0].regions[0].world
        without = [s for s in sectors if s is not portal_sector(sectors, 'Skull 3')]
        info = ConstraintInfo(make_builder('Skull Woods'), without, [], flags)
        fall = fall_door(world, 'Skull Back Drop Drop Portal')
        enablers = [d for d, falls in info.dependent_lookup.items() if fall in falls]
        self.assertEqual([portal_sector(sectors, 'Skull 2 West').portals[0].door], enablers)
        self.assertNotIn(fall, info.drop_starts)
        self.assertNotIn(fall, info.free_hooks)

    def test_gated_drop_without_its_portal_is_a_free_hook(self):
        sectors, flags = skull_sectors()
        world = sectors[0].regions[0].world
        without = [s for s in sectors if s not in (portal_sector(sectors, 'Skull 2 West'), portal_sector(sectors, 'Skull 3'))]
        info = ConstraintInfo(make_builder('Skull Woods'), without, [], flags)
        self.assertIn(fall_door(world, 'Skull Back Drop Drop Portal'), info.free_hooks)

    def test_free_hook_is_never_offered_a_lone_terminal(self):
        sectors, flags = skull_sectors()
        world = sectors[0].regions[0].world
        without = [s for s in sectors if s not in (portal_sector(sectors, 'Skull 2 West'), portal_sector(sectors, 'Skull 3'))]
        info = ConstraintInfo(make_builder('Skull Woods'), without, [], flags)
        fall = fall_door(world, 'Skull Back Drop Drop Portal')
        doors = [d for s in without for d in s.outstanding_doors]
        t = Transitivity(doors, [], [])
        t.remaining_doors.remove(fall)
        t.unconnected_doors[fall] = None
        offered = [hanger for hanger, hook in t.find_connectable_doors(info) if hook == fall]
        self.assertTrue(offered, 'a free hook should be offered some terminal')
        for hanger in offered:
            with self.subTest(terminal=hanger.name):
                self.assertGreater(len(info.door_sector_map[hanger].outstanding_doors), 1)

    def test_free_hook_never_lands_where_only_one_way_doors_lead_in(self):
        # two free hooks could otherwise fill both Terminals of a sector reached by nothing else
        sectors, flags = skull_sectors()
        world = sectors[0].regions[0].world
        info = ConstraintInfo(make_builder('Skull Woods'), sectors, [], flags)
        left, pinball = world.get_door('Skull Left Drop Terminal', 1), world.get_door('Skull Pinball Terminal', 1)
        hole = world.get_door('Skull Final Drop Hole', 1)
        for others in ([pinball], [hole]):
            with self.subTest(others=[d.name for d in others]):
                info.door_sector_map[left] = mock.Mock(outstanding_doors=[left] + others)
                self.assertFalse(info.free_hook_may_land(left))
        info.door_sector_map[left] = mock.Mock(outstanding_doors=[left, world.get_door('Skull Compass Room ES', 1)])
        self.assertTrue(info.free_hook_may_land(left))


class TestLockedDrops(unittest.TestCase):
    """At intensity 3 a hole's fall stays inside its sector. Rooms reached only from the hole need the hole to be a way
    in: a start, or a dependent of a portal of this builder leading out onto the hole's region."""

    @classmethod
    def setUpClass(cls):
        cls.sectors, cls.flags = skull_sectors(intensity=3)
        cls.world = cls.sectors[0].regions[0].world
        cls.fall = fall_door(cls.world, 'Skull Back Drop Drop Portal')

    def without(self, *portal_names):
        removed = [portal_sector(self.sectors, n) for n in portal_names]
        return [s for s in self.sectors if s not in removed]

    def test_rooms_reached_only_from_the_hole_are_its_landing(self):
        back_drop = next(s for s in self.sectors if 'Skull Back Drop' in s.region_set())
        self.assertNotIn(self.fall, back_drop.outstanding_doors)
        self.assertEqual({'Skull Back Drop'}, {r.name for r in back_drop.descriptor.locked_drop_landings[self.fall]})

    def test_a_start_portal_onto_the_forest_makes_the_hole_a_start(self):
        info = ConstraintInfo(make_builder('Skull Woods'), self.sectors, [], self.flags)
        self.assertIn(self.fall, info.drop_starts)

    def test_a_destination_portal_onto_the_forest_must_be_reached(self):
        sector_list = self.without('Skull 3')
        info = ConstraintInfo(make_builder('Skull Woods'), sector_list, [], self.flags)
        enter_west = self.world.get_door('Enter Skull Woods 2 (West)', 1)
        self.assertNotIn(self.fall, info.drop_starts)
        self.assertIn([enter_west], [c.doors for c in info.constraints if c.type == ConstraintType.MustEnter])

    def leading_to_swamp(self, *portal_names):
        """Patches the given portals to lead out onto Swamp Area, as entrance shuffle can."""
        swamp = self.world.get_region('Swamp Area', 1)
        original = transitivity.portal_overworld_side
        return mock.patch.object(transitivity, 'portal_overworld_side',
                                 lambda p, w: swamp if p.name in portal_names else original(p, w))

    def test_no_way_in_leaves_the_landing_unreachable(self):
        with self.leading_to_swamp('Skull 3', 'Skull 2 West'), hard_timeout(120):
            self.assertFalse(do_transitivity_check(make_builder('Skull Woods'), self.sectors, self.flags))

    def test_a_reachable_destination_portal_lets_the_landing_be_reached(self):
        with self.leading_to_swamp('Skull 3'), hard_timeout(120):
            self.assertTrue(do_transitivity_check(make_builder('Skull Woods'), self.sectors, self.flags))


class TestLockedDropLinkedPortal(unittest.TestCase):

    def test_a_linked_portal_is_reached_by_entering_its_lobby_sector(self):
        from source.dungeon.DungeonStitcherV2 import link_portal_candidate
        sectors, flags = capture_sectors(3, seed=101)  # captures are cached: a seed no other test shares, as linking changes sectors
        skull = sectors_by_dungeon(sectors)['Skull Woods']
        world = skull[0].regions[0].world
        builder = make_builder('Skull Woods')
        builder.sectors = skull
        west = world.get_portal('Skull 2 West', 1)
        lobby = world.get_door('Skull 2 West Lobby S', 1)
        master_door_list = [d for s in skull for d in s.outstanding_doors if d.portalAble]
        link_portal_candidate(builder, lobby, [], master_door_list, west, flags)
        lobby_sector = next(s for s in skull if lobby.entrance.parent_region in s.regions)
        ordered = sorted(skull, key=lambda s: s is lobby_sector)  # the emptied portal sector also holds the portal
        info = ConstraintInfo(builder, ordered, [], flags)
        self.assertEqual(lobby_sector.outstanding_doors, info.portal_entries(west, ordered))


class TestStandardSewersDrop(unittest.TestCase):

    def test_sewers_drop_is_a_free_hook_for_the_escape_builders(self):
        sectors, flags = capture_sectors(4, mode='standard')
        hc = [s for s in sectors if any(r.dungeon is not None and r.dungeon.name == 'Hyrule Castle' for r in s.regions)]
        world = hc[0].regions[0].world
        fall = fall_door(world, 'Sewers Drop Portal')
        for name in ['Hyrule Castle Sewers', 'Hyrule Castle Dungeon']:
            with self.subTest(builder=name):
                info = ConstraintInfo(make_builder(name), hc, [], flags)
                self.assertIn(fall, info.free_hooks)
                self.assertNotIn(fall, info.drop_starts)


class TestStitcherGatedDrops(unittest.TestCase):
    """The stitcher opens a gated drop when its traversal reaches a portal leading out onto the hole's region."""

    def gated(self):
        from source.dungeon.DungeonStitcherV2 import gated_drop_portals
        sectors, flags = skull_sectors()
        world = sectors[0].regions[0].world
        builder = make_builder('Skull Woods')
        builder.sectors = sectors
        return gated_drop_portals(builder, world, 1), world

    def test_skull_back_drop_is_gated(self):
        gated, world = self.gated()
        self.assertIn(world.get_region('Skull Back Drop Drop Portal', 1), [r for r, parent in gated])

    def test_reaching_a_portal_onto_the_forest_opens_it(self):
        from source.dungeon.DungeonStitcherV2 import opened_drop_portals
        gated, world = self.gated()
        visited = {world.get_region('Skull 2 West Portal', 1)}
        self.assertEqual([world.get_region('Skull Back Drop Drop Portal', 1)], opened_drop_portals(gated, visited))

    def test_reaching_another_portal_does_not(self):
        from source.dungeon.DungeonStitcherV2 import opened_drop_portals
        gated, world = self.gated()
        self.assertEqual([], opened_drop_portals(gated, {world.get_region('Skull 1 Portal', 1)}))


if __name__ == '__main__':
    unittest.main()
