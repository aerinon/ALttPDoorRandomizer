# Pitwarps Phase 3: Drop Lobbies

An overworld hole's landing is shuffled the way a pit's is. Feature plan: `docs/plans/pitwarps_feature.md`; pit model
and verification: `docs/plans/transitivity_pitwarp_verification.md`.

## Model

Overworld hole → Drop Portal → any Terminal in the owning dungeon.

- Entrance shuffle decides which hole leads to which Drop Portal; door shuffle never changes that link.
- A Drop Portal is a logical construct. It belongs to its vanilla dungeon, as portals do: Skull Woods owns its four,
  Hyrule Castle owns Sewers Rat Path's. The dungeon entrances feature may relax this later; it is out of scope here.
- Its exit is a one-way source matched to a Terminal in that dungeon, the same way pits are matched. The landing can be a
  vanilla drop landing or a pit Terminal, and its sector may come from anywhere in the door-shuffle pool.
- The entrance row carries the full landing data, as `LandingZoneData` rows do for pits.

## Scope

- Enabled only when lobbies and pits both shuffle: intensity 4, or a custom intensity with `lobbies` on and `pit_warps`
  `pits` or `both`. Otherwise every drop stays on its vanilla landing and nothing below changes behavior.
- Sewers Rat Path is not locked in any mode.
- Whether a hole is usable comes from the entrance topology, through the existing inaccessible-region logic.

## Data and regions

Five Drop Portal regions, one per hole:

| Drop Portal region | Owner (builder) | Vanilla landing | Entrance ID |
|---|---|---|---|
| `Skull Pot Circle Drop Portal` | `Skull Woods` (`Skull Woods Front` when split) | `Skull Pot Circle` | `0x76` |
| `Skull Left Drop Drop Portal` | `Skull Woods` (`Skull Woods Front` when split) | `Skull Left Drop` | `0x77` |
| `Skull Pinball Drop Portal` | `Skull Woods` (`Skull Woods Front` when split) | `Skull Pinball` | `0x78` |
| `Skull Back Drop Drop Portal` | `Skull Woods` (`Skull Woods Back` when split) | `Skull Back Drop` | `0x79` |
| `Sewers Rat Path Drop Portal` (replaces `Sewer Drop`) | `Hyrule Castle` (`Hyrule Castle Sewers` in standard) | `Sewers Rat Path` | `0x81` |

- Each region has one entrance (the hole) and one exit: a one-way source door, a single-member `Hole` group with a
  `PitWarp` hook. Locked, the source is connected to its vanilla landing, as unshuffled pits are.
- Entrance shuffle points holes at the Drop Portal regions instead of the landing regions: the hole target tables, the
  region-name lists naming the landing regions, and the entrance ID table (keyed by the Drop Portal region; the ID stays
  the landing's, since that is the entrance the ROM uses).
- Each Drop Portal region is its own sector (its source door is outstanding), assigned to its owning dungeon the way
  portal sectors are.
- Five new Terminals in `data/terminals.yaml`, the vanilla landings above. Their landing blocks are derived from the
  vanilla ROM entrance rows for their entrance IDs. Each drop's vanilla landing is its own group's Terminal, so the
  source/terminal matching stays one-to-one.
- Drop sources and pit sources share one Terminal pool within a dungeon: a drop may land on a pit Terminal and a pit on a
  drop landing.
- With the vanilla landings as ordinary Terminals, `default_lobby_drops` no longer pins their sectors.
- One helper lists a builder's Drop Portal regions and each drop's overworld parent region, read from the hole entrance.
  It replaces `drop_parent_region` and the vanilla `drop_entrances` / `default_lobby_drops` tables as the source of truth.
- Explicit helpers for lobby portal regions and drop portal regions replace the `' Portal'` suffix checks in
  `DoorShuffle.py` and the witness checker, so a Drop Portal is never taken for a lobby portal.

## Generation stages

- **LocalSearch:** `drop_lobbies_locked` is "locked unless `lobbies` and `pit_warps` is `pits` or `both`". Unlocked,
  Drop Portal sectors are pinned to their owning dungeon and landing sectors join the free pool. Locked, behavior is as
  today.
- **Pit machinery:** drop sources are `Hole` groups, so grouping, hook/hanger balance and the pit matching count them
  unchanged.
- **Sector descriptor:** a Drop Portal sector is entered from the overworld and explored like a non-destination portal:
  start Orange, reach its own source door.
- **Transitivity:** an ungated Drop Portal sector is a start (its source reached at the beginning, Orange). A gated one
  is enabled when the dungeon reaches a portal whose overworld side is the drop's parent region (the witness checker's
  rule), through the dependent-portal mechanism: enabling portal door → drop source. With vanilla entrances the Skull
  Back forest opens through Skull 3 or Skull 2 West, whichever is the destination; both belong to Skull Woods, as does
  the drop.
- **Stitcher:** pit assignment already maps a builder's sources to its Terminals. Drop Portal regions are entrance
  regions for the traversal simulation under the same ungated/gated rule, replacing the `default_lobby_drops` loop.
- **Key, big key and trap stages:** `find_possible_entrances` and `find_accessible_entrances` use the owning dungeon's
  Drop Portal regions instead of the landing names in `drop_entrances`.
- **Standard:** the Rat Path drop is not a start for the escape builders (Hyrule Castle Sewers, Hyrule Castle Dungeon);
  during the escape the sewers are walked from inside.
- **Item logic:** the world graph carries hole → Drop Portal → source → landing; no drop-specific rules.

## ROM

Entrance tables (bank 02 `EntranceData`), indexed by entrance ID. Word tables, then byte tables `0x85` apart:

| Field | Address | Field | Address |
|---|---|---|---|
| room | `0x14577` | main GFX | `0x150E5` |
| camera bounds (8 bytes) | `0x14681` | floor | `0x1516A` |
| horizontal scroll | `0x14AA9` | dungeon ID | `0x151EF` |
| vertical scroll | `0x14BB3` | in-door | `0x15274` |
| Link Y | `0x14CBD` | layer | `0x152F9` |
| Link X | `0x14DC7` | scroll controller | `0x1537E` |
| camera trigger Y | `0x14ED1` | quadrant | `0x15403` |
| camera trigger X | `0x14FDB` | overworld door tilemap | `0x15488` |
| | | song | `0x1550D` |

- Written only for a Drop Portal whose source is shuffled; otherwise the row stays vanilla (as `write_pitwarps`).
- From the chosen Terminal's landing data: room, bounds, scrolls, Link Y/X, camera triggers, layer, scroll controller,
  quadrant, floor and main GFX. An overworld drop loads fresh from the entrance row, so it needs floor and main GFX,
  which a pit does not.
- Unchanged: dungeon ID (ownership pinned), in-door and overworld door tilemap, and the song (the dungeon entered is
  unchanged).
- Rom.py's write of Hyrule Castle into the Sewer Drop dungeon byte (`0x15270`) still holds.

## Testing and verification

- **Data:** the derived landing blocks round-trip: an entrance row rebuilt from each block equals the vanilla row byte for
  byte (skipped without the vanilla ROM).
- **Regions:** each hole leads to its Drop Portal under vanilla entrances and under a shuffled entrance mode.
- **Locked mode:** `TestPitWarpsOffStayVanilla` (intensity 3, and intensity 4 with `pit_warps: none`) also checks drop
  sources stay on their vanilla landings and no entrance row is written.
- **ROM writer:** a shuffled drop writes exactly the fields above at its entrance ID; dungeon, in-door, tilemap and song
  are untouched; unshuffled drops write nothing.
- **Transitivity:** the witness checker reads drops from the new helper; the verification bar holds at intensity 4 with
  drops (13 vanilla dungeons, 78 pairs, real LocalSearch calls on seeds 1–12 with every True checked).
- **Gating:** with Skull Back's drop gated, Transitivity refuses a layout that works only through that drop until a
  destination portal opening the forest is reached, and accepts it once one is.
- **Standard:** `TestStandardEscape` at intensity 4; the Rat Path drop never counts as a start for the escape builders.
- **Generation:** `gen_check` crossed intensity 4, seeds 1–40, before and after; small standard and entrance-shuffle
  sweeps. Stitched layouts reach every region and every drop lands in its owning dungeon. A TestSuite run at the end
  (one at a time across sessions).
- **Emulator:** one test seed in `test_games/` with drops moved, with notes on which hole lands where; checked for landing
  position, falling animation, graphics, floor and music.
