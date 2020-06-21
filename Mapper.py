import graphviz
from collections import defaultdict, deque
from graphviz import Digraph, Graph
from DungeonGenerator import convert_regions
from BaseClasses import RegionType, Door, DoorType, Direction, Sector, CrystalBarrier, Direction, Region
from DoorShuffle import interior_doors, logical_connections, dungeon_warps, switch_dir_safe
from MapData import region_to_rooms, make_room

from decimal import Decimal

DHalf = Decimal('0.5')
DZero = Decimal(0)

def drange(start, stop, step):
    assert(type(start) != float)
    assert(type(stop) != float)
    assert(type(step) != float)
    start = Decimal(start)
    stop = Decimal(stop)

    step = Decimal(step)
    r = start
    while r < stop:
        yield r
        r += step



def get_door_port(region, door, is_lead):
    print(f'Gen door for {door and door.name}')

    if door:
        if type(door) != Door:
            print('not a door')
            return ''

        if door.type == DoorType.Warp:
            print('warp')
            return ''
        elif door.type == DoorType.Hole:
            print('hole')
            if is_lead:
                return ''
            return ''

        port_mapping = {
            Direction.West : 'w',
            Direction.East : 'e',
            Direction.South : 's',
            Direction.North : 'n',
            #Direction.Up : ':n',  # Allow any direction, these are stairs...
            #Direction.Down : ':s',
        }

        if door.direction not in port_mapping:
            print('not a dir')
            return ''

        #assert(door.type != DoorType.Interior)
        if door.type == DoorType.Interior:
            print('WARNING: interior door not combined!!!!')
            print(door.name)
            return ''

        if door.doorIndex == -1:
            print('No doorindex :\'(')
            return ''

        #(No, 0x9b, Left, High)
        supertile = supertile_for_room(merged_room_data[region.name])
        dir_str = str(door.direction).replace('Direction.', '')
        s = f':{supertile}_{dir_str}_{door.doorIndex}'
         
        print(f'{door.name} <=> {s}')

        return s



def generate_connection(region_to_horiz_region, graph, region, connect, door_a, door_b):
    arrow_dir = 'forward'
    if type(door_b) == Door:
        if not door_b.blocked and not door_a.blocked:
            arrow_dir = 'both'
        elif door_a.blocked:
            arrow_dir = 'back'
    else:
        #print(f"Warning {door_b} is not a door")
        pass
    

    name_a = region_to_horiz_region[region][0].name + get_door_port(region, door_a, True)
    name_b = region_to_horiz_region[connect][0].name + get_door_port(connect, door_b, False)
    
    if door_a.type in [DoorType.Normal]:
        style = 'solid'
    else:
        style = 'dashed'

    if door_a.type in [DoorType.Interior]:
        color = 'red'
    else:
        color = 'black'

    constraint_types = [
        DoorType.Normal,
        DoorType.StraightStairs,
        DoorType.Hole,
        DoorType.Interior,
        DoorType.Open,
    ]
    constraint= 'true' if door_a.type in constraint_types else 'false'

    spline = 'polyline' if door_a.type == DoorType.SpiralStairs or door_a.type == DoorType.Warp else 'spline'

    if door_a.direction == Direction.East or door_a.direction == Direction.West:
        assert(constraint)

    # fix horizontal order
    if door_a.direction == Direction.West or door_a.direction == Direction.South or door_a.type == DoorType.Hole or door_a.type == DoorType.Warp:
        if arrow_dir == 'forward':
            arrow_dir = 'back'
        elif arrow_dir == 'back':
            arrow_dir = 'forward'
        graph.edge(name_b, name_a, dir=arrow_dir,constraint=constraint, splines=spline, style=style, color=color)
    else:
        graph.edge(name_a, name_b, dir=arrow_dir,constraint=constraint,splines=spline, style=style, color=color)

def is_valid_map_exit(exit):
    return exit.door and get_region(exit) and get_region(exit).type == RegionType.Dungeon

def opposite_ew_dir(direction):
    if direction == Direction.East:
        return Direction.East
    elif direction == Direction.West:
        return Direction.West
    assert(False)

# I have....regrets
def get_valid_single_dirs(region):
    dirs, exits = get_valid_single_dirs_inner(region)
    return dirs

def get_valid_single_exits(region):
    dirs, exits = get_valid_single_dirs_inner(region)
    return exits

def get_valid_single_dirs_inner(region, noisy=False):
    num_exits_dir = {}
    found_exits_dir = {}
    exits_for_dir = {}
    for exit in region.exits:
        if not is_valid_map_exit(exit):
            if noisy:
                print("Skipped " + str(exit.door.name) + " not valid")
            continue

        # allowed to loop on self
        if get_region(exit) == region:
            if noisy:
                print("Skipped " + str(exit.door.name) + " self loop")
            continue

        direction = exit.door.direction

        #defaultdict

        # allowed multiple arrows to the same place
        # TODO: maybe shouldn't allow multiple exits to same place
        if direction not in found_exits_dir or found_exits_dir[direction] != get_region(exit):
            if noisy:
                print("Added " + str(exit.door.name) + " on " + str(direction))
            num_exits_dir.setdefault(direction, 0)
            num_exits_dir[direction] += 1
            #if num_exits_dir[direction] > 1:
            #    print("invalid dir!")
            found_exits_dir.setdefault(direction, []).append(get_region(exit))
            exits_for_dir[direction] = exit
        else:
            print("Skipped " + str(exit.door.name) + " " + str(direction) + " " + str(found_exits_dir.get(direction)))


    assert (num_exits_dir.get(Direction.West, 0) == len(found_exits_dir.get(Direction.West, [])))
    assert (num_exits_dir.get(Direction.East, 0) == len(found_exits_dir.get(Direction.East, [])))

    found_entrances_dir = {}

    for entrance in region.entrances:
        if is_valid_map_exit(entrance):
            if entrance.parent_region != region:
                direction = switch_dir_safe(entrance.door.direction)
                if direction:
                    found_entrances_dir.setdefault(direction, []).append(entrance.parent_region)
                    exits_for_dir[direction] = entrance
    dirs = [Direction.West, Direction.East]

    def ok(d):
        if len(found_exits_dir.get(d, [])) > 1:
            return False
        if len(found_entrances_dir.get(d, [])) > 1:
            return False

        total = len(found_exits_dir.get(d, [])) + len(found_entrances_dir.get(d, []))
        if total == 0:
            return False
        if total == 1:
            return True
        if total == 2:
            return found_exits_dir[d][0] == found_entrances_dir[d][0]

    r = {d:(found_exits_dir.get(d) or found_entrances_dir.get(d))[0] for d in dirs if ok(d)}

    return r, {d:exits_for_dir[d] for d in r}

logical_regions = set()

LOGICAL_INTERIOR_DOORS = True
def generate_logical_regions():
    #assert(not logical_regions)
    global logical_regions

    for connection in logical_connections+(interior_doors if LOGICAL_INTERIOR_DOORS else []):
        logical_regions.add(connection[0])
        logical_regions.add(connection[1])

    # Fixup GT warp maze D:
    for connection in dungeon_warps:
        if 'GT Warp Maze' in connection[0]:
            logical_regions.add(connection[0])
            logical_regions.add(connection[1])

    # TODO: convert lists into logical name

def get_region(exit):
    return exit.connected_region

from copy import copy

def merge_regions(a, b):
    # don't merge regions in the REAL world
    assert(a.world is None)
    assert(b.world is None)
    
    for exit in b.exits:
        other_region = exit.connected_region
        if other_region != a:
            # find all the exits and replace references
            # probably could just loop over the entrances instead...
            # ...would require validation and setting up the entrances    
            
            for other_exit in other_region.exits:
                if other_exit.connected_region == b:
                    other_exit.connected_region = a
        a.exits.append(exit)

    a.exits = [exit for exit in a.exits if exit.connected_region != b]
    a.exits = [exit for exit in a.exits if (exit.connected_region != a) or (exit.name not in logical_regions)]
    # clear the exits so we don't try to use them
    b.exits = []

                    

# TODO: all of this is leaving a bunch of properties pointing to the real world. TAKE CARE.
# doing this needs a LOT of memoization
def copy_exit(exit, region):
    out = copy(exit)
    out.parent_region = region
    #out.door = copy(exit.door)
    return out

def generate_shadow_region(region):
    shadow_region = Region(region.name, region.type, 'this is a bug - you are in the shadow realm', region.player)
    shadow_region.exits = [copy_exit(exit, shadow_region) for exit in region.exits if is_valid_map_exit(exit)]

    return shadow_region

def regenerate_entrances_from_exits(regions):
    for region in regions:
        region.entrances = []

    for region in regions:
        for exit in region.exits:
            exit.connected_region.entrances.append(exit)

def generate_shadow_dungeon(start_regions):
    reg_queue = deque(start_regions)
    visited = set(start_regions)

    shadow_dungeon = []
    shadow_start_regions = set()

    region_to_shadow_region = {None: None}

    # Walk the dungeon graph
    while len(reg_queue) > 0:
        region = reg_queue.pop()
        
        # Make a copy of the region
        shadow_region = generate_shadow_region(region)
        shadow_dungeon.append(shadow_region)
        region_to_shadow_region[region] = shadow_region

        if region in start_regions:
            shadow_start_regions.add(shadow_region)

        # walk all exits that don't go outside
        for exit in region.exits:
            if not is_valid_map_exit(exit):
                continue

            if exit.connected_region and exit.connected_region not in visited:
                visited.add(exit.connected_region)
                reg_queue.append(exit.connected_region)

    # fixup exit references - they were copied but still refer to the real dungeon
    for shadow_region in shadow_dungeon:
        for exit in shadow_region.exits:
            exit.connected_region = region_to_shadow_region[exit.connected_region]

    regenerate_entrances_from_exits(shadow_dungeon)

    return shadow_dungeon, shadow_start_regions
    # TODO: handle entrances



TABLE_START = "<<TABLE BORDER=\"0\" CELLBORDER=\"0\" CELLSPACING=\"0\" CELLPADDING=\"0\" >"
ROW_START = "<TR>"
ROW_END = "</TR>"
TABLE_END = "</TABLE>>"

def make_spacer_cell(width=0, height=0):
    return f'<TD FIXEDSIZE="TRUE" WIDTH="{width}" HEIGHT="{height}"></TD>'


def make_cell(label="", image='', port="", colspan=1, rowspan=1, height=0, width=0):
    # TODO: figure out how the fuck image sizing works
    if port:

        port = ' PORT="{}" '.format(port)
        print("set port to ")
        print(port)
    if image:
        image = f'<IMG SRC="{image}" />'
    return f'<TD FIXEDSIZE="TRUE" {port} COLSPAN="{rowspan}" ROWSPAN="{colspan}" HEIGHT="{height}" WIDTH="{width}">{image}{label}</TD>'

    

def get_room_image(region):
    return merged_room_data.get(region.name)

from collections import defaultdict

def add_offset(p, o):
    return (p[0] + o[0], p[1] + o[1])

quad_to_offset = [
    (0,0),
    (1,0),
    (0,1),
    (1,1),
]

OccupiedTileBottom = object()
OccupiedTileRight = object()
OccupiedTileBottomRight = object()

Occupied = {
    OccupiedTileRight: (1, 0),
    OccupiedTileBottom: (0, 1),
    OccupiedTileBottomRight: (1, 1),
}

# TODO: make coordinate object to not have to deal with 5s and 10s

class RoomGrid():
    def __init__(self):
        #self.extents = [[0,0],[0,0]]
        self.last_room = None
        self.grid = {}#defaultdict(str)
        self.last_supertile_height = Decimal(0)
    def _extents_for_grid(self,grid):
        if not grid:
            return ((DZero,DZero),(DZero,DZero))
        min_x = Decimal(1000)
        min_y = Decimal(1000)
        max_x = Decimal(-1000)
        max_y = Decimal(-1000)
        for x,y in grid:
            min_x = min(x, min_x)
            min_y = min(y, min_y)
            max_x = max(x, max_x)
            max_y = max(y, max_y)
        return ((min_x, min_y), (max_x, max_y))

    # this is a mess
    def add_region(self, region, y_offset=0):
        supertile = get_room_image(region)
        if not supertile:
            return
        
        # todo: grab the last supertile instead of simply caching height
        base_addr = (Decimal(0),Decimal(0))
        # always add to upper right for now


        for x in range(len(supertile[0])):
            if supertile[0][x]:
                y_offset += supertile[0][x][1] // 2
                break
        else:
            assert(False)


        if self.grid:
            extents = self._extents_for_grid(self.grid)
            base_addr = (extents[1][0] + DHalf, self.last_supertile_height+y_offset)

        #print(region.name)
        #print(supertile)
        #print(self.grid)
        #print(f'BA: {base_addr}')
        for y in range(len(supertile)):
            
            row = supertile[y]
            for x in range(len(row)):
            
                if row[x]:
                    # don't allow overwrite
                    addr = add_offset(base_addr, (x, y))

                    assert not self.grid.get(addr)

                    self.grid[addr] = row[x] + [region]
                    self.grid[add_offset(addr,(DHalf,0))] = OccupiedTileRight
                    self.grid[add_offset(addr,(0,DHalf))] = OccupiedTileBottom
                    self.grid[add_offset(addr,(DHalf,DHalf))] = OccupiedTileBottomRight
        
        for x in range(len(supertile[0])):
            if supertile[0][x]:
                if supertile[0][x][1] // 2 == 1:
                    self.last_supertile_height = base_addr[1] - 1
                    break
                else:
                    self.last_supertile_height = base_addr[1]
                    break
        else:
            assert(False)



def supertile_to_grid(supertile):
    return supertile


def construct_geometry_for_group(group):
    return room_group_to_grid[group[0].name]
    # this is sort of overdone
    RG = RoomGrid()

    for region in group:
        RG.add_region(region)

    return RG

def make_cell_debug(l):
    if False:
        return make_cell(label=l)
    else:
        return make_cell()

def get_door_str_for_quad_and_dir(supertile, quad, i):
    Top = 0
    Left = 0
    Mid = 1
    Bot = 2
    Right = 2


    # look, there's a way to do this mathematically but i cba
    lookup = {
        (0, 2): (Direction.North, Left),
        (0, 3): (Direction.North, Left),
        (0, 5): (Direction.North, Mid),
        (1, 0): (Direction.North, Mid),
        (1, 2): (Direction.North, Right),
        (1, 3): (Direction.North, Right),

        (0, 8): (Direction.West, Top),
        (0, 10): (Direction.West, Top),
        (0, 14): (Direction.West, Mid),
        (2, 0): (Direction.West, Mid),
        (2, 8): (Direction.West, Bot),
        (2, 10): (Direction.West, Bot),

        (2, 16): (Direction.South, Left),
        (2, 17): (Direction.South, Left),
        (2, 19): (Direction.South, Mid),
        (3, 14): (Direction.South, Mid),
        (3, 16): (Direction.South, Right),
        (3, 17): (Direction.South, Right),

        (1, 9): (Direction.East, Top),
        (1, 11): (Direction.East, Top),
        (1, 19): (Direction.East, Mid),
        (3, 5): (Direction.East, Mid),
        (3, 9): (Direction.East, Bot),
        (3, 11): (Direction.East, Bot),
    }

    foobar = lookup.get((quad, i))
    if not foobar:
        return f''

    dir_str = str(foobar[0]).replace('Direction.', '')

    return f'{supertile}_{dir_str}_{foobar[1]}'
    
def make_table_for_group(graph, group):
    room_grid = construct_geometry_for_group(group)

    empty_cell = make_cell()

    # TODO: fix this shit
    # each tile needs to have an nsew
    # so each row needs to be repeated
    s = TABLE_START

    extents = room_grid._extents_for_grid(room_grid.grid)
    s += ROW_START + empty_cell
    for x in drange(extents[0][0], extents[1][0] + DHalf, DHalf):
        s += empty_cell
        s += make_spacer_cell(width=128)
        s += empty_cell
    s += ROW_END

    # for each row
    for y in drange(extents[0][1], extents[1][1] + DHalf, DHalf):
        #always lead with empty cell so that the row isnt empty
        top_row = ROW_START + make_spacer_cell()
        inner_row = ROW_START + make_spacer_cell(height=128)
        bottom_row = ROW_START + make_spacer_cell()
        
        #s += make_cell(port=group[0].name+'_w') 

        # for each tile within row
        for x in drange(extents[0][0], extents[1][0] + DHalf, DHalf):
            tile = room_grid.grid.get((x, y))
            if type(tile) != list and tile in Occupied:
                offset = Occupied[tile]
                # TODO: the occupied can probably just contain the tile...

                real_tile = room_grid.grid.get((x - DHalf * offset[0], y - DHalf*offset[1]))
                supertile_id = real_tile[0]
                quad_id = real_tile[1]

                if tile == OccupiedTileRight:
                    #top_row += empty_cell * 3
                    top_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 3)) \
                               + make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 4)) \
                               + make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 5))
                    inner_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 7))
                    bottom_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 9))
                elif tile == OccupiedTileBottom:
                    top_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 10))
                    inner_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 12))
                    bottom_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 14)) \
                                  + make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 15)) \
                                  + make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 16)) 
                elif tile == OccupiedTileBottomRight:
                    top_row +=  make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 11))
                    inner_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 13))
                    bottom_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 17)) \
                                  + make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 18)) \
                                  + make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 19)) 
                continue
            if not tile:
                top_row += make_cell_debug('E') + make_cell_debug('E') + make_cell_debug('E')
                inner_row += make_cell_debug('E') + make_cell(image='room_images/empty-tile.png', width=128, height=128) + make_cell_debug('E')
                #inner_row += make_cell_debug('E') + make_cell(label='e') + make_cell_debug('E')
                #inner_row += make_cell_debug('E') + make_cell_debug('E') + make_cell_debug('E')
                bottom_row += make_cell_debug('E') + make_cell_debug('E') + make_cell_debug('E')
                continue
            image = f'room_images/{tile[0]}-{tile[1]}.png'
            supertile_id = tile[0]
            quad_id = tile[1]
            top_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 0)) \
                       + make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 1)) \
                       + make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 2))
            inner_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 6)) \
                      + make_cell(label='', port=str(supertile_id) + '_' + str(quad_id), image=image, colspan=4, rowspan=4, width=256, height=256)
            bottom_row += make_cell(port=get_door_str_for_quad_and_dir(supertile_id, quad_id, 8))

        s += top_row + ROW_END
        s += inner_row + ROW_END
        s += bottom_row + ROW_END
    
    s += TABLE_END
    
    graph.node(group[0].name,label=s, shape='plain')
    

def add_region_group(graph, group):
    #for region in group:
    #    make_table_for_group(graph, [region])
    make_table_for_group(graph, group)

# uuuugh globals. TODO: wrap html generation into class to allow passing context
merged_room_data = {}

room_group_to_grid = {}

def supertile_for_room(room):
    for row in room:
        for tile in row:
            if tile:
                return tile[0]
def map(world):
    global merged_room_data

    player = 1

    queue = deque(world.dungeon_layouts[player].values())

    # TODO: pass player here and reset

    graph = Digraph(comment='Maps',  graph_attr={'rankdir': 'BT'}, node_attr={'shape': 'box'})
    graph.attr(nodesep='2', ranksep='2', pack='8')

    generate_logical_regions()

    while len(queue) > 0:
        builder = queue.popleft()
        done = set()

        start_regions = set(convert_regions(builder.layout_starts, world, player))  # todo: set all_entrances for basic

        shadow_dungeon, start_regions = generate_shadow_dungeon(start_regions)

        dead_regions = set()

        def get_room_data(region):
            if region in merged_room_data:
                return merged_room_data[region]
            return 

        

        def fixup_exit(region, merged_region):
            # hackery because I didn't copy entrances TODO fix this

            for region2 in shadow_dungeon:
                for exit in region2.exits:
                    #assert(exit.connected_region not in dead_regions)
                    if exit.connected_region == merged_region:
                        exit.connected_region = region

        merged_room_data = copy(region_to_rooms)
        for name in merged_room_data:
            if not merged_room_data[name]:
                merged_room_data[name] = [ [ [0,0] ] ]

        supertile_to_region = {}
        for region in shadow_dungeon:
            assert(region.name in merged_room_data)
            room = merged_room_data[region.name]
            if room:
                supertile_to_region.setdefault(supertile_for_room(room), []).append((region, room))

        def overlapping_rooms(a, b):
            quad_a = []
            for row in a:
                for p in row:
                    if not p:
                        continue
                    i, q = p
                    quad_a.append(q)

            quad_b = []
            for row in b:
                for p in row:
                    if not p:
                        continue
                    i, q = p
                    quad_b.append(q)
            for q in quad_a:
                if q in quad_b:
                    return True

            return False

        def merge_rooms(a, b):
            quads = set()
            for row in a:
                for p in row:
                    if not p:
                        continue
                    i, q = p
                    quads.add(q)

            
            for row in b:
                for p in row:
                    if not p:
                        continue
                    i, q = p
                    quads.add(q)
            
            return make_room(supertile_for_room(a), list(quads))

        MERGE_BY_ROOM_DATA = True
        if MERGE_BY_ROOM_DATA:
            for supertile_key in supertile_to_region:
                if supertile_key == 0:
                    continue
                supertile = supertile_to_region[supertile_key]

                while True:
                    merged_some_rooms = False
                    for region, room in supertile:

                        merged_some_rooms = False
                        for other_region, other_room in supertile:
                            if region == other_region:
                                continue

                            # TODO: check for logical connection + interior door here
                            should_merge = overlapping_rooms(room, other_room)

                            if not should_merge:
                                for exit in region.exits:
                                    if exit.name in logical_regions:
                                        if exit.connected_region == other_region:
                                            should_merge = True


                            if should_merge:
                                merge_regions(region, other_region)
                                dead_regions.add(other_region)
                                fixup_exit(region, other_region)
                                print(f'merging {region.name} + {other_region.name}')
                                print(f'merging {room} + {other_room}')
                                new_room = merge_rooms(room, other_room)
                                print(new_room)
                                merged_room_data[region.name] = new_room
                                supertile = [p for p in supertile if p[0] != other_region and p[0] != region] + [(region, new_room)]
                                merged_some_rooms = True
                                break
                            else:
                                print(f'not merging {region.name} + {other_region.name}')
                                print(f'not merging {room} + {other_room}')

                        if merged_some_rooms:
                            break
                    if not merged_some_rooms:
                        break

        #while True:
        #    did_logical_merge
        # uuuuugh
        regenerate_entrances_from_exits(shadow_dungeon)


        MERGE_LOGICAL_REGIONS = True
        if MERGE_LOGICAL_REGIONS:
            for region in shadow_dungeon:
                if region in dead_regions:
                    continue
                while True:
                    for exit in region.exits:
                        if exit.name in logical_regions:
                            if exit.connected_region != region:
                                print(f"Merge {region.name} <- {exit.connected_region.name}")
                                merge_regions(region, exit.connected_region)
                                dead_regions.add(exit.connected_region)
                                fixup_exit(region, exit.connected_region)
                                
                                # restart the search, we got more exits
                                break
                    else:
                        # we didn't hit any logical reasons, now we can stop
                        break

        shadow_dungeon = [region for region in shadow_dungeon if region not in dead_regions]


        # TODO  outputorder=nodesfirst
        future_connections = {}



        with graph.subgraph(name='cluster_'+str(builder)) as dungeon_subgraph:

            # todo: just rewrite all this crap
            horiz_regions = []
            region_to_horiz_region = {}

            walked_regions = set()

            def new_horiz_region(region):
                horiz_regions.append([region])
                region_to_horiz_region[region] = horiz_regions[-1]
                rg = RoomGrid()
                rg.add_region(region)
                room_group_to_grid[horiz_regions[-1][0].name] = rg

            # Once we are more knowledgable about door locations and dungeon shapes we can use a fitting algo to allow for N/S stuff too
            # this whole thing is just all fucked, it needs a rewrite
            def process_region(region, cur_list=[]):
                if region in walked_regions:
                    return cur_list
                print("walking to " + region.name)
                walked_regions.add(region)

                valid_single_dirs = get_valid_single_dirs(region)
                valid_single_exits = get_valid_single_exits(region)

                if Direction.West in valid_single_dirs and valid_single_dirs[Direction.West] not in cur_list:
                    west_region = valid_single_dirs[Direction.West]
                    
                    cur_list = process_region(west_region, cur_list + [region])

                    valid_single_dirs_for_west = get_valid_single_dirs(west_region)
      

                    if valid_single_dirs_for_west.get(Direction.East) == region:
                        # TODO: this can fail...how?!
                        print("link " + region.name + " is east of " + west_region.name) 
                        h_region = region_to_horiz_region[west_region]

                        h_region.append(region)
                        region_to_horiz_region[region] = h_region



                        exit = valid_single_exits[Direction.West]
                        
                        assert(exit.door.doorIndex < 3)
                        assert(exit.door.dest.doorIndex < 3)
                        assert(exit.door.doorIndex >= 0)
                        assert(exit.door.dest.doorIndex >= 0)
                        offset = (exit.door.doorIndex) - (exit.door.dest.doorIndex)
                        #print(f"With offset of {offset * DHalf}")
                        room_group_to_grid[h_region[0].name].add_region(region, offset * DHalf)
                    else:
                        foobar = valid_single_dirs_for_west.get(Direction.East)
                        if foobar:
                            print("Pointed to " + foobar.name)
                        else:
                            print("Pointed to none")

                        # Our valid west region has a oneway to somewhere else, make a new region
                        new_horiz_region(region)    
                else:
                    # we are by definition the westmost region, start a new horiz region
                    new_horiz_region(region)

                # attempt to walk east...this doesn't work well
                # really we need to split exit processing and combining ffs

                if Direction.East in valid_single_dirs and valid_single_dirs[Direction.East] not in cur_list:
                    
                    
                    process_region(valid_single_dirs[Direction.East], cur_list)

                for exit in region.exits:
                    if not is_valid_map_exit(exit):
                        continue
                    door_a = exit.door
                    
                    connect = get_region(exit)
               
                    door_b = door_a.dest
                    assert(door_b)
                    if door_a not in done:
                        done.add(door_a)
                        # TODO: this is really dumb - we should just check if we are walking through a link that's in our horiz region :(
                        if (door_a.direction == Direction.West or door_a.direction == Direction.East) and door_a.direction in valid_single_dirs:

                            if get_valid_single_dirs(valid_single_dirs[door_a.direction]).get(opposite_ew_dir(door_a.direction), None) == region:
                                pass
                            elif door_b not in done:
                                future_connections.setdefault(region, []).append((region, connect, door_a, door_b))
                                pass
                        else:
                            if door_b not in done:
                                #generate_connection(dungeon_subgraph, region, connect, door_a, door_b)
                                future_connections.setdefault(region, []).append((region, connect, door_a, door_b))

                return cur_list

            for region in shadow_dungeon:
                process_region(region)

            for horiz_region in horiz_regions:
                add_region_group(dungeon_subgraph, horiz_region)

            for horiz_region in horiz_regions:
                for region in horiz_region:
                    for c in future_connections.get(region, []):
                        generate_connection(region_to_horiz_region, dungeon_subgraph, c[0], c[1], c[2], c[3])
                        
    graph.render('test-output/map.gv', view=True) 
    
