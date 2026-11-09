import unittest

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish

# Stage keys in the order main() reaches them; each also has a cli translation.
STAGES = ['create.meta', 'shuffling.pots', 'shuffling.world', 'shuffling.prep', 'shuffling.dungeons',
          'generating.itempool', 'calc.access.rules', 'placing.dungeon.prizes', 'placing.dungeon.items',
          'fill.world', 'balance.multiworld', 'patching.rom', 'patching.spoiler', 'calc.playthrough', 'done']


def generate(*extra, progress=None):
    args = parse_cli(['--suppress_rom', '--loglevel', 'warning', *extra])
    return Main.main(args=args, seed=1, fish=BabelFish(lang='en'), progress=progress)


class TestProgressCallback(unittest.TestCase):
    def assert_in_order(self, seen):
        # the spoiler is written again after the playthrough, so only first appearances must be in order
        firsts = list(dict.fromkeys(seen))
        positions = [STAGES.index(s) for s in firsts]
        self.assertEqual(positions, sorted(positions), seen)

    def test_reports_each_stage_in_order(self):
        seen = []
        world = generate('--door_shuffle', 'basic', progress=seen.append)
        self.assertIsNotNone(world)
        for required in ['shuffling.world', 'shuffling.dungeons', 'generating.itempool', 'calc.access.rules',
                         'fill.world', 'calc.playthrough', 'done']:
            self.assertIn(required, seen)
        self.assertEqual('done', seen[-1])
        self.assert_in_order(seen)

    def test_stage_keys_are_translated(self):
        fish = BabelFish(lang='en')
        for key in STAGES:
            self.assertNotEqual(key, fish.translate('cli', 'cli', key), key)

    def test_progress_is_optional(self):
        self.assertIsNotNone(generate('--spoiler', 'none'))


if __name__ == '__main__':
    unittest.main()
