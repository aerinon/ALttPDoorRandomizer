import logging
import unittest

import DoorShuffle
import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


class TestPortalLookup(unittest.TestCase):
    """Each dungeon lobby entered from '<name> Portal' must resolve to that portal; the suffix was stripped as a set of
    characters ('Hera Portal' -> 'He'), so most lookups found nothing."""

    def test_every_lobby_finds_its_portal(self):
        original = Main.link_doors

        def stop(world, player):
            raise Stop(world)

        Main.link_doors = stop
        logging.disable(logging.WARNING)
        try:
            with self.assertRaises(Stop) as stopped:
                Main.main(parse_cli(['--door_shuffle', 'vanilla', '--suppress_rom', '--spoiler', 'none', '--seed', '1']),
                          seed=1, fish=BabelFish(lang='en'))
        finally:
            Main.link_doors = original
            logging.disable(logging.NOTSET)
        world = stopped.exception.args[0]
        for portal in world.dungeon_portals[1]:
            portal_region = world.get_region(f'{portal.name} Portal', 1)
            for ext in portal_region.exits:
                lobby = ext.connected_region
                if lobby is None or not ext.name.startswith('Enter '):
                    continue
                with self.subTest(portal=portal.name):
                    self.assertIs(portal, DoorShuffle._find_portal_for_region(lobby, world, 1))


if __name__ == '__main__':
    unittest.main()
