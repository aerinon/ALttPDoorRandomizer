---
layout: default
title: Installation & Usage
nav_order: 3
---

# Installation & Usage
{: .no_toc }

Complete guide to installing and running ALttP Door Randomizer.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Requirements

- Python 3.10 or higher (for running from source)
- A legal copy of The Legend of Zelda: A Link to the Past (JP 1.0 version) ROM

---

## Installation Methods

### Method 1: Pre-built Releases (Recommended)

This is the easiest method for most users.

1. Visit the [Releases page](https://github.com/aerinon/ALttPDoorRandomizer/releases)
2. Download the appropriate build for your system:
   - **Windows**: `ALttPDoorRandomizer-{version}-windows.zip`
   - **macOS**: `ALttPDoorRandomizer-{version}-osx.tar.gz`
   - **Linux**: `ALttPDoorRandomizer-{version}-linux-focal.tar.gz`
3. Extract the archive to a folder of your choice
4. Run the executable:
   - **Windows**: `DungeonRandomizer.exe`
   - **macOS/Linux**: `./DungeonRandomizer` or `./Gui.py`

### Method 2: Running from Source

For developers or users who want to run the latest development version.

#### Step 1: Clone the Repository

```bash
git clone https://github.com/aerinon/ALttPDoorRandomizer.git
cd ALttPDoorRandomizer
```

For the development branch:
```bash
git checkout DoorDevUnstable
```

#### Step 2: Install Python Dependencies

The project includes a script to install platform-specific dependencies:

```bash
python resources/ci/common/local_install.py
```

This will install all necessary Python packages and platform-specific dependencies.

#### Step 3: Verify Installation

Test that everything is working:

```bash
python DungeonRandomizer.py --help
```

You should see the help text with all available options.

---

## Usage

### GUI (Graphical User Interface)

The GUI provides an easy-to-use interface for generating seeds.

#### Starting the GUI

**Pre-built release:**
- **Windows**: Double-click `DungeonRandomizer.exe`
- **macOS/Linux**: Run `./DungeonRandomizer` from terminal

**From source:**
```bash
python Gui.py
```

#### Using the GUI

1. **Select your ROM**: Click "Select ROM" and choose your ALttP ROM file
2. **Configure settings**: Use the tabs to adjust:
   - **Dungeon Settings**: Door shuffle mode, intensity, key logic
   - **Item Settings**: Item placement, shopsanity, pottery
   - **Entrance Settings**: Entrance randomization options
   - **Enemy Settings**: Enemy shuffle, boss shuffle
   - **Game Options**: MSU resume, collection rate, etc.
3. **Generate**: Click "Generate" to create your seed
4. **Output**: The patched ROM will be created in the same directory

### CLI (Command-Line Interface)

The CLI offers more control and is useful for batch generation or scripting.

#### Basic Usage

```bash
python DungeonRandomizer.py [options]
```

#### Common Examples

**Basic crossed dungeon shuffle:**
```bash
python DungeonRandomizer.py --doorShuffle crossed --intensity 2
```

**With key shuffle and shopsanity:**
```bash
python DungeonRandomizer.py --doorShuffle crossed --keyshuffle wild --shopsanity
```

**Pottery and enemy drops:**
```bash
python DungeonRandomizer.py --doorShuffle basic --pottery lottery --dropshuffle underworld
```

**Generate without creating ROM (testing):**
```bash
python DungeonRandomizer.py --suppress_rom --spoiler none
```

**Create BPS patch instead of ROM:**
```bash
python DungeonRandomizer.py --bps --doorShuffle crossed
```

**Batch generation:**
```bash
python DungeonRandomizer.py --doorShuffle crossed --count 10
```

#### Key CLI Arguments

**Dungeon Settings:**
- `--doorShuffle [vanilla|basic|partitioned|crossed]` - Door shuffle mode
- `--intensity [1|2|3]` - Intensity level
- `--keyshuffle [none|wild|universal]` - Key shuffle mode
- `--key_logic [partial|strict|dangerous]` - Key logic algorithm
- `--door_type_mode [original|big|all|chaos]` - Door type shuffle
- `--trap_door_mode [vanilla|optional|boss|oneway]` - Trap door removal

**Item Settings:**
- `--algorithm [balanced|vanilla_fill|major_only|dungeon_only|district]` - Item placement
- `--pottery [none|keys|cave|cavekeys|reduced|clustered|nonempty|dungeon|lottery]` - Pot shuffle
- `--dropshuffle [none|keys|underworld]` - Enemy drop shuffle
- `--shopsanity` - Enable shop randomization
- `--bombbag` - Enable bomb bag item
- `--pseudoboots` - Enable pseudo boots

**Entrance Settings:**
- `--shuffle [vanilla|simple|restricted|full|crossed|insanity|...]` - Entrance shuffle mode
- `--overworld_map [default|compass|map]` - Overworld map mode

**Enemy Settings:**
- `--enemizercli [none|basic|shuffled]` - Enemy shuffle mode
- `--enemy_damage [default|shuffled|chaos]` - Enemy damage
- `--enemy_health [default|easy|hard]` - Enemy health
- `--shufflebosses [none|basic|normal|chaos|unique]` - Boss shuffle

**Logic:**
- `--logic [noglitches|owglitches|hybridglitches|nologic]` - Logic mode
- `--mode [open|standard|inverted]` - Game mode
- `--goal [ganon|trinity|ganonhunt|completionist]` - Victory condition

**Generation:**
- `--seed SEED` - Set seed number
- `--count N` - Generate N seeds
- `--suppress_rom` - Don't create ROM (testing)
- `--bps` - Create BPS patch instead of ROM
- `--spoiler [none|spoiler|playthrough]` - Spoiler log type

**Game Options:**
- `--msu_resume` - Enable MSU resume
- `--collection_rate` - Display collection rate
- `--reduce_flashing` - Reduce flashing animations
- `--shuffle_sfx` - Shuffle sound effects

For a complete list of options:
```bash
python DungeonRandomizer.py --help
```

---

## Multiworld Setup

Door Randomizer supports multiworld seeds where multiple players play different randomized games with shared item pools.

### Installing Multiworld Dependencies

Run the same installation script to install multiworld-specific dependencies:

```bash
python resources/ci/common/local_install.py
```

### Generating Multiworld Seeds

Create YAML files for each player (see `docs/player1.yml`, `docs/player2.yml`, `docs/player3.yml` for individual examples, or `docs/multi_mystery_example.yaml` for a complete multiworld configuration).

**Example player configuration:**
```yaml
description: Player 1's World
name: Player1
doorShuffle: crossed
intensity: 2
keyshuffle: wild
shopsanity: true
```

Generate the multiworld using the multi-mystery configuration file:
```bash
python DungeonRandomizer.py --customizer docs/multi_mystery_example.yaml
```

### Running Multiworld Server

```bash
python MultiServer.py
```

It will prompt you for the multidata file created from the multiworld generation step.

### Connecting with Multiworld Client

```bash
python MultiClient.py
```

Enter the server address and your player name to connect.

---

## Testing & Verification

### Running the Test Suite

To verify your installation and test the randomizer logic:

```bash
python TestSuite.py
```

**Test with specific settings:**
```bash
python TestSuite.py --dr basic --count 10 --tense 2
```

**Run specific test modules:**
```bash
python -m pytest test/
python -m pytest test/dungeons/TestDarkPalace.py
```

---

## Troubleshooting

### Common Issues

#### "Python not found" or "python: command not found"

- **Windows**: Make sure Python is installed and added to PATH during installation
- **macOS/Linux**: Install Python 3.10+ via your package manager or from [python.org](https://www.python.org/)

#### "No module named 'yaml'" or similar import errors

Run the dependency installation script:
```bash
python resources/ci/common/local_install.py
```

#### Pre-built executable won't run on macOS

macOS may block unsigned applications. Right-click the app and select "Open" to bypass the warning.

#### Pre-built executable won't run on Linux

Ensure the file has execute permissions:
```bash
chmod +x DungeonRandomizer
```

#### GUI window is too small or cut off

Try running from the command line to see if there are any error messages. Some display scaling settings can cause issues.

#### Generated ROM doesn't work with emulator

- Ensure you're using a clean US version of ALttP ROM (Japan 1.0)
- Try a different emulator (recommended: SNES9x, RetroArch with bsnes core)
- Verify the ROM was patched successfully (check file size and modification date)

### Getting Help

If you encounter issues:

1. Check the [Known Issues](/known-issues) page
2. Search [GitHub Issues](https://github.com/aerinon/ALttPDoorRandomizer/issues)
3. Ask in the [ALTTP Randomizer Discord](https://discordapp.com/invite/alttprandomizer):
   - `#door-rando` - General help and questions
   - `#bug-reports` - Report bugs and issues

When reporting issues, please include:
- Operating system and version
- Python version (`python --version`)
- Door Randomizer version or commit hash
- Full error message or description of the problem
- Settings used (CLI command or screenshot of GUI)

---

## Advanced Usage

### Custom Presets

You can create custom preset files to save your favorite settings combinations.

See the [Customizer documentation](docs/Customizer.md) for details on creating custom seeds with custom dungeons and rooms.

### Build from Source (Packaging)

To create a standalone executable from source:

See [BUILDING.md](docs/BUILDING.md) for detailed build instructions.

### Development Workflow

For contributors:

1. Fork the repository
2. Create a feature branch from `DoorDevUnstable`:
   ```bash
   git checkout DoorDevUnstable
   git checkout -b my-feature
   ```
3. Make your changes
4. Run tests: `python TestSuite.py`
5. Submit a pull request to `DoorDevUnstable` (not main/master)

---

## Next Steps

- Read the [Features Guide](/features) for detailed information on all settings
- Check the [Known Issues](/known-issues) page for current limitations
- See the [Roadmap](/roadmap) for upcoming features
- Join the community on [Discord](https://discordapp.com/invite/alttprandomizer)
