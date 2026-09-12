import unittest

from CLI import parse_cli
from Main import main
from source.classes.BabelFish import BabelFish


def generate(seed, *extra):
    args = parse_cli(['--suppress_rom', '--spoiler', 'none', '--loglevel', 'warning', *extra])
    main(args=args, seed=seed, fish=BabelFish(lang='en'))


class TestMoneyBalance(unittest.TestCase):
    def test_upgrade_when_later_rupees_are_too_small(self):
        # seed 202: by the stall every early rupee spot already holds 20 or more and the only rupees left in
        # later spheres are 5s and 20s, so no swap can add money; the pass must mint 300s instead of bailing
        with self.assertLogs('', level='DEBUG') as logs:
            generate(202)
        messages = '\n'.join(logs.output)
        self.assertIn('Upgrading Rupees', messages)
        self.assertNotIn('money grind', messages)

    def test_crossed_keysanity_seed(self):
        with self.assertLogs('', level='DEBUG') as logs:
            generate(1, '--shuffle', 'crossed', '--keyshuffle', 'wild', '--bigkeyshuffle', '--mapshuffle',
                     '--compassshuffle', '--accessibility', 'locations')
        self.assertNotIn('money grind', '\n'.join(logs.output))


if __name__ == '__main__':
    unittest.main()
