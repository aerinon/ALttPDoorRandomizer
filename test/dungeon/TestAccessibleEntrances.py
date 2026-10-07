import unittest
from types import SimpleNamespace

from BaseClasses import Entrance, Region, RegionType
from DoorShuffle import find_accessible_entrances


def connect(parent, child, door=None):
    ext = Entrance(1, f'{parent.name} -> {child.name}', parent)
    ext.door = door
    parent.exits.append(ext)
    ext.connect(child)


class TestAccessibleEntrances(unittest.TestCase):
    """The overworld walk runs before trap door shuffle, so a trap that shuffle may still remove can't hide a dungeon's
    only entrance; in vanilla trap mode the traps are final."""

    def setUp(self):
        self.regions = {n: Region(n, RegionType.LightWorld, None, 1)
                        for n in ['Links House', 'Dark Sanctuary Hint', 'Hyrule Castle Ledge', 'Field', 'Ice Room',
                                  'Forest']}
        lobby = Region('Swamp Lobby', RegionType.Dungeon, None, 1)
        lobby.dungeon = SimpleNamespace(name='Swamp Palace')
        self.regions['Swamp Lobby'] = lobby
        r = self.regions
        connect(r['Links House'], r['Field'])
        connect(r['Field'], r['Ice Room'])
        self.trap = SimpleNamespace(blocked=True, trapped=True)
        connect(r['Ice Room'], r['Forest'], self.trap)  # the only way on crosses a vanilla trap door
        lobby_door = SimpleNamespace(entrance=SimpleNamespace(parent_region=lobby))
        connect(r['Forest'], lobby)
        self.portal = SimpleNamespace(door=lobby_door)

    def world(self, trap_mode):
        return SimpleNamespace(mode={1: 'inverted'}, trap_door_mode={1: trap_mode}, dungeon_portals={1: [self.portal]},
                               get_region=lambda name, player: self.regions[name])

    def test_trap_not_final(self):
        builder = SimpleNamespace(name='Swamp Palace')
        self.assertEqual(['Swamp Lobby'], find_accessible_entrances(self.world('optional'), 1, builder))

    def test_vanilla_traps_are_final(self):
        builder = SimpleNamespace(name='Swamp Palace')
        self.assertEqual([], find_accessible_entrances(self.world('vanilla'), 1, builder))


if __name__ == '__main__':
    unittest.main()
