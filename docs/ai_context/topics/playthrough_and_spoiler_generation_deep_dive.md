# Playthrough and Spoiler Generation Deep Dive

## Overview

The playthrough and spoiler generation system in the dungeon randomizer creates detailed analysis of what items are required to complete the game, generates sphere-based solution paths, and produces comprehensive spoiler logs. This system operates after all items have been placed and validates the generated seed's solvability.

## Core Components

### Main Entry Point: [`create_playthrough()`](../../../Main.py)
The primary function that orchestrates the entire playthrough generation process by creating a world copy to avoid modifying the original, identifying progression locations containing advancement items, and handling completionist mode and multiworld scenarios.

Key characteristics:
- **Creates a world copy** to avoid modifying the original during analysis
- **Identifies progression locations** that contain advancement items
- **Supports completionist mode** where all locations are considered required
- **Handles multiworld scenarios** with multiple players

### Sphere Construction Algorithm

The system builds **collection spheres** - groups of items that can be obtained together without depending on each other:

#### Phase 1: Initial Sphere Building
The algorithm builds collection spheres using [`CollectionState`](../../../BaseClasses.py) and [`state.sweep_for_events()`](../../../BaseClasses.py) with key flooding protection via [`state.not_flooding_a_key()`](../../../BaseClasses.py).

**Sphere Logic:**
- **Independence**: Items in the same sphere don't depend on each other
- **Progression**: Each sphere only depends on items from lower-numbered spheres
- **Key flooding protection**: Prevents collecting keys that would break logic
- **Event handling**: Processes location events and state changes

#### Phase 2: Requirement Pruning
Uses backwards analysis to test each item's necessity by temporarily removing items and checking [`world.can_beat_game()`](../../../BaseClasses.py). Skips pruning for completionist goals and uses [`world.clear_exp_cache()`](../../../BaseClasses.py) for fresh validation.

**Pruning Process:**
- **Backwards analysis**: Tests spheres from highest to lowest
- **Temporary removal**: Removes each item to test necessity
- **Game completion check**: Verifies if game is still beatable
- **Conservative approach**: Only removes items if game remains solvable
- **Completionist handling**: Skips pruning for completionist goals

#### Phase 3: Final Sphere Reconstruction
Rebuilds spheres based on actual dependencies using filtered reachability checks to correct ordering and validate that all required items remain obtainable after pruning.

**Final Reconstruction:**
- **Dependency resolution**: Rebuilds spheres based on actual dependencies
- **Corrects ordering**: Handles cases where pruning changed dependencies
- **Validates reachability**: Ensures all required items are still obtainable

### Key Flooding Prevention System

The [`not_flooding_a_key()`](../../../BaseClasses.py) system prevents logical inconsistencies by protecting against Swamp Palace water level changes that could break key access, ensuring important keys remain accessible.

**Flood Prevention:**
- **Swamp Palace protection**: Prevents water level changes from breaking key access
- **Key preservation**: Ensures important keys remain accessible
- **Location validation**: Checks if flood-sensitive locations are already processed

### Spoiler Class and Data Management

The [`Spoiler`](../../../BaseClasses.py) class manages all spoiler information including hashes, entrances, doors, playthrough data, paths, and locations through comprehensive data structures.

#### Spoiler Data Categories

**Settings Information:** The spoiler system supports multiple modes from minimal settings-only to full comprehensive information including all game data categories.

**Spoiler Modes:**
- **None**: No spoiler information generated
- **Settings**: Only basic configuration details
- **Semi**: Settings plus entrance/requirement information
- **Full**: Complete information including item locations
- **Debug**: Full information plus detailed debugging data

### Path Generation System

The system generates detailed paths showing how to reach each required location:

The [`get_path()`](../../../Main.py) function generates detailed paths showing region traversal and exit usage, with separate path generation per player in multiworld scenarios.

**Path Features:**
- **Region tracking**: Records path through world regions
- **Exit documentation**: Shows which exits were used
- **Player separation**: Generates paths per player in multiworld
- **Special cases**: Handles unique locations like Big Bomb Shop

### Playthrough Output Generation

The final playthrough structure organizes items by collection sphere:

The playthrough structure organizes items by collection sphere with Sphere 0 containing starting inventory and numbered spheres containing progressively accessible items with full location and item identification.

**Playthrough Structure:**
- **Sphere 0**: Starting inventory and precollected items
- **Numbered spheres**: Items that can be collected in each phase
- **Location names**: Full names including dungeon context when needed
- **Item identification**: Clear item names with player information

## Key Algorithms and Logic

### Collection State Management

The [`CollectionState`](../../../BaseClasses.py) class tracks what items have been collected:

**Progressive Item Handling:** The [`CollectionState`](../../../BaseClasses.py) class handles progressive items like swords by tracking upgrade levels and managing small key, big key, and forced key logic integration.

**Key Logic Integration:**
- **Small key tracking**: Handles per-dungeon and universal keys
- **Big key management**: Tracks dungeon big keys
- **Forced key tracking**: Manages keys placed by logic requirements

### Reachability Analysis

The system performs sophisticated reachability analysis:

**Region Traversal:** The [`update_reachable_regions()`](../../../BaseClasses.py) method performs sophisticated reachability analysis with crystal switch state handling, door logic integration, and exploration cache optimization.

**Advanced Features:**
- **Crystal switch states**: Handles blue/orange crystal switch requirements
- **Door logic**: Integrates with door shuffle and key logic
- **Dungeon exploration**: Special handling for complex dungeon layouts
- **Cache optimization**: Uses exploration cache for performance

### Multiworld Considerations

The system handles multiple players with shared item pools:

**Player Separation:** The system handles multiple players by generating separate solution paths per player while managing remote items, shared progression, and cross-player logic.

**Cross-Player Logic:**
- **Remote items**: Handles items sent between players
- **Shared progression**: Manages items that benefit multiple players
- **Individual paths**: Generates separate solution paths per player

## Error Handling and Validation

### Unreachable Item Detection

**Unreachable Item Detection:** The system detects unreachable items through accessibility checking that respects player settings, handles optional locations, provides detailed error reporting, and supports graceful degradation.

**Validation Features:**
- **Accessibility checking**: Respects player accessibility settings
- **Optional location handling**: Allows certain locations to be unreachable
- **Error reporting**: Detailed logging of unreachable items
- **Graceful degradation**: Continues generation when possible

### Game Completion Verification

**Game Completion Verification:** The [`can_beat_game()`](../../../BaseClasses.py) method validates victory conditions through goal validation, state progression simulation, and early termination when completion is possible.

**Completion Checking:**
- **Goal validation**: Checks if victory conditions are met
- **State progression**: Simulates item collection
- **Early termination**: Returns as soon as completion is possible

## Output Formats and Integration

### File Output System

The spoiler system generates multiple output formats:

**Output Formats:** The spoiler system generates both human-readable text format via [`playthrough_to_file()`](../../../BaseClasses.py) and machine-readable JSON format through [`to_json()`](../../../BaseClasses.py) for tool integration.

### Integration Points

**Main Algorithm Flow:**
1. Called after item placement is complete
2. Validates seed solvability
3. Generates solution documentation
4. Integrates with ROM patching process

**CLI Integration:** The system integrates with the main algorithm flow through conditional playthrough generation in the CLI processing pipeline.

**Output Coordination:**
- **Spoiler files**: Comprehensive text-based spoilers
- **JSON output**: Machine-readable format for tools
- **Meta information**: Settings and configuration details
- **Hash generation**: Seed verification data

## Performance Considerations

### Optimization Strategies

**World Copying:**
- **Selective copying**: Only copies necessary data structures
- **Reference preservation**: Maintains object relationships
- **Memory management**: Cleans up temporary objects

**Cache Systems:**
- **Exploration cache**: Stores dungeon exploration results
- **State caching**: Preserves intermediate collection states
- **Region caching**: Optimizes reachability calculations

**Algorithmic Efficiency:**
- **Early termination**: Stops analysis when goals are met
- **Incremental updates**: Only recalculates changed state
- **Batch processing**: Groups similar operations

## Advanced Features and Edge Cases

### Special Location Handling

**Event Locations:** The [`sweep_for_events()`](../../../BaseClasses.py) method handles special location processing with flood protection and crystal switch state management for blue/orange states and room transitions.

**Crystal Switch Logic:**
- **State tracking**: Manages blue/orange crystal switch states
- **Room transitions**: Handles state changes between rooms
- **Alternative paths**: Considers multiple crystal states

### Door Shuffle Integration

**Key Logic Coordination:** Door shuffle integration manages key logic through door state tracking (reached vs opened), key requirement validation, and dungeon-limited exploration for the dangerous key logic algorithm.

**Door State Management:**
- **Reached vs opened**: Tracks door accessibility separately from usage
- **Key requirements**: Validates key availability for door progression
- **Dungeon limits**: Restricts exploration to relevant dungeons

This playthrough and spoiler generation system ensures that every generated seed is solvable and provides players with detailed information about solution paths, making it an essential component of the randomization process.