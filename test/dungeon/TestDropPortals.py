import logging
import os
import tempfile
import unittest

import yaml

import Main
from BaseClasses import CollectionState, RegionType
from CLI import parse_cli
from Items import ItemFactory
from source.classes.BabelFish import BabelFish
from source.dungeon.DropPortals import drop_portals, is_drop_portal, drop_parent_region, sector_drop_portals

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


def generate_i4(extra=()):
    """The first crossed intensity-4 seed of 1-8 that generates."""
    argv = ['--door_shuffle', 'crossed', '--intensity', '4', '--dungeon_shuffle_algorithm', 'experimental',
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
    raise RuntimeError('no intensity 4 seed generated')


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


class TestDropPortalSectors(unittest.TestCase):
    """With drop lobbies unlocked, a Drop Portal stays with its owning dungeon while its fall may land elsewhere."""

    def test_unlocked_drop_portals_stay_with_their_owner(self):
        world = generate_i4()
        for p in drop_portals:
            with self.subTest(drop=p.region):
                self.assertEqual(p.owner, world.get_region(p.region, 1).dungeon.name)

    def test_stages_credit_drops_to_their_dungeon(self):
        from DoorShuffle import find_possible_entrances
        world = generate_i4()
        for name, builder in world.dungeon_layouts[1].items():
            drops = [r.name for s in builder.sectors for r in sector_drop_portals(s)]
            with self.subTest(builder=name):
                self.assertTrue(set(drops) <= set(find_possible_entrances(world, 1, builder)))

    def test_spoiler_lists_drops_with_the_lobbies_not_the_pits(self):
        world = generate_i4()
        world.spoiler.parse_data()
        lobbies = {entry['lobby_name']: entry['door_name'] for entry in world.spoiler.lobbies.values()}
        pit_lines = {entry['entrance'] for entry in world.spoiler.doors.values()}
        for p in drop_portals:
            with self.subTest(drop=p.region):
                self.assertEqual(world.get_door(p.fall, 1).pit_terminal.name, lobbies[p.region])
                self.assertNotIn(p.fall, pit_lines)

    def test_spoiler_lists_drops_when_custom_intensity_unlocks_them(self):
        # world intensity 2, with lobbies and pits switched on by the customizer
        with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as f:
            yaml.safe_dump({'doors': {1: {'intensity': {'lobbies': True, 'pit_warps': 'pits'}}}}, f)
        try:
            world = generate_i4(['--intensity', '2', '--customizer', f.name])
        finally:
            os.unlink(f.name)
        world.spoiler.parse_data()
        lobbies = {entry['lobby_name']: entry['door_name'] for entry in world.spoiler.lobbies.values()}
        for p in drop_portals:
            with self.subTest(drop=p.region):
                self.assertEqual(world.get_door(p.fall, 1).pit_terminal.name, lobbies.get(p.region))

    def test_sewer_palette_spreads_from_the_sanctuary_grave_landing_in_hyrule_castle(self):
        for extra in ([], ['--mode', 'inverted']):
            world = generate_i4(extra)
            dungeons_of_room = {}
            for r in world.regions:
                for ext in r.exits:
                    if r.player == 1 and r.dungeon and ext.door and ext.door.roomIndex >= 0:
                        dungeons_of_room.setdefault(ext.door.roomIndex, set()).add(r.dungeon.name)
            landing = world.get_door('Sewers Drop Portal Fall', 1).entrance.connected_region
            landing_room = next(ext.door.roomIndex for ext in landing.exits if ext.door and ext.door.roomIndex >= 0)
            with self.subTest(mode=extra):
                if landing.dungeon.name == 'Hyrule Castle':
                    self.assertEqual(0x1, world.get_room(landing_room, 1).palette)
                for idx, dungeons in dungeons_of_room.items():
                    if world.get_room(idx, 1).palette == 0x1:
                        self.assertIn('Hyrule Castle', dungeons, hex(idx))

    def test_any_hole_into_a_drop_portal_revives_at_its_landing(self):
        from Rules import revival_lobby
        world = generate_i4()
        hole, drop = world.get_entrance('Kakariko Well Drop', 1), world.get_region('Skull Pinball Drop Portal', 1)
        landing = world.get_door('Skull Pinball Drop Portal Fall', 1).entrance.connected_region
        original = hole.connected_region
        hole.connected_region = drop
        try:
            self.assertEqual(landing, revival_lobby(hole, drop, world, 1))
        finally:
            hole.connected_region = original

    def test_no_mirrorless_courtyard_path_through_any_drop_portal(self):
        from Rules import mirrorless_path_to_castle_courtyard
        world = generate_i4()
        hole = world.get_entrance('Hyrule Castle Secret Entrance Drop', 1)
        original = hole.connected_region
        hole.connected_region = world.get_region('Skull Pinball Drop Portal', 1)
        try:
            rules = mirrorless_path_to_castle_courtyard(world, 1)
        finally:
            hole.connected_region = original
        self.assertEqual(1, len(rules))
        self.assertFalse(rules[0](CollectionState(world)))

    def test_unlocked_falls_are_shuffled(self):
        world = generate_i4()
        for p in drop_portals:
            with self.subTest(drop=p.region):
                self.assertIsNotNone(world.get_door(p.fall, 1).pit_terminal)


def generate_doors(seed, *door_args):
    argv = [*door_args, '--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental',
            '--suppress_rom', '--spoiler', 'none', '--seed', str(seed)]
    logging.disable(logging.WARNING)
    try:
        return Main.main(parse_cli(argv), seed=seed, fish=BabelFish(lang='en'))
    finally:
        logging.disable(logging.NOTSET)


class TestDropPortalKeyLogic(unittest.TestCase):
    """Key logic walks a dungeon from its Drop Portals, where a hole enters it, so it never locks a hole behind a key."""

    @classmethod
    def setUpClass(cls):
        cls.vanilla = generate_doors(1, '--door_shuffle', 'vanilla')
        cls.basic = generate_doors(2, '--door_shuffle', 'basic', '--intensity', '1')

    def test_walks_start_at_drop_portals(self):
        for label, world in [('vanilla', self.vanilla), ('basic', self.basic)]:
            starts = {r.name for r in world.key_layout[1]['Hyrule Castle'].start_regions}
            with self.subTest(doors=label):
                self.assertIn('Sewers Drop Portal', starts)
                self.assertNotIn('Sewers Rat Path', starts)

    def test_starts_are_listed_once(self):
        for label, world in [('vanilla', self.vanilla), ('basic', self.basic)]:
            for name, layout in world.key_layout[1].items():
                with self.subTest(doors=label, dungeon=name):
                    names = [r.name for r in layout.start_regions]
                    self.assertEqual(len(names), len(set(names)))

    def test_no_drop_portal_is_locked(self):
        for label, world in [('vanilla', self.vanilla), ('basic', self.basic)]:
            for name, logic in world.key_logic[1].items():
                if logic.new_logic is None:
                    continue
                locked = set(logic.new_logic.bk_regions) | set(logic.new_logic.region_key_reqs)
                with self.subTest(doors=label, dungeon=name):
                    self.assertEqual([], sorted(r.name for r in locked if is_drop_portal(r)))

    def test_sanctuary_grave_needs_only_the_glove(self):
        world = self.vanilla
        state = CollectionState(world)
        state.collect(ItemFactory('Power Glove', 1), True)
        self.assertTrue(world.get_entrance('Sanctuary Grave', 1).access_rule(state))


if __name__ == '__main__':
    unittest.main()
