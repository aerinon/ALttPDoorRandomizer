# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ALttPDoorRandomizer** is a sophisticated dungeon and door randomizer for *The Legend of Zelda: A Link to the Past* (SNES). It extends the standard ALTTP Entrance Randomizer with advanced dungeon shuffling capabilities that can rearrange dungeon interiors at the door and sector level.

- **Repository**: https://github.com/aerinon/ALttPDoorRandomizer
- **Python Version**: 3.10+
- **Current Branch**: DoorDevUnstable (dev branch: NewGeneration)
- **Discord**: #door-rando and #bug-reports channels at ALTTP Randomizer discord

## Development Commands

### Running the Randomizer
```bash
# CLI interface
python DungeonRandomizer.py

# GUI interface
python Gui.py

```

### Dependencies
```bash
# Install platform-specific dependencies
python resources/ci/common/local_install.py

# For multiworld server/client
# Run the same command to install multiworld dependencies
```

### Testing
```bash
# Run test suite
python TestSuite.py

# Run test suite with specific door shuffle mode
python TestSuite.py --dr basic --count 10 --tense 2

# Individual test files (unittest-based)
python -m pytest test/
python -m pytest test/dungeons/TestDarkPalace.py
```

### ROM Generation
```bash
# Basic door shuffle seed
python DungeonRandomizer.py --doorShuffle crossed --intensity 2

# Suppress ROM output (for testing)
python DungeonRandomizer.py --suppress_rom --spoiler none

# Create BPS patch
python DungeonRandomizer.py --bps
```

## Architecture Overview

### Generation Pipeline

The randomizer follows this high-level flow (orchestrated in `Main.py`):

1. **World Setup** → Initialize World object, parse settings, set seed
2. **Region Creation** → Build game regions, locations, entrances (`Regions.py`)
3. **Dungeon Structure** → Create dungeon objects and rooms (`Dungeons.py`, `RoomData.py`)
4. **Door/Entrance Shuffling** → Shuffle dungeon interiors and/or overworld entrances
5. **Logic Rules** → Set access requirements for all locations (`Rules.py`)
6**Item Placement** → Generate item pool and place items with logic constraints (`Fill.py`)
7. **ROM Patching** → Apply changes to base ROM (`Rom.py`)
8. **Output** → Generate ROM file, spoiler log, and/or multiworld data

### Core Data Structures (BaseClasses.py)

- **World**: Container for all game state, regions, dungeons, items, and settings
- **Region**: Geographic area with locations and exits
- **Location**: Item placement spot with access rules
- **Item**: Game items with advancement/priority flags
- **Entrance**: Connections between regions with conditional access
- **CollectionState**: Tracks player's collected items for logic evaluation

### Dungeon Generation System

The dungeon shuffling system uses a three-stage algorithm:

#### 1. DungeonGenLocalSearch (source/dungeon/DungeonGenLocalSearch.py)
**Purpose**: Assigns dungeon sectors to dungeons using constraint satisfaction

**Balancing Constraints**:
- **Polarity**: North/South and East/West door balance
- **Crystal Balance**: Blue/orange barriers must have matching switches
- **Portal Balance**: Entrance distribution
- **Location Balance**: Ensures dungeons have accessible non-big-key locations
- **Branching**: Dead ends vs branches ratio (insufficient branches = unreachable areas)
- **Transitivity**: Validates that doors can actually connect

**Algorithm**: Local search with greedy constraint satisfaction, prioritizing crystal switches → portals → locations → branching → polarity → transitivity

#### 2. DungeonGenTransitivity (source/dungeon/DungeonGenTransitivity.py)
**Purpose**: Validates that door connections are possible for a given sector assignment

**Key Features**:
- Verifies all doors can be validly connected (e.g., North↔South, East↔West, Stairs↔Stairs)
- Propagates crystal switch states through connections
- Detects forced connections and impossible layouts
- Uses depth-first search with constraint propagation
- Handles special mechanics (portals, crystal barriers, special rooms)

#### 3. DungeonStitcherV2 (source/dungeon/DungeonStitcherV2.py)
**Purpose**: Realizes actual door connections from validated sector assignments

**Key Features**:
- Generates random valid door pairings
- Assigns portal connections (dungeon entrances)
- Simulates player traversal to verify connectivity
- Manages crystal barrier state propagation

### Key Logic Components

**Rules.py** (~7000 lines): Sets logical requirements for accessing locations
- Supports multiple logic modes: noglitches, owglitches, hybridglitches, nologic
- Handles multiple key logic algorithms: partial, strict, dangerous, experimental
- Manages dungeon-specific access rules and boss requirements

**Fill.py** (~2000 lines): Item placement algorithms
- **Balanced**: Random distribution
- **Vanilla Fill**: Attempts vanilla item locations when possible
- **Major Location Restriction**: Major items → major locations
- **Dungeon Restriction**: Major items → dungeons
- **District Restriction**: Items distributed by geographic region

**KeyPlacement.py** / **NewKeyLogic.py**: Advanced key door logic
- Handles small key placement with multiple satisfiability algorithms
- Prevents self-locking situations
- Manages big key placement rules
- Validates minimum key requirements for dungeon completion

### Source Module Organization

```
source/
├── dungeon/          # Dungeon generation algorithms and key logic
├── overworld/        # Entrance shuffling (EntranceShuffle2.py)
├── item/             # Item placement utilities (FillUtil.py, District.py)
├── enemizer/         # Enemy randomization system
├── gui/              # GUI components (tkinter-based)
├── rom/              # ROM patching utilities
├── classes/          # Utility classes (BabelFish, CustomSettings)
├── meta/             # Metadata and build tools
└── limited/          # Limited run coordination
```

### Important Files by Size/Complexity

- **DoorShuffle.py** (~8500 lines): Door shuffling orchestration
- **Rules.py** (~7000 lines): Location access logic
- **EnemyList.py** (~6000 lines): Enemy definitions
- **Doors.py** (~5500 lines): Door object definitions
- **Rom.py** (~5500 lines): ROM patching
- **Regions.py** (~5000 lines): World region creation
- **DungeonGenerator.py** (~5000 lines): Legacy dungeon generation
- **EntranceShuffle2.py** (~5000 lines): Entrance shuffling logic
- **BaseClasses.py** (~4000 lines): Core data structures
- **KeyDoorShuffle.py** (~3500 lines): Key door logic
- **PotShuffle.py** (~3500 lines): Pot randomization

## Key Concepts

### Door Shuffle Modes
- **Vanilla**: No shuffling
- **Basic**: Shuffle within each dungeon
- **Partitioned**: Shuffle in pools (Light World, Early Dark World, Late Dark World)
- **Crossed**: Full shuffle between all dungeons

### Intensity Levels
- **Level 1**: Normal doors and spiral staircases
- **Level 2**: + open edges and straight staircases
- **Level 3**: + dungeon lobbies

### Key Shuffle Modes
- **In Dungeon** (keyshuffle=none): Keys restricted to their dungeon
- **Randomized** (keyshuffle=wild): Keys can be anywhere
- **Universal** (keyshuffle=universal): Keys work in any dungeon

### Fill Algorithms (--algorithm)
See Fill.py for implementation details. The algorithm affect where item may be placed.

### Logic Modes
- **noglitches**: Standard logic
- **owglitches**: Overworld glitches (OOB, clips, superbunny)
- **hybridglitches**: + major underworld glitches (not compatible with door shuffle)
- **nologic**: No logical constraints

## Testing Strategy

Tests verify location accessibility with various item combinations:
- **test/dungeons/**: Per-dungeon location access tests
- **test/vanilla/**: Vanilla world logic tests
- **test/owg/**: Overworld glitch logic tests
- **test/inverted/**: Inverted mode tests
- **TestBase.py**: Base test class with utility methods

Use `TestSuite.py` for batch generation testing across modes (Open/Standard/Inverted) and settings.

## Important Development Notes

### Starting Items & Special Items
- **Mirror Scroll**: Dungeon-only mirror (starting item in door shuffle)
- **Bomb Bag**: Optional item that gates bomb usage
- **Pseudo Boots**: Allows dashing but gates certain sequence breaks

### Branch Structure
- **DoorDev**: Main development branch (use for PRs)
- **DoorDevUnstable**: Current working branch
- **Dev/Master**: Do NOT use for PRs

### Git Workflow
Recent commits show work on:
- Limited run coordination
- Custom rooms support
- Key logic improvements (transitivity, portal checks, placement rules)
- Isolated region detection fixes
- Big key placement satisfiability

### Documentation Resources
- **Algorithm.md**: Detailed dungeon generation algorithm documentation
- **docs/ai_context/**: Comprehensive architectural documentation by topic
- **docs/Customizer.md**: Custom seed configuration guide
- **docs/DR_hint_reference.md**: Hint system documentation
- **docs/BUILDING.md**: Build and installation instructions
- **README.md**: User-facing feature documentation

## Common Gotchas

1. **Transitivity Checks**: Most expensive constraint check - always run last
2. **Self-Locking Keys**: Key logic must prevent situations where players cannot access the rest of the dungeon
3. **Crystal Barriers**: Blue/orange barriers require matching switches in dungeon
4. **Portal Distribution**: Each dungeon needs at least one entrance
5. **Branching Balance**: Too many dead ends without branches = unreachable areas
6**Polarity Balance**: N/S and E/W door counts must allow valid connections

## CLI Argument Reference

Key arguments from `resources/app/cli/args.json`:
- `--doorShuffle [vanilla|basic|partitioned|crossed]`
- `--intensity [1|2|3]`
- `--keyshuffle [none|wild|universal]`
- `--key_logic [partial|strict|dangerous|experimental]`
- `--algorithm [balanced|vanilla_fill|major_only|dungeon_only|district]`
- `--logic [noglitches|owglitches|hybridglitches|nologic]`
- `--mode [open|standard|inverted]`
- `--shuffle`: Entrance randomizer options (vanilla, simple, restricted, full, crossed, insanity, etc.)
- `--pottery`: Pot shuffling modes
- `--shopsanity`: Enable shop item randomization
- `--enemizer`: Enemy randomization options
