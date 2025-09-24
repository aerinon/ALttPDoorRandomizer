# Dungeon Generation Algorithms

Dungeon generation is done through a series of classes to process and create dungeons. The main classes are:

* `DungeonGenLocalSearch` for assignment of sectors to a dungeon
* `DungeonGenTransitivity` for validation for a given dungeon
* `DungeonStitcherV2` for realization of a dungeon by connecting doors

# DungeonGenLocalSearch

`DungeonGenLocalSearch` is a sophisticated dungeon generation system that distributes dungeon sectors across multiple dungeons while maintaining game balance and logical connectivity.

## Core Purpose

The main function `main_dungeon_builders` takes pools of dungeons, sectors, and portals, then assigns sectors to dungeons in a balanced way that respects game constraints and ensures dungeons remain solvable.

## Key Components

### Dungeon Builder Assignment
- Creates `DungeonBuilder` objects for each dungeon in the pool
- Handles special dungeon splits (Skull Woods, Desert Palace, Hyrule Castle) that can be divided into Front/Back or Sewers/Dungeon variants
- Assigns portal sectors and mandatory sectors (like boss rooms) to appropriate dungeons

### Balancing System (`Balance` class)
The system tracks multiple balance criteria for each dungeon:
- **Polarity**: North/South and East/West door balance to prevent impossible layouts
- **Crystal Balance**: Blue barriers must have matching crystal switches
- **Portal Balance**: Ensures proper portal distribution and connectivity
- **Location Balance**: : Ensures dungeons with big key requirements have at least one non-big-key location accessible
- **Branching**: Dead ends vs branches ratio to ensure connectivity - insufficient branches mean dead ends will be paired together and become unreachable, while extra branches are acceptable (they can form loops)
- **Transitivity**: Uses `DungeonGenTransitivity` to verify all doors can be validly connected

### Local Search Algorithm
1. **Initial Assignment**: Randomly assigns sectors to dungeons using weighted selection
2. **Balance Detection**: Identifies dungeons that violate balance constraints
3. **Constraint Prioritization**: Fixes balance violations in order of severity (crystal switches, portal distribution, location requirements, branching, polarity, transitivity)
4. **Greedy Selection**: For each constraint type, finds the move that minimizes the "charge" (total constraint violations)
5. **Fallback to Random**: Only resorts to random moves when polarity constraints cannot be resolved deterministically

### Optimization Features
- **Forced Assignments**: Some sectors must go to specific dungeons (boss rooms, special mechanics)
- **Recent Move Tracking**: Prevents oscillation by avoiding recently moved sectors

### Customization Features
- **Restriction Lists**: Sectors can be limited to certain dungeon sets
- **Exclusion Lists**: Sectors can be banned from certain dungeons
- **Biased Generation**: Can pack specific dungeons with more sectors when specified

### Transitivity Integration
The system uses `DungeonGenTransitivity` to verify that proposed sector arrangements can form valid door connections. This is the most expensive check, so it's performed last after other balance criteria are met.

The algorithm essentially solves a complex constraint satisfaction problem, ensuring that randomly shuffled dungeon layouts remain both balanced and completable according to the game's rules.

# DungeonGenTransitivity

`DungeonGenTransitivity` is a complex dungeon generation system that uses graph theory and constraint satisfaction to determine if doors in dungeon sectors can be validly connected while respecting various game constraints.

## Core Purpose

The main function `do_transitivity_check` verifies whether all outstanding doors in a list of dungeon sectors can be connected in a way that satisfies all constraints and maintains proper game logic.

## Key Components

### Transitivity Class
- Maintains the state of door connections during the search process
- Tracks remaining doors, satisfied/unsatisfied constraints, and connection mappings
- Uses branch-and-bound with pruning to explore connection possibilities while avoiding impossible states

### Constraint Types
The system handles multiple constraint types:
- **MustEnter**: Certain doors must be used to access areas
- **DeadEnd**: Terminal paths that must connect appropriately
- **Crystal**: Color-coded barriers (blue/orange) that require crystal switches
- **Portal**: Traversal-only connections between areas
- **Special**: Custom constraints (like Ice Cross mechanics)

### Connection Logic
1. **Door Matching**: Doors are matched based on compatible "hanger" and "hook" types
2. **Reachability Propagation**: When doors connect, the system propagates crystal states and determines newly reachable areas
3. **Constraint Satisfaction**: Each connection attempt checks if constraints are satisfied or become impossible to satisfy

### Search Algorithm

- Uses depth-first search with constraint propagation to explore possible door connection combinations
- Maintains a search tree where each node represents a partial door connection assignment
- Detects forced connections (when only one valid option exists)
- Performs cycle detection to prevent impossible loops
- Balances branches vs dead-ends to ensure solvable layouts


### Key Optimizations
- **Early Termination**: Stops immediately when impossible states are detected
- **State Deduplication**: Avoids revisiting identical connection states
- **Constraint Prioritization**: Focuses on satisfying critical constraints first
- **Greedy Mode**: Faster search mode that explores exactly one set of choices rather than all alternatives. Often a greedy solution is easy to find so it is useful to check for a greedy solution first. 

The system essentially ensures that randomly generated dungeon layouts remain logically traversable and solvable according to the game's rules.

# DungeonStitcherV2

`DungeonStitcherV2` is a sophisticated dungeon generation system that takes pre-built dungeon sectors and connects them into complete dungeons by intelligently linking doors while respecting game constraints. While DungeonGenTransitivity ensures some valid connection exists, DungeonStitcherV2 finds a specific random valid connection for actual dungeon generation.

## Core Purpose

The main function `create_dungeon` takes a `DungeonBuilder` containing multiple sectors and stitches them together by:
1. Determining valid door connections through `generate_dungeon_find_proposal`
2. Physically connecting the doors to create a unified dungeon layout
3. Merging all sectors into a single master sector

## Key Components

### Proposal Generation System
The heart of the system is `generate_dungeon_find_proposal`, which:
- **Creates Door Mappings**: Maps doors by compatible hook types (North↔South, East↔West, Stairs↔Stairs)
- **Generates Random Proposals**: Uses `create_random_proposal` to randomly pair doors of opposite types
- **Validates Connectivity**: Uses `explore_proposal` to simulate player traversal and ensure all regions are reachable
- **Iterative Refinement**: Uses `modify_proposal` to adjust connections when validation fails

### Portal Assignment System
`determine_entrance_regions` handles dungeon entrances:
- **Portal Categorization**: Separates destination portals from regular entrances
- **Candidate Filtering**: Uses `find_portal_candidates` to find valid doors based on:
    - Vanilla trap compatibility
    - Big key shuffle requirements
    - Standard mode restrictions
    - Rupee bow limitations
- **Transitivity Checking**: Ensures portal assignments don't break dungeon connectivity

### Exploration and Validation
The system uses `ExplorationState` to simulate player movement:
- **Crystal State Tracking**: Manages blue/orange crystal barrier states
- **Key Logic**: Tracks big key availability and small key usage
- **Region Visitation**: Records which regions can be reached under different conditions
- **Door Availability**: Maintains lists of traversable, blocked, and event-gated doors

### Connection Algorithms
Two main exploration functions handle different scenarios:
- **`extend_reachable_state_lenient`**: For initial proposal validation (more permissive)
- **`extend_reachable_state_improved`**: For detailed connectivity analysis (stricter)

### Path Validation System
`valid_paths` ensures critical game objectives remain achievable:
- **Boss Access**: Verifies boss rooms can be reached
- **Special Requirements**: Handles dungeon-specific mechanics (Thieves' Town attic, Hyrule Castle throne room)
- **Drop Connections**: Manages hole-based connections between areas

### Key Features
- **Hook-Based Matching**: Doors connect based on compatible directional types
- **Crystal Barrier Logic**: Handles blue/orange switch puzzles
- **Big Key Validation**: Ensures big key doors have proper access patterns
- **Trap Door Handling**: Special logic for vanilla vs randomized trap doors
- **Decoupled Door Support**: Can handle one-way connections when enabled
- **Hash-Based Deduplication**: Prevents infinite loops by tracking tried configurations

The system essentially solves a complex constraint satisfaction problem, ensuring that randomly connected dungeon layouts remain logically traversable while maintaining proper game balance and mechanics. It uses iterative refinement with backtracking to find valid solutions when initial random proposals fail connectivity tests.