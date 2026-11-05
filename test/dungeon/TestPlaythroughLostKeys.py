import logging
import tempfile
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class TestPlaythroughLostKeys(unittest.TestCase):
    """Under items accessibility a small key may stay behind a door the worst case can't open; the playthrough accepts
    the same worlds generation does and lists the key as unreachable."""

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out:
                # crossed i2 keysanity: the sixth Thieves Town key sits behind the sixth Thieves Town door
                cls.world = Main.main(parse_cli(['--customizer', 'test/customizer/lost_small_key.yaml',
                                                 '--suppress_rom', '--spoiler', 'none', '--outputpath', out]),
                                      fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)

    def test_playthrough_completes(self):
        self.assertTrue(self.world.required_locations)

    def test_lost_key_is_unreachable(self):
        lost = {(l.name, l.item.name) for l in self.world.spoiler.unreachables}
        self.assertIn(('Swamp Palace - Trench 1 Pot Key', 'Small Key (Thieves Town)'), lost)
        for location in self.world.spoiler.unreachables:
            self.assertIn(location.item.type, ('SmallKey', 'Event'), location.name)


if __name__ == '__main__':
    unittest.main()
