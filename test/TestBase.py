import unittest

from BaseClasses import CollectionState, World
from CLI import parse_cli
from DoorShuffle import link_doors, link_doors_prep
from Doors import create_doors
from Dungeons import create_dungeons
from Fill import get_dungeon_item_pool
from ItemList import difficulties, generate_itempool
from Main import set_world_options
from Items import ItemFactory
from OverworldGlitchRules import create_owg_connections
from OverworldShuffle import link_overworld, create_dynamic_exits
from Regions import create_regions, create_dungeon_regions, create_shops, mark_light_dark_world_regions
from RoomData import create_rooms
from Rules import set_rules
from source.classes.BabelFish import BabelFish
from source.enemizer.DamageTables import DamageTable
from source.item.FillUtil import create_item_pool_config
from source.overworld.EntranceShuffle2 import link_entrances_new
from source.rom.DataTables import init_data_tables

PRIZES = ['Green Pendant', 'Red Pendant', 'Blue Pendant', 'Beat Agahnim 1', 'Beat Agahnim 2',
          'Crystal 1', 'Crystal 2', 'Crystal 3', 'Crystal 4', 'Crystal 5', 'Crystal 6', 'Crystal 7']


def build_vanilla_world(mode='open', logic='noglitches', customizer=None):
    player = 1
    args = parse_cli(['--mode', mode, '--logic', logic, '--shuffle', 'vanilla', '--door_shuffle', 'vanilla',
                      '--intensity', '1', '--suppress_rom', '--spoiler', 'none'])
    world = World(args.multi, args.shuffle, args.door_shuffle, args.logic, args.mode, args.swords,
                  args.difficulty, args.item_functionality, args.timer, args.progressive, args.goal, args.algorithm,
                  args.accessibility, args.shuffleganon, args.custom, args.customitemarray, args.hints, args.spoiler)
    world.customizer = customizer
    world.seed = 1
    set_world_options(world, args, BabelFish(lang='en'))
    world.difficulty_requirements[player] = difficulties[world.difficulty[player]]

    create_regions(world, player)
    if logic in ('owglitches', 'hybridglitches', 'nologic'):
        create_owg_connections(world, player)
    create_dungeon_regions(world, player)
    create_shops(world, player)
    create_doors(world, player)
    create_rooms(world, player)
    create_dungeons(world, player)
    world.damage_table[player] = DamageTable()
    world.data_tables[player] = init_data_tables(world, player)

    link_overworld(world, player)
    create_dynamic_exits(world, player)
    link_entrances_new(world, player)
    link_doors_prep(world, player)
    create_item_pool_config(world)
    link_doors(world, player)
    mark_light_dark_world_regions(world, player)

    generate_itempool(world, player)
    world.required_medallions[player] = ['Ether', 'Quake']
    world.itempool.extend(get_dungeon_item_pool(world))
    world.itempool.extend(ItemFactory(PRIZES, player))
    world.get_location('Agahnim 1', player).item = None
    world.get_location('Agahnim 2', player).item = None
    set_rules(world, player)
    return world


class TestBase(unittest.TestCase):

    _state_cache = {}

    def get_state(self, items):
        key = (id(self.world), tuple((item.name, item.player) for item in items))
        if key in self._state_cache:
            return self._state_cache[key]
        state = CollectionState(self.world)
        for item in items:
            item.advancement = True
            state.collect(item)
        state.sweep_for_events()
        self._state_cache[key] = state
        return state

    def run_location_tests(self, access_pool):
        for location, access, *item_pool in access_pool:
            items = item_pool[0]
            all_except = item_pool[1] if len(item_pool) > 1 else None
            with self.subTest(location=location, access=access, items=items, all_except=all_except):
                if all_except and len(all_except) > 0:
                    items = self.world.itempool[:]
                    items = [item for item in items if item.name not in all_except and not ("Bottle" in item.name and "AnyBottle" in all_except)]
                    items.extend(ItemFactory(item_pool[0], 1))
                else:
                    items = ItemFactory(items, 1)
                state = self.get_state(items)

                self.assertEqual(self.world.get_location(location, 1).can_reach(state), access)

    def run_entrance_tests(self, access_pool):
        for entrance, access, *item_pool in access_pool:
            items = item_pool[0]
            all_except = item_pool[1] if len(item_pool) > 1 else None
            with self.subTest(entrance=entrance, access=access, items=items, all_except=all_except):
                if all_except and len(all_except) > 0:
                    items = self.world.itempool[:]
                    items = [item for item in items if item.name not in all_except and not ("Bottle" in item.name and "AnyBottle" in all_except)]
                    items.extend(ItemFactory(item_pool[0], 1))
                else:
                    items = ItemFactory(items, 1)
                state = self.get_state(items)

                self.assertEqual(self.world.get_entrance(entrance, 1).can_reach(state), access)