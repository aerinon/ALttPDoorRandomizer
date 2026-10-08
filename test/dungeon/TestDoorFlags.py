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
        bigkeyshuffle={p: False}, pottery={p: 'none'}, door_type_mode={p: 'original'}, customizer=customizer)


class TestDoorFlags(unittest.TestCase):

    def test_pit_warps_follow_intensity(self):
        self.assertEqual('none', DoorFlags.for_player(stub_world(3), 1).pit_warps)
        self.assertEqual('both', DoorFlags.for_player(stub_world(4), 1).pit_warps)

    def test_custom_intensity_overrides_world_intensity(self):
        flags = DoorFlags.for_player(stub_world(3, custom_intensity={'pit_warps': 'both'}), 1)
        self.assertEqual('both', flags.pit_warps)

    def test_drop_lobbies_unlock_with_lobbies_and_pits(self):
        for intensity, locked in [(1, True), (2, True), (3, True), (4, False)]:
            with self.subTest(intensity=intensity):
                self.assertEqual(locked, drop_lobbies_locked(DoorFlags.for_player(stub_world(intensity), 1)))

    def test_drop_lobbies_need_both_lobbies_and_pits(self):
        for custom, locked in [({'pit_warps': 'pits'}, False), ({'pit_warps': 'warps'}, True),
                               ({'pit_warps': 'both', 'lobbies': False}, True)]:
            with self.subTest(custom=custom):
                flags = DoorFlags.for_player(stub_world(4, custom_intensity=custom), 1)
                self.assertEqual(locked, drop_lobbies_locked(flags))
