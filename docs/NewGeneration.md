# NewGeneration Branch

NewGeneration introduces a new dungeon generation algorithm alongside a significantly expanded set of customizer options. The new algorithm unlocks configurations that were previously impossible or unreliable — including mega-dungeons, custom sector assignments, and fine-grained control over what connections get shuffled.

Existing customizer files work without changes. All new features require opting in explicitly.

---

## What's New at a Glance

- **New dungeon generation algorithms** — classic (v1-compatible), experimental (new), and biased (mega-dungeon)
- **`dungeon_bias`** — designate which dungeon absorbs extra rooms to become the mega-dungeon
- **`smaller_dungeon_gen`** — trims rooms with no locations or other important features for leaner dungeon layouts
- **Custom sector assignments** — force specific rooms into specific dungeons, or exclude them
- **Custom dungeon pools** — control exactly which dungeons are shuffled together
- **Custom intensity** — choose which connection types (normal, spiral stairs, open edges etc.) are randomized
- **Expanded key logic** — new algorithm supports higher key counts required by biased generation
- **`door_type_only` shuffle** — shuffle key/bomb/dash door assignments without changing room layout
- **`paired` door shuffle** — shuffle rooms within fixed dungeon pairs
- **`door_type_distribution`** — control how door type counts redistribute across dungeon pools
- **Customizer: custom rooms, sprites, and text**

---

## New Settings

### `dungeon_shuffle_algorithm`

Controls which generation algorithm is used. Most new features require `experimental` or `biased`.

| Value | Description |
|---|---|
| `classic` | Original v1 algorithm. Fully backwards-compatible. Default when not specified. |
| `experimental` | New constraint-based algorithm. Required for sector assignments, custom pools, and custom intensity. More reliable generation at high intensity. |
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

Randomizes which doors are key doors, bomb doors, and dash doors (and other types as per door_type_mode) without changing which rooms connect to which. Dugeons layout remains vanilla; only the door type assignments are shuffled.

```yaml
settings:
  1:
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

---

### `door_type_distribution`

Controls how door type counts (key doors, bomb doors, dash doors, etc.) are distributed when dungeons are pooled together. Only meaningful when `door_shuffle` is `crossed`, `paired`, or `partitioned`, or when a custom `pools` configuration is used.

| Value | Description |
|---|---|
| `pooled` | Door type counts are summed across each pool and redistributed randomly within it. Default. |
| `vanilla` | Each dungeon keeps its own vanilla door type counts even when rooms are shuffled across dungeons. |
| `crossed` | Door type counts are pooled and redistributed across all dungeons, ignoring pool boundaries. |

```yaml
settings:
  1:
    door_type_distribution: vanilla
```

`vanilla` is useful when you want accurate per-dungeon key counts regardless of how rooms are shuffled. `crossed` provides maximum mixing and is only meaningful when combined with a pool configuration that would otherwise restrict redistribution.

---

## Key Logic

The new algorithms can produce dungeons with more key doors than the original algorithm supported. The `key_logic_algorithm` setting controls how placement is validated:

| Value | Description                                                                                                                                                                                                                                                                       |
|---|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `partial` | Rule-based analysis (KeyDoorShuffle). Minor-glitch safe. Default for most dungeons with standard key door counts.                                                                                                                                                                 |
| `strict` | Minor-glitch safe. More conservative than `partial` — may require more keys than theoretically necessary in complex layouts. Requires all keys in possesion before opening a single door.                                                                                         |
| `dangerous` | Relaxed rule-based validation. **Not minor-glitch safe.** Has a known bug in multiworld seeds that can produce unwinnable games. Only use for offline analysis or testing.                                                                                                        |
| `experimental` | Sphere-based analysis engine (NewKeyLogic). Minor-glitch safe in the same manner as partial. Will operate in strict mode for large dungeons produced by `experimental` or `biased` generation. Required when using those modes and many different new dungeon generation features |

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
```

Valid direction filters for `normal` and `edges` are `horizontal`, `vertical`, or `both` (default), or `none`. Other values take either `true` or `false` which removes it from the shuffle entirely. Requires `dungeon_shuffle_algorithm` of `experimental` or `biased`.

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

Overrides room data for specific rooms by SNES room address. Intended for tournament and limited-run event seeds requiring specific room configurations.

This is a low-level feature. Invalid values can corrupt the room or cause crashes. Refer to the limited run example files for working configurations.

### Custom Sprites (`sprites`)

Overrides enemy sprites in specific rooms. Supports underworld and overworld sprite replacement including layer 3 and overlord sprite types.

Sprite names correspond to entries in `EnemyList.py`. Sprite sheet constraints still apply — incompatible placements log a warning and fall back to the original sprite.

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

**`dungeon_entrances: vanilla | free`** — Each dungeon currently keeps its vanilla number of overworld entrances and dropdown connections (Eastern Palace always has 1, Desert always has 4, Skull Woods has 4 plus 3 drop-downs, etc.). `free` would allow those counts to redistribute across dungeons within the same pool — a dungeon might end up with more or fewer lobby portals than vanilla. Only meaningful when dungeons are pooled together and some form of entrance shuffle is active; connector logic in entrance shuffle will need to account for the redistributed counts.

**Pit and warp transitions (`pitwarps: none | pits | warps | both`)** — Pit falls and warp tiles are currently fixed in vanilla positions. Adding them as a `pitwarps` option in the `doors.intensity` section would make them part of the shuffle, meaningfully expanding the connection space available to the algorithm.

**Generation rate and speed improvements** — The new algorithms are more thorough but can be slower than classic in certain configurations. Ongoing work to improve constraint pruning and reduce unnecessary transitivity checks.

---

## Migration Notes

All existing settings and customizer files continue to work. The new `dungeon_shuffle_algorithm` defaults to `classic` (v1 behavior) when not specified.

The new features — sector assignments, custom pools, custom intensity, and biased generation — all require explicitly setting `dungeon_shuffle_algorithm` to `experimental` or `biased`. Nothing changes unless you opt in.
