# World and Player Setup

This topic explains how the randomizer initializes the core `World` object and configures player-specific options and precollected items.

## Overview

- The `World` object is the central data structure representing the game state for all players.
- Each player can have unique settings, inventory, and progression logic.
- Precollected items and starting inventory are assigned before world generation.

## Key Steps

1. **World Object Creation**
   - Instantiated in [`Main.py`](../../Main.py:85) with all relevant settings.
   - Stores player count, shuffle modes, logic, difficulty, item pools, and more.
   - Handles both single-player and multiworld scenarios.

2. **Player-Specific Options**
   - Each player has individualized settings for logic, difficulty, sword mode, accessibility, etc.
   - Player names and teams are parsed and stored.
   - Customizer and CLI/GUI arguments can override defaults per player.

3. **Precollected Items and Starting Inventory**
   - Items specified in arguments or customizer YAML are assigned to players before generation.
   - Items like Ocarina (Activated), Bombbag, and others can be precollected.
   - See [`ItemFactory`](../../Items.py) and `world.push_precollected()`.

4. **Seed and Randomization**
   - Each player/world instance receives a seed for deterministic generation.
   - Secure random mode is supported for additional entropy.

## Relevant Code

- [`main()` in Main.py](../../Main.py:59)
- [`World`](../../BaseClasses.py)
- [`ItemFactory`](../../Items.py)
- [`CustomSettings`](../../source/classes/CustomSettings.py)

## Notes

- Proper world and player setup is essential for supporting multiworld, custom logic, and reproducibility.
- The `World` object is referenced throughout the randomizer's orchestration and logic modules.