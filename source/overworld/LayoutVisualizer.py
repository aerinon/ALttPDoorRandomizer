import logging
import os
from datetime import datetime
from typing import Dict, List
from PIL import Image, ImageDraw
from BaseClasses import Direction, OWEdge
from source.overworld.LayoutGenerator import Screen

def get_edge_lists(grid: List[List[List[int]]],
                   overworld_screens: Dict[int, Screen],
                   large_screen_quadrant_info: Dict[int, Dict]) -> Dict:
    """
    Get list of edges for each cell and direction.

    Args:
        grid: 3D list [world][row][col] containing screen IDs
        overworld_screens: Dict of screen_id -> Screen objects
        large_screen_quadrant_info: Dict of screen_id -> quadrant info for large screens

    Returns:
        Dict mapping (world, row, col, direction) -> list of edges
        Each edge has a .dest property (None if unconnected)
    """
    GRID_SIZE = 8
    edge_lists = {}

    # Large screen base IDs
    large_screen_base_ids = [0x00, 0x03, 0x05, 0x18, 0x1B, 0x1E, 0x30, 0x35,
                            0x40, 0x43, 0x45, 0x58, 0x5B, 0x5E, 0x70, 0x75]

    for world_idx in range(2):
        # Build a map of screen_id -> list of (row, col) positions for large screens
        large_screen_positions = {}
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                screen_id = grid[world_idx][row][col]
                if screen_id != -1 and screen_id in large_screen_base_ids:
                    if screen_id not in large_screen_positions:
                        large_screen_positions[screen_id] = []
                    large_screen_positions[screen_id].append((row, col))

        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                screen_id = grid[world_idx][row][col]

                if screen_id == -1:
                    # Empty cell - no edges
                    for direction in [Direction.North, Direction.South, Direction.East, Direction.West]:
                        edge_lists[(world_idx, row, col, direction)] = []
                    continue

                screen = overworld_screens.get(screen_id)
                if not screen:
                    for direction in [Direction.North, Direction.South, Direction.East, Direction.West]:
                        edge_lists[(world_idx, row, col, direction)] = []
                    continue

                is_large = screen_id in large_screen_base_ids

                if is_large:
                    # For large screens, determine which quadrant this cell is
                    # Find all positions of this large screen and determine quadrant
                    positions = large_screen_positions.get(screen_id, [(row, col)])

                    # Determine quadrant by finding relative position
                    # The quadrant is determined by which cells are adjacent
                    quadrant = determine_large_screen_quadrant(row, col, positions, GRID_SIZE)

                    # Get edges for this quadrant
                    if screen_id in large_screen_quadrant_info:
                        quad_info = large_screen_quadrant_info[screen_id]

                        for direction in [Direction.North, Direction.South, Direction.East, Direction.West]:
                            edges = quad_info.get(quadrant, {}).get(direction, [])
                            edge_lists[(world_idx, row, col, direction)] = edges
                    else:
                        # No quadrant info - no edges
                        for direction in [Direction.North, Direction.South, Direction.East, Direction.West]:
                            edge_lists[(world_idx, row, col, direction)] = []
                else:
                    # Small screen - get edges directly
                    for direction in [Direction.North, Direction.South, Direction.East, Direction.West]:
                        edges_in_dir = [e for e in screen.edges.values() if e.direction == direction]
                        edge_lists[(world_idx, row, col, direction)] = edges_in_dir

    return edge_lists

def determine_large_screen_quadrant(row: int, col: int, positions: List[tuple], grid_size: int) -> str:
    """
    Determine which quadrant (NW, NE, SW, SE) a cell is in for a large screen.
    Handles wrapping correctly by checking adjacency patterns.

    Args:
        row: Current cell row
        col: Current cell column
        positions: List of all (row, col) positions for this large screen
        grid_size: Size of the grid (8)

    Returns:
        Quadrant string: "NW", "NE", "SW", or "SE"
    """
    positions_set = set(positions)

    # Check which adjacent cells also belong to this large screen
    has_right = ((row, (col + 1) % grid_size) in positions_set)
    has_below = (((row + 1) % grid_size, col) in positions_set)
    has_left = ((row, (col - 1) % grid_size) in positions_set)
    has_above = (((row - 1) % grid_size, col) in positions_set)

    # Determine quadrant based on adjacency
    # NW: has right and below neighbors
    # NE: has left and below neighbors
    # SW: has right and above neighbors
    # SE: has left and above neighbors

    if has_right and has_below:
        return "NW"
    elif has_left and has_below:
        return "NE"
    elif has_right and has_above:
        return "SW"
    elif has_left and has_above:
        return "SE"
    else:
        raise Exception("?")

def is_crossed_edge(edge: OWEdge, overworld_screens: Dict[int, Screen]) -> bool:
    if edge.dest is None:
        return False

    source_screen = overworld_screens.get(edge.owIndex)
    dest_screen = overworld_screens.get(edge.dest.owIndex)
    return source_screen.dark_world != dest_screen.dark_world

def visualize_layout(grid: List[List[List[int]]], output_dir: str,
                     overworld_screens: Dict[int, Screen],
                     large_screen_quadrant_info: Dict[int, Dict]) -> None:
    # Constants
    GRID_SIZE = 8
    BORDER_WIDTH = 1
    OUTPUT_CELL_SIZE = 64  # Each cell in output is always 64x64 pixels

    # Load the world images
    try:
        lightworld_img = Image.open("data/overworld/lightworld.png")
        darkworld_img = Image.open("data/overworld/darkworld.png")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"World image not found: {e}. Ensure lightworld.png and darkworld.png are in the data/overworld directory.")

    # Calculate source cell size from the base images
    # Each world image is 8x8 screens, so divide by 8 to get source cell size
    img_width, _ = lightworld_img.size
    SOURCE_CELL_SIZE = img_width // GRID_SIZE  # Size of each cell in the source image

    # Calculate dimensions for the output (always based on 64x64 cells)
    world_width = GRID_SIZE * OUTPUT_CELL_SIZE
    world_height = GRID_SIZE * OUTPUT_CELL_SIZE

    # Create output image (two worlds side by side with a small gap)
    gap = 32
    output_width = world_width * 2 + gap
    output_height = world_height
    output_img = Image.new('RGB', (output_width, output_height), color='black')

    # Large screen base IDs (defined once for reuse)
    large_screen_base_ids = [0x00, 0x03, 0x05, 0x18, 0x1B, 0x1E, 0x30, 0x35,
                            0x40, 0x43, 0x45, 0x58, 0x5B, 0x5E, 0x70, 0x75]

    # Process both worlds
    for world_idx in range(2):
        x_offset = 0 if world_idx == 0 else (world_width + gap)

        # Build a map of screen_id -> list of (row, col) positions for large screens
        large_screen_positions = {}
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                screen_id = grid[world_idx][row][col]
                if screen_id != -1 and screen_id in large_screen_base_ids:
                    if screen_id not in large_screen_positions:
                        large_screen_positions[screen_id] = []
                    large_screen_positions[screen_id].append((row, col))

        # Process each cell in the grid individually
        # This handles wrapped large screens correctly by drawing each quadrant separately
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                screen_id = grid[world_idx][row][col]

                if screen_id == -1:
                    # Empty cell - fill with black (already black from initialization)
                    continue

                is_large = screen_id in large_screen_base_ids

                # Calculate source position in the world image
                source_row = (screen_id % 0x40) >> 3
                source_col = screen_id % 0x08
                world_img = lightworld_img if screen_id < 0x40 else darkworld_img

                if is_large:
                    # For large screens, determine which quadrant this cell represents
                    positions = large_screen_positions.get(screen_id, [(row, col)])
                    quadrant = determine_large_screen_quadrant(row, col, positions, GRID_SIZE)

                    # Map quadrant to source offset within the 2x2 large screen
                    quadrant_offsets = {
                        "NW": (0, 0),
                        "NE": (1, 0),
                        "SW": (0, 1),
                        "SE": (1, 1)
                    }
                    q_col_offset, q_row_offset = quadrant_offsets[quadrant]

                    # Calculate source position for this quadrant
                    source_x = (source_col + q_col_offset) * SOURCE_CELL_SIZE
                    source_y = (source_row + q_row_offset) * SOURCE_CELL_SIZE

                    # Crop single cell from source (the specific quadrant)
                    cropped = world_img.crop((
                        source_x,
                        source_y,
                        source_x + SOURCE_CELL_SIZE,
                        source_y + SOURCE_CELL_SIZE
                    ))
                else:
                    # Small screen (1x1)
                    source_x = source_col * SOURCE_CELL_SIZE
                    source_y = source_row * SOURCE_CELL_SIZE

                    # Crop single cell from source
                    cropped = world_img.crop((
                        source_x,
                        source_y,
                        source_x + SOURCE_CELL_SIZE,
                        source_y + SOURCE_CELL_SIZE
                    ))

                # Resize to output size (64x64 pixels)
                resized = cropped.resize(
                    (OUTPUT_CELL_SIZE, OUTPUT_CELL_SIZE),
                    Image.LANCZOS
                )

                # Paste into output at grid position
                dest_x = x_offset + col * OUTPUT_CELL_SIZE
                dest_y = row * OUTPUT_CELL_SIZE
                output_img.paste(resized, (dest_x, dest_y))

    edge_lists = get_edge_lists(grid, overworld_screens, large_screen_quadrant_info)

    # Draw borders and edge connection indicators after all screens are placed
    draw = ImageDraw.Draw(output_img)

    # Size of the indicator squares
    INDICATOR_SIZE = 12

    for world_idx in range(2):
        x_offset = 0 if world_idx == 0 else (world_width + gap)

        # Build large screen positions map for this world
        large_screen_positions = {}
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                screen_id = grid[world_idx][row][col]
                if screen_id != -1 and screen_id in large_screen_base_ids:
                    if screen_id not in large_screen_positions:
                        large_screen_positions[screen_id] = []
                    large_screen_positions[screen_id].append((row, col))

        # Draw borders for each cell
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                screen_id = grid[world_idx][row][col]

                if screen_id == -1:
                    continue

                is_large = screen_id in large_screen_base_ids

                dest_x = x_offset + col * OUTPUT_CELL_SIZE
                dest_y = row * OUTPUT_CELL_SIZE

                if is_large:
                    # For large screens, determine which quadrant this cell is
                    positions = large_screen_positions.get(screen_id, [(row, col)])
                    quadrant = determine_large_screen_quadrant(row, col, positions, GRID_SIZE)

                    # Draw border only on the outer edges of the large screen
                    # (not on internal edges between quadrants)
                    # NW: draw top and left borders
                    # NE: draw top and right borders
                    # SW: draw bottom and left borders
                    # SE: draw bottom and right borders

                    if quadrant in ["NW", "NE"]:
                        # Draw top border
                        draw.line([(dest_x, dest_y), (dest_x + OUTPUT_CELL_SIZE - 1, dest_y)], fill='black', width=BORDER_WIDTH)
                    if quadrant in ["SW", "SE"]:
                        # Draw bottom border
                        draw.line([(dest_x, dest_y + OUTPUT_CELL_SIZE - 1), (dest_x + OUTPUT_CELL_SIZE - 1, dest_y + OUTPUT_CELL_SIZE - 1)], fill='black', width=BORDER_WIDTH)
                    if quadrant in ["NW", "SW"]:
                        # Draw left border
                        draw.line([(dest_x, dest_y), (dest_x, dest_y + OUTPUT_CELL_SIZE - 1)], fill='black', width=BORDER_WIDTH)
                    if quadrant in ["NE", "SE"]:
                        # Draw right border
                        draw.line([(dest_x + OUTPUT_CELL_SIZE - 1, dest_y), (dest_x + OUTPUT_CELL_SIZE - 1, dest_y + OUTPUT_CELL_SIZE - 1)], fill='black', width=BORDER_WIDTH)
                else:
                    # Small screen - draw border around single cell
                    draw.rectangle(
                        [dest_x, dest_y, dest_x + OUTPUT_CELL_SIZE - 1, dest_y + OUTPUT_CELL_SIZE - 1],
                        outline='black',
                        width=BORDER_WIDTH
                    )

        # Draw edge connection indicators for each cell
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                screen_id = grid[world_idx][row][col]
                if screen_id == -1:
                    continue

                dest_x = x_offset + col * OUTPUT_CELL_SIZE
                dest_y = row * OUTPUT_CELL_SIZE

                # Draw indicator for each direction (only if edges exist)
                # Use bright colors for visibility
                GREEN = (0, 255, 0)     # Bright green
                YELLOW = (255, 255, 0)  # Bright yellow
                RED = (255, 0, 0)       # Bright red

                # North indicators - positioned based on edge midpoint
                north_edges = edge_lists.get((world_idx, row, col, Direction.North), [])
                if north_edges:
                    north_y = dest_y  # Touch the top border

                    for edge in north_edges:
                        # For north/south edges, midpoint gives the X coordinate
                        # Take midpoint modulo 0x0200, range 0-0x01FF maps to full side
                        midpoint = edge.midpoint % 0x0200
                        # Map from game coordinate range to pixel position
                        edge_x_offset = (midpoint * OUTPUT_CELL_SIZE) // 0x0200
                        edge_x = dest_x + edge_x_offset - INDICATOR_SIZE // 2

                        edge_color = GREEN if edge.dest is not None else YELLOW if any(e for e in north_edges if e.dest) else RED
                        draw.rectangle(
                            [edge_x, north_y, edge_x + INDICATOR_SIZE - 1, north_y + INDICATOR_SIZE - 1],
                            fill=edge_color,
                            outline='black'
                        )

                        # Draw diagonal cross if edge crosses between worlds
                        if edge.dest is not None and is_crossed_edge(edge, overworld_screens):
                            draw.line(
                                [edge_x, north_y, edge_x + INDICATOR_SIZE - 1, north_y + INDICATOR_SIZE - 1],
                                fill='black',
                                width=1
                            )
                            draw.line(
                                [edge_x + INDICATOR_SIZE - 1, north_y, edge_x, north_y + INDICATOR_SIZE - 1],
                                fill='black',
                                width=1
                            )

                # South indicators - positioned based on edge midpoint
                south_edges = edge_lists.get((world_idx, row, col, Direction.South), [])
                if south_edges:
                    south_y = dest_y + OUTPUT_CELL_SIZE - INDICATOR_SIZE  # Touch the bottom border

                    for edge in south_edges:
                        # For north/south edges, midpoint gives the X coordinate
                        # Take midpoint modulo 0x0200, range 0-0x01FF maps to full side
                        midpoint = edge.midpoint % 0x0200
                        # Map from game coordinate range to pixel position
                        edge_x_offset = (midpoint * OUTPUT_CELL_SIZE) // 0x0200
                        edge_x = dest_x + edge_x_offset - INDICATOR_SIZE // 2

                        edge_color = GREEN if edge.dest is not None else YELLOW if any(e for e in south_edges if e.dest) else RED
                        draw.rectangle(
                            [edge_x, south_y, edge_x + INDICATOR_SIZE - 1, south_y + INDICATOR_SIZE - 1],
                            fill=edge_color,
                            outline='black'
                        )

                        # Draw diagonal cross if edge crosses between worlds
                        if edge.dest is not None and is_crossed_edge(edge, overworld_screens):
                            draw.line(
                                [edge_x, south_y, edge_x + INDICATOR_SIZE - 1, south_y + INDICATOR_SIZE - 1],
                                fill='black',
                                width=1
                            )
                            draw.line(
                                [edge_x + INDICATOR_SIZE - 1, south_y, edge_x, south_y + INDICATOR_SIZE - 1],
                                fill='black',
                                width=1
                            )

                # West indicators - positioned based on edge midpoint
                west_edges = edge_lists.get((world_idx, row, col, Direction.West), [])
                if west_edges:
                    west_x = dest_x  # Touch the left border

                    for edge in west_edges:
                        # For west/east edges, midpoint gives the Y coordinate
                        # Take midpoint modulo 0x0200, range 0-0x01FF maps to full side
                        midpoint = edge.midpoint % 0x0200
                        # Map from game coordinate range to pixel position
                        edge_y_offset = (midpoint * OUTPUT_CELL_SIZE) // 0x0200
                        edge_y = dest_y + edge_y_offset - INDICATOR_SIZE // 2

                        edge_color = GREEN if edge.dest is not None else YELLOW if any(e for e in west_edges if e.dest) else RED
                        draw.rectangle(
                            [west_x, edge_y, west_x + INDICATOR_SIZE - 1, edge_y + INDICATOR_SIZE - 1],
                            fill=edge_color,
                            outline='black'
                        )

                        # Draw diagonal cross if edge crosses between worlds
                        if edge.dest is not None and is_crossed_edge(edge, overworld_screens):
                            draw.line(
                                [west_x, edge_y, west_x + INDICATOR_SIZE - 1, edge_y + INDICATOR_SIZE - 1],
                                fill='black',
                                width=1
                            )
                            draw.line(
                                [west_x + INDICATOR_SIZE - 1, edge_y, west_x, edge_y + INDICATOR_SIZE - 1],
                                fill='black',
                                width=1
                            )

                # East indicators - positioned based on edge midpoint
                east_edges = edge_lists.get((world_idx, row, col, Direction.East), [])
                if east_edges:
                    east_x = dest_x + OUTPUT_CELL_SIZE - INDICATOR_SIZE  # Touch the right border

                    for edge in east_edges:
                        # For west/east edges, midpoint gives the Y coordinate
                        # Take midpoint modulo 0x0200, range 0-0x01FF maps to full side
                        midpoint = edge.midpoint % 0x0200
                        # Map from game coordinate range to pixel position
                        edge_y_offset = (midpoint * OUTPUT_CELL_SIZE) // 0x0200
                        edge_y = dest_y + edge_y_offset - INDICATOR_SIZE // 2

                        edge_color = GREEN if edge.dest is not None else YELLOW if any(e for e in east_edges if e.dest) else RED
                        draw.rectangle(
                            [east_x, edge_y, east_x + INDICATOR_SIZE - 1, edge_y + INDICATOR_SIZE - 1],
                            fill=edge_color,
                            outline='black'
                        )

                        # Draw diagonal cross if edge crosses between worlds
                        if edge.dest is not None and is_crossed_edge(edge, overworld_screens):
                            draw.line(
                                [east_x, edge_y, east_x + INDICATOR_SIZE - 1, edge_y + INDICATOR_SIZE - 1],
                                fill='black',
                                width=1
                            )
                            draw.line(
                                [east_x + INDICATOR_SIZE - 1, edge_y, east_x, edge_y + INDICATOR_SIZE - 1],
                                fill='black',
                                width=1
                            )

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"layout_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)

    # Save the image
    output_img.save(filepath, "PNG")
    logging.getLogger('').info(f"Layout visualization saved to {filepath}")