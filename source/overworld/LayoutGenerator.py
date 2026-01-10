import copy
import logging
import RaceRandom as random
import random as _random
from typing import List, Dict, Optional, Set, Tuple
from BaseClasses import OWEdge, World, Direction, Terrain
from OverworldShuffle import connect_two_way, validate_layout

ENABLE_KEEP_SIMILAR_SPECIAL_HANDLING = False
PREVENT_WRAPPED_LARGE_SCREENS = False
DRAW_IMAGE = True

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
        screens: List[List[Optional[Screen]]],
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
        self.screens = screens
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
    __slots__ = ('main', 'parallel', 'world', 'width', 'height',
                 'invalid_wrap_row', 'invalid_wrap_column', 'restriction',
                 'crossed_groups', 'delay', 'order', 'edge_sides', 'max_edges_per_side')

    def __init__(
        self,
        main: WorldPiece,
        parallel: Optional[WorldPiece] = None,
        world: int = 0,
        width: int = 0,
        height: int = 0,
        invalid_wrap_row: Optional[List[int]] = None,
        invalid_wrap_column: Optional[List[int]] = None,
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
        self.invalid_wrap_row = invalid_wrap_row if invalid_wrap_row is not None else []
        self.invalid_wrap_column = invalid_wrap_column if invalid_wrap_column is not None else []
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
    __slots__ = ('horizontal_wrap', 'vertical_wrap',
                 'large_screen_pool', 'distortion_chance', 'random_order',
                 'multi_choice', 'max_delay', 'first_ignore_bonus_points',
                 'penalty_full_edge_mismatch', 'penalty_partial_edge_mismatch', 'bonus_partial_edge_match',
                 'bonus_full_edge_match', 'bonus_crossed_group_match', 'bonus_fill_parallel',
                 'forced_non_crossed_edges', 'forced_crossed_edges', 'check_reachability',
                 'crossed_chance', 'crossed_limit',
                 'sort_by_edge_sides', 'sort_by_max_edges_per_side', 'sort_by_piece_size',
                 'min_runs', 'max_runs', 'target_runs_times_successes')

    def __init__(
        self,
        horizontal_wrap: bool = True,
        vertical_wrap: bool = True,
        large_screen_pool: bool = False,
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
        target_runs_times_successes: int = 5000
    ):
        self.horizontal_wrap = horizontal_wrap
        self.vertical_wrap = vertical_wrap
        self.large_screen_pool = large_screen_pool
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
    used_screens_set = set()

    all_large_screens = [s for s in overworld_screens.values() if s.big]
    all_small_screens = [s for s in overworld_screens.values() if not s.big]

    if world.owParallel[player]:
        # In Parallel, only use light world screens
        # Each piece will automatically handle both worlds through parallel mechanism
        all_large_screens = [s for s in all_large_screens if not s.dark_world]
        all_small_screens = [s for s in all_small_screens if not s.dark_world]

    # In Standard mode, screens 0x1B, 0x2B, 0x2C are glued together as a single piece
    if world.mode[player] == 'standard':
        castle_screen = overworld_screens.get(0x1B)
        central_bonk_screen = overworld_screens.get(0x2B)
        links_house_screen = overworld_screens.get(0x2C)

        if castle_screen and central_bonk_screen and links_house_screen:
            piece = create_piece(world, player, [
                [0x1B, 0x1B],
                [0x1B, 0x1B],
                [0x2B, 0x2C]
            ], overworld_screens)

            if options.large_screen_pool:
                piece.restriction = [0x00, 0x03, 0x05, 0x18, 0x1B, 0x1E, 0x30, 0x35]

            piece_list.append(piece)
            used_screens_set.add(castle_screen)
            used_screens_set.add(central_bonk_screen)
            used_screens_set.add(links_house_screen)

            if world.owParallel[player]:
                used_screens_set.add(castle_screen.parallel)
                used_screens_set.add(central_bonk_screen.parallel)
                used_screens_set.add(links_house_screen.parallel)

    # Add large screens
    for screen in all_large_screens:
        if screen not in used_screens_set:
            piece = create_piece(world, player, [[screen.id, screen.id], [screen.id, screen.id]], overworld_screens)
            if options.large_screen_pool:
                piece.restriction = [0x00, 0x03, 0x05, 0x18, 0x1B, 0x1E, 0x30, 0x35]
            piece_list.append(piece)
            used_screens_set.add(screen)
            if world.owParallel[player]:
                used_screens_set.add(screen.parallel)

    # Add small screens
    for screen in all_small_screens:
        if screen not in used_screens_set:
            piece = create_piece(world, player, [[screen.id]], overworld_screens)
            if options.large_screen_pool:
                piece.restriction = [s.id for s in overworld_screens.values() if not s.big]
            piece_list.append(piece)
            used_screens_set.add(screen)
            if world.owParallel[player]:
                used_screens_set.add(screen.parallel)

    # Add piece data
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
                    screen_id = piece.main.grid[k][l]
                    if screen_id != -1:
                        piece.crossed_groups[k][l] = 1 if screen_id in crossed_group_b else 0
                    else:
                        if piece.parallel and piece.parallel.screens[k][l]:
                            piece.crossed_groups[k][l] = 1 if piece.parallel.grid[k][l] in crossed_group_b else 0

    return piece_list

def create_piece(world: World, player: int, grid: List[List[int]], overworld_screens: Dict[int, Screen]) -> Piece:
    """
    Create piece from grid of screen IDs
    Takes 2D array of screen IDs and creates main and parallel pieces
    """
    piece = Piece(
        main=WorldPiece(screens=[]),
        width=len(grid[0]),
        height=len(grid)
    )

    if world.owParallel[player]:
        piece.parallel = WorldPiece(screens=[])

    found_screens = set()

    for i in range(piece.height):
        new_row = []
        new_row_parallel = []
        piece.main.screens.append(new_row)
        if world.owParallel[player]:
            piece.parallel.screens.append(new_row_parallel)

        for j in range(piece.width):
            screen = overworld_screens.get(grid[i][j])
            new_row.append(screen)
            if world.owParallel[player]:
                new_row_parallel.append(screen.parallel if screen else None)

            if screen and screen not in found_screens:
                found_screens.add(screen)
                piece.world = 1 if screen.dark_world else 0
                if screen.big and PREVENT_WRAPPED_LARGE_SCREENS:
                    # For large screens, prevent wrapping at the second row/column
                    # This ensures the 2x2 piece doesn't split across the grid boundary
                    if (i + 1) not in piece.invalid_wrap_row:
                        piece.invalid_wrap_row.append(i + 1)
                    if (j + 1) not in piece.invalid_wrap_column:
                        piece.invalid_wrap_column.append(j + 1)

    return piece

def add_piece_data(world: World, player: int, piece: Piece, large_screen_quadrant_info: Dict[int, Dict], large_screen_quadrant_info_land: Dict[int, Dict], large_screen_quadrant_info_water: Dict[int, Dict]) -> None:
    """
    Add computed data to piece
    Calls add_piece_grid_info for main and parallel pieces
    """
    num_pieces = 2 if piece.parallel else 1
    for p in range(num_pieces):
        world_piece = piece.main if p == 0 else piece.parallel
        world_piece.width = len(world_piece.screens[0])
        world_piece.height = len(world_piece.screens)
        add_piece_grid_info(world, player, world_piece, large_screen_quadrant_info, large_screen_quadrant_info_land, large_screen_quadrant_info_water)

    piece.width = piece.main.width
    piece.height = piece.main.height

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

def add_piece_grid_info(world: World, player: int, piece: WorldPiece, large_screen_quadrant_info: Dict[int, Dict], large_screen_quadrant_info_land: Dict[int, Dict], large_screen_quadrant_info_water: Dict[int, Dict]) -> None:
    """
    Populate piece edge information
    Initializes 8x8 edge arrays and extracts edges from screens
    """
    piece.grid = [[] for _ in range(8)]
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
            piece.grid[k].append(piece.screens[k][l].id if piece.screens[k][l] else -1)
            piece.north_edges[k].append([])
            piece.south_edges[k].append([])
            piece.west_edges[k].append([])
            piece.east_edges[k].append([])

            if not world.owTerrain[player]:
                piece.north_edges_water[k].append([])
                piece.south_edges_water[k].append([])
                piece.west_edges_water[k].append([])
                piece.east_edges_water[k].append([])

    done_large = set()
    for k in range(piece.height):
        for l in range(piece.width):
            screen = piece.screens[k][l]
            if not screen:
                continue

            if screen.big:
                if screen.id not in done_large:
                    done_large.add(screen.id)
                    quadrant_info = (large_screen_quadrant_info[screen.id] if world.owTerrain[player]
                                   else large_screen_quadrant_info_land[screen.id])

                    piece.north_edges[k][l] = [e for e in quadrant_info["NW"][Direction.North] if not e.dest]
                    piece.north_edges[k][l + 1] = [e for e in quadrant_info["NE"][Direction.North] if not e.dest]
                    piece.south_edges[k + 1][l] = [e for e in quadrant_info["SW"][Direction.South] if not e.dest]
                    piece.south_edges[k + 1][l + 1] = [e for e in quadrant_info["SE"][Direction.South] if not e.dest]
                    piece.west_edges[k][l] = [e for e in quadrant_info["NW"][Direction.West] if not e.dest]
                    piece.west_edges[k + 1][l] = [e for e in quadrant_info["SW"][Direction.West] if not e.dest]
                    piece.east_edges[k][l + 1] = [e for e in quadrant_info["NE"][Direction.East] if not e.dest]
                    piece.east_edges[k + 1][l + 1] = [e for e in quadrant_info["SE"][Direction.East] if not e.dest]

                    if not world.owTerrain[player]:
                        quadrant_info = large_screen_quadrant_info_water[screen.id]
                        piece.north_edges_water[k][l] = [e for e in quadrant_info["NW"][Direction.North] if not e.dest]
                        piece.north_edges_water[k][l + 1] = [e for e in quadrant_info["NE"][Direction.North] if not e.dest]
                        piece.south_edges_water[k + 1][l] = [e for e in quadrant_info["SW"][Direction.South] if not e.dest]
                        piece.south_edges_water[k + 1][l + 1] = [e for e in quadrant_info["SE"][Direction.South] if not e.dest]
                        piece.west_edges_water[k][l] = [e for e in quadrant_info["NW"][Direction.West] if not e.dest]
                        piece.west_edges_water[k + 1][l] = [e for e in quadrant_info["SW"][Direction.West] if not e.dest]
                        piece.east_edges_water[k][l + 1] = [e for e in quadrant_info["NE"][Direction.East] if not e.dest]
                        piece.east_edges_water[k + 1][l + 1] = [e for e in quadrant_info["SE"][Direction.East] if not e.dest]
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
        invalid_wrap_row = piece.invalid_wrap_row
        invalid_wrap_column = piece.invalid_wrap_column
        restriction = piece.restriction
        piece_width = piece.width
        piece_height = piece.height
        piece_crossed_groups = piece.crossed_groups

        grid_main_world = grid[wrld]
        grid_other_world = grid[1 - wrld]

        i_range = height if vertical_wrap else height - piece_height + 1
        for i in range(i_range):
            if i >= height - piece_height + 1 and (height - i) in invalid_wrap_row:
                continue

            j_range = width if horizontal_wrap else width - piece_width + 1
            for j in range(j_range):
                if j >= width - piece_width + 1 and (width - j) in invalid_wrap_column:
                    continue
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

def get_random_layout(world: World, player: int, connected_edges_cache: List[str], pieces_to_place: List[Piece], options: LayoutGeneratorOptions, prio_edges: List[str], overworld_screens: Dict[int, Screen]) -> LayoutGeneratorResult:
    total_score = 0
    best_score = -1000000
    worst_score = 1000000
    best_grid_info = None

    successes = 0
    failures = 0
    run = 0
    while run < options.min_runs or (run * successes < options.target_runs_times_successes and run < options.max_runs):
        run += 1
        connected_edges = connected_edges_cache.copy()
        piece_list = pieces_to_place.copy()

        grid_info = create_empty_grid_info(random.random())
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

            result = random_place_piece(world, player, grid_info, options, pieces, len(placed_pieces) < options.first_ignore_bonus_points)

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
                valid_layout = validate_layout(world, player)
                # Clean up connected entrances and edges
                for edge_name in connected_edges:
                    if edge_name not in connected_edges_cache:
                        entrance = world.get_entrance(edge_name, player)
                        entrance.connected_region.entrances.remove(entrance)
                        entrance.connected_region = None
                        edge = world.get_owedge(edge_name, player)
                        edge.dest = None
                if not valid_layout:
                    failures += 1
                    continue
                logging.getLogger('').debug("Found valid layout with " + str(disabled_count)+ " disabled edges")
                successes += 1
                score = -disabled_count
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
                raise Exception("There should never be multiple edges with high priority in an edge set")

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
    id1 = grid[row1 % 8][col1 % 8]
    id2 = grid[row2 % 8][col2 % 8]
    if id1 == -1 or id2 == -1:
        return False
    return id1 == id2 and id1 in large_screen_ids

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def generate_random_grid_layout(world: World, player: int, connected_edges: List[str], crossed_group_b: List[int], forced_non_crossed: Set[str], forced_crossed: Set[str], crossed_limit: int, crossed_chance: float):
    """Main execution function"""
    import time

    first_ignore_bonus = 2
    if not world.owParallel[player]:
        first_ignore_bonus *= 2
        if world.owCrossed[player] == 'unrestricted':
            first_ignore_bonus *= 2
    options = LayoutGeneratorOptions(
        horizontal_wrap=False,
        vertical_wrap=False,
        large_screen_pool=False,
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
        target_runs_times_successes=5000
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

        # Make new grid containing cell IDs for the overworld map
        map_grid = copy.deepcopy(grid)
        for w in range(2):
            for i in range(8):
                for j in range(8):
                    screen_id = map_grid[w][i][j]
                    if screen_id in large_screen_ids and map_grid[w][i][(j + 1) % 8] == screen_id and map_grid[w][(i + 1) % 8][j] == screen_id and map_grid[w][(i + 1) % 8][(j + 1) % 8] == screen_id:
                        map_grid[w][i][(j + 1) % 8] = screen_id + 0x01
                        map_grid[w][(i + 1) % 8][j] = screen_id + 0x08
                        map_grid[w][(i + 1) % 8][(j + 1) % 8] = screen_id + 0x09
        world.owgrid[player] = map_grid
        world.owlayoutmap_lw[player] = {id & 0xBF: i for i, id in enumerate(sum(map_grid[0], []))}
        world.owlayoutmap_dw[player] = {id & 0xBF: i for i, id in enumerate(sum(map_grid[1], []))}

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

        if DRAW_IMAGE:
            logger.debug("Creating layout visualization...")
            try:
                from source.overworld.LayoutVisualizer import visualize_layout
                visualize_layout(grid, "visualizations", overworld_screens, large_screen_quadrant_info)
            except Exception as e:
                logger.warning(f"Warning: Could not create visualization: {e}")
    else:
        raise Exception(f"Layout generation FAILED after {result.failures} attempts and {elapsed_time:.3f} seconds")