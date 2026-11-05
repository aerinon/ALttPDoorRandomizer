import logging
import tempfile
import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish


class TestPlaythroughBigKeyInBigChest(unittest.TestCase):
    """Under items accessibility key logic lets a big key lie in its own big chest when nothing else needs it; the
    playthrough accepts the same worlds generation does and lists the big key as unreachable."""

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory() as out:
                # basic i2 keysanity standard: Misery Mire's big key sits in Misery Mire's big chest
                cls.world = Main.main(parse_cli(['--customizer', 'test/customizer/big_key_in_big_chest.yaml',
                                                 '--suppress_rom', '--spoiler', 'none', '--outputpath', out]),
                                      fish=BabelFish(lang='en'))
        finally:
            logging.disable(logging.NOTSET)

    def test_playthrough_completes(self):
        self.assertTrue(self.world.required_locations)

    def test_big_key_is_unreachable(self):
        lost = {(l.name, l.item.name) for l in self.world.spoiler.unreachables}
        self.assertEqual({('Misery Mire - Big Chest', 'Big Key (Misery Mire)')}, lost)


if __name__ == '__main__':
    unittest.main()
