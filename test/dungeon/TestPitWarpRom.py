import json
import os
import unittest
from types import SimpleNamespace

import yaml

from Rom import LANDING_ZONE_DATA, LANDING_ZONE_ROW_SIZE, pitwarp_row_bytes, write_pitwarps
from Utils import snes_to_pc

TERMINALS = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'terminals.yaml')
CAPTURES = os.path.join(os.path.dirname(__file__), '..', '..', 'pit_warp_data_manual.json')
ROWS = 61
UNSHUFFLED_ROWS = {0x16, 0x17, 0x18, 0x19, 0x24, 0x25, 0x26, 0x27}  # cave interiors, not shuffled yet


def terminal_entries():
    with open(TERMINALS) as f:
        data = yaml.safe_load(f)
    return data['pits'] + data['warps']


def row_entries():
    """Pit/warp terminals; a hole's Drop Portal terminal has an entrance row instead of LandingZoneData rows."""
    return [e for e in terminal_entries() if 'rows' in e['rom']]


class TestPitWarpRowBytes(unittest.TestCase):

    def test_row_matches_hand_packed_bytes(self):
        # HeraStartiles Landing, packed by hand from the interface doc's row format
        landing = next(e for e in terminal_entries() if e['name'] == 'Hera Startile Wide Terminal')['rom']['landing']
        self.assertEqual([0x31, 0x00,  # room
                          0x78, 0x06, 0xF8, 0x02,  # link y, x
                          0x80, 0x02, 0x0C, 0x06,  # scroll x, y
                          0x83, 0x00, 0xFF, 0x00,  # camera y, x
                          0x00, 0x02, 0x00,  # target layer, camera control, scroll quadrant
                          0x06, 0x06, 0x06, 0x07, 0x02, 0x02, 0x02, 0x03],  # camera bounds $0601..$060F
                         pitwarp_row_bytes(landing))

    def test_target_layer_is_layer_plus_bg_setting(self):
        landing = dict(next(iter(terminal_entries()))['rom']['landing'], layer_0476=1, bg_setting_ee=1)
        self.assertEqual(2, pitwarp_row_bytes(landing)[14])


class TestPitWarpRomData(unittest.TestCase):

    def test_every_terminal_has_rows_and_a_landing(self):
        for e in row_entries():
            with self.subTest(terminal=e['name']):
                self.assertTrue(e['rom']['rows'])
                self.assertIn('source_room', e['rom'])
                self.assertEqual(LANDING_ZONE_ROW_SIZE, len(pitwarp_row_bytes(e['rom']['landing'])))

    def test_rows_are_distinct_and_cover_every_shuffled_row(self):
        rows = [r for e in row_entries() for r in e['rom']['rows']]
        self.assertEqual(len(rows), len(set(rows)))
        self.assertEqual(set(range(ROWS)) - UNSHUFFLED_ROWS, set(rows))

    @unittest.skipUnless(os.path.exists(CAPTURES), 'capture file not present')
    def test_landings_match_their_captures(self):
        with open(CAPTURES) as f:
            captures = {t['label']: t for t in json.load(f)['transitions']}
        for e in row_entries():
            landing, capture = e['rom']['landing'], captures[e['rom']['capture']]
            with self.subTest(terminal=e['name']):
                bounds = [capture[f'scroll_bound_60{c}'] for c in '13579bdf']
                self.assertEqual(bounds, landing['scroll_bounds'])
                self.assertEqual({k: capture[k] for k in landing if k != 'scroll_bounds'},
                                 {k: v for k, v in landing.items() if k != 'scroll_bounds'})


class RecordingRom:
    def __init__(self):
        self.writes = {}

    def write_bytes(self, address, values):
        self.writes[address] = list(values)


def stub_world(assignments):
    """assignments: vanilla terminal name -> assigned terminal name, for one single-source group each."""
    entries = {e['name']: e for e in terminal_entries()}
    terminals = {n: SimpleNamespace(name=n, player=1, pit_terminal=None, group_rep=None, pitwarp_rom=entries[n]['rom'])
                 for n in entries}
    sources = []
    for vanilla, assigned in assignments.items():
        s = SimpleNamespace(name=f'{vanilla} source', player=1, group=vanilla, pit_terminal=terminals[assigned])
        s.group_rep = s
        sources.append(s)
    return SimpleNamespace(doors=sources + list(terminals.values()), get_door=lambda name, player: terminals[name]), entries


class TestWritePitWarps(unittest.TestCase):

    def test_group_on_its_own_terminal_still_writes_its_landing(self):
        # a vanilla fall can land elsewhere than the terminal models (Hera fall chains), so the row pins the landing
        world, entries = stub_world({'Hera Startile Wide Terminal': 'Hera Startile Wide Terminal'})
        rom = RecordingRom()
        write_pitwarps(world, rom, 1)
        address = snes_to_pc(LANDING_ZONE_DATA + 0x05 * LANDING_ZONE_ROW_SIZE)
        self.assertEqual({address: pitwarp_row_bytes(entries['Hera Startile Wide Terminal']['rom']['landing'])}, rom.writes)

    def test_unshuffled_sources_write_nothing(self):
        world, entries = stub_world({})
        rom = RecordingRom()
        write_pitwarps(world, rom, 1)
        self.assertEqual({}, rom.writes)

    def test_remapped_group_writes_its_vanilla_rows_with_the_new_landing(self):
        # Hera 2F Startiles Wide (quadrants A and S, row $1A) lands on the Ice Boss landing
        world, entries = stub_world({'Hera Back Terminal': 'Ice Boss Terminal'})
        rom = RecordingRom()
        write_pitwarps(world, rom, 1)
        address = snes_to_pc(LANDING_ZONE_DATA + 0x1A * LANDING_ZONE_ROW_SIZE)
        self.assertEqual({address: pitwarp_row_bytes(entries['Ice Boss Terminal']['rom']['landing'])}, rom.writes)


if __name__ == '__main__':
    unittest.main()
