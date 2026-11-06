# NewGeneration Branch

NewGeneration introduces a new dungeon generation algorithm alongside a significantly expanded set of customizer options. The new algorithm unlocks configurations that were previously impossible or unreliable — including mega-dungeons, custom sector assignments, and fine-grained control over what connections get shuffled.

Existing settings and customizer files work without changes, with one exception: `door_type_mode: chaos` is now `door_type_distribution: chaos` (see [Migration Notes](#migration-notes)). All new features require opting in explicitly.

---

## What's New at a Glance

- **New dungeon generation algorithms** — classic (v1-compatible), experimental (new), and biased (mega-dungeon)
- **Higher generation rate** — experimental generation produces a seed far more often than classic, at similar time per seed
- **`dungeon_bias`** — designate which dungeon absorbs extra rooms to become the mega-dungeon
- **`smaller_dungeon_gen`** — trims rooms with no locations or other important features for leaner dungeon layouts
- **Custom sector assignments** — force specific rooms into specific dungeons, or exclude them
- **Custom dungeon pools** — control exactly which dungeons are shuffled together
- **Custom intensity** — choose which connection types (normal, spiral stairs, open edges etc.) are randomized
- **Intensity 4** — shuffles pit falls, warp tiles, and where overworld holes land
- **Rewritten key logic** — the `experimental` key logic is a new engine, built to keep larger key door layouts safe
- **`door_type_only` shuffle** — shuffle key/bomb/dash door assignments without changing room layout
- **`paired` door shuffle** — shuffle rooms within fixed dungeon pairs
- **`door_type_distribution`** — control how door type counts redistribute across dungeon pools
- **Customizer: custom rooms, sprites, and text**

---

## New Settings

### `dungeon_shuffle_algorithm`

Controls which generation algorithm is used. Most new features require `experimental` or `biased`. Both run the [experimental key logic](#experimental-key-logic): a `key_logic_algorithm` of `partial` or `dangerous` switches to `experimental` with them, while `strict` and `static` are kept.

| Value | Description |
|---|---|
| `classic` | Original v1 algorithm. Fully backwards-compatible. |
| `experimental` | New constraint-based algorithm. Required for sector assignments, custom pools, and custom intensity. More reliable generation at high intensity. Default. |
| `biased` | Experimental algorithm with one dungeon designated to absorb extra rooms, creating a mega-dungeon. |

```yaml
settings:
  1:
    dungeon_shuffle_algorithm: experimental
```

### `dungeon_bias`

When using `biased` generation, sets which dungeon becomes the mega-dungeon. Defaults to `Hyrule Castle`.

```yaml
settings:
  1:
    dungeon_shuffle_algorithm: biased
    dungeon_bias: Ganons Tower
```

Any standard dungeon name is valid. The biased dungeon will receive extra sectors that do not fit elsewhere, resulting in a significantly larger dungeon than normal.

### `smaller_dungeon_gen`

When enabled, the generator attempts to exclude rooms that have no item locations and are otherwise redundant. This produces leaner dungeon layouts with less filler traversal.

```yaml
settings:
  1:
    smaller_dungeon_gen: true
```

### New `door_shuffle` Modes

#### `door_type_only`

Randomizes which doors are key doors, bomb doors, and dash doors (and other types as per door_type_mode) without changing which rooms connect to which. Dungeon layouts remain vanilla; only the door type assignments are shuffled. Requires `experimental` generation.

```yaml
settings:
  1:
    dungeon_shuffle_algorithm: experimental
    door_shuffle: door_type_only
```

This is a lighter randomization option and a useful foundation for customizer seeds where room connections are fixed via the `doors` section.

#### `paired`

Shuffles dungeon rooms within fixed dungeon pairs (and one trio, since there are 13 dungeons). Each pair only mixes rooms with its partner — a middle ground between `basic` (single dungeon) and `partitioned` (three fixed groups).

```yaml
settings:
  1:
    door_shuffle: paired
```

Pairs are determined by the randomizer. This mode is `experimental` generation only.

### Intensity 4: Pits, Warps and Drop Lobbies

Intensity 4 shuffles everything intensity 3 does, plus pit falls and warp tiles. A pit or warp still leads somewhere in
its own dungeon, but it can land on any landing spot there instead of its vanilla one. Both are one way, and the logic
treats them that way. Requires `experimental` or `biased` generation; the classic algorithm never shuffles pits or warps.

```yaml
settings:
  1:
    dungeon_shuffle_algorithm: experimental
    door_shuffle: crossed
    intensity: 4
```

**Drop lobbies.** When lobbies and pits both shuffle, the overworld holes into dungeons (Skull Woods' four drops and
Hyrule Castle's sewer drop) shuffle too. Each hole still belongs to its vanilla dungeon but can land on any landing spot
in it. When lobbies or pits stay vanilla, the holes land where they always have.

The spoiler lists each shuffled pit and warp with where it lands, and lists shuffled holes with the dungeon lobbies.

To shuffle only some of these, use `pit_warps` in [Custom Intensity](#custom-intensity-doorsintensity).

---

### `door_type_distribution`

Controls how door type counts (key doors, bomb doors, dash doors, etc.) are distributed among dungeons. `crossed` and `chaos` move door types between dungeons, even across the pools of `door_shuffle: partitioned`. They are not compatible with `door_shuffle: basic`, which keeps each dungeon's own keys; generation stops with an error. Requires `experimental` or `biased` generation, except that `chaos` also varies the counts under `classic`.

| Value | Description |
|---|---|
| `pooled` | Door type counts are summed within each shuffle pool (the dungeons whose rooms mix) and redistributed randomly within it. With `basic`, each dungeon is its own pool. Default. |
| `vanilla` | Each dungeon keeps its own vanilla door type counts even when rooms are shuffled across dungeons. |
| `crossed` | Door type counts are summed across all dungeons and redistributed among them, whatever the door shuffle mode or pools. |
| `chaos` | As `crossed`, but each dungeon's counts first vary at random (from one fewer to three more of each type), so totals differ from vanilla. |

```yaml
settings:
  1:
    door_type_distribution: vanilla
```

`vanilla` is useful when you want accurate per-dungeon key counts regardless of how rooms are shuffled. `crossed` provides maximum mixing: it moves key, bomb and dash doors between all dungeons, so one dungeon may have no key doors while another has many more than vanilla. With `door_shuffle: crossed`, `pooled` and `crossed` are the same.

---

## Key Logic

The new algorithms can produce dungeons with more key doors than the original algorithm supported. The `key_logic_algorithm` setting controls how placement is validated:

| Value | Description                                                                                                                                                                                                                                                                       |
|---|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `partial` | Rule-based analysis (KeyDoorShuffle). Minor-glitch safe.                                                                                                                                                                         |
| `strict` | Minor-glitch safe. More conservative than `partial` — may require more keys than theoretically necessary in complex layouts. Requires all keys in possesion before opening a single door.                                                                                         |
| `dangerous` | Relaxed rule-based validation. **Not minor-glitch safe.** Has a known bug in multiworld seeds that can produce unwinnable games. Only use for offline analysis or testing.                                                                                                        |
| `static` | The entrance randomizer's hand-written key rules, counting chest keys only. Requires vanilla doors and unshuffled key drops and key pots; with enemy shuffle on, `any_enemy_logic` must be `none`. |
| `experimental` | The rewritten key logic (below). Minor-glitch safe in the same manner as partial. Used by `experimental` and `biased` generation in place of `partial` and `dangerous`. Default. |

### Experimental Key Logic

`experimental` is a rewrite, not an extension of `partial`. `partial` gives each key door a fixed worst-case key
count. `experimental` instead explores the orders in which a player can open a dungeon's key doors and works out what
is reachable in every one of them, so a key is only required where some order of play would actually need it.

- **Guarantees hold whatever the player has.** What a dungeon promises is computed for every case that changes it: with
  or without the big key, with or without the prize that opens an entrance (Ganon's Tower, the Pyramid Fairy), and
  with each combination of entrances the player may be able to use, including dropping in through holes and the save
  and quit start in the Sanctuary.
- **Keys count where they lie.** A key found inside a dungeon only helps once the player can reach it.
- **Self-locking key doors** (a key behind its own door) are allowed only for that key.
- **Large layouts.** With more than 8 key doors (common in `biased` mega-dungeons and `chaos` door types), it switches
  to a faster, more conservative mode.
- **A final check.** After items are placed, every seed is checked for a key door order that softlocks the player. A
  seed that fails the check is not used.

Universal keys, key drops, pottery keys, and keys shuffled outside their dungeon are all supported.

---

## Generation Rate and Speed

Experimental generation produces a seed far more often than classic. Across the test suite's settings (open,
standard and inverted; vanilla, simple through insanity entrance shuffle, retro, keysanity, shopsanity and overworld
glitches; intensities 1 to 3), **92%** of experimental attempts produce a seed, against **65%** for classic.

Head to head against the 1.5.8 release, 30 seeds per setting:

| Setting | 1.5.8 | 2.0 classic | 2.0 experimental | Seconds per seed (1.5.8 / experimental) |
|---|---|---|---|---|
| basic, intensity 3 | 60% | 53% | 100% | 1.6 / 5.5 |
| crossed, intensity 1 | 63% | 73% | 100% | 4.2 / 5.2 |
| crossed, intensity 2 | 80% | 60% | 87% | 5.2 / 6.9 |
| crossed, intensity 3 | 47% | 70% | 90% | 20.0 / 8.3 |
| crossed, intensity 3, standard | 23% | 30% | 73% | 14.6 / 8.4 |
| crossed, intensity 3, crossed entrances, inverted | 73% | 57% | 73% | 8.7 / 15.3 |
| **All** | **58%** | **57%** | **87%** | 7.7 / 8.0 |

Seconds are per seed generated. Experimental is slower on simple settings (basic, low intensities) and faster on the
hardest ones (crossed intensity 3). Counting the time spent on failed attempts, all three take about 17
seconds per seed produced. Classic generates as it did in 1.5.8; differences between those columns are within the
noise of 30 seeds.

**Intensity 4 is new and still has generation issues to work out:** about 64% of attempts produce a seed, and each
takes 20 to 40 seconds.

---

## Customizer Additions

These features are available in customizer files. All existing v1 customizer sections continue to work.

### Custom Dungeon Pools (`doors.pools`)

Controls which dungeons are shuffled together. Without this setting, `door_shuffle: crossed` mixes all dungeons. With custom pools, you can define specific groups.

```yaml
doors:
  1:
    pools:
      - [Palace of Darkness, Eastern Palace]
      - [Desert Palace, Misery Mire]
      - [Skull Woods, Thieves Town]
      - [Ice Palace, Swamp Palace]
      - [Tower of Hera, Turtle Rock, Ganons Tower]
      - [Hyrule Castle, Agahnims Tower]
```

Each list entry is a pool of dungeons whose rooms will only be shuffled among themselves. Dungeons not listed use default behavior. Requires `dungeon_shuffle_algorithm: experimental` or `biased`.

### Sector Assignments (`doors.sectors` and `doors.sector_exclusions`)

A sector is a group of rooms that are always kept together during generation (rooms that cannot currently be split). Sector assignments let you force specific sectors into specific dungeons, or ensure they are excluded from certain dungeons.

```yaml
doors:
  1:
    sectors:
      GT Big Chest: Ganons Tower          # force this sector into GT
      TR Big Chest: Turtle Rock           # force this sector into TR
      Swamp Hub: Swamp Palace
    sector_exclusions:
      Swamp Lobby: [Hyrule Castle]        # prevent this sector from going into HC
      GT Gauntlet 1: [Hyrule Castle]
```

Sector names correspond to a region within that sector (typically the most recognizable room). This is a low-level feature — forcing too many sectors can make generation impossible if the constraints conflict. Requires `dungeon_shuffle_algorithm: experimental` or `biased`.

See [custom_sector_example.yaml](presets/custom_sector_example.yaml) for a working example.

### Custom Intensity (`doors.intensity`)

Controls which connection types are included in shuffling. By default, the `intensity` setting determines this globally. The `doors.intensity` section gives fine-grained control.

```yaml
doors:
  1:
    intensity:
      normal: horizontal    # only shuffle horizontal normal doors
      edges: horizontal     # only shuffle horizontal edge connections
      straight: false       # exclude straight staircases
      ladder: false         # exclude ladder connections
      spiral: true          # include spiral staircases
      lobbies: false        # keep dungeon entrances on their vanilla doors
      pit_warps: pits       # shuffle pit falls but not warp tiles
```

Valid direction filters for `normal` and `edges` are `horizontal`, `vertical`, or `both` (default), or `none`. `pit_warps` takes `none`, `pits`, `warps`, or `both`. `lobbies` shuffles which door each dungeon entrance leads to; shuffling lobbies without vertical normal doors limits which doors can be entrances, and overworld holes shuffle only when `lobbies` and pits both do. Other values take either `true` or `false` which removes it from the shuffle entirely. Requires `dungeon_shuffle_algorithm` of `experimental` or `biased`.

See [verticality.yaml](presets/customizer/verticality.yaml) for an example that restricts shuffling to horizontal connections only.

### `item_pool_adjust`

Adjusts the base item pool by adding or removing items without replacing it entirely. Unlike `item_pool` (which is a full pool replacement), this applies deltas on top of what the randomizer settings generate.

```yaml
item_pool_adjust:
  1:
    Bottle (Random): 2        # add 2 extra bottles
    Boss Heart Container: -3  # remove 3 heart containers
```

See [Customizer.md](Customizer.md) for full documentation.

### Custom Rooms (`rooms`)

Overrides room data for specific rooms by room ID (hex). Intended for tournament and limited-run event seeds requiring specific room configurations.

This is a low-level feature. Invalid values can corrupt the room or cause crashes. Refer to the limited run example files for working configurations.

### Custom Sprites (`sprites`)

Replaces the sprite list of specific dungeon rooms, keyed by room ID (hex). Each entry is `[kind, tile_x, tile_y, layer]` with an optional fifth `sub_type`; `kind` is a sprite name from `EnemyList.py` or a hex sprite ID, and overlords are supported.

```yaml
sprites:
  "0x02":
    - ["CricketRat", "0x12", "0x05", "0x01"]
```

Nothing checks the placements against the room's sprite sheet; an unknown sprite name stops generation with an error.

### Custom Text (`text`)

Overrides in-game text strings by key. Useful for custom hint text, NPC dialogue, or event flavor text.

```yaml
text:
  uncle_leaving_text: "The treasure waits."
```

---

## Examples

- [Custom sector assignments](presets/custom_sector_example.yaml) — forcing sectors to dungeons and exclusions
- [Custom dungeon pools](presets/custom_pools_example.yaml) — restricting which dungeons mix
- [Custom intensity](presets/customizer/verticality.yaml) — horizontal-only shuffling

---

## In Progress / Testing

These features are implemented but not yet fully validated:

**`door_type_distribution`** — Implemented and plumbed but not yet fully tested across all pool configurations. See the [door_type_distribution](#door_type_distribution) section above for full documentation.

---

## Roadmap

These features are planned for future development on this branch:

**`dungeon_entrances: vanilla | free`** — Each dungeon currently keeps its vanilla number of overworld entrances and dropdown connections (Eastern Palace always has 1, Desert always has 4, Skull Woods has 4 plus 4 drop-downs, etc.). `free` would allow those counts to redistribute across dungeons within the same pool — a dungeon might end up with more or fewer lobby portals than vanilla. Only meaningful when dungeons are pooled together and some form of entrance shuffle is active; connector logic in entrance shuffle will need to account for the redistributed counts.

**Generation rate and speed improvements** — Ongoing work to raise the generation rate further, especially at intensity 4 and crossed intensity 3, where most remaining failures are layouts the generator gives up on checking.

---

## Migration Notes

Existing settings and customizer files continue to work, with one exception: `door_type_mode: chaos` has moved to `door_type_distribution: chaos`. The closest replacement is `door_type_mode: all` plus `door_type_distribution: chaos`; unlike the old mode, the new one pools door types across all dungeons, not only within each shuffle pool, and it is not compatible with `door_shuffle: basic`.

The defaults are now `dungeon_shuffle_algorithm: experimental`, `key_logic_algorithm: experimental` and `intensity: 3`. Settings and customizer files that leave these out get the new defaults; set `dungeon_shuffle_algorithm: classic`, `key_logic_algorithm: partial` and `intensity: 2` for v1 behavior.

The new features — sector assignments, custom pools, custom intensity, and biased generation — require `dungeon_shuffle_algorithm` of `experimental` or `biased`.
