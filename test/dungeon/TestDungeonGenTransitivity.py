import unittest

from BaseClasses import World
from Dungeons import create_dungeons
from overworld.EntranceShuffle2 import mandatory_connections, connect_simple
from Regions import create_regions, create_dungeon_regions
from Doors import create_doors
from RoomData import create_rooms

from DoorShuffle import prep_world_for_doors_prototype, convert_to_sectors
from dungeon.DungeonGenTransitivity import do_transitivity_check
from dungeon.DungeonGen3 import create_sector_descriptors


class TestDungeon(unittest.TestCase):
    def setUp(self):
        self.world = World(1, {1: 'vanilla'}, {1: 'crossed'}, {1: 'noglitches'}, {1: 'open'}, {}, {}, {},
                      {}, {}, {}, {}, {}, True, {}, [], {}, 'none')
        self.world.intensity = {1: 3}
        self.world.experimental = {1: True}
        self.world.trap_door_mode = {1: 'vanilla'}
        create_regions(self.world, 1)
        create_dungeon_regions(self.world, 1)
        create_doors(self.world, 1)
        create_rooms(self.world, 1)
        create_dungeons(self.world, 1)
        for exitname, regionname in mandatory_connections:
            connect_simple(self.world, exitname, regionname, 1)

        prep_world_for_doors_prototype(self.world, 1)
        self.sector_pool = []
        for pool, region_list in self.world.dungeon_pool[1]:
            self.sector_pool += convert_to_sectors(region_list, self.world, 1)
        create_sector_descriptors(self.sector_pool, self.world, 1)

    def test_do_transitivity_check_case1(self):
        test_case = ['Ice Portal', 'Ice Antechamber', 'GT Big Key Room', 'TR Lava Escape', 'TR Refill', 'TR Torches',
                     'Mire Chest View', 'Ice Compass Room', 'Skull Star Pits', 'PoD Conveyor', 'Tower Dark Archers',
                     'Hera Tile Room', 'Sewers Dark Cross', 'GT Frozen Over', 'Sewers Pull Switch', 'Thieves Lobby',
                     'Ice Bomb Drop', 'Swamp Left Elbow', 'Ice Spike Room', 'PoD Big Chest Balcony']
        test_pool = [s for s in self.sector_pool if s.sector_key() in test_case]
        do_transitivity_check(test_pool, [])

    def test_do_transitivity_check_case2(self):
        test_case = ['Eastern Portal', 'Eastern Boss', 'GT Beam Dash', 'GT Hidden Star', 'GT Compass Room', 'TR Roller Room', 'TR Compass Room',
                     'Mire Lobby', 'Thieves Attic', 'Thieves Big Chest Nook', 'PoD Bow Statue Left', 'PoD Shooter Room', 'Tower Altar',
                     'Desert Big Chest Room', 'Desert Compass Room', 'Eastern Compass Room', 'Hyrule Castle East Hall', 'TR Torches',
                     'Ice Hammer Block', 'Ice Lonely Freezor', 'Thieves Compass Room', 'Ice Big Key', 'Hyrule Dungeon South Abyss']



