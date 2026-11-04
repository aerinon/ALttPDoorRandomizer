import logging
import tempfile
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class TestPlaythroughCopy(unittest.TestCase):
    """The spoiler playthrough's world copy has its own doors and key logic, so the copy's rules match the world's."""

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out:
                # seed 59, crossed i3 standard: the copy used to miss its key door rules and stall in the escape
                cls.world = Main.main(parse_cli(['--customizer', 'test/customizer/playthrough_copy_key_rules.yaml',
                                                 '--suppress_rom', '--spoiler', 'none', '--outputpath', out]),
                                      fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)

    def test_playthrough_completes(self):
        self.assertTrue(self.world.required_locations)

    def test_copy_doors_use_copy_entrances(self):
        copy = Main.copy_world(self.world)
        entrances = {id(e) for region in copy.regions for e in region.exits}
        originals = {id(d) for d in self.world.doors}
        for door in copy.doors:
            self.assertNotIn(id(door), originals)
            if door.entrance is not None and copy.check_for_entrance(door.name, door.player) is not None:
                self.assertIn(id(door.entrance), entrances, door.name)
        for name, logic in copy.key_logic[1].items():
            self.assertIsNot(logic, self.world.key_logic[1][name])


if __name__ == '__main__':
    unittest.main()
