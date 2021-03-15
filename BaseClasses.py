import copy
import json
import logging
from collections import OrderedDict, Counter, deque, defaultdict
from enum import Enum, unique

try:
    from fast_enum import FastEnum
except ImportError:
    from enum import IntFlag as FastEnum


from source.classes.BabelFish import BabelFish
from EntranceShuffle import door_addresses, indirect_connections
from Utils import int16_as_bytes
from Tables import normal_offset_table, spiral_offset_table, multiply_lookup, divisor_lookup
from RoomData import Room

class World(object):

    def __init__(self, players, shuffle, doorShuffle, logic, mode, swords, difficulty, difficulty_adjustments,
                 timer, progressive, goal, algorithm, accessibility, shuffle_ganon, retro, custom, customitemarray, hints):
        self.players = players
        self.teams = 1
        self.shuffle = shuffle.copy()
        self.doorShuffle = doorShuffle.copy()
        self.intensity = {}
        self.logic = logic.copy()
        self.mode = mode.copy()
        self.swords = swords.copy()
        self.difficulty = difficulty.copy()
        self.difficulty_adjustments = difficulty_adjustments.copy()
        self.timer = timer
        self.progressive = progressive
        self.goal = goal.copy()
        self.algorithm = algorithm
        self.dungeons = []
        self.regions = []
        self.shops = []
        self.itempool = []
        self.seed = None
        self.precollected_items = []
        self.state = CollectionState(self)
        self._cached_entrances = None
        self._cached_locations = None
        self._entrance_cache = {}
        self._location_cache = {}
        self.required_locations = []
        self.shuffle_bonk_prizes = False
        self.light_world_light_cone = False
        self.dark_world_light_cone = False
        self.clock_mode = 'none'
        self.rupoor_cost = 10
        self.aga_randomness = True
        self.lock_aga_door_in_escape = False
        self.save_and_quit_from_boss = True
        self.accessibility = accessibility.copy()
        self.fix_skullwoods_exit = {}
        self.fix_palaceofdarkness_exit = {}
        self.fix_trock_exit = {}
        self.shuffle_ganon = shuffle_ganon
        self.fix_gtower_exit = self.shuffle_ganon
        self.retro = retro.copy()
        self.custom = custom
        self.customitemarray = customitemarray
        self.can_take_damage = True
        self.hints = hints.copy()
        self.dynamic_regions = []
        self.dynamic_locations = []
        self.spoiler = Spoiler(self)
        self.lamps_needed_for_dark_rooms = 1
        self.doors = []
        self._door_cache = {}
        self.paired_doors = {}
        self.rooms = []
        self._room_cache = {}
        self.dungeon_layouts = {}
        self.inaccessible_regions = {}
        self.key_logic = {}
        self.pool_adjustment = {}
        self.key_layout = defaultdict(dict)
        self.dungeon_portals = defaultdict(list)
        self._portal_cache = {}
        self.sanc_portal = {}
        self.fish = BabelFish()

        for player in range(1, players + 1):
            # If World State is Retro, set to Open and set Retro flag
            if self.mode[player] == "retro":
                self.mode[player] = "open"
                self.retro[player] = True
            def set_player_attr(attr, val):
                self.__dict__.setdefault(attr, {})[player] = val
            set_player_attr('_region_cache', {})
            set_player_attr('player_names', [])
            set_player_attr('remote_items', False)
            set_player_attr('required_medallions', ['Ether', 'Quake'])
            set_player_attr('swamp_patch_required', False)
            set_player_attr('powder_patch_required', False)
            set_player_attr('ganon_at_pyramid', True)
            set_player_attr('ganonstower_vanilla', True)
            set_player_attr('sewer_light_cone', self.mode[player] == 'standard')
            set_player_attr('fix_trock_doors', self.shuffle[player] != 'vanilla' or self.mode[player] == 'inverted')
            set_player_attr('fix_skullwoods_exit', self.shuffle[player] not in ['vanilla', 'simple', 'restricted', 'dungeonssimple'] or self.doorShuffle[player] not in ['vanilla'])
            set_player_attr('fix_palaceofdarkness_exit', self.shuffle[player] not in ['vanilla', 'simple', 'restricted', 'dungeonssimple'])
            set_player_attr('fix_trock_exit', self.shuffle[player] not in ['vanilla', 'simple', 'restricted', 'dungeonssimple'])
            set_player_attr('can_access_trock_eyebridge', None)
            set_player_attr('can_access_trock_front', None)
            set_player_attr('can_access_trock_big_chest', None)
            set_player_attr('can_access_trock_middle', None)
            set_player_attr('fix_fake_world', True)
            set_player_attr('mapshuffle', False)
            set_player_attr('compassshuffle', False)
            set_player_attr('keyshuffle', False)
            set_player_attr('bigkeyshuffle', False)
            set_player_attr('difficulty_requirements', None)
            set_player_attr('boss_shuffle', 'none')
            set_player_attr('enemy_shuffle', 'none')
            set_player_attr('enemy_health', 'default')
            set_player_attr('enemy_damage', 'default')
            set_player_attr('beemizer', 0)
            set_player_attr('escape_assist', [])
            set_player_attr('crystals_needed_for_ganon', 7)
            set_player_attr('crystals_needed_for_gt', 7)
            set_player_attr('crystals_ganon_orig', {})
            set_player_attr('crystals_gt_orig', {})
            set_player_attr('open_pyramid', False)
            set_player_attr('treasure_hunt_icon', 'Triforce Piece')
            set_player_attr('treasure_hunt_count', 0)
            set_player_attr('potshuffle', False)
            set_player_attr('pot_contents', None)

            set_player_attr('keydropshuffle', False)
            set_player_attr('mixed_travel', 'prevent')
            set_player_attr('standardize_palettes', 'standardize')
            set_player_attr('force_fix', {'gt': False, 'sw': False, 'pod': False, 'tr': False});

    def get_name_string_for_object(self, obj):
        return obj.name if self.players == 1 else f'{obj.name} ({self.get_player_names(obj.player)})'

    def get_player_names(self, player):
        return ", ".join([name for i, name in enumerate(self.player_names[player]) if self.player_names[player].index(name) == i])

    def initialize_regions(self, regions=None):
        for region in regions if regions else self.regions:
            region.world = self
            self._region_cache[region.player][region.name] = region
            for exit in region.exits:
                self._entrance_cache[(exit.name, exit.player)] = exit

    def initialize_doors(self, doors):
        for door in doors:
            self._door_cache[(door.name, door.player)] = door

    def remove_door(self, door, player):
        if (door, player) in self._door_cache.keys():
            del self._door_cache[(door, player)]
        self.doors.remove(door)

    def get_regions(self, player=None):
        return self.regions if player is None else self._region_cache[player].values()

    def get_region(self, regionname, player):
        if isinstance(regionname, Region):
            return regionname
        try:
            return self._region_cache[player][regionname]
        except KeyError:
            for region in self.regions:
                if region.name == regionname and region.player == player:
                    assert not region.world  # this should only happen before initialization
                    return region
            raise RuntimeError('No such region %s for player %d' % (regionname, player))

    def get_entrance(self, entrance, player):
        if isinstance(entrance, Entrance):
            return entrance
        try:
            return self._entrance_cache[(entrance, player)]
        except KeyError:
            for region in self.regions:
                for exit in region.exits:
                    if exit.name == entrance and exit.player == player:
                        self._entrance_cache[(entrance, player)] = exit
                        return exit
            raise RuntimeError('No such entrance %s for player %d' % (entrance, player))

    def remove_entrance(self, entrance, player):
        if (entrance, player) in self._entrance_cache.keys():
            del self._entrance_cache[(entrance, player)]

    def get_location(self, location, player):
        if isinstance(location, Location):
            return location
        try:
            return self._location_cache[(location, player)]
        except KeyError:
            for region in self.regions:
                for r_location in region.locations:
                    if r_location.name == location and r_location.player == player:
                        self._location_cache[(location, player)] = r_location
                        return r_location
        raise RuntimeError('No such location %s for player %d' % (location, player))

    def get_dungeon(self, dungeonname, player):
        if isinstance(dungeonname, Dungeon):
            return dungeonname

        for dungeon in self.dungeons:
            if dungeon.name == dungeonname and dungeon.player == player:
                return dungeon
        raise RuntimeError('No such dungeon %s for player %d' % (dungeonname, player))

    def get_door(self, doorname, player):
        if isinstance(doorname, Door):
            return doorname
        try:
            return self._door_cache[(doorname, player)]
        except KeyError:
            for door in self.doors:
                if door.name == doorname and door.player == player:
                    self._door_cache[(doorname, player)] = door
                    return door
            raise RuntimeError('No such door %s for player %d' % (doorname, player))

    def get_portal(self, portal_name, player):
        if isinstance(portal_name, Portal):
            return portal_name
        try:
            return self._portal_cache[(portal_name, player)]
        except KeyError:
            for portal in self.dungeon_portals[player]:
                if portal.name == portal_name and portal.player == player:
                    self._portal_cache[(portal_name, player)] = portal
                    return portal
            raise RuntimeError('No such portal %s for player %d' % (portal_name, player))

    def check_for_door(self, doorname, player):
        if isinstance(doorname, Door):
            return doorname
        try:
            return self._door_cache[(doorname, player)]
        except KeyError:
            for door in self.doors:
                if door.name == doorname and door.player == player:
                    self._door_cache[(doorname, player)] = door
                    return door
            return None

    def check_for_entrance(self, entrance, player):
        if isinstance(entrance, Entrance):
            return entrance
        try:
            return self._entrance_cache[(entrance, player)]
        except KeyError:
            for region in self.regions:
                for ext in region.exits:
                    if ext.name == entrance and ext.player == player:
                        self._entrance_cache[(entrance, player)] = ext
                        return ext
            return None

    def get_room(self, room_idx, player):
        if isinstance(room_idx, Room):
            return room_idx
        try:
            return self._room_cache[(room_idx, player)]
        except KeyError:
            for room in self.rooms:
                if room.index == room_idx and room.player == player:
                    self._room_cache[(room_idx, player)] = room
                    return room
            raise RuntimeError('No such room %s for player %d' % (room_idx, player))

    def get_all_state(self, keys=False):
        ret = CollectionState(self)

        def soft_collect(item):
            if item.name.startswith('Progressive '):
                if 'Sword' in item.name:
                    if ret.has('Golden Sword', item.player):
                        pass
                    elif ret.has('Tempered Sword', item.player) and self.difficulty_requirements[item.player].progressive_sword_limit >= 4:
                        ret.prog_items['Golden Sword', item.player] += 1
                    elif ret.has('Master Sword', item.player) and self.difficulty_requirements[item.player].progressive_sword_limit >= 3:
                        ret.prog_items['Tempered Sword', item.player] += 1
                    elif ret.has('Fighter Sword', item.player) and self.difficulty_requirements[item.player].progressive_sword_limit >= 2:
                        ret.prog_items['Master Sword', item.player] += 1
                    elif self.difficulty_requirements[item.player].progressive_sword_limit >= 1:
                        ret.prog_items['Fighter Sword', item.player] += 1
                elif 'Glove' in item.name:
                    if ret.has('Titans Mitts', item.player):
                        pass
                    elif ret.has('Power Glove', item.player):
                        ret.prog_items['Titans Mitts', item.player] += 1
                    else:
                        ret.prog_items['Power Glove', item.player] += 1
                elif 'Shield' in item.name:
                    if ret.has('Mirror Shield', item.player):
                        pass
                    elif ret.has('Red Shield', item.player) and self.difficulty_requirements[item.player].progressive_shield_limit >= 3:
                        ret.prog_items['Mirror Shield', item.player] += 1
                    elif ret.has('Blue Shield', item.player) and self.difficulty_requirements[item.player].progressive_shield_limit >= 2:
                        ret.prog_items['Red Shield', item.player] += 1
                    elif self.difficulty_requirements[item.player].progressive_shield_limit >= 1:
                        ret.prog_items['Blue Shield', item.player] += 1
                elif 'Bow' in item.name:
                    if ret.has('Silver Arrows', item.player):
                        pass
                    elif ret.has('Bow', item.player) and self.difficulty_requirements[item.player].progressive_bow_limit >= 2:
                        ret.prog_items['Silver Arrows', item.player] += 1
                    elif self.difficulty_requirements[item.player].progressive_bow_limit >= 1:
                        ret.prog_items['Bow', item.player] += 1
            elif item.name.startswith('Bottle'):
                if ret.bottle_count(item.player) < self.difficulty_requirements[item.player].progressive_bottle_limit:
                    ret.prog_items[item.name, item.player] += 1
            elif item.advancement or item.smallkey or item.bigkey:
                ret.prog_items[item.name, item.player] += 1

        for item in self.itempool:
            soft_collect(item)

        if keys:
            for p in range(1, self.players + 1):
                key_list = []
                player_dungeons = [x for x in self.dungeons if x.player == p]
                for dungeon in player_dungeons:
                    if dungeon.big_key is not None:
                        key_list += [dungeon.big_key.name]
                    if len(dungeon.small_keys) > 0:
                        key_list += [x.name for x in dungeon.small_keys]
                from Items import ItemFactory
                for item in ItemFactory(key_list, p):
                    soft_collect(item)
        ret.sweep_for_events()
        return ret

    def get_items(self):
        return [loc.item for loc in self.get_filled_locations()] + self.itempool

    def find_items(self, item, player):
        return [location for location in self.get_locations() if location.item is not None and location.item.name == item and location.item.player == player]

    def find_items_not_key_only(self, item, player):
        return [location for location in self.get_locations() if location.item is not None and location.item.name == item and location.item.player == player and location.forced_item is None]

    def push_precollected(self, item):
        item.world = self
        if (item.smallkey and self.keyshuffle[item.player]) or (item.bigkey and self.bigkeyshuffle[item.player]):
            item.advancement = True
        self.precollected_items.append(item)
        self.state.collect(item, True)

    def push_item(self, location, item, collect=True):
        if not isinstance(location, Location):
            raise RuntimeError('Cannot assign item %s to location %s (player %d).' % (item, location, item.player))

        if location.can_fill(self.state, item, False):
            location.item = item
            item.location = location
            item.world = self
            if collect:
                self.state.collect(item, location.event, location)

            logging.getLogger('').debug('Placed %s at %s', item, location)
        else:
            raise RuntimeError('Cannot assign item %s to location %s.' % (item, location))

    def get_entrances(self):
        if self._cached_entrances is None:
            self._cached_entrances = []
            for region in self.regions:
                self._cached_entrances.extend(region.entrances)
        return self._cached_entrances

    def clear_entrance_cache(self):
        self._cached_entrances = None

    def get_locations(self):
        if self._cached_locations is None:
            self._cached_locations = []
            for region in self.regions:
                self._cached_locations.extend(region.locations)
        return self._cached_locations

    def clear_location_cache(self):
        self._cached_locations = None

    def get_unfilled_locations(self, player=None):
        return [location for location in self.get_locations() if (player is None or location.player == player) and location.item is None]

    def get_filled_locations(self, player=None):
        return [location for location in self.get_locations() if (player is None or location.player == player) and location.item is not None]

    def get_reachable_locations(self, state=None, player=None):
        if state is None:
            state = self.state
        return [location for location in self.get_locations() if (player is None or location.player == player) and location.can_reach(state)]

    def get_placeable_locations(self, state=None, player=None):
        if state is None:
            state = self.state
        return [location for location in self.get_locations() if (player is None or location.player == player) and location.item is None and location.can_reach(state)]

    def unlocks_new_location(self, item):
        temp_state = self.state.copy()
        temp_state.collect(item, True)

        for location in self.get_unfilled_locations():
            if temp_state.can_reach(location) and not self.state.can_reach(location):
                return True

        return False

    def has_beaten_game(self, state, player=None):
        if player:
            return state.has('Triforce', player)
        else:
            return all((self.has_beaten_game(state, p) for p in range(1, self.players + 1)))

    def can_beat_game(self, starting_state=None):
        if starting_state:
            state = starting_state.copy()
        else:
            state = CollectionState(self)

        if self.has_beaten_game(state):
            return True

        prog_locations = [location for location in self.get_locations() if location.item is not None and (location.item.advancement or location.event) and location not in state.locations_checked]

        while prog_locations:
            sphere = []
            # build up spheres of collection radius. Everything in each sphere is independent from each other in dependencies and only depends on lower spheres
            for location in prog_locations:
                if location.can_reach(state) and state.not_flooding_a_key(state.world, location):
                    sphere.append(location)

            if not sphere:
                # ran out of places and did not finish yet, quit
                return False

            for location in sphere:
                prog_locations.remove(location)
                state.collect(location.item, True, location)

            if self.has_beaten_game(state):
                return True

        return False


class CollectionState(object):

    def __init__(self, parent):
        self.prog_items = Counter()
        self.world = parent
        self.reachable_regions = {player: dict() for player in range(1, parent.players + 1)}
        self.blocked_connections = {player: dict() for player in range(1, parent.players + 1)}
        self.events = []
        self.path = {}
        self.locations_checked = set()
        self.stale = {player: True for player in range(1, parent.players + 1)}
        for item in parent.precollected_items:
            self.collect(item, True)

    def update_reachable_regions(self, player):
        self.stale[player] = False
        rrp = self.reachable_regions[player]
        bc = self.blocked_connections[player]

        # init on first call - this can't be done on construction since the regions don't exist yet
        start = self.world.get_region('Menu', player)
        if not start in rrp:
            rrp[start] = CrystalBarrier.Orange
            for exit in start.exits:
                bc[exit] = CrystalBarrier.Orange

        queue = deque(self.blocked_connections[player].items())

        # run BFS on all connections, and keep track of those blocked by missing items
        while True:
            try:
                connection, crystal_state = queue.popleft()
                new_region = connection.connected_region
                if new_region is None or new_region in rrp and (new_region.type != RegionType.Dungeon or (rrp[new_region] & crystal_state) == crystal_state):
                    bc.pop(connection, None)
                elif connection.can_reach(self):
                    if new_region.type == RegionType.Dungeon:
                        new_crystal_state = crystal_state
                        for exit in new_region.exits:
                            door = exit.door
                            if door is not None and door.crystal == CrystalBarrier.Either and door.entrance.can_reach(self):
                                new_crystal_state = CrystalBarrier.Either
                                break
                        if new_region in rrp:
                            new_crystal_state |= rrp[new_region]

                        rrp[new_region] = new_crystal_state

                        for exit in new_region.exits:
                            door = exit.door
                            if door is not None and not door.blocked:
                                door_crystal_state = door.crystal if door.crystal else new_crystal_state
                                bc[exit] = door_crystal_state
                                queue.append((exit, door_crystal_state))
                            elif door is None:
                                queue.append((exit, new_crystal_state))
                    else:
                        new_crystal_state = CrystalBarrier.Orange
                        rrp[new_region] = new_crystal_state
                        bc.pop(connection, None)
                        for exit in new_region.exits:
                            bc[exit] = new_crystal_state
                            queue.append((exit, new_crystal_state))

                    self.path[new_region] = (new_region.name, self.path.get(connection, None))

                    # Retry connections if the new region can unblock them
                    if new_region.name in indirect_connections:
                        new_entrance = self.world.get_entrance(indirect_connections[new_region.name], player)
                        if new_entrance in bc and new_entrance not in queue and new_entrance.parent_region in rrp:
                            queue.append((new_entrance, rrp[new_entrance.parent_region]))
            except IndexError:
                break


    def copy(self):
        ret = CollectionState(self.world)
        ret.prog_items = self.prog_items.copy()
        ret.reachable_regions = {player: copy.copy(self.reachable_regions[player]) for player in range(1, self.world.players + 1)}
        ret.blocked_connections = {player: copy.copy(self.blocked_connections[player]) for player in range(1, self.world.players + 1)}
        ret.events = copy.copy(self.events)
        ret.path = copy.copy(self.path)
        ret.locations_checked = copy.copy(self.locations_checked)
        return ret

    def can_reach(self, spot, resolution_hint=None, player=None):
        try:
            spot_type = spot.spot_type
        except AttributeError:
            # try to resolve a name
            if resolution_hint == 'Location':
                spot = self.world.get_location(spot, player)
            elif resolution_hint == 'Entrance':
                spot = self.world.get_entrance(spot, player)
            else:
                # default to Region
                spot = self.world.get_region(spot, player)

        return spot.can_reach(self)


    def sweep_for_events(self, key_only=False, locations=None):
        # this may need improvement
        if locations is None:
            locations = self.world.get_filled_locations()
        new_locations = True
        checked_locations = 0
        while new_locations:
            reachable_events = [location for location in locations if location.event and
                                (not key_only or (not self.world.keyshuffle[location.item.player] and location.item.smallkey) or (not self.world.bigkeyshuffle[location.item.player] and location.item.bigkey))
                                and location.can_reach(self)]
            reachable_events = self._do_not_flood_the_keys(reachable_events)
            for event in reachable_events:
                if (event.name, event.player) not in self.events:
                    self.events.append((event.name, event.player))
                    self.collect(event.item, True, event)
            new_locations = len(reachable_events) > checked_locations
            checked_locations = len(reachable_events)


    def can_reach_blue(self, region, player):
        return region in self.reachable_regions[player] and self.reachable_regions[player][region] in [CrystalBarrier.Blue, CrystalBarrier.Either]

    def can_reach_orange(self, region, player):
        return region in self.reachable_regions[player] and self.reachable_regions[player][region] in [CrystalBarrier.Orange, CrystalBarrier.Either]

    def _do_not_flood_the_keys(self, reachable_events):
        adjusted_checks = list(reachable_events)
        for event in reachable_events:
            if event.name in flooded_keys.keys():
                flood_location = self.world.get_location(flooded_keys[event.name], event.player)
                if flood_location.item and flood_location not in self.locations_checked:
                    adjusted_checks.remove(event)
        if len(adjusted_checks) < len(reachable_events):
            return adjusted_checks
        return reachable_events

    def not_flooding_a_key(self, world, location):
        if location.name in flooded_keys.keys():
            flood_location = world.get_location(flooded_keys[location.name], location.player)
            item = flood_location.item
            item_is_important = False if not item else item.advancement or item.bigkey or item.smallkey
            return flood_location in self.locations_checked or not item_is_important or location.parent_region.name not in ['Swamp Trench 1 Alcove', 'Swamp Trench 2 Alcove']
        return True

    def has(self, item, player, count=1):
        if count == 1:
            return (item, player) in self.prog_items
        return self.prog_items[item, player] >= count

    def has_sm_key(self, item, player, count=1):
        if self.world.retro[player]:
            if self.world.mode[player] == 'standard' and self.world.doorShuffle[player] == 'vanilla' and item == 'Small Key (Escape)':
                return True  # Cannot access the shop until escape is finished.  This is safe because the key is manually placed in make_custom_item_pool
            return self.can_buy_unlimited('Small Key (Universal)', player)
        if count == 1:
            return (item, player) in self.prog_items
        return self.prog_items[item, player] >= count

    def can_buy_unlimited(self, item, player):
        for shop in self.world.shops:
            if shop.region.player == player and shop.has_unlimited(item) and shop.region.can_reach(self):
                return True
        return False

    def item_count(self, item, player):
        return self.prog_items[item, player]

    def has_crystals(self, count, player):
        crystals = ['Crystal 1', 'Crystal 2', 'Crystal 3', 'Crystal 4', 'Crystal 5', 'Crystal 6', 'Crystal 7']
        return len([crystal for crystal in crystals if self.has(crystal, player)]) >= count

    def can_lift_rocks(self, player):
        return self.has('Power Glove', player) or self.has('Titans Mitts', player)

    def has_bottle(self, player):
        return self.bottle_count(player) > 0

    def bottle_count(self, player):
        return len([item for (item, itemplayer) in self.prog_items if item.startswith('Bottle') and itemplayer == player])

    def has_hearts(self, player, count):
        # Warning: This only considers items that are marked as advancement items
        return self.heart_count(player) >= count

    def heart_count(self, player):
        # Warning: This only considers items that are marked as advancement items
        diff = self.world.difficulty_requirements[player]
        return (
            min(self.item_count('Boss Heart Container', player), diff.boss_heart_container_limit)
            + self.item_count('Sanctuary Heart Container', player)
            + min(self.item_count('Piece of Heart', player), diff.heart_piece_limit) // 4
            + 3 # starting hearts
        )

    def can_lift_heavy_rocks(self, player):
        return self.has('Titans Mitts', player)

    def can_extend_magic(self, player, smallmagic=16, fullrefill=False): #This reflects the total magic Link has, not the total extra he has.
        basemagic = 8
        if self.has('Magic Upgrade (1/4)', player):
            basemagic = 32
        elif self.has('Magic Upgrade (1/2)', player):
            basemagic = 16
        if self.can_buy_unlimited('Green Potion', player) or self.can_buy_unlimited('Blue Potion', player):
            if self.world.difficulty_adjustments[player] == 'hard' and not fullrefill:
                basemagic = basemagic + int(basemagic * 0.5 * self.bottle_count(player))
            elif self.world.difficulty_adjustments[player] == 'expert' and not fullrefill:
                basemagic = basemagic + int(basemagic * 0.25 * self.bottle_count(player))
            else:
                basemagic = basemagic + basemagic * self.bottle_count(player)
        return basemagic >= smallmagic

    def can_kill_most_things(self, player, enemies=5):
        return (self.has_blunt_weapon(player)
                or self.has('Cane of Somaria', player)
                or (self.has('Cane of Byrna', player) and (enemies < 6 or self.can_extend_magic(player)))
                or self.can_shoot_arrows(player)
                or self.has('Fire Rod', player)
               )

    def can_shoot_arrows(self, player):
        if self.world.retro[player]:
            #todo: Non-progressive silvers grant wooden arrows, but progressive bows do not.  Always require shop arrows to be safe
            return self.has('Bow', player) and self.can_buy_unlimited('Single Arrow', player)
        return self.has('Bow', player)

    def can_get_good_bee(self, player):
        cave = self.world.get_region('Good Bee Cave', player)
        return (
            self.has_bottle(player) and
            self.has('Bug Catching Net', player) and
            (self.has_Boots(player) or (self.has_sword(player) and self.has('Quake', player))) and
            cave.can_reach(self) and
            self.is_not_bunny(cave, player)
        )

    def has_sword(self, player):
        return self.has('Fighter Sword', player) or self.has('Master Sword', player) or self.has('Tempered Sword', player) or self.has('Golden Sword', player)

    def has_beam_sword(self, player):
        return self.has('Master Sword', player) or self.has('Tempered Sword', player) or self.has('Golden Sword', player)

    def has_blunt_weapon(self, player):
        return self.has_sword(player) or self.has('Hammer', player)

    def has_Mirror(self, player):
        return self.has('Magic Mirror', player)

    def has_Boots(self, player):
        return self.has('Pegasus Boots', player)

    def has_Pearl(self, player):
        return self.has('Moon Pearl', player)

    def has_fire_source(self, player):
        return self.has('Fire Rod', player) or self.has('Lamp', player)

    def can_flute(self, player):
        lw = self.world.get_region('Light World', player)
        return self.has('Ocarina', player) and lw.can_reach(self) and self.is_not_bunny(lw, player)

    def can_melt_things(self, player):
        return self.has('Fire Rod', player) or (self.has('Bombos', player) and self.has_sword(player))

    def can_avoid_lasers(self, player):
        return self.has('Mirror Shield', player) or self.has('Cane of Byrna', player) or self.has('Cape', player)

    def is_not_bunny(self, region, player):
        if self.has_Pearl(player):
            return True

        return region.is_light_world if self.world.mode[player] != 'inverted' else region.is_dark_world

    def can_reach_light_world(self, player):
        if True in [i.is_light_world for i in self.reachable_regions[player]]:
            return True
        return False

    def can_reach_dark_world(self, player):
        if True in [i.is_dark_world for i in self.reachable_regions[player]]:
            return True
        return False

    def has_misery_mire_medallion(self, player):
        return self.has(self.world.required_medallions[player][0], player)

    def has_turtle_rock_medallion(self, player):
        return self.has(self.world.required_medallions[player][1], player)

    def collect(self, item, event=False, location=None):
        if location:
            self.locations_checked.add(location)
        changed = False
        if item.name.startswith('Progressive '):
            if 'Sword' in item.name:
                if self.has('Golden Sword', item.player):
                    pass
                elif self.has('Tempered Sword', item.player) and self.world.difficulty_requirements[item.player].progressive_sword_limit >= 4:
                    self.prog_items['Golden Sword', item.player] += 1
                    changed = True
                elif self.has('Master Sword', item.player) and self.world.difficulty_requirements[item.player].progressive_sword_limit >= 3:
                    self.prog_items['Tempered Sword', item.player] += 1
                    changed = True
                elif self.has('Fighter Sword', item.player) and self.world.difficulty_requirements[item.player].progressive_sword_limit >= 2:
                    self.prog_items['Master Sword', item.player] += 1
                    changed = True
                elif self.world.difficulty_requirements[item.player].progressive_sword_limit >= 1:
                    self.prog_items['Fighter Sword', item.player] += 1
                    changed = True
            elif 'Glove' in item.name:
                if self.has('Titans Mitts', item.player):
                    pass
                elif self.has('Power Glove', item.player):
                    self.prog_items['Titans Mitts', item.player] += 1
                    changed = True
                else:
                    self.prog_items['Power Glove', item.player] += 1
                    changed = True
            elif 'Shield' in item.name:
                if self.has('Mirror Shield', item.player):
                    pass
                elif self.has('Red Shield', item.player) and self.world.difficulty_requirements[item.player].progressive_shield_limit >= 3:
                    self.prog_items['Mirror Shield', item.player] += 1
                    changed = True
                elif self.has('Blue Shield', item.player)  and self.world.difficulty_requirements[item.player].progressive_shield_limit >= 2:
                    self.prog_items['Red Shield', item.player] += 1
                    changed = True
                elif self.world.difficulty_requirements[item.player].progressive_shield_limit >= 1:
                    self.prog_items['Blue Shield', item.player] += 1
                    changed = True
            elif 'Bow' in item.name:
                if self.has('Silver Arrows', item.player):
                    pass
                elif self.has('Bow', item.player):
                    self.prog_items['Silver Arrows', item.player] += 1
                    changed = True
                else:
                    self.prog_items['Bow', item.player] += 1
                    changed = True
            elif 'Armor' in item.name:
                if self.has('Red Mail', item.player):
                    pass
                elif self.has('Blue Mail', item.player):
                    self.prog_items['Red Mail', item.player] += 1
                    changed = True
                else:
                    self.prog_items['Blue Mail', item.player] += 1
                    changed = True

        elif item.name.startswith('Bottle'):
            if self.bottle_count(item.player) < self.world.difficulty_requirements[item.player].progressive_bottle_limit:
                self.prog_items[item.name, item.player] += 1
                changed = True
        elif event or item.advancement:
            self.prog_items[item.name, item.player] += 1
            changed = True

        self.stale[item.player] = True

        if changed:
            if not event:
                self.sweep_for_events()

    def remove(self, item):
        if item.advancement:
            to_remove = item.name
            if to_remove.startswith('Progressive '):
                if 'Sword' in to_remove:
                    if self.has('Golden Sword', item.player):
                        to_remove = 'Golden Sword'
                    elif self.has('Tempered Sword', item.player):
                        to_remove = 'Tempered Sword'
                    elif self.has('Master Sword', item.player):
                        to_remove = 'Master Sword'
                    elif self.has('Fighter Sword', item.player):
                        to_remove = 'Fighter Sword'
                    else:
                        to_remove = None
                elif 'Glove' in item.name:
                    if self.has('Titans Mitts', item.player):
                        to_remove = 'Titans Mitts'
                    elif self.has('Power Glove', item.player):
                        to_remove = 'Power Glove'
                    else:
                        to_remove = None
                elif 'Shield' in item.name:
                    if self.has('Mirror Shield', item.player):
                        to_remove = 'Mirror Shield'
                    elif self.has('Red Shield', item.player):
                        to_remove = 'Red Shield'
                    elif self.has('Blue Shield', item.player):
                        to_remove = 'Blue Shield'
                    else:
                        to_remove = 'None'
                elif 'Bow' in item.name:
                    if self.has('Silver Arrows', item.player):
                        to_remove = 'Silver Arrows'
                    elif self.has('Bow', item.player):
                        to_remove = 'Bow'
                    else:
                        to_remove = None

            if to_remove is not None:

                self.prog_items[to_remove, item.player] -= 1
                if self.prog_items[to_remove, item.player] < 1:
                    del (self.prog_items[to_remove, item.player])
                # invalidate caches, nothing can be trusted anymore now
                self.reachable_regions[item.player] = dict()
                self.blocked_connections[item.player] = dict()
                self.stale[item.player] = True

    def __getattr__(self, item):
        if item.startswith('can_reach_'):
            return self.can_reach(item[10])
        #elif item.startswith('has_'):
        #    return self.has(item[4])
        if item == '__len__':
            return

        raise RuntimeError('Cannot parse %s.' % item)

@unique
class RegionType(Enum):
    Menu = 0
    LightWorld = 1
    DarkWorld = 2
    Cave = 3  # Also includes Houses
    Dungeon = 4

    @property
    def is_indoors(self):
        """Shorthand for checking if Cave or Dungeon"""
        return self in (RegionType.Cave, RegionType.Dungeon)


class Region(object):

    def __init__(self, name, type, hint, player):
        self.name = name
        self.type = type
        self.entrances = []
        self.exits = []
        self.locations = []
        self.dungeon = None
        self.shop = None
        self.world = None
        self.is_light_world = False # will be set aftermaking connections.
        self.is_dark_world = False
        self.spot_type = 'Region'
        self.hint_text = hint
        self.recursion_count = 0
        self.player = player
        self.crystal_switch = False

    def can_reach(self, state):
        if state.stale[self.player]:
            state.update_reachable_regions(self.player)
        return self in state.reachable_regions[self.player]

    def can_reach_private(self, state):
        for entrance in self.entrances:
            if entrance.can_reach(state):
                if not self in state.path:
                    state.path[self] = (self.name, state.path.get(entrance, None))
                return True
        return False

    def can_fill(self, item):
        inside_dungeon_item = ((item.smallkey and not self.world.keyshuffle[item.player])
                               or (item.bigkey and not self.world.bigkeyshuffle[item.player])
                               or (item.map and not self.world.mapshuffle[item.player])
                               or (item.compass and not self.world.compassshuffle[item.player]))
        sewer_hack = self.world.mode[item.player] == 'standard' and item.name == 'Small Key (Escape)'
        if sewer_hack or inside_dungeon_item:
            return self.dungeon and self.dungeon.is_dungeon_item(item) and item.player == self.player

        return True

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return self.world.get_name_string_for_object(self) if self.world else f'{self.name} (Player {self.player})'


class Entrance(object):

    def __init__(self, player, name='', parent=None):
        self.name = name
        self.parent_region = parent
        self.connected_region = None
        self.target = None
        self.addresses = None
        self.spot_type = 'Entrance'
        self.recursion_count = 0
        self.vanilla = None
        self.access_rule = lambda state: True
        self.player = player
        self.door = None
        self.hide_path = False

    def can_reach(self, state):
        if self.parent_region.can_reach(state) and self.access_rule(state):
            if not self.hide_path and not self in state.path:
                state.path[self] = (self.name, state.path.get(self.parent_region, (self.parent_region.name, None)))
            return True

        return False

    def connect(self, region, addresses=None, target=None, vanilla=None):
        self.connected_region = region
        self.target = target
        self.addresses = addresses
        self.vanilla = vanilla
        region.entrances.append(self)

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        world = self.parent_region.world if self.parent_region else None
        return world.get_name_string_for_object(self) if world else f'{self.name} (Player {self.player})'


class Dungeon(object):

    def __init__(self, name, regions, big_key, small_keys, dungeon_items, player, dungeon_id):
        self.name = name
        self.regions = regions
        self.big_key = big_key
        self.small_keys = small_keys
        self.dungeon_items = dungeon_items
        self.bosses = dict()
        self.player = player
        self.world = None
        self.dungeon_id = dungeon_id

        self.entrance_regions = []

    @property
    def boss(self):
        return self.bosses.get(None, None)

    @boss.setter
    def boss(self, value):
        self.bosses[None] = value

    @property
    def keys(self):
        return self.small_keys + ([self.big_key] if self.big_key else [])

    @property
    def all_items(self):
        return self.dungeon_items + self.keys

    def is_dungeon_item(self, item):
        return item.player == self.player and item.name in [dungeon_item.name for dungeon_item in self.all_items]

    def count_dungeon_item(self):
        return len(self.dungeon_items) + 1 if self.big_key_required else 0 + self.key_number

    def incomplete_paths(self):
        ret = 0
        for path in self.paths:
            if not self.path_completion[path]:
                ret += 1
        return ret

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return self.world.get_name_string_for_object(self) if self.world else f'{self.name} (Player {self.player})'


@unique
class DoorType(Enum):
    Normal = 1
    SpiralStairs = 2
    StraightStairs = 3
    Ladder = 4
    Open = 5
    Hole = 6
    Warp = 7
    Interior = 8
    Logical = 9


@unique
class Direction(Enum):
    North = 0
    West = 1
    South = 2
    East = 3
    Up = 4
    Down = 5


@unique
class Hook(Enum):
    North = 0
    West = 1
    South = 2
    East = 3
    Stairs = 4


hook_dir_map = {
    Direction.North: Hook.North,
    Direction.South: Hook.South,
    Direction.West: Hook.West,
    Direction.East: Hook.East,
}


def hook_from_door(door):
    if door.type == DoorType.SpiralStairs:
        return Hook.Stairs
    if door.type in [DoorType.Normal, DoorType.Open, DoorType.StraightStairs]:
        return hook_dir_map[door.direction]
    return None


class Polarity:
    def __init__(self):
        self.vector = [0, 0, 0]

    def __len__(self):
        return len(self.vector)

    def __add__(self, other):
        result = Polarity()
        for i in range(len(self.vector)):
            result.vector[i] = pol_add[pol_idx_2[i]](self.vector[i], other.vector[i])
        return result

    def __iadd__(self, other):
        for i in range(len(self.vector)):
            self.vector[i] = pol_add[pol_idx_2[i]](self.vector[i], other.vector[i])
        return self

    def __getitem__(self, item):
        return self.vector[item]

    def __eq__(self, other):
        for i in range(len(self.vector)):
            if self.vector[i] != other.vector[i]:
                return False
        return True

    def __hash__(self):
        h = 17
        spot = self.vector[0]
        h *= 31 + (spot if spot >= 0 else spot + 100)
        spot = self.vector[1]
        h *= 43 + (spot if spot >= 0 else spot + 100)
        spot = self.vector[2]
        h *= 73 + (spot if spot >= 0 else spot + 100)
        return h

    def is_neutral(self):
        for i in range(len(self.vector)):
            if self.vector[i] != 0:
                return False
        return True

    def complement(self):
        result = Polarity()
        for i in range(len(self.vector)):
            result.vector[i] = pol_comp[pol_idx_2[i]](self.vector[i])
        return result

    def charge(self):
        result = 0
        for i in range(len(self.vector)):
            result += abs(self.vector[i])
        return result

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return f'{self.vector}'


pol_idx = {
    Direction.North: (0, 'Pos'),
    Direction.South: (0, 'Neg'),
    Direction.East: (1, 'Pos'),
    Direction.West: (1, 'Neg'),
    Direction.Up: (2, 'Mod'),
    Direction.Down: (2, 'Mod')
}
pol_idx_2 = {
    0: 'Add',
    1: 'Add',
    2: 'Mod'
}
pol_inc = {
    'Pos': lambda x: x + 1,
    'Neg': lambda x: x - 1,
    'Mod': lambda x: (x + 1) % 2
}
pol_add = {
    'Add': lambda x, y: x + y,
    'Mod': lambda x, y: (x + y) % 2
}
pol_comp = {
    'Add': lambda x: -x,
    'Mod': lambda x: 0 if x == 0 else 1
}


@unique
class PolSlot(Enum):
    NorthSouth = 0
    EastWest = 1
    Stairs = 2


class CrystalBarrier(FastEnum):
    Null = 0  # no special requirement
    Blue = 1  # blue must be down and explore state set to Blue
    Orange = 2  # orange must be down and explore state set to Orange
    Either = 3  # you choose to leave this room in Either state


class Door(object):
    def __init__(self, player, name, type, entrance=None):
        self.player = player
        self.name = name
        self.type = type
        self.direction = None

        # rom properties
        self.roomIndex = -1
        # 0,1,2 + Direction (N:0, W:3, S:6, E:9) for normal
        # 0-4 for spiral offset thing
        self.doorIndex = -1
        self.layer = -1  # 0 for normal floor, 1 for the inset layer
        self.pseudo_bg = 0  # 0 for normal floor, 1 for pseudo bg
        self.toggle = False
        self.trapFlag = 0x0
        self.quadrant = 2
        self.shiftX = 78
        self.shiftY = 78
        self.zeroHzCam = False
        self.zeroVtCam = False
        self.doorListPos = -1
        self.edge_id = None
        self.edge_width = None

        #portal items
        self.portalAble = False
        self.roomLayout = 0x22  # free scroll-  both directions
        self.entranceFlag = False
        self.deadEnd = False
        self.passage = True
        self.dungeonLink = None
        self.bk_shuffle_req = False
        # self.incognitoPos = -1
        # self.sectorLink = False

        # logical properties
        # self.connected = False  # combine with Dest?
        self.dest = None
        self.blocked = False  # Indicates if the door is normally blocked off as an exit. (Sanc door or always closed)
        self.stonewall = False  # Indicate that the door cannot be enter until exited (Desert Torches, PoD Eye Statue)
        self.smallKey = False  # There's a small key door on this side
        self.bigKey = False  # There's a big key door on this side
        self.ugly = False  # Indicates that it can't be seen from the front (e.g. back of a big key door)
        self.crystal = CrystalBarrier.Null  # How your crystal state changes if you use this door
        self.req_event = None  # if a dungeon event is required for this door - swamp palace mostly
        self.controller = None
        self.dependents = []
        self.dead = False

        self.entrance = entrance
        if entrance is not None:
            entrance.door = self

    def getAddress(self):
        if self.type in [DoorType.Normal, DoorType.StraightStairs]:
            return 0x13A000 + normal_offset_table[self.roomIndex] * 24 + (self.doorIndex + self.direction.value * 3) * 2
        elif self.type == DoorType.SpiralStairs:
            return 0x13B000 + (spiral_offset_table[self.roomIndex] + self.doorIndex) * 4
        elif self.type == DoorType.Open:
            base_address = {
                Direction.North: 0x13C500,
                Direction.South: 0x13C521,
                Direction.West: 0x13C542,
                Direction.East: 0x13C55D,
            }
            return base_address[self.direction] + self.edge_id * 3

    def getTarget(self, src):
        if self.type in [DoorType.Normal, DoorType.StraightStairs]:
            bitmask = 4 * (self.layer ^ 1 if src.toggle else self.layer)
            bitmask += 0x08 * int(self.trapFlag)
            if src.type == DoorType.StraightStairs:
                bitmask += 0x40
            return [self.roomIndex, bitmask + self.doorIndex]
        if self.type == DoorType.SpiralStairs:
            bitmask = int(self.layer) << 2
            bitmask += 0x10 * int(self.zeroHzCam)
            bitmask += 0x20 * int(self.zeroVtCam)
            bitmask += 0x80 if self.direction == Direction.Up else 0
            return [self.roomIndex, bitmask + self.quadrant, self.shiftX, self.shiftY]
        if self.type == DoorType.Open:
            bitmask = self.edge_id
            bitmask += 0x10 * (self.layer ^ 1 if src.toggle else self.layer)
            bitmask += 0x80
            if src.type == DoorType.StraightStairs:
                bitmask += 0x40
            if src.type == DoorType.Open:
                bitmask += 0x20 * self.quadrant
                fraction = 0x10 * multiply_lookup[src.edge_width][self.edge_width]
                fraction += divisor_lookup[src.edge_width][self.edge_width]
                return [self.roomIndex, bitmask, fraction]
            else:
                bitmask += 0x20 * self.quad_indicator()
                return [self.roomIndex, bitmask]

    def quad_indicator(self):
        if self.direction in [Direction.North, Direction.South]:
            return self.quadrant & 0x1
        elif self.direction in [Direction.East, Direction.West]:
            return (self.quadrant & 0x2) >> 1
        return 0

    def dir(self, direction, room, doorIndex, layer):
        self.direction = direction
        self.roomIndex = room
        self.doorIndex = doorIndex
        self.layer = layer
        return self

    def ss(self, quadrant, shift_y, shift_x, zero_hz_cam=False, zero_vt_cam=False):
        self.quadrant = quadrant
        self.shiftY = shift_y
        self.shiftX = shift_x
        self.zeroHzCam = zero_hz_cam
        self.zeroVtCam = zero_vt_cam
        return self

    def edge(self, edge_id, quadrant, width):
        self.edge_id = edge_id
        self.quadrant = quadrant
        self.edge_width = width
        return self

    def small_key(self):
        self.smallKey = True
        return self

    def big_key(self):
        self.bigKey = True
        return self

    def toggler(self):
        self.toggle = True
        return self

    def no_exit(self):
        self.blocked = True
        return self

    def no_entrance(self):
        self.stonewall = True
        return self

    def trap(self, trapFlag):
        self.trapFlag = trapFlag
        return self

    def pos(self, pos):
        self.doorListPos = pos
        return self

    def event(self, event):
        self.req_event = event
        return self

    def barrier(self, crystal):
        self.crystal = crystal
        return self

    def c_switch(self):
        self.crystal = CrystalBarrier.Either
        return self

    def kill(self):
        self.dead = True
        return self

    def portal(self, quadrant, roomLayout, pseudo_bg=0):
        self.quadrant = quadrant
        self.roomLayout = roomLayout
        self.pseudo_bg = pseudo_bg
        self.portalAble = True
        return self

    def dead_end(self, allowPassage=False):
        self.deadEnd = True
        if allowPassage:
            self.passage = True
        else:
            self.passage = False

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return '%s' % self.name


class Sector(object):

    def __init__(self):
        self.regions = []
        self.outstanding_doors = []
        self.name = None
        self.r_name_set = None
        self.chest_locations = 0
        self.key_only_locations = 0
        self.c_switch = False
        self.orange_barrier = False
        self.blue_barrier = False
        self.bk_required = False
        self.bk_provided = False
        self.conn_balance = None
        self.branch_factor = None
        self.dead_end_cnt = None
        self.entrance_sector = None
        self.destination_entrance = False
        self.equations = None

    def region_set(self):
        if self.r_name_set is None:
            self.r_name_set = dict.fromkeys(map(lambda r: r.name, self.regions))
        return self.r_name_set.keys()

    def polarity(self):
        pol = Polarity()
        for door in self.outstanding_doors:
            idx, inc = pol_idx[door.direction]
            pol.vector[idx] = pol_inc[inc](pol.vector[idx])
        return pol

    def magnitude(self):
        magnitude = [0, 0, 0]
        for door in self.outstanding_doors:
            idx, inc = pol_idx[door.direction]
            magnitude[idx] = magnitude[idx] + 1
        return magnitude

    def hook_magnitude(self):
        magnitude = [0] * len(Hook)
        for door in self.outstanding_doors:
            idx = hook_from_door(door).value
            magnitude[idx] = magnitude[idx] + 1
        return magnitude

    def outflow(self):
        outflow = 0
        for door in self.outstanding_doors:
            if not door.blocked:
                outflow = outflow + 1
        return outflow

    def adj_outflow(self):
        outflow = 0
        for door in self.outstanding_doors:
            if not door.blocked and not door.dead:
                outflow = outflow + 1
        return outflow

    def branching_factor(self):
        if self.branch_factor is None:
            self.branch_factor = len(self.outstanding_doors)
            cnt_dead = len([x for x in self.outstanding_doors if x.dead])
            if cnt_dead > 1:
                self.branch_factor -= cnt_dead - 1
            for region in self.regions:
                for ent in region.entrances:
                    if (ent.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld] and ent.parent_region.name != 'Menu') or ent.parent_region.name == 'Sewer Drop':
                        self.branch_factor += 1
                        break  # you only ever get one allowance for an entrance region, multiple entrances don't help
        return self.branch_factor

    def branches(self):
        return max(0, self.branching_factor() - 2)

    def dead_ends(self):
        if self.dead_end_cnt is None:
            if self.branching_factor() <= 1:
                self.dead_end_cnt = 1
            else:
                dead_cnt = len([x for x in self.outstanding_doors if x.dead])
                self.dead_end_cnt = dead_cnt - 1 if dead_cnt > 2 else 0
        return self.dead_end_cnt

    def is_entrance_sector(self):
        if self.entrance_sector is None:
            self.entrance_sector = False
            for region in self.regions:
                for ent in region.entrances:
                    if ent.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld] or ent.parent_region.name == 'Sewer Drop':
                        self.entrance_sector = True
        return self.entrance_sector

    def get_start_regions(self):
        if self.is_entrance_sector():
            starts = []
            for region in self.regions:
                for ent in region.entrances:
                    if ent.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld] or ent.parent_region.name == 'Sewer Drop':
                        starts.append(region)
            return starts
        return None

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        if len(self.regions) > 0:
            return f'{self.regions[0].name}'
        return f'{next(iter(self.region_set()))}'


class Portal(object):

    def __init__(self, player, name, door, entrance_offset, exit_offset, boss_exit_idx):
        self.player = player
        self.name = name
        self.door = door
        self.ent_offset = entrance_offset
        self.exit_offset = exit_offset
        self.boss_exit_idx = boss_exit_idx
        self.default = True
        self.destination = False
        self.dependent = None
        self.deadEnd = False
        self.light_world = False

    def change_boss_exit(self, exit_idx):
        self.default = False
        self.boss_exit_idx = exit_idx

    def change_door(self, new_door):
        if new_door != self.door:
            self.default = False
            self.door = new_door

    def current_room(self):
        return self.door.roomIndex

    def relative_coords(self):
        y_rel = (self.door.roomIndex & 0xf0) >> 3 #todo: fix the shift!!!!
        x_rel = (self.door.roomIndex & 0x0f) * 2
        quad = self.door.quadrant
        if quad == 0:
            return [y_rel, y_rel, y_rel, y_rel+1, x_rel, x_rel, x_rel, x_rel+1]
        elif quad == 1:
            return [y_rel, y_rel, y_rel, y_rel+1, x_rel+1, x_rel, x_rel+1, x_rel+1]
        elif quad == 2:
            return [y_rel+1, y_rel, y_rel+1, y_rel+1, x_rel, x_rel, x_rel, x_rel+1]
        else:
            return [y_rel+1, y_rel, y_rel+1, y_rel+1, x_rel+1, x_rel, x_rel+1, x_rel+1]

    def scroll_x(self):
        x_rel = (self.door.roomIndex & 0x0f) * 2
        if self.door.doorIndex == 0:
            return [0x00, x_rel]
        elif self.door.doorIndex == 1:
            return [0x80, x_rel]
        else:
            return [0x00, x_rel+1]

    def scroll_y(self):
        y_rel = ((self.door.roomIndex & 0xf0) >> 3) + 1
        return [0x10, y_rel]

    def link_y(self):
        y_rel = ((self.door.roomIndex & 0xf0) >> 3) + 1
        inset = False
        if self.door.pseudo_bg == 1 or self.door.layer == 1:
            inset = True
        return [(0xd8 if not inset else 0xc0), y_rel]

    def link_x(self):
        x_rel = (self.door.roomIndex & 0x0f) * 2
        if self.door.doorIndex == 0:
            return [0x78, x_rel]
        elif self.door.doorIndex == 1:
            return [0xf8, x_rel]
        else:
            return [0x78, x_rel+1]

    # def camera_y(self):
    #     return [0x87, 0x01]

    def camera_x(self):
        if self.door.doorIndex == 0:
            return [0x7f, 0x00]
        elif self.door.doorIndex == 1:
            return [0xff, 0x00]
        else:
            return [0x7f, 0x01]

    def bg_setting(self):
        if self.door.layer == 0:
            return 0x00 | self.door.pseudo_bg
        else:
            return 0x10 | self.door.pseudo_bg

    def hv_scroll(self):
        return self.door.roomLayout

    def scroll_quad(self):
        quad = self.door.quadrant
        if quad == 0:
            return 0x00
        elif quad == 1:
            return 0x10
        elif quad == 2:
            return 0x02
        else:
            return 0x12

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return f'{self.name}:{self.door.name}'


class DungeonInfo(object):
    def __init__(self, name):
        self.name = name
        self.total = 0
        self.required_passage = {}
        self.sole_entrance = None
        # self.dead_ends = 0  total - 1 - req = dead_ends possible


class Boss(object):
    def __init__(self, name, enemizer_name, defeat_rule, player):
        self.name = name
        self.enemizer_name = enemizer_name
        self.defeat_rule = defeat_rule
        self.player = player

    def can_defeat(self, state):
        return self.defeat_rule(state, self.player)

class Location(object):
    def __init__(self, player, name='', address=None, crystal=False, hint_text=None, parent=None, forced_item=None, player_address=None):
        self.name = name
        self.parent_region = parent
        if forced_item is not None:
          from Items import ItemFactory
          self.forced_item = ItemFactory([forced_item], player)[0]
          self.item = self.forced_item
          self.item.location = self
          self.event = True
        else:
          self.forced_item = None
          self.item = None
          self.event = False
        self.crystal = crystal
        self.address = address
        self.player_address = player_address
        self.spot_type = 'Location'
        self.hint_text = hint_text if hint_text is not None else 'Hyrule'
        self.recursion_count = 0
        self.staleness_count = 0
        self.locked = False
        self.always_allow = lambda item, state: False
        self.access_rule = lambda state: True
        self.item_rule = lambda item: True
        self.player = player

    def can_fill(self, state, item, check_access=True):
        return self.always_allow(state, item) or (self.parent_region.can_fill(item) and self.item_rule(item) and (not check_access or self.can_reach(state)))

    def can_reach(self, state):
        if self.parent_region.can_reach(state) and self.access_rule(state):
            return True
        return False

    def forced_big_key(self):
        if self.forced_item and self.forced_item.bigkey and self.player == self.forced_item.player:
            item_dungeon = self.forced_item.name.split('(')[1][:-1]
            if item_dungeon == 'Escape':
                item_dungeon = 'Hyrule Castle'
            if self.parent_region.dungeon.name == item_dungeon:
                return True
        return False

    def gen_name(self):
        name = self.name
        world = self.parent_region.world if self.parent_region and self.parent_region.world else None
        if self.parent_region.dungeon and world and world.doorShuffle[self.player] == 'crossed':
            name += f' @ {self.parent_region.dungeon.name}'
        if world and world.players > 1:
            name += f' ({world.get_player_names(self.player)})'
        return name

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        world = self.parent_region.world if self.parent_region and self.parent_region.world else None
        return world.get_name_string_for_object(self) if world else f'{self.name} (Player {self.player})'


class Item(object):

    def __init__(self, name='', advancement=False, priority=False, type=None, code=None, pedestal_hint=None, pedestal_credit=None, sickkid_credit=None, zora_credit=None, witch_credit=None, fluteboy_credit=None, hint_text=None, player=None):
        self.name = name
        self.advancement = advancement
        self.priority = priority
        self.type = type
        self.pedestal_hint_text = pedestal_hint
        self.pedestal_credit_text = pedestal_credit
        self.sickkid_credit_text = sickkid_credit
        self.zora_credit_text = zora_credit
        self.magicshop_credit_text = witch_credit
        self.fluteboy_credit_text = fluteboy_credit
        self.hint_text = hint_text
        self.code = code
        self.location = None
        self.world = None
        self.player = player

    @property
    def crystal(self):
        return self.type == 'Crystal'

    @property
    def smallkey(self):
        return self.type == 'SmallKey'

    @property
    def bigkey(self):
        return self.type == 'BigKey'

    @property
    def map(self):
        return self.type == 'Map'

    @property
    def compass(self):
        return self.type == 'Compass'

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return self.world.get_name_string_for_object(self) if self.world else f'{self.name} (Player {self.player})'


# have 6 address that need to be filled
class Crystal(Item):
    pass

@unique
class ShopType(Enum):
    Shop = 0
    TakeAny = 1
    UpgradeShop = 2

class Shop(object):
    def __init__(self, region, room_id, type, shopkeeper_config, custom, locked):
        self.region = region
        self.room_id = room_id
        self.type = type
        self.inventory = [None, None, None]
        self.shopkeeper_config = shopkeeper_config
        self.custom = custom
        self.locked = locked

    @property
    def item_count(self):
        return (3 if self.inventory[2] else
                2 if self.inventory[1] else
                1 if self.inventory[0] else
                0)

    def get_bytes(self):
        # [id][roomID-low][roomID-high][doorID][zero][shop_config][shopkeeper_config][sram_index]
        entrances = self.region.entrances
        config = self.item_count
        if len(entrances) == 1 and entrances[0].name in door_addresses:
            door_id = door_addresses[entrances[0].name][0]+1
        else:
            door_id = 0
            config |= 0x40 # ignore door id
        if self.type == ShopType.TakeAny:
            config |= 0x80
        if self.type == ShopType.UpgradeShop:
            config |= 0x10 # Alt. VRAM
        return [0x00]+int16_as_bytes(self.room_id)+[door_id, 0x00, config, self.shopkeeper_config, 0x00]

    def has_unlimited(self, item):
        for inv in self.inventory:
            if inv is None:
                continue
            if inv['max'] != 0 and inv['replacement'] is not None and inv['replacement'] == item:
                return True
            elif inv['item'] is not None and inv['item'] == item:
                return True
        return False

    def clear_inventory(self):
        self.inventory = [None, None, None]

    def add_inventory(self, slot, item, price, max=0, replacement=None, replacement_price=0, create_location=False):
        self.inventory[slot] = {
            'item': item,
            'price': price,
            'max': max,
            'replacement': replacement,
            'replacement_price': replacement_price,
            'create_location': create_location
        }


class Spoiler(object):

    def __init__(self, world):
        self.world = world
        self.hashes = {}
        self.entrances = {}
        self.doors = {}
        self.doorTypes = {}
        self.lobbies = {}
        self.medallions = {}
        self.playthrough = {}
        self.unreachables = []
        self.startinventory = []
        self.locations = {}
        self.paths = {}
        self.metadata = {}
        self.shops = []
        self.bosses = OrderedDict()

    def set_entrance(self, entrance, exit, direction, player):
        if self.world.players == 1:
            self.entrances[(entrance, direction, player)] = OrderedDict([('entrance', entrance), ('exit', exit), ('direction', direction)])
        else:
            self.entrances[(entrance, direction, player)] = OrderedDict([('player', player), ('entrance', entrance), ('exit', exit), ('direction', direction)])

    def set_door(self, entrance, exit, direction, player, d_name):
        if self.world.players == 1:
            self.doors[(entrance, direction, player)] = OrderedDict([('player', player), ('entrance', entrance), ('exit', exit), ('direction', direction), ('dname', d_name)])
        else:
            self.doors[(entrance, direction, player)] = OrderedDict([('player', player), ('entrance', entrance), ('exit', exit), ('direction', direction), ('dname', d_name)])

    def set_lobby(self, lobby_name, door_name, player):
        if self.world.players == 1:
            self.lobbies[(lobby_name, player)] = {'lobby_name': lobby_name, 'door_name': door_name}
        else:
            self.lobbies[(lobby_name, player)] = {'player': player, 'lobby_name': lobby_name, 'door_name': door_name}

    def set_door_type(self, doorNames, type, player):
        if self.world.players == 1:
            self.doorTypes[(doorNames, player)] = OrderedDict([('doorNames', doorNames), ('type', type)])
        else:
            self.doorTypes[(doorNames, player)] = OrderedDict([('player', player), ('doorNames', doorNames), ('type', type)])

    def parse_data(self):
        self.medallions = OrderedDict()
        if self.world.players == 1:
            self.medallions['Misery Mire'] = self.world.required_medallions[1][0]
            self.medallions['Turtle Rock'] = self.world.required_medallions[1][1]
        else:
            for player in range(1, self.world.players + 1):
                self.medallions[f'Misery Mire ({self.world.get_player_names(player)})'] = self.world.required_medallions[player][0]
                self.medallions[f'Turtle Rock ({self.world.get_player_names(player)})'] = self.world.required_medallions[player][1]

        self.startinventory = list(map(str, self.world.precollected_items))

        self.locations = OrderedDict()
        listed_locations = set()

        lw_locations = [loc for loc in self.world.get_locations() if loc not in listed_locations and loc.parent_region and loc.parent_region.type == RegionType.LightWorld]
        self.locations['Light World'] = OrderedDict([(location.gen_name(), str(location.item) if location.item is not None else 'Nothing') for location in lw_locations])
        listed_locations.update(lw_locations)

        dw_locations = [loc for loc in self.world.get_locations() if loc not in listed_locations and loc.parent_region and loc.parent_region.type == RegionType.DarkWorld]
        self.locations['Dark World'] = OrderedDict([(location.gen_name(), str(location.item) if location.item is not None else 'Nothing') for location in dw_locations])
        listed_locations.update(dw_locations)

        cave_locations = [loc for loc in self.world.get_locations() if loc not in listed_locations and loc.parent_region and loc.parent_region.type == RegionType.Cave]
        self.locations['Caves'] = OrderedDict([(location.gen_name(), str(location.item) if location.item is not None else 'Nothing') for location in cave_locations])
        listed_locations.update(cave_locations)

        for dungeon in self.world.dungeons:
            dungeon_locations = [loc for loc in self.world.get_locations() if loc not in listed_locations and loc.parent_region and loc.parent_region.dungeon == dungeon]
            self.locations[str(dungeon)] = OrderedDict([(location.gen_name(), str(location.item) if location.item is not None else 'Nothing') for location in dungeon_locations])
            listed_locations.update(dungeon_locations)

        other_locations = [loc for loc in self.world.get_locations() if loc not in listed_locations]
        if other_locations:
            self.locations['Other Locations'] = OrderedDict([(location.gen_name(), str(location.item) if location.item is not None else 'Nothing') for location in other_locations])
            listed_locations.update(other_locations)

        self.shops = []
        for shop in self.world.shops:
            if not shop.custom:
                continue
            shopdata = {'location': str(shop.region),
                        'type': 'Take Any' if shop.type == ShopType.TakeAny else 'Shop'
                       }
            for index, item in enumerate(shop.inventory):
                if item is None:
                    continue
                shopdata['item_{}'.format(index)] = "{} - {}".format(item['item'], item['price']) if item['price'] else item['item']
            self.shops.append(shopdata)

        for player in range(1, self.world.players + 1):
            self.bosses[str(player)] = OrderedDict()
            self.bosses[str(player)]["Eastern Palace"] = self.world.get_dungeon("Eastern Palace", player).boss.name
            self.bosses[str(player)]["Desert Palace"] = self.world.get_dungeon("Desert Palace", player).boss.name
            self.bosses[str(player)]["Tower Of Hera"] = self.world.get_dungeon("Tower of Hera", player).boss.name
            self.bosses[str(player)]["Hyrule Castle"] = "Agahnim"
            self.bosses[str(player)]["Palace Of Darkness"] = self.world.get_dungeon("Palace of Darkness", player).boss.name
            self.bosses[str(player)]["Swamp Palace"] = self.world.get_dungeon("Swamp Palace", player).boss.name
            self.bosses[str(player)]["Skull Woods"] = self.world.get_dungeon("Skull Woods", player).boss.name
            self.bosses[str(player)]["Thieves Town"] = self.world.get_dungeon("Thieves Town", player).boss.name
            self.bosses[str(player)]["Ice Palace"] = self.world.get_dungeon("Ice Palace", player).boss.name
            self.bosses[str(player)]["Misery Mire"] = self.world.get_dungeon("Misery Mire", player).boss.name
            self.bosses[str(player)]["Turtle Rock"] = self.world.get_dungeon("Turtle Rock", player).boss.name
            self.bosses[str(player)]["Ganons Tower Basement"] = [x for x in self.world.dungeons if x.player == player and 'bottom' in x.bosses.keys()][0].bosses['bottom'].name
            self.bosses[str(player)]["Ganons Tower Middle"] = [x for x in self.world.dungeons if x.player == player and 'middle' in x.bosses.keys()][0].bosses['middle'].name
            self.bosses[str(player)]["Ganons Tower Top"] = [x for x in self.world.dungeons if x.player == player and 'top' in x.bosses.keys()][0].bosses['top'].name

            self.bosses[str(player)]["Ganons Tower"] = "Agahnim 2"
            self.bosses[str(player)]["Ganon"] = "Ganon"

        if self.world.players == 1:
            self.bosses = self.bosses["1"]

        for player in range(1, self.world.players + 1):
            if self.world.intensity[player] >= 3:
                for portal in self.world.dungeon_portals[player]:
                    self.set_lobby(portal.name, portal.door.name, player)

        from Main import __version__ as ERVersion
        self.metadata = {'version': ERVersion,
                         'logic': self.world.logic,
                         'mode': self.world.mode,
                         'retro': self.world.retro,
                         'weapons': self.world.swords,
                         'goal': self.world.goal,
                         'shuffle': self.world.shuffle,
                         'door_shuffle': self.world.doorShuffle,
                         'intensity': self.world.intensity,
                         'item_pool': self.world.difficulty,
                         'item_functionality': self.world.difficulty_adjustments,
                         'gt_crystals': self.world.crystals_needed_for_gt,
                         'ganon_crystals': self.world.crystals_needed_for_ganon,
                         'open_pyramid': self.world.open_pyramid,
                         'accessibility': self.world.accessibility,
                         'hints': self.world.hints,
                         'mapshuffle': self.world.mapshuffle,
                         'compassshuffle': self.world.compassshuffle,
                         'keyshuffle': self.world.keyshuffle,
                         'bigkeyshuffle': self.world.bigkeyshuffle,
                         'boss_shuffle': self.world.boss_shuffle,
                         'enemy_shuffle': self.world.enemy_shuffle,
                         'enemy_health': self.world.enemy_health,
                         'enemy_damage': self.world.enemy_damage,
                         'players': self.world.players,
                         'teams': self.world.teams,
                         'experimental': self.world.experimental,
                         'keydropshuffle': self.world.keydropshuffle,
                         }

    def to_json(self):
        self.parse_data()
        out = OrderedDict()
        out['Entrances'] = list(self.entrances.values())
        out['Doors'] = list(self.doors.values())
        out['Lobbies'] = list(self.lobbies.values())
        out['DoorTypes'] = list(self.doorTypes.values())
        out.update(self.locations)
        out['Starting Inventory'] = self.startinventory
        out['Special'] = self.medallions
        if self.hashes:
            out['Hashes'] = {f"{self.world.player_names[player][team]} (Team {team+1})": hash for (player, team), hash in self.hashes.items()}
        if self.shops:
            out['Shops'] = self.shops
        out['playthrough'] = self.playthrough
        out['paths'] = self.paths
        out['Bosses'] = self.bosses
        out['meta'] = self.metadata

        return json.dumps(out)

    def to_file(self, filename):
        self.parse_data()
        with open(filename, 'w') as outfile:
            outfile.write('ALttP Entrance Randomizer Version %s  -  Seed: %s\n\n' % (self.metadata['version'], self.world.seed))
            outfile.write('Filling Algorithm:               %s\n' % self.world.algorithm)
            outfile.write('Players:                         %d\n' % self.world.players)
            outfile.write('Teams:                           %d\n' % self.world.teams)
            for player in range(1, self.world.players + 1):
                if self.world.players > 1:
                    outfile.write('\nPlayer %d: %s\n' % (player, self.world.get_player_names(player)))
                if len(self.hashes) > 0:
                    for team in range(self.world.teams):
                        outfile.write('%s%s\n' % (f"Hash - {self.world.player_names[player][team]} (Team {team+1}): " if self.world.teams > 1 else 'Hash: ', self.hashes[player, team]))
                outfile.write('Logic:                           %s\n' % self.metadata['logic'][player])
                outfile.write('Mode:                            %s\n' % self.metadata['mode'][player])
                outfile.write('Retro:                           %s\n' % ('Yes' if self.metadata['retro'][player] else 'No'))
                outfile.write('Swords:                          %s\n' % self.metadata['weapons'][player])
                outfile.write('Goal:                            %s\n' % self.metadata['goal'][player])
                outfile.write('Difficulty:                      %s\n' % self.metadata['item_pool'][player])
                outfile.write('Item Functionality:              %s\n' % self.metadata['item_functionality'][player])
                outfile.write('Entrance Shuffle:                %s\n' % self.metadata['shuffle'][player])
                outfile.write('Door Shuffle:                    %s\n' % self.metadata['door_shuffle'][player])
                outfile.write('Intensity:                       %s\n' % self.metadata['intensity'][player])
                addition = ' (Random)' if self.world.crystals_gt_orig[player] == 'random' else ''
                outfile.write('Crystals required for GT:        %s\n' % (str(self.metadata['gt_crystals'][player]) + addition))
                addition = ' (Random)' if self.world.crystals_ganon_orig[player] == 'random' else ''
                outfile.write('Crystals required for Ganon:     %s\n' % (str(self.metadata['ganon_crystals'][player]) + addition))
                outfile.write('Pyramid hole pre-opened:         %s\n' % ('Yes' if self.metadata['open_pyramid'][player] else 'No'))
                outfile.write('Accessibility:                   %s\n' % self.metadata['accessibility'][player])
                outfile.write('Map shuffle:                     %s\n' % ('Yes' if self.metadata['mapshuffle'][player] else 'No'))
                outfile.write('Compass shuffle:                 %s\n' % ('Yes' if self.metadata['compassshuffle'][player] else 'No'))
                outfile.write('Small Key shuffle:               %s\n' % ('Yes' if self.metadata['keyshuffle'][player] else 'No'))
                outfile.write('Big Key shuffle:                 %s\n' % ('Yes' if self.metadata['bigkeyshuffle'][player] else 'No'))
                outfile.write('Boss shuffle:                    %s\n' % self.metadata['boss_shuffle'][player])
                outfile.write('Enemy shuffle:                   %s\n' % self.metadata['enemy_shuffle'][player])
                outfile.write('Enemy health:                    %s\n' % self.metadata['enemy_health'][player])
                outfile.write('Enemy damage:                    %s\n' % self.metadata['enemy_damage'][player])
                outfile.write('Hints:                           %s\n' % ('Yes' if self.metadata['hints'][player] else 'No'))
                outfile.write('Experimental:                    %s\n' % ('Yes' if self.metadata['experimental'][player] else 'No'))
                outfile.write('Key Drops shuffled:              %s\n' % ('Yes' if self.metadata['keydropshuffle'][player] else 'No'))
            if self.doors:
                outfile.write('\n\nDoors:\n\n')
                outfile.write('\n'.join(
                    ['%s%s %s %s %s' % ('Player {0}: '.format(entry['player']) if self.world.players > 1 else '',
                                        self.world.fish.translate("meta","doors",entry['entrance']),
                                        '<=>' if entry['direction'] == 'both' else '<=' if entry['direction'] == 'exit' else '=>',
                                        self.world.fish.translate("meta","doors",entry['exit']),
                                        '({0})'.format(entry['dname']) if self.world.doorShuffle[entry['player']] == 'crossed' else '') for
                     entry in self.doors.values()]))
            if self.lobbies:
                outfile.write('\n\nDungeon Lobbies:\n\n')
                outfile.write('\n'.join(
                    [f"{'Player {0}: '.format(entry['player']) if self.world.players > 1 else ''}{entry['lobby_name']}: {entry['door_name']}"
                     for
                     entry in self.lobbies.values()]))
            if self.doorTypes:
                # doorNames: For some reason these come in combined, somehow need to split on the thing to translate
                # doorTypes: Small Key, Bombable, Bonkable
                outfile.write('\n\nDoor Types:\n\n')
                outfile.write('\n'.join(['%s%s %s' % ('Player {0}: '.format(entry['player']) if self.world.players > 1 else '', self.world.fish.translate("meta","doors",entry['doorNames']), self.world.fish.translate("meta","doorTypes",entry['type'])) for entry in self.doorTypes.values()]))
            if self.entrances:
                # entrances: To/From overworld; Checking w/ & w/out "Exit" and translating accordingly
                outfile.write('\n\nEntrances:\n\n')
                outfile.write('\n'.join(['%s%s %s %s' % (f'{self.world.get_player_names(entry["player"])}: ' if self.world.players > 1 else '', self.world.fish.translate("meta","entrances",entry['entrance']), '<=>' if entry['direction'] == 'both' else '<=' if entry['direction'] == 'exit' else '=>', self.world.fish.translate("meta","entrances",entry['exit'])) for entry in self.entrances.values()]))
            outfile.write('\n\nMedallions:\n')
            for dungeon, medallion in self.medallions.items():
                outfile.write(f'\n{dungeon}: {medallion} Medallion')
            if self.startinventory:
                outfile.write('\n\nStarting Inventory:\n\n')
                outfile.write('\n'.join(self.startinventory))

            # locations: Change up location names; in the instance of a location with multiple sections, it'll try to translate the room name
            # items: Item names
            outfile.write('\n\nLocations:\n\n')
            outfile.write('\n'.join(['%s: %s' % (self.world.fish.translate("meta", "locations", location), self.world.fish.translate("meta", "items", item)) for grouping in self.locations.values() for (location, item) in grouping.items()]))

            # locations: Change up location names; in the instance of a location with multiple sections, it'll try to translate the room name
            # items: Item names
            outfile.write('\n\nShops:\n\n')
            outfile.write('\n'.join("{} [{}]\n    {}".format(self.world.fish.translate("meta","locations",shop['location']), shop['type'], "\n    ".join(self.world.fish.translate("meta","items",item) for item in [shop.get('item_0', None), shop.get('item_1', None), shop.get('item_2', None)] if item)) for shop in self.shops))

            for player in range(1, self.world.players + 1):
                if self.world.boss_shuffle[player] != 'none':
                    bossmap = self.bosses[player] if self.world.players > 1 else self.bosses
                    outfile.write(f'\n\nBosses ({self.world.get_player_names(player)}):\n\n')
                    outfile.write('\n'.join([f'{x}: {y}' for x, y in bossmap.items() if y not in ['Agahnim', 'Agahnim 2', 'Ganon']]))

            # locations: Change up location names; in the instance of a location with multiple sections, it'll try to translate the room name
            # items: Item names
            outfile.write('\n\nPlaythrough:\n\n')
            outfile.write('\n'.join(['%s: {\n%s\n}' % (sphere_nr, '\n'.join(['  %s: %s' % (self.world.fish.translate("meta","locations",location), self.world.fish.translate("meta","items",item)) for (location, item) in sphere.items()] if sphere_nr != '0' else [f'  {item}' for item in sphere])) for (sphere_nr, sphere) in self.playthrough.items()]))
            if self.unreachables:
                # locations: Change up location names; in the instance of a location with multiple sections, it'll try to translate the room name
                # items: Item names
                outfile.write('\n\nUnreachable Items:\n\n')
                outfile.write('\n'.join(['%s: %s' % (self.world.fish.translate("meta", "items", unreachable.item.name),
                                                     self.world.fish.translate("meta", "locations", unreachable.name))
                                         for unreachable in self.unreachables]))

            # rooms: Change up room names; only if it's got no locations in it
            # entrances: To/From overworld; Checking w/ & w/out "Exit" and translating accordingly
            # locations: Change up location names; in the instance of a location with multiple sections, it'll try to translate the room name
            outfile.write('\n\nPaths:\n\n')
            path_listings = []
            for location, path in sorted(self.paths.items()):
                path_lines = []
                for region, exit in path:
                    if exit is not None:
                        path_lines.append("{} -> {}".format(self.world.fish.translate("meta","rooms",region), self.world.fish.translate("meta","entrances",exit)))
                    else:
                        path_lines.append(self.world.fish.translate("meta","rooms",region))
                path_listings.append("{}\n        {}".format(self.world.fish.translate("meta","locations",location), "\n   =>   ".join(path_lines)))

            outfile.write('\n'.join(path_listings))


flooded_keys = {
    'Trench 1 Switch': 'Swamp Palace - Trench 1 Pot Key',
    'Trench 2 Switch': 'Swamp Palace - Trench 2 Pot Key'
}

dungeon_names = [
    'Hyrule Castle', 'Eastern Palace', 'Desert Palace', 'Tower of Hera', 'Agahnims Tower', 'Palace of Darkness',
    'Swamp Palace', 'Skull Woods', 'Thieves Town', 'Ice Palace', 'Misery Mire', 'Turtle Rock', 'Ganons Tower'
]


class PotItem(FastEnum):
    Nothing = 0x0
    OneRupee = 0x1
    RockCrab = 0x2
    Bee = 0x3
    Random = 0x4
    Bomb_0 = 0x5
    Heart_0 = 0x6
    FiveRupees = 0x7
    Key = 0x8
    FiveArrows = 0x9
    Bomb = 0xA
    Heart = 0xB
    SmallMagic = 0xC
    BigMagic = 0xD
    Chicken = 0xE
    GreenSoldier = 0xF
    AliveRock = 0x10
    BlueSoldier = 0x11
    GroundBomb = 0x12
    Heart_2 = 0x13
    Fairy = 0x14
    Heart_3 = 0x15
    Hole = 0x80
    Warp = 0x82
    Staircase = 0x84
    Bombable = 0x86
    Switch = 0x88


class PotFlags(FastEnum):
    Normal = 0x0
    NoSwitch = 0x1  # A switch should never go here
    SwitchLogicChange = 0x2  # A switch can go here, but requires a logic change


class Pot(object):
    def __init__(self, x, y, item, room, flags = PotFlags.Normal):
        self.x = x
        self.y = y
        self.item = item
        self.room = room
        self.flags = flags