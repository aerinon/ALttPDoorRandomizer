import unittest

import Main
from CLI import parse_cli
from ItemList import ItemFactory
from source.classes.BabelFish import BabelFish

# a vanilla-shop world whose free rupees cover the paid checks but not the vanilla shop stock
vanilla_shops = 'test/customizer/money_balance_vanilla_shops.yaml'


def generate(seed, *extra):
    args = parse_cli(['--suppress_rom', '--spoiler', 'none', '--loglevel', 'warning', *extra])
    return Main.main(args=args, seed=seed, fish=BabelFish(lang='en'))


def generate_custom(customizer, *extra):
    args = parse_cli(['--customizer', customizer, '--suppress_rom', '--spoiler', 'none', '--loglevel', 'warning', *extra])
    return Main.main(args=args, fish=BabelFish(lang='en'))


def count_300s(world):
    return sum(1 for loc in world.get_locations() if loc.item and loc.item.name == 'Rupees (300)')


class TestMoneyBalance(unittest.TestCase):
    def test_vanilla_shop_stock_is_not_a_required_purchase(self):
        with self.assertLogs('', level='DEBUG') as logs:
            world = generate_custom(vanilla_shops)
        messages = '\n'.join(logs.output)
        self.assertNotIn('Money balancing needed', messages)
        self.assertEqual(5, count_300s(world))

    def test_upgrade_when_later_rupees_are_too_small(self):
        # every rupee and balancer spot holds 20, so once the early spheres come up short no swap can add money;
        # the pass must mint 300s instead of giving up
        original = Main.balance_money_progression
        money = {'Rupee (1)', 'Rupees (5)', 'Rupees (50)', 'Rupees (100)', 'Rupees (300)',
                 'Bombs (3)', 'Arrows (10)', 'Bombs (10)'}

        def rigged(world):
            for loc in world.get_locations():
                if loc.item and loc.forced_item is None and loc.item.name in money:
                    loc.item = ItemFactory('Rupees (20)', loc.item.player)
                    loc.item.location = loc
            original(world)
        Main.balance_money_progression = rigged
        try:
            with self.assertLogs('', level='DEBUG') as logs:
                generate_custom(vanilla_shops)
        finally:
            Main.balance_money_progression = original
        messages = '\n'.join(logs.output)
        self.assertIn('Upgrading Rupees (20)', messages)
        self.assertNotIn('money grind', messages)

    def test_crossed_keysanity_seed(self):
        with self.assertLogs('', level='DEBUG') as logs:
            world = generate(1, '--shuffle', 'crossed', '--keyshuffle', 'wild', '--bigkeyshuffle', '--mapshuffle',
                             '--compassshuffle', '--accessibility', 'locations', '--key_logic_algorithm', 'static')
        messages = '\n'.join(logs.output)
        self.assertNotIn('money grind', messages)
        self.assertEqual(5, count_300s(world))


if __name__ == '__main__':
    unittest.main()
