import unittest

from BaseClasses import CollectionState
from Items import ItemFactory
from Rules import challenge_room_rules
from source.dungeon.EnemyList import EnemySprite
from test.TestBase import build_vanilla_world


class TestKillChests(unittest.TestCase):
    def state(self, world, without):
        # one bow (no silvers) for the eyegore rooms on the way
        state = CollectionState(world)
        for item in ItemFactory([i.name for i in world.itempool if i.name not in without], 1):
            if not (item.name == 'Progressive Bow' and state.has('Bow', 1)):
                item.advancement = True
                state.collect(item)
        return state

    def test_eastern_big_key_chest_needs_its_enemies_killed(self):
        world = build_vanilla_world()
        world.data_tables[1].uw_enemy_table.room_map[0xb8][0].kind = EnemySprite.Lynel
        challenge_room_rules(world, 1)
        chest = world.get_location('Eastern Palace - Big Key Chest', 1)
        self.assertFalse(chest.can_reach(self.state(world, ('Progressive Sword', 'Hammer'))))
        self.assertTrue(chest.can_reach(self.state(world, ('Progressive Sword',))))


if __name__ == '__main__':
    unittest.main()
