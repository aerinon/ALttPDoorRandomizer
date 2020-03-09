import logging
from BaseClasses import CollectionState, RegionType, DoorType
from Regions import key_only_locations
from RoomData import DoorKind
from collections import deque
import OWGSets


def set_rules(world, player):

    if world.logic[player] == 'nologic':
        logging.getLogger('').info('WARNING! Seeds generated under this logic often require major glitches and may be impossible!')
        if world.mode[player] != 'inverted':
            world.get_region('Links House', player).can_reach_private = lambda state: True
            world.get_region('Sanctuary', player).can_reach_private = lambda state: True
            old_rule = world.get_region('Old Man House', player).can_reach
            world.get_region('Old Man House', player).can_reach_private = lambda state: state.can_reach('Old Man', 'Location', player) or old_rule(state)
            return
        else:
            world.get_region('Inverted Links House', player).can_reach_private = lambda state: True
            world.get_region('Inverted Dark Sanctuary', player).entrances[0].parent_region.can_reach_private = lambda state: True
            if world.shuffle[player] != 'vanilla':
                old_rule = world.get_region('Old Man House', player).can_reach
                world.get_region('Old Man House', player).can_reach_private = lambda state: state.can_reach('Old Man', 'Location', player) or old_rule(state)
            world.get_region('Hyrule Castle Ledge', player).can_reach_private = lambda state: True
            return

    global_rules(world, player)
    if world.mode[player] != 'inverted':
        default_rules(world, player)

    if world.mode[player] == 'open':
        open_rules(world, player)
    elif world.mode[player] == 'standard':
        standard_rules(world, player)
    elif world.mode[player] == 'inverted':
        open_rules(world, player)
        inverted_rules(world, player)
    else:
        raise NotImplementedError('Not implemented yet')

    if world.logic[player] == 'noglitches':
        no_glitches_rules(world, player)
    elif world.logic[player] == 'owglitches':
        logging.getLogger('').info('There is a chance OWG has bugged edge case rulesets, especially in inverted. Definitely file a report on GitHub if you see anything strange.')
        # Initially setting no_glitches_rules to set the baseline rules for some
        # entrances. The overworld_glitches_rules set is primarily additive.
        no_glitches_rules(world, player)
        overworld_glitches_rules(world, player)
    elif world.logic[player] == 'minorglitches':
        logging.getLogger('').info('Minor Glitches may be buggy still. No guarantee for proper logic checks.')
    else:
        raise NotImplementedError('Not implemented yet')

    if world.goal[player] == 'dungeons':
        # require all dungeons to beat ganon
        add_rule(world.get_location('Ganon', player), lambda state: state.can_reach('Master Sword Pedestal', 'Location', player) and state.has('Beat Agahnim 1', player) and state.has('Beat Agahnim 2', player) and state.has_crystals(7, player))
    elif world.goal[player] == 'ganon':
        # require aga2 to beat ganon
        add_rule(world.get_location('Ganon', player), lambda state: state.has('Beat Agahnim 2', player))
    
    if world.mode[player] != 'inverted':
        set_big_bomb_rules(world, player)
    else:
        set_inverted_big_bomb_rules(world, player)

    # if swamp and dam have not been moved we require mirror for swamp palace
    if not world.swamp_patch_required[player]:
        add_rule(world.get_entrance('Swamp Lobby Moat', player), lambda state: state.has_Mirror(player))

    if world.mode[player] != 'inverted':
        set_bunny_rules(world, player)
    else:
        set_inverted_bunny_rules(world, player)

def set_rule(spot, rule):
    spot.access_rule = rule

def set_defeat_dungeon_boss_rule(location):
    # Lambda required to defer evaluation of dungeon.boss since it will change later if boos shuffle is used
    set_rule(location, lambda state: location.parent_region.dungeon.boss.can_defeat(state))

def set_always_allow(spot, rule):
    spot.always_allow = rule

def add_rule(spot, rule, combine='and'):
    old_rule = spot.access_rule
    if combine == 'or':
        spot.access_rule = lambda state: rule(state) or old_rule(state)
    else:
        spot.access_rule = lambda state: rule(state) and old_rule(state)


def add_lamp_requirement(spot, player):
    add_rule(spot, lambda state: state.has('Lamp', player, state.world.lamps_needed_for_dark_rooms))


def forbid_item(location, item, player):
    old_rule = location.item_rule
    location.item_rule = lambda i: (i.name != item or i.player != player) and old_rule(i)

def add_item_rule(location, rule):
    old_rule = location.item_rule
    location.item_rule = lambda item: rule(item) and old_rule(item)

def item_in_locations(state, item, player, locations):
    for location in locations:
        if item_name(state, location[0], location[1]) == (item, player):
            return True
    return False

def item_name(state, location, player):
    location = state.world.get_location(location, player)
    if location.item is None:
        return None
    return (location.item.name, location.item.player)

def global_rules(world, player):
    # ganon can only carry triforce
    add_item_rule(world.get_location('Ganon', player), lambda item: item.name == 'Triforce' and item.player == player)

    # we can s&q to the old man house after we rescue him. This may be somewhere completely different if caves are shuffled!
    old_rule = world.get_region('Old Man House', player).can_reach_private
    world.get_region('Old Man House', player).can_reach_private = lambda state: state.can_reach('Old Man', 'Location', player) or old_rule(state)

    set_rule(world.get_location('Sunken Treasure', player), lambda state: state.has('Open Floodgate', player))
    set_rule(world.get_location('Dark Blacksmith Ruins', player), lambda state: state.has('Return Smith', player))
    set_rule(world.get_location('Purple Chest', player), lambda state: state.has('Pick Up Purple Chest', player))  # Can S&Q with chest
    set_rule(world.get_location('Ether Tablet', player), lambda state: state.has('Book of Mudora', player) and state.has_beam_sword(player))
    set_rule(world.get_location('Master Sword Pedestal', player), lambda state: state.has('Red Pendant', player) and state.has('Blue Pendant', player) and state.has('Green Pendant', player))

    set_rule(world.get_location('Missing Smith', player), lambda state: state.has('Get Frog', player) and state.can_reach('Blacksmiths Hut', 'Region', player)) # Can't S&Q with smith
    set_rule(world.get_location('Blacksmith', player), lambda state: state.has('Return Smith', player))
    set_rule(world.get_location('Magic Bat', player), lambda state: state.has('Magic Powder', player))
    set_rule(world.get_location('Sick Kid', player), lambda state: state.has_bottle(player))
    set_rule(world.get_location('Library', player), lambda state: state.has_Boots(player))
    set_rule(world.get_location('Mimic Cave', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_location('Sahasrahla', player), lambda state: state.has('Green Pendant', player))


    set_rule(world.get_location('Spike Cave', player), lambda state:
    state.has('Hammer', player) and state.can_lift_rocks(player) and
    ((state.has('Cape', player) and state.can_extend_magic(player, 16, True)) or
     (state.has('Cane of Byrna', player) and
      (state.can_extend_magic(player, 12, True) or
       (state.world.can_take_damage and (state.has_Boots(player) or state.has_hearts(player, 4))))))
             )

    set_rule(world.get_location('Hookshot Cave - Top Right', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_location('Hookshot Cave - Top Left', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_location('Hookshot Cave - Bottom Right', player), lambda state: state.has('Hookshot', player) or state.has('Pegasus Boots', player))
    set_rule(world.get_location('Hookshot Cave - Bottom Left', player), lambda state: state.has('Hookshot', player))

    # Start of door rando rules
    # TODO: Do these need to flag off when door rando is off? - some of them, yes

    # Eastern Palace
    # Eyegore room needs a bow
    set_rule(world.get_entrance('Eastern Duo Eyegores NE', player), lambda state: state.can_shoot_arrows(player))
    set_rule(world.get_entrance('Eastern Single Eyegore NE', player), lambda state: state.can_shoot_arrows(player))
    set_rule(world.get_entrance('Eastern Map Balcony Hook Path', player), lambda state: state.has('Hookshot', player))

    # Boss rules. Same as below but no BK or arrow requirement.
    set_defeat_dungeon_boss_rule(world.get_location('Eastern Palace - Prize', player))
    set_defeat_dungeon_boss_rule(world.get_location('Eastern Palace - Boss', player))

    # Desert
    set_rule(world.get_location('Desert Palace - Torch', player), lambda state: state.has_Boots(player))
    set_rule(world.get_entrance('Desert Wall Slide NW', player), lambda state: state.has_fire_source(player))
    set_defeat_dungeon_boss_rule(world.get_location('Desert Palace - Prize', player))
    set_defeat_dungeon_boss_rule(world.get_location('Desert Palace - Boss', player))

    # Tower of Hera
    set_rule(world.get_location('Tower of Hera - Big Key Chest', player), lambda state: state.has_fire_source(player))
    set_defeat_dungeon_boss_rule(world.get_location('Tower of Hera - Boss', player))
    set_defeat_dungeon_boss_rule(world.get_location('Tower of Hera - Prize', player))

    set_rule(world.get_entrance('Tower Altar NW', player), lambda state: state.has_sword(player))
    set_defeat_dungeon_boss_rule(world.get_location('Agahnim 1', player))

    set_rule(world.get_entrance('PoD Arena Bonk Path', player), lambda state: state.has_Boots(player))
    set_rule(world.get_entrance('PoD Mimics 1 NW', player), lambda state: state.can_shoot_arrows(player))
    set_rule(world.get_entrance('PoD Mimics 2 NW', player), lambda state: state.can_shoot_arrows(player))
    set_rule(world.get_entrance('PoD Bow Statue Down Ladder', player), lambda state: state.can_shoot_arrows(player))
    set_rule(world.get_entrance('PoD Map Balcony Drop Down', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_entrance('PoD Dark Pegs WN', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_entrance('PoD Dark Pegs Up Ladder', player), lambda state: state.has('Hammer', player))
    set_defeat_dungeon_boss_rule(world.get_location('Palace of Darkness - Boss', player))
    set_defeat_dungeon_boss_rule(world.get_location('Palace of Darkness - Prize', player))

    set_rule(world.get_entrance('Swamp Lobby Moat', player), lambda state: state.has('Flippers', player) and state.has('Open Floodgate', player))
    set_rule(world.get_entrance('Swamp Trench 1 Approach Dry', player), lambda state: not state.has('Trench 1 Filled', player))
    set_rule(world.get_entrance('Swamp Trench 1 Key Ledge Dry', player), lambda state: not state.has('Trench 1 Filled', player))
    set_rule(world.get_entrance('Swamp Trench 1 Departure Dry', player), lambda state: not state.has('Trench 1 Filled', player))
    set_rule(world.get_entrance('Swamp Trench 1 Approach Key', player), lambda state: state.has('Flippers', player) and state.has('Trench 1 Filled', player))
    set_rule(world.get_entrance('Swamp Trench 1 Approach Swim Depart', player), lambda state: state.has('Flippers', player) and state.has('Trench 1 Filled', player))
    set_rule(world.get_entrance('Swamp Trench 1 Key Approach', player), lambda state: state.has('Flippers', player) and state.has('Trench 1 Filled', player))
    set_rule(world.get_entrance('Swamp Trench 1 Key Ledge Depart', player), lambda state: state.has('Flippers', player) and state.has('Trench 1 Filled', player))
    set_rule(world.get_entrance('Swamp Trench 1 Departure Approach', player), lambda state: state.has('Flippers', player) and state.has('Trench 1 Filled', player))
    set_rule(world.get_entrance('Swamp Trench 1 Departure Key', player), lambda state: state.has('Flippers', player) and state.has('Trench 1 Filled', player))
    set_rule(world.get_location('Trench 1 Switch', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_entrance('Swamp Hub Hook Path', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_location('Swamp Palace - Hookshot Pot Key', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Swamp Trench 2 Pots Dry', player), lambda state: not state.has('Trench 2 Filled', player))
    set_rule(world.get_entrance('Swamp Trench 2 Pots Wet', player), lambda state: state.has('Flippers', player) and state.has('Trench 2 Filled', player))
    set_rule(world.get_entrance('Swamp Trench 2 Departure Wet', player), lambda state: state.has('Flippers', player) and state.has('Trench 2 Filled', player))
    set_rule(world.get_entrance('Swamp West Ledge Hook Path', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Swamp Barrier Ledge Hook Path', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Swamp Drain Right Switch', player), lambda state: state.has('Drained Swamp', player))
    set_rule(world.get_entrance('Swamp Drain WN', player), lambda state: state.has('Drained Swamp', player))
    set_rule(world.get_entrance('Swamp Flooded Room WS', player), lambda state: state.has('Drained Swamp', player))
    set_rule(world.get_entrance('Swamp Flooded Room Ladder', player), lambda state: state.has('Drained Swamp', player))
    set_rule(world.get_location('Swamp Palace - Flooded Room - Left', player), lambda state: state.has('Drained Swamp', player))
    set_rule(world.get_location('Swamp Palace - Flooded Room - Right', player), lambda state: state.has('Drained Swamp', player))
    set_rule(world.get_entrance('Swamp Waterway NW', player), lambda state: state.has('Flippers', player))
    set_rule(world.get_entrance('Swamp Waterway N', player), lambda state: state.has('Flippers', player))
    set_rule(world.get_entrance('Swamp Waterway NE', player), lambda state: state.has('Flippers', player))
    set_rule(world.get_location('Swamp Palace - Waterway Pot Key', player), lambda state: state.has('Flippers', player))
    set_defeat_dungeon_boss_rule(world.get_location('Swamp Palace - Boss', player))
    set_defeat_dungeon_boss_rule(world.get_location('Swamp Palace - Prize', player))

    set_rule(world.get_entrance('Skull Big Chest Hookpath', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Skull Torch Room WN', player), lambda state: state.has('Fire Rod', player))
    set_rule(world.get_entrance('Skull Vines NW', player), lambda state: state.has_sword(player))
    set_defeat_dungeon_boss_rule(world.get_location('Skull Woods - Boss', player))
    set_defeat_dungeon_boss_rule(world.get_location('Skull Woods - Prize', player))

    # blind can't have the small key? - not necessarily true anymore - but likely still
    set_rule(world.get_location('Thieves\' Town - Big Chest', player), lambda state: state.has('Hammer', player))
    for entrance in ['Thieves Basement Block Path', 'Thieves Blocked Entry Path', 'Thieves Conveyor Block Path', 'Thieves Conveyor Bridge Block Path']:
        set_rule(world.get_entrance(entrance, player), lambda state: state.can_lift_rocks(player))
    for location in ['Thieves\' Town - Blind\'s Cell', 'Thieves\' Town - Boss']:
        forbid_item(world.get_location(location, player), 'Big Key (Thieves Town)', player)
    forbid_item(world.get_location('Thieves\' Town - Blind\'s Cell', player), 'Big Key (Thieves Town)', player)
    for location in ['Suspicious Maiden', 'Thieves\' Town - Blind\'s Cell']:
        set_rule(world.get_location(location, player), lambda state: state.has('Big Key (Thieves Town)', player))
    set_rule(world.get_location('Revealing Light', player), lambda state: state.has('Shining Light', player) and state.has('Maiden Rescued', player))
    set_rule(world.get_location('Thieves\' Town - Boss', player), lambda state: state.has('Maiden Unmasked', player) and world.get_location('Thieves\' Town - Boss', player).parent_region.dungeon.boss.can_defeat(state))
    set_rule(world.get_location('Thieves\' Town - Prize', player), lambda state: state.has('Maiden Unmasked', player) and world.get_location('Thieves\' Town - Prize', player).parent_region.dungeon.boss.can_defeat(state))

    set_rule(world.get_entrance('Ice Lobby WS', player), lambda state: state.can_melt_things(player))
    set_rule(world.get_entrance('Ice Hammer Block ES', player), lambda state: state.can_lift_rocks(player) and state.has('Hammer', player))
    set_rule(world.get_location('Ice Palace - Hammer Block Key Drop', player), lambda state: state.can_lift_rocks(player) and state.has('Hammer', player))
    set_rule(world.get_location('Ice Palace - Map Chest', player), lambda state: state.can_lift_rocks(player) and state.has('Hammer', player))
    set_rule(world.get_entrance('Ice Antechamber Hole', player), lambda state: state.can_lift_rocks(player) and state.has('Hammer', player))
    # todo: ohko rules for spike room - could split into two regions instead of these, but can_take_damage is usually true
    set_rule(world.get_entrance('Ice Spike Room WS', player), lambda state: state.world.can_take_damage or state.has('Hookshot', player) or state.has('Cape', player) or state.has('Cane of Byrna', player))
    set_rule(world.get_entrance('Ice Spike Room Up Stairs', player), lambda state: state.world.can_take_damage or state.has('Hookshot', player) or state.has('Cape', player) or state.has('Cane of Byrna', player))
    set_rule(world.get_entrance('Ice Spike Room Down Stairs', player), lambda state: state.world.can_take_damage or state.has('Hookshot', player) or state.has('Cape', player) or state.has('Cane of Byrna', player))
    set_rule(world.get_location('Ice Palace - Spike Room', player), lambda state: state.world.can_take_damage or state.has('Hookshot', player) or state.has('Cape', player) or state.has('Cane of Byrna', player))
    set_rule(world.get_location('Ice Palace - Freezor Chest', player), lambda state: state.can_melt_things(player))
    set_rule(world.get_entrance('Ice Hookshot Ledge Path', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Ice Hookshot Balcony Path', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Ice Switch Room SE', player), lambda state: state.has('Cane of Somaria', player) or state.has('Convenient Block', player))
    set_defeat_dungeon_boss_rule(world.get_location('Ice Palace - Boss', player))
    set_defeat_dungeon_boss_rule(world.get_location('Ice Palace - Prize', player))

    set_rule(world.get_entrance('Mire Lobby Gap', player), lambda state: state.has_Boots(player) or state.has('Hookshot', player))
    set_rule(world.get_entrance('Mire Post-Gap Gap', player), lambda state: state.has_Boots(player) or state.has('Hookshot', player))
    set_rule(world.get_entrance('Mire Falling Bridge WN', player), lambda state: state.has_Boots(player) or state.has('Hookshot', player))  # this is due to the fact the the door opposite is blocked
    set_rule(world.get_entrance('Mire 2 NE', player), lambda state: state.has_sword(player) or state.has('Fire Rod', player) or state.has('Ice Rod', player) or state.has('Hammer', player) or state.has('Cane of Somaria', player) or state.can_shoot_arrows(player))  # need to defeat wizzrobes, bombs don't work ...
    set_rule(world.get_location('Misery Mire - Spike Chest', player), lambda state: (state.world.can_take_damage and state.has_hearts(player, 4)) or state.has('Cane of Byrna', player) or state.has('Cape', player))
    set_rule(world.get_entrance('Mire Left Bridge Hook Path', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Mire Tile Room NW', player), lambda state: state.has_fire_source(player))
    set_rule(world.get_entrance('Mire Attic Hint Hole', player), lambda state: state.has_fire_source(player))
    set_rule(world.get_entrance('Mire Dark Shooters SW', player), lambda state: state.has('Cane of Somaria', player))
    set_defeat_dungeon_boss_rule(world.get_location('Misery Mire - Boss', player))
    set_defeat_dungeon_boss_rule(world.get_location('Misery Mire - Prize', player))

    set_rule(world.get_entrance('TR Main Lobby Gap', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Lobby Ledge Gap', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Hub SW', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Hub SE', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Hub ES', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Hub EN', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Hub NW', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Hub NE', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Torches NW', player), lambda state: state.has('Cane of Somaria', player) and state.has('Fire Rod', player))
    set_rule(world.get_entrance('TR Big Chest Entrance Gap', player), lambda state: state.has('Cane of Somaria', player) or state.has('Hookshot', player))
    set_rule(world.get_entrance('TR Big Chest Gap', player), lambda state: state.has('Cane of Somaria', player) or state.has('Hookshot', player))
    set_rule(world.get_entrance('TR Dark Ride Up Stairs', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Dark Ride SW', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Crystal Maze Cane Path', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Final Abyss South Stairs', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('TR Final Abyss NW', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_location('Turtle Rock - Eye Bridge - Bottom Left', player), lambda state: state.has('Cane of Byrna', player) or state.has('Cape', player) or state.has('Mirror Shield', player))
    set_rule(world.get_location('Turtle Rock - Eye Bridge - Bottom Right', player), lambda state: state.has('Cane of Byrna', player) or state.has('Cape', player) or state.has('Mirror Shield', player))
    set_rule(world.get_location('Turtle Rock - Eye Bridge - Top Left', player), lambda state: state.has('Cane of Byrna', player) or state.has('Cape', player) or state.has('Mirror Shield', player))
    set_rule(world.get_location('Turtle Rock - Eye Bridge - Top Right', player), lambda state: state.has('Cane of Byrna', player) or state.has('Cape', player) or state.has('Mirror Shield', player))
    set_defeat_dungeon_boss_rule(world.get_location('Turtle Rock - Boss', player))
    set_defeat_dungeon_boss_rule(world.get_location('Turtle Rock - Prize', player))

    set_rule(world.get_location('Ganons Tower - Bob\'s Torch', player), lambda state: state.has_Boots(player))
    set_rule(world.get_entrance('GT Hope Room EN', player), lambda state: state.has('Cane of Somaria', player))
    set_rule(world.get_entrance('GT Conveyor Cross WN', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_entrance('GT Conveyor Cross EN', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('GT Speed Torch SE', player), lambda state: state.has('Fire Rod', player))
    set_rule(world.get_entrance('GT Hookshot East-North Path', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('GT Hookshot South-East Path', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('GT Hookshot South-North Path', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('GT Hookshot East-South Path', player), lambda state: state.has('Hookshot', player) or state.has_Boots(player))
    set_rule(world.get_entrance('GT Hookshot North-East Path', player), lambda state: state.has('Hookshot', player) or state.has_Boots(player))
    set_rule(world.get_entrance('GT Hookshot North-South Path', player), lambda state: state.has('Hookshot', player) or state.has_Boots(player))
    set_rule(world.get_entrance('GT Firesnake Room Hook Path', player), lambda state: state.has('Hookshot', player))
    # I am tempted to stick an invincibility rule for getting across falling bridge
    set_rule(world.get_entrance('GT Ice Armos NE', player), lambda state: world.get_region('GT Ice Armos', player).dungeon.bosses['bottom'].can_defeat(state))
    set_rule(world.get_entrance('GT Ice Armos WS', player), lambda state: world.get_region('GT Ice Armos', player).dungeon.bosses['bottom'].can_defeat(state))

    set_rule(world.get_entrance('GT Mimics 1 NW', player), lambda state: state.can_shoot_arrows(player))
    set_rule(world.get_entrance('GT Mimics 1 ES', player), lambda state: state.can_shoot_arrows(player))
    set_rule(world.get_entrance('GT Mimics 2 WS', player), lambda state: state.can_shoot_arrows(player))
    set_rule(world.get_entrance('GT Mimics 2 NE', player), lambda state: state.can_shoot_arrows(player))
    # consider access to refill room
    set_rule(world.get_entrance('GT Gauntlet 1 WN', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Gauntlet 2 EN', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Gauntlet 2 SW', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Gauntlet 3 NW', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Gauntlet 3 SW', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Gauntlet 4 NW', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Gauntlet 4 SW', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Gauntlet 5 NW', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Gauntlet 5 WS', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Wizzrobes 1 SW', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Wizzrobes 2 SE', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Wizzrobes 2 NE', player), lambda state: state.can_kill_most_things(player))
    set_rule(world.get_entrance('GT Lanmolas 2 ES', player), lambda state: world.get_region('GT Lanmolas 2', player).dungeon.bosses['middle'].can_defeat(state))
    set_rule(world.get_entrance('GT Lanmolas 2 NW', player), lambda state: world.get_region('GT Lanmolas 2', player).dungeon.bosses['middle'].can_defeat(state))
    set_rule(world.get_entrance('GT Torch Cross ES', player), lambda state: state.has_fire_source(player))
    set_rule(world.get_entrance('GT Falling Torches NE', player), lambda state: state.has_fire_source(player))
    set_rule(world.get_entrance('GT Moldorm Gap', player), lambda state: state.has('Hookshot', player) and world.get_region('GT Moldorm', player).dungeon.bosses['top'].can_defeat(state))
    set_defeat_dungeon_boss_rule(world.get_location('Agahnim 2', player))

    add_key_logic_rules(world, player)

    # crystal switch rules
    set_rule(world.get_entrance('PoD Arena Crystal Path', player), lambda state: state.can_reach_blue(world.get_region('PoD Arena Crystal', player), player))
    set_rule(world.get_entrance('Swamp Trench 2 Pots Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Swamp Trench 2 Pots', player), player))
    set_rule(world.get_entrance('Swamp Shortcut Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Swamp Shortcut', player), player))
    set_rule(world.get_entrance('Thieves Attic ES', player), lambda state: state.can_reach_blue(world.get_region('Thieves Attic', player), player))
    set_rule(world.get_entrance('Thieves Hellway Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Thieves Hellway', player), player))
    set_rule(world.get_entrance('Thieves Hellway Crystal Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Thieves Hellway N Crystal', player), player))
    set_rule(world.get_entrance('Thieves Triple Bypass SE', player), lambda state: state.can_reach_blue(world.get_region('Thieves Triple Bypass', player), player))
    set_rule(world.get_entrance('Thieves Triple Bypass WN', player), lambda state: state.can_reach_blue(world.get_region('Thieves Triple Bypass', player), player))
    set_rule(world.get_entrance('Thieves Triple Bypass EN', player), lambda state: state.can_reach_blue(world.get_region('Thieves Triple Bypass', player), player))
    set_rule(world.get_entrance('Ice Crystal Right Blue Hole', player), lambda state: state.can_reach_blue(world.get_region('Ice Crystal Right', player), player))
    set_rule(world.get_entrance('Ice Crystal Left Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Ice Crystal Left', player), player))
    set_rule(world.get_entrance('Ice Backwards Room Hole', player), lambda state: state.can_reach_blue(world.get_region('Ice Backwards Room', player), player))
    set_rule(world.get_entrance('Mire Hub Upper Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Hub', player), player))
    set_rule(world.get_entrance('Mire Hub Lower Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Hub', player), player))
    set_rule(world.get_entrance('Mire Hub Right Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Hub Right', player), player))
    set_rule(world.get_entrance('Mire Hub Top Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Hub Top', player), player))
    set_rule(world.get_entrance('Mire Map Spike Side Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Map Spike Side', player), player))
    set_rule(world.get_entrance('Mire Map Spot Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Map Spot', player), player))
    set_rule(world.get_entrance('Mire Crystal Dead End Left Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Crystal Dead End', player), player))
    set_rule(world.get_entrance('Mire Crystal Dead End Right Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Crystal Dead End', player), player))
    set_rule(world.get_entrance('Mire South Fish Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire South Fish', player), player))
    set_rule(world.get_entrance('Mire Compass Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Compass Room', player), player))
    set_rule(world.get_entrance('Mire Crystal Mid Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Crystal Mid', player), player))
    set_rule(world.get_entrance('Mire Crystal Left Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('Mire Crystal Left', player), player))
    set_rule(world.get_entrance('TR Crystal Maze Blue Path', player), lambda state: state.can_reach_blue(world.get_region('TR Crystal Maze End', player), player))
    set_rule(world.get_entrance('GT Hookshot Entry Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('GT Hookshot South Entry', player), player))
    set_rule(world.get_entrance('GT Double Switch Key Blue Path', player), lambda state: state.can_reach_blue(world.get_region('GT Double Switch Key Spot', player), player))
    set_rule(world.get_entrance('GT Double Switch Blue Barrier', player), lambda state: state.can_reach_blue(world.get_region('GT Double Switch Switches', player), player))
    set_rule(world.get_entrance('GT Double Switch Transition Blue', player), lambda state: state.can_reach_blue(world.get_region('GT Double Switch Transition', player), player))

    set_rule(world.get_entrance('Swamp Barrier Ledge - Orange', player), lambda state: state.can_reach_orange(world.get_region('Swamp Barrier Ledge', player), player))
    set_rule(world.get_entrance('Swamp Barrier - Orange', player), lambda state: state.can_reach_orange(world.get_region('Swamp Barrier', player), player))
    set_rule(world.get_entrance('Thieves Hellway Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('Thieves Hellway', player), player))
    set_rule(world.get_entrance('Thieves Hellway Crystal Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('Thieves Hellway S Crystal', player), player))
    set_rule(world.get_entrance('Ice Bomb Jump Ledge Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('Ice Bomb Jump Ledge', player), player))
    set_rule(world.get_entrance('Ice Bomb Jump Catwalk Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('Ice Bomb Jump Catwalk', player), player))
    set_rule(world.get_entrance('Ice Crystal Right Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('Ice Crystal Right', player), player))
    set_rule(world.get_entrance('Ice Crystal Left Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('Ice Crystal Left', player), player))
    set_rule(world.get_entrance('Mire Crystal Right Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('Mire Crystal Right', player), player))
    set_rule(world.get_entrance('Mire Crystal Mid Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('Mire Crystal Mid', player), player))
    set_rule(world.get_entrance('Mire Firesnake Skip Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('Mire Firesnake Skip', player), player))
    set_rule(world.get_entrance('Mire Antechamber Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('Mire Antechamber', player), player))
    set_rule(world.get_entrance('GT Double Switch Orange Barrier', player), lambda state: state.can_reach_orange(world.get_region('GT Double Switch Entry', player), player))
    set_rule(world.get_entrance('GT Double Switch Orange Barrier 2', player), lambda state: state.can_reach_orange(world.get_region('GT Double Switch Entry', player), player))
    set_rule(world.get_entrance('GT Double Switch Orange Path', player), lambda state: state.can_reach_orange(world.get_region('GT Double Switch Switches', player), player))
    set_rule(world.get_entrance('GT Double Switch Key Orange Path', player), lambda state: state.can_reach_orange(world.get_region('GT Double Switch Key Spot', player), player))

    # End of door rando rules.

    add_rule(world.get_location('Sunken Treasure', player), lambda state: state.has('Open Floodgate', player))
    set_rule(world.get_location('Ganon', player), lambda state: state.has_beam_sword(player) and state.has_fire_source(player) and state.has_crystals(world.crystals_needed_for_ganon[player], player)
                                                                and (state.has('Tempered Sword', player) or state.has('Golden Sword', player) or (state.has('Silver Arrows', player) and state.can_shoot_arrows(player)) or state.has('Lamp', player) or state.can_extend_magic(player, 12)))  # need to light torch a sufficient amount of times
    set_rule(world.get_entrance('Ganon Drop', player), lambda state: state.has_beam_sword(player))  # need to damage ganon to get tiles to drop


def default_rules(world, player):
    if world.mode[player] == 'standard':
        # Links house requires reaching Sanc so skipping that chest isn't a softlock.
        world.get_region('Hyrule Castle Secret Entrance', player).can_reach_private = lambda state: True
        old_rule = world.get_region('Links House', player).can_reach_private
        world.get_region('Links House', player).can_reach_private = lambda state: state.has('Zelda Delivered', player) or old_rule(state)
    else:
        # these are default save&quit points and always accessible
        world.get_region('Links House', player).can_reach_private = lambda state: True
        world.get_region('Sanctuary', player).can_reach_private = lambda state: True

    # overworld requirements
    set_rule(world.get_entrance('Kings Grave', player), lambda state: state.has_Boots(player))
    set_rule(world.get_entrance('Kings Grave Outer Rocks', player), lambda state: state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Kings Grave Inner Rocks', player), lambda state: state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Kings Grave Mirror Spot', player), lambda state: state.has_Pearl(player) and state.has_Mirror(player))
    # Caution: If king's grave is releaxed at all to account for reaching it via a two way cave's exit in insanity mode, then the bomb shop logic will need to be updated (that would involve create a small ledge-like Region for it)
    set_rule(world.get_entrance('Bonk Fairy (Light)', player), lambda state: state.has_Boots(player))
    set_rule(world.get_entrance('Lumberjack Tree Tree', player), lambda state: state.has_Boots(player) and state.has('Beat Agahnim 1', player))
    set_rule(world.get_entrance('Bonk Rock Cave', player), lambda state: state.has_Boots(player))
    set_rule(world.get_entrance('Desert Palace Stairs', player), lambda state: state.has('Book of Mudora', player))
    set_rule(world.get_entrance('Sanctuary Grave', player), lambda state: state.can_lift_rocks(player))
    set_rule(world.get_entrance('20 Rupee Cave', player), lambda state: state.can_lift_rocks(player))
    set_rule(world.get_entrance('50 Rupee Cave', player), lambda state: state.can_lift_rocks(player))
    set_rule(world.get_entrance('Death Mountain Entrance Rock', player), lambda state: state.can_lift_rocks(player))
    set_rule(world.get_entrance('Bumper Cave Entrance Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Flute Spot 1', player), lambda state: state.has('Ocarina', player))
    set_rule(world.get_entrance('Lake Hylia Central Island Teleporter', player), lambda state: state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Dark Desert Teleporter', player), lambda state: state.has('Ocarina', player) and state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('East Hyrule Teleporter', player), lambda state: state.has('Hammer', player) and state.can_lift_rocks(player) and state.has_Pearl(player)) # bunny cannot use hammer
    set_rule(world.get_entrance('South Hyrule Teleporter', player), lambda state: state.has('Hammer', player) and state.can_lift_rocks(player) and state.has_Pearl(player)) # bunny cannot use hammer
    set_rule(world.get_entrance('Kakariko Teleporter', player), lambda state: ((state.has('Hammer', player) and state.can_lift_rocks(player)) or state.can_lift_heavy_rocks(player)) and state.has_Pearl(player)) # bunny cannot lift bushes
    set_rule(world.get_location('Flute Spot', player), lambda state: state.has('Shovel', player))

    set_rule(world.get_location('Zora\'s Ledge', player), lambda state: state.has('Flippers', player))
    set_rule(world.get_entrance('Waterfall of Wishing', player), lambda state: state.has('Flippers', player))  # can be fake flippered into, but is in weird state inside that might prevent you from doing things. Can be improved in future Todo
    set_rule(world.get_location('Frog', player), lambda state: state.can_lift_heavy_rocks(player)) # will get automatic moon pearl requirement
    set_rule(world.get_location('Potion Shop', player), lambda state: state.has('Mushroom', player))
    set_rule(world.get_entrance('Desert Palace Entrance (North) Rocks', player), lambda state: state.can_lift_rocks(player))
    set_rule(world.get_entrance('Desert Ledge Return Rocks', player), lambda state: state.can_lift_rocks(player))  # should we decide to place something that is not a dungeon end up there at some point
    set_rule(world.get_entrance('Checkerboard Cave', player), lambda state: state.can_lift_rocks(player))
    set_rule(world.get_entrance('Agahnims Tower', player), lambda state: state.has('Cape', player) or state.has_beam_sword(player) or state.has('Beat Agahnim 1', player))  # barrier gets removed after killing agahnim, relevant for entrance shuffle
    set_rule(world.get_entrance('Top of Pyramid', player), lambda state: state.has('Beat Agahnim 1', player))
    set_rule(world.get_entrance('Old Man Cave Exit (West)', player), lambda state: False)  # drop cannot be climbed up
    set_rule(world.get_entrance('Broken Bridge (West)', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Broken Bridge (East)', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('East Death Mountain Teleporter', player), lambda state: state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Fairy Ascension Rocks', player), lambda state: state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Paradox Cave Push Block Reverse', player), lambda state: state.has('Mirror', player))  # can erase block
    set_rule(world.get_entrance('Death Mountain (Top)', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_entrance('Turtle Rock Teleporter', player), lambda state: state.can_lift_heavy_rocks(player) and state.has('Hammer', player))
    set_rule(world.get_entrance('East Death Mountain (Top)', player), lambda state: state.has('Hammer', player))

    set_rule(world.get_entrance('Catfish Exit Rock', player), lambda state: state.can_lift_rocks(player))
    set_rule(world.get_entrance('Catfish Entrance Rock', player), lambda state: state.can_lift_rocks(player))
    set_rule(world.get_entrance('Northeast Dark World Broken Bridge Pass', player), lambda state: state.has_Pearl(player) and (state.can_lift_rocks(player) or state.has('Hammer', player) or state.has('Flippers', player)))
    set_rule(world.get_entrance('East Dark World Broken Bridge Pass', player), lambda state: state.has_Pearl(player) and (state.can_lift_rocks(player) or state.has('Hammer', player)))
    set_rule(world.get_entrance('South Dark World Bridge', player), lambda state: state.has('Hammer', player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Bonk Fairy (Dark)', player), lambda state: state.has_Pearl(player) and state.has_Boots(player))
    set_rule(world.get_entrance('West Dark World Gap', player), lambda state: state.has_Pearl(player) and state.has('Hookshot', player))
    set_rule(world.get_entrance('Palace of Darkness', player), lambda state: state.has_Pearl(player)) # kiki needs pearl
    set_rule(world.get_entrance('Hyrule Castle Ledge Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Hyrule Castle Main Gate', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Dark Lake Hylia Drop (East)', player), lambda state: (state.has_Pearl(player) and state.has('Flippers', player) or state.has_Mirror(player)))  # Overworld Bunny Revival
    set_rule(world.get_location('Bombos Tablet', player), lambda state: state.has('Book of Mudora', player) and state.has_beam_sword(player))
    set_rule(world.get_entrance('Dark Lake Hylia Drop (South)', player), lambda state: state.has_Pearl(player) and state.has('Flippers', player))  # ToDo any fake flipper set up?
    set_rule(world.get_entrance('Dark Lake Hylia Ledge Fairy', player), lambda state: state.has_Pearl(player)) # bomb required
    set_rule(world.get_entrance('Dark Lake Hylia Ledge Spike Cave', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Dark Lake Hylia Teleporter', player), lambda state: state.has_Pearl(player) and (state.has('Hammer', player) or state.can_lift_rocks(player)))  # Fake Flippers
    set_rule(world.get_entrance('Village of Outcasts Heavy Rock', player), lambda state: state.has_Pearl(player) and state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Hype Cave', player), lambda state: state.has_Pearl(player)) # bomb required
    set_rule(world.get_entrance('Brewery', player), lambda state: state.has_Pearl(player)) # bomb required
    set_rule(world.get_entrance('Thieves Town', player), lambda state: state.has_Pearl(player)) # bunny cannot pull
    set_rule(world.get_entrance('Skull Woods First Section Hole (North)', player), lambda state: state.has_Pearl(player)) # bunny cannot lift bush
    set_rule(world.get_entrance('Skull Woods Second Section Hole', player), lambda state: state.has_Pearl(player)) # bunny cannot lift bush
    set_rule(world.get_entrance('Maze Race Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Cave 45 Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Bombos Tablet Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('East Dark World Bridge', player), lambda state: state.has_Pearl(player) and state.has('Hammer', player))
    set_rule(world.get_entrance('Lake Hylia Island Mirror Spot', player), lambda state: state.has_Pearl(player) and state.has_Mirror(player) and state.has('Flippers', player))
    set_rule(world.get_entrance('Lake Hylia Central Island Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('East Dark World River Pier', player), lambda state: state.has_Pearl(player) and state.has('Flippers', player))  # ToDo any fake flipper set up?
    set_rule(world.get_entrance('Graveyard Ledge Mirror Spot', player), lambda state: state.has_Pearl(player) and state.has_Mirror(player))
    set_rule(world.get_entrance('Bumper Cave Entrance Rock', player), lambda state: state.has_Pearl(player) and state.can_lift_rocks(player))
    set_rule(world.get_entrance('Bumper Cave Ledge Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Bat Cave Drop Ledge Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Dark World Hammer Peg Cave', player), lambda state: state.has_Pearl(player) and state.has('Hammer', player))
    set_rule(world.get_entrance('Village of Outcasts Eastern Rocks', player), lambda state: state.has_Pearl(player) and state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Peg Area Rocks', player), lambda state: state.has_Pearl(player) and state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Village of Outcasts Pegs', player), lambda state: state.has_Pearl(player) and state.has('Hammer', player))
    set_rule(world.get_entrance('Grassy Lawn Pegs', player), lambda state: state.has_Pearl(player) and state.has('Hammer', player))
    set_rule(world.get_entrance('Bumper Cave Exit (Top)', player), lambda state: state.has('Cape', player))
    set_rule(world.get_entrance('Bumper Cave Exit (Bottom)', player), lambda state: state.has('Cape', player) or state.has('Hookshot', player))

    set_rule(world.get_entrance('Skull Woods Final Section', player), lambda state: state.has('Fire Rod', player) and state.has_Pearl(player)) # bunny cannot use fire rod
    set_rule(world.get_entrance('Misery Mire', player), lambda state: state.has_Pearl(player) and state.has_sword(player) and state.has_misery_mire_medallion(player))  # sword required to cast magic (!)
    set_rule(world.get_entrance('Desert Ledge (Northeast) Mirror Spot', player), lambda state: state.has_Mirror(player))

    set_rule(world.get_entrance('Desert Ledge Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Desert Palace Stairs Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Desert Palace Entrance (North) Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Spectacle Rock Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Hookshot Cave', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))

    set_rule(world.get_entrance('East Death Mountain (Top) Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Mimic Cave Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Spiral Cave Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Fairy Ascension Mirror Spot', player), lambda state: state.has_Mirror(player) and state.has_Pearl(player))  # need to lift flowers
    set_rule(world.get_entrance('Isolated Ledge Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Superbunny Cave Exit (Bottom)', player), lambda state: False)  # Cannot get to bottom exit from top. Just exists for shuffling
    set_rule(world.get_entrance('Floating Island Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Turtle Rock', player), lambda state: state.has_Pearl(player) and state.has_sword(player) and state.has_turtle_rock_medallion(player) and state.can_reach('Turtle Rock (Top)', 'Region', player))  # sword required to cast magic (!)

    set_rule(world.get_entrance('Pyramid Hole', player), lambda state: state.has('Beat Agahnim 2', player) or world.open_pyramid[player])
    set_rule(world.get_entrance('Ganons Tower', player), lambda state: False) # This is a safety for the TR function below to not require GT entrance in its key logic.

    if world.swords[player] == 'swordless':
        swordless_rules(world, player)

    set_rule(world.get_entrance('Ganons Tower', player), lambda state: state.has_crystals(world.crystals_needed_for_gt[player], player))


def forbid_overworld_glitches(world, player):
    for exit in OWGSets.get_boots_clip_exits_lw(world.mode[player] == 'inverted'):
        set_rule(world.get_entrance(exit, player), lambda state: False)
    for exit in OWGSets.get_boots_clip_exits_dw(world.mode[player] == 'inverted'):
        set_rule(world.get_entrance(exit, player), lambda state: False)
    for exit in OWGSets.get_glitched_speed_drops_dw():
        set_rule(world.get_entrance(exit, player), lambda state: False)
    if world.mode[player] != 'inverted':
        for exit in OWGSets.get_mirror_clip_spots_dw():
            set_rule(world.get_entrance(exit, player), lambda state: False)


def inverted_rules(world, player):
    # s&q regions. link's house entrance is set to true so the filler knows the chest inside can always be reached
    world.get_region('Inverted Links House', player).can_reach_private = lambda state: True
    world.get_region('Inverted Links House', player).entrances[0].can_reach = lambda state: True
    world.get_region('Inverted Dark Sanctuary', player).entrances[0].parent_region.can_reach_private = lambda state: True

    old_rule = world.get_region('Hyrule Castle Ledge', player).can_reach_private
    world.get_region('Hyrule Castle Ledge', player).can_reach_private = lambda state: (state.has_Mirror(player) and state.has('Beat Agahnim 1', player) and state.can_reach_light_world(player)) or old_rule(state)

    # overworld requirements 
    set_rule(world.get_location('Maze Race', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Mini Moldorm Cave', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Light Hype Fairy', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Potion Shop Pier', player), lambda state: state.has('Flippers', player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Light World Pier', player), lambda state: state.has('Flippers', player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Kings Grave', player), lambda state: state.has_Boots(player) and state.can_lift_heavy_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Kings Grave Outer Rocks', player), lambda state: state.can_lift_heavy_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Kings Grave Inner Rocks', player), lambda state: state.can_lift_heavy_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Potion Shop Inner Bushes', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Potion Shop Outer Bushes', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Potion Shop Outer Rock', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Potion Shop Inner Rock', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Graveyard Cave Inner Bushes', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Graveyard Cave Outer Bushes', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Secret Passage Inner Bushes', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Secret Passage Outer Bushes', player), lambda state: state.has_Pearl(player))
    # Caution: If king's grave is releaxed at all to account for reaching it via a two way cave's exit in insanity mode, then the bomb shop logic will need to be updated (that would involve create a small ledge-like Region for it)
    set_rule(world.get_entrance('Bonk Fairy (Light)', player), lambda state: state.has_Boots(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Bat Cave Drop Ledge', player), lambda state: state.has('Hammer', player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Lumberjack Tree Tree', player), lambda state: state.has_Boots(player) and state.has_Pearl(player) and state.has('Beat Agahnim 1', player))
    set_rule(world.get_entrance('Bonk Rock Cave', player), lambda state: state.has_Boots(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Desert Palace Stairs', player), lambda state: state.has('Book of Mudora', player))  # bunny can use book
    set_rule(world.get_entrance('Sanctuary Grave', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('20 Rupee Cave', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('50 Rupee Cave', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Death Mountain Entrance Rock', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Bumper Cave Entrance Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Lake Hylia Central Island Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Dark Lake Hylia Central Island Teleporter', player), lambda state: state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Dark Desert Teleporter', player), lambda state: state.can_flute(player) and state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('East Dark World Teleporter', player), lambda state: state.has('Hammer', player) and state.can_lift_rocks(player) and state.has_Pearl(player)) # bunny cannot use hammer
    set_rule(world.get_entrance('South Dark World Teleporter', player), lambda state: state.has('Hammer', player) and state.can_lift_rocks(player) and state.has_Pearl(player)) # bunny cannot use hammer
    set_rule(world.get_entrance('West Dark World Teleporter', player), lambda state: ((state.has('Hammer', player) and state.can_lift_rocks(player)) or state.can_lift_heavy_rocks(player)) and state.has_Pearl(player))
    set_rule(world.get_location('Flute Spot', player), lambda state: state.has('Shovel', player) and state.has_Pearl(player))

    set_rule(world.get_location('Zora\'s Ledge', player), lambda state: state.has('Flippers', player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Waterfall of Wishing', player), lambda state: state.has('Flippers', player) and state.has_Pearl(player))  # can be fake flippered into, but is in weird state inside that might prevent you from doing things. Can be improved in future Todo
    set_rule(world.get_location('Frog', player), lambda state: state.can_lift_heavy_rocks(player) or (state.can_reach('Light World', 'Region', player) and state.has_Mirror(player)))
    set_rule(world.get_location('Mushroom', player), lambda state: state.has_Pearl(player)) # need pearl to pick up bushes
    set_rule(world.get_entrance('Bush Covered Lawn Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Bush Covered Lawn Inner Bushes', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Bush Covered Lawn Outer Bushes', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Bomb Hut Inner Bushes', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Bomb Hut Outer Bushes', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('North Fairy Cave Drop', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Lost Woods Hideout Drop', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_location('Potion Shop', player), lambda state: state.has('Mushroom', player) and (state.can_reach('Potion Shop Area', 'Region', player))) # new inverted region, need pearl for bushes or access to potion shop door/waterfall fairy
    set_rule(world.get_entrance('Desert Palace Entrance (North) Rocks', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Desert Ledge Return Rocks', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))  # should we decide to place something that is not a dungeon end up there at some point
    set_rule(world.get_entrance('Checkerboard Cave', player), lambda state: state.can_lift_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Hyrule Castle Secret Entrance Drop', player), lambda state: state.has_Pearl(player))
    set_rule(world.get_entrance('Old Man Cave Exit (West)', player), lambda state: False)  # drop cannot be climbed up
    set_rule(world.get_entrance('Broken Bridge (West)', player), lambda state: state.has('Hookshot', player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Broken Bridge (East)', player), lambda state: state.has('Hookshot', player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Dark Death Mountain Teleporter (East Bottom)', player), lambda state: state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Fairy Ascension Rocks', player), lambda state: state.can_lift_heavy_rocks(player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Paradox Cave Push Block Reverse', player), lambda state: state.has('Mirror', player))  # can erase block
    set_rule(world.get_entrance('Death Mountain (Top)', player), lambda state: state.has('Hammer', player) and state.has_Pearl(player))
    set_rule(world.get_entrance('Dark Death Mountain Teleporter (East)', player), lambda state: state.can_lift_heavy_rocks(player) and state.has('Hammer', player) and state.has_Pearl(player))  # bunny cannot use hammer
    set_rule(world.get_entrance('East Death Mountain (Top)', player), lambda state: state.has('Hammer', player) and state.has_Pearl(player))  # bunny can not use hammer

    set_rule(world.get_location('Catfish', player), lambda state: state.can_lift_rocks(player) or (state.has('Flippers', player) and state.has_Mirror(player) and state.has_Pearl(player) and state.can_reach('Light World', 'Region', player)))
    set_rule(world.get_entrance('Northeast Dark World Broken Bridge Pass', player), lambda state: ((state.can_lift_rocks(player) or state.has('Hammer', player)) or state.has('Flippers', player)))
    set_rule(world.get_entrance('East Dark World Broken Bridge Pass', player), lambda state: (state.can_lift_rocks(player) or state.has('Hammer', player)))
    set_rule(world.get_entrance('South Dark World Bridge', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_entrance('Bonk Fairy (Dark)', player), lambda state: state.has_Boots(player))
    set_rule(world.get_entrance('West Dark World Gap', player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Dark Lake Hylia Drop (East)', player), lambda state: state.has('Flippers', player))
    set_rule(world.get_location('Bombos Tablet', player), lambda state: state.has('Book of Mudora', player) and state.has_beam_sword(player))
    set_rule(world.get_entrance('Dark Lake Hylia Drop (South)', player), lambda state: state.has('Flippers', player))  # ToDo any fake flipper set up?
    set_rule(world.get_entrance('Dark Lake Hylia Ledge Pier', player), lambda state: state.has('Flippers', player))
    set_rule(world.get_entrance('Dark Lake Hylia Ledge Spike Cave', player), lambda state: state.can_lift_rocks(player))
    set_rule(world.get_entrance('Dark Lake Hylia Teleporter', player), lambda state: state.has('Flippers', player) and (state.has('Hammer', player) or state.can_lift_rocks(player)))  # Fake Flippers
    set_rule(world.get_entrance('Village of Outcasts Heavy Rock', player), lambda state: state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('East Dark World Bridge', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_entrance('Lake Hylia Central Island Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('East Dark World River Pier', player), lambda state: state.has('Flippers', player))  # ToDo any fake flipper set up? (Qirn Jump)
    set_rule(world.get_entrance('Bumper Cave Entrance Rock', player), lambda state: state.can_lift_rocks(player))
    set_rule(world.get_entrance('Bumper Cave Ledge Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Hammer Peg Area Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Dark World Hammer Peg Cave', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_entrance('Village of Outcasts Eastern Rocks', player), lambda state: state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Peg Area Rocks', player), lambda state: state.can_lift_heavy_rocks(player))
    set_rule(world.get_entrance('Village of Outcasts Pegs', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_entrance('Grassy Lawn Pegs', player), lambda state: state.has('Hammer', player))
    set_rule(world.get_entrance('Bumper Cave Exit (Top)', player), lambda state: state.has('Cape', player))
    set_rule(world.get_entrance('Bumper Cave Exit (Bottom)', player), lambda state: state.has('Cape', player) or state.has('Hookshot', player))

    set_rule(world.get_entrance('Skull Woods Final Section', player), lambda state: state.has('Fire Rod', player)) 
    set_rule(world.get_entrance('Misery Mire', player), lambda state: state.has_sword(player) and state.has_misery_mire_medallion(player))  # sword required to cast magic (!)

    set_rule(world.get_entrance('Hookshot Cave', player), lambda state: state.can_lift_rocks(player))

    set_rule(world.get_entrance('East Death Mountain Mirror Spot (Top)', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Death Mountain (Top) Mirror Spot', player), lambda state: state.has_Mirror(player))

    set_rule(world.get_entrance('East Death Mountain Mirror Spot (Bottom)', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Dark Death Mountain Ledge Mirror Spot (East)', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Dark Death Mountain Ledge Mirror Spot (West)', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Laser Bridge Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Superbunny Cave Exit (Bottom)', player), lambda state: False)  # Cannot get to bottom exit from top. Just exists for shuffling
    set_rule(world.get_entrance('Floating Island Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Turtle Rock', player), lambda state: state.has_sword(player) and state.has_turtle_rock_medallion(player) and state.can_reach('Turtle Rock (Top)', 'Region', player)) # sword required to cast magic (!)
    
    # new inverted spots
    set_rule(world.get_entrance('Post Aga Teleporter', player), lambda state: state.has('Beat Agahnim 1', player))
    set_rule(world.get_entrance('Mire Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Desert Palace Stairs Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Death Mountain Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('East Dark World Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('West Dark World Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('South Dark World Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Northeast Dark World Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Potion Shop Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Shopping Mall Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Maze Race Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Desert Palace North Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Death Mountain (Top) Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Graveyard Cave Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Bomb Hut Mirror Spot', player), lambda state: state.has_Mirror(player))
    set_rule(world.get_entrance('Skull Woods Mirror Spot', player), lambda state: state.has_Mirror(player))
    
    # inverted flute spots

    set_rule(world.get_entrance('DDM Flute', player), lambda state: state.can_flute(player))
    set_rule(world.get_entrance('NEDW Flute', player), lambda state: state.can_flute(player))
    set_rule(world.get_entrance('WDW Flute', player), lambda state: state.can_flute(player))
    set_rule(world.get_entrance('SDW Flute', player), lambda state: state.can_flute(player))
    set_rule(world.get_entrance('EDW Flute', player), lambda state: state.can_flute(player))
    set_rule(world.get_entrance('DLHL Flute', player), lambda state: state.can_flute(player))
    set_rule(world.get_entrance('DD Flute', player), lambda state: state.can_flute(player))
    set_rule(world.get_entrance('EDDM Flute', player), lambda state: state.can_flute(player))
    set_rule(world.get_entrance('Dark Grassy Lawn Flute', player), lambda state: state.can_flute(player))
    set_rule(world.get_entrance('Hammer Peg Area Flute', player), lambda state: state.can_flute(player))
    
    set_rule(world.get_entrance('Inverted Pyramid Hole', player), lambda state: state.has('Beat Agahnim 2', player) or world.open_pyramid[player])
    set_rule(world.get_entrance('Inverted Ganons Tower', player), lambda state: False) # This is a safety for the TR function below to not require GT entrance in its key logic.

    if world.swords[player] == 'swordless':
        swordless_rules(world, player)

    set_rule(world.get_entrance('Inverted Ganons Tower', player), lambda state: state.has_crystals(world.crystals_needed_for_gt[player], player))

def no_glitches_rules(world, player):
    if world.mode[player] != 'inverted':
        add_rule(world.get_entrance('Zoras River', player), lambda state: state.has('Flippers', player) or state.can_lift_rocks(player))
        add_rule(world.get_entrance('Lake Hylia Central Island Pier', player), lambda state: state.has('Flippers', player))  # can be fake flippered to
        add_rule(world.get_entrance('Hobo Bridge', player), lambda state: state.has('Flippers', player))
        add_rule(world.get_entrance('Dark Lake Hylia Drop (East)', player), lambda state: state.has_Pearl(player) and state.has('Flippers', player))
        add_rule(world.get_entrance('Dark Lake Hylia Teleporter', player), lambda state: state.has_Pearl(player) and state.has('Flippers', player) and (state.has('Hammer', player) or state.can_lift_rocks(player)))
        add_rule(world.get_entrance('Dark Lake Hylia Ledge Drop', player), lambda state: state.has_Pearl(player) and state.has('Flippers', player))
    else:
        add_rule(world.get_entrance('Zoras River', player), lambda state: state.has_Pearl(player) and (state.has('Flippers', player) or state.can_lift_rocks(player)))
        add_rule(world.get_entrance('Lake Hylia Central Island Pier', player), lambda state: state.has_Pearl(player) and state.has('Flippers', player))  # can be fake flippered to
        add_rule(world.get_entrance('Lake Hylia Island', player), lambda state: state.has_Pearl(player) and state.has('Flippers', player))
        add_rule(world.get_entrance('Hobo Bridge', player), lambda state: state.has_Pearl(player) and state.has('Flippers', player))
        add_rule(world.get_entrance('Dark Lake Hylia Drop (East)', player), lambda state: state.has('Flippers', player))
        add_rule(world.get_entrance('Dark Lake Hylia Teleporter', player), lambda state: state.has('Flippers', player) and (state.has('Hammer', player) or state.can_lift_rocks(player)))
        add_rule(world.get_entrance('Dark Lake Hylia Ledge Drop', player), lambda state: state.has('Flippers', player))
        add_rule(world.get_entrance('East Dark World Pier', player), lambda state: state.has('Flippers', player))
        set_rule(world.get_entrance('Bat Cave Drop Ledge', player), lambda state: state.has('Hammer', player))

    # todo: move some dungeon rules to no glictes logic - see these for examples
    # add_rule(world.get_entrance('Ganons Tower (Hookshot Room)', player), lambda state: state.has('Hookshot', player) or state.has_Boots(player))
    # add_rule(world.get_entrance('Ganons Tower (Double Switch Room)', player), lambda state: state.has('Hookshot', player))
    # DMs_room_chests = ['Ganons Tower - DMs Room - Top Left', 'Ganons Tower - DMs Room - Top Right', 'Ganons Tower - DMs Room - Bottom Left', 'Ganons Tower - DMs Room - Bottom Right']
    # for location in DMs_room_chests:
    #     add_rule(world.get_location(location, player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Paradox Cave Push Block Reverse', player), lambda state: False)  # no glitches does not require block override
    forbid_bomb_jump_requirements(world, player)
    forbid_overworld_glitches(world, player)
    add_conditional_lamps(world, player)


def forbid_bomb_jump_requirements(world, player):
    DMs_room_chests = ['Ganons Tower - DMs Room - Top Left', 'Ganons Tower - DMs Room - Top Right', 'Ganons Tower - DMs Room - Bottom Left', 'Ganons Tower - DMs Room - Bottom Right']
    for location in DMs_room_chests:
        add_rule(world.get_location(location, player), lambda state: state.has('Hookshot', player))
    set_rule(world.get_entrance('Paradox Cave Bomb Jump', player), lambda state: False)


DW_Entrances = ['Bumper Cave (Bottom)',
                'Superbunny Cave (Top)',
                'Superbunny Cave (Bottom)',
                'Hookshot Cave',
                'Bumper Cave (Top)',
                'Hookshot Cave Back Entrance',
                'Dark Death Mountain Ledge (East)',
                'Turtle Rock Isolated Ledge Entrance',
                'Thieves Town',
                'Skull Woods Final Section',
                'Ice Palace',
                'Misery Mire',
                'Palace of Darkness',
                'Swamp Palace',
                'Turtle Rock',
                'Dark Death Mountain Ledge (West)']

def check_is_dark_world(region):
    for entrance in region.entrances:
        if entrance.name in DW_Entrances:
            return True
    return False


def add_conditional_lamps(world, player):
    # Light cones in standard depend on which world we actually are in, not which one the location would normally be
    # We add Lamp requirements only to those locations which lie in the dark world (or everything if open

    def add_conditional_lamp(spot, region, spottype='Location'):
        if spottype == 'Location':
            spot = world.get_location(spot, player)
        else:
            spot = world.get_entrance(spot, player)
        if (not world.dark_world_light_cone and check_is_dark_world(world.get_region(region, player))) or (not world.light_world_light_cone and not check_is_dark_world(world.get_region(region, player))):
            add_lamp_requirement(spot, player)

    dark_rooms = {
        'TR Dark Ride': {'sewer': False, 'entrances': ['TR Dark Ride Up Stairs', 'TR Dark Ride SW'], 'locations': []},
        'Mire Dark Shooters': {'sewer': False, 'entrances': ['Mire Dark Shooters Up Stairs', 'Mire Dark Shooters SW', 'Mire Dark Shooters SE'], 'locations': []},
        'Mire Key Rupees': {'sewer': False, 'entrances': ['Mire Key Rupees NE'], 'locations': []},
        'Mire Block X': {'sewer': False, 'entrances': ['Mire Block X NW', 'Mire Block X WS'], 'locations': []},
        'Mire Tall Dark and Roomy': {'sewer': False, 'entrances': ['Mire Tall Dark and Roomy ES', 'Mire Tall Dark and Roomy WS', 'Mire Tall Dark and Roomy WN'], 'locations': []},
        'Mire Crystal Right': {'sewer': False, 'entrances': ['Mire Crystal Right ES'], 'locations': []},
        'Mire Crystal Mid': {'sewer': False, 'entrances': ['Mire Crystal Mid NW'], 'locations': []},
        'Mire Crystal Left': {'sewer': False, 'entrances': ['Mire Crystal Left WS'], 'locations': []},
        'Mire Crystal Top': {'sewer': False, 'entrances': ['Mire Crystal Top SW'], 'locations': []},
        'Mire Shooter Rupees': {'sewer': False, 'entrances': ['Mire Shooter Rupees EN'], 'locations': []},
        'PoD Dark Alley': {'sewer': False, 'entrances': ['PoD Dark Alley NE'], 'locations': []},
        'PoD Callback': {'sewer': False, 'entrances': ['PoD Callback WS', 'PoD Callback Warp'], 'locations': []},
        'PoD Turtle Party': {'sewer': False, 'entrances': ['PoD Turtle Party ES', 'PoD Turtle Party NW'], 'locations': []},
        'PoD Lonely Turtle': {'sewer': False, 'entrances': ['PoD Lonely Turtle SW', 'PoD Lonely Turtle EN'], 'locations': []},
        'PoD Dark Pegs': {'sewer': False, 'entrances': ['PoD Dark Pegs Up Ladder', 'PoD Dark Pegs WN'], 'locations': []},
        'PoD Dark Basement': {'sewer': False, 'entrances': ['PoD Dark Basement W Up Stairs', 'PoD Dark Basement E Up Stairs'], 'locations': ['Palace of Darkness - Dark Basement - Left', 'Palace of Darkness - Dark Basement - Right']},
        'PoD Dark Maze': {'sewer': False, 'entrances': ['PoD Dark Maze EN', 'PoD Dark Maze E'], 'locations': ['Palace of Darkness - Dark Maze - Top', 'Palace of Darkness - Dark Maze - Bottom']},
        'Eastern Dark Square': {'sewer': False, 'entrances': ['Eastern Dark Square NW', 'Eastern Dark Square Key Door WN', 'Eastern Dark Square EN'], 'locations': []},
        'Eastern Dark Pots': {'sewer': False, 'entrances': ['Eastern Dark Pots WN'], 'locations': ['Eastern Palace - Dark Square Pot Key']},
        'Eastern Darkness': {'sewer': False, 'entrances': ['Eastern Darkness S', 'Eastern Darkness Up Stairs', 'Eastern Darkness NE'], 'locations': ['Eastern Palace - Dark Eyegore Key Drop']},
        'Eastern Rupees': {'sewer': False, 'entrances': ['Eastern Rupees SE'], 'locations': []},
        'Tower Lone Statue': {'sewer': False, 'entrances': ['Tower Lone Statue Down Stairs', 'Tower Lone Statue WN'], 'locations': []},
        'Tower Dark Maze': {'sewer': False, 'entrances': ['Tower Dark Maze EN', 'Tower Dark Maze ES'], 'locations': ['Castle Tower - Dark Maze']},
        'Tower Dark Chargers': {'sewer': False, 'entrances': ['Tower Dark Chargers WS', 'Tower Dark Chargers Up Stairs'], 'locations': []},
        'Tower Dual Statues': {'sewer': False, 'entrances': ['Tower Dual Statues Down Stairs', 'Tower Dual Statues WS'], 'locations': []},
        'Tower Dark Pits': {'sewer': False, 'entrances': ['Tower Dark Pits ES', 'Tower Dark Pits EN'], 'locations': []},
        'Tower Dark Archers': {'sewer': False, 'entrances': ['Tower Dark Archers WN', 'Tower Dark Archers Up Stairs'], 'locations': ['Castle Tower - Dark Archer Key Drop']},
        'Sewers Dark Cross': {'sewer': True, 'entrances': ['Sewers Dark Cross Key Door N', 'Sewers Dark Cross South Stairs'], 'locations': ['Sewers - Dark Cross']},
        'Sewers Behind Tapestry': {'sewer': True, 'entrances': ['Sewers Behind Tapestry S', 'Sewers Behind Tapestry Down Stairs'], 'locations': []},
        'Sewers Rope Room': {'sewer': True, 'entrances': ['Sewers Rope Room Up Stairs', 'Sewers Rope Room North Stairs'], 'locations': []},
        'Sewers Water': {'sewer': True, 'entrances': ['Sewers Water S', 'Sewers Water W'], 'locations': []},
        'Sewers Key Rat': {'sewer': True, 'entrances': ['Sewers Key Rat E', 'Sewers Key Rat Key Door N'], 'locations': ['Hyrule Castle - Key Rat Key Drop']},
    }

    dark_debug_set = set()
    for region, info in dark_rooms.items():
        is_dark = False
        if not world.sewer_light_cone[player]:
            is_dark = True
        elif world.doorShuffle[player] != 'crossed' and not info['sewer']:
            is_dark = True
        elif world.doorShuffle[player] == 'crossed':
            sewer_builder = world.dungeon_layouts[player]['Hyrule Castle']
            is_dark = region not in sewer_builder.master_sector.region_set()
        if is_dark:
            dark_debug_set.add(region)
            for ent in info['entrances']:
                add_conditional_lamp(ent, region, 'Entrance')
            for loc in info['locations']:
                add_conditional_lamp(loc, region, 'Location')
    logging.getLogger('').debug('Non Dark Regions: ' + ', '.join(set(dark_rooms.keys()).difference(dark_debug_set)))

    add_conditional_lamp('Old Man', 'Old Man Cave', 'Location')
    add_conditional_lamp('Old Man Cave Exit (East)', 'Old Man Cave', 'Entrance')
    add_conditional_lamp('Death Mountain Return Cave Exit (East)', 'Death Mountain Return Cave', 'Entrance')
    add_conditional_lamp('Death Mountain Return Cave Exit (West)', 'Death Mountain Return Cave', 'Entrance')
    add_conditional_lamp('Old Man House Front to Back', 'Old Man House', 'Entrance')
    add_conditional_lamp('Old Man House Back to Front', 'Old Man House', 'Entrance')


def overworld_glitches_rules(world, player):
    # Spots that are immediately accessible.
    for entrance in OWGSets.get_immediately_accessible_entrances(world, player):
        set_rule(world.get_entrance(entrance, player), lambda state: True)

    # Boots-accessible locations.
    for entrance in OWGSets.get_boots_clip_exits_lw(world.mode[player] == 'inverted'):
        set_rule(world.get_entrance(entrance, player), lambda state: state.can_boots_clip_lw(player))
    for entrance in OWGSets.get_boots_clip_exits_dw(world.mode[player] == 'inverted'):
        set_rule(world.get_entrance(entrance, player), lambda state: state.can_boots_clip_dw(player))

    # Glitched speed drops.
    for drop in OWGSets.get_glitched_speed_drops_dw():
        set_rule(world.get_entrance(drop, player), lambda state: state.can_get_glitched_speed_dw(player))
    # Dark Death Mountain Ledge Clip Spot also accessible with mirror.
    if world.mode[player] != 'inverted':
        add_rule(world.get_entrance('Dark Death Mountain Ledge Clip Spot', player), lambda state: state.has_Mirror(player), 'or')

    # Mirror clip spots.
    if world.mode[player] != 'inverted':
        for clip_spot in OWGSets.get_mirror_clip_spots_dw():
            set_rule(world.get_entrance(clip_spot, player), lambda state: state.has_Mirror(player))
    else:
        for clip_spot in OWGSets.get_mirror_clip_spots_lw():
            set_rule(world.get_entrance(clip_spot, player), lambda state: state.has_Mirror(player))

    # Locations that you can superbunny mirror into, but need a sword to clear.
    for superbunny_mirror_weapon_region in OWGSets.get_sword_required_superbunny_mirror_regions():
        region = world.get_region(superbunny_mirror_weapon_region, player)
        if check_is_dark_world(region):
            for spot in region.locations:
                add_rule(world.get_location(spot, player), lambda state: state.can_superbunny_mirror_with_sword(player), 'or')

    # Regions that require the boots and some other stuff.
    if world.mode[player] != 'inverted':
        set_rule(world.get_entrance('Dark Desert Teleporter', player), lambda state: state.has('Ocarina', player) or (state.can_boots_clip_dw(player) and state.can_lift_heavy_rocks(player)))
        set_rule(world.get_entrance('Turtle Rock Teleporter', player), lambda state: (state.can_boots_clip_dw(player) or state.can_lift_heavy_rocks(player)) and state.has('Hammer', player))
        add_rule(world.get_entrance('Catfish Exit Rock', player), lambda state: state.can_boots_clip_dw(player), 'or')
        add_rule(world.get_entrance('East Dark World Broken Bridge Pass', player), lambda state: state.can_boots_clip_dw(player), 'or')
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.can_reach('Dark Death Mountain (West Bottom)', 'Region', player) and state.has_Mirror(player))
    else:
        add_rule(world.get_entrance('South Dark World Teleporter', player), lambda state: state.has_Boots(player) and state.can_lift_rocks(player), 'or')

    # Zora's Ledge via waterwalk setup.
    add_rule(world.get_location('Zora\'s Ledge', player), lambda state: state.has_Boots(player), 'or')


def open_rules(world, player):
    # softlock protection as you can reach the sewers small key door with a guard drop key
    set_rule(world.get_location('Hyrule Castle - Boomerang Chest', player), lambda state: state.has_key('Small Key (Escape)', player))
    set_rule(world.get_location('Hyrule Castle - Zelda\'s Chest', player), lambda state: state.has_key('Small Key (Escape)', player))


def swordless_rules(world, player):

    set_rule(world.get_entrance('Tower Altar NW', player), lambda state: True)
    set_rule(world.get_entrance('Skull Vines NW', player), lambda state: True)
    set_rule(world.get_entrance('Ice Lobby WS', player), lambda state: state.has('Fire Rod', player) or state.has('Bombos', player))
    set_rule(world.get_location('Ice Palace - Freezor Chest', player), lambda state: state.has('Fire Rod', player) or state.has('Bombos', player))

    set_rule(world.get_location('Ether Tablet', player), lambda state: state.has('Book of Mudora', player) and state.has('Hammer', player))
    set_rule(world.get_location('Ganon', player), lambda state: state.has('Hammer', player) and state.has_fire_source(player) and state.has('Silver Arrows', player) and state.can_shoot_arrows(player) and state.has_crystals(world.crystals_needed_for_ganon[player], player))
    set_rule(world.get_entrance('Ganon Drop', player), lambda state: state.has('Hammer', player))  # need to damage ganon to get tiles to drop

    if world.mode[player] != 'inverted':
        set_rule(world.get_entrance('Agahnims Tower', player), lambda state: state.has('Cape', player) or state.has('Hammer', player) or state.has('Beat Agahnim 1', player))  # barrier gets removed after killing agahnim, relevant for entrance shuffle
        set_rule(world.get_entrance('Turtle Rock', player), lambda state: state.has_Pearl(player) and state.has_turtle_rock_medallion(player) and state.can_reach('Turtle Rock (Top)', 'Region', player))   # sword not required to use medallion for opening in swordless (!)
        set_rule(world.get_entrance('Misery Mire', player), lambda state: state.has_Pearl(player) and state.has_misery_mire_medallion(player))  # sword not required to use medallion for opening in swordless (!)
        set_rule(world.get_location('Bombos Tablet', player), lambda state: state.has('Book of Mudora', player) and state.has('Hammer', player) and state.has_Mirror(player))    
    else:
        # only need ddm access for aga tower in inverted
        set_rule(world.get_entrance('Turtle Rock', player), lambda state: state.has_turtle_rock_medallion(player) and state.can_reach('Turtle Rock (Top)', 'Region', player))   # sword not required to use medallion for opening in swordless (!)
        set_rule(world.get_entrance('Misery Mire', player), lambda state: state.has_misery_mire_medallion(player))  # sword not required to use medallion for opening in swordless (!)
        set_rule(world.get_location('Bombos Tablet', player), lambda state: state.has('Book of Mudora', player) and state.has('Hammer', player))


std_kill_rooms = {
    'Hyrule Dungeon Armory Main': ['Hyrule Dungeon Armory S'],
    'Hyrule Dungeon Armory Boomerang': ['Hyrule Dungeon Armory Boomerang WS'],
    'Eastern Stalfos Spawn': ['Eastern Stalfos Spawn ES', 'Eastern Stalfos Spawn NW'],
    'Desert Compass Room': ['Desert Compass NW'],
    'Desert Four Statues': ['Desert Four Statues NW', 'Desert Four Statues ES'],
    'Hera Beetles': ['Hera Beetles WS'],
    'Tower Gold Knights': ['Tower Gold Knights SW', 'Tower Gold Knights EN'],
    'Tower Dark Archers': ['Tower Dark Archers WN'],
    'Tower Red Spears': ['Tower Red Spears WN'],
    'Tower Red Guards': ['Tower Red Guards EN', 'Tower Red Guards SW'],
    'Tower Circle of Pots': ['Tower Circle of Pots NW'],
    'PoD Turtle Party': ['PoD Turtle Party ES', 'PoD Turtle Party NW'],  # todo: hammer req. in main rules
    'Thieves Basement Block': ['Thieves Basement Block WN'],
    'Ice Stalfos Hint': ['Ice Stalfos Hint SE'],
    'Ice Pengator Trap': ['Ice Pengator Trap NE'],
    'Mire 2': ['Mire 2 NE'],
    'Mire Cross': ['Mire Cross ES'],
    'TR Twin Pokeys': ['TR Twin Pokeys EN', 'TR Twin Pokeys SW'],
    'GT Petting Zoo': ['GT Petting Zoo SE'],
    'GT DMs Room': ['GT DMs Room SW'],
    'GT Gauntlet 1': ['GT Gauntlet 1 WN'],
    'GT Gauntlet 2': ['GT Gauntlet 2 EN', 'GT Gauntlet 2 SW'],
    'GT Gauntlet 3': ['GT Gauntlet 3 NW', 'GT Gauntlet 3 SW'],
    'GT Gauntlet 4': ['GT Gauntlet 4 NW', 'GT Gauntlet 4 SW'],
    'GT Gauntlet 5': ['GT Gauntlet 5 NW', 'GT Gauntlet 5 WS'],
    'GT Wizzrobes 1': ['GT Wizzrobes 1 SW'],
    'GT Wizzrobes 2': ['GT Wizzrobes 2 SE', 'GT Wizzrobes 2 NE']
}  # all trap rooms?


def standard_rules(world, player):
    # these are because of rails
    if world.shuffle[player] != 'vanilla':
        set_rule(world.get_entrance('Hyrule Castle Exit (East)', player), lambda state: state.has('Zelda Delivered', player))
        set_rule(world.get_entrance('Hyrule Castle Exit (West)', player), lambda state: state.has('Zelda Delivered', player))

    # too restrictive for crossed?
    def uncle_item_rule(item):
        copy_state = CollectionState(world)
        copy_state.collect(item)
        copy_state.sweep_for_events()
        return copy_state.has('Zelda Delivered', player)

    add_item_rule(world.get_location('Link\'s Uncle', player), uncle_item_rule)

    # ensures the required weapon for escape lands on uncle (unless player has it pre-equipped)
    for location in ['Link\'s House', 'Sanctuary', 'Sewers - Secret Room - Left', 'Sewers - Secret Room - Middle',
                     'Sewers - Secret Room - Right']:
        add_rule(world.get_location(location, player), lambda state: state.can_kill_most_things(player))
    add_rule(world.get_location('Secret Passage', player), lambda state: state.can_kill_most_things(player))

    escape_builder = world.dungeon_layouts[player]['Hyrule Castle']
    for region in escape_builder.master_sector.regions:
        for loc in region.locations:
            add_rule(loc, lambda state: state.can_kill_most_things(player))
        if region.name in std_kill_rooms:
            for ent in std_kill_rooms[region.name]:
                add_rule(world.get_entrance(ent, player), lambda state: state.can_kill_most_things(player))

    set_rule(world.get_location('Zelda Pickup', player), lambda state: state.has('Big Key (Escape)', player))
    set_rule(world.get_entrance('Hyrule Castle Throne Room N', player), lambda state: state.has('Zelda Herself', player))

    def check_rule_list(state, r_list):
        return True if len(r_list) <= 0 else r_list[0](state) and check_rule_list(state, r_list[1:])
    rule_list, debug_path = find_rules_for_zelda_delivery(world, player)
    set_rule(world.get_location('Zelda Drop Off', player), lambda state: state.has('Zelda Herself', player) and check_rule_list(state, rule_list))

    for location in ['Mushroom', 'Bottle Merchant', 'Flute Spot', 'Sunken Treasure', 'Purple Chest']:
        add_rule(world.get_location(location, player), lambda state: state.has('Zelda Delivered', player))

    # Bonk Fairy (Light) is a notable omission in ER shuffles/Retro
    for entrance in ['Blinds Hideout', 'Zoras River', 'Kings Grave Outer Rocks', 'Dam', 'Tavern North', 'Chicken House',
                     'Aginahs Cave', 'Sahasrahlas Hut', 'Kakariko Well Drop', 'Kakariko Well Cave', 'Blacksmiths Hut',
                     'Bat Cave Drop Ledge', 'Bat Cave Cave', 'Sick Kids House', 'Hobo Bridge',
                     'Lost Woods Hideout Drop', 'Lost Woods Hideout Stump', 'Lumberjack Tree Tree',
                     'Lumberjack Tree Cave', 'Mini Moldorm Cave', 'Ice Rod Cave', 'Lake Hylia Central Island Pier',
                     'Bonk Rock Cave', 'Library', 'Potion Shop', 'Two Brothers House (East)', 'Desert Palace Stairs',
                     'Eastern Palace', 'Master Sword Meadow', 'Sanctuary', 'Sanctuary Grave',
                     'Death Mountain Entrance Rock', 'Flute Spot 1', 'Dark Desert Teleporter', 'East Hyrule Teleporter',
                     'South Hyrule Teleporter', 'Kakariko Teleporter', 'Elder House (East)', 'Elder House (West)',
                     'North Fairy Cave', 'North Fairy Cave Drop', 'Lost Woods Gamble', 'Snitch Lady (East)',
                     'Snitch Lady (West)', 'Tavern (Front)', 'Bush Covered House', 'Light World Bomb Hut',
                     'Kakariko Shop', 'Long Fairy Cave', 'Good Bee Cave', '20 Rupee Cave', 'Cave Shop (Lake Hylia)',
                     'Waterfall of Wishing', 'Hyrule Castle Main Gate', '50 Rupee Cave',
                     'Fortune Teller (Light)', 'Lake Hylia Fairy', 'Light Hype Fairy', 'Desert Fairy',
                     'Lumberjack House', 'Lake Hylia Fortune Teller', 'Kakariko Gamble Game', 'Top of Pyramid']:
        add_rule(world.get_entrance(entrance, player), lambda state: state.has('Zelda Delivered', player))


def find_rules_for_zelda_delivery(world, player):
    # path rules for backtracking
    start_region = world.get_region('Hyrule Dungeon Cellblock', player)
    queue = deque([(start_region, [], [])])
    visited = {start_region}
    blank_state = CollectionState(world)
    while len(queue) > 0:
        region, path_rules, path = queue.popleft()
        for ext in region.exits:
            connect = ext.connected_region
            if connect and connect.type == RegionType.Dungeon and connect not in visited:
                rule = ext.access_rule
                rule_list = list(path_rules)
                next_path = list(path)
                if not rule(blank_state):
                    rule_list.append(rule)
                    next_path.append(ext.name)
                if connect.name == 'Sanctuary':
                    return rule_list, next_path
                else:
                    visited.add(connect)
                    queue.append((connect, rule_list, next_path))
    raise Exception('No path to Sanctuary found')


def set_big_bomb_rules(world, player):
    # this is a mess
    bombshop_entrance = world.get_region('Big Bomb Shop', player).entrances[0]
    Normal_LW_entrances = ['Blinds Hideout',
                           'Bonk Fairy (Light)',
                           'Lake Hylia Fairy',
                           'Light Hype Fairy',
                           'Desert Fairy',
                           'Chicken House',
                           'Aginahs Cave',
                           'Sahasrahlas Hut',
                           'Cave Shop (Lake Hylia)',
                           'Blacksmiths Hut',
                           'Sick Kids House',
                           'Lost Woods Gamble',
                           'Fortune Teller (Light)',
                           'Snitch Lady (East)',
                           'Snitch Lady (West)',
                           'Bush Covered House',
                           'Tavern (Front)',
                           'Light World Bomb Hut',
                           'Kakariko Shop',
                           'Mini Moldorm Cave',
                           'Long Fairy Cave',
                           'Good Bee Cave',
                           '20 Rupee Cave',
                           '50 Rupee Cave',
                           'Ice Rod Cave',
                           'Bonk Rock Cave',
                           'Library',
                           'Potion Shop',
                           'Dam',
                           'Lumberjack House',
                           'Lake Hylia Fortune Teller',
                           'Eastern Palace',
                           'Kakariko Gamble Game',
                           'Kakariko Well Cave',
                           'Bat Cave Cave',
                           'Elder House (East)',
                           'Elder House (West)',
                           'North Fairy Cave',
                           'Lost Woods Hideout Stump',
                           'Lumberjack Tree Cave',
                           'Two Brothers House (East)',
                           'Sanctuary',
                           'Hyrule Castle Entrance (South)',
                           'Hyrule Castle Secret Entrance Stairs']
    LW_walkable_entrances = ['Dark Lake Hylia Ledge Fairy',
                             'Dark Lake Hylia Ledge Spike Cave',
                             'Dark Lake Hylia Ledge Hint',
                             'Mire Shed',
                             'Dark Desert Hint',
                             'Dark Desert Fairy',
                             'Misery Mire']
    Northern_DW_entrances = ['Brewery',
                             'C-Shaped House',
                             'Chest Game',
                             'Dark World Hammer Peg Cave',
                             'Red Shield Shop',
                             'Dark Sanctuary Hint',
                             'Fortune Teller (Dark)',
                             'Dark World Shop',
                             'Dark World Lumberjack Shop',
                             'Thieves Town',
                             'Skull Woods First Section Door',
                             'Skull Woods Second Section Door (East)']
    Southern_DW_entrances = ['Hype Cave',
                             'Bonk Fairy (Dark)',
                             'Archery Game',
                             'Big Bomb Shop',
                             'Dark Lake Hylia Shop',
                             'Swamp Palace']
    Isolated_DW_entrances = ['Spike Cave',
                             'Cave Shop (Dark Death Mountain)',
                             'Dark Death Mountain Fairy',
                             'Mimic Cave',
                             'Skull Woods Second Section Door (West)',
                             'Skull Woods Final Section',
                             'Ice Palace',
                             'Turtle Rock',
                             'Dark Death Mountain Ledge (West)',
                             'Dark Death Mountain Ledge (East)',
                             'Bumper Cave (Top)',
                             'Superbunny Cave (Top)',
                             'Superbunny Cave (Bottom)',
                             'Hookshot Cave',
                             'Ganons Tower',
                             'Turtle Rock Isolated Ledge Entrance',
                             'Hookshot Cave Back Entrance']
    Isolated_LW_entrances = ['Capacity Upgrade',
                             'Tower of Hera',
                             'Death Mountain Return Cave (West)',
                             'Paradox Cave (Top)',
                             'Fairy Ascension Cave (Top)',
                             'Spiral Cave',
                             'Desert Palace Entrance (East)']
    West_LW_DM_entrances = ['Old Man Cave (East)',
                            'Old Man House (Bottom)',
                            'Old Man House (Top)',
                            'Death Mountain Return Cave (East)',
                            'Spectacle Rock Cave Peak',
                            'Spectacle Rock Cave',
                            'Spectacle Rock Cave (Bottom)']
    East_LW_DM_entrances = ['Paradox Cave (Bottom)',
                            'Paradox Cave (Middle)',
                            'Hookshot Fairy',
                            'Spiral Cave (Bottom)']
    Mirror_from_SDW_entrances = ['Two Brothers House (West)',
                                 'Cave 45']
    Castle_ledge_entrances = ['Hyrule Castle Entrance (West)',
                              'Hyrule Castle Entrance (East)',
                              'Agahnims Tower']
    Desert_mirrorable_ledge_entrances = ['Desert Palace Entrance (West)',
                                         'Desert Palace Entrance (North)',
                                         'Desert Palace Entrance (South)',
                                         'Checkerboard Cave']

    set_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.can_reach('East Dark World', 'Region', player) and state.can_reach('Big Bomb Shop', 'Region', player) and state.has('Crystal 5', player) and state.has('Crystal 6', player))

    #crossing peg bridge starting from the southern dark world
    def cross_peg_bridge(state):
        return state.has('Hammer', player) and state.has_Pearl(player)

    # returning via the eastern and southern teleporters needs the same items, so we use the southern teleporter for out routing.
    # crossing preg bridge already requires hammer so we just add the gloves to the requirement
    def southern_teleporter(state):
        return state.can_lift_rocks(player) and cross_peg_bridge(state)

    # the basic routes assume you can reach eastern light world with the bomb.
    # you can then use the southern teleporter, or (if you have beaten Aga1) the hyrule castle gate warp
    def basic_routes(state):
        return southern_teleporter(state) or state.can_reach('Top of Pyramid', 'Entrance', player)

    # Key for below abbreviations:
    # P = pearl
    # A = Aga1
    # H = hammer
    # M = Mirror
    # G = Glove

    if bombshop_entrance.name in Normal_LW_entrances:
        #1. basic routes
        #2. Can reach Eastern dark world some other way, mirror, get bomb, return to mirror spot, walk to pyramid: Needs mirror
        # -> M or BR
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: basic_routes(state) or state.has_Mirror(player))
    elif bombshop_entrance.name in LW_walkable_entrances:
        #1. Mirror then basic routes
        # -> M and BR
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has_Mirror(player) and basic_routes(state))
    elif bombshop_entrance.name in Northern_DW_entrances:
        #1. Mirror and basic routes
        #2. Go to south DW and then cross peg bridge: Need Mitts and hammer and moon pearl
        # -> (Mitts and CPB) or (M and BR)
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.can_lift_heavy_rocks(player) and cross_peg_bridge(state)) or (state.has_Mirror(player) and basic_routes(state)))
    elif bombshop_entrance.name == 'Bumper Cave (Bottom)':
        #1. Mirror and Lift rock and basic_routes
        #2. Mirror and Flute and basic routes (can make difference if accessed via insanity or w/ mirror from connector, and then via hyrule castle gate, because no gloves are needed in that case)
        #3. Go to south DW and then cross peg bridge: Need Mitts and hammer and moon pearl
        # -> (Mitts and CPB) or (((G or Flute) and M) and BR))
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.can_lift_heavy_rocks(player) and cross_peg_bridge(state)) or (((state.can_lift_rocks(player) or state.has('Ocarina', player)) and state.has_Mirror(player)) and basic_routes(state)))
    elif bombshop_entrance.name in Southern_DW_entrances:
        #1. Mirror and enter via gate: Need mirror and Aga1
        #2. cross peg bridge: Need hammer and moon pearl
        # -> CPB or (M and A)
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: cross_peg_bridge(state) or (state.has_Mirror(player) and state.can_reach('Top of Pyramid', 'Entrance', player)))
    elif bombshop_entrance.name in Isolated_DW_entrances:
        # 1. mirror then flute then basic routes
        # -> M and Flute and BR
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has_Mirror(player) and state.has('Ocarina', player) and basic_routes(state))
    elif bombshop_entrance.name in Isolated_LW_entrances:
        # 1. flute then basic routes
        # Prexisting mirror spot is not permitted, because mirror might have been needed to reach these isolated locations.
        # -> Flute and BR
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has('Ocarina', player) and basic_routes(state))
    elif bombshop_entrance.name in West_LW_DM_entrances:
        # 1. flute then basic routes or mirror
        # Prexisting mirror spot is permitted, because flute can be used to reach west DM directly.
        # -> Flute and (M or BR)
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has('Ocarina', player) and (state.has_Mirror(player) or basic_routes(state)))
    elif bombshop_entrance.name in East_LW_DM_entrances:
        # 1. flute then basic routes or mirror and hookshot
        # Prexisting mirror spot is permitted, because flute can be used to reach west DM directly and then east DM via Hookshot
        # -> Flute and ((M and Hookshot) or BR)
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has('Ocarina', player) and ((state.has_Mirror(player) and state.has('Hookshot', player)) or basic_routes(state)))
    elif bombshop_entrance.name == 'Fairy Ascension Cave (Bottom)':
        # Same as East_LW_DM_entrances except navigation without BR requires Mitts
        # -> Flute and ((M and Hookshot and Mitts) or BR)
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has('Ocarina', player) and ((state.has_Mirror(player) and state.has('Hookshot', player) and state.can_lift_heavy_rocks(player)) or basic_routes(state)))
    elif bombshop_entrance.name in Castle_ledge_entrances:
        # 1. mirror on pyramid to castle ledge, grab bomb, return through mirror spot: Needs mirror
        # 2. flute then basic routes
        # -> M or (Flute and BR)
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has_Mirror(player) or (state.has('Ocarina', player) and basic_routes(state)))
    elif bombshop_entrance.name in Desert_mirrorable_ledge_entrances:
        # Cases when you have mire access: Mirror to reach locations, return via mirror spot, move to center of desert, mirror anagin and:
        # 1. Have mire access, Mirror to reach locations, return via mirror spot, move to center of desert, mirror again and then basic routes
        # 2. flute then basic routes
        # -> (Mire access and M) or Flute) and BR
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: ((state.can_reach('Dark Desert', 'Region', player) and state.has_Mirror(player)) or state.has('Ocarina', player)) and basic_routes(state))
    elif bombshop_entrance.name == 'Old Man Cave (West)':
        # 1. Lift rock then basic_routes
        # 2. flute then basic_routes
        # -> (Flute or G) and BR
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.has('Ocarina', player) or state.can_lift_rocks(player)) and basic_routes(state))
    elif bombshop_entrance.name == 'Graveyard Cave':
        # 1. flute then basic routes
        # 2. (has west dark world access) use existing mirror spot (required Pearl), mirror again off ledge
        # -> (Flute or (M and P and West Dark World access) and BR
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.has('Ocarina', player) or (state.can_reach('West Dark World', 'Region', player) and state.has_Pearl(player) and state.has_Mirror(player))) and basic_routes(state))
    elif bombshop_entrance.name in Mirror_from_SDW_entrances:
        # 1. flute then basic routes
        # 2. (has South dark world access) use existing mirror spot, mirror again off ledge
        # -> (Flute or (M and South Dark World access) and BR
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.has('Ocarina', player) or (state.can_reach('South Dark World', 'Region', player) and state.has_Mirror(player))) and basic_routes(state))
    elif bombshop_entrance.name == 'Dark World Potion Shop':
        # 1. walk down by lifting rock: needs gloves and pearl`
        # 2. walk down by hammering peg: needs hammer and pearl
        # 3. mirror and basic routes
        # -> (P and (H or Gloves)) or (M and BR)
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.has_Pearl(player) and (state.has('Hammer', player) or state.can_lift_rocks(player))) or (state.has_Mirror(player) and basic_routes(state)))
    elif bombshop_entrance.name == 'Kings Grave':
        # same as the Normal_LW_entrances case except that the pre-existing mirror is only possible if you have mitts
        # (because otherwise mirror was used to reach the grave, so would cancel a pre-existing mirror spot)
        # to account for insanity, must consider a way to escape without a cave for basic_routes
        # -> (M and Mitts) or ((Mitts or Flute or (M and P and West Dark World access)) and BR)
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.can_lift_heavy_rocks(player) and state.has_Mirror(player)) or ((state.can_lift_heavy_rocks(player) or state.has('Ocarina', player) or (state.can_reach('West Dark World', 'Region', player) and state.has_Pearl(player) and state.has_Mirror(player))) and basic_routes(state)))
    elif bombshop_entrance.name == 'Waterfall of Wishing':
        # same as the Normal_LW_entrances case except in insanity it's possible you could be here without Flippers which
        # means you need an escape route of either Flippers or Flute
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.has('Flippers', player) or state.has('Ocarina', player)) and (basic_routes(state) or state.has_Mirror(player)))

def set_inverted_big_bomb_rules(world, player):
    bombshop_entrance = world.get_region('Inverted Big Bomb Shop', player).entrances[0]
    Normal_LW_entrances = ['Blinds Hideout',
                           'Bonk Fairy (Light)',
                           'Lake Hylia Fairy',
                           'Light Hype Fairy',
                           'Desert Fairy',
                           'Chicken House',
                           'Aginahs Cave',
                           'Sahasrahlas Hut',
                           'Cave Shop (Lake Hylia)',
                           'Blacksmiths Hut',
                           'Sick Kids House',
                           'Lost Woods Gamble',
                           'Fortune Teller (Light)',
                           'Snitch Lady (East)',
                           'Snitch Lady (West)',
                           'Tavern (Front)',
                           'Kakariko Shop',
                           'Mini Moldorm Cave',
                           'Long Fairy Cave',
                           'Good Bee Cave',
                           '20 Rupee Cave',
                           '50 Rupee Cave',
                           'Ice Rod Cave',
                           'Bonk Rock Cave',
                           'Library',
                           'Potion Shop',
                           'Dam',
                           'Lumberjack House',
                           'Lake Hylia Fortune Teller',
                           'Eastern Palace',
                           'Kakariko Gamble Game',
                           'Kakariko Well Cave',
                           'Bat Cave Cave',
                           'Elder House (East)',
                           'Elder House (West)',
                           'North Fairy Cave',
                           'Lost Woods Hideout Stump',
                           'Lumberjack Tree Cave',
                           'Two Brothers House (East)',
                           'Sanctuary',
                           'Hyrule Castle Entrance (South)',
                           'Hyrule Castle Secret Entrance Stairs',
                           'Hyrule Castle Entrance (West)',
                           'Hyrule Castle Entrance (East)',
                           'Inverted Ganons Tower',
                           'Cave 45',
                           'Checkerboard Cave',
                           'Inverted Big Bomb Shop']
    LW_DM_entrances = ['Old Man Cave (East)',
                       'Old Man House (Bottom)',
                       'Old Man House (Top)',
                       'Death Mountain Return Cave (East)',
                       'Spectacle Rock Cave Peak',
                       'Tower of Hera',
                       'Death Mountain Return Cave (West)',
                       'Paradox Cave (Top)',
                       'Fairy Ascension Cave (Top)',
                       'Spiral Cave',
                       'Paradox Cave (Bottom)',
                       'Paradox Cave (Middle)',
                       'Hookshot Fairy',
                       'Spiral Cave (Bottom)',
                       'Mimic Cave',
                       'Fairy Ascension Cave (Bottom)',
                       'Desert Palace Entrance (West)',
                       'Desert Palace Entrance (North)',
                       'Desert Palace Entrance (South)']
    Northern_DW_entrances = ['Brewery',
                             'C-Shaped House',
                             'Chest Game',
                             'Dark World Hammer Peg Cave',
                             'Red Shield Shop',
                             'Inverted Dark Sanctuary',
                             'Fortune Teller (Dark)',
                             'Dark World Shop',
                             'Dark World Lumberjack Shop',
                             'Thieves Town',
                             'Skull Woods First Section Door',
                             'Skull Woods Second Section Door (East)']
    Southern_DW_entrances = ['Hype Cave',
                             'Bonk Fairy (Dark)',
                             'Archery Game',
                             'Inverted Links House',
                             'Dark Lake Hylia Shop',
                             'Swamp Palace']
    Isolated_DW_entrances = ['Spike Cave',
                             'Cave Shop (Dark Death Mountain)',
                             'Dark Death Mountain Fairy',
                             'Skull Woods Second Section Door (West)',
                             'Skull Woods Final Section',
                             'Turtle Rock',
                             'Dark Death Mountain Ledge (West)',
                             'Dark Death Mountain Ledge (East)',
                             'Bumper Cave (Top)',
                             'Superbunny Cave (Top)',
                             'Superbunny Cave (Bottom)',
                             'Hookshot Cave',
                             'Turtle Rock Isolated Ledge Entrance',
                             'Hookshot Cave Back Entrance',
                             'Inverted Agahnims Tower',
                             'Dark Lake Hylia Ledge Fairy',
                             'Dark Lake Hylia Ledge Spike Cave',
                             'Dark Lake Hylia Ledge Hint',
                             'Mire Shed',
                             'Dark Desert Hint',
                             'Dark Desert Fairy',
                             'Misery Mire']

    LW_bush_entrances = ['Bush Covered House',
                         'Light World Bomb Hut',
                         'Graveyard Cave']
    
    set_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.can_reach('East Dark World', 'Region', player) and state.can_reach('Inverted Big Bomb Shop', 'Region', player) and state.has('Crystal 5', player) and state.has('Crystal 6', player))

    # crossing peg bridge starting from the southern dark world
    def cross_peg_bridge(state):
        return state.has('Hammer', player)

    # Key for below abbreviations:
    # P = pearl
    # A = Aga1
    # H = hammer
    # M = Mirror
    # G = Glove
    if bombshop_entrance.name in Normal_LW_entrances:
        # Just walk to the castle and mirror.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has_Mirror(player))
    elif bombshop_entrance.name in LW_DM_entrances:
        # For these entrances, you cannot walk to the castle/pyramid and thus must use Mirror and then Flute.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.can_flute(player) and state.has_Mirror(player))
    elif bombshop_entrance.name in Northern_DW_entrances:
        # You can just fly with the Flute, you can take a long walk with Mitts and Hammer,
        # or you can leave a Mirror portal nearby and then walk to the castle to Mirror again.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.can_flute or (state.can_lift_heavy_rocks(player) and cross_peg_bridge(state)) or (state.has_Mirror(player) and state.can_reach('Light World', 'Region', player)))
    elif bombshop_entrance.name in Southern_DW_entrances:
        # This is the same as north DW without the Mitts rock present.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: cross_peg_bridge(state) or state.can_flute(player) or (state.has_Mirror(player) and state.can_reach('Light World', 'Region', player)))
    elif bombshop_entrance.name in Isolated_DW_entrances:
        # There's just no way to escape these places with the bomb and no Flute.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.can_flute(player))
    elif bombshop_entrance.name in LW_bush_entrances:
        # These entrances are behind bushes in LW so you need either Pearl or the tools to solve NDW bomb shop locations.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has_Mirror(player) and (state.can_flute(player) or state.has_Pearl(player) or (state.can_lift_heavy_rocks(player) and cross_peg_bridge(state))))
    elif bombshop_entrance.name == 'Bumper Cave (Bottom)':
        # This is mostly the same as NDW but the Mirror path requires being able to lift a rock.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.can_flute or (state.can_lift_heavy_rocks(player) and cross_peg_bridge(state)) or (state.has_Mirror(player) and state.can_lift_rocks(player) and state.can_reach('Light World', 'Region', player)))
    elif bombshop_entrance.name == 'Old Man Cave (West)':
        # The three paths back are Mirror and DW walk, Mirror and Flute, or LW walk and then Mirror.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has_Mirror(player) and ((state.can_lift_heavy_rocks(player) and cross_peg_bridge(state)) or (state.can_lift_rocks(player) and state.has_Pearl(player)) or state.can_flute(player)))
    elif bombshop_entrance.name == 'Dark World Potion Shop':
        # You either need to Flute to 5 or cross the rock/hammer choice pass to the south.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.can_flute(player) or state.has('Hammer', player) or state.can_lift_rocks(player))
    elif bombshop_entrance.name == 'Kings Grave':
        # Either lift the rock and walk to the castle to Mirror or Mirror immediately and Flute.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.can_flute(player) or state.can_lift_heavy_rocks(player)) and state.has_Mirror(player))
    elif bombshop_entrance.name == 'Two Brothers House (West)':
        # First you must Mirror. Then you can either Flute, cross the peg bridge, or use the Agah 1 portal to Mirror again.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.can_flute(player) or cross_peg_bridge(state) or state.has('Beat Agahnim 1', player)) and state.has_Mirror(player))
    elif bombshop_entrance.name == 'Waterfall of Wishing':
        # You absolutely must be able to swim to return it from here.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has('Flippers', player) and state.has_Pearl(player) and state.has_Mirror(player))
    elif bombshop_entrance.name == 'Ice Palace':
        # You can swim to the dock or use the Flute to get off the island.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: state.has('Flippers', player) or state.can_flute(player))
    elif bombshop_entrance.name == 'Capacity Upgrade':
        # You must Mirror but then can use either Ice Palace return path.
        add_rule(world.get_entrance('Pyramid Fairy', player), lambda state: (state.has('Flippers', player) or state.can_flute(player)) and state.has_Mirror(player))


def set_bunny_rules(world, player):
    # regions for the exits of multi-entrace caves/drops that bunny cannot pass
    # Note spiral cave may be technically passible, but it would be too absurd to require since OHKO mode is a thing.
    bunny_impassable_caves = ['Bumper Cave', 'Two Brothers House', 'Hookshot Cave',
                              'Pyramid', 'Spiral Cave (Top)', 'Fairy Ascension Cave (Drop)']
    bunny_accessible_locations = ['Link\'s Uncle', 'Sahasrahla', 'Sick Kid', 'Lost Woods Hideout', 'Lumberjack Tree',
                                  'Checkerboard Cave', 'Potion Shop', 'Spectacle Rock Cave', 'Pyramid',
                                  'Hype Cave - Generous Guy', 'Peg Cave', 'Bumper Cave Ledge', 'Dark Blacksmith Ruins']

    def path_to_access_rule(path, entrance):
        return lambda state: state.can_reach(entrance) and all(rule_func(state) for rule_func in path)

    def options_to_access_rule(options):
        return lambda state: any(rule_func(state) for rule_func in options)

    def get_rule_to_add(region, location = None, connecting_entrance = None):
        # In OWG, a location can potentially be superbunny-mirror accessible or
        # bunny revival accessible.
        if world.logic[player] == 'owglitches':
            if region.name in OWGSets.get_invalid_bunny_revival_dungeons():
                return lambda state: state.has_Mirror(player) or state.has_Pearl(player)
            if not any([
                None not in [location, connecting_entrance] and location.name in OWGSets.get_superbunny_accessible_locations() and connecting_entrance.name not in OWGSets.get_invalid_mirror_bunny_entrances_dw(),
                not region.is_light_world]):
                return lambda state: state.has_Pearl(player)
        else:
            if not region.is_light_world:
                return lambda state: state.has_Pearl(player)

        # in this case we are mixed region.
        # we collect possible options.

        # The base option is having the moon pearl
        possible_options = [lambda state: state.has_Pearl(player)]

        # We will search entrances recursively until we find
        # one that leads to an exclusively light world region
        # for each such entrance a new option is added that consist of:
        #    a) being able to reach it, and
        #    b) being able to access all entrances from there to `region`
        seen = {region}
        queue = deque([(region, [])])
        while queue:
            (current, path) = queue.popleft()
            for entrance in current.entrances:
                new_region = entrance.parent_region
                if new_region in seen:
                    continue
                new_path = path + [entrance.access_rule]
                seen.add(new_region)
                if not new_region.is_light_world:
                    # For OWG, establish superbunny and revival rules.
                    if world.logic[player] == 'owglitches' and entrance.name not in OWGSets.get_invalid_mirror_bunny_entrances_dw():
                        for location in entrance.connected_region.locations:
                            if location.name in OWGSets.get_superbunny_accessible_locations():
                                possible_options.append(lambda state: path_to_access_rule(new_path, entrance) and state.has_Mirror(player))
                                continue
                    else:
                        continue
                if new_region.is_dark_world:
                    queue.append((new_region, new_path))
                else:
                    # we have reached pure light world or a dungeon, so we have a new possible option
                    possible_options.append(path_to_access_rule(new_path, entrance))
        return options_to_access_rule(possible_options)

    # Add requirements for bunny-impassible caves if they occur in the dark world
    for region in [world.get_region(name, player) for name in bunny_impassable_caves]:

        if not region.is_dark_world:
            continue
        rule = get_rule_to_add(region)
        for ext in region.exits:
            add_rule(ext, rule)

    paradox_shop = world.get_region('Light World Death Mountain Shop', player)
    if paradox_shop.is_dark_world:
        add_rule(paradox_shop.entrances[0], get_rule_to_add(paradox_shop))

    for ent_name in bunny_impassible_doors:
        bunny_exit = world.get_entrance(ent_name, player)
        if bunny_exit.parent_region.is_dark_world:
            add_rule(bunny_exit, get_rule_to_add(bunny_exit.parent_region))

    doors_to_check = [x for x in world.doors if x.player == player and x not in bunny_impassible_doors]
    doors_to_check = [x for x in doors_to_check if x.type in [DoorType.Normal, DoorType.Interior] and not x.blocked]
    for door in doors_to_check:
        room = world.get_room(door.roomIndex, player)
        if door.entrance.parent_region.is_dark_world and room.kind(door) in [DoorKind.Dashable, DoorKind.Bombable, DoorKind.Hidden]:
            add_rule(door.entrance, get_rule_to_add(door.entrance.parent_region))

    # Add requirements for all locations that are actually in the dark world, except those available to the bunny, including dungeon revival
    for entrance in world.get_entrances():
        if entrance.player == player and entrance.parent_region.is_dark_world:
            if world.logic[player] == 'owglitches':
                if entrance.connected_region.type == RegionType.Dungeon:
                    if entrance.connected_region.name in OWGSets.get_invalid_bunny_revival_dungeons():
                        add_rule(entrance, get_rule_to_add(entrance.connected_region, None, entrance))
                    continue
                if entrance.connected_region.name == 'Turtle Rock (Entrance)':
                    add_rule(world.get_entrance('Turtle Rock Entrance Gap', player), get_rule_to_add(entrance.connected_region, None, entrance))
                if entrance.name in OWGSets.get_invalid_mirror_bunny_entrances_dw():
                    continue
            for location in entrance.connected_region.locations:
                if world.logic[player] == 'owglitches' and entrance.name in OWGSets.get_invalid_mirror_bunny_entrances_dw():
                    add_rule(location, get_rule_to_add(entrance.connected_region, location, entrance))
                    continue
                if location.name in bunny_accessible_locations:
                        continue
                add_rule(location, get_rule_to_add(entrance.connected_region, location))


def set_inverted_bunny_rules(world, player):
    # regions for the exits of multi-entrace caves/drops that bunny cannot pass
    # Note spiral cave may be technically passible, but it would be too absurd to require since OHKO mode is a thing.
    bunny_impassable_caves = ['Bumper Cave', 'Two Brothers House', 'Hookshot Cave', 'Skull Woods First Section (Right)', 'Skull Woods First Section (Left)', 'Skull Woods First Section (Top)', 'Turtle Rock (Entrance)', 'Turtle Rock (Second Section)', 'Turtle Rock (Big Chest)', 'Skull Woods Second Section (Drop)',
                              'Turtle Rock (Eye Bridge)', 'Sewers', 'Pyramid', 'Spiral Cave (Top)', 'Desert Palace Main (Inner)', 'Fairy Ascension Cave (Drop)', 'The Sky']
    bunny_accessible_locations = ['Link\'s Uncle', 'Sahasrahla', 'Sick Kid', 'Lost Woods Hideout', 'Lumberjack Tree', 'Checkerboard Cave', 'Potion Shop', 'Spectacle Rock Cave', 'Pyramid', 'Hype Cave - Generous Guy', 'Peg Cave', 'Bumper Cave Ledge', 'Dark Blacksmith Ruins', 'Bombos Tablet Ledge', 'Ether Tablet', 'Purple Chest']

    def path_to_access_rule(path, entrance):
        return lambda state: state.can_reach(entrance) and all(rule_func(state) for rule_func in path)

    def options_to_access_rule(options):
        return lambda state: any(rule_func(state) for rule_func in options)

    def get_rule_to_add(region, location = None, connecting_entrance = None):
        # In OWG, a location can potentially be superbunny-mirror accessible or
        # bunny revival accessible.
        if world.logic[player] == 'owglitches':
            if region.name in OWGSets.get_invalid_bunny_revival_dungeons():
                return lambda state: state.has_Mirror(player) or state.has_Pearl(player)
            if not any([
                None not in [location, connecting_entrance] and location.name in OWGSets.get_superbunny_accessible_locations() and connecting_entrance.name not in OWGSets.get_invalid_mirror_bunny_entrances_lw(),
                not region.is_dark_world]):
                return lambda state: state.has_Pearl(player)
        else:
            if not region.is_dark_world:
                return lambda state: state.has_Pearl(player)
        # in this case we are mixed region.
        # we collect possible options.

        # The base option is having the moon pearl
        possible_options = [lambda state: state.has_Pearl(player)]

        # We will search entrances recursively until we find
        # one that leads to an exclusively dark world region
        # for each such entrance a new option is added that consist of:
        #    a) being able to reach it, and
        #    b) being able to access all entrances from there to `region`
        seen = {region}
        queue = deque([(region, [])])
        while queue:
            (current, path) = queue.popleft()
            for entrance in current.entrances:
                new_region = entrance.parent_region
                if new_region in seen:
                    continue
                new_path = path + [entrance.access_rule]
                seen.add(new_region)
                if not new_region.is_dark_world:
                    # For OWG, establish superbunny and revival rules.
                    if world.logic[player] == 'owglitches' and entrance.name not in OWGSets.get_invalid_mirror_bunny_entrances_lw():
                        for location in entrance.connected_region.locations:
                            if location.name in OWGSets.get_superbunny_accessible_locations():
                                possible_options.append(lambda state: path_to_access_rule(new_path, entrance) and state.has_Mirror(player))
                                continue
                    else:
                        continue
                if new_region.is_light_world:
                    queue.append((new_region, new_path))
                else:
                    # we have reached pure dark world, so we have a new possible option
                    possible_options.append(path_to_access_rule(new_path, entrance))
        return options_to_access_rule(possible_options)

    # Add requirements for bunny-impassible caves if they occur in the light world
    for region in [world.get_region(name, player) for name in bunny_impassable_caves]:

        if not region.is_light_world:
            continue
        rule = get_rule_to_add(region)
        for ext in region.exits:
            add_rule(ext, rule)

    paradox_shop = world.get_region('Light World Death Mountain Shop', player)
    if paradox_shop.is_light_world:
        add_rule(paradox_shop.entrances[0], get_rule_to_add(paradox_shop))

    for ent_name in bunny_impassible_doors:
        bunny_exit = world.get_entrance(ent_name, player)
        if bunny_exit.parent_region.is_light_world:
            add_rule(bunny_exit, get_rule_to_add(bunny_exit.parent_region))

    doors_to_check = [x for x in world.doors if x.player == player and x not in bunny_impassible_doors]
    doors_to_check = [x for x in doors_to_check if x.type in [DoorType.Normal, DoorType.Interior] and not x.blocked]
    for door in doors_to_check:
        room = world.get_room(door.roomIndex, player)
        if door.entrance.parent_region.is_light_world and room.kind(door) in [DoorKind.Dashable, DoorKind.Bombable, DoorKind.Hidden]:
            add_rule(door.entrance, get_rule_to_add(door.entrance.parent_region))

    # Add requirements for all locations that are actually in the light world, except those available to the bunny, including dungeon revival
    for entrance in world.get_entrances():
        if entrance.player == player and entrance.parent_region.is_light_world:
            if world.logic[player] == 'owglitches':
                if entrance.connected_region.type == RegionType.Dungeon:
                    if entrance.connected_region.name in OWGSets.get_invalid_bunny_revival_dungeons():
                        add_rule(entrance, get_rule_to_add(entrance.connected_region, None, entrance))
                    continue
                if entrance.connected_region.name == 'Turtle Rock (Entrance)':
                    add_rule(world.get_entrance('Turtle Rock Entrance Gap', player), get_rule_to_add(entrance.connected_region, None, entrance))
                if entrance.name in OWGSets.get_invalid_mirror_bunny_entrances_lw():
                    continue
            for location in entrance.connected_region.locations:
                if world.logic[player] == 'owglitches' and entrance.name in OWGSets.get_invalid_mirror_bunny_entrances_lw():
                    add_rule(location, get_rule_to_add(entrance.connected_region, location, entrance))
                    continue
                if location.name in bunny_accessible_locations:
                        continue
                add_rule(location, get_rule_to_add(entrance.connected_region, location))


bunny_impassible_doors = {
    'Hyrule Dungeon Armory S', 'Hyrule Dungeon Armory ES', 'Sewers Secret Room Push Block', 'Sewers Pull Switch S',
    'Eastern Lobby N', 'Eastern Courtyard Ledge W', 'Eastern Courtyard Ledge E', 'Eastern Pot Switch SE',
    'Eastern Map Balcony Hook Path',     'Eastern Stalfos Spawn ES', 'Eastern Stalfos Spawn NW',
    'Eastern Hint Tile Push Block', 'Eastern Darkness S', 'Eastern Darkness NE', 'Eastern Darkness Up Stairs',
    'Eastern Attic Start WS', 'Eastern Single Eyegore NE', 'Eastern Duo Eyegores NE', 'Desert Main Lobby Left Path',
    'Desert Main Lobby Right Path', 'Desert Left Alcove Path', 'Desert Right Alcove Path', 'Desert Compass NW',
    'Desert West Lobby NW', 'Desert Back Lobby NW', 'Desert Four Statues NW',  'Desert Four Statues ES',
    'Desert Beamos Hall WS', 'Desert Beamos Hall NE', 'Desert Wall Slide NW', 'Hera Lobby Down Stairs',
    'Hera Lobby Key Stairs', 'Hera Lobby Up Stairs', 'Hera Tile Room EN', 'Hera Tridorm SE', 'Hera Beetles WS',
    'Hera 4F Down Stairs', 'Tower Gold Knights SW', 'Tower Dark Maze EN', 'Tower Dark Pits ES', 'Tower Dark Archers WN',
    'Tower Red Spears WN', 'Tower Red Guards EN', 'Tower Red Guards SW', 'Tower Circle of Pots NW', 'Tower Altar NW',
    'PoD Left Cage SW', 'PoD Middle Cage SE', 'PoD Pit Room Bomb Hole', 'PoD Pit Room Block Path N',
    'PoD Pit Room Block Path S', 'PoD Stalfos Basement Warp', 'PoD Arena Main SW', 'PoD Arena Main Crystal Path',
    'PoD Arena Bonk Path', 'PoD Arena Crystal Path', 'PoD Sexy Statue NW', 'PoD Map Balcony Drop Down',
    'PoD Mimics 1 NW', 'PoD Warp Hint Warp', 'PoD Falling Bridge Path N', 'PoD Falling Bridge Path S',
    'PoD Mimics 2 NW', 'PoD Bow Statue Down Ladder', 'PoD Dark Pegs Up Ladder', 'PoD Dark Pegs WN',
    'PoD Turtle Party ES', 'PoD Turtle Party NW', 'PoD Callback Warp', 'Swamp Lobby Moat', 'Swamp Entrance Moat',
    'Swamp Trench 1 Approach Swim Depart', 'Swamp Trench 1 Approach Key', 'Swamp Trench 1 Key Approach',
    'Swamp Trench 1 Key Ledge Depart', 'Swamp Trench 1 Departure Approach', 'Swamp Trench 1 Departure Key',
    'Swamp Hub Hook Path', 'Swamp Compass Donut Push Block',
    'Swamp Shortcut Blue Barrier', 'Swamp Trench 2 Pots Blue Barrier', 'Swamp Trench 2 Pots Wet',
    'Swamp Trench 2 Departure Wet', 'Swamp West Shallows Push Blocks', 'Swamp West Ledge Hook Path',
    'Swamp Barrier Ledge Hook Path', 'Swamp Attic Left Pit', 'Swamp Attic Right Pit', 'Swamp Push Statue NW',
    'Swamp Push Statue NE', 'Swamp Drain Right Switch', 'Swamp Waterway NE', 'Swamp Waterway N', 'Swamp Waterway NW',
    'Skull Pot Circle WN', 'Skull Pot Circle Star Path', 'Skull Pull Switch S', 'Skull Big Chest N',
    'Skull Big Chest Hookpath', 'Skull 2 East Lobby NW', 'Skull Back Drop Star Path', 'Skull 2 West Lobby NW',
    'Skull 3 Lobby EN', 'Skull Star Pits SW', 'Skull Star Pits ES', 'Skull Torch Room WN', 'Skull Vines NW',
    'Thieves Conveyor Maze EN', 'Thieves Triple Bypass EN', 'Thieves Triple Bypass SE', 'Thieves Triple Bypass WN',
    'Thieves Hellway Blue Barrier', 'Thieves Hellway Crystal Blue Barrier', 'Thieves Attic ES',
    'Thieves Basement Block Path', 'Thieves Blocked Entry Path', 'Thieves Conveyor Bridge Block Path',
    'Thieves Conveyor Block Path', 'Ice Lobby WS', 'Ice Cross Left Push Block', 'Ice Cross Bottom Push Block Left',
    'Ice Cross Bottom Push Block Right', 'Ice Cross Right Push Block Top', 'Ice Cross Right Push Block Bottom',
    'Ice Cross Top Push Block Bottom', 'Ice Cross Top Push Block Right', 'Ice Bomb Drop Hole', 'Ice Pengator Switch WS',
    'Ice Pengator Switch ES', 'Ice Big Key Push Block',  'Ice Stalfos Hint SE', 'Ice Bomb Jump EN',
    'Ice Pengator Trap NE', 'Ice Hammer Block ES', 'Ice Tongue Pull WS', 'Ice Freezors Bomb Hole', 'Ice Tall Hint WS',
    'Ice Hookshot Ledge Path', 'Ice Hookshot Balcony Path', 'Ice Many Pots SW', 'Ice Many Pots WS',
    'Ice Crystal Right Blue Hole', 'Ice Crystal Left Blue Barrier', 'Ice Big Chest Landing Push Blocks',
    'Ice Backwards Room Hole', 'Ice Switch Room SE', 'Ice Antechamber NE', 'Ice Antechamber Hole', 'Mire Lobby Gap',
    'Mire Post-Gap Gap', 'Mire 2 NE', 'Mire Hub Upper Blue Barrier', 'Mire Hub Lower Blue Barrier',
    'Mire Hub Right Blue Barrier', 'Mire Hub Top Blue Barrier', 'Mire Falling Bridge WN',
    'Mire Map Spike Side Blue Barrier', 'Mire Map Spot Blue Barrier', 'Mire Crystal Dead End Left Barrier',
    'Mire Crystal Dead End Right Barrier', 'Mire Cross ES', 'Mire Hidden Shooters Block Path S',
    'Mire Hidden Shooters Block Path N', 'Mire Left Bridge Hook Path', 'Mire Fishbone Blue Barrier',
    'Mire South Fish Blue Barrier', 'Mire Tile Room NW', 'Mire Compass Blue Barrier', 'Mire Attic Hint Hole',
    'Mire Dark Shooters SW', 'Mire Crystal Mid Blue Barrier', 'Mire Crystal Left Blue Barrier', 'TR Main Lobby Gap',
    'TR Lobby Ledge Gap', 'TR Hub SW', 'TR Hub SE', 'TR Hub ES', 'TR Hub EN', 'TR Hub NW', 'TR Hub NE', 'TR Torches NW',
    'TR Pokey 2 EN', 'TR Pokey 2 ES', 'TR Twin Pokeys SW', 'TR Twin Pokeys EN', 'TR Big Chest Gap',
    'TR Big Chest Entrance Gap', 'TR Lazy Eyes ES', 'TR Tongue Pull WS', 'TR Tongue Pull NE', 'TR Dark Ride Up Stairs',
    'TR Dark Ride SW', 'TR Crystal Maze Forwards Path', 'TR Crystal Maze Blue Path', 'TR Crystal Maze Cane Path',
    'TR Final Abyss South Stairs', 'TR Final Abyss NW', 'GT Hope Room EN', 'GT Blocked Stairs Block Path',
    'GT Bob\'s Room Hole', 'GT Speed Torch SE', 'GT Speed Torch South Path', 'GT Speed Torch North Path',
    'GT Crystal Conveyor NE', 'GT Crystal Conveyor WN', 'GT Conveyor Cross EN', 'GT Conveyor Cross WN',
    'GT Hookshot East-North Path', 'GT Hookshot East-South Path', 'GT Hookshot North-East Path',
    'GT Hookshot North-South Path', 'GT Hookshot South-East Path', 'GT Hookshot South-North Path',
    'GT Hookshot Platform Blue Barrier', 'GT Hookshot Entry Blue Barrier', 'GT Double Switch Blue Path',
    'GT Double Switch Key Blue Path', 'GT Double Switch Blue Barrier', 'GT Double Switch Transition Blue',
    'GT Firesnake Room Hook Path', 'GT Falling Bridge WN', 'GT Falling Bridge WS', 'GT Ice Armos NE', 'GT Ice Armos WS',
    'GT Crystal Paths SW', 'GT Mimics 1 NW', 'GT Mimics 1 ES', 'GT Mimics 2 WS', 'GT Mimics 2 NE',
    'GT Hidden Spikes EN', 'GT Cannonball Bridge SE', 'GT Gauntlet 1 WN', 'GT Gauntlet 2 EN', 'GT Gauntlet 2 SW',
    'GT Gauntlet 3 NW',  'GT Gauntlet 3 SW', 'GT Gauntlet 4 NW', 'GT Gauntlet 4 SW', 'GT Gauntlet 5 NW',
    'GT Gauntlet 5 WS', 'GT Lanmolas 2 ES', 'GT Lanmolas 2 NW', 'GT Wizzrobes 1 SW', 'GT Wizzrobes 2 SE',
    'GT Wizzrobes 2 NE', 'GT Torch Cross ES', 'GT Falling Torches NE', 'GT Moldorm Gap', 'GT Validation Block Path'
}


def add_key_logic_rules(world, player):
    key_logic = world.key_logic[player]
    for d_name, d_logic in key_logic.items():
        for door_name, keys in d_logic.door_rules.items():
            add_rule(world.get_entrance(door_name, player), create_advanced_key_rule(d_logic, player, keys))
        for location in d_logic.bk_restricted:
            if location.name not in key_only_locations.keys():
                forbid_item(location, d_logic.bk_name, player)
        for location in d_logic.sm_restricted:
            forbid_item(location, d_logic.small_key_name, player)
        for door in d_logic.bk_doors:
            add_rule(world.get_entrance(door.name, player), create_rule(d_logic.bk_name, player))
        for chest in d_logic.bk_chests:
            add_rule(world.get_location(chest.name, player), create_rule(d_logic.bk_name, player))


def create_rule(item_name, player):
    return lambda state: state.has(item_name, player)


def create_key_rule(small_key_name, player, keys):
    return lambda state: state.has_key(small_key_name, player, keys)


def create_key_rule_allow_small(small_key_name, player, keys, location):
    loc = location.name
    return lambda state: state.has_key(small_key_name, player, keys) or (item_name(state, loc, player) in [(small_key_name, player)] and state.has_key(small_key_name, player, keys-1))


def create_key_rule_bk_exception(small_key_name, big_key_name, player, keys, bk_keys, bk_locs):
    chest_names = [x.name for x in bk_locs]
    return lambda state: (state.has_key(small_key_name, player, keys) and not item_in_locations(state, big_key_name, player, zip(chest_names, [player] * len(chest_names)))) or (item_in_locations(state, big_key_name, player, zip(chest_names, [player] * len(chest_names))) and state.has_key(small_key_name, player, bk_keys))


def create_key_rule_bk_exception_or_allow(small_key_name, big_key_name, player, keys, location, bk_keys, bk_locs):
    loc = location.name
    chest_names = [x.name for x in bk_locs]
    return lambda state: (state.has_key(small_key_name, player, keys) and not item_in_locations(state, big_key_name, player, zip(chest_names, [player] * len(chest_names)))) or (item_name(state, loc, player) in [(small_key_name, player)] and state.has_key(small_key_name, player, keys-1)) or (item_in_locations(state, big_key_name, player, zip(chest_names, [player] * len(chest_names))) and state.has_key(small_key_name, player, bk_keys))


def create_advanced_key_rule(key_logic, player, rule):
    if not rule.allow_small and rule.alternate_small_key is None:
        return create_key_rule(key_logic.small_key_name, player, rule.small_key_num)
    if rule.allow_small and rule.alternate_small_key is None:
        return create_key_rule_allow_small(key_logic.small_key_name, player, rule.small_key_num, rule.small_location)
    if not rule.allow_small and rule.alternate_small_key is not None:
        return create_key_rule_bk_exception(key_logic.small_key_name, key_logic.bk_name, player, rule.small_key_num,
                                            rule.alternate_small_key, rule.alternate_big_key_loc)
    if rule.allow_small and rule.alternate_small_key is not None:
        return create_key_rule_bk_exception_or_allow(key_logic.small_key_name, key_logic.bk_name, player,
                                                     rule.small_key_num, rule.small_location, rule.alternate_small_key,
                                                     rule.alternate_big_key_loc)
