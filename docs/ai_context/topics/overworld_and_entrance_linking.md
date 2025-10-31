# Overworld and Entrance Linking

This topic explains how the randomizer links overworld regions and entrances, including dynamic exits and entrance shuffling logic.

## Overview

- Overworld regions and entrances are linked to create a connected game world.
- Supports multiple entrance shuffle modes and dynamic exit creation.
- Handles both standard and shuffled entrance configurations.

## Key Steps

1. **Overworld Linking**
   - Overworld regions are linked for each player using [`link_overworld`](../../OverworldShuffle.py).
   - Handles standard and shuffled overworld layouts.

2. **Dynamic Exit Creation**
   - Dynamic exits are created with [`create_dynamic_exits`](../../OverworldShuffle.py).
   - Supports advanced entrance shuffle modes and custom logic.

3. **Entrance Shuffling**
   - Entrances are shuffled using [`link_entrances_new`](../../source/overworld/EntranceShuffle2.py).
   - Supports multiple shuffle algorithms and cross-world connections.

4. **Special Logic for Glitches**
   - Additional connections and logic are added for glitch modes (e.g., overworld glitches, hybrid major glitches).
   - See [`create_owg_connections`](../../OverworldGlitchRules.py) and [`create_hmg_entrances_regions`](../../UnderworldGlitchRules.py).

## Relevant Code

- [`main()` in Main.py](../../Main.py:270-272)
- [`link_overworld`](../../OverworldShuffle.py)
- [`create_dynamic_exits`](../../OverworldShuffle.py)
- [`link_entrances_new`](../../source/overworld/EntranceShuffle2.py)
- [`create_owg_connections`](../../OverworldGlitchRules.py)
- [`create_hmg_entrances_regions`](../../UnderworldGlitchRules.py)

## Notes

- Overworld and entrance linking is essential for ensuring all regions are accessible and the game is solvable.
- Shuffle modes and glitch logic provide a wide range of gameplay experiences.