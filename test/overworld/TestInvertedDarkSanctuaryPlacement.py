import logging
import tempfile
import unittest
from unittest import mock

import Main
from BaseClasses import RegionType
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class Stop(Exception):
    pass


OVERWORLD = (RegionType.LightWorld, RegionType.DarkWorld)


class TestInvertedDarkSanctuaryPlacement(unittest.TestCase):
    """Decoupled inverted shuffle places the dark sanctuary once, leaving every dungeon portal an overworld entrance."""

    def portals_without_entrance(self, shuffle, seed):
        missing = []
        original = Main.link_entrances_new

        def stop(world, player):
            original(world, player)
            for region in world.regions:
                if region.player == player and region.name.endswith(' Portal'):
                    if not any(e.parent_region.type in OVERWORLD for e in region.entrances):
                        missing.append(region.name)
            raise Stop

        with tempfile.TemporaryDirectory() as out, mock.patch.object(Main, 'link_entrances_new', stop):
            try:
                Main.main(parse_cli(['--mode', 'inverted', '--shuffle', shuffle, '--suppress_rom', '--spoiler', 'none',
                                     '--outputpath', out, '--seed', str(seed)]), seed=seed, fish=BabelFish(lang='en'))
            except Stop:
                pass
        return missing

    def test_every_portal_has_an_entrance(self):
        logging.disable(logging.WARNING)
        try:
            for seed in range(1, 31):
                with self.subTest(seed=seed):
                    self.assertEqual([], self.portals_without_entrance('insanity', seed))
        finally:
            logging.disable(logging.NOTSET)


if __name__ == '__main__':
    unittest.main()
