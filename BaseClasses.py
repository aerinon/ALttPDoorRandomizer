import base64
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
from source.dungeon.RoomObject import RoomObject


class World(object):

    def __init__(self, players, shuffle, doorShuffle, logic, mode, swords, difficulty, difficulty_adjustments,
                 timer, progressive, goal, algorithm, accessibility, shuffle_ganon, custom, customitemarray, hints, seed_name, seed_notes):
        self.players = players
        self.teams = 1
        self.shuffle = shuffle.copy()
        self.doorShuffle = doorShuffle.copy()
        self.intensity = {}
        self.door_type_mode = {}
        self.trap_door_mode = {}
        self.key_logic_algorithm = {}
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
        self.shops = {}
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
        self.enabled_entrances = {}
        self.key_logic = {}
        self.pool_adjustment = {}
        self.key_layout = defaultdict(dict)
        self.dungeon_portals = defaultdict(list)
        self._portal_cache = {}
        self.sanc_portal = {}
        self.fish = BabelFish()
        self.pot_contents = {}
        self.seed_name = seed_name
        self.seed_notes = seed_notes

        for player in range(1, players + 1):
            def set_player_attr(attr, val):
                self.__dict__.setdefault(attr, {})[player] = val
            set_player_attr('_region_cache', {})
            set_player_attr('player_names', [])
            set_player_attr('remote_items', False)
            set_player_attr('required_medallions', ['Ether', 'Quake'])
            set_player_attr('bottle_refills', ['Bottle (Green Potion)', 'Bottle (Green Potion)'])
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
            set_player_attr('fix_fake_world', logic[player] not in ['owglitches', 'nologic']
                            or shuffle[player] in ['lean', 'crossed', 'insanity'])
            set_player_attr('mapshuffle', False)
            set_player_attr('compassshuffle', False)
            set_player_attr('keyshuffle', 'none')
            set_player_attr('bigkeyshuffle', False)
            set_player_attr('restrict_boss_items', 'none')
            set_player_attr('bombbag', False)
            set_player_attr('flute_mode', False)
            set_player_attr('bow_mode', False)
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
            set_player_attr('open_pyramid', 'auto')
            set_player_attr('take_any', 'none')
            set_player_attr('treasure_hunt_icon', 'Triforce Piece')
            set_player_attr('treasure_hunt_count', 0)
            set_player_attr('treasure_hunt_total', 0)
            set_player_attr('potshuffle', False)
            set_player_attr('pot_contents', None)
            set_player_attr('pseudoboots', False)
            set_player_attr('collection_rate', False)
            set_player_attr('colorizepots', True)
            set_player_attr('pot_pool', {})
            set_player_attr('decoupledoors', False)
            set_player_attr('door_type_mode', 'original')
            set_player_attr('trap_door_mode', 'optional')
            set_player_attr('key_logic_algorithm', 'default')

            set_player_attr('shopsanity', False)
            set_player_attr('mixed_travel', 'prevent')
            set_player_attr('standardize_palettes', 'standardize')
            set_player_attr('force_fix', {'gt': False, 'sw': False, 'pod': False, 'tr': False})

            set_player_attr('exp_cache', defaultdict(dict))
            set_player_attr('enabled_entrances', {})

    def finish_init(self):
        for player in range(1, self.players + 1):
            if self.mode[player] == 'retro':
                self.mode[player] = 'open'
            if self.goal[player] == 'completionist':
                self.accessibility[player] = 'locations'

    def get_name_string_for_object(self, obj):
        return obj.name if self.players == 1 else f'{obj.name} ({self.get_player_names(obj.player)})'

    def get_player_names(self, player):
        return ", ".join([name for i, name in enumerate(self.player_names[player]) if self.player_names[player].index(name) == i])

    def initialize_regions(self, regions=None):
        for region in regions if regions else self.regions:
            region.world = self
            self._region_cache[region.player][region.name] = region
            for exit in region.exits:
                self._entrance_cache[exit.name, exit.player] = exit
            for r_location in region.locations:
                self._location_cache[r_location.name, r_location.player] = r_location

    def initialize_doors(self, doors):
        for door in doors:
            self._door_cache[(door.name, door.player)] = door

    def remove_door(self, door, player):
        if (door.name, player) in self._door_cache.keys():
            del self._door_cache[(door.name, player)]
        if door in self.doors:
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

    def get_location_unsafe(self, location, player):
        if (location, player) in self._location_cache:
            return self._location_cache[(location, player)]
        return None

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

    def is_atgt_swapped(self, player):
        return self.mode[player] == 'inverted'

    def is_pyramid_open(self, player):
        if self.open_pyramid[player] == 'yes':
            return True
        elif self.open_pyramid[player] == 'no':
            return False
        else:
            if self.shuffle[player] not in ['vanilla', 'dungeonssimple', 'dungeonsfull']:
                return False
            elif self.goal[player] in ['crystals', 'trinity']:
                return True
            else:
                return False

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
            elif item.advancement or item.smallkey or item.bigkey or item.compass or item.map:
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
                    # map/compass may be required now
                    key_list += [x.name for x in dungeon.dungeon_items]
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
        if ((item.smallkey and self.keyshuffle[item.player] != 'none')
           or (item.bigkey and self.bigkeyshuffle[item.player])):
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
            if location.player != item.player and location.type == LocationType.Pot:
                self.pot_contents[location.player].multiworld_count += 1
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

    def clear_exp_cache(self):
        for p in range(1, self.players + 1):
            self.exp_cache[p].clear()

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

    def can_beat_game(self, starting_state=None, log_error=False):
        if starting_state:
            if self.has_beaten_game(starting_state):
                return True
            state = starting_state.copy()
        else:
            state = CollectionState(self)

        if self.has_beaten_game(state):
            return True

        prog_locations = [location for location in self.get_locations() if location.item is not None
                          and (location.item.advancement or location.event
                               or self.goal[location.player] == 'completionist')
                          and location not in state.locations_checked]

        while prog_locations:
            sphere = []
            # build up spheres of collection radius. Everything in each sphere is independent from each other in dependencies and only depends on lower spheres
            for location in prog_locations:
                if location.can_reach(state) and state.not_flooding_a_key(state.world, location):
                    sphere.append(location)

            if not sphere:
                # ran out of places and did not finish yet, quit
                if log_error:
                    missing_locations = ", ".join([x.name for x in prog_locations])
                    logging.getLogger('').error(f'Cannot reach the following locations: {missing_locations}')
                return False

            for location in sphere:
                prog_locations.remove(location)
                state.collect(location.item, True, location)

            if self.has_beaten_game(state):
                return True

        return False


class CollectionState(object):

    def __init__(self, parent, skip_init=False):
        self.world = parent
        if not skip_init:
            self.prog_items = Counter()
            self.forced_keys = Counter()
            self.reachable_regions = {player: dict() for player in range(1, parent.players + 1)}
            self.blocked_connections = {player: dict() for player in range(1, parent.players + 1)}
            self.events = []
            self.path = {}
            self.locations_checked = set()
            self.stale = {player: True for player in range(1, parent.players + 1)}
            for item in parent.precollected_items:
                self.collect(item, True)
            # reached vs. opened in the counter
            self.door_counter = {player: (Counter(), Counter()) for player in range(1, parent.players + 1)}
            self.reached_doors = {player: set() for player in range(1, parent.players + 1)}
            self.opened_doors = {player: set() for player in range(1, parent.players + 1)}
            self.dungeons_to_check = {player: defaultdict(dict) for player in range(1, parent.players + 1)}
        self.dungeon_limits = None
        self.placing_item = None
        # self.trace = None

    def update_reachable_regions(self, player):
        self.stale[player] = False
        rrp = self.reachable_regions[player]
        bc = self.blocked_connections[player]

        # init on first call - this can't be done on construction since the regions don't exist yet
        start = self.world.get_region('Menu', player)
        if not start in rrp:
            rrp[start] = CrystalBarrier.Orange
            for conn in start.exits:
                bc[conn] = CrystalBarrier.Orange

        queue = deque(self.blocked_connections[player].items())

        self.traverse_world(queue, rrp, bc, player)
        if self.world.key_logic_algorithm[player] == 'default':
            unresolved_events = [x for y in self.reachable_regions[player] for x in y.locations
                                 if x.event and x.item and (x.item.smallkey or x.item.bigkey or x.item.advancement)
                                 and x not in self.locations_checked and x.can_reach(self)]
            unresolved_events = self._do_not_flood_the_keys(unresolved_events)
            if len(unresolved_events) == 0:
                self.check_key_doors_in_dungeons(rrp, player)

    def traverse_world(self, queue, rrp, bc, player):
        # run BFS on all connections, and keep track of those blocked by missing items
        while len(queue) > 0:
            connection, crystal_state = queue.popleft()
            new_region = connection.connected_region
            if not self.should_visit(new_region, rrp, crystal_state, player):
                if not new_region or not self.dungeon_limits or self.possibly_connected_to_dungeon(new_region, player):
                    bc.pop(connection, None)
            elif connection.can_reach(self):
                bc.pop(connection, None)
                if new_region.type == RegionType.Dungeon:
                    new_crystal_state = crystal_state
                    if new_region in rrp:
                        new_crystal_state |= rrp[new_region]

                    rrp[new_region] = new_crystal_state
                    for conn in new_region.exits:
                        door = conn.door
                        if door is not None and not door.blocked:
                            if self.valid_crystal(door, new_crystal_state):
                                door_crystal_state = door.crystal if door.crystal else new_crystal_state
                                bc[conn] = door_crystal_state
                                queue.append((conn, door_crystal_state))
                        elif door is None:
                            # note: no door in dungeon indicates what exactly? (always traversable)?
                            queue.append((conn, new_crystal_state))
                else:
                    new_crystal_state = CrystalBarrier.Orange
                    rrp[new_region] = new_crystal_state
                    for conn in new_region.exits:
                        bc[conn] = new_crystal_state
                        queue.append((conn, new_crystal_state))

                self.path[new_region] = (new_region.name, self.path.get(connection, None))

                # Retry connections if the new region can unblock them
                if new_region.name in indirect_connections:
                    new_entrance = self.world.get_entrance(indirect_connections[new_region.name], player)
                    if new_entrance in bc and new_entrance.parent_region in rrp:
                        new_crystal_state = rrp[new_entrance.parent_region]
                        if (new_entrance, new_crystal_state) not in queue:
                            queue.append((new_entrance, new_crystal_state))
            # else those connections that are not accessible yet
            if self.is_small_door(connection):
                door = connection.door if connection.door.smallKey else connection.door.controller
                dungeon_name = connection.parent_region.dungeon.name
                key_logic = self.world.key_logic[player][dungeon_name]
                if door.name not in self.reached_doors[player]:
                    self.door_counter[player][0][dungeon_name] += 1
                    self.reached_doors[player].add(door.name)
                    if key_logic.sm_doors[door]:
                        self.reached_doors[player].add(key_logic.sm_doors[door].name)
                if not connection.can_reach(self):
                    checklist_key = 'Universal' if self.world.keyshuffle[player] == 'universal' else dungeon_name
                    checklist = self.dungeons_to_check[player][checklist_key]
                    checklist[connection.name] = (connection, crystal_state)
                elif door.name not in self.opened_doors[player]:
                    opened_doors = self.opened_doors[player]
                    door = connection.door if connection.door.smallKey else connection.door.controller
                    if door.name not in opened_doors:
                        self.door_counter[player][1][dungeon_name] += 1
                        opened_doors.add(door.name)
                        key_logic = self.world.key_logic[player][dungeon_name]
                        if key_logic.sm_doors[door]:
                            opened_doors.add(key_logic.sm_doors[door].name)

    def should_visit(self, new_region, rrp, crystal_state, player):
        if not new_region:
            return False
        if self.dungeon_limits and not self.possibly_connected_to_dungeon(new_region, player):
            return False
        if new_region not in rrp:
            return True
        if new_region.type != RegionType.Dungeon:
            return False
        return (rrp[new_region] & crystal_state) != crystal_state

    def possibly_connected_to_dungeon(self, new_region, player):
        if new_region.dungeon:
            return new_region.dungeon.name in self.dungeon_limits
        else:
            return new_region.name in self.world.inaccessible_regions[player]

    @staticmethod
    def valid_crystal(door, new_crystal_state):
        return (not door.crystal or door.crystal == CrystalBarrier.Either or new_crystal_state == CrystalBarrier.Either
                or new_crystal_state == door.crystal)

    def check_key_doors_in_dungeons(self, rrp, player):
        for dungeon_name, checklist in self.dungeons_to_check[player].items():
            # todo: optimization idea - abort exploration if there are unresolved events now
            if self.apply_dungeon_exploration(rrp, player, dungeon_name, checklist):
                continue
            init_door_candidates = self.should_explore_child_state(self, dungeon_name, player)
            key_total = self.prog_items[(dungeon_keys[dungeon_name], player)]  # todo: universal
            remaining_keys = key_total - self.door_counter[player][1][dungeon_name]
            if not init_door_candidates or remaining_keys == 0:
                continue
            dungeon_doors = {x.name for x in self.world.key_logic[player][dungeon_name].sm_doors.keys()}

            def valid_d_door(x):
                return x in dungeon_doors

            child_states = deque()
            child_states.append(self)
            visited_opened_doors = set()
            visited_opened_doors.add(frozenset(self.opened_doors[player]))
            terminal_states, common_regions, common_bc, common_doors = [], {}, {}, set()
            while len(child_states) > 0:
                next_child = child_states.popleft()
                door_candidates = CollectionState.should_explore_child_state(next_child, dungeon_name, player)
                child_checklist = next_child.dungeons_to_check[player][dungeon_name]
                if door_candidates:
                    for chosen_door in door_candidates:
                        child_state = next_child.copy()
                        child_queue = deque()
                        child_state.door_counter[player][1][dungeon_name] += 1
                        if isinstance(chosen_door, tuple):
                            child_state.opened_doors[player].add(chosen_door[0])
                            child_state.opened_doors[player].add(chosen_door[1])
                            if chosen_door[0] in child_checklist:
                                child_queue.append(child_checklist[chosen_door[0]])
                            if chosen_door[1] in child_checklist:
                                child_queue.append(child_checklist[chosen_door[1]])
                        else:
                            child_state.opened_doors[player].add(chosen_door)
                            if chosen_door in child_checklist:
                                child_queue.append(child_checklist[chosen_door])
                        if child_state.opened_doors[player] not in visited_opened_doors:
                            done = False
                            while not done:
                                rrp_ = child_state.reachable_regions[player]
                                bc_ = child_state.blocked_connections[player]
                                child_state.set_dungeon_limits(player, dungeon_name)
                                child_queue.extend([(x, y) for x, y in bc_.items()
                                                    if child_state.possibly_connected_to_dungeon(x.parent_region,
                                                                                                 player)])
                                child_state.traverse_world(child_queue, rrp_, bc_, player)
                                new_events = child_state.sweep_for_events_once(player)
                                child_state.stale[player] = False
                                if new_events:
                                    for conn in bc_:
                                        if conn.parent_region.dungeon and conn.parent_region.dungeon.name == dungeon_name:
                                            child_queue.append((conn, bc_[conn]))
                                done = not new_events
                            if child_state.opened_doors[player] not in visited_opened_doors:
                                visited_opened_doors.add(frozenset(child_state.opened_doors[player]))
                                child_states.append(child_state)
                else:
                    terminal_states.append(next_child)
            common_regions, common_bc, common_doors, first = {}, {}, set(), True
            bc = self.blocked_connections[player]
            for term_state in terminal_states:
                t_rrp = term_state.reachable_regions[player]
                t_bc = term_state.blocked_connections[player]
                if first:
                    first = False
                    common_regions = {x: y for x, y in t_rrp.items() if x not in rrp or y != rrp[x]}
                    common_bc = {x: y for x, y in t_bc.items() if x not in bc}
                    common_doors = {x for x in term_state.opened_doors[player] - self.opened_doors[player]
                                    if valid_d_door(x)}
                else:
                    cm_rrp = {x: y for x, y in t_rrp.items() if x not in rrp or y != rrp[x]}
                    common_regions = {k: self.comb_crys(v, cm_rrp[k]) for k, v in common_regions.items()
                                      if k in cm_rrp and self.crys_agree(v, cm_rrp[k])}
                    common_bc.update({x: y for x, y in t_bc.items() if x not in bc and x not in common_bc})
                    common_doors &= {x for x in term_state.opened_doors[player] - self.opened_doors[player]
                                     if valid_d_door(x)}

            terminal_queue = deque()
            for door in common_doors:
                pair = self.find_door_pair(player, dungeon_name, door)
                if door not in self.reached_doors[player]:
                    self.door_counter[player][0][dungeon_name] += 1
                    self.reached_doors[player].add(door)
                    if pair not in self.reached_doors[player]:
                        self.reached_doors[player].add(pair)
                self.opened_doors[player].add(door)
                if door in checklist:
                    terminal_queue.append(checklist[door])
                if pair not in self.opened_doors[player]:
                    self.door_counter[player][1][dungeon_name] += 1

            self.set_dungeon_limits(player, dungeon_name)
            rrp_ = self.reachable_regions[player]
            bc_ = self.blocked_connections[player]
            for block, crystal in bc_.items():
                if (block, crystal) not in terminal_queue and self.possibly_connected_to_dungeon(block.connected_region, player):
                        terminal_queue.append((block, crystal))
            self.traverse_world(terminal_queue, rrp_, bc_, player)
            self.dungeon_limits = None

            rrp = self.reachable_regions[player]
            missing_regions = {x: y for x, y in common_regions.items() if x not in rrp}
            paths = {}
            for k in missing_regions:
                rrp[k] = missing_regions[k]
                possible_path = terminal_states[0].path[k]
                self.path[k] = paths[k] = possible_path
                for conn in k.exits:
                    if self.is_small_door(conn):
                        door = conn.door if conn.door.smallKey else conn.door.controller
                        key_logic = self.world.key_logic[player][dungeon_name]
                        if door.name not in self.reached_doors[player]:
                            self.door_counter[player][0][dungeon_name] += 1
                            self.reached_doors[player].add(door.name)
                            if key_logic.sm_doors[door]:
                                self.reached_doors[player].add(key_logic.sm_doors[door].name)
            missing_bc = {}
            for blocked, crystal in common_bc.items():
                if (blocked not in bc and blocked.parent_region in rrp
                   and self.should_visit(blocked.connected_region, rrp, crystal, player)):
                    missing_bc[blocked] = crystal
            for k in missing_bc:
                bc[k] = missing_bc[k]
            self.record_dungeon_exploration(player, dungeon_name, checklist,
                                            common_doors, missing_regions, missing_bc, paths)
            checklist.clear()

    @staticmethod
    def comb_crys(a, b):
        return a if a == b or a != CrystalBarrier.Either else b

    @staticmethod
    def crys_agree(a, b):
        return a == b or a == CrystalBarrier.Either or b == CrystalBarrier.Either

    def find_door_pair(self, player, dungeon_name, name):
        for door in self.world.key_logic[player][dungeon_name].sm_doors.keys():
            if door.name == name:
                paired_door = self.world.key_logic[player][dungeon_name].sm_doors[door]
                return paired_door.name if paired_door else None
        return None

    def set_dungeon_limits(self, player, dungeon_name):
        if self.world.keyshuffle[player] == 'universal' and self.world.mode[player] == 'standard':
            self.dungeon_limits = ['Hyrule Castle', 'Agahnims Tower']
        else:
            self.dungeon_limits = [dungeon_name]

    @staticmethod
    def should_explore_child_state(state, dungeon_name, player):
        small_key_name = dungeon_keys[dungeon_name]
        key_total = state.prog_items[(small_key_name, player)]
        remaining_keys = key_total - state.door_counter[player][1][dungeon_name]
        unopened_doors = state.door_counter[player][0][dungeon_name] - state.door_counter[player][1][dungeon_name]
        if remaining_keys > 0 and unopened_doors > 0:
            key_logic = state.world.key_logic[player][dungeon_name]
            door_candidates, skip = [], set()
            for door, paired in key_logic.sm_doors.items():
                if door.name in state.reached_doors[player] and door.name not in state.opened_doors[player]:
                    if door.name not in skip:
                        if paired:
                            door_candidates.append((door.name, paired.name))
                            skip.add(paired.name)
                        else:
                            door_candidates.append(door.name)
            return door_candidates
        door_candidates, skip = [], set()
        if (state.world.accessibility[player] != 'locations' and remaining_keys == 0 and dungeon_name != 'Universal'
           and state.placing_item and state.placing_item.name == small_key_name):
            key_logic = state.world.key_logic[player][dungeon_name]
            for door, paired in key_logic.sm_doors.items():
                if door.name in key_logic.door_rules:
                    rule = key_logic.door_rules[door.name]
                    key = KeyRuleType.AllowSmall
                    if (key in rule.new_rules and key_total >= rule.new_rules[key] and door.name not in skip
                       and door.name in state.reached_doors[player] and door.name not in state.opened_doors[player]
                       and rule.small_location.item is None):
                        if paired:
                            door_candidates.append((door.name, paired.name))
                            skip.add(paired.name)
                        else:
                            door_candidates.append(door.name)
        return door_candidates if door_candidates else None

    @staticmethod
    def print_rrp(rrp):
        logger = logging.getLogger('')
        logger.debug('RRP Checking')
        for region, packet in rrp.items():
            new_crystal_state, logic, path = packet
            logger.debug(f'\nRegion: {region.name} (CS: {str(new_crystal_state)})')
            for i in range(0, len(logic)):
                logger.debug(f'{logic[i]}')
                logger.debug(f'{",".join(str(x) for x in path[i])}')

    def copy(self):
        ret = CollectionState(self.world, skip_init=True)
        ret.prog_items = self.prog_items.copy()
        ret.forced_keys = self.forced_keys.copy()
        ret.reachable_regions = {player: copy.copy(self.reachable_regions[player]) for player in range(1, self.world.players + 1)}
        ret.blocked_connections = {player: copy.copy(self.blocked_connections[player]) for player in range(1, self.world.players + 1)}
        ret.events = copy.copy(self.events)
        ret.path = copy.copy(self.path)
        ret.locations_checked = copy.copy(self.locations_checked)
        ret.stale = {player: self.stale[player] for player in range(1, self.world.players + 1)}
        ret.door_counter = {player: (copy.copy(self.door_counter[player][0]), copy.copy(self.door_counter[player][1]))
                            for player in range(1, self.world.players + 1)}
        ret.reached_doors = {player: copy.copy(self.reached_doors[player]) for player in range(1, self.world.players + 1)}
        ret.opened_doors = {player: copy.copy(self.opened_doors[player]) for player in range(1, self.world.players + 1)}
        ret.dungeons_to_check = {
            player: defaultdict(dict, {name: copy.copy(checklist)
                                       for name, checklist in self.dungeons_to_check[player].items()})
            for player in range(1, self.world.players + 1)}
        ret.placing_item = self.placing_item
        return ret

    def apply_dungeon_exploration(self, rrp, player, dungeon_name, checklist):
        bc = self.blocked_connections[player]
        ec = self.world.exp_cache[player]
        prog_set = self.reduce_prog_items(player, dungeon_name)
        exp_key = (prog_set, frozenset(checklist))
        if dungeon_name in ec and exp_key in ec[dungeon_name]:
            # apply
            common_doors, missing_regions, missing_bc, paths = ec[dungeon_name][exp_key]
            terminal_queue = deque()
            for door in common_doors:
                pair = self.find_door_pair(player, dungeon_name, door)
                if door not in self.reached_doors[player]:
                    self.door_counter[player][0][dungeon_name] += 1
                    self.reached_doors[player].add(door)
                    if pair not in self.reached_doors[player]:
                        self.reached_doors[player].add(pair)
                self.opened_doors[player].add(door)
                if door in checklist:
                    terminal_queue.append(checklist[door])
                if pair not in self.opened_doors[player]:
                    self.door_counter[player][1][dungeon_name] += 1

            self.set_dungeon_limits(player, dungeon_name)
            rrp_ = self.reachable_regions[player]
            bc_ = self.blocked_connections[player]
            for block, crystal in bc_.items():
                if (block, crystal) not in terminal_queue and self.possibly_connected_to_dungeon(block.connected_region, player):
                    terminal_queue.append((block, crystal))
            self.traverse_world(terminal_queue, rrp_, bc_, player)
            self.dungeon_limits = None

            for k in missing_regions:
                rrp[k] = missing_regions[k]
            for r, path in paths.items():
                self.path[r] = path
            for k in missing_bc:
                bc[k] = missing_bc[k]

            return True
        return False

    def record_dungeon_exploration(self, player, dungeon_name, checklist,
                                   common_doors, missing_regions, missing_bc, paths):
        ec = self.world.exp_cache[player]
        prog_set = self.reduce_prog_items(player, dungeon_name)
        exp_key = (prog_set, frozenset(checklist))
        ec[dungeon_name][exp_key] = (common_doors, missing_regions, missing_bc, paths)

    def reduce_prog_items(self, player, dungeon_name):
        # todo: possibly could include an analysis of dungeon items req. like Hammer, Hookshot, etc
        # cross dungeon requirements may be necessary for keysanity - which invalidates the above
        # todo: universal smalls where needed
        life_count, bottle_count = 0, 0
        reduced = Counter()
        for item, cnt in self.prog_items.items():
            item_name, item_player = item
            if item_player == player and self.check_if_progressive(item_name, player):
                if item_name.startswith('Bottle'):  # I think magic requirements can require multiple bottles
                    bottle_count += cnt
                elif item_name in ['Boss Heart Container', 'Sanctuary Heart Container', 'Piece of Heart']:
                    if 'Container' in item_name:
                        life_count += 1
                    elif 'Piece of Heart' == item_name:
                        life_count += .25
                else:
                    reduced[item] = cnt
        if bottle_count > 0:
            reduced[('Bottle', player)] = 1
        if life_count >= 1:
            reduced[('Heart Container', player)] = 1
        return frozenset(reduced.items())

    def check_if_progressive(self, item_name, player):
        return (item_name in
                ['Bow', 'Progressive Bow', 'Progressive Bow (Alt)', 'Book of Mudora', 'Hammer', 'Hookshot',
                 'Magic Mirror', 'Ocarina', 'Pegasus Boots', 'Power Glove', 'Cape', 'Mushroom', 'Shovel',
                 'Lamp', 'Magic Powder', 'Moon Pearl', 'Cane of Somaria', 'Fire Rod', 'Flippers', 'Ice Rod',
                 'Titans Mitts', 'Bombos', 'Ether', 'Quake', 'Master Sword', 'Tempered Sword', 'Fighter Sword',
                 'Golden Sword', 'Progressive Sword', 'Progressive Glove', 'Silver Arrows', 'Green Pendant',
                 'Blue Pendant', 'Red Pendant', 'Crystal 1', 'Crystal 2', 'Crystal 3', 'Crystal 4', 'Crystal 5',
                 'Crystal 6', 'Crystal 7', 'Blue Boomerang', 'Red Boomerang', 'Blue Shield', 'Red Shield',
                 'Mirror Shield', 'Progressive Shield', 'Bug Catching Net', 'Cane of Byrna', 'Ocarina (Activated)',
                 'Boss Heart Container', 'Sanctuary Heart Container', 'Piece of Heart', 'Magic Upgrade (1/2)',
                 'Magic Upgrade (1/4)']
            or item_name.startswith(('Bottle', 'Small Key', 'Big Key'))
            or (self.world.restrict_boss_items[player] != 'none' and item_name.startswith(('Map', 'Compass'))))

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

    def sweep_for_events_once(self, player):
        locations = self.world.get_filled_locations(player)
        checked_locations = set([l for l in locations if l in self.locations_checked])
        reachable_events = [location for location in locations if location.event and location.can_reach(self)]
        reachable_events = self._do_not_flood_the_keys(reachable_events)
        found_new = False
        for event in reachable_events:
            if event not in checked_locations:
                self.events.append((event.name, event.player))
                self.collect(event.item, True, event)
                found_new = True
        return found_new

    def sweep_for_events(self, key_only=False, locations=None):
        # this may need improvement
        if locations is None:
            locations = self.world.get_filled_locations()
        new_locations = True
        while new_locations:
            reachable_events = [location for location in locations if location.event and
                                (not key_only or (self.world.keyshuffle[location.item.player] == 'none' and location.item.smallkey) or (not self.world.bigkeyshuffle[location.item.player] and location.item.bigkey))
                                and location.can_reach(self)]
            reachable_events = self._do_not_flood_the_keys(reachable_events)
            new_locations = False
            for event in reachable_events:
                if (event.name, event.player) not in self.events:
                    self.events.append((event.name, event.player))
                    self.collect(event.item, True, event)
                    new_locations = True


    def can_reach_blue(self, region, player):
        return region in self.reachable_regions[player] and self.reachable_regions[player][region] in [CrystalBarrier.Blue, CrystalBarrier.Either]

    def can_reach_orange(self, region, player):
        return region in self.reachable_regions[player] and self.reachable_regions[player][region] in [CrystalBarrier.Orange, CrystalBarrier.Either]

    def _do_not_flood_the_keys(self, reachable_events):
        adjusted_checks = list(reachable_events)
        for event in reachable_events:
            if event.name in flooded_keys.keys():
                flood_location = self.world.get_location(flooded_keys[event.name], event.player)
                if (flood_location.item and flood_location not in self.locations_checked
                   and self.location_can_be_flooded(flood_location)):
                    adjusted_checks.remove(event)
        if len(adjusted_checks) < len(reachable_events):
            return adjusted_checks
        return reachable_events

    def not_flooding_a_key(self, world, location):
        if location.name in flooded_keys.keys():
            flood_location = world.get_location(flooded_keys[location.name], location.player)
            item = flood_location.item
            item_is_important = False if not item else item.advancement or item.bigkey or item.smallkey
            return (flood_location in self.locations_checked or not item_is_important
                    or not self.location_can_be_flooded(flood_location))
        return True

    @staticmethod
    def is_small_door(connection):
        return connection and connection.door and (connection.door.smallKey or
                                                   CollectionState.is_controlled_by_small(connection))

    @staticmethod
    def is_controlled_by_small(connection):
        return connection.door.controller and connection.door.controller.smallKey

    def is_door_open(self, door_name, player):
        return door_name in self.opened_doors[player]

    @staticmethod
    def location_can_be_flooded(location):
        return location.parent_region.name in ['Swamp Trench 1 Alcove', 'Swamp Trench 2 Alcove']

    def has(self, item, player, count=1):
        if count == 1:
            return (item, player) in self.prog_items
        return self.prog_items[item, player] >= count

    def has_sm_key(self, item, player, count=1):
        if self.world.keyshuffle[player] == 'universal':
            if self.world.mode[player] == 'standard' and self.world.doorShuffle[player] == 'vanilla' and item == 'Small Key (Escape)':
                return True  # Cannot access the shop until escape is finished.  This is safe because the key is manually placed in make_custom_item_pool
            return self.can_buy_unlimited('Small Key (Universal)', player)
        if count == 1:
            return (item, player) in self.prog_items
        return self.prog_items[item, player] >= count

    def has_sm_key_strict(self, item, player, count=1):
        if self.world.keyshuffle[player] == 'universal':
            if self.world.mode[player] == 'standard' and self.world.doorShuffle[player] == 'vanilla' and item == 'Small Key (Escape)':
                return True  # Cannot access the shop until escape is finished.  This is safe because the key is manually placed in make_custom_item_pool
            return self.can_buy_unlimited('Small Key (Universal)', player)
        obtained = self.prog_items[item, player] - self.forced_keys[item, player]
        return obtained >= count

    def can_buy_unlimited(self, item, player):
        for shop in self.world.shops[player]:
            if shop.region.player == player and shop.has_unlimited(item) and shop.region.can_reach(self):
                return True
        return False

    def item_count(self, item, player):
        return self.prog_items[item, player]

    def everything(self, player):
        all_locations = self.world.get_filled_locations(player)
        all_locations.remove(self.world.get_location('Ganon', player))
        return (len([x for x in self.locations_checked if x.player == player])
                >= len(all_locations))

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

    # In the future, this can be used to check if the player starts without bombs
    def can_use_bombs(self, player):
        return (not self.world.bombbag[player] or self.has('Bomb Upgrade (+10)', player))

    def can_hit_crystal(self, player):
        return (self.can_use_bombs(player)
                or self.can_shoot_arrows(player)
                or self.has_blunt_weapon(player)
                or self.has('Blue Boomerang', player)
                or self.has('Red Boomerang', player)
                or self.has('Hookshot', player)
                or self.has('Fire Rod', player)
                or self.has('Ice Rod', player)
                or self.has('Cane of Somaria', player)
                or self.has('Cane of Byrna', player))
    
    def can_hit_crystal_through_barrier(self, player):
        return (self.can_use_bombs(player)
            or self.can_shoot_arrows(player)
            or self.has('Blue Boomerang', player)
            or self.has('Red Boomerang', player)
            or self.has('Fire Rod', player)
            or self.has('Ice Rod', player)
            or self.has('Cane of Somaria', player))

    def can_shoot_arrows(self, player):
        if self.world.bow_mode[player] in ['retro', 'retro_silvers']:
            #todo: Non-progressive silvers grant wooden arrows, but progressive bows do not.  Always require shop arrows to be safe
            return self.has('Bow', player) and (self.can_buy_unlimited('Single Arrow', player) or self.has('Single Arrow', player))
        return self.has('Bow', player)

    # def can_get_good_bee(self, player):
    #     cave = self.world.get_region('Good Bee Cave', player)
    #     return (
    #         self.can_use_bombs(player) and
    #         self.has_bottle(player) and
    #         self.has('Bug Catching Net', player) and
    #         (self.has_Boots(player) or (self.has_sword(player) and self.has('Quake', player))) and
    #         cave.can_reach(self) and
    #         self.is_not_bunny(cave, player)
    #     )

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
        if self.world.mode[player] == 'standard' and not self.has('Zelda Delivered', player):
            return False  # can't flute in rain state
        lw = self.world.get_region('Light World', player)
        return self.has('Ocarina (Activated)', player) or (self.has('Ocarina', player) and lw.can_reach(self)
                                                         and self.is_not_bunny(lw, player))

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

    def can_boots_clip_lw(self, player):
        if self.world.mode[player] == 'inverted':
            return self.has_Boots(player) and self.has_Pearl(player)
        return self.has_Boots(player)

    def can_boots_clip_dw(self, player):
        if self.world.mode[player] != 'inverted':
            return self.has_Boots(player) and self.has_Pearl(player)
        return self.has_Boots(player)

    def can_get_glitched_speed_lw(self, player):
        rules = [self.has_Boots(player), any([self.has('Hookshot', player), self.has_sword(player)])]
        if self.world.mode[player] == 'inverted':
            rules.append(self.has_Pearl(player))
        return all(rules)

    def can_get_glitched_speed_dw(self, player):
        rules = [self.has_Boots(player), any([self.has('Hookshot', player), self.has_sword(player)])]
        if self.world.mode[player] != 'inverted':
            rules.append(self.has_Pearl(player))
        return all(rules)

    def can_superbunny_mirror_with_sword(self, player):
        return self.has_Mirror(player) and self.has_sword(player)

    def collect(self, item, event=False, location=None):
        if location:
            self.locations_checked.add(location)
            if item and item.smallkey and location.forced_item is not None:
                self.forced_keys[item.name, item.player] += 1
        if not item:
            return
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
                elif self.has('Shield Level', item.player, 2) and self.world.difficulty_requirements[item.player].progressive_shield_limit >= 3:
                    self.prog_items['Mirror Shield', item.player] += 1
                    self.prog_items['Shield Level', item.player] += 1
                    changed = True
                elif self.has('Shield Level', item.player, 1) and self.world.difficulty_requirements[item.player].progressive_shield_limit >= 2:
                    self.prog_items['Red Shield', item.player] += 1
                    self.prog_items['Shield Level', item.player] += 1
                    changed = True
                elif self.world.difficulty_requirements[item.player].progressive_shield_limit >= 1:
                    self.prog_items['Blue Shield', item.player] += 1
                    self.prog_items['Shield Level', item.player] += 1
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
        inside_dungeon_item = ((item.smallkey and self.world.keyshuffle[item.player] == 'none')
                               or (item.bigkey and not self.world.bigkeyshuffle[item.player])
                               or (item.map and not self.world.mapshuffle[item.player])
                               or (item.compass and not self.world.compassshuffle[item.player]))
        # not all small keys to escape must be in escape
        # sewer_hack = self.world.mode[item.player] == 'standard' and item.name == 'Small Key (Escape)'
        if inside_dungeon_item:
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


class FillError(RuntimeError):
    pass


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
    if door.type in [DoorType.Normal, DoorType.Open, DoorType.StraightStairs, DoorType.Ladder]:
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
        # 0,1,2 for normal
        # 0-7 for ladder
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
        self.standard_restricted = False  # flag if portal is not allowed in HC in standard
        self.lw_restricted = False  # flag if portal is not allowed in DW
        self.rupee_bow_restricted = False  # flag if portal is not allowed in HC in standard+rupee_bow
        # self.incognitoPos = -1
        # self.sectorLink = False

        # logical properties
        # self.connected = False  # combine with Dest?
        self.dest = None
        self.blocked = False  # Indicates if the door is normally blocked off as an exit. (Sanc door or always closed)
        self.blocked_orig = False
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
        if entrance is not None and not entrance.door:
            entrance.door = self

    def getAddress(self):
        if self.type in [DoorType.Normal, DoorType.StraightStairs]:
            return 0x13A000 + normal_offset_table[self.roomIndex] * 24 + (self.doorIndex + self.direction.value * 3) * 2
        elif self.type == DoorType.SpiralStairs:
            return 0x13B000 + (spiral_offset_table[self.roomIndex] + self.doorIndex) * 4
        elif self.type == DoorType.Ladder:
            return 0x13C700 + self.doorIndex * 2
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
        if self.type == DoorType.Ladder:
            bitmask = 4 * (self.layer ^ 1 if src.toggle else self.layer)
            bitmask += 0x08 * self.doorIndex
            if src.type == DoorType.StraightStairs:
                bitmask += 0x40
            return [self.roomIndex, bitmask + 0x03]
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

    def kind(self, world):
        if self.roomIndex != -1 and self.doorListPos != -1:
            return world.get_room(self.roomIndex, self.player).kind(self)
        return None

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
        self.blocked = self.blocked_orig = True
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

    def kind(self, world):
        if self.roomIndex != -1 and self.doorListPos != -1:
            return world.get_room(self.roomIndex, self.player).kind(self)
        return None

    def dungeon_name(self):
        return self.entrance.parent_region.dungeon.name if self.entrance.parent_region.dungeon else 'Cave'

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
        self.item_logic = set()
        self.chest_location_set = set()

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
        self.chosen = False

    def find_portal_entrance(self):
        p_region = self.door.entrance.connected_region
        return next((x for x in p_region.entrances
                     if x.parent_region.type in [RegionType.LightWorld, RegionType.DarkWorld]), None)

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
        self.real = not crystal
        self.always_allow = lambda item, state: False
        self.access_rule = lambda state: True
        self.item_rule = lambda item: True
        self.player = player
        self.skip = False
        self.type = LocationType.Normal if not crystal else LocationType.Prize
        self.pot = None

    def can_fill(self, state, item, check_access=True):
        if not self.valid_multiworld(state, item):
            return False
        return self.always_allow(state, item) or (self.parent_region.can_fill(item) and self.item_rule(item) and (not check_access or self.can_reach(state)))

    def valid_multiworld(self, state, item):
        if self.type == LocationType.Pot and self.player != item.player:
            return state.world.pot_contents[self.player].multiworld_count < 256
        return True

    def can_reach(self, state):
        return self.parent_region.can_reach(state) and self.access_rule(state)

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
        if self.parent_region.dungeon and world and world.doorShuffle[self.player] not in ['basic', 'vanilla']:
            name += f' @ {self.parent_region.dungeon.name}'
        if world and world.players > 1:
            name += f' ({world.get_player_names(self.player)})'
        return name

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        world = self.parent_region.world if self.parent_region and self.parent_region.world else None
        return world.get_name_string_for_object(self) if world else f'{self.name} (Player {self.player})'

    def __eq__(self, other):
        return self.name == other.name and self.player == other.player

    def __hash__(self):
        return hash((self.name, self.player))


class LocationType(FastEnum):
    Normal = 0
    Prize = 1
    Logical = 2
    Shop = 3
    Pot = 4
    Drop = 5


class Item(object):

    def __init__(self, name='', advancement=False, priority=False, type=None, code=None, price=999, pedestal_hint=None,
                 pedestal_credit=None, sickkid_credit=None, zora_credit=None, witch_credit=None, fluteboy_credit=None,
                 hint_text=None, player=None):
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
        self.price = price
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

    @property
    def dungeon(self):
        if not self.smallkey and not self.bigkey and not self.map and not self.compass:
            return None
        item_dungeon = self.name.split('(')[1][:-1]
        if item_dungeon == 'Escape':
            item_dungeon = 'Hyrule Castle'
        return item_dungeon

    def is_inside_dungeon_item(self, world):
        return ((self.smallkey and world.keyshuffle[self.player] == 'none')
                or (self.bigkey and not world.bigkeyshuffle[self.player])
                or (self.compass and not world.compassshuffle[self.player])
                or (self.map and not world.mapshuffle[self.player]))

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return self.world.get_name_string_for_object(self) if self.world else f'{self.name} (Player {self.player})'

    def __eq__(self, other):
        return self.name == other.name and self.player == other.player


# have 6 address that need to be filled
class Crystal(Item):
    pass

@unique
class ShopType(Enum):
    Shop = 0
    TakeAny = 1
    UpgradeShop = 2

class Shop(object):
    def __init__(self, region, room_id, type, shopkeeper_config, custom, locked, sram_address):
        self.region = region
        self.room_id = room_id
        self.type = type
        self.inventory = [None, None, None]
        self.shopkeeper_config = shopkeeper_config
        self.custom = custom
        self.locked = locked
        self.sram_address = sram_address

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
            config |= 0x40  # ignore door id
        if self.type == ShopType.TakeAny:
            config |= 0x80
        if self.type == ShopType.UpgradeShop:
            config |= 0x10  # Alt. VRAM
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

    def add_inventory(self, slot: int, item, price, max=0, replacement=None, replacement_price=0,
                      create_location=False, player=0):
        self.inventory[slot] = {
            'item': item,
            'price': price,
            'max': max,
            'replacement': replacement,
            'replacement_price': replacement_price,
            'create_location': create_location,
            'player': player
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
        self.bottles = {}
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

    def parse_meta(self):
        from Main import __version__ as ERVersion

        self.startinventory = list(map(str, self.world.precollected_items))
        self.metadata = {'version': ERVersion,
                         'logic': self.world.logic,
                         'mode': self.world.mode,
                         'bombbag': self.world.bombbag,
                         'weapons': self.world.swords,
                         'flute_mode': self.world.flute_mode,
                         'bow_mode': self.world.bow_mode,
                         'goal': self.world.goal,
                         'shuffle': self.world.shuffle,
                         'shuffleganon': self.world.shuffle_ganon,
                         'shufflelinks': self.world.shufflelinks,
                         'shuffletavern': self.world.shuffletavern,
                         'take_any': self.world.take_any,
                         'overworld_map': self.world.overworld_map,
                         'door_shuffle': self.world.doorShuffle,
                         'intensity': self.world.intensity,
                         'door_type_mode': self.world.door_type_mode,
                         'trap_door_mode': self.world.trap_door_mode,
                         'key_logic': self.world.key_logic_algorithm,
                         'decoupledoors': self.world.decoupledoors,
                         'dungeon_counters': self.world.dungeon_counters,
                         'item_pool': self.world.difficulty,
                         'item_functionality': self.world.difficulty_adjustments,
                         'gt_crystals': self.world.crystals_needed_for_gt,
                         'ganon_crystals': self.world.crystals_needed_for_ganon,
                         'open_pyramid': self.world.open_pyramid,
                         'accessibility': self.world.accessibility,
                         'restricted_boss_items': self.world.restrict_boss_items,
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
                         'dropshuffle': self.world.dropshuffle,
                         'pottery': self.world.pottery,
                         'potshuffle': self.world.potshuffle,
                         'shopsanity': self.world.shopsanity,
                         'pseudoboots': self.world.pseudoboots,
                         'triforcegoal': self.world.treasure_hunt_count,
                         'triforcepool': self.world.treasure_hunt_total,
                         'race': self.world.settings.world_rep['meta']['race'],
                         'code': {p: Settings.make_code(self.world, p) for p in range(1, self.world.players + 1)},
                         'seed': self.world.seed
                         }
        
        if self.world.seed_name:
            self.metadata['seed_name'] = self.world.seed_name
        if self.world.seed_notes:
            self.metadata['seed_notes'] = self.world.seed_notes

        for p in range(1, self.world.players + 1):
            from ItemList import set_default_triforce
            if self.world.custom and p in self.world.customitemarray:
                self.metadata['triforcegoal'][p], self.metadata['triforcepool'][p] = set_default_triforce(self.metadata['goal'][p], self.world.customitemarray[p]["triforcepiecesgoal"], self.world.customitemarray[p]["triforcepieces"])
            else:
                custom_goal = self.world.treasure_hunt_count[p] if isinstance(self.world.treasure_hunt_count, dict) else self.world.treasure_hunt_count
                custom_total = self.world.treasure_hunt_total[p] if isinstance(self.world.treasure_hunt_total, dict) else self.world.treasure_hunt_total
                self.metadata['triforcegoal'][p], self.metadata['triforcepool'][p] = set_default_triforce(self.metadata['goal'][p], custom_goal, custom_total)

    def parse_data(self):
        self.medallions = OrderedDict()
        if self.world.players == 1:
            self.medallions['Misery Mire'] = self.world.required_medallions[1][0]
            self.medallions['Turtle Rock'] = self.world.required_medallions[1][1]
        else:
            for player in range(1, self.world.players + 1):
                self.medallions[f'Misery Mire ({self.world.get_player_names(player)})'] = self.world.required_medallions[player][0]
                self.medallions[f'Turtle Rock ({self.world.get_player_names(player)})'] = self.world.required_medallions[player][1]

        self.bottles = OrderedDict()
        if self.world.players == 1:
            self.bottles['Waterfall Bottle'] = self.world.bottle_refills[1][0]
            self.bottles['Pyramid Bottle'] = self.world.bottle_refills[1][1]
        else:
            for player in range(1, self.world.players + 1):
                self.bottles[f'Waterfall Bottle ({self.world.get_player_names(player)})'] = self.world.bottle_refills[player][0]
                self.bottles[f'Pyramid Bottle ({self.world.get_player_names(player)})'] = self.world.bottle_refills[player][1]

        self.locations = OrderedDict()
        listed_locations = set()

        lw_locations = [loc for loc in self.world.get_locations() if loc not in listed_locations and loc.parent_region and loc.parent_region.type == RegionType.LightWorld]
        self.locations['Light World'] = OrderedDict([(location.gen_name(), str(location.item) if location.item is not None else 'Nothing') for location in lw_locations])
        listed_locations.update(lw_locations)

        dw_locations = [loc for loc in self.world.get_locations() if loc not in listed_locations and loc.parent_region and loc.parent_region.type == RegionType.DarkWorld]
        self.locations['Dark World'] = OrderedDict([(location.gen_name(), str(location.item) if location.item is not None else 'Nothing') for location in dw_locations])
        listed_locations.update(dw_locations)

        cave_locations = [loc for loc in self.world.get_locations() if loc not in listed_locations and loc.parent_region and loc.parent_region.type == RegionType.Cave and not loc.skip]
        self.locations['Caves'] = OrderedDict([(location.gen_name(), str(location.item) if location.item is not None else 'Nothing') for location in cave_locations])
        listed_locations.update(cave_locations)

        for dungeon in self.world.dungeons:
            dungeon_locations = [loc for loc in self.world.get_locations() if loc not in listed_locations and loc.parent_region and loc.parent_region.dungeon == dungeon and not loc.forced_item and not loc.skip]
            self.locations[str(dungeon)] = OrderedDict([(location.gen_name(), str(location.item) if location.item is not None else 'Nothing') for location in dungeon_locations])
            listed_locations.update(dungeon_locations)

        other_locations = [loc for loc in self.world.get_locations() if loc not in listed_locations and not loc.skip]
        if other_locations:
            self.locations['Other Locations'] = OrderedDict([(location.gen_name(), str(location.item) if location.item is not None else 'Nothing') for location in other_locations])
            listed_locations.update(other_locations)

        self.shops = []
        for player in range(1, self.world.players + 1):
            for shop in self.world.shops[player]:
                if not shop.custom:
                    continue
                shopdata = {'location': str(shop.region),
                            'type': 'Take Any' if shop.type == ShopType.TakeAny else 'Shop'
                            }
                for index, item in enumerate(shop.inventory):
                    if item is None:
                        continue
                    if self.world.players == 1:
                        shopdata[f'item_{index}'] = f"{item['item']} — {item['price']}" if item['price'] else item['item']
                    else:
                        shopdata[f'item_{index}'] = f"{item['item']} (Player {item['player']}) — {item['price']}"
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
            if self.world.intensity[player] >= 3 and self.world.doorShuffle[player] != 'vanilla':
                for portal in self.world.dungeon_portals[player]:
                    self.set_lobby(portal.name, portal.door.name, player)

    def to_json(self):
        self.parse_meta()
        self.parse_data()
        out = OrderedDict()
        out['Entrances'] = list(self.entrances.values())
        out['Doors'] = list(self.doors.values())
        out['Lobbies'] = list(self.lobbies.values())
        out['DoorTypes'] = list(self.doorTypes.values())
        out.update(self.locations)
        out['Starting Inventory'] = self.startinventory
        out['Special'] = self.medallions
        out['Bottles'] = self.bottles
        if self.hashes:
            out['Hashes'] = {f"{self.world.player_names[player][team]} (Team {team+1})": hash for (player, team), hash in self.hashes.items()}
        if self.shops:
            out['Shops'] = self.shops
        out['playthrough'] = self.playthrough
        out['paths'] = self.paths
        out['Bosses'] = self.bosses
        out['meta'] = self.metadata

        return json.dumps(out)

    def mystery_meta_to_file(self, filename):
        self.parse_meta()
        with open(filename, 'w') as outfile:
            outfile.write(f'ALttP Dungeon Randomizer Version {self.metadata["version"]}\n\n')
            for player in range(1, self.world.players + 1):
                if self.world.players > 1:
                    outfile.write('\nPlayer %d: %s\n' % (player, self.world.get_player_names(player)))
                outfile.write('Logic:                           %s\n' % self.metadata['logic'][player])

    def meta_to_file(self, filename):
        def yn(flag):
            return 'Yes' if flag else 'No'

        line_width = 35
        self.parse_meta()
        with open(filename, 'w') as outfile:
            outfile.write('ALttP Dungeon Randomizer Version %s  -  Seed: %s\n\n' % (self.metadata['version'], self.world.seed))
            if self.world.seed_name:
                outfile.write('Seed Name:                       %s\n' % self.world.seed_name)
            outfile.write('Filling Algorithm:               %s\n' % self.world.algorithm)
            outfile.write('Players:                         %d\n' % self.world.players)
            outfile.write('Teams:                           %d\n' % self.world.teams)
            for player in range(1, self.world.players + 1):
                if self.world.players > 1:
                    outfile.write('\nPlayer %d: %s\n' % (player, self.world.get_player_names(player)))
                outfile.write(f'Settings Code:                   {self.metadata["code"][player]}\n')
                outfile.write('Logic:                           %s\n' % self.metadata['logic'][player])
                outfile.write('Mode:                            %s\n' % self.metadata['mode'][player])
                outfile.write('Swords:                          %s\n' % self.metadata['weapons'][player])
                outfile.write('Goal:                            %s\n' % self.metadata['goal'][player])
                if self.metadata['goal'][player] in ['triforcehunt', 'trinity', 'ganonhunt']:
                    outfile.write('Triforce Pieces Required:        %s\n' % self.metadata['triforcegoal'][player])
                    outfile.write('Triforce Pieces Total:           %s\n' % self.metadata['triforcepool'][player])
                outfile.write('Crystals required for GT:        %s\n' % (str(self.world.crystals_gt_orig[player])))
                outfile.write('Crystals required for Ganon:     %s\n' % (str(self.world.crystals_ganon_orig[player])))
                outfile.write('Accessibility:                   %s\n' % self.metadata['accessibility'][player])
                outfile.write(f"Restricted Boss Items:           {self.metadata['restricted_boss_items'][player]}\n")
                outfile.write('Difficulty:                      %s\n' % self.metadata['item_pool'][player])
                outfile.write('Item Functionality:              %s\n' % self.metadata['item_functionality'][player])
                outfile.write(f"Flute Mode:                      {self.metadata['flute_mode'][player]}\n")
                outfile.write(f"Bow Mode:                        {self.metadata['bow_mode'][player]}\n")
                outfile.write(f"Shopsanity:                      {yn(self.metadata['shopsanity'][player])}\n")
                outfile.write(f"Bombbag:                         {yn(self.metadata['bombbag'][player])}\n")
                outfile.write(f"Pseudoboots:                     {yn(self.metadata['pseudoboots'][player])}\n")
                outfile.write('Entrance Shuffle:                %s\n' % self.metadata['shuffle'][player])
                if self.metadata['shuffle'][player] != 'vanilla':
                    outfile.write(f"Link's House Shuffled:           {yn(self.metadata['shufflelinks'][player])}\n")
                    outfile.write(f"Back of Tavern Shuffled:         {yn(self.metadata['shuffletavern'][player])}\n")
                    outfile.write(f"GT/Ganon Shuffled:               {yn(self.metadata['shuffleganon'])}\n")
                    outfile.write(f"Overworld Map:                   {self.metadata['overworld_map'][player]}\n")
                outfile.write(f"Take Any Caves:                  {self.metadata['take_any'][player]}\n")
                if self.metadata['goal'][player] != 'trinity':
                    outfile.write('Pyramid hole pre-opened:         %s\n' % (self.metadata['open_pyramid'][player]))
                outfile.write('Door Shuffle:                    %s\n' % self.metadata['door_shuffle'][player])
                if self.metadata['door_shuffle'][player] != 'vanilla':
                    outfile.write(f"Intensity:                       {self.metadata['intensity'][player]}\n")
                    outfile.write(f"Door Type Mode:                  {self.metadata['door_type_mode'][player]}\n")
                    outfile.write(f"Trap Door Mode:                  {self.metadata['trap_door_mode'][player]}\n")
                    outfile.write(f"Key Logic Algorithm:             {self.metadata['key_logic'][player]}\n")
                    outfile.write(f"Decouple Doors:                  {yn(self.metadata['decoupledoors'][player])}\n")
                    outfile.write(f"Experimental:                    {yn(self.metadata['experimental'][player])}\n")
                outfile.write(f"Dungeon Counters:                {self.metadata['dungeon_counters'][player]}\n")
                outfile.write(f"Drop Shuffle:                    {yn(self.metadata['dropshuffle'][player])}\n")
                outfile.write(f"Pottery Mode:                    {self.metadata['pottery'][player]}\n")
                outfile.write(f"Pot Shuffle (Legacy):            {yn(self.metadata['potshuffle'][player])}\n")
                outfile.write('Map shuffle:                     %s\n' % ('Yes' if self.metadata['mapshuffle'][player] else 'No'))
                outfile.write('Compass shuffle:                 %s\n' % ('Yes' if self.metadata['compassshuffle'][player] else 'No'))
                outfile.write(f"Small Key shuffle:               {self.metadata['keyshuffle'][player]}\n")
                outfile.write('Big Key shuffle:                 %s\n' % ('Yes' if self.metadata['bigkeyshuffle'][player] else 'No'))
                outfile.write('Boss shuffle:                    %s\n' % self.metadata['boss_shuffle'][player])
                outfile.write('Enemy shuffle:                   %s\n' % self.metadata['enemy_shuffle'][player])
                outfile.write('Enemy health:                    %s\n' % self.metadata['enemy_health'][player])
                outfile.write('Enemy damage:                    %s\n' % self.metadata['enemy_damage'][player])
                outfile.write(f"Hints:                           {yn(self.metadata['hints'][player])}\n")
                outfile.write('Race:                            %s\n' % ('Yes' if self.world.settings.world_rep['meta']['race'] else 'No'))
                if self.world.seed_notes:
                    outfile.write('Notes:                           %s\n' % self.world.seed_notes)

            if self.startinventory:
                outfile.write('Starting Inventory:'.ljust(line_width))
                outfile.write('\n'.ljust(line_width+1).join(self.startinventory) + '\n')

    def hashes_to_file(self, filename):
        with open(filename, 'r') as infile:
            contents = infile.readlines()

        def insert(lines, i, value):
            lines.insert(i, value)
            i += 1
            return i

        idx = 2
        if self.world.players > 1:
            idx = insert(contents, idx, 'Hashes:')
        for player in range(1, self.world.players + 1):
            if self.world.players > 1:
                idx = insert(contents, idx, f'\nPlayer {player}: {self.world.get_player_names(player)}\n')
            if len(self.hashes) > 0:
                for team in range(self.world.teams):
                    player_name = self.world.player_names[player][team]
                    label = f"Hash - {player_name} (Team {team+1}): " if self.world.teams > 1 else 'Hash: '
                    idx = insert(contents, idx, f'{label}{self.hashes[player, team]}\n')
        if self.world.players > 1:
            insert(contents, idx, '\n')  # return value ignored here, if you want to add more lines

        with open(filename, "w") as f:
            contents = "".join(contents)
            f.write(contents)

    def to_file(self, filename):
        self.parse_data()
        with open(filename, 'a') as outfile:
            line_width = 35

            outfile.write('\nRequirements:\n\n')
            for dungeon, medallion in self.medallions.items():
                outfile.write(f'{dungeon}: {medallion} Medallion\n')
            for player in range(1, self.world.players + 1):
                player_name = '' if self.world.players == 1 else str(' (Player ' + str(player) + ')')
                if self.world.crystals_gt_orig[player] == 'random':
                    outfile.write(str('Crystals Required for GT' + player_name + ':').ljust(line_width) + '%s\n' % (str(self.metadata['gt_crystals'][player])))
                if self.world.crystals_ganon_orig[player] == 'random':
                    outfile.write(str('Crystals Required for Ganon' + player_name + ':').ljust(line_width) + '%s\n' % (str(self.metadata['ganon_crystals'][player])))

            outfile.write('\n\nBottle Refills:\n\n')
            for fairy, bottle in self.bottles.items():
                outfile.write(f'{fairy}: {bottle}\n')

            if self.entrances:
                # entrances: To/From overworld; Checking w/ & w/out "Exit" and translating accordingly
                outfile.write('\nEntrances:\n\n')
                outfile.write('\n'.join(['%s%s %s %s' % (f'{self.world.get_player_names(entry["player"])}: ' if self.world.players > 1 else '', self.world.fish.translate("meta","entrances",entry['entrance']), '<=>' if entry['direction'] == 'both' else '<=' if entry['direction'] == 'exit' else '=>', self.world.fish.translate("meta","entrances",entry['exit'])) for entry in self.entrances.values()]))

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
                    bossmap = self.bosses[str(player)] if self.world.players > 1 else self.bosses
                    outfile.write(f'\n\nBosses ({self.world.get_player_names(player)}):\n\n')
                    outfile.write('\n'.join([f'{x}: {y}' for x, y in bossmap.items() if y not in ['Agahnim', 'Agahnim 2', 'Ganon']]))

    def playthrough_to_file(self, filename):
        with open(filename, 'a') as outfile:
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

dungeon_keys = {
    'Hyrule Castle': 'Small Key (Escape)',
    'Eastern Palace': 'Small Key (Eastern Palace)',
    'Desert Palace': 'Small Key (Desert Palace)',
    'Tower of Hera': 'Small Key (Tower of Hera)',
    'Agahnims Tower': 'Small Key (Agahnims Tower)',
    'Palace of Darkness': 'Small Key (Palace of Darkness)',
    'Swamp Palace': 'Small Key (Swamp Palace)',
    'Skull Woods': 'Small Key (Skull Woods)',
    'Thieves Town': 'Small Key (Thieves Town)',
    'Ice Palace': 'Small Key (Ice Palace)',
    'Misery Mire': 'Small Key (Misery Mire)',
    'Turtle Rock': 'Small Key (Turtle Rock)',
    'Ganons Tower': 'Small Key (Ganons Tower)',
    'Universal': 'Small Key (Universal)'
}

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
    Block = 0x4  # This is actually a block
    LowerRegion = 0x8  # This is a pot in the lower region


class Pot(object):
    def __init__(self, x, y, item, room, flags=PotFlags.Normal, obj=None):
        self.x = x
        self.y = y
        self.item = item
        self.room = room
        self.flags = flags
        self.indicator = None  # 0x80 for standing item, 0xC0 multiworld item
        self.standing_item_code = None  # standing item code if nay
        self.obj_ref = obj
        self.location = None  # location back ref

    def copy(self):
        obj_ref = RoomObject(self.obj_ref.address, self.obj_ref.data) if self.obj_ref else None
        return Pot(self.x, self.y, self.item, self.room, self.flags, obj_ref)

    def pot_data(self):
        high_byte = self.y
        if self.flags & PotFlags.LowerRegion:
            high_byte |= 0x20
        if self.indicator:
            high_byte |= self.indicator
        item = self.item if not self.indicator else self.standing_item_code
        return [self.x, high_byte, item]

    def get_region(self, world, player):
        return world.get_region(self.room, 1)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.room == other.room

    def __hash__(self):
        return hash((self.x, self.y, self.room))


# byte 0: DDDE EEEE (DR, ER)
dr_mode = {"basic": 1, "crossed": 2, "vanilla": 0, "partitioned": 3}
er_mode = {"vanilla": 0, "simple": 1, "restricted": 2, "full": 3, "crossed": 4, "insanity": 5, 'lite': 8,
           'lean': 9, "dungeonsfull": 7, "dungeonssimple": 6}

# byte 1: LLLW WSS? (logic, mode, sword)
logic_mode = {"noglitches": 0, "minorglitches": 1, "nologic": 2, "owglitches": 3, "majorglitches": 4}
world_mode = {"open": 0, "standard": 1, "inverted": 2}
sword_mode = {"random": 0,  "assured": 1, "swordless": 2, "vanilla": 3}

# byte 2: GGGD DFFH (goal, diff, item_func, hints)
goal_mode = {'ganon': 0, 'pedestal': 1, 'dungeons': 2, 'triforcehunt': 3, 'crystals': 4, 'trinity': 5,
             'ganonhunt': 6, 'completionist': 7}
diff_mode = {"normal": 0, "hard": 1, "expert": 2}
func_mode = {"normal": 0, "hard": 1, "expert": 2}

# byte 3: SDMM PIII (shop, decouple doors, mixed, palettes, intensity)
# keydrop now has it's own byte
mixed_travel_mode = {"prevent": 0, "allow": 1, "force": 2}
# intensity is 3 bits (reserves 4-7 levels)

# new byte 4: TDDD PPPP (tavern shuffle, drop, pottery)
# dropshuffle reserves 2 bits, pottery needs 4)
pottery_mode = {'none': 0, 'keys': 2, 'lottery': 3, 'dungeon': 4, 'cave': 5, 'cavekeys': 6, 'reduced': 7,
                'clustered': 8, 'nonempty': 9}

# byte 5: CCCC CTTX (crystals gt, ctr2, experimental)
counter_mode = {"default": 0, "off": 1, "on": 2, "pickup": 3}

# byte 6: CCCC CPAA (crystals ganon, pyramid, access
access_mode = {"items": 0, "locations": 1, "none": 2}

# byte 7: B?MC DDEE (big, ?, maps, compass, door_type, enemies)
door_type_mode = {'original': 0, 'big': 1, 'all': 2, 'chaos': 3}
enemy_mode = {"none": 0, "shuffled": 1, "chaos": 2, "random": 2, "legacy": 3}

# byte 8: HHHD DPBS (enemy_health, enemy_dmg, potshuffle, bomb logic, shuffle links)
# potshuffle decprecated, now unused
e_health = {"default": 0, "easy": 1, "normal": 2, "hard": 3, "expert": 4}
e_dmg = {"default": 0, "shuffled": 1, "random": 2}

# byte 9: RRAA ABBB (restrict boss mode, algorithm, boss shuffle)
rb_mode = {"none": 0, "mapcompass": 1, "dungeon": 2}
# algorithm:
algo_mode = {"balanced": 0, "equitable": 1, "vanilla_fill": 2, "dungeon_only": 3, "district": 4, 'major_only': 5}
boss_mode = {"none": 0, "simple": 1, "full": 2, "chaos": 3, 'random': 3, 'unique': 4}


# byte 10: settings_version
# byte 11: FBBB TTSS (flute_mode, bow_mode, take_any, small_key_mode)
flute_mode = {'normal': 0, 'active': 1}
keyshuffle_mode = {'none': 0, 'wild': 1, 'universal': 2}  # reserved 8 modes?
take_any_mode = {'none': 0, 'random': 1, 'fixed': 2}
bow_mode = {'progressive': 0, 'silvers': 1, 'retro': 2, 'retro_silvers': 3}

# additions
# byte 12: POOT TKKK (pseudoboots, overworld_map, trap_door_mode, key_logic_algo)
overworld_map_mode = {'default': 0, 'compass': 1, 'map': 2}
trap_door_mode = {'vanilla': 0, 'optional': 1, 'boss': 2, 'oneway': 3}
key_logic_algo = {'default': 0, 'partial': 1, 'strict': 2}

# sfx_shuffle and other adjust items does not affect settings code

# Bump this when making changes that are not backwards compatible (nearly all of them)
settings_version = 1


class Settings(object):

    @staticmethod
    def make_code(w, p):
        code = bytes([
            (dr_mode[w.doorShuffle[p]] << 5) | er_mode[w.shuffle[p]],

            (logic_mode[w.logic[p]] << 5) | (world_mode[w.mode[p]] << 3)
            | (sword_mode[w.swords[p]] << 1),

            (goal_mode[w.goal[p]] << 5) | (diff_mode[w.difficulty[p]] << 3)
            | (func_mode[w.difficulty_adjustments[p]] << 1) | (1 if w.hints[p] else 0),

            (0x80 if w.shopsanity[p] else 0) | (0x40 if w.decoupledoors[p] else 0)
            | (mixed_travel_mode[w.mixed_travel[p]] << 4)
            | (0x8 if w.standardize_palettes[p] == "original" else 0)
            | (0 if w.intensity[p] == "random" else w.intensity[p]),

            (0x80 if w.shuffletavern[p] else 0) | (0x10 if w.dropshuffle[p] else 0) | (pottery_mode[w.pottery[p]]),

            ((8 if w.crystals_gt_orig[p] == "random" else int(w.crystals_gt_orig[p])) << 3)
            | (counter_mode[w.dungeon_counters[p]] << 1) | (1 if w.experimental[p] else 0),

            ((8 if w.crystals_ganon_orig[p] == "random" else int(w.crystals_ganon_orig[p])) << 3)
            | (0x4 if w.is_pyramid_open(p) else 0) | access_mode[w.accessibility[p]],

            (0x80 if w.bigkeyshuffle[p] else 0)
            | (0x20 if w.mapshuffle[p] else 0) | (0x10 if w.compassshuffle[p] else 0)
            | (door_type_mode[w.door_type_mode[p]] << 2) | (enemy_mode[w.enemy_shuffle[p]]),

            (e_health[w.enemy_health[p]] << 5) | (e_dmg[w.enemy_damage[p]] << 3) | (0x4 if w.potshuffle[p] else 0)
            | (0x2 if w.bombbag[p] else 0) | (1 if w.shufflelinks[p] else 0),

            (rb_mode[w.restrict_boss_items[p]] << 6) | (algo_mode[w.algorithm] << 3) | (boss_mode[w.boss_shuffle[p]]),

            settings_version,

            (flute_mode[w.flute_mode[p]] << 7 | bow_mode[w.bow_mode[p]] << 4
             | take_any_mode[w.take_any[p]] << 2 | keyshuffle_mode[w.keyshuffle[p]]),

            ((0x80 if w.pseudoboots[p] else 0) | overworld_map_mode[w.overworld_map[p]] << 6
             | trap_door_mode[w.trap_door_mode[p]] << 4 | key_logic_algo[w.key_logic_algorithm[p]]),
            ])
        return base64.b64encode(code, "+-".encode()).decode()

    @staticmethod
    def adjust_args_from_code(code, player, args):
        settings, p = base64.b64decode(code.encode(), "+-".encode()), player

        if len(settings) < 12:
            raise Exception('Provided code is incompatible with this version')
        if settings[10] != settings_version:
            raise Exception('Provided code is incompatible with this version')

        def r(d):
            return {y: x for x, y in d.items()}

        args.shuffle[p] = r(er_mode)[settings[0] & 0x1F]
        args.door_shuffle[p] = r(dr_mode)[(settings[0] & 0xE0) >> 5]
        args.logic[p] = r(logic_mode)[(settings[1] & 0xE0) >> 5]
        args.mode[p] = r(world_mode)[(settings[1] & 0x18) >> 3]
        args.swords[p] = r(sword_mode)[(settings[1] & 0x6) >> 1]
        args.difficulty[p] = r(diff_mode)[(settings[2] & 0x18) >> 3]
        args.item_functionality[p] = r(func_mode)[(settings[2] & 0x6) >> 1]
        args.goal[p] = r(goal_mode)[(settings[2] & 0xE0) >> 5]
        args.accessibility[p] = r(access_mode)[settings[6] & 0x3]
        # args.retro[p] = True if settings[1] & 0x01 else False
        args.hints[p] = True if settings[2] & 0x01 else False
        args.shopsanity[p] = True if settings[3] & 0x80 else False
        args.decoupledoors[p] = True if settings[3] & 0x40 else False
        args.mixed_travel[p] = r(mixed_travel_mode)[(settings[3] & 0x30) >> 4]
        args.standardize_palettes[p] = "original" if settings[3] & 0x8 else "standardize"
        intensity = settings[3] & 0x7
        args.intensity[p] = "random" if intensity == 0 else intensity

        args.shuffletavern[p] = True if settings[4] & 0x80 else False
        args.dropshuffle[p] = True if settings[4] & 0x10 else False
        args.pottery[p] = r(pottery_mode)[settings[4] & 0x0F]

        args.dungeon_counters[p] = r(counter_mode)[(settings[5] & 0x6) >> 1]
        cgt = (settings[5] & 0xf8) >> 3
        args.crystals_gt[p] = "random" if cgt == 8 else cgt
        args.experimental[p] = True if settings[5] & 0x1 else False

        cgan = (settings[6] & 0xf8) >> 3
        args.crystals_ganon[p] = "random" if cgan == 8 else cgan
        args.openpyramid[p] = True if settings[6] & 0x4 else False

        args.bigkeyshuffle[p] = True if settings[7] & 0x80 else False
        # args.keyshuffle[p] = True if settings[7] & 0x40 else False
        args.mapshuffle[p] = True if settings[7] & 0x20 else False
        args.compassshuffle[p] = True if settings[7] & 0x10 else False
        args.door_type_mode[p] = r(door_type_mode)[(settings[7] & 0xc) >> 2]
        args.shuffleenemies[p] = r(enemy_mode)[settings[7] & 0x3]

        args.enemy_health[p] = r(e_health)[(settings[8] & 0xE0) >> 5]
        args.enemy_damage[p] = r(e_dmg)[(settings[8] & 0x18) >> 3]
        args.shufflepots[p] = True if settings[8] & 0x4 else False
        args.bombbag[p] = True if settings[8] & 0x2 else False
        args.shufflelinks[p] = True if settings[8] & 0x1 else False
        if len(settings) > 9:
            args.restrict_boss_items[p] = r(rb_mode)[(settings[9] & 0xC0) >> 6]
            args.algorithm = r(algo_mode)[(settings[9] & 0x38) >> 3]
            args.shufflebosses[p] = r(boss_mode)[(settings[9] & 0x07)]
        if len(settings) > 11:
            args.flute_mode[p] = r(flute_mode)[(settings[11] & 0x80) >> 7]
            args.bow_mode[p] = r(bow_mode)[(settings[11] & 0x70) >> 4]
            args.take_any[p] = r(take_any_mode)[(settings[11] & 0xC) >> 2]
            args.keyshuffle[p] = r(keyshuffle_mode)[settings[11] & 0x3]
        if len(settings) > 12:
            args.pseudoboots[p] = True if settings[12] & 0x80 else False
            args.overworld_map[p] = r(overworld_map_mode)[(settings[12] & 0x60) >> 6]
            args.trap_door_mode[p] = r(trap_door_mode)[(settings[12] & 0x14) >> 4]
            args.key_logic_algorithm[p] = r(key_logic_algo)[settings[12] & 0x07]


class KeyRuleType(FastEnum):
    WorstCase = 0
    AllowSmall = 1
    Lock = 2
