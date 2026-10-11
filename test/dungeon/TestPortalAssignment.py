import logging
import unittest

import Main
import source.dungeon.DungeonStitcherV2 as stitcher
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
from source.dungeon.DungeonGenTransitivity import do_transitivity_check


class Stop(Exception):
    pass


class TestPortalAssignment(unittest.TestCase):
    """A portal pin Transitivity accepts stays solvable once the stitcher makes the connection: the pinned check and the
    connected state describe the same layout. A prune that counted forced doors (detect_problematic_forced_scenarios)
    rejected the connected state, leaving the next portal no candidate (seed 335424647, Turtle Rock)."""

    def test_connected_portals_stay_solvable(self):
        unsolvable = []
        original_assign, original_link = stitcher.assign_portal_candidate, Main.link_doors_prototype

        def checked(builder, candidates, entrance_regions, master_door_list, portal, flags, *args, **kwargs):
            candidate = original_assign(builder, candidates, entrance_regions, master_door_list, portal, flags,
                                        *args, **kwargs)
            if not do_transitivity_check(builder, builder.sectors, flags, []):
                unsolvable.append(f'{builder.name}: {portal.name} <-> {candidate.name}')
            return candidate

        def stop_after(*args, **kwargs):
            original_link(*args, **kwargs)
            raise Stop()

        stitcher.assign_portal_candidate, Main.link_doors_prototype = checked, stop_after
        argv = ['--door_shuffle', 'crossed', '--intensity', '3', '--shuffle', 'vanilla', '--shopsanity',
                '--dungeon_shuffle_algorithm', 'experimental', '--key_logic_algorithm', 'experimental',
                '--suppress_rom', '--spoiler', 'none', '--seed', '335424647']
        logging.disable(logging.WARNING)
        try:
            Main.main(parse_cli(argv), seed=335424647, fish=BabelFish(lang='en'))
        except Stop:
            pass
        finally:
            stitcher.assign_portal_candidate, Main.link_doors_prototype = original_assign, original_link
            logging.disable(logging.NOTSET)
        self.assertEqual([], unsolvable)


if __name__ == '__main__':
    unittest.main()
