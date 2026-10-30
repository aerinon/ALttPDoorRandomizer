import unittest

from BaseClasses import CollectionState
from Items import ItemFactory
from test.TestBase import build_vanilla_world


def keys(dungeon, count):
    """Every item but the dungeon's small keys, then count of them."""
    return [f'Small Key ({dungeon})'] * count, [f'Small Key ({dungeon})']


class PitWarpLayout:
    """A vanilla dungeon whose pit or warp groups swap Terminals as intensity 4 swaps them, pinned without a seed. Each
    row (location, reachable, items, every item except) holds in the moved layout and is the other way in vanilla."""
    dungeon = None
    pit_landings = {}
    rows = []

    @classmethod
    def setUpClass(cls):
        swaps = dict(cls.pit_landings)
        swaps.update({b: a for a, b in cls.pit_landings.items()})
        cls.world = build_vanilla_world(key_logic='experimental', pit_landings=swaps)
        cls.vanilla = build_vanilla_world(key_logic='experimental')

    @staticmethod
    def reachable(world, location, items, all_except):
        state = CollectionState(world)
        for item in [i for i in world.itempool if i.name not in all_except] + ItemFactory(items, 1):
            item.advancement = True
            state.collect(item)
        return world.get_location(location, 1).can_reach(state)

    def test_every_location_is_reachable_with_everything(self):
        dungeon = next(d for d in self.world.dungeons if d.name == self.dungeon)
        unreachable = [loc.name for loc in self.world.get_locations() if loc.parent_region.dungeon == dungeon
                       and not self.reachable(self.world, loc.name, [], [])]
        self.assertEqual([], unreachable)

    def test_moved_layout(self):
        for location, access, items, all_except in self.rows:
            with self.subTest(location=location, items=items, all_except=all_except):
                self.assertEqual(access, self.reachable(self.world, location, items, all_except))

    def test_rows_differ_from_vanilla(self):
        for location, access, items, all_except in self.rows:
            with self.subTest(location=location, items=items, all_except=all_except):
                self.assertEqual(not access, self.reachable(self.vanilla, location, items, all_except))


class TestHeraPits(PitWarpLayout, unittest.TestCase):
    """The Beetles holes land on Big Chest Landing, above the big key door."""
    dungeon = 'Tower of Hera'
    pit_landings = {'Hera Big Chest Landing Terminal': 'Hera Up Stairs Landing Terminal'}
    rows = [
        ['Tower of Hera - Compass Chest', True, [], ['Big Key (Tower of Hera)']],
        ['Tower of Hera - Boss', True, [], ['Big Key (Tower of Hera)']],
        ['Tower of Hera - Prize', True, [], ['Big Key (Tower of Hera)']],
    ]


class TestPalaceOfDarknessWarps(PitWarpLayout, unittest.TestCase):
    """The Warp Room warp lands in Dark Alley beside the boss; Warp Hint, the way to the Map Chest and the Arena Ledge,
    is left to the Callback warp, which needs every key, the Lamp and the Hammer."""
    dungeon = 'Palace of Darkness'
    pit_landings = {'PoD Dark Alley Terminal': 'PoD Warp Hint Terminal'}
    rows = [
        ['Palace of Darkness - Boss', True, [], ['Hammer']],
        ['Palace of Darkness - Boss', True, [], ['Progressive Bow']],
        ['Palace of Darkness - Prize', True, [], ['Hammer']],
        ['Palace of Darkness - Map Chest', False, [], ['Lamp']],
        ['Palace of Darkness - Map Chest', False, [], ['Hammer']],
        ['Palace of Darkness - Map Chest', False, *keys('Palace of Darkness', 5)],
        ['Palace of Darkness - The Arena - Ledge', False, [], ['Lamp']],
        ['Palace of Darkness - The Arena - Ledge', False, *keys('Palace of Darkness', 5)],
    ]


class TestSwampPits(PitWarpLayout, unittest.TestCase):
    """The attic pits trade ledges; either ledge leads on, so nothing moves out of reach."""
    dungeon = 'Swamp Palace'
    pit_landings = {'Swamp Barrier Ledge Terminal': 'Swamp West Ledge Terminal'}


class TestIcePalacePits(PitWarpLayout, unittest.TestCase):
    """The Bomb Drop hole lands in Tall Hint, so the Stalfos Hint side is left to the Falling Square hole, past Spike
    Cross: both keys and the Hookshot."""
    dungeon = 'Ice Palace'
    pit_landings = {'Ice Stalfos Hint Terminal': 'Ice Tall Hint Terminal'}
    rows = [
        ['Ice Palace - Freezor Chest', False, *keys('Ice Palace', 1)],
        ['Ice Palace - Big Chest', False, *keys('Ice Palace', 1)],
        ['Ice Palace - Conveyor Key Drop', False, *keys('Ice Palace', 1)],
        ['Ice Palace - Freezor Chest', False, [], ['Hookshot']],
        ['Ice Palace - Big Chest', False, [], ['Hookshot']],
        ['Ice Palace - Big Key Chest', False, [], ['Hookshot']],
        ['Ice Palace - Map Chest', False, [], ['Hookshot']],
        ['Ice Palace - Spike Room', False, [], ['Hookshot']],
    ]


class TestMiseryMireWarps(PitWarpLayout, unittest.TestCase):
    """The Lone warp lands back on Square Rail, so without keys the BK Door Room and every crystal switch past it are
    cut off and the Hub's blue barriers stay up."""
    dungeon = 'Misery Mire'
    pit_landings = {'Mire BK Door Room Terminal': 'Mire Square Rail Terminal'}
    rows = [
        ['Misery Mire - Main Lobby', False, *keys('Misery Mire', 0)],
        ['Misery Mire - Map Chest', False, *keys('Misery Mire', 0)],
        ['Misery Mire - Boss', False, *keys('Misery Mire', 0)],
    ]


class TestGanonsTowerPits(PitWarpLayout, unittest.TestCase):
    """Bob's Room hole lands in Staredown, upstairs past the big key door and the rooms that need the bow."""
    dungeon = 'Ganons Tower'
    pit_landings = {'GT Ice Armos Terminal': 'GT Staredown Terminal'}
    rows = [
        ['Ganons Tower - Mini Helmasaur Room - Left', True, [], ['Big Key (Ganons Tower)']],
        ['Ganons Tower - Pre-Moldorm Chest', True, [], ['Big Key (Ganons Tower)']],
        ['Ganons Tower - Validation Chest', True, [], ['Big Key (Ganons Tower)']],
        ['Ganons Tower - Mini Helmasaur Room - Right', True, [], ['Progressive Bow']],
        ['Agahnim 2', True, [], ['Progressive Bow']],
    ]


class TestGanonsTowerWarps(PitWarpLayout, unittest.TestCase):
    """The Compass Room and Spike Crystals warps trade sides: Firesnake Room and the Randomizer Room follow the Fire Rod
    and Somaria side, Conveyor Star Pits the Hammer side."""
    dungeon = 'Ganons Tower'
    pit_landings = {'GT Firesnake Room Terminal': 'GT Conveyor Star Pits Terminal'}
    rows = [
        ['Ganons Tower - Firesnake Room', True, [], ['Hammer']],
        ['Ganons Tower - Firesnake Room', False, [], ['Fire Rod']],
        ['Ganons Tower - Randomizer Room - Top Left', True, [], ['Hammer']],
        ['Ganons Tower - Randomizer Room - Top Left', False, [], ['Cane of Somaria']],
        ['Ganons Tower - Conveyor Star Pits Pot Key', True, [], ['Fire Rod']],
        ['Ganons Tower - Conveyor Star Pits Pot Key', True, [], ['Cane of Somaria']],
        ['Ganons Tower - Conveyor Star Pits Pot Key', False, [], ['Hammer']],
    ]


if __name__ == '__main__':
    unittest.main()
