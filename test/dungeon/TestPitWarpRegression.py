import logging
import os
import tempfile
import unittest

import yaml

import Main
from BaseClasses import DoorType
from CLI import parse_cli
from DoorShuffle import dungeon_warps, falldown_pits
from Rom import write_pitwarps
from source.classes.BabelFish import BabelFish

VANILLA_LANDINGS = dict(falldown_pits + dungeon_warps)
SEEDS = range(1, 9)  # generation can fail on a seed; the first that completes is checked


class RecordingRom:
    def __init__(self):
        self.writes = []

    def write_bytes(self, address, values):
        self.writes.append(address)


def generate(intensity, algorithm, customizer=None):
    logging.disable(logging.WARNING)
    try:
        for seed in SEEDS:
            argv = ['--door_shuffle', 'crossed', '--intensity', str(intensity), '--dungeon_shuffle_algorithm', algorithm,
                    '--key_logic_algorithm', 'experimental' if algorithm != 'classic' else 'partial',
                    '--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]
            if customizer:
                argv += ['--customizer', customizer]
            try:
                return Main.main(parse_cli(argv), seed=seed, fish=BabelFish(lang='en'))
            except Exception:
                continue
    finally:
        logging.disable(logging.NOTSET)
    raise RuntimeError(f'no seed in {list(SEEDS)} generated at intensity {intensity} ({algorithm})')


def pit_sources(world):
    return [d for d in world.doors if d.player == 1 and d.type in (DoorType.Hole, DoorType.Warp) and d.group]


class TestPitWarpsOffStayVanilla(unittest.TestCase):
    """Without pit/warp shuffle every pit keeps its vanilla landing and the ROM's LandingZoneData is left alone."""

    def assert_vanilla(self, world):
        for d in pit_sources(world):
            with self.subTest(source=d.name):
                self.assertIsNone(d.pit_terminal)
                self.assertEqual(VANILLA_LANDINGS[d.name], d.entrance.connected_region.name)
        rom = RecordingRom()
        write_pitwarps(world, rom, 1)
        self.assertEqual([], rom.writes)

    def test_intensity_3_experimental(self):
        self.assert_vanilla(generate(3, 'experimental'))

    def test_intensity_3_classic(self):
        self.assert_vanilla(generate(3, 'classic'))

    def test_intensity_4_with_pit_warps_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'pits_off.yaml')
            with open(path, 'w') as f:
                yaml.safe_dump({'doors': {1: {'intensity': {'pit_warps': 'none'}}}}, f)
            self.assert_vanilla(generate(4, 'experimental', path))

    def test_intensity_4_shuffles_and_writes(self):
        # positive control: the checks above would pass vacuously if nothing were ever shuffled
        world = generate(4, 'experimental')
        self.assertTrue(any(d.pit_terminal is not None for d in pit_sources(world)))
        rom = RecordingRom()
        write_pitwarps(world, rom, 1)
        self.assertTrue(rom.writes)


if __name__ == '__main__':
    unittest.main()
