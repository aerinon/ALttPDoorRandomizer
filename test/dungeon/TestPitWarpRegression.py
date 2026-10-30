import logging
import os
import tempfile
import unittest

import yaml

import Main
from BaseClasses import DoorType
from CLI import parse_cli
from DoorShuffle import boss_indicator, drop_falls, dungeon_warps, falldown_pits, pit_boss_regions
from Rom import pit_boss_sources, write_boss_indicators, write_pitwarps
from source.classes.BabelFish import BabelFish

VANILLA_LANDINGS = dict(falldown_pits + dungeon_warps + drop_falls)
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


def custom_intensity(tmp, intensity):
    path = os.path.join(tmp, 'intensity.yaml')
    with open(path, 'w') as f:
        yaml.safe_dump({'doors': {1: {'intensity': intensity}}}, f)
    return path


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
            self.assert_vanilla(generate(4, 'experimental', custom_intensity(tmp, {'pit_warps': 'none'})))

    def test_intensity_4_with_pit_warps_none_generates_intensity_3(self):
        def layout(world):
            return (world.seed,
                    sorted((d.name, str(getattr(d.dest, 'name', None)), d.smallKey, d.bigKey)
                           for d in world.doors if d.player == 1),
                    sorted((loc.name, loc.item.name if loc.item else '') for loc in world.get_locations()))
        with tempfile.TemporaryDirectory() as tmp:
            custom = generate(4, 'experimental', custom_intensity(tmp, {'pit_warps': 'none'}))
        self.assertEqual(layout(generate(3, 'experimental')), layout(custom))

    def test_intensity_4_shuffles_and_writes(self):
        # positive control: the checks above would pass vacuously if nothing were ever shuffled
        world = generate(4, 'experimental')
        self.assertTrue(any(d.pit_terminal is not None for d in pit_sources(world)))
        rom = RecordingRom()
        write_pitwarps(world, rom, 1)
        self.assertTrue(rom.writes)


class ByteRom:
    def __init__(self):
        self.writes = {}

    def write_byte(self, address, value):
        self.writes[address] = value


def indicator_slot(world, region):
    return 0x13f000 + boss_indicator[world.get_region(region, 1).dungeon.name][0]


class TestBossIndicator(unittest.TestCase):
    """A shuffled fall into Skull Woods' or Ice Palace's boss marks the pit's room; an unshuffled one keeps marking the
    room before the vestibule above the boss."""

    def assert_pit_rooms(self, world):
        sources = pit_boss_sources(world, 1)
        self.assertEqual(set(pit_boss_regions), set(sources))
        rom = ByteRom()
        write_boss_indicators(world, rom, 1)
        for name, region in pit_boss_regions.items():
            with self.subTest(boss=name):
                source = sources[name]
                self.assertEqual(region, source.entrance.connected_region.name)
                vanilla_rom = world.get_door(source.group, 1).pitwarp_rom
                # a hole falling into the boss has no room before it: it is entered from the overworld
                expected = vanilla_rom['source_room'] if 'source_room' in vanilla_rom else 0
                self.assertEqual(expected, rom.writes[indicator_slot(world, region)])

    def assert_vestibule_rooms(self, world):
        self.assertEqual({}, pit_boss_sources(world, 1))
        rom = ByteRom()
        write_boss_indicators(world, rom, 1)
        for vestibule_door, region in [('Skull Spike Corner SW', 'Skull Boss'), ('Ice Antechamber NE', 'Ice Boss')]:
            with self.subTest(boss=region):
                before = world.get_door(vestibule_door, 1).entrance.parent_region.entrances
                room = next(e for e in before if e.name != 'Skull Final Drop WS').door.roomIndex
                if room < 0:
                    continue  # the vestibule is a lobby: no room before it to mark
                self.assertEqual(room, rom.writes[indicator_slot(world, region)])

    def test_intensity_4_marks_the_pit_room(self):
        self.assert_pit_rooms(generate(4, 'experimental'))

    def test_custom_pits_mark_the_pit_room(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assert_pit_rooms(generate(3, 'experimental', custom_intensity(tmp, {'pit_warps': 'pits'})))

    def test_intensity_3_marks_the_room_before_the_vestibule(self):
        self.assert_vestibule_rooms(generate(3, 'experimental'))

    def test_custom_warps_only_marks_the_room_before_the_vestibule(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assert_vestibule_rooms(generate(4, 'experimental', custom_intensity(tmp, {'pit_warps': 'warps'})))


if __name__ == '__main__':
    unittest.main()
