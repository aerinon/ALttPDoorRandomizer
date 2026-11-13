import logging
import os
import tempfile
import unittest
from collections import Counter

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
from source.dungeon.DungeonGenLocalSearch import bias_dungeons, resolve_dungeon_bias
from source.dungeon.DungeonGenerationCommon import dungeon_portals

crossed = ['--door_shuffle', 'crossed', '--intensity', '3', '--key_logic_algorithm', 'experimental']
seeds = range(1, 6)


class Stop(Exception):
    pass


def generate(argv, settings=None, seed_list=seeds, doors_only=True):
    """The world of the first seed in seed_list that generates, or None. Generation failures of single seeds aren't
    what these tests check, but every seed failing is. doors_only stops after dungeon generation."""
    original_link = Main.link_doors_prototype
    found = {}

    def stop_after(world, player):
        original_link(world, player)
        found['world'] = world
        raise Stop()

    logging.disable(logging.WARNING)
    try:
        with tempfile.TemporaryDirectory() as out:
            base = ['--suppress_rom', '--spoiler', 'none', '--outputpath', out]
            if settings:
                custom = os.path.join(out, 'custom.yaml')
                with open(custom, 'w') as f:
                    f.write('settings:\n  1:\n' + ''.join(f'    {k}: {v}\n' for k, v in settings.items()))
                base += ['--customizer', custom]
            if doors_only:
                Main.link_doors_prototype = stop_after
            for seed in seed_list:
                try:
                    return Main.main(parse_cli(argv + base + ['--seed', str(seed)]), seed=seed,
                                     fish=BabelFish(lang='en'))
                except Stop:
                    return found['world']
                except Exception:
                    continue
            return None
    finally:
        Main.link_doors_prototype = original_link
        logging.disable(logging.NOTSET)


def dungeon_sizes(world):
    """Regions per dungeon, counting only regions the generated layouts use (trimmed ones keep a stale dungeon)."""
    used = {r for builder in world.dungeon_layouts[1].values() for s in builder.sectors for r in s.regions}
    return Counter(r.dungeon.name for r in used)


class TestBiasedGeneration(unittest.TestCase):

    def test_bias_dungeon_is_largest(self):
        world = generate(crossed + ['--dungeon_shuffle_algorithm', 'biased'], {'dungeon_bias': 'Desert Palace'})
        self.assertIsNotNone(world, f'no seed in {list(seeds)} generates')
        self.assertEqual('Desert Palace', dungeon_sizes(world).most_common(1)[0][0])

    def test_random_picks_a_dungeon(self):
        world = generate(crossed + ['--dungeon_shuffle_algorithm', 'biased'], {'dungeon_bias': 'random'})
        self.assertIsNotNone(world, f'no seed in {list(seeds)} generates')
        bias = world.dungeon_bias[1]
        self.assertIn(bias, bias_dungeons)
        self.assertEqual(bias, dungeon_sizes(world).most_common(1)[0][0])

    def test_unknown_dungeon_is_rejected(self):
        class World:
            dungeon_shuffle_algorithm = {1: 'biased'}
            dungeon_bias = {1: 'Hyrule Castel'}
        with self.assertRaises(ValueError):
            resolve_dungeon_bias(World(), 1)

    def test_full_generation(self):
        world = generate(crossed + ['--dungeon_shuffle_algorithm', 'biased'], {'dungeon_bias': 'random'},
                         doors_only=False)
        self.assertIsNotNone(world, f'no seed in {list(seeds)} generates')


class TestSmallerDungeonGen(unittest.TestCase):

    def test_fewer_dungeon_regions(self):
        argv = crossed + ['--dungeon_shuffle_algorithm', 'experimental']
        for seed in seeds:
            full = generate(argv, seed_list=[seed])
            smaller = generate(argv, {'smaller_dungeon_gen': 'true'}, seed_list=[seed])
            if full and smaller:
                break
        else:
            self.fail(f'no seed in {list(seeds)} generates both ways')
        self.assertTrue(smaller.smaller_dungeon_gen[1])
        self.assertLess(sum(dungeon_sizes(smaller).values()), sum(dungeon_sizes(full).values()))

    def test_command_line_flag(self):
        world = generate(crossed + ['--dungeon_shuffle_algorithm', 'experimental', '--smaller_dungeon_gen'])
        self.assertIsNotNone(world, f'no seed in {list(seeds)} generates')
        self.assertTrue(world.smaller_dungeon_gen[1])

    def test_full_generation(self):
        for door_shuffle in ('basic', 'crossed'):
            with self.subTest(door_shuffle=door_shuffle):
                argv = ['--door_shuffle', door_shuffle, '--intensity', '3', '--dungeon_shuffle_algorithm',
                        'experimental', '--key_logic_algorithm', 'experimental']
                world = generate(argv, {'smaller_dungeon_gen': 'true'}, doors_only=False)
                self.assertIsNotNone(world, f'no seed in {list(seeds)} generates')


class TestSanctuaryWorld(unittest.TestCase):
    """Without cross-world entrance shuffle, a dark world Sanctuary respawns Link as a bunny with no way back, so
    open mode keeps it in a dungeon with a light world entrance."""

    def test_light_world_dungeon(self):
        argv = crossed + ['--dungeon_shuffle_algorithm', 'experimental', '--mode', 'open', '--shuffle', 'vanilla']
        for seed in seeds:
            world = generate(argv, seed_list=[seed])
            if world is None:
                continue
            with self.subTest(seed=seed):
                dungeon = world.get_region('Sanctuary', 1).dungeon.name
                lw = {p.name for p in world.dungeon_portals[1] if p.light_world}
                self.assertTrue(any(name in lw for name in dungeon_portals[dungeon]), dungeon)


if __name__ == '__main__':
    unittest.main()
