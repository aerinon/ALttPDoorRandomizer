# Playthrough and Spoiler Generation

This document describes the playthrough and spoiler generation process in the randomizer, focusing on sphere calculation, required items, and spoiler log creation. It is structured for LLMs and developers to quickly understand the main concepts and code structure.

---

## Overview

Playthrough and spoiler generation simulate the player's progression through the randomized game, calculate required items and locations, and produce detailed spoiler logs for analysis and debugging.

---

## Key Concepts

- **Sphere Calculation:**  
  - Divides the playthrough into "spheres" of progression, where each sphere contains locations accessible with the current inventory.
  - Used to determine the order in which items can be collected.

- **Required Items:**  
  - Identifies which items are necessary to complete the game.
  - Used for logic validation and spoiler log accuracy.

- **Spoiler Logs:**  
  - Detailed logs of item placements, progression spheres, and required items.
  - Useful for debugging, analysis, and player reference.

---

## Main Steps

1. **Simulate Playthrough:**  
   - Progress through the game, collecting items and unlocking new locations.
   - Reference: playthrough logic in [`Fill.py`](../../Fill.py)

2. **Calculate Spheres:**  
   - Divide locations into spheres based on accessibility.
   - Reference: sphere calculation logic in [`Fill.py`](../../Fill.py)

3. **Identify Required Items:**  
   - Determine which items are essential for game completion.
   - Reference: required item logic in [`Fill.py`](../../Fill.py)

4. **Generate Spoiler Log:**  
   - Output detailed logs of item placements and progression.
   - Reference: spoiler log generation in [`Fill.py`](../../Fill.py)

---

## Relevant Files and Functions

- [`Fill.py`](../../Fill.py)
- [`Algorithm.md`](../../Algorithm.md) (for playthrough overview)

---

## Best Practices for Documentation

- Reference all relevant modules and functions.
- Summarize the logic and purpose of each step.
- Note any extensibility points or custom logic.
- Keep explanations concise and LLM-friendly.
