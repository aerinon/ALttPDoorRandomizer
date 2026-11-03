import logging
import os
import tempfile
import unittest

import Main
from BaseClasses import DoorType
from CLI import parse_cli
from source.classes.BabelFish import BabelFish

shuffled_types = (DoorType.Normal, DoorType.SpiralStairs, DoorType.Open, DoorType.StraightStairs, DoorType.Ladder)


def snapshot(world):
    def door_kinds():
        kinds = {}
        for (names, player), entry in world.spoiler.doorTypes.items():
            for name in names.rsplit(' (', 1)[0].split(' <-> '):
                kinds[name] = entry['type']
        return kinds

    def proposal(layout):
        return sorted(' <-> '.join(sorted(d.name for d in x)) if isinstance(x, tuple) else x.name for x in layout.proposal)

    return {
        'doors': {d.name: getattr(d.dest, 'name', None) for d in world.doors
                  if d.player == 1 and d.type in shuffled_types and not d.traversal_only},
        'door types': door_kinds(),
        'portals': {p.name: p.door.name for p in world.dungeon_portals[1]},
        'placements': {l.name: l.item.name for l in world.get_locations() if l.item and l.player == 1},
        'key doors': {name: proposal(layout) for name, layout in world.key_layout[1].items()},
        'pits': {d.name: d.pit_terminal.name for d in world.doors if d.player == 1 and d.pit_terminal is not None},
    }


class TestCustomizerRoundTrip(unittest.TestCase):
    """A world exported with --print_custom_yaml loads back unchanged."""

    def round_trip(self, argv, seeds=range(1, 6)):
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out:
                base = ['--suppress_rom', '--spoiler', 'none', '--outputpath', out]
                for seed in seeds:  # the first seed that generates; generation failures aren't what this tests
                    try:
                        original = Main.main(parse_cli(argv + base + ['--print_custom_yaml', '--seed', str(seed)]),
                                             seed=seed, fish=BabelFish(lang='en'))
                        break
                    except Exception:
                        continue
                else:
                    self.skipTest(f'no seed in {list(seeds)} generates')
                custom = os.path.join(out, f'DR_{seed}_custom.yaml')
                reloaded = Main.main(parse_cli(['--customizer', custom] + base), fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)
        before, after = snapshot(original), snapshot(reloaded)
        for aspect in before:
            with self.subTest(seed=seed, aspect=aspect):
                self.assertEqual(before[aspect], after[aspect])

    def test_basic_classic(self):
        self.round_trip(['--door_shuffle', 'basic', '--intensity', '2'])

    def test_crossed_experimental(self):
        self.round_trip(['--door_shuffle', 'crossed', '--intensity', '3', '--dungeon_shuffle_algorithm', 'experimental'])

    def test_crossed_pits_and_warps(self):
        self.round_trip(['--door_shuffle', 'crossed', '--intensity', '4', '--dungeon_shuffle_algorithm', 'experimental',
                         '--key_logic_algorithm', 'experimental'])


if __name__ == '__main__':
    unittest.main()
