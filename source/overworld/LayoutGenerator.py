import logging
from DungeonGenerator import GenerationException
import RaceRandom as random
import random as _random
from typing import List, Dict, Optional, Set, Tuple
from BaseClasses import OWEdge, World, Direction, Terrain
from OverworldShuffle import connect_two_way, get_separate_ow_areas, validate_layout

ENABLE_KEEP_SIMILAR_SPECIAL_HANDLING = False
DRAW_IMAGE = False

large_screen_ids = [0x00, 0x03, 0x05, 0x18, 0x1B, 0x1E, 0x30, 0x35] + [0x40, 0x43, 0x45, 0x58, 0x5B, 0x5E, 0x70, 0x75]

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class Screen:
    """
    Represents a game map screen.
    """
    __slots__ = ('id', 'big', 'dark_world', 'parallel',
                 'edges', 'mixed_state')

    def __init__(
        self,
        id: int,
        big: bool = False,
        dark_world: bool = False,
        parallel: Optional['Screen'] = None,
        edges: Optional[Dict[str, OWEdge]] = None,
        mixed_state: str = "normal"
    ):
        self.id = id
        self.big = big
        self.dark_world = dark_world
        self.parallel = parallel
        self.edges = edges if edges is not None else {}
        self.mixed_state = mixed_state # "normal" or "swapped"

class WorldPiece:
    """
    Represents a piece within a world containing screens to be placed on the grid.
    """
    __slots__ = ('screens', 'grid', 'width', 'height', 'north_edges', 'south_edges',
                 'west_edges', 'east_edges', 'north_edges_water', 'south_edges_water',
                 'west_edges_water', 'east_edges_water')

    def __init__(
        self,
        screens: Optional[List[List[Optional[Screen]]]] = None,
        grid: Optional[List[List[int]]] = None,
        width: int = 0,
        height: int = 0,
        north_edges: Optional[List[List[List[OWEdge]]]] = None,
        south_edges: Optional[List[List[List[OWEdge]]]] = None,
        west_edges: Optional[List[List[List[OWEdge]]]] = None,
        east_edges: Optional[List[List[List[OWEdge]]]] = None,
        north_edges_water: Optional[List[List[List[OWEdge]]]] = None,
        south_edges_water: Optional[List[List[List[OWEdge]]]] = None,
        west_edges_water: Optional[List[List[List[OWEdge]]]] = None,
        east_edges_water: Optional[List[List[List[OWEdge]]]] = None
    ):
        self.screens = screens if screens is not None else []
        self.grid = grid if grid is not None else []
        self.width = width
        self.height = height
        self.north_edges = north_edges if north_edges is not None else []
        self.south_edges = south_edges if south_edges is not None else []
        self.west_edges = west_edges if west_edges is not None else []
        self.east_edges = east_edges if east_edges is not None else []
        self.north_edges_water = north_edges_water if north_edges_water is not None else []
        self.south_edges_water = south_edges_water if south_edges_water is not None else []
        self.west_edges_water = west_edges_water if west_edges_water is not None else []
        self.east_edges_water = east_edges_water if east_edges_water is not None else []

class Piece:
    """
    Represents a piece consisting of a main and optionally a parallel world piece.
    """
    __slots__ = ('main', 'parallel', 'world', 'width', 'height', 'restriction',
                 'crossed_groups', 'delay', 'order', 'edge_sides', 'max_edges_per_side')

    def __init__(
        self,
        main: WorldPiece,
        parallel: Optional[WorldPiece] = None,
        world: int = 0,
        width: int = 0,
        height: int = 0,
        restriction: Optional[List[int]] = None,
        crossed_groups: Optional[List[List[int]]] = None,
        delay: int = 0,
        order: float = 0.0,
        edge_sides: int = 0,
        max_edges_per_side: int = 0
    ):
        self.main = main
        self.parallel = parallel
        self.world = world # 0 or 1
        self.width = width
        self.height = height
        self.restriction = restriction
        self.crossed_groups = crossed_groups if crossed_groups is not None else []
        self.delay = delay
        self.order = order
        self.edge_sides = edge_sides
        self.max_edges_per_side = max_edges_per_side

class GridInfo:
    """
    Container for grid layout information during placement runs.
    Stores screen IDs and edge information for both Light and Dark worlds.
    """
    __slots__ = (
        'grid', 'north_edges_grid', 'south_edges_grid', 'west_edges_grid', 'east_edges_grid',
        'north_edges_water_grid', 'south_edges_water_grid', 'west_edges_water_grid', 'east_edges_water_grid',
        'crossed_groups', 'edge_connection_seed'
    )

    def __init__(
        self,
        grid: List[List[List[int]]],
        north_edges_grid: List[List[List[List[OWEdge]]]],
        south_edges_grid: List[List[List[List[OWEdge]]]],
        west_edges_grid: List[List[List[List[OWEdge]]]],
        east_edges_grid: List[List[List[List[OWEdge]]]],
        north_edges_water_grid: List[List[List[List[OWEdge]]]],
        south_edges_water_grid: List[List[List[List[OWEdge]]]],
        west_edges_water_grid: List[List[List[List[OWEdge]]]],
        east_edges_water_grid: List[List[List[List[OWEdge]]]],
        crossed_groups: List[List[int]],
        edge_connection_seed: float
    ):
        self.grid = grid
        self.north_edges_grid = north_edges_grid
        self.south_edges_grid = south_edges_grid
        self.west_edges_grid = west_edges_grid
        self.east_edges_grid = east_edges_grid
        self.north_edges_water_grid = north_edges_water_grid
        self.south_edges_water_grid = south_edges_water_grid
        self.west_edges_water_grid = west_edges_water_grid
        self.east_edges_water_grid = east_edges_water_grid
        self.crossed_groups = crossed_groups
        self.edge_connection_seed = edge_connection_seed

class LayoutGeneratorOptions:
    """
    Configuration options for layout generation.
    """
    __slots__ = ('horizontal_wrap', 'vertical_wrap', 'split_large_screens', 'distortion_chance', 'random_order',
                 'multi_choice', 'max_delay', 'first_ignore_bonus_points',
                 'penalty_full_edge_mismatch', 'penalty_partial_edge_mismatch', 'bonus_partial_edge_match',
                 'bonus_full_edge_match', 'bonus_crossed_group_match', 'bonus_fill_parallel',
                 'forced_non_crossed_edges', 'forced_crossed_edges', 'check_reachability',
                 'crossed_chance', 'crossed_limit',
                 'sort_by_edge_sides', 'sort_by_max_edges_per_side', 'sort_by_piece_size',
                 'min_runs', 'max_runs', 'target_runs_times_successes', 'score_mult_separate_areas',
                 'start_loc_min_distance', 'score_mult_start_loc_distance')

    def __init__(
        self,
        horizontal_wrap: bool = True,
        vertical_wrap: bool = True,
        split_large_screens = False,
        distortion_chance: float = 0.0,
        random_order: int = 0,
        multi_choice: int = 1,
        max_delay: int = 10,
        first_ignore_bonus_points: int = 0,
        penalty_full_edge_mismatch: float = 1,
        penalty_partial_edge_mismatch: float = 0,
        bonus_partial_edge_match: float = 1,
        bonus_full_edge_match: float = 1,
        bonus_crossed_group_match: float = 1,
        bonus_fill_parallel: float = 0,
        forced_non_crossed_edges: Set[str] = [],
        forced_crossed_edges: Set[str] = [],
        crossed_chance: float = 0.5,
        crossed_limit: int = -1,
        check_reachability: bool = True,
        sort_by_edge_sides: bool = False,
        sort_by_max_edges_per_side: bool = False,
        sort_by_piece_size: bool = False,
        min_runs: int = 100,
        max_runs: int = 10000,
        target_runs_times_successes: int = 5000,
        score_mult_separate_areas: float = 4,
        start_loc_min_distance: int = 4,
        score_mult_start_loc_distance: float = 3
    ):
        self.horizontal_wrap = horizontal_wrap
        self.vertical_wrap = vertical_wrap
        self.split_large_screens = split_large_screens
        self.distortion_chance = distortion_chance
        self.random_order = random_order
        self.multi_choice = multi_choice
        self.max_delay = max_delay
        self.first_ignore_bonus_points = first_ignore_bonus_points
        self.penalty_full_edge_mismatch = penalty_full_edge_mismatch
        self.penalty_partial_edge_mismatch = penalty_partial_edge_mismatch
        self.bonus_partial_edge_match = bonus_partial_edge_match
        self.bonus_full_edge_match = bonus_full_edge_match
        self.bonus_crossed_group_match = bonus_crossed_group_match
        self.bonus_fill_parallel = bonus_fill_parallel
        self.forced_non_crossed_edges = forced_non_crossed_edges
        self.forced_crossed_edges = forced_crossed_edges
        self.check_reachability = check_reachability
        self.crossed_chance = crossed_chance
        self.crossed_limit = crossed_limit
        self.sort_by_edge_sides = sort_by_edge_sides
        self.sort_by_max_edges_per_side = sort_by_max_edges_per_side
        self.sort_by_piece_size = sort_by_piece_size
        self.min_runs = min_runs
        self.max_runs = max_runs
        self.target_runs_times_successes = target_runs_times_successes
        self.score_mult_separate_areas = score_mult_separate_areas
        self.start_loc_min_distance = start_loc_min_distance
        self.score_mult_start_loc_distance = score_mult_start_loc_distance

class LayoutGeneratorResult:
    """
    Result object for the layout generation.
    """
    __slots__ = ('grid_info', 'score', 'worst_score', 'average_score', 'successes', 'failures')

    def __init__(
        self,
        grid_info: Optional[GridInfo] = None,
        score: int = 0,
        worst_score: int = 0,
        average_score: float = 0.0,
        successes: int = 0,
        failures: int = 0
    ):
        self.grid_info = grid_info
        self.score = score
        self.worst_score = worst_score
        self.average_score = average_score
        self.successes = successes
        self.failures = failures

class PiecePlacementResult:
    """
    Result object for the layout generator placement operations.
    """
    __slots__ = ('success', 'piece', 'score_major', 'score_minor')

    def __init__(
        self,
        success: bool = False,
        piece: Optional[Piece] = None,
        score_major: float = 0,
        score_minor: float = 0
    ):
        self.success = success
        self.piece = piece
        self.score_major = score_major
        self.score_minor = score_minor

# ============================================================================
# GRID INITIALIZATION
# ============================================================================

def create_empty_grid_info(edge_connection_seed: float) -> GridInfo:
    return GridInfo(
        grid=[[[-1] * 8 for _ in range(8)] for _ in range(2)],
        north_edges_grid=[[[[] for _ in range(8)] for _ in range(8)] for _ in range(2)],
        south_edges_grid=[[[[] for _ in range(8)] for _ in range(8)] for _ in range(2)],
        west_edges_grid=[[[[] for _ in range(8)] for _ in range(8)] for _ in range(2)],
        east_edges_grid=[[[[] for _ in range(8)] for _ in range(8)] for _ in range(2)],
        north_edges_water_grid=[[[[] for _ in range(8)] for _ in range(8)] for _ in range(2)],
        south_edges_water_grid=[[[[] for _ in range(8)] for _ in range(8)] for _ in range(2)],
        west_edges_water_grid=[[[[] for _ in range(8)] for _ in range(8)] for _ in range(2)],
        east_edges_water_grid=[[[[] for _ in range(8)] for _ in range(8)] for _ in range(2)],
        crossed_groups=[[-1] * 8 for _ in range(8)],
        edge_connection_seed=edge_connection_seed
    )

def copy_grid_info(source: GridInfo, edge_connection_seed: float) -> GridInfo:
    """
    Create a deep copy of a GridInfo object with a new edge_connection_seed.
    Only copies the grid data structures, not the OWEdge references (which are shared).
    """
    return GridInfo(
        grid=[[row[:] for row in world_grid] for world_grid in source.grid],
        north_edges_grid=[[[cell[:] for cell in row] for row in world_grid] for world_grid in source.north_edges_grid],
        south_edges_grid=[[[cell[:] for cell in row] for row in world_grid] for world_grid in source.south_edges_grid],
        west_edges_grid=[[[cell[:] for cell in row] for row in world_grid] for world_grid in source.west_edges_grid],
        east_edges_grid=[[[cell[:] for cell in row] for row in world_grid] for world_grid in source.east_edges_grid],
        north_edges_water_grid=[[[cell[:] for cell in row] for row in world_grid] for world_grid in source.north_edges_water_grid],
        south_edges_water_grid=[[[cell[:] for cell in row] for row in world_grid] for world_grid in source.south_edges_water_grid],
        west_edges_water_grid=[[[cell[:] for cell in row] for row in world_grid] for world_grid in source.west_edges_water_grid],
        east_edges_water_grid=[[[cell[:] for cell in row] for row in world_grid] for world_grid in source.east_edges_water_grid],
        crossed_groups=[row[:] for row in source.crossed_groups],
        edge_connection_seed=edge_connection_seed
    )

def initialize_screens(world: World, player: int) -> Dict[int, Screen]:
    overworld_screens: Dict[int, Screen] = {}
    screen_edges_map = group_owedges_by_screens(world, player)

    for screen_id in range(0x80):
        if screen_id - 0x01 not in large_screen_ids and screen_id - 0x08 not in large_screen_ids and screen_id - 0x09 not in large_screen_ids:
            is_vanilla_dark = screen_id >= 0x40
            is_big = screen_id in large_screen_ids
            is_flipped = world.owMixed[player] and screen_id in world.owswaps[player][0]

            screen = Screen(
                id=screen_id,
                big=is_big,
                dark_world=not is_vanilla_dark if is_flipped else is_vanilla_dark,
                mixed_state="swapped" if is_flipped else "normal"
            )

            if screen_id in screen_edges_map:
                for edge in screen_edges_map[screen_id]:
                    screen.edges[edge.name] = edge

            overworld_screens[screen_id] = screen

    for light_id in range(0x40):
        dark_id = light_id + 0x40
        if light_id in overworld_screens:
            overworld_screens[light_id].parallel = overworld_screens[dark_id]
            overworld_screens[dark_id].parallel = overworld_screens[light_id]

    return overworld_screens

def group_owedges_by_screens(world: World, player: int) -> Dict[int, List[OWEdge]]:
    screen_edges: Dict[int, List[OWEdge]] = {}
    edges: List[OWEdge] = world.owedges

    for edge in edges:
        # Skip edges that lead to/from special screens
        if edge.player == player and not edge.specialEntrance and not edge.specialExit:
            owIndex = edge.owIndex
            if owIndex not in screen_edges:
                screen_edges[owIndex] = []
            screen_edges[owIndex].append(edge)

    return screen_edges

def initialize_large_screen_data(overworld_screens: Dict[int, Screen]) -> Tuple[Dict[int, Dict], Dict[int, Dict], Dict[int, Dict]]:
    i: Dict[int, Dict] = {}
    il: Dict[int, Dict] = {}
    iw: Dict[int, Dict] = {}
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x00, [], [], [], [], ["Lost Woods EN"], [], ["Lost Woods SW", "Lost Woods SC"], ["Lost Woods SE"])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x40, [], [], [], [], ["Skull Woods EN"], [], ["Skull Woods SW", "Skull Woods SC"], ["Skull Woods SE"])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x03, [], [], [], [], ["West Death Mountain EN"], ["West Death Mountain ES"], [], [])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x43, [], [], [], [], ["West Dark Death Mountain EN"], ["West Dark Death Mountain ES"], [], [])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x05, [], [], ["East Death Mountain WN"], ["East Death Mountain WS"], ["East Death Mountain EN"], [], [], [])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x45, [], [], ["East Dark Death Mountain WN"], ["East Dark Death Mountain WS"], ["East Dark Death Mountain EN"], [], [], [])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x18, ["Kakariko NW", "Kakariko NC"], ["Kakariko NE"], [], [], [], ["Kakariko ES"], [], ["Kakariko SE"])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x58, ["Village of Outcasts NW", "Village of Outcasts NC"], ["Village of Outcasts NE"], [], [], [], ["Village of Outcasts ES"], [], ["Village of Outcasts SE"])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x1B, [], [], ["Hyrule Castle WN"], [], [], ["Hyrule Castle ES"], ["Hyrule Castle SW"], ["Hyrule Castle SE"])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x5B, [], [], [], [], [], ["Pyramid ES"], ["Pyramid SW"], ["Pyramid SE"])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x1E, [], [], [], [], [], [], ["Eastern Palace SW"], ["Eastern Palace SE"])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x5E, [], [], [], [], [], [], ["Palace of Darkness SW"], ["Palace of Darkness SE"])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x30, [], [], [], [], [], ["Desert EC", "Desert ES"], [], [])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x70, [], [], [], [], [], [], [], [])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x35, ["Lake Hylia NW"], ["Lake Hylia NC", "Lake Hylia NE"], [], ["Lake Hylia WS"], [], ["Lake Hylia EC", "Lake Hylia ES"], [], [])
    define_large_screen_quadrants(overworld_screens, i, il, iw, 0x75, ["Ice Lake NW"], ["Ice Lake NC", "Ice Lake NE"], [], ["Ice Lake WS"], [], ["Ice Lake EC", "Ice Lake ES"], [], [])
    return (i, il, iw)

def define_large_screen_quadrants(
    overworld_screens: Dict[int, Screen],
    large_screen_quadrant_info: Dict[int, Dict],
    large_screen_quadrant_info_land: Dict[int, Dict],
    large_screen_quadrant_info_water: Dict[int, Dict],
    screen_id: int,
    north1: List[str], north2: List[str],
    west1: List[str], west2: List[str],
    east1: List[str], east2: List[str],
    south1: List[str], south2: List[str]
) -> None:
    """
    Define edge info for large screens
    Maps edge names to quadrants (NW, NE, SW, SE)

    Edge names are the actual edge names from OWEdges.py like "Lost Woods SW", "Kakariko NW", etc.
    """
    edges = overworld_screens[screen_id].edges
    info = {
        "NW": {Direction.North: [], Direction.West: [], Direction.East: [], Direction.South: []},
        "NE": {Direction.North: [], Direction.West: [], Direction.East: [], Direction.South: []},
        "SW": {Direction.North: [], Direction.West: [], Direction.East: [], Direction.South: []},
        "SE": {Direction.North: [], Direction.West: [], Direction.East: [], Direction.South: []}
    }
    info["NW"][Direction.North] = [edges[name] for name in north1]
    info["NE"][Direction.North] = [edges[name] for name in north2]
    info["NW"][Direction.West] = [edges[name] for name in west1]
    info["SW"][Direction.West] = [edges[name] for name in west2]
    info["NE"][Direction.East] = [edges[name] for name in east1]
    info["SE"][Direction.East] = [edges[name] for name in east2]
    info["SW"][Direction.South] = [edges[name] for name in south1]
    info["SE"][Direction.South] = [edges[name] for name in south2]

    large_screen_quadrant_info[screen_id] = info

    large_screen_quadrant_info_land[screen_id] = {
        "NW": {}, "NE": {}, "SW": {}, "SE": {}
    }
    large_screen_quadrant_info_water[screen_id] = {
        "NW": {}, "NE": {}, "SW": {}, "SE": {}
    }

    for quadrant_name in ["NW", "NE", "SW", "SE"]:
        for direction in [Direction.North, Direction.West, Direction.East, Direction.South]:
            large_screen_quadrant_info_land[screen_id][quadrant_name][direction] = \
                [edge for edge in info[quadrant_name][direction] if edge.terrain != Terrain.Water]
            large_screen_quadrant_info_water[screen_id][quadrant_name][direction] = \
                [edge for edge in info[quadrant_name][direction] if edge.terrain == Terrain.Water]

# ============================================================================
# PIECE CREATION
# ============================================================================

def create_piece_list(world: World, player: int, options: LayoutGeneratorOptions, crossed_group_b: List[int], overworld_screens: Dict[int, Screen], large_screen_quadrant_info: Dict[int, Dict], large_screen_quadrant_info_land: Dict[int, Dict], large_screen_quadrant_info_water: Dict[int, Dict]) -> List[Piece]:
    piece_list: List[Piece] = []

    # Determine which screens to process
    all_screens = list(overworld_screens.values())
    if world.owParallel[player]:
        # In Parallel, only use light world screens
        # Each piece will automatically handle both worlds through parallel mechanism
        all_screens = [s for s in all_screens if not s.dark_world]

    # Phase 1: Create individual 1x1 pieces for all cells
    for screen in all_screens:
        if screen.big:
            # Create 4 pieces for large screen quadrants
            for offset in [0x00, 0x01, 0x08, 0x09]:
                piece = create_piece(world, player, [[screen.id + offset]], overworld_screens)
                piece_list.append(piece)
        else:
            piece = create_piece(world, player, [[screen.id]], overworld_screens)
            piece_list.append(piece)

    # Apply position restrictions from Customizer
    piece_list = apply_position_restrictions(world, player, piece_list, overworld_screens)

    # Phase 2: Apply options via merging

    # Merge large screens if not split
    if not options.split_large_screens:
        for large_id in large_screen_ids:
            if large_id in [s.id for s in all_screens if s.big]:
                piece_list = merge_pieces(piece_list, [[large_id, large_id + 0x01], [large_id + 0x08, large_id + 0x09]], world, player, overworld_screens)

    # Standard mode: merge castle area
    if world.mode[player] == 'standard':
        piece_list = merge_pieces(piece_list, [[0x23, 0x24], [0x2B, 0x2C]], world, player, overworld_screens)

    # Apply fixed arrangement restrictions from Customizer
    piece_list = apply_arrangement_restrictions(world, player, piece_list, overworld_screens)

    # Trim pieces by removing empty rows/columns on edges
    piece_list = [trim_piece(piece) for piece in piece_list]

    # Validate piece sizes and apply wrapping if needed
    piece_list = validate_and_wrap_pieces(piece_list, options, world, player, overworld_screens)

    # Phase 3: Add piece data
    for piece in piece_list:
        add_piece_data(world, player, piece, large_screen_quadrant_info, large_screen_quadrant_info_land, large_screen_quadrant_info_water)
        # Handle crossed groups
        if world.owCrossed[player] == 'polar' and world.owMixed[player]:
            piece.crossed_groups = [[] for _ in range(8)]
            for k in range(piece.height):
                for l in range(piece.width):
                    piece.crossed_groups[k].append(-1)
                    screen = piece.main.screens[k][l]
                    if screen:
                        piece.crossed_groups[k][l] = 1 if screen.mixed_state == "swapped" else 0
                    else:
                        if piece.parallel and piece.parallel.screens[k][l]:
                            piece.crossed_groups[k][l] = 1 if piece.parallel.screens[k][l].mixed_state == "swapped" else 0
        if world.owCrossed[player] == 'grouped':
            piece.crossed_groups = [[] for _ in range(8)]
            for k in range(piece.height):
                for l in range(piece.width):
                    piece.crossed_groups[k].append(-1)
                    screen = piece.main.screens[k][l]
                    if screen:
                        piece.crossed_groups[k][l] = 1 if screen.id in crossed_group_b else 0
                    else:
                        if piece.parallel and piece.parallel.screens[k][l]:
                            piece.crossed_groups[k][l] = 1 if piece.parallel.screens[k][l].id in crossed_group_b else 0

    return piece_list

def create_piece(world: World, player: int, grid: List[List[int]], overworld_screens: Dict[int, Screen]) -> Piece:
    """
    Create piece from grid of cell IDs
    Takes 2D array of cell IDs and creates main and parallel pieces
    """
    piece = Piece(
        main=WorldPiece(width=len(grid[0]), height=len(grid)),
        width=len(grid[0]),
        height=len(grid)
    )

    if world.owParallel[player]:
        piece.parallel = WorldPiece(width=len(grid[0]), height=len(grid))

    found_screens = set()

    for i in range(piece.height):
        new_row = []
        new_screen_row = []
        new_row_parallel = []
        new_screen_row_parallel = []
        piece.main.grid.append(new_row)
        piece.main.screens.append(new_screen_row)
        if world.owParallel[player]:
            piece.parallel.grid.append(new_row_parallel)
            piece.parallel.screens.append(new_screen_row_parallel)

        for j in range(piece.width):
            cell_id = grid[i][j]
            new_row.append(cell_id)
            screen = None if cell_id == -1 else overworld_screens.get(get_screen_id_from_cell(cell_id))
            if screen:
                found_screens.add(screen)
            new_screen_row.append(screen)
            if world.owParallel[player]:
                if screen:
                    new_row_parallel.append(cell_id - screen.id + screen.parallel.id)
                    new_screen_row_parallel.append(screen.parallel)
                else:
                    new_row_parallel.append(-1)
                    new_screen_row_parallel.append(None)

    worlds = set(s.dark_world for s in found_screens if s is not None)
    if len(worlds) != 1:
        raise GenerationException("Piece contains screens from both Light World and Dark World")
    piece.world = 1 if True in worlds else 0

    return piece

def apply_position_restrictions(world: World, player: int, piece_list: List[Piece], overworld_screens: Dict[int, Screen]) -> List[Piece]:
    """
    Apply position restrictions from Customizer to pieces at the end of phase 1.

    Position restrictions specify that certain cells can only be placed at certain positions.
    The Customizer format is:
        restricted_positions:
          - cells: [0x13, 0x2C]
            positions: [0x00, 0x07, 0x38, 0x3F]
            world: both # or 'light' or 'dark'

    Note: At the end of phase 1, all pieces are 1x1 (one piece per cell).

    The world bit (0x40) in user input is ignored. The actual cell ID is determined by:
    - The world where the restriction applies (light=0, dark=1)
    - The mixed_state of the screen containing that cell (swapped screens flip the world bit)
    """
    if not world.customizer:
        return piece_list

    grid_options = world.customizer.get_owgrid()
    if not grid_options or player not in grid_options:
        return piece_list

    grid_options = grid_options[player]
    restricted_positions = grid_options.get('restricted_positions', [])
    if not restricted_positions:
        return piece_list

    # Build a mapping from cell ID to piece for quick lookup
    cell_to_piece = {piece.main.grid[0][0]: piece for piece in piece_list}

    for restriction_idx, restriction in enumerate(restricted_positions):
        cells = restriction.get('cells', [])
        positions = restriction.get('positions', [])
        restriction_world = restriction.get('world', 'both')

        # Validate input
        if not cells:
            raise GenerationException(f"Invalid restriction in restricted_positions[{restriction_idx}]: No cells provided")
        for cell_id in cells:
            validate_cell_id(cell_id, f"restricted_positions[{restriction_idx}].cells")
        if not positions:
            raise GenerationException(f"Invalid restriction in restricted_positions[{restriction_idx}]: No positions provided")
        for pos in positions:
            validate_cell_id(pos, f"restricted_positions[{restriction_idx}].positions")
        validate_world_value(restriction_world, f"restricted_positions[{restriction_idx}]")

        position_set = set(positions)

        for user_cell_id in cells:
            # Ignore the world bit in user input
            base_cell_id = user_cell_id & 0xBF

            # Determine which worlds this restriction applies to
            worlds_to_check = []
            if restriction_world == 'light' or restriction_world == 'both':
                worlds_to_check.append(0) # Light World
            if restriction_world == 'dark' or restriction_world == 'both':
                worlds_to_check.append(1) # Dark World

            for target_world in worlds_to_check:
                # Determine the actual cell ID based on the target world and mixed state
                screen_id = get_screen_id_from_cell(base_cell_id)
                screen = overworld_screens.get(screen_id)
                is_swapped = screen.mixed_state == "swapped"

                # Calculate the actual cell ID:
                # - In Light World (target_world=0): use base_cell_id if normal, base_cell_id|0x40 if swapped
                # - In Dark World (target_world=1): use base_cell_id|0x40 if normal, base_cell_id if swapped
                if target_world == 0:
                    # Light World
                    actual_cell_id = (base_cell_id | 0x40) if is_swapped else base_cell_id
                else:
                    # Dark World
                    actual_cell_id = base_cell_id if is_swapped else (base_cell_id | 0x40)

                piece = cell_to_piece.get(actual_cell_id)

                # Apply the position restriction
                if piece.restriction is None:
                    piece.restriction = list(position_set)
                else:
                    # Intersect with existing restrictions
                    piece.restriction = [p for p in piece.restriction if p in position_set]

    return piece_list

def apply_arrangement_restrictions(world: World, player: int, piece_list: List[Piece], overworld_screens: Dict[int, Screen]) -> List[Piece]:
    """
    Apply fixed arrangement restrictions from Customizer to pieces at the end of phase 2.

    Fixed arrangements specify the relative positioning between multiple screens.
    The Customizer format is:
        fixed_arrangements:
          - arrangement:
              - 0x03 0x04 0x05 0x06 0x07
              - 0x0B 0x0C 0x0D 0x0E    .
            world: both # or 'light' or 'dark'

    The '.' character is a placeholder that allows any screen to be placed there.

    The world bit (0x40) in user input is ignored. The actual cell ID is determined by:
    - The world where the restriction applies (light=0, dark=1)
    - The mixed_state of the screen containing that cell (swapped screens flip the world bit)
    """
    if not world.customizer:
        return piece_list

    grid_options = world.customizer.get_owgrid()
    if not grid_options or player not in grid_options:
        return piece_list

    grid_options = grid_options[player]
    fixed_arrangements = grid_options.get('fixed_arrangements', [])
    if not fixed_arrangements:
        return piece_list

    for arrangement_idx, arrangement_config in enumerate(fixed_arrangements):
        arrangement_rows = arrangement_config.get('arrangement', [])
        arrangement_world = arrangement_config.get('world', 'both')

        # Validate world value
        validate_world_value(arrangement_world, f"fixed_arrangements[{arrangement_idx}]")

        if not arrangement_rows:
            raise GenerationException(f"Invalid arrangement in fixed_arrangements[{arrangement_idx}]: No arrangement provided")

        # Pre-validate the arrangement: check row lengths and entry validity
        expected_row_length = None
        for row_idx, row_str in enumerate(arrangement_rows):
            parts = str(row_str).split()
            if expected_row_length is None:
                expected_row_length = len(parts)
            elif len(parts) != expected_row_length:
                raise GenerationException(f"Invalid arrangement in fixed_arrangements[{arrangement_idx}]: row {row_idx} has {len(parts)} entries but expected {expected_row_length} (all rows must have the same number of entries)")

            # Validate each entry
            for part_idx, part in enumerate(parts):
                part = part.strip()
                if part == '.':
                    continue
                # Try to parse as cell ID
                try:
                    if part.startswith('0x') or part.startswith('0X'):
                        cell_id = int(part, 16)
                    else:
                        cell_id = int(part)
                    validate_cell_id(cell_id, f"fixed_arrangements[{arrangement_idx}].arrangement[{row_idx}][{part_idx}]")
                except ValueError:
                    raise GenerationException(f"Invalid entry '{part}' in fixed_arrangements[{arrangement_idx}].arrangement[{row_idx}][{part_idx}]: must be a cell ID (0x00-0x7F) or '.'")

        # Determine which worlds this arrangement applies to
        worlds_to_apply = []
        if arrangement_world == 'light' or arrangement_world == 'both':
            worlds_to_apply.append(0) # Light World
        if arrangement_world == 'dark' or arrangement_world == 'both':
            worlds_to_apply.append(1) # Dark World

        for target_world in worlds_to_apply:
            # Parse the arrangement into a 2D list of cell IDs, translating based on world and mixed state
            # Each row is a string like "0x03 0x04 0x05 0x06 0x07" or contains '.' for wildcards
            arrangement = []
            for row_str in arrangement_rows:
                row = []
                # Split by whitespace
                parts = str(row_str).split()
                for part in parts:
                    part = part.strip()
                    if part == '.':
                        row.append(-1) # -1 represents wildcard
                    else:
                        # Parse as hex or decimal (already validated above)
                        if part.startswith('0x') or part.startswith('0X'):
                            user_cell_id = int(part, 16)
                        else:
                            user_cell_id = int(part)

                        # Ignore the world bit in user input
                        base_cell_id = user_cell_id & 0xBF

                        # Get the screen that contains this cell
                        screen_id = get_screen_id_from_cell(base_cell_id)
                        screen = overworld_screens.get(screen_id)
                        is_swapped = screen.mixed_state == "swapped"

                        # Calculate the actual cell ID:
                        # - In Light World (target_world=0): use base_cell_id if normal, base_cell_id|0x40 if swapped
                        # - In Dark World (target_world=1): use base_cell_id|0x40 if normal, base_cell_id if swapped
                        if target_world == 0:
                            # Light World
                            actual_cell_id = (base_cell_id | 0x40) if is_swapped else base_cell_id
                        else:
                            # Dark World
                            actual_cell_id = base_cell_id if is_swapped else (base_cell_id | 0x40)

                        row.append(actual_cell_id)
                if row:
                    arrangement.append(row)

            # Merge the pieces according to the arrangement
            piece_list = merge_pieces(piece_list, arrangement, world, player, overworld_screens)

    return piece_list

def get_piece_cells(piece: Piece) -> Set[int]:
    """Get all cell IDs contained in a piece."""
    cells = set()
    for row in piece.main.grid:
        for cell in row:
            if cell != -1:
                cells.add(cell)
    return cells

def validate_cell_id(cell_id: int, context: str) -> None:
    if not isinstance(cell_id, int) or cell_id < 0x00 or cell_id > 0x7F:
        raise GenerationException(f"Invalid cell ID 0x{cell_id:02X} in {context}: must be in range 0x00-0x7F")

def validate_world_value(world_value: str, context: str) -> None:
    allowed_values = {'light', 'dark', 'both'}
    if world_value not in allowed_values:
        raise GenerationException(f"Invalid world value '{world_value}' in {context}: must be one of {allowed_values}")

def trim_piece(piece: Piece) -> Piece:
    """
    Trim a piece by removing any full rows or columns on the edges that only consist of -1.
    Adjusts position restrictions when present.
    """
    # Find the bounds of non-empty cells
    min_row, max_row = piece.height, -1
    min_col, max_col = piece.width, -1

    for i in range(piece.height):
        for j in range(piece.width):
            has_content = piece.main.grid[i][j] != -1
            if piece.parallel:
                has_content = has_content or piece.parallel.grid[i][j] != -1
            if has_content:
                min_row = min(min_row, i)
                max_row = max(max_row, i)
                min_col = min(min_col, j)
                max_col = max(max_col, j)

    if max_row < 0 or (min_row == 0 and max_row == piece.height - 1 and min_col == 0 and max_col == piece.width - 1):
        return piece

    new_height = max_row - min_row + 1
    new_width = max_col - min_col + 1
    piece.width = new_width
    piece.height = new_height

    # Trim piece
    piece.main.grid = [row[min_col:max_col + 1] for row in piece.main.grid[min_row:max_row + 1]]
    piece.main.screens = [row[min_col:max_col + 1] for row in piece.main.screens[min_row:max_row + 1]]
    piece.main.width = new_width
    piece.main.height = new_height

    if piece.parallel:
        piece.parallel.grid = [row[min_col:max_col + 1] for row in piece.parallel.grid[min_row:max_row + 1]]
        piece.parallel.screens = [row[min_col:max_col + 1] for row in piece.parallel.screens[min_row:max_row + 1]]
        piece.parallel.width = new_width
        piece.parallel.height = new_height

    # Adjust restrictions if present
    if piece.restriction is not None:
        adjusted_restrictions = []
        for pos in piece.restriction:
            old_row = pos // 8
            old_col = pos % 8
            new_row = (old_row + min_row) % 8
            new_col = (old_col + min_col) % 8
            adjusted_restrictions.append(new_row * 8 + new_col)
        piece.restriction = adjusted_restrictions

    return piece

def expand_arrangement(arrangement: List[List[int]], pieces: List[Piece]) -> List[List[int]]:
    """
    Expand an arrangement to include all cells from the pieces being merged.

    When merging pieces, if a piece contains cells not in the original arrangement,
    we need to expand the arrangement to include those cells in their correct
    relative positions.

    Raises an exception if the relative positions of cells within pieces conflict
    with the requested arrangement (e.g., contradictory merge operations).

    Note: This function uses wrap-aware position checking. Positions that differ
    by multiples of 8 are considered equivalent (for wrapping support). This allows
    arrangements like [[0x10, 0x11, 0x12, 0x13, 0x14]] and [[0x14, 0x15, 0x16, 0x17, 0x10]]
    to be merged into a valid horizontal loop.
    """
    # Build a mapping of cell_id -> (row, col) for all cells in all pieces
    # relative to a common coordinate system
    cell_positions: Dict[int, Tuple[int, int]] = {}
    # Track wrapped_position -> cell_id to detect when two different cells would occupy the same position after wrapping
    wrapped_position_to_cell: Dict[Tuple[int, int], int] = {}

    # First, map cells from the original arrangement
    for i, row in enumerate(arrangement):
        for j, cell in enumerate(row):
            if cell != -1:
                cell_positions[cell] = (i, j)
                wrapped_pos = (i % 8, j % 8)
                wrapped_position_to_cell[wrapped_pos] = cell

    # For each piece, determine where its cells should go
    for piece in pieces:
        # Find a cell that's already in our arrangement to anchor this piece
        anchor_cell = None
        anchor_piece_pos = None
        for i, row in enumerate(piece.main.grid):
            for j, cell in enumerate(row):
                if cell != -1 and cell in cell_positions:
                    anchor_cell = cell
                    anchor_piece_pos = (i, j)
                    break
            if anchor_cell is not None:
                break

        # Calculate offset between piece coordinates and arrangement coordinates
        anchor_arr_pos = cell_positions[anchor_cell]
        offset_row = anchor_arr_pos[0] - anchor_piece_pos[0]
        offset_col = anchor_arr_pos[1] - anchor_piece_pos[1]

        # Add all cells from this piece to cell_positions, checking for conflicts
        for i, row in enumerate(piece.main.grid):
            for j, cell in enumerate(row):
                if cell != -1:
                    new_pos = (i + offset_row, j + offset_col)
                    # Normalize position for wrapping (positions differing by 8 are equivalent)
                    wrapped_pos = (new_pos[0] % 8, new_pos[1] % 8)

                    if cell in cell_positions:
                        # Cell already has a position - verify it's consistent after wrapping
                        existing_pos = cell_positions[cell]
                        existing_wrapped = (existing_pos[0] % 8, existing_pos[1] % 8)
                        if existing_wrapped != wrapped_pos:
                            raise GenerationException(
                                f"Cannot merge: cell 0x{cell:02X} has conflicting positions. "
                                f"Existing position {existing_pos} (wrapped: {existing_wrapped}) conflicts with "
                                f"position {new_pos} (wrapped: {wrapped_pos}) from piece containing cells "
                                f"{[c for row in piece.main.grid for c in row if c != -1]}. "
                                f"This indicates contradictory merge operations."
                            )
                        # Same cell at same wrapped position - this is fine (loop detected)
                    elif wrapped_pos in wrapped_position_to_cell:
                        # Position is already occupied by a different cell after wrapping
                        existing_cell = wrapped_position_to_cell[wrapped_pos]
                        raise GenerationException(
                            f"Cannot merge: cell 0x{cell:02X} would be placed at position {new_pos} "
                            f"(wrapped: {wrapped_pos}), but that position is already occupied by "
                            f"cell 0x{existing_cell:02X}. This indicates contradictory merge operations."
                        )
                    else:
                        cell_positions[cell] = new_pos
                        wrapped_position_to_cell[wrapped_pos] = cell

    # Find the bounding box of all cells
    if not cell_positions:
        return arrangement

    min_row = min(pos[0] for pos in cell_positions.values())
    max_row = max(pos[0] for pos in cell_positions.values())
    min_col = min(pos[1] for pos in cell_positions.values())
    max_col = max(pos[1] for pos in cell_positions.values())

    # Create new arrangement with normalized coordinates
    new_height = max_row - min_row + 1
    new_width = max_col - min_col + 1
    new_arrangement = [[-1] * new_width for _ in range(new_height)]

    for cell, (row, col) in cell_positions.items():
        new_arrangement[row - min_row][col - min_col] = cell

    return new_arrangement

def calculate_merged_restrictions(pieces: List[Piece], arrangement: List[List[int]]) -> Optional[List[int]]:
    """
    Calculate restrictions for the merged piece.

    For each piece with restrictions, we translate the restrictions to account
    for the piece's position in the merged arrangement. The final restriction
    is the intersection of all translated restrictions.

    For example, when merging 4 quadrant pieces into a 2x2:
    - NW piece (at position 0,0) has restrictions like [0x00, 0x03, ...] - no translation needed
    - NE piece (at position 0,1) has restrictions like [0x01, 0x04, ...] - translate left by 1
    - SW piece (at position 1,0) has restrictions like [0x08, 0x0B, ...] - translate up by 1
    - SE piece (at position 1,1) has restrictions like [0x09, 0x0C, ...] - translate up and left by 1

    After translation, all should give [0x00, 0x03, 0x05, 0x18, 0x1B, 0x1E, 0x30, 0x35]
    """
    if not any(p.restriction for p in pieces):
        return None

    # Build mapping from cell to position in arrangement
    cell_to_new_pos = {}
    for i, row in enumerate(arrangement):
        for j, cell in enumerate(row):
            if cell != -1:
                cell_to_new_pos[cell] = (i, j)

    # For each piece, translate its restrictions
    translated_restrictions = []
    for piece in pieces:
        if piece.restriction is None:
            continue

        # Find the first cell in this piece and its position in the arrangement
        piece_cell = None
        piece_old_pos = None
        for i, row in enumerate(piece.main.grid):
            for j, cell in enumerate(row):
                if cell != -1 and cell in cell_to_new_pos:
                    piece_cell = cell
                    piece_old_pos = (i, j)
                    break
            if piece_cell is not None:
                break

        if piece_cell is None:
            continue

        new_pos = cell_to_new_pos[piece_cell]
        # The offset is how much we need to shift the restriction positions
        # to get the top-left corner position of the merged piece
        offset_row = new_pos[0] - piece_old_pos[0]
        offset_col = new_pos[1] - piece_old_pos[1]

        # Translate restrictions: shift each restriction position back by the offset
        # to get the position where the merged piece's top-left corner would be
        translated = []
        for r in piece.restriction:
            r_row = r // 8
            r_col = r % 8
            new_r_row = (r_row - offset_row) % 8
            new_r_col = (r_col - offset_col) % 8
            translated.append(new_r_row * 8 + new_r_col)
        translated_restrictions.append(set(translated))

    # Intersection of all translated restrictions
    result = translated_restrictions[0]
    for tr in translated_restrictions[1:]:
        result &= tr

    return list(result)

def merge_pieces(piece_list: List[Piece], arrangement: List[List[int]], world: World, player: int, overworld_screens: Dict[int, Screen]) -> List[Piece]:
    """
    Merge pieces according to the specified arrangement.

    The arrangement is a 2D list where:
    - Positive values are cell IDs that must be included
    - -1 indicates a flexible/empty position

    Example: [[0x00, 0x01], [0x08, 0x09]] merges 4 pieces into a 2x2 piece

    If a piece being merged contains additional cells not in the arrangement,
    the arrangement is automatically expanded to include all cells from all
    pieces being merged.
    """
    # Collect all cell IDs from arrangement, excluding -1
    target_cells = set()
    for row in arrangement:
        for cell in row:
            if cell != -1:
                target_cells.add(cell)

    # Find all pieces containing any of the target cells
    pieces_to_merge = []
    remaining_pieces = []

    for piece in piece_list:
        piece_cells = get_piece_cells(piece)
        if piece_cells & target_cells:
            pieces_to_merge.append(piece)
        else:
            remaining_pieces.append(piece)

    # Validate: all target cells must be found
    found_cells = set()
    for piece in pieces_to_merge:
        piece_cells = get_piece_cells(piece)
        # Check for overlapping cells between pieces (indicates contradictory merges)
        overlap = found_cells & piece_cells
        if overlap:
            raise GenerationException(f"Cannot merge: cells {overlap} appear in multiple pieces (contradictory merge operations)")
        found_cells.update(piece_cells)

    if not target_cells.issubset(found_cells):
        missing = target_cells - found_cells
        raise GenerationException(f"Cannot merge: cells {missing} not found in any piece")

    # If pieces contain additional cells not in the arrangement, expand the arrangement
    if found_cells != target_cells:
        arrangement = expand_arrangement(arrangement, pieces_to_merge)

    # Create the merged piece
    merged_piece = create_piece(world, player, arrangement, overworld_screens)

    # Calculate merged restrictions
    merged_piece.restriction = calculate_merged_restrictions(pieces_to_merge, arrangement)

    remaining_pieces.append(merged_piece)
    return remaining_pieces

def validate_and_wrap_pieces(piece_list: List[Piece], options: LayoutGeneratorOptions, world: World, player: int, overworld_screens: Dict[int, Screen]) -> List[Piece]:
    """
    Validate that all pieces are at most 8x8 in size.
    If a piece is too large, attempt to reduce its size using wrapping.
    """
    result_pieces = []

    for piece in piece_list:
        if piece.width <= 8 and piece.height <= 8:
            result_pieces.append(piece)
            continue

        # Piece is too large, need to apply wrapping
        if piece.width > 8 and not options.horizontal_wrap:
            raise GenerationException(
                f"Piece has width {piece.width} which exceeds 8, but horizontal wrapping is not enabled. "
                f"Cells: {[c for row in piece.main.grid for c in row if c != -1]}"
            )

        if piece.height > 8 and not options.vertical_wrap:
            raise GenerationException(
                f"Piece has height {piece.height} which exceeds 8, but vertical wrapping is not enabled. "
                f"Cells: {[c for row in piece.main.grid for c in row if c != -1]}"
            )

        # Calculate wrapped dimensions
        wrapped_width = min(piece.width, 8)
        wrapped_height = min(piece.height, 8)

        # Create new wrapped grid, checking for conflicts
        wrapped_grid = [[-1] * wrapped_width for _ in range(wrapped_height)]

        for i in range(piece.height):
            wrapped_i = i % 8
            for j in range(piece.width):
                wrapped_j = j % 8
                cell = piece.main.grid[i][j]

                if cell != -1:
                    existing = wrapped_grid[wrapped_i][wrapped_j]
                    if existing != -1 and existing != cell:
                        raise GenerationException(
                            f"Wrapping conflict: cell 0x{cell:02X} at position ({i}, {j}) "
                            f"would wrap to ({wrapped_i}, {wrapped_j}) which already contains cell 0x{existing:02X}. "
                            f"Piece cells: {[c for row in piece.main.grid for c in row if c != -1]}"
                        )
                    wrapped_grid[wrapped_i][wrapped_j] = cell

        # Create the wrapped piece
        wrapped_piece = create_piece(world, player, wrapped_grid, overworld_screens)
        wrapped_piece.restriction = piece.restriction
        result_pieces.append(wrapped_piece)

    return result_pieces

def add_piece_data(world: World, player: int, piece: Piece, large_screen_quadrant_info: Dict[int, Dict], large_screen_quadrant_info_land: Dict[int, Dict], large_screen_quadrant_info_water: Dict[int, Dict]) -> None:
    """
    Add computed data to piece
    Calls add_world_piece_edge_info for main and parallel pieces
    """
    num_pieces = 2 if piece.parallel else 1
    for p in range(num_pieces):
        world_piece = piece.main if p == 0 else piece.parallel
        add_world_piece_edge_info(world, player, world_piece, large_screen_quadrant_info, large_screen_quadrant_info_land, large_screen_quadrant_info_water)

    # Calculate edge_sides and max_edges_per_side: 0 for multi-cell pieces
    if piece.width == 1 and piece.height == 1:
        edge_sides = 0
        max_edges_per_side = 0
        # Count edge sides and max edges for main piece and parallel piece (if exists)
        for world_piece in ([piece.main, piece.parallel] if piece.parallel else [piece.main]):
            north_count = len(world_piece.north_edges[0][0]) + (len(world_piece.north_edges_water[0][0]) if world_piece.north_edges_water else 0)
            if north_count > 0:
                edge_sides += 1
                max_edges_per_side = max(max_edges_per_side, north_count)
            south_count = len(world_piece.south_edges[0][0]) + (len(world_piece.south_edges_water[0][0]) if world_piece.south_edges_water else 0)
            if south_count > 0:
                edge_sides += 1
                max_edges_per_side = max(max_edges_per_side, south_count)
            west_count = len(world_piece.west_edges[0][0]) + (len(world_piece.west_edges_water[0][0]) if world_piece.west_edges_water else 0)
            if west_count > 0:
                edge_sides += 1
                max_edges_per_side = max(max_edges_per_side, west_count)
            east_count = len(world_piece.east_edges[0][0]) + (len(world_piece.east_edges_water[0][0]) if world_piece.east_edges_water else 0)
            if east_count > 0:
                edge_sides += 1
                max_edges_per_side = max(max_edges_per_side, east_count)
        piece.edge_sides = edge_sides
        piece.max_edges_per_side = max_edges_per_side
    else:
        piece.edge_sides = 0
        piece.max_edges_per_side = 0

def add_world_piece_edge_info(world: World, player: int, piece: WorldPiece, large_screen_quadrant_info: Dict[int, Dict], large_screen_quadrant_info_land: Dict[int, Dict], large_screen_quadrant_info_water: Dict[int, Dict]) -> None:
    """
    Populate piece edge information
    Initializes 8x8 edge arrays and extracts edges from screens
    """
    piece.north_edges = [[] for _ in range(8)]
    piece.south_edges = [[] for _ in range(8)]
    piece.west_edges = [[] for _ in range(8)]
    piece.east_edges = [[] for _ in range(8)]

    if not world.owTerrain[player]:
        piece.north_edges_water = [[] for _ in range(8)]
        piece.south_edges_water = [[] for _ in range(8)]
        piece.west_edges_water = [[] for _ in range(8)]
        piece.east_edges_water = [[] for _ in range(8)]

    for k in range(piece.height):
        for l in range(piece.width):
            piece.north_edges[k].append([])
            piece.south_edges[k].append([])
            piece.west_edges[k].append([])
            piece.east_edges[k].append([])

            if not world.owTerrain[player]:
                piece.north_edges_water[k].append([])
                piece.south_edges_water[k].append([])
                piece.west_edges_water[k].append([])
                piece.east_edges_water[k].append([])

    for k in range(piece.height):
        for l in range(piece.width):
            screen = piece.screens[k][l]
            if not screen:
                continue

            cell_id = piece.grid[k][l]

            if screen.big:
                # Determine quadrant by subtracting cell ID from screen ID
                # 0x00 = NW (top-left), 0x01 = NE (top-right), 0x08 = SW (bottom-left), 0x09 = SE (bottom-right)
                quadrant_offset = cell_id - screen.id
                if quadrant_offset == 0x00:
                    quadrant_name = "NW"
                elif quadrant_offset == 0x01:
                    quadrant_name = "NE"
                elif quadrant_offset == 0x08:
                    quadrant_name = "SW"
                else:
                    quadrant_name = "SE"

                quadrant_info = (large_screen_quadrant_info[screen.id] if world.owTerrain[player]
                               else large_screen_quadrant_info_land[screen.id])

                piece.north_edges[k][l] = [e for e in quadrant_info[quadrant_name][Direction.North] if not e.dest]
                piece.south_edges[k][l] = [e for e in quadrant_info[quadrant_name][Direction.South] if not e.dest]
                piece.west_edges[k][l] = [e for e in quadrant_info[quadrant_name][Direction.West] if not e.dest]
                piece.east_edges[k][l] = [e for e in quadrant_info[quadrant_name][Direction.East] if not e.dest]

                if not world.owTerrain[player]:
                    quadrant_info_water = large_screen_quadrant_info_water[screen.id]
                    piece.north_edges_water[k][l] = [e for e in quadrant_info_water[quadrant_name][Direction.North] if not e.dest]
                    piece.south_edges_water[k][l] = [e for e in quadrant_info_water[quadrant_name][Direction.South] if not e.dest]
                    piece.west_edges_water[k][l] = [e for e in quadrant_info_water[quadrant_name][Direction.West] if not e.dest]
                    piece.east_edges_water[k][l] = [e for e in quadrant_info_water[quadrant_name][Direction.East] if not e.dest]
            else:
                for edge in sorted(screen.edges.values(), key=lambda e: e.midpoint):
                    if not edge.dest:
                        if edge.direction == Direction.North:
                            target = piece.north_edges[k][l] if world.owTerrain[player] or edge.terrain != Terrain.Water else piece.north_edges_water[k][l]
                            target.append(edge)
                        elif edge.direction == Direction.South:
                            target = piece.south_edges[k][l] if world.owTerrain[player] or edge.terrain != Terrain.Water else piece.south_edges_water[k][l]
                            target.append(edge)
                        elif edge.direction == Direction.West:
                            target = piece.west_edges[k][l] if world.owTerrain[player] or edge.terrain != Terrain.Water else piece.west_edges_water[k][l]
                            target.append(edge)
                        elif edge.direction == Direction.East:
                            target = piece.east_edges[k][l] if world.owTerrain[player] or edge.terrain != Terrain.Water else piece.east_edges_water[k][l]
                            target.append(edge)

def get_screen_id_from_cell(cell_id: int) -> int:
    """Get the base screen ID from a cell ID.

    For large screens, returns the top-left corner ID.
    For small screens, returns the cell ID unchanged.
    """
    base_id = cell_id & 0xBF # Remove world bit if present
    # Check if this is a quadrant of a large screen
    for large_id in large_screen_ids:
        if base_id in [large_id, large_id + 0x01, large_id + 0x08, large_id + 0x09]:
            return large_id | (cell_id & 0x40) # Preserve world bit
    return cell_id

# ============================================================================
# PLACEMENT ALGORITHM
# ============================================================================

def random_place_piece(
    world: World,
    player: int,
    grid_info: GridInfo,
    options: LayoutGeneratorOptions,
    pieces: List[Piece],
    ignore_bonus_points: bool
) -> PiecePlacementResult:
    """
    Core placement algorithm
    Evaluates all valid positions and scores each based on edge compatibility
    Performance is critical within these deeply nested loops, every optimization matters
    """
    use_crossed_groups = (world.owCrossed[player] == 'polar' and world.owMixed[player]) or world.owCrossed[player] == 'grouped'
    is_unrestricted_crossed = world.owCrossed[player] == 'unrestricted'
    keep_similar = ENABLE_KEEP_SIMILAR_SPECIAL_HANDLING and world.owKeepSimilar[player]

    width = 8
    height = 8
    horizontal_wrap = options.horizontal_wrap
    vertical_wrap = options.vertical_wrap
    distortion_chance = options.distortion_chance
    use_distortion = distortion_chance > 0
    crossed_chance = options.crossed_chance
    crossworld_weights = (1 - crossed_chance, crossed_chance) if is_unrestricted_crossed else (1, 0)
    if not is_unrestricted_crossed:
        crossed_score_weight = 1
    penalty_full_edge_mismatch = options.penalty_full_edge_mismatch
    penalty_partial_edge_mismatch = options.penalty_partial_edge_mismatch
    bonus_partial_edge_match = 0 if ignore_bonus_points else options.bonus_partial_edge_match
    bonus_full_edge_match = 0 if ignore_bonus_points else options.bonus_full_edge_match
    bonus_crossed_group_match = 0 if ignore_bonus_points else options.bonus_crossed_group_match
    bonus_fill_parallel = 0 if ignore_bonus_points else options.bonus_fill_parallel
    can_stop_early = penalty_full_edge_mismatch >= 0 and penalty_partial_edge_mismatch >= 0

    grid = grid_info.grid
    crossed_groups = grid_info.crossed_groups
    north_edges_grid = grid_info.north_edges_grid
    south_edges_grid = grid_info.south_edges_grid
    west_edges_grid = grid_info.west_edges_grid
    east_edges_grid = grid_info.east_edges_grid
    north_edges_water_grid = grid_info.north_edges_water_grid
    south_edges_water_grid = grid_info.south_edges_water_grid
    west_edges_water_grid = grid_info.west_edges_water_grid
    east_edges_water_grid = grid_info.east_edges_water_grid

    best_choices = []
    max_score_major = -1000000
    max_score_minor = -1000000

    for c, piece in enumerate(pieces):
        piece_main = piece.main
        piece_parallel = piece.parallel
        wrld = piece.world
        restriction = piece.restriction
        piece_width = piece.width
        piece_height = piece.height
        piece_crossed_groups = piece.crossed_groups

        grid_main_world = grid[wrld]
        grid_other_world = grid[1 - wrld]

        i_range = height if vertical_wrap else height - piece_height + 1
        for i in range(i_range):
            j_range = width if horizontal_wrap else width - piece_width + 1
            for j in range(j_range):
                if restriction and (i * 8 + j) not in restriction:
                    continue

                # Check for overlap
                overlap = False
                for k in range(piece_height):
                    row_idx = (i + k) % height
                    for l in range(piece_width):
                        col_idx = (j + l) % width

                        if grid_main_world[row_idx][col_idx] != -1 and piece_main.screens[k][l]:
                            overlap = True
                            break

                        if use_crossed_groups and crossed_groups[row_idx][col_idx] != -1 and crossed_groups[row_idx][col_idx] != piece_crossed_groups[k][l]:
                            overlap = True
                            break

                        if piece_parallel and grid_other_world[row_idx][col_idx] != -1 and piece_parallel.screens[k][l]:
                            overlap = True
                            break

                if not overlap:
                    score_major = 0
                    score_minor = 0

                    # Calculate scores based on edge compatibility
                    for k in range(piece_height):
                        row_idx = (i + k) % height
                        row_above = (i + k + height - 1) % height
                        row_below = (i + k + 1) % height
                        i_plus_k = i + k

                        for l in range(piece_width):
                            col_idx = (j + l) % width
                            col_left = (j + l + width - 1) % width
                            col_right = (j + l + 1) % width
                            j_plus_l = j + l

                            num_pieces = 2 if piece_parallel else 1
                            for p in range(num_pieces):
                                world_piece = piece_main if p == 0 else piece_parallel
                                cw = wrld if p == 0 else 1 - wrld

                                if not world_piece.screens[k][l]:
                                    continue

                                # Add small bias when the crossed group is already determined and matches the piece to avoid issues later on
                                if use_crossed_groups and not piece_parallel and crossed_groups[row_idx][col_idx] == piece_crossed_groups[k][l]:
                                    score_minor += bonus_crossed_group_match

                                if not piece_parallel and grid_other_world[row_idx][col_idx] != -1:
                                    score_minor += bonus_fill_parallel

                                for terrain in range(1 if world.owTerrain[player] else 2):
                                    north_piece = world_piece.north_edges if terrain == 0 else world_piece.north_edges_water
                                    south_piece = world_piece.south_edges if terrain == 0 else world_piece.south_edges_water
                                    west_piece = world_piece.west_edges if terrain == 0 else world_piece.west_edges_water
                                    east_piece = world_piece.east_edges if terrain == 0 else world_piece.east_edges_water

                                    north_edges = north_edges_grid if terrain == 0 else north_edges_water_grid
                                    south_edges = south_edges_grid if terrain == 0 else south_edges_water_grid
                                    west_edges = west_edges_grid if terrain == 0 else west_edges_water_grid
                                    east_edges = east_edges_grid if terrain == 0 else east_edges_water_grid

                                    # Check boundary edges
                                    if not vertical_wrap and i_plus_k == 0 and (not use_distortion or distortion_chance <= random.random()):
                                        if north_piece[k][l]:
                                            score_major -= penalty_full_edge_mismatch
                                        else:
                                            score_minor += bonus_full_edge_match

                                    if not vertical_wrap and i_plus_k == height - 1 and (not use_distortion or distortion_chance <= random.random()):
                                        if south_piece[k][l]:
                                            score_major -= penalty_full_edge_mismatch
                                        else:
                                            score_minor += bonus_full_edge_match

                                    if not horizontal_wrap and j_plus_l == 0 and (not use_distortion or distortion_chance <= random.random()):
                                        if west_piece[k][l]:
                                            score_major -= penalty_full_edge_mismatch
                                        else:
                                            score_minor += bonus_full_edge_match

                                    if not horizontal_wrap and j_plus_l == width - 1 and (not use_distortion or distortion_chance <= random.random()):
                                        if east_piece[k][l]:
                                            score_major -= penalty_full_edge_mismatch
                                        else:
                                            score_minor += bonus_full_edge_match

                                    for other_world_index in range(2 if is_unrestricted_crossed else 1):
                                        # Check neighbor compatibility (north)
                                        if is_unrestricted_crossed:
                                            w = cw if other_world_index == 0 else 1 - cw
                                            crossed_score_weight = crossworld_weights[other_world_index]
                                        elif use_crossed_groups and crossed_groups[row_above][col_idx] != piece_crossed_groups[k][l]:
                                            w = 1 - cw
                                        else:
                                            w = cw

                                        if (i_plus_k != 0 or vertical_wrap) and grid[w][row_above][col_idx] != -1 and (not use_distortion or distortion_chance <= random.random()):
                                            piece_edges = len(north_piece[k][l])
                                            grid_edges = len(south_edges[w][row_above][col_idx])
                                            if piece_edges == grid_edges:
                                                score_minor += bonus_full_edge_match * crossed_score_weight
                                            elif not keep_similar and ((piece_edges == 0) == (grid_edges == 0)):
                                                score_minor += bonus_partial_edge_match * crossed_score_weight
                                                score_major -= penalty_partial_edge_mismatch * crossed_score_weight
                                            else:
                                                score_major -= penalty_full_edge_mismatch * crossed_score_weight

                                        # Check south neighbor
                                        if is_unrestricted_crossed:
                                            w = cw if other_world_index == 0 else 1 - cw
                                            crossed_score_weight = crossworld_weights[other_world_index]
                                        elif use_crossed_groups and crossed_groups[row_below][col_idx] != piece_crossed_groups[k][l]:
                                            w = 1 - cw
                                        else:
                                            w = cw

                                        if (i_plus_k != height - 1 or vertical_wrap) and grid[w][row_below][col_idx] != -1 and (not use_distortion or distortion_chance <= random.random()):
                                            piece_edges = len(south_piece[k][l])
                                            grid_edges = len(north_edges[w][row_below][col_idx])
                                            if piece_edges == grid_edges:
                                                score_minor += bonus_full_edge_match * crossed_score_weight
                                            elif not keep_similar and ((piece_edges == 0) == (grid_edges == 0)):
                                                score_minor += bonus_partial_edge_match * crossed_score_weight
                                                score_major -= penalty_partial_edge_mismatch * crossed_score_weight
                                            else:
                                                score_major -= penalty_full_edge_mismatch * crossed_score_weight

                                        # Check west neighbor
                                        if is_unrestricted_crossed:
                                            w = cw if other_world_index == 0 else 1 - cw
                                            crossed_score_weight = crossworld_weights[other_world_index]
                                        elif use_crossed_groups and crossed_groups[row_idx][col_left] != piece_crossed_groups[k][l]:
                                            w = 1 - cw
                                        else:
                                            w = cw

                                        if (j_plus_l != 0 or horizontal_wrap) and grid[w][row_idx][col_left] != -1 and (not use_distortion or distortion_chance <= random.random()):
                                            piece_edges = len(west_piece[k][l])
                                            grid_edges = len(east_edges[w][row_idx][col_left])
                                            if piece_edges == grid_edges:
                                                score_minor += bonus_full_edge_match * crossed_score_weight
                                            elif not keep_similar and ((piece_edges == 0) == (grid_edges == 0)):
                                                score_minor += bonus_partial_edge_match * crossed_score_weight
                                                score_major -= penalty_partial_edge_mismatch * crossed_score_weight
                                            else:
                                                score_major -= penalty_full_edge_mismatch * crossed_score_weight

                                        # Check east neighbor
                                        if is_unrestricted_crossed:
                                            w = cw if other_world_index == 0 else 1 - cw
                                            crossed_score_weight = crossworld_weights[other_world_index]
                                        elif use_crossed_groups and crossed_groups[row_idx][col_right] != piece_crossed_groups[k][l]:
                                            w = 1 - cw
                                        else:
                                            w = cw

                                        if (j_plus_l != width - 1 or horizontal_wrap) and grid[w][row_idx][col_right] != -1 and (not use_distortion or distortion_chance <= random.random()):
                                            piece_edges = len(east_piece[k][l])
                                            grid_edges = len(west_edges[w][row_idx][col_right])
                                            if piece_edges == grid_edges:
                                                score_minor += bonus_full_edge_match * crossed_score_weight
                                            elif not keep_similar and ((piece_edges == 0) == (grid_edges == 0)):
                                                score_minor += bonus_partial_edge_match * crossed_score_weight
                                                score_major -= penalty_partial_edge_mismatch * crossed_score_weight
                                            else:
                                                score_major -= penalty_full_edge_mismatch * crossed_score_weight

                                        if can_stop_early and score_major < max_score_major:
                                            break
                                    # This is so an we can break out of all remaining checks for the current placement option
                                    else:
                                        continue
                                    break
                                else:
                                    continue
                                break
                            else:
                                continue
                            break
                        else:
                            continue
                        break

                    if score_major == max_score_major and score_minor == max_score_minor:
                        best_choices.append((c, i, j))

                    if score_major > max_score_major or (score_major == max_score_major and score_minor > max_score_minor):
                        max_score_major = score_major
                        max_score_minor = score_minor
                        best_choices = [(c, i, j)]

    if not best_choices:
        return PiecePlacementResult(success=False, piece=None, score_major=0, score_minor=0)

    # Select random best choice
    piece_index, row, column = random.choice(best_choices)
    used_score_major = max_score_major
    used_score_minor = max_score_minor

    piece = pieces[piece_index]
    wrld = piece.world

    # Place the piece on the grid
    for k in range(piece.height):
        row_idx = (row + k) % height
        for l in range(piece.width):
            col_idx = (column + l) % width
            num_pieces = 2 if piece.parallel else 1
            for p in range(num_pieces):
                world_piece = piece.main if p == 0 else piece.parallel
                w = wrld if p == 0 else 1 - wrld

                grid[w][row_idx][col_idx] = world_piece.grid[k][l]
                north_edges_grid[w][row_idx][col_idx] = world_piece.north_edges[k][l]
                south_edges_grid[w][row_idx][col_idx] = world_piece.south_edges[k][l]
                west_edges_grid[w][row_idx][col_idx] = world_piece.west_edges[k][l]
                east_edges_grid[w][row_idx][col_idx] = world_piece.east_edges[k][l]

                if not world.owTerrain[player]:
                    north_edges_water_grid[w][row_idx][col_idx] = world_piece.north_edges_water[k][l]
                    south_edges_water_grid[w][row_idx][col_idx] = world_piece.south_edges_water[k][l]
                    west_edges_water_grid[w][row_idx][col_idx] = world_piece.west_edges_water[k][l]
                    east_edges_water_grid[w][row_idx][col_idx] = world_piece.east_edges_water[k][l]

            if use_crossed_groups:
                crossed_groups[row_idx][col_idx] = piece_crossed_groups[k][l]

    return PiecePlacementResult(success=True, piece=piece, score_major=used_score_major, score_minor=used_score_minor)

def place_single_restriction_pieces(
    world: World,
    player: int,
    grid_info: GridInfo,
    options: LayoutGeneratorOptions,
    pieces: List[Piece]
) -> Tuple[List[Piece], int]:
    """
    Place pieces that have a restriction list with only a single element.
    These pieces are forced into a single position, so we can place them deterministically.

    This function iteratively:
    1. Validates restriction lists against current grid state and grid bounds
    2. Places pieces with single-element restrictions
    3. Repeats until no more pieces can be placed

    Returns a tuple of (remaining_pieces, count_of_placed_pieces).
    """
    use_crossed_groups = (world.owCrossed[player] == 'polar' and world.owMixed[player]) or world.owCrossed[player] == 'grouped'

    remaining_pieces = list(pieces)
    placed_count = 0

    placed_this_iteration = True
    while placed_this_iteration:
        placed_this_iteration = False

        # Validate and update restriction lists for all remaining pieces
        for piece in remaining_pieces:
            if piece.restriction is None:
                continue

            valid_positions = []
            for position in piece.restriction:
                row = position // 8
                column = position % 8
                wrld = piece.world
                piece_crossed_groups = piece.crossed_groups

                # Check if this position is valid
                is_valid = True

                # Check if piece would go outside grid bounds when wrapping is disabled
                if not options.horizontal_wrap and column + piece.width > 8:
                    is_valid = False
                if not options.vertical_wrap and row + piece.height > 8:
                    is_valid = False

                # Check for overlap with already placed pieces
                if is_valid:
                    for k in range(piece.height):
                        if not is_valid:
                            break
                        row_idx = (row + k) % 8
                        for l in range(piece.width):
                            col_idx = (column + l) % 8

                            # Check main world overlap
                            if grid_info.grid[wrld][row_idx][col_idx] != -1 and piece.main.screens[k][l]:
                                is_valid = False
                                break

                            # Check parallel world overlap
                            if piece.parallel and grid_info.grid[1 - wrld][row_idx][col_idx] != -1 and piece.parallel.screens[k][l]:
                                is_valid = False
                                break

                            # Check crossed groups
                            if use_crossed_groups and grid_info.crossed_groups[row_idx][col_idx] != -1 and grid_info.crossed_groups[row_idx][col_idx] != piece_crossed_groups[k][l]:
                                is_valid = False
                                break

                if is_valid:
                    valid_positions.append(position)

            # Update the restriction list
            if len(valid_positions) == 0:
                raise GenerationException(f"No valid positions remaining for piece with restriction list (original: {piece.restriction})")

            piece.restriction = valid_positions

        # Place pieces with single-element restrictions
        new_remaining_pieces = []
        for piece in remaining_pieces:
            # Check if this piece has exactly one restriction position
            if piece.restriction is not None and len(piece.restriction) == 1:
                position = piece.restriction[0]
                row = position // 8
                column = position % 8
                wrld = piece.world
                piece_crossed_groups = piece.crossed_groups

                # Place the piece on the grid
                for k in range(piece.height):
                    row_idx = (row + k) % 8
                    for l in range(piece.width):
                        col_idx = (column + l) % 8
                        num_pieces = 2 if piece.parallel else 1
                        for p in range(num_pieces):
                            world_piece = piece.main if p == 0 else piece.parallel
                            w = wrld if p == 0 else 1 - wrld

                            grid_info.grid[w][row_idx][col_idx] = world_piece.grid[k][l]
                            grid_info.north_edges_grid[w][row_idx][col_idx] = world_piece.north_edges[k][l]
                            grid_info.south_edges_grid[w][row_idx][col_idx] = world_piece.south_edges[k][l]
                            grid_info.west_edges_grid[w][row_idx][col_idx] = world_piece.west_edges[k][l]
                            grid_info.east_edges_grid[w][row_idx][col_idx] = world_piece.east_edges[k][l]

                            if not world.owTerrain[player]:
                                grid_info.north_edges_water_grid[w][row_idx][col_idx] = world_piece.north_edges_water[k][l]
                                grid_info.south_edges_water_grid[w][row_idx][col_idx] = world_piece.south_edges_water[k][l]
                                grid_info.west_edges_water_grid[w][row_idx][col_idx] = world_piece.west_edges_water[k][l]
                                grid_info.east_edges_water_grid[w][row_idx][col_idx] = world_piece.east_edges_water[k][l]

                        if use_crossed_groups:
                            grid_info.crossed_groups[row_idx][col_idx] = piece_crossed_groups[k][l]

                placed_count += 1
                placed_this_iteration = True
            else:
                new_remaining_pieces.append(piece)

        remaining_pieces = new_remaining_pieces

    return remaining_pieces, placed_count

def get_random_layout(world: World, player: int, connected_edges_cache: List[str], pieces_to_place: List[Piece], options: LayoutGeneratorOptions, prio_edges: List[str], overworld_screens: Dict[int, Screen]) -> LayoutGeneratorResult:
    skip_validate_layout = world.accessibility[player] == 'none'
    score_mult_separate_areas = options.score_mult_separate_areas
    apply_start_loc_penalty = options.score_mult_start_loc_distance > 0 and world.shuffle[player] == 'vanilla' and (world.is_dark_chapel_start(player) or world.doorShuffle[player] == 'vanilla' or world.intensity[player] < 3 or world.mode[player] == 'standard')
    total_score = 0
    best_score = -1000000
    worst_score = 1000000
    best_grid_info = None
    separate_areas = None
    start_loc_distance = None

    # Pre-place pieces with single-element restriction lists
    base_grid_info = create_empty_grid_info(0.0)
    remaining_pieces, preplaced_count = place_single_restriction_pieces(world, player, base_grid_info, options, pieces_to_place)
    logger = logging.getLogger('')

    successes = 0
    failures = 0
    run = 0
    while run < options.min_runs or (run * successes < options.target_runs_times_successes and run < options.max_runs):
        run += 1
        connected_edges = connected_edges_cache.copy()
        piece_list = remaining_pieces.copy()

        # Copy the pre-placed grid with a new random seed for edge connections
        grid_info = copy_grid_info(base_grid_info, random.random())
        for piece in piece_list:
            piece.delay = 0

        major_score = 0

        # Order pieces by size, max_edges_per_side, edge_sides, and randomness
        random.shuffle(piece_list)
        if options.sort_by_edge_sides:
            piece_list.sort(key=lambda p: p.edge_sides)
        if options.sort_by_max_edges_per_side:
            piece_list.sort(key=lambda p: p.max_edges_per_side, reverse=True)
        if options.sort_by_piece_size:
            piece_list.sort(key=lambda p: p.width * p.height, reverse=True)
        if options.random_order > 0:
            for i, piece in enumerate(piece_list):
                piece.order = i + random.random() * (options.random_order + 1)
            piece_list.sort(key=lambda p: p.order)

        # Place pieces
        placed_pieces = set()
        while piece_list:
            pieces = [piece_list[0]]
            if piece_list[0].delay < options.max_delay:
                for i in range(1, min(options.multi_choice, len(piece_list))):
                    pieces.append(piece_list[i])

            result = random_place_piece(world, player, grid_info, options, pieces, len(placed_pieces) + preplaced_count < options.first_ignore_bonus_points)

            if not result.success:
                failures += 1
                break

            if result.piece != piece_list[0]:
                piece_list[0].delay += 1

            placed_pieces.add(result.piece)
            piece_list.remove(result.piece)
            major_score += result.score_major
        else:
            # Successfully placed all pieces
            if options.check_reachability:
                disabled_count = connect_edges_for_screen_layout(world, player, grid_info, options, connected_edges, prio_edges, overworld_screens, False)
                valid_layout = skip_validate_layout or validate_layout(world, player)
                if not valid_layout:
                    clean_up_connected_edges(world, player, connected_edges_cache, connected_edges)
                    failures += 1
                    continue
                score = -disabled_count
                if score_mult_separate_areas > 0:
                    separate_areas = len(get_separate_ow_areas(world, player))
                    score -= score_mult_separate_areas * separate_areas
                if apply_start_loc_penalty:
                    start_loc_distance = get_start_loc_distance(world, player, grid_info.grid, options)
                    min_dist = options.start_loc_min_distance
                    if start_loc_distance < min_dist:
                        score -= options.score_mult_start_loc_distance * (min_dist - start_loc_distance)
                logger.debug("Found valid layout with " + str(disabled_count) + " disabled edges and " + str(separate_areas) + " separate areas and distance " + str(start_loc_distance) + " between start locations")
                clean_up_connected_edges(world, player, connected_edges_cache, connected_edges)
                successes += 1
            else:
                successes += 1
                score = major_score

            total_score += score

            if score > best_score:
                best_score = score
                best_grid_info = grid_info

            if score < worst_score:
                worst_score = score

    if best_grid_info is None:
        return LayoutGeneratorResult(
            successes=successes,
            failures=failures
        )

    return LayoutGeneratorResult(
        grid_info=best_grid_info,
        score=best_score,
        worst_score=worst_score,
        average_score=total_score / successes,
        successes=successes,
        failures=failures
    )

def clean_up_connected_edges(world: World, player: int, connected_edges_cache: List[str], connected_edges: List[str]) -> None:
    for edge_name in connected_edges:
        if edge_name not in connected_edges_cache:
            entrance = world.get_entrance(edge_name, player)
            entrance.connected_region.entrances.remove(entrance)
            entrance.connected_region = None
            edge = world.get_owedge(edge_name, player)
            edge.dest = None

def find_cell_position(grid: List[List[List[int]]], cell_id: int) -> Optional[Tuple[int, int, int]]:
    """Find the position of a cell in the grid, returning (world, row, col) or None if not found."""
    for w in range(2):
        for row in range(8):
            for col in range(8):
                if grid[w][row][col] == cell_id:
                    return (w, row, col)
    return None

def get_start_loc_distance(world: World, player: int, grid: List[List[List[int]]], options: LayoutGeneratorOptions) -> float:
    """Computes the starting location Manhattan distance on the grid, treating the world as a third dimension (switching world adds 1 to the distance)."""
    pos_lh = find_cell_position(grid, 0x6C if world.is_bombshop_start(player) else 0x2C)
    pos_sanc = find_cell_position(grid, 0x53 if world.is_dark_chapel_start(player) else 0x13)
    if pos_lh is None or pos_sanc is None:
        raise GenerationException("Could not find starting location cells, something went wrong with grid layout generation!")
    w1, row1, col1 = pos_lh
    w2, row2, col2 = pos_sanc
    row_diff = abs(row1 - row2)
    col_diff = abs(col1 - col2)
    if options.horizontal_wrap:
        col_diff = min(col_diff, 8 - col_diff)
    if options.vertical_wrap:
        row_diff = min(row_diff, 8 - row_diff)
    return row_diff + col_diff + abs(w1 - w2)

def get_prioritized_edges(world: World, player: int) -> List[str]:
    prio_edges = []
    if world.accessibility[player] != 'none':
        prio_edges += ['Desert EC']
        if not world.is_tile_swapped(0x3A, player):
            prio_edges += ['Desert Pass WC']
        if world.is_tile_swapped(0x13, player):
            prio_edges += ['Sanctuary WN']
            if world.owParallel[player]:
                prio_edges += ['Dark Chapel WN']
        if world.owParallel[player]:
            prio_edges += ['Flute Boy SC', 'Stumpy SC']
        else:
            if world.is_tile_swapped(0x2A, player):
                prio_edges += ['Flute Boy SC']
            else:
                prio_edges += ['Stumpy SC']
        if world.owTerrain[player]:
            prio_edges += ['Octoballoon NW', 'Bomber Corner NW']
            if world.is_tile_swapped(0x2D, player):
                prio_edges += ['Stone Bridge EC']
                if world.owParallel[player]:
                    prio_edges += ['Hammer Bridge EC']
            if not world.is_tile_swapped(0x35, player):
                prio_edges += ['Ice Lake ES']
                if world.owParallel[player]:
                    prio_edges += ['Lake Hylia ES']
    return prio_edges

escape_screen_ids = set([0x1B, 0x2B, 0x2C])

def connect_edges_for_screen_layout(world: World, player: int, grid_info: GridInfo, options: LayoutGeneratorOptions, connected_edges: List[str], prio_edges: List[str], overworld_screens: Dict[int, Screen], final_placement: bool) -> int:
    use_crossed_groups = (world.owCrossed[player] == 'polar' and world.owMixed[player]) or world.owCrossed[player] == 'grouped'
    is_unrestricted_crossed = world.owCrossed[player] == 'unrestricted'
    is_standard = world.mode[player] == 'standard'
    edge_random = _random.Random(grid_info.edge_connection_seed)
    left_to_connect: List[Direction, int, int, int, int] = []
    make_non_crossed = set()
    make_crossed = set()
    make_disabled = set()
    undecided = []

    # Collect information about all edge sets to connect
    for dir in [Direction.East, Direction.South]:
        for i in range(7 if dir == Direction.South and not options.vertical_wrap else 8):
            for j in range(7 if dir == Direction.East and not options.horizontal_wrap else 8):
                forced_escape = False
                forced_non_crossed = False
                forced_crossed = False
                has_edges_1 = [False, False]
                has_edges_2 = [False, False]
                for w in range(2):
                    for terrain in range(1 if world.owTerrain[player] else 2):
                        left_to_connect.append((dir, w, i, j, terrain))

                        if is_unrestricted_crossed:
                            if dir == Direction.East:
                                west_edges = grid_info.west_edges_grid if terrain == 0 else grid_info.west_edges_water_grid
                                east_edges = grid_info.east_edges_grid if terrain == 0 else grid_info.east_edges_water_grid
                                edge_set_1 = east_edges[w][i][j]
                                edge_set_2 = west_edges[w][i][(j + 1) % 8]
                                if is_standard and grid_info.grid[w][i][j] in escape_screen_ids and grid_info.grid[w][i][(j + 1) % 8] in escape_screen_ids:
                                    forced_escape = True
                            else:
                                north_edges = grid_info.north_edges_grid if terrain == 0 else grid_info.north_edges_water_grid
                                south_edges = grid_info.south_edges_grid if terrain == 0 else grid_info.south_edges_water_grid
                                edge_set_1 = south_edges[w][i][j]
                                edge_set_2 = north_edges[w][(i + 1) % 8][j]
                                if is_standard and grid_info.grid[w][i][j] in escape_screen_ids and grid_info.grid[w][(i + 1) % 8][j] in escape_screen_ids:
                                    forced_escape = True
                            if any(edge for edge in edge_set_1 if edge.name in options.forced_non_crossed_edges) or any(edge for edge in edge_set_2 if edge.name in options.forced_non_crossed_edges):
                                forced_non_crossed = True
                            if any(edge for edge in edge_set_1 if edge.name in options.forced_crossed_edges) or any(edge for edge in edge_set_2 if edge.name in options.forced_crossed_edges):
                                forced_crossed = True
                            if edge_set_1:
                                has_edges_1[w] = True
                            if edge_set_2:
                                has_edges_2[w] = True
                if is_unrestricted_crossed:
                    if forced_escape:
                        make_non_crossed.add((dir, i, j))
                    elif forced_non_crossed and forced_crossed:
                        make_disabled.add((dir, i, j))
                    elif forced_non_crossed:
                        make_non_crossed.add((dir, i, j))
                    elif forced_crossed:
                        make_crossed.add((dir, i, j))
                    elif has_edges_1[0] != has_edges_1[1] and has_edges_2[0] != has_edges_2[1]:
                        # On both sides of the transition only one world has any edges, so make sure we can connect those
                        (make_non_crossed if has_edges_1[0] == has_edges_2[0] else make_crossed).add((dir, i, j))
                    else:
                        undecided.append((dir, i, j))

    if is_unrestricted_crossed:
        # Make outstanding crossed choices
        if options.crossed_limit > 0:
            edge_random.shuffle(undecided)
        remaining_crossed_edges = len(undecided) if options.crossed_limit < 0 else max(0, options.crossed_limit - len(make_crossed))
        if remaining_crossed_edges > 0:
            for x in undecided:
                if edge_random.random() < options.crossed_chance:
                    make_crossed.add(x)
                    remaining_crossed_edges -= 1
                    if remaining_crossed_edges == 0:
                        break

    # Connect the edge sets
    for dir, w, i, j, terrain in left_to_connect:
        if not is_unrestricted_crossed or not (dir, i, j) in make_disabled:
            world_idx = w
            if dir == Direction.East:
                edges_1 = grid_info.east_edges_grid if terrain == 0 else grid_info.east_edges_water_grid
                edges_2 = grid_info.west_edges_grid if terrain == 0 else grid_info.west_edges_water_grid
                if use_crossed_groups and grid_info.crossed_groups[i][j] != grid_info.crossed_groups[i][(j + 1) % 8]:
                    world_idx = 1 - w
                elif is_unrestricted_crossed and (dir, i, j) in make_crossed:
                    world_idx = 1 - w
                connect_edge_sets(world, player, edges_1[w][i][j], edges_2[world_idx][i][(j + 1) % 8], edge_random, connected_edges, prio_edges, final_placement)
            else:
                edges_1 = grid_info.south_edges_grid if terrain == 0 else grid_info.south_edges_water_grid
                edges_2 = grid_info.north_edges_grid if terrain == 0 else grid_info.north_edges_water_grid
                if use_crossed_groups and grid_info.crossed_groups[i][j] != grid_info.crossed_groups[(i + 1) % 8][j]:
                    world_idx = 1 - w
                elif is_unrestricted_crossed and (dir, i, j) in make_crossed:
                    world_idx = 1 - w
                connect_edge_sets(world, player, edges_1[w][i][j], edges_2[world_idx][(i + 1) % 8][j], edge_random, connected_edges, prio_edges, final_placement)

    # Count disabled edges
    disabled_count = 0
    for screen in overworld_screens.values():
        for edge in screen.edges.values():
            if not edge.dest:
                disabled_count += 1
    return disabled_count

def connect_edge_sets(world: World, player: int, edge_set_1: List[OWEdge], edge_set_2: List[OWEdge], edge_random: _random.Random, connected_edges: List[str], prio_edges: List[str], final_placement: bool) -> None:
    if edge_set_1 and edge_set_2:
        if world.owParallel[player]:
            # Make sure that we do not connect parallel with non-parallel edges
            parallel_edge_set_1 = [edge for edge in edge_set_1 if edge.parallel]
            parallel_edge_set_2 = [edge for edge in edge_set_2 if edge.parallel]
            if any(parallel_edge_set_1) and any(parallel_edge_set_2):
                # Special case for screens that have both types of edges in the same direction (Dig Game and Frog)
                if len(edge_set_1) == 2 and len(edge_set_2) == 2 and not edge_set_1[0].parallel and edge_set_1[1].parallel and not edge_set_2[0].parallel and edge_set_2[1].parallel:
                    connect_two_way(world, edge_set_1[0].name, edge_set_2[0].name, player, connected_edges, final_placement)
                # Check if the edges already got connected when handling the other world
                if any(edge for edge in parallel_edge_set_1 if edge.dest) or any(edge for edge in parallel_edge_set_2 if edge.dest):
                    return
                # Special case for Maze Race and Kakariko Suburb with Keep Similar, only connect those when handling the other world
                if ENABLE_KEEP_SIMILAR_SPECIAL_HANDLING and world.owKeepSimilar[player] and ((len(edge_set_1) == 1 and (edge_set_1[0].name == 'Maze Race ES' or edge_set_1[0].name == 'Kakariko Suburb WS')) or (len(edge_set_2) == 1 and (edge_set_2[0].name == 'Maze Race ES' or edge_set_2[0].name == 'Kakariko Suburb WS'))):
                    return
                edge_set_1 = parallel_edge_set_1
                edge_set_2 = parallel_edge_set_2
            else:
                non_parallel_edge_set_1 = [edge for edge in edge_set_1 if not edge.parallel]
                non_parallel_edge_set_2 = [edge for edge in edge_set_2 if not edge.parallel]
                if not any(non_parallel_edge_set_1) or not any(non_parallel_edge_set_2):
                    return
                edge_set_1 = non_parallel_edge_set_1
                edge_set_2 = non_parallel_edge_set_2
        if len(edge_set_1) == len(edge_set_2):
            for k in range(len(edge_set_1)):
                connect_two_way(world, edge_set_1[k].name, edge_set_2[k].name, player, connected_edges, final_placement)
        elif not ENABLE_KEEP_SIMILAR_SPECIAL_HANDLING or not world.owKeepSimilar[player]:
            if len(edge_set_1) < len(edge_set_2):
                edge_set_1, edge_set_2 = edge_set_2, edge_set_1
            # Not all edges from edge_set_1 can get connected
            prio_set = [edge for edge in edge_set_1 if edge.name in prio_edges]
            if len(prio_set) == len(edge_set_2):
                for k in range(len(prio_set)):
                    connect_two_way(world, prio_set[k].name, edge_set_2[k].name, player, connected_edges, final_placement)
            elif len(prio_set) < len(edge_set_2):
                unconnected_edges = edge_random.sample([edge.name for edge in edge_set_1 if edge.name not in prio_edges], len(edge_set_1) - len(edge_set_2))
                edges_to_connect = [edge for edge in edge_set_1 if edge.name not in unconnected_edges]
                for k in range(len(edge_set_2)):
                    connect_two_way(world, edges_to_connect[k].name, edge_set_2[k].name, player, connected_edges, final_placement)
            else:
                raise GenerationException("There should never be multiple edges with high priority in an edge set")

# ============================================================================
# GRID FORMATTING
# ============================================================================

def format_grid_for_spoiler(grid: List[List[int]]) -> str:
    lines = []
    header = "      "
    for col in range(8):
        header += f" {col} "
    lines.append(header)

    for row in range(8):
        border_line = "     +"
        for col in range(8):
            if row > 0 and is_same_large_screen(grid, row, col, row - 1, col):
                border_line += "  "
            else:
                border_line += "--"

            # Check if we need a corner or continuation
            if col < 7:
                has_horizontal_left = row == 0 or not is_same_large_screen(grid, row, col, row - 1, col)
                has_horizontal_right = row == 0 or not is_same_large_screen(grid, row, col + 1, row - 1, col + 1)
                has_vertical_top = row == 0 or not is_same_large_screen(grid, row - 1, col, row - 1, col + 1)
                has_vertical_bottom = not is_same_large_screen(grid, row, col, row, col + 1)

                if has_vertical_bottom or has_vertical_top:
                    if has_horizontal_left or has_horizontal_right:
                        border_line += "+"
                    else:
                        border_line += "|"
                else:
                    if has_horizontal_left or has_horizontal_right:
                        border_line += "-"
                    else:
                        border_line += " "
            else:
                border_line += "+"

        lines.append(border_line)

        row_name = "ABCDEFGH"[row]
        content_line = f"{row_name}({row * 8:02X})|"
        for col in range(8):
            screen_id = grid[row][col]
            if screen_id == -1:
                content_line += "--"
            else:
                content_line += f"{screen_id:02X}"

            # Check if we need a vertical separator after this cell
            if col < 7:
                if is_same_large_screen(grid, row, col, row, col + 1):
                    content_line += " "
                else:
                    content_line += "|"
            else:
                content_line += "|"

        lines.append(content_line)

    bottom_border = "     +"
    for col in range(8):
        bottom_border += "--"
        if col < 7:
            # Check if the bottom cells are part of the same large screen
            if is_same_large_screen(grid, 7, col, 7, col + 1):
                bottom_border += "-"
            else:
                bottom_border += "+"
        else:
            bottom_border += "+"
    lines.append(bottom_border)
    return "\n".join(lines)

def is_same_large_screen(grid: List[List[int]], row1: int, col1: int, row2: int, col2: int) -> bool:
    """Checks if two adjacent cells belong to the same large screen with correct quadrant positions."""
    id1, id2 = grid[row1 % 8][col1 % 8], grid[row2 % 8][col2 % 8]
    if id1 == -1 or id2 == -1:
        return False
    base1, base2 = get_screen_id_from_cell(id1), get_screen_id_from_cell(id2)
    if base1 != base2 or base1 not in large_screen_ids:
        return False
    # Get quadrant offsets (0x00=NW, 0x01=NE, 0x08=SW, 0x09=SE)
    q1, q2 = (id1 & 0xBF) - (base1 & 0xBF), (id2 & 0xBF) - (base2 & 0xBF)
    # Swap if cell2 is before cell1
    if col1 > col2 or row1 > row2:
        q1, q2 = q2, q1
    # Check valid adjacency: east (0x00->0x01, 0x08->0x09) or south (0x00->0x08, 0x01->0x09)
    if col1 != col2:
        return (q1, q2) in [(0x00, 0x01), (0x08, 0x09)]
    return (q1, q2) in [(0x00, 0x08), (0x01, 0x09)]

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def generate_random_grid_layout(world: World, player: int, connected_edges: List[str], crossed_group_b: List[int], forced_non_crossed: Set[str], forced_crossed: Set[str], crossed_limit: int, crossed_chance: float):
    """Main execution function"""
    import time

    horizontal_wrap = False
    vertical_wrap = False
    split_large_screens = False
    if world.customizer:
        grid_options = world.customizer.get_owgrid()
        if grid_options and player in grid_options:
            grid_options = grid_options[player]
            horizontal_wrap = 'wrap_horizontal' in grid_options and grid_options['wrap_horizontal'] == True
            vertical_wrap = 'wrap_vertical' in grid_options and grid_options['wrap_vertical'] == True
            split_large_screens = 'split_large_screens' in grid_options and grid_options['split_large_screens'] == True

    first_ignore_bonus = 2
    if not world.owParallel[player]:
        first_ignore_bonus *= 2
        if world.owCrossed[player] == 'unrestricted':
            first_ignore_bonus *= 2
    options = LayoutGeneratorOptions(
        horizontal_wrap=horizontal_wrap,
        vertical_wrap=vertical_wrap,
        split_large_screens=split_large_screens,
        distortion_chance=0.0,
        random_order=6 if world.owParallel[player] else 12,
        multi_choice=1,
        max_delay=10,
        penalty_full_edge_mismatch=1,
        penalty_partial_edge_mismatch=1,
        bonus_partial_edge_match=1,
        bonus_full_edge_match=1,
        bonus_crossed_group_match=1,
        bonus_fill_parallel=1 if world.owCrossed[player] == 'unrestricted' else 0,
        first_ignore_bonus_points=first_ignore_bonus,
        forced_non_crossed_edges=forced_non_crossed,
        forced_crossed_edges=forced_crossed,
        crossed_chance=crossed_chance,
        crossed_limit=crossed_limit,
        check_reachability=True,
        sort_by_edge_sides=world.owParallel[player] or not world.owTerrain[player],
        sort_by_max_edges_per_side=False,
        sort_by_piece_size=True,
        min_runs=100,
        max_runs=10000,
        target_runs_times_successes=5000,
        score_mult_separate_areas=4,
        start_loc_min_distance=4,
        score_mult_start_loc_distance=3
    )

    overworld_screens = initialize_screens(world, player)
    large_screen_quadrant_info, large_screen_quadrant_info_land, large_screen_quadrant_info_water = initialize_large_screen_data(overworld_screens)
    prio_edges = get_prioritized_edges(world, player)
    pieces_to_place = create_piece_list(world, player, options, crossed_group_b, overworld_screens, large_screen_quadrant_info, large_screen_quadrant_info_land, large_screen_quadrant_info_water)

    start_time = time.time()
    result = get_random_layout(world, player, connected_edges, pieces_to_place, options, prio_edges, overworld_screens)
    elapsed_time = time.time() - start_time

    if result.grid_info:
        connect_edges_for_screen_layout(world, player, result.grid_info, options, connected_edges, prio_edges, overworld_screens, True)
        grid = result.grid_info.grid

        world.owgrid[player] = grid
        world.owlayoutmap_lw[player] = {id & 0xBF: i for i, id in enumerate(sum(grid[0], []))}
        world.owlayoutmap_dw[player] = {id & 0xBF: i for i, id in enumerate(sum(grid[1], []))}

        world.spoiler.set_map('layout_grid_lw', format_grid_for_spoiler(grid[0]), grid[0], player)
        if not world.owParallel[player]:
            world.spoiler.set_map('layout_grid_dw', format_grid_for_spoiler(grid[1]), grid[1], player)

        logger = logging.getLogger('')
        logger.debug(f"\nLayout generation statistics:")
        logger.debug(f"  Best score: {result.score}")
        logger.debug(f"  Worst score: {result.worst_score}")
        logger.debug(f"  Average score: {result.average_score:.2f}")
        logger.debug(f"  Successes: {result.successes}")
        logger.debug(f"  Failures: {result.failures}")
        logger.debug(f"  Generation time: {elapsed_time:.3f}s")
        logger.debug(f"  Layouts per second: {(result.successes+result.failures)/elapsed_time:.3f}")

        if DRAW_IMAGE:
            logger.debug("Creating layout visualization...")
            try:
                from source.overworld.LayoutVisualizer import visualize_layout
                visualize_layout(grid, "visualizations", overworld_screens, large_screen_quadrant_info)
            except Exception as e:
                logger.warning(f"Warning: Could not create visualization: {e}")
    else:
        raise GenerationException(f"Layout generation FAILED after {result.failures} attempts and {elapsed_time:.3f} seconds")