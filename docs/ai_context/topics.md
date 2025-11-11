# Documentation Topics for LLMs

This list outlines the major topics and domains that should be covered to provide comprehensive context for LLMs working with this project.

## Project Overview

The project is a randomizer for A Link to the Past, focusing on dungeon and item shuffling for replayability.  
It is based on the Entrance Randomizer ([KevinCathcart's Project](https://github.com/KevinCathcart/ALttPEntranceRandomizer)), but adds extensive new features and logic, including:

- **Dungeon Door Shuffle**: Multiple algorithms and modes for shuffling dungeon doors, including cross-dungeon and partitioned shuffles.
- **Key Logic Algorithms**: Advanced logic for small key placement and usage, with several protection and strictness levels.
---

## Key Logic Algorithm Summary

There are four main algorithms for key logic in this randomizer. Each has different safety and gameplay properties:

**Dangerous:**  
Simulates all possible ways a player could use keys in a dungeon, testing every scenario. Most realistic, but does not account for minor glitches and can create unwinnable situations in multiplayer. Not minor glitch safe.

**Partial:**  
Uses a set of rules to decide key placement. Safe even if most minor glitches are used, since these are treated as having a full inventory. Balances safety and flexibility. Minor glitch safe.

**Strict:**  
Assumes every key door requires all small keys to open. Safest and simplest; always safe even with minor glitches, but least dynamic. No progress can be made until all keys are collected. Minor glitch safe.

**Experimental:**  
A work-in-progress hybrid that combines strict and partial logic. Acts like strict in dungeons with many key doors to avoid performance issues, but uses more advanced logic in smaller dungeons. Designed for future extensibility and optimization.

**Note:**  
No algorithm is safe from Hybrid Major Glitches (HMG), where players use keys from one dungeon in another to break intended logic.

For technical details and code paths, see:
- [Key Logic Architecture Deep Dive](topics/key_logic_architecture_deep_dive.md)
- [Key Logic Edge Cases Deep Dive](topics/key_logic_edge_cases_deep_dive.md)
- [Door and Dungeon Shuffling Deep Dive](topics/door_and_dungeon_shuffling_deep_dive.md)
- **Trap Door and Door Type Shuffling**: Options for shuffling or removing trap doors and randomizing door types.
- **Pottery and Enemy Drop Expansion**: Adds pots and enemy drops as item locations, with dynamic and legacy modes.
- **Item Pool Expansions**: New items (Bombbag, Pseudo Boots, Mirror Scroll, etc.), shopsanity, and custom item pools.
- **Experimental and Crossed Dungeon Features**: Mixed travel, palette standardization, and more.
- **Enemizer Integration**: Built-in enemy randomization and logic, with unique features and bans.
- **Goal and Logic Modes**: Multiple win conditions, logic levels (including glitched logic), and accessibility options.
- **Multiplayer Support**: Multiworld and networking features.
- **GUI and CLI**: Both graphical and command-line interfaces for setup and play.
- **Customizer**: Extensive customization and preset support.
- **Testing and Validation**: Scripts and options for automated testing and validation.

**Intended audience:**  
Randomizer enthusiasts.

## Main Code Flow and Entry Points (Project Root)

- [`Main.py`](Main.py): Main entry point and core orchestration logic
- [`DungeonRandomizer.py`](DungeonRandomizer.py): Dungeon randomization process
- [`Gui.py`](Gui.py): GUI entry point and main loop
- [`CLI.py`](CLI.py): Command-line interface and argument parsing
- [`Adjuster.py`](Adjuster.py), [`AdjusterMain.py`](AdjusterMain.py): Adjustment and patching utilities
- [`MultiClient.py`](MultiClient.py), [`MultiServer.py`](MultiServer.py): Multiplayer networking logic
- [`TestSuite.py`](TestSuite.py), [`test-options.py`](test-options.py): Testing and validation scripts
- [`Tables.py`](Tables.py), [`RaceRandom.py`](RaceRandom.py): Data tables and randomization utilities
- [`Utils.py`](Utils.py): General utilities
- [`BaseClasses.py`](BaseClasses.py): Core data structures and base classes
- [`Bosses.py`](Bosses.py): Boss logic and rules
- [`Doors.py`](Doors.py), [`DoorShuffle.py`](DoorShuffle.py): Door and key shuffling logic
- [`Fill.py`](Fill.py): Item fill and placement logic
- [`ItemList.py`](ItemList.py), [`Items.py`](Items.py): Item definitions and pools
- [`Regions.py`](Regions.py): Region and location definitions
- [`Rom.py`](Rom.py): ROM manipulation and patching
- [`Rules.py`](Rules.py): Game rules and logic
- [`OverworldGlitchRules.py`](OverworldGlitchRules.py), [`UnderworldGlitchRules.py`](UnderworldGlitchRules.py): Glitch logic
- [`PotShuffle.py`](PotShuffle.py): Pot shuffle logic
- [`RoomData.py`](RoomData.py): Room data and manipulation
- [`InitialSram.py`](InitialSram.py): SRAM initialization
- [`Plando.py`](Plando.py): **Deprecated** plandomizer and custom world logic (for historical reference only)
- [`Mystery.py`](Mystery.py): **Deprecated** mystery mode logic (for historical reference only)

## Randomizer Flow and Orchestration

- Overview of the main flow in [`Main.py`](Main.py)
- See [`topics/main_algorithm_flow.md`](topics/main_algorithm_flow.md) for a detailed breakdown of the orchestration steps, module interactions, and key functions.

## Argument and Settings Initialization

- See [`topics/argument_and_settings_initialization.md`](topics/argument_and_settings_initialization.md) for details on CLI/GUI argument parsing, customizer YAML, seed logic, and output path setup.

## World and Player Setup

- See [`topics/world_and_player_setup.md`](topics/world_and_player_setup.md) for details on the World object, player-specific options, and precollected items.

## Module and Data Structure Creation

- See [`topics/module_and_data_structure_creation.md`](topics/module_and_data_structure_creation.md) for details on the creation of regions, dungeons, shops, doors, and rooms.

## Boss and Enemy Placement

- See [`topics/boss_and_enemy_placement.md`](topics/boss_and_enemy_placement.md) for details on boss assignment, enemy randomization, and Enemizer integration.

## Overworld and Entrance Linking

- See [`topics/overworld_and_entrance_linking.md`](topics/overworld_and_entrance_linking.md) for details on overworld region linking, dynamic exits, and entrance shuffle logic.

## Core Classes and Utilities (`source/classes/`)

- Purpose and structure of core classes and utilities

## Dungeon Generation and Logic (`source/dungeon/`)

- Dungeon generation algorithms and logic
- Key modules: NewKeyLogic, SmallKeyDoorShuffle, etc.
- [Dungeon Generation Algorithms and Variations](topics/dungeon_generation_algorithms.md)
- [Key Logic Architecture Deep Dive](topics/key_logic_architecture_deep_dive.md)

## Enemy Randomization and Logic (`source/enemizer/`)

- Enemy randomization systems and configuration

## GUI Components and Customization (`source/gui/`)

- GUI architecture and modules

## Item Handling and Logic (`source/item/`)

- Item data structures and logic

## Game Logic and Rules (`source/logic/`)

- Rule definitions and logic modules

## Overworld Data and Shuffling (`source/overworld/`)

- Overworld entrance data and shuffling

## ROM Data and Manipulation (`source/rom/`)

- ROM data tables and manipulation scripts

## Tools and Utilities (`source/tools/`)

- Utility scripts and helper modules

## Meta Scripts and Build Tools (`source/meta/`)

- Build, diagnostics, and requirements scripts

## Data Files and Constraints

- Data and constraint files (e.g., must_enter_info.txt)
- Configuration and YAML files

## Integration Points and Dependencies

- How modules interact with each other
- External dependencies and integration points
- Cross-module data flow and communication patterns

## Core System Topics

### Algorithm and Logic Deep Dives
- [Door and Dungeon Shuffling](topics/door_and_dungeon_shuffling.md)
  - [Door and Dungeon Shuffling Deep Dive](topics/door_and_dungeon_shuffling_deep_dive.md)
- [Key Logic Edge Cases Deep Dive](topics/key_logic_edge_cases_deep_dive.md)
- [Key Logic Architecture Deep Dive](topics/key_logic_architecture_deep_dive.md)
- [Overworld and Entrance Linking](topics/overworld_and_entrance_linking.md)
  - [Entrance Linking Deep Dive](topics/entrance_linking_deep_dive.md)

### Item and Economy Systems
- [Item Pool Generation and Placement](topics/item_pool_generation_and_placement.md)
  - [Item Pool Deep Dive](topics/item_pool_generation_and_placement_deep_dive.md)
- [Shop and Money Logic](topics/shop_and_money_logic.md)

### Game Logic and Rules
- [Logic and Rule Setup](topics/logic_and_rule_setup.md)

### Generation Pipeline
- [Finalization and Validation](topics/finalization_and_validation.md)
  - [Finalization Deep Dive](topics/finalization_and_validation_deep_dive.md)
- [ROM Patching and Output](topics/rom_patching_and_output.md)
- [Playthrough and Spoiler Generation](topics/playthrough_and_spoiler_generation.md)
  - [Playthrough Deep Dive](topics/playthrough_and_spoiler_generation_deep_dive.md)

### Multiplayer and Extensions
- [Multiworld and Multiplayer Logic](topics/multiworld_and_multiplayer_logic.md)
- [Customization and Extensibility](topics/customization_and_extensibility.md)

### Infrastructure and Utilities
- [Utility Modules and Data Tables](topics/utility_modules_and_data_tables.md)
- [Testing Framework and Validation](topics/testing_framework_and_validation.md)
