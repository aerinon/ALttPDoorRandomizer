import unittest
from types import SimpleNamespace

from source.dungeon.DungeonGenLocalSearch import DoorFlags, drop_lobbies_locked


def stub_world(intensity, custom_intensity=None):
    p = 1
    customizer = None
    if custom_intensity is not None:
        customizer = SimpleNamespace(get_custom_intensity=lambda player: custom_intensity)
    return SimpleNamespace(
        trap_door_mode={p: 'optional'}, door_self_loops={p: False}, decoupledoors={p: False},
        doorShuffle={p: 'crossed'}, intensity={p: intensity}, mode={p: 'open'}, bow_mode={p: 'progressive'},
        bigkeyshuffle={p: False}, pottery={p: 'none'}, door_type_mode='original', customizer=customizer)


class TestDoorFlags(unittest.TestCase):

    def test_pit_warps_follow_intensity(self):
        self.assertEqual('none', DoorFlags.for_player(stub_world(3), 1).pit_warps)
        self.assertEqual('both', DoorFlags.for_player(stub_world(4), 1).pit_warps)

    def test_custom_intensity_overrides_world_intensity(self):
        flags = DoorFlags.for_player(stub_world(3, custom_intensity={'pit_warps': 'both'}), 1)
        self.assertEqual('both', flags.pit_warps)

    def test_drop_lobbies_stay_locked_until_moved_drops_are_modeled(self):
        for intensity in (2, 3, 4):
            self.assertTrue(drop_lobbies_locked(DoorFlags.for_player(stub_world(intensity), 1)))
