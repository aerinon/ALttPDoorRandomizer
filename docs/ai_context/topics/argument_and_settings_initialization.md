# Argument and Settings Initialization

This topic covers how the randomizer initializes its configuration, parses arguments, and sets up the environment for a run.

## Overview

- Handles both CLI and GUI argument parsing.
- Supports customizer YAML files for advanced configuration.
- Initializes random seed logic and output paths.

## Key Steps

1. **Argument Parsing**
   - CLI arguments are parsed in [`CLI.py`](../../CLI.py).
   - GUI arguments are handled in [`Gui.py`](../../Gui.py).
   - Arguments include settings for shuffle modes, logic, item pools, output, and more.

2. **Customizer YAML Support**
   - If a customizer YAML file is provided (`args.customizer`), it is loaded and parsed.
   - Custom settings can override or extend CLI/GUI arguments.
   - See [`CustomSettings`](../../source/classes/CustomSettings.py) for implementation.

3. **Seed Initialization**
   - If a seed is provided, it is used for deterministic generation.
   - If not, a random seed is generated.
   - Secure random mode is supported for additional entropy.

4. **Output Path Setup**
   - Output directory is created if specified.
   - Output path is cached for use by other modules.

## Relevant Code

- [`main()` in Main.py](../../Main.py:59)
- [`CLI.py`](../../CLI.py)
- [`Gui.py`](../../Gui.py)
- [`CustomSettings`](../../source/classes/CustomSettings.py)

## Notes

- Argument and settings initialization is the first step in the orchestration flow.
- Proper configuration ensures reproducibility and customizability for users.