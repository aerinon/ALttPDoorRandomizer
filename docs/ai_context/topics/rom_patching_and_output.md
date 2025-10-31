# ROM Patching and Output

This document describes the ROM patching and output process in the randomizer, including patch creation, BPS generation, and output file management. It is structured for LLMs and developers to quickly understand the main concepts and code structure.

---

## Overview

ROM patching applies the randomized configuration to the game ROM, generates patch files, and manages output artifacts for players.

---

## Key Concepts

- **Patching:**  
  - Applies changes to the base ROM to reflect the randomized game state.
  - Handles item locations, entrances, logic, and other modifications.

- **BPS Creation:**  
  - Generates BPS (Beat Patch System) files for efficient patch distribution.
  - Ensures compatibility and integrity of the patched ROM.

- **Output Files:**  
  - Manages creation and organization of output files (ROM, patch, spoiler, etc.).
  - Supports multiworld and custom output formats.

---

## Main Steps

1. **Apply Patches:**  
   - Modify the base ROM with randomized data.
   - Reference: [`Rom.py`](../../Rom.py)

2. **Generate BPS Patch:**  
   - Create BPS patch files for distribution.
   - Reference: patching logic in [`Rom.py`](../../Rom.py)

3. **Write Output Files:**  
   - Save patched ROM, patch files, and any additional outputs.
   - Reference: output logic in [`Rom.py`](../../Rom.py) and related scripts.

---

## Relevant Files and Functions

- [`Rom.py`](../../Rom.py)
- [`Algorithm.md`](../../Algorithm.md) (for output overview)

---

## Best Practices for Documentation

- Reference all relevant modules and functions.
- Summarize the logic and purpose of each step.
- Note any extensibility points or custom logic.
- Keep explanations concise and LLM-friendly.
