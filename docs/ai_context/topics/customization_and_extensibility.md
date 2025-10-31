# Customization and Extensibility

This document describes customization and extensibility features in the randomizer, focusing on YAML configuration, presets, and modular architecture. It is structured for LLMs and developers to quickly understand the main concepts and code structure.

---

## Overview

Customization and extensibility allow users and developers to tailor the randomizer to their needs, add new features, and modify behavior without changing core code.

---

## Key Concepts

- **YAML Configuration:**  
  - Supports custom game settings, logic, and item pools via YAML files.
  - Allows users to define presets and custom scenarios.

- **Presets:**  
  - Predefined configurations for common or recommended setups.
  - Can be loaded and combined for flexible customization.

- **Modular Architecture:**  
  - Codebase is organized into modules for logic, item placement, patching, etc.
  - Facilitates extension and maintenance.

---

## Main Steps

1. **Define Custom Settings:**  
   - Create or edit YAML files for custom logic, items, or rules.
   - Reference: [`docs/presets/`](../../docs/presets/) and [`docs/customizer_example.yaml`](../../docs/customizer_example.yaml)

2. **Load Presets:**  
   - Select and combine presets for desired gameplay.
   - Reference: preset loading logic in [`Customizer.md`](../../docs/Customizer.md)

3. **Extend Modules:**  
   - Add or modify modules for new features or logic.
   - Reference: modular code structure in [`source/`](../../source/)

---

## Relevant Files and Functions

- [`docs/presets/`](../../docs/presets/)
- [`docs/customizer_example.yaml`](../../docs/customizer_example.yaml)
- [`docs/Customizer.md`](../../docs/Customizer.md)
- [`source/`](../../source/)

---

## Best Practices for Documentation

- Reference all relevant modules and functions.
- Summarize the logic and purpose of each step.
- Note any extensibility points or custom logic.
- Keep explanations concise and LLM-friendly.
