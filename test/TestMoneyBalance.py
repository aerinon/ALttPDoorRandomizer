import unittest

from CLI import parse_cli
from Main import main
from source.classes.BabelFish import BabelFish


def generate(seed, *extra):
    args = parse_cli(['--suppress_rom', '--spoiler', 'none', '--loglevel', 'warning', *extra])
    return main(args=args, seed=seed, fish=BabelFish(lang='en'))


def count_300s(world):
    return sum(1 for loc in world.get_locations() if loc.item and loc.item.name == 'Rupees (300)')


class TestMoneyBalance(unittest.TestCase):
    def test_vanilla_shop_stock_is_not_a_required_purchase(self):
        # seed 202 used to count every potion, shield and capacity upgrade in the vanilla shops as a purchase
        # and came up short on money
        with self.assertLogs('', level='DEBUG') as logs:
            world = generate(202)
        messages = '\n'.join(logs.output)
        self.assertNotIn('Money balancing needed', messages)
        self.assertEqual(5, count_300s(world))

    def test_crossed_keysanity_seed(self):
        with self.assertLogs('', level='DEBUG') as logs:
            world = generate(1, '--shuffle', 'crossed', '--keyshuffle', 'wild', '--bigkeyshuffle', '--mapshuffle',
                             '--compassshuffle', '--accessibility', 'locations', '--key_logic_algorithm', 'static')
        messages = '\n'.join(logs.output)
        self.assertNotIn('money grind', messages)
        self.assertEqual(5, count_300s(world))


if __name__ == '__main__':
    unittest.main()
