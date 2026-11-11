import unittest
from unittest import mock

import source.dungeon.DungeonGenTransitivity as transitivity
from source.dungeon.DungeonGenTransitivity import find_transitivity_solution
from test.dungeon.transitivity_harness import capture_sectors, make_builder, hard_timeout

SECTORS = ['Hyrule Castle South Portal', 'Hyrule Castle West Portal', 'Sewers Drop Portal', 'Hyrule Castle Lobby',
           'Hyrule Castle West Lobby', 'Hyrule Dungeon Armory Boomerang']


class TestPinnedPortalRules(unittest.TestCase):
    """A pin is held to the pairing rules unpinned connections follow. In standard, Hyrule Castle West is a
    destination portal: its lobby is left through, so it must be reachable from inside the dungeon, and no other door
    of its sector reaches Sewers Secret Room Key Door S."""

    @classmethod
    def setUpClass(cls):
        sectors, cls.flags = capture_sectors(3, seed=1, mode='standard')
        by_key = {s.sector_key(): s for s in sectors}
        cls.sectors = [by_key[k] for k in SECTORS]
        cls.world = sectors[0].regions[0].world

    def door(self, name):
        return self.world.get_door(name, 1)

    def solvable(self, pins):
        with hard_timeout(60):
            return find_transitivity_solution(make_builder('Hyrule Castle'), self.sectors, self.flags, pins) is not None

    def test_the_set_is_solvable_unpinned(self):
        self.assertTrue(self.solvable([]))

    def test_a_destination_portal_pinned_to_a_door_nothing_reaches_is_refuted_without_search(self):
        pin = [(self.door('Sewers Secret Room Key Door S'), self.door('Enter HC (West)'))]
        # no search budget and no model to fall back on: any search at all fails the check with an exception
        with mock.patch.object(transitivity, 'ITERATION_CAP', 0), \
                mock.patch.object(transitivity.transitivity_model, 'available', lambda: False):
            self.assertFalse(self.solvable(pin))


if __name__ == '__main__':
    unittest.main()
