import logging
import os
import unittest

import yaml

import Main
from BaseClasses import RegionType
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
from source.dungeon.DropPortals import drop_portals, is_drop_portal, drop_parent_region

TERMINALS = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'terminals.yaml')
VANILLA_ROM = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'orig', 'z3.sfc')
VANILLA_HOLES = {'Skull Woods First Section Hole (North)': 'Skull Pot Circle Drop Portal',
                 'Skull Woods First Section Hole (West)': 'Skull Left Drop Drop Portal',
                 'Skull Woods First Section Hole (East)': 'Skull Pinball Drop Portal',
                 'Skull Woods Second Section Hole': 'Skull Back Drop Drop Portal',
                 'Sanctuary Grave': 'Sewers Drop Portal'}

def generate(extra=()):
    argv = ['--door_shuffle', 'crossed', '--intensity', '3', '--dungeon_shuffle_algorithm', 'experimental',
            '--key_logic_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none', *extra]
    logging.disable(logging.WARNING)
    try:
        for seed in range(1, 9):
            try:
                return Main.main(parse_cli(argv + ['--seed', str(seed)]), seed=seed, fish=BabelFish(lang='en'))
            except Exception:
                continue
    finally:
        logging.disable(logging.NOTSET)
    raise RuntimeError('no seed generated')


class TestDropPortals(unittest.TestCase):

    def test_vanilla_holes_lead_to_drop_portals(self):
        world = generate()
        for hole, portal in VANILLA_HOLES.items():
            with self.subTest(hole=hole):
                region = world.get_entrance(hole, 1).connected_region
                self.assertEqual(portal, region.name)
                self.assertTrue(is_drop_portal(region))
                self.assertIsNotNone(drop_parent_region(region))

    def test_shuffled_holes_still_lead_to_drop_portals(self):
        # holes shuffle with every other hole, so any hole may lead to a Drop Portal, but exactly one does
        world = generate(['--shuffle', 'crossed'])
        for p in drop_portals:
            with self.subTest(drop=p.region):
                region = world.get_region(p.region, 1)
                holes = [e for e in region.entrances if e.parent_region.type != RegionType.Dungeon]
                self.assertEqual(1, len(holes))
                self.assertEqual(holes[0].parent_region, drop_parent_region(region))

    def test_locked_falls_land_on_their_vanilla_landing(self):
        world = generate()
        for p in drop_portals:
            with self.subTest(drop=p.region):
                fall = world.get_door(p.fall, 1)
                self.assertIsNone(fall.pit_terminal)
                self.assertEqual(p.landing, fall.entrance.connected_region.name)

    def test_every_drop_has_a_terminal_with_a_full_landing(self):
        with open(TERMINALS) as f:
            entries = {e['name']: e for e in yaml.safe_load(f)['pits']}
        for p in drop_portals:
            with self.subTest(drop=p.region):
                entry = entries[p.terminal]
                self.assertEqual(p.landing, entry['region'])
                self.assertEqual([p.fall], entry['sources'])
                self.assertEqual(p.entrance_id, entry['rom']['entrance'])
                for key in ['floor_a4', 'blockset_aa1', 'room_id_a0', 'scroll_bounds']:
                    self.assertIn(key, entry['rom']['landing'])

    @unittest.skip('entrance_row_fields arrives in Task 6')
    @unittest.skipUnless(os.path.exists(VANILLA_ROM), 'vanilla ROM not present')
    def test_drop_landings_match_the_vanilla_entrance_rows(self):
        from Rom import entrance_row_fields
        with open(VANILLA_ROM, 'rb') as f:
            rom = f.read()
        with open(TERMINALS) as f:
            entries = {e['name']: e for e in yaml.safe_load(f)['pits']}
        for p in drop_portals:
            with self.subTest(drop=p.region):
                for address, data in entrance_row_fields(p.entrance_id, entries[p.terminal]['rom']['landing']):
                    self.assertEqual(list(rom[address:address + len(data)]), data, hex(address))


if __name__ == '__main__':
    unittest.main()
