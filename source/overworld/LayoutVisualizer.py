import logging
import os
from datetime import datetime
from typing import Dict, List
from PIL import Image, ImageDraw
from BaseClasses import Direction, OWEdge
from source.overworld.LayoutGenerator import Screen, get_screen_id_from_cell

def get_quadrant_from_cell_id(cell_id: int, screen_id: int) -> str:
    offset = (cell_id & 0xBF) - (screen_id & 0xBF)
    if offset == 0x00:
        return "NW"
    elif offset == 0x01:
        return "NE"
    elif offset == 0x08:
        return "SW"
    else:
        return "SE"

def get_edge_lists(grid: List[List[List[int]]],
                   overworld_screens: Dict[int, Screen],
                   large_screen_quadrant_info: Dict[int, Dict]) -> Dict:
    """
    Get list of edges for each cell and direction.

    Args:
        grid: 3D list [world][row][col] containing cell IDs
        overworld_screens: Dict of screen_id -> Screen objects
        large_screen_quadrant_info: Dict of screen_id -> quadrant info for large screens

    Returns:
        Dict mapping (world, row, col, direction) -> list of edges
        Each edge has a .dest property (None if unconnected)
    """
    GRID_SIZE = 8
    edge_lists = {}

    for world_idx in range(2):
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                cell_id = grid[world_idx][row][col]

                if cell_id == -1:
                    # Empty cell - no edges
                    for direction in [Direction.North, Direction.South, Direction.East, Direction.West]:
                        edge_lists[(world_idx, row, col, direction)] = []
                    continue

                screen_id = get_screen_id_from_cell(cell_id)
                screen = overworld_screens.get(screen_id)
                if not screen:
                    for direction in [Direction.North, Direction.South, Direction.East, Direction.West]:
                        edge_lists[(world_idx, row, col, direction)] = []
                    continue

                if screen.big:
                    # For large screens, determine quadrant from cell ID
                    quadrant = get_quadrant_from_cell_id(cell_id, screen_id)

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

def is_crossed_edge(edge: OWEdge, overworld_screens: Dict[int, Screen]) -> bool:
    if edge.dest is None:
        return False

    source_screen = overworld_screens.get(edge.owIndex)
    dest_screen = overworld_screens.get(edge.dest.owIndex)
    return source_screen.dark_world != dest_screen.dark_world

def are_large_screen_cells_connected(cell_id1: int, cell_id2: int, quadrant1: str, quadrant2: str, direction: str) -> bool:
    """
    Check if two cells of a large screen are connected (should have no border between them).

    For cells to be connected:
    1. They must be from the same large screen (same base screen ID)
    2. Their quadrants must be adjacent in the expected direction

    Args:
        cell_id1: Cell ID of the first cell
        cell_id2: Cell ID of the second cell
        quadrant1: Quadrant of the first cell ("NW", "NE", "SW", "SE")
        quadrant2: Quadrant of the second cell
        direction: Direction from cell1 to cell2 ("east", "south")

    Returns:
        True if the cells should have no border between them
    """
    # Must be from the same large screen
    screen_id1 = get_screen_id_from_cell(cell_id1)
    screen_id2 = get_screen_id_from_cell(cell_id2)
    if screen_id1 != screen_id2:
        return False

    # Check if quadrants are properly adjacent
    if direction == "east":
        # For east connection: NW->NE or SW->SE
        return (quadrant1 == "NW" and quadrant2 == "NE") or (quadrant1 == "SW" and quadrant2 == "SE")
    elif direction == "south":
        # For south connection: NW->SW or NE->SE
        return (quadrant1 == "NW" and quadrant2 == "SW") or (quadrant1 == "NE" and quadrant2 == "SE")

    return False

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

    # Process both worlds
    for world_idx in range(2):
        x_offset = 0 if world_idx == 0 else (world_width + gap)

        # Process each cell in the grid individually
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                cell_id = grid[world_idx][row][col]

                if cell_id == -1:
                    # Empty cell - fill with black (already black from initialization)
                    continue

                screen_id = get_screen_id_from_cell(cell_id)
                screen = overworld_screens.get(screen_id)
                if not screen:
                    continue

                is_large = screen.big

                # Calculate source position in the world image based on cell_id
                # For large screens, cell_id already encodes the quadrant position
                source_row = (cell_id % 0x40) >> 3
                source_col = cell_id % 0x08
                world_img = lightworld_img if cell_id < 0x40 else darkworld_img

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

        # Draw borders for each cell
        # For large screens, only draw borders where cells are not connected
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                cell_id = grid[world_idx][row][col]

                if cell_id == -1:
                    continue

                screen_id = get_screen_id_from_cell(cell_id)
                screen = overworld_screens.get(screen_id)
                if not screen:
                    continue

                is_large = screen.big

                dest_x = x_offset + col * OUTPUT_CELL_SIZE
                dest_y = row * OUTPUT_CELL_SIZE

                if is_large:
                    quadrant = get_quadrant_from_cell_id(cell_id, screen_id)

                    # Check each border direction
                    # Top border: draw if this is a north quadrant OR if the cell above is not connected
                    draw_top = True
                    if quadrant in ["SW", "SE"]:
                        # Check if cell above is connected
                        above_row = (row - 1) % GRID_SIZE
                        above_cell_id = grid[world_idx][above_row][col]
                        if above_cell_id != -1:
                            above_screen_id = get_screen_id_from_cell(above_cell_id)
                            above_screen = overworld_screens.get(above_screen_id)
                            if above_screen and above_screen.big:
                                above_quadrant = get_quadrant_from_cell_id(above_cell_id, above_screen_id)
                                if are_large_screen_cells_connected(above_cell_id, cell_id, above_quadrant, quadrant, "south"):
                                    draw_top = False

                    # Bottom border: draw if this is a south quadrant OR if the cell below is not connected
                    draw_bottom = True
                    if quadrant in ["NW", "NE"]:
                        # Check if cell below is connected
                        below_row = (row + 1) % GRID_SIZE
                        below_cell_id = grid[world_idx][below_row][col]
                        if below_cell_id != -1:
                            below_screen_id = get_screen_id_from_cell(below_cell_id)
                            below_screen = overworld_screens.get(below_screen_id)
                            if below_screen and below_screen.big:
                                below_quadrant = get_quadrant_from_cell_id(below_cell_id, below_screen_id)
                                if are_large_screen_cells_connected(cell_id, below_cell_id, quadrant, below_quadrant, "south"):
                                    draw_bottom = False

                    # Left border: draw if this is a west quadrant OR if the cell to the left is not connected
                    draw_left = True
                    if quadrant in ["NE", "SE"]:
                        # Check if cell to the left is connected
                        left_col = (col - 1) % GRID_SIZE
                        left_cell_id = grid[world_idx][row][left_col]
                        if left_cell_id != -1:
                            left_screen_id = get_screen_id_from_cell(left_cell_id)
                            left_screen = overworld_screens.get(left_screen_id)
                            if left_screen and left_screen.big:
                                left_quadrant = get_quadrant_from_cell_id(left_cell_id, left_screen_id)
                                if are_large_screen_cells_connected(left_cell_id, cell_id, left_quadrant, quadrant, "east"):
                                    draw_left = False

                    # Right border: draw if this is an east quadrant OR if the cell to the right is not connected
                    draw_right = True
                    if quadrant in ["NW", "SW"]:
                        # Check if cell to the right is connected
                        right_col = (col + 1) % GRID_SIZE
                        right_cell_id = grid[world_idx][row][right_col]
                        if right_cell_id != -1:
                            right_screen_id = get_screen_id_from_cell(right_cell_id)
                            right_screen = overworld_screens.get(right_screen_id)
                            if right_screen and right_screen.big:
                                right_quadrant = get_quadrant_from_cell_id(right_cell_id, right_screen_id)
                                if are_large_screen_cells_connected(cell_id, right_cell_id, quadrant, right_quadrant, "east"):
                                    draw_right = False

                    # Draw the borders
                    if draw_top:
                        draw.line([(dest_x, dest_y), (dest_x + OUTPUT_CELL_SIZE - 1, dest_y)], fill='black', width=BORDER_WIDTH)
                    if draw_bottom:
                        draw.line([(dest_x, dest_y + OUTPUT_CELL_SIZE - 1), (dest_x + OUTPUT_CELL_SIZE - 1, dest_y + OUTPUT_CELL_SIZE - 1)], fill='black', width=BORDER_WIDTH)
                    if draw_left:
                        draw.line([(dest_x, dest_y), (dest_x, dest_y + OUTPUT_CELL_SIZE - 1)], fill='black', width=BORDER_WIDTH)
                    if draw_right:
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
                cell_id = grid[world_idx][row][col]
                if cell_id == -1:
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