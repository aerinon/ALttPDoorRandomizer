import unittest

from BaseClasses import CrystalBarrier, Door, DoorType, Entrance, Region, RegionType
from source.dungeon.DungeonGenSectorDesc import SimpleExplorationState
from source.dungeon.DungeonStitcher import ExplorableDoor


class TestSectorExploration(unittest.TestCase):

    def test_warp_into_its_own_room_finishes(self):
        """PoD Stalfos Basement Warp landing in its own room: an unforced Null and a forced Either visit alternate."""
        room = Region('PoD Stalfos Basement', RegionType.Dungeon, None, 1)
        warp = Door(1, 'PoD Stalfos Basement Warp', DoorType.Warp)
        warp.entrance = Entrance(1, warp.name, room)
        warp.entrance.door = warp
        warp.dest = warp
        room.exits.append(warp.entrance)
        warp.entrance.connect(room)

        state = SimpleExplorationState(False)
        state.visited_map[room] = CrystalBarrier.Either, CrystalBarrier.Blue
        state.avail_doors = [ExplorableDoor(warp, CrystalBarrier.Null, CrystalBarrier.Null),
                             ExplorableDoor(warp, CrystalBarrier.Either, CrystalBarrier.Blue)]
        steps = 0
        while state.avail_doors:
            steps += 1
            self.assertLess(steps, 100, 'exploration does not finish')
            exp_door = state.next_avail_door()
            state.crystal_forced = exp_door.flag
            if not state.visited(room):
                state.visit_region(room)
        self.assertEqual(state.visited_map[room], (CrystalBarrier.Either, CrystalBarrier.Null))


if __name__ == '__main__':
    unittest.main()
