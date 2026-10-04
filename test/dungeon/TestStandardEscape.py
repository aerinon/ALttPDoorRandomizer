import logging
import types
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
import source.dungeon.DungeonGenTransitivity as Transitivity
import source.dungeon.DungeonStitcherV2 as Stitcher


class Stop(Exception):
    pass


def generate_standard(seed, intensity, extra=()):
    argv = ['--door_shuffle', 'crossed', '--intensity', str(intensity), '--dungeon_shuffle_algorithm', 'experimental',
            '--key_logic_algorithm', 'experimental', '--mode', 'standard', '--suppress_rom', '--spoiler', 'none',
            '--seed', str(seed), *extra]
    logging.disable(logging.WARNING)
    try:
        return Main.main(parse_cli(argv), seed=seed, fish=BabelFish(lang='en'))
    finally:
        logging.disable(logging.NOTSET)


class TestStandardEscape(unittest.TestCase):
    """The mirror scroll returns Link to Cellblock or Throne Room, so in standard both must lead back to the lobby and
    Cellblock must reach Throne Room; Transitivity rejects sector sets that can't satisfy that."""

    def setUp(self):
        self.originals = (Transitivity.do_transitivity_check_main, Stitcher.generate_dungeon_find_proposal)

    def tearDown(self):
        Transitivity.do_transitivity_check_main, Stitcher.generate_dungeon_find_proposal = self.originals

    def test_one_way_trap_rejected(self):
        # crossed i1, vanilla entrances, shopsanity, seed 382466786: Cellblock's only door can attach only to GT Four
        # Torches, which Bob's Room drops into but never leads back from. Formerly passed Transitivity, then the
        # stitcher exhausted every layout ("Generation taking too long. Ref Hyrule Castle Dungeon").
        results = []
        check = self.originals[0]

        def first_hc_check(builder, sector_list, flags, initial_connections=None, greedy=False):
            result = check(builder, sector_list, flags, initial_connections, greedy)
            if builder.name == 'Hyrule Castle Dungeon':
                results.append(result)
                if not greedy:
                    raise Stop()
            return result

        Transitivity.do_transitivity_check_main = first_hc_check
        with self.assertRaises(Stop):
            generate_standard(382466786, 1, ['--shuffle', 'vanilla', '--shopsanity'])
        self.assertEqual(2, len(results))  # greedy and full passes
        self.assertFalse(any(results))  # rejected, whatever form a result takes

    def test_stitched_layout_satisfies_escape(self):
        layouts = []
        stitch = self.originals[1]

        def record_hc(builder, flags, world, player):
            proposal = stitch(builder, flags, world, player)
            if builder.name == 'Hyrule Castle Dungeon':
                layouts.append((builder.sectors, flags, proposal))
            return proposal

        Stitcher.generate_dungeon_find_proposal = record_hc
        generate_standard(382466786, 1, ['--shuffle', 'vanilla', '--shopsanity'])
        sectors, flags, proposal = layouts[0]
        escape = Transitivity.EscapeCheck(sectors, types.SimpleNamespace(vanilla_traps=flags.vanilla_traps))
        self.assertTrue(escape.satisfied(proposal))


if __name__ == '__main__':
    unittest.main()
