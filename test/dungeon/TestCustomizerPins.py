import logging
import os
import tempfile
import unittest

import yaml

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class TestCustomizerPins(unittest.TestCase):
    """A hand-written customizer doors section pins what it names, the way generation would have made it."""

    def generate(self, argv, doors, seeds=range(1, 6)):
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out:
                custom = os.path.join(out, 'custom.yaml')
                with open(custom, 'w') as f:
                    yaml.safe_dump({'doors': {1: doors}}, f)
                base = ['--customizer', custom, '--suppress_rom', '--spoiler', 'none', '--outputpath', out]
                for seed in seeds:  # the first seed that generates; generation failures aren't what this tests
                    try:
                        return Main.main(parse_cli(argv + base + ['--seed', str(seed)]), seed=seed,
                                         fish=BabelFish(lang='en'))
                    except Exception as e:  # a file that fails to load fails the test
                        if type(e).__name__ not in ('GenerationException', 'FillError'):
                            raise
                self.skipTest(f'no seed in {list(seeds)} generates')
        finally:
            logging.disable(logging.NOTSET)

    def test_pit_lands_its_whole_group(self):
        world = self.generate(
            ['--door_shuffle', 'basic', '--intensity', '4', '--dungeon_shuffle_algorithm', 'experimental',
             '--key_logic_algorithm', 'experimental'],
            {'doors': {'Hera Beetles Holes Landing': {'dest': 'Hera Down Stairs Landing Terminal', 'one-way': True},
                       'Hera Startile Corner Holes Front': {'dest': 'Hera Up Stairs Landing Terminal', 'one-way': True}}})
        for source, terminal in [('Hera Beetles Holes Front', 'Hera Down Stairs Landing Terminal'),
                                 ('Hera Beetles Holes Landing', 'Hera Down Stairs Landing Terminal'),
                                 ('Hera Startile Corner Holes Front', 'Hera Up Stairs Landing Terminal'),
                                 ('Hera Startile Corner Holes Landing', 'Hera Up Stairs Landing Terminal')]:
            door = world.get_door(source, 1)
            with self.subTest(source=source):
                self.assertEqual(terminal, door.pit_terminal.name)
                self.assertEqual(world.get_region(terminal.removesuffix(' Terminal'), 1), door.entrance.connected_region)
                self.assertIsNotNone(door.group_rep)  # the ROM writes each group's rows through its representative

    def test_trap_door_lobbies_are_unblocked(self):
        """A pinned world skips stitching, which unblocks the doors it makes lobbies; loading the lobbies must instead.
        Seed 1, crossed i3, key drops, pot keys, keysanity: Desert West's lobby is Desert Boss SW, a no-exit trap."""
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out:
                world = Main.main(parse_cli(['--customizer', 'test/customizer/trap_door_lobbies.yaml', '--suppress_rom',
                                             '--spoiler', 'none', '--outputpath', out]), fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)
        for door in ['Desert Boss SW', 'Ice Switch Room SE', 'GT Gauntlet 3 SW', 'Ice Many Pots SW',
                     'GT Speed Torch SE', 'Sewers Pull Switch S']:
            with self.subTest(door=door):
                self.assertFalse(world.get_door(door, 1).blocked)

    def test_final_door_types_remove_unlisted_traps(self):
        """Seed 4, basic i4: every Palace of Darkness trap candidate has a listed type, so trap shuffle has nothing to
        place; the vanilla trap on PoD Arena Main NE, a Bomb Door in the file, must still come off."""
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out:
                world = Main.main(parse_cli(['--customizer', 'test/customizer/untrapped_door_types.yaml',
                                             '--suppress_rom', '--spoiler', 'none', '--outputpath', out]),
                                  fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)
        door = world.get_door('PoD Arena Main NE', 1)
        self.assertFalse(door.blocked)
        self.assertFalse(door.trapped)

    def test_warp_into_its_own_room_loads(self):
        """Crossed i4 seed 9: PoD Stalfos Basement Warp lands on a terminal in its own room, which sector analysis of
        the pinned world used to explore forever."""
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out:
                world = Main.main(parse_cli(['--customizer', 'test/customizer/self_landing_warp.yaml',
                                             '--suppress_rom', '--spoiler', 'none', '--outputpath', out]),
                                  fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)
        warp = world.get_door('PoD Stalfos Basement Warp', 1)
        self.assertEqual(warp.entrance.connected_region, warp.entrance.parent_region)


if __name__ == '__main__':
    unittest.main()
