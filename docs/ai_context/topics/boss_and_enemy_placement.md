# Boss and Enemy Placement

This topic describes how bosses and enemies are placed and randomized within the randomizer, including logic, configuration, and relevant modules.

## Overview

- Bosses are assigned to dungeons and shuffled according to settings.
- Enemy randomization is handled by the Enemizer integration.
- Both systems support advanced logic and bans for problematic placements.

## Key Steps

1. **Boss Placement**
   - Bosses are placed in dungeons using [`place_bosses`](../../Bosses.py).
   - Supports shuffling, unique boss requirements, and logic for special cases (e.g., Blind in Thieves' Town).
   - Boss placement is performed after dungeon and region creation.

2. **Enemy Randomization**
   - Enemies are randomized using [`randomize_enemies`](../../source/enemizer/Enemizer.py).
   - Enemizer supports enemy bans, logic for special rooms, and tile pattern shuffling.
   - Damage tables and enemy logic are initialized per player with [`DamageTable`](../../source/enemizer/DamageTables.py).

3. **Configuration and Bans**
   - Enemy and boss bans are maintained to avoid softlocks and unplayable scenarios.
   - Configuration files (YAML) and code-based lists define allowed and banned placements.

## Relevant Code

- [`main()` in Main.py](../../Main.py:231-232)
- [`place_bosses`](../../Bosses.py)
- [`randomize_enemies`](../../source/enemizer/Enemizer.py)
- [`DamageTable`](../../source/enemizer/DamageTables.py)
- Enemizer configuration files: [`enemy_deny.yaml`](../../source/enemizer/enemy_deny.yaml)

## Notes

- Boss and enemy placement is critical for game balance and playability.
- The logic ensures that all dungeons are solvable and that no enemy or boss can block progression unfairly.