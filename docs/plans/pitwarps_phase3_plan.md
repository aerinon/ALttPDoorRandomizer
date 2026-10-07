# Pitwarps Phase 3 (Drop Lobbies) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** an overworld hole leads to its Drop Portal, whose one-way source lands on any Terminal in the owning dungeon,
with the entrance row carrying the landing data.

**Architecture:** five Drop Portal regions sit between the holes and the dungeon. Each one's exit is a single-member
`Hole` group that the existing pit machinery matches to a Terminal; the five vanilla landings become Terminals. One
helper module answers "is this a drop portal / entered from outside / which drops does this builder own" for every
stage. The ROM writes the drop's entrance row from the chosen Terminal's landing block.

**Tech Stack:** Python 3.12+ (venv at the scratchpad path below), unittest, `data/terminals.yaml`, the vanilla ROM at
`../orig/z3.sfc` for data checks.

**Spec:** `docs/specs/2026-10-06-pitwarps-phase3-drop-lobbies-design.md`

## Global Constraints

- Branch `PitWarp`; never commit to `NewGeneration`, never push, never merge. Show the user a diff (color-coded, line
  numbers, explained inline, plus a side-by-side HTML under `analysis/`) before every commit.
- Leave the user's uncommitted changes alone: `data/base2current.bps`, the `RANDOMIZERBASEHASH` line in `Rom.py`, the
  `.github/actions/build/action.yml` deletion. Stage `Rom.py` hunk by hunk.
- Never edit `test_games/*_guide.md`.
- Conventional Commits, no ticket key; commit complete units, not sub-steps.
- Position and ROM values in hex.
- Only one TestSuite at a time across sessions (max 5 CPU threads, no `--count`); prefer `source/tools/gen_check.py`.
- Run tests with: `PYTHONPATH=.:source PYTHONHASHSEED=0 $PY -m unittest discover -s test/dungeon -p 'Test*.py' -t .`
  where `PY=/tmp/claude-1000/-home-randall-dev-kwyn-doors/58450237-f9f2-4899-90a7-4618caa98086/scratchpad/venv/bin/python`.
- Generic (non-pit) bugs found along the way go to the generator-fixes session, not onto PitWarp.
- Drops unlock only when `lobbies` is on and `pit_warps` is `pits` or `both` (`drop_lobbies_locked`). Locked, every
  drop stays on its vanilla landing.
- Ownership: the four Skull Drop Portals belong to `Skull Woods` (`Skull Woods Front` when split); the Rat Path Drop
  Portal belongs to `Hyrule Castle` (either `Hyrule Castle Sewers` or `Hyrule Castle Dungeon` in standard).

## Review Focus

- **Locked mode drifts:** intensity 3 or `pit_warps: none` should generate the same dungeons as before. Task 2 pins it
  with a before/after door-connection comparison on fixed seeds.
- **Entrance shuffle modes:** with holes shuffled (e.g. `--shuffle crossed`), each hole must still reach a Drop Portal
  and the entrance ID must follow the Drop Portal, not the hole. Task 1 tests one shuffled mode.
- **Standard mode:** the Rat Path drop must never seed an escape builder's reachability. Task 4 tests it.
- **A free hook landing on a lone Terminal** (e.g. Skull Boss): must be refused. Task 4 tests it.
- **Inverted:** holes and drop regions are the same in inverted; Task 2's sweep includes one inverted slice.

---

### Task 1: Drop Portal regions, fall doors, Terminals and entrance shuffle

**Files:**
- Create: `source/dungeon/DropPortals.py`
- Modify: `Regions.py:277` (Sewer Drop), `Regions.py:674-685` (Skull landings, add four Drop Portal regions next to them)
- Modify: `Doors.py` `create_doors` list (five `Hole` fall doors)
- Modify: `Dungeons.py:49-58` (`hyrule_castle_regions`), `Dungeons.py:125-131` (`skull_regions`)
- Modify: `data/terminals.yaml` (five entries; `floor_a4` and `blockset_aa1` on every landing block)
- Modify: `DoorShuffle.py` (`drop_falls` list; connect it in `link_doors_prep`, the vanilla branch near line 4856, and
  `handle_intensity_settings` near line 4995)
- Modify: `source/overworld/EntranceShuffle2.py:1990-1993, 2001` (`drop_map`), `:2411` (`mandatory_connections`),
  `:2479` (`default_connections`), `:2282-2286` (`dungeon_restriction_checks`), `:2814-2818` (`exit_ids`),
  `:690-697` (`determine_dungeon_restrictions`)
- Modify: `ItemList.py:602` (`connect_entrance` copy of the `exit_ids` lookup), `Utils.py:185-189` (dev table)
- Test: `test/dungeon/TestDropPortals.py`

**Interfaces:**
- Produces (`source/dungeon/DropPortals.py`):
  - `DropPortal` namedtuple `(region, fall, landing, terminal, entrance_id, owner)`, `drop_portals: list[DropPortal]`,
    `drop_portal_by_region: dict[str, DropPortal]`
  - `is_drop_portal(region) -> bool`, `is_lobby_portal(region) -> bool`, `is_outside(region) -> bool`,
    `entered_from_outside(entrance) -> bool`, `drop_parent_region(drop_portal_region) -> Region | None`,
    `sector_drop_portals(sector) -> list[Region]`
  - Terminal names `'<landing> Terminal'`; fall door names `'<Drop Portal region> Fall'`.

- [ ] **Step 1: Write the failing test**

```python
# test/dungeon/TestDropPortals.py
import logging
import os
import unittest

import yaml

import Main
from CLI import parse_cli
from source.classes.BabelFish import BabelFish
from source.dungeon.DropPortals import drop_portals, is_drop_portal, drop_parent_region

TERMINALS = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'terminals.yaml')
VANILLA_ROM = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'orig', 'z3.sfc')
VANILLA_HOLES = {'Skull Woods First Section Hole (North)': 'Skull Pot Circle Drop Portal',
                 'Skull Woods First Section Hole (West)': 'Skull Left Drop Drop Portal',
                 'Skull Woods First Section Hole (East)': 'Skull Pinball Drop Portal',
                 'Skull Woods Second Section Hole': 'Skull Back Drop Drop Portal',
                 'Sanctuary Grave': 'Sewers Drop Portal'}


def generate(extra=()):
    argv = ['--door_shuffle', 'crossed', '--intensity', '3', '--dungeon_shuffle_algorithm', 'experimental',
            '--key_logic_algorithm', 'experimental', '--suppress_rom', '--spoiler', 'none', *extra]
    logging.disable(logging.WARNING)
    try:
        for seed in range(1, 9):
            try:
                return Main.main(parse_cli(argv + ['--seed', str(seed)]), seed=seed, fish=BabelFish(lang='en'))
            except Exception:
                continue
    finally:
        logging.disable(logging.NOTSET)
    raise RuntimeError('no seed generated')


class TestDropPortals(unittest.TestCase):

    def test_vanilla_holes_lead_to_drop_portals(self):
        world = generate()
        for hole, portal in VANILLA_HOLES.items():
            with self.subTest(hole=hole):
                region = world.get_entrance(hole, 1).connected_region
                self.assertEqual(portal, region.name)
                self.assertTrue(is_drop_portal(region))
                self.assertIsNotNone(drop_parent_region(region))

    def test_shuffled_holes_still_lead_to_drop_portals(self):
        world = generate(['--shuffle', 'crossed'])
        targets = {world.get_entrance(h, 1).connected_region for h in VANILLA_HOLES}
        self.assertEqual({p.region for p in drop_portals}, {r.name for r in targets})

    def test_locked_falls_land_on_their_vanilla_landing(self):
        world = generate()
        for p in drop_portals:
            with self.subTest(drop=p.region):
                fall = world.get_door(p.fall, 1)
                self.assertIsNone(fall.pit_terminal)
                self.assertEqual(p.landing, fall.entrance.connected_region.name)

    def test_every_drop_has_a_terminal_with_a_full_landing(self):
        with open(TERMINALS) as f:
            entries = {e['name']: e for e in yaml.safe_load(f)['pits']}
        for p in drop_portals:
            with self.subTest(drop=p.region):
                entry = entries[p.terminal]
                self.assertEqual(p.landing, entry['region'])
                self.assertEqual([p.fall], entry['sources'])
                self.assertEqual(p.entrance_id, entry['rom']['entrance'])
                for key in ['floor_a4', 'blockset_aa1', 'room_id_a0', 'scroll_bounds']:
                    self.assertIn(key, entry['rom']['landing'])

    @unittest.skipUnless(os.path.exists(VANILLA_ROM), 'vanilla ROM not present')
    def test_drop_landings_match_the_vanilla_entrance_rows(self):
        from Rom import entrance_row_fields
        with open(VANILLA_ROM, 'rb') as f:
            rom = f.read()
        with open(TERMINALS) as f:
            entries = {e['name']: e for e in yaml.safe_load(f)['pits']}
        for p in drop_portals:
            with self.subTest(drop=p.region):
                for address, data in entrance_row_fields(p.entrance_id, entries[p.terminal]['rom']['landing']):
                    self.assertEqual(list(rom[address:address + len(data)]), data, hex(address))
```

`entrance_row_fields` is produced in Task 6; until then that one test is skipped by adding
`@unittest.skip('entrance_row_fields arrives in Task 6')` above it, removed in Task 6.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=.:source PYTHONHASHSEED=0 $PY -m unittest test.dungeon.TestDropPortals -v`
Expected: `ModuleNotFoundError: No module named 'source.dungeon.DropPortals'`

- [ ] **Step 3: Create the helper module**

```python
# source/dungeon/DropPortals.py
from collections import namedtuple

from BaseClasses import RegionType

# An overworld hole always leads to its Drop Portal; the portal's fall (a one-way Hole) lands on a Terminal.
DropPortal = namedtuple('DropPortal', ['region', 'fall', 'landing', 'terminal', 'entrance_id', 'owner'])

drop_portals = [
    DropPortal('Skull Pot Circle Drop Portal', 'Skull Pot Circle Drop Portal Fall', 'Skull Pot Circle',
               'Skull Pot Circle Terminal', 0x76, 'Skull Woods'),
    DropPortal('Skull Left Drop Drop Portal', 'Skull Left Drop Drop Portal Fall', 'Skull Left Drop',
               'Skull Left Drop Terminal', 0x77, 'Skull Woods'),
    DropPortal('Skull Pinball Drop Portal', 'Skull Pinball Drop Portal Fall', 'Skull Pinball',
               'Skull Pinball Terminal', 0x78, 'Skull Woods'),
    DropPortal('Skull Back Drop Drop Portal', 'Skull Back Drop Drop Portal Fall', 'Skull Back Drop',
               'Skull Back Drop Terminal', 0x79, 'Skull Woods'),
    DropPortal('Sewers Drop Portal', 'Sewers Drop Portal Fall', 'Sewers Rat Path',
               'Sewers Rat Path Terminal', 0x81, 'Hyrule Castle'),
]
drop_portal_by_region = {p.region: p for p in drop_portals}


def is_drop_portal(region):
    return region is not None and region.name in drop_portal_by_region


def is_lobby_portal(region):
    return region is not None and region.name.endswith(' Portal') and not is_drop_portal(region)


def is_outside(region):
    return region is not None and region.type in [RegionType.LightWorld, RegionType.DarkWorld] and region.name != 'Menu'


def entered_from_outside(entrance):
    """Whether entrance comes into the dungeon from the overworld, directly or through a hole's Drop Portal."""
    return is_outside(entrance.parent_region) or is_drop_portal(entrance.parent_region)


def drop_parent_region(drop_portal_region):
    """The overworld region whose hole leads to this Drop Portal (None until entrance shuffle connects it)."""
    return next((e.parent_region for e in drop_portal_region.entrances if is_outside(e.parent_region)), None)


def sector_drop_portals(sector):
    return [r for r in sector.regions if is_drop_portal(r)]
```

- [ ] **Step 4: Regions.** In `Regions.py`, replace line 277 with the Rat Path Drop Portal, and add the four Skull Drop
  Portals after `Skull Back Drop` (line 685):

```python
        create_dungeon_region(player, 'Sewers Drop Portal', 'Hyrule Castle', None, ['Sewers Drop Portal Fall']),
```

```python
        create_dungeon_region(player, 'Skull Pot Circle Drop Portal', 'Skull Woods', None, ['Skull Pot Circle Drop Portal Fall']),
        create_dungeon_region(player, 'Skull Left Drop Drop Portal', 'Skull Woods', None, ['Skull Left Drop Drop Portal Fall']),
        create_dungeon_region(player, 'Skull Pinball Drop Portal', 'Skull Woods', None, ['Skull Pinball Drop Portal Fall']),
        create_dungeon_region(player, 'Skull Back Drop Drop Portal', 'Skull Woods', None, ['Skull Back Drop Drop Portal Fall']),
```

  In `Dungeons.py`, append `'Sewers Drop Portal'` to `hyrule_castle_regions` (after `'Hyrule Castle East
  Portal'`, line 58) and the four Skull Drop Portal names to `skull_regions` (after `'Skull 3 Portal'`, line 130).

- [ ] **Step 5: Fall doors.** In `Doors.py` `create_doors`, next to `create_door(player, 'Skull Final Drop Hole', Hole)`
  (line 646), add:

```python
        create_door(player, 'Skull Pot Circle Drop Portal Fall', Hole),
        create_door(player, 'Skull Left Drop Drop Portal Fall', Hole),
        create_door(player, 'Skull Pinball Drop Portal Fall', Hole),
        create_door(player, 'Skull Back Drop Drop Portal Fall', Hole),
```

  and next to the Hyrule Castle doors:

```python
        create_door(player, 'Sewers Drop Portal Fall', Hole),
```

- [ ] **Step 6: Vanilla fall connections.** In `DoorShuffle.py`, after `dungeon_warps` (line 4187 block), add:

```python
# a hole's Drop Portal falls onto its vanilla landing unless drop lobbies shuffle
drop_falls = [(p.fall, p.landing) for p in drop_portals]
```

  (import `from source.dungeon.DropPortals import drop_portals` at the top). Connect them with `connect_terminal_door`
  in three places: `link_doors_prep` after the `dungeon_warps` loop (line 74), the `doorShuffle == 'vanilla'` branch
  after its `dungeon_warps` loop (line 4859), and `handle_intensity_settings` after its `dungeon_warps` block:

```python
    if drop_lobbies_locked(flags):
        for exitName, regionName in drop_falls:
            connect_terminal_door(world, exitName, regionName, player)
```

  (`drop_lobbies_locked` is imported from `source.dungeon.DungeonGenLocalSearch`.)

- [ ] **Step 7: Terminals.** Append to the `pits:` list in `data/terminals.yaml`. The landing values are the vanilla
  entrance rows, decoded per the spec's ROM table:

```yaml
  - name: Skull Pot Circle Terminal
    region: Skull Pot Circle
    sources:
      - Skull Pot Circle Drop Portal Fall
    rom:
      entrance: 0x76  # the hole's entrance row (EntranceData), not a LandingZoneData row
      landing:
        room_id_a0: 0x0058
        link_y_20: 0x0A69
        link_x_22: 0x1190
        scroll_x_e2: 0x1100
        scroll_y_e8: 0x0A00
        camera_y_618: 0x0077
        camera_x_61c: 0x017F
        layer_0476: 0x00
        bg_setting_ee: 0x00
        hv_scroll_a6: 0x00
        hv_scroll_a7: 0x02
        scroll_quad_a9: 0x01
        scroll_quad_aa: 0x00
        floor_a4: 0xFF
        blockset_aa1: 0x09
        scroll_bounds: [0x0A, 0x0A, 0x0A, 0x0B, 0x11, 0x10, 0x11, 0x11]

  - name: Skull Left Drop Terminal
    region: Skull Left Drop
    sources:
      - Skull Left Drop Drop Portal Fall
    rom:
      entrance: 0x77
      landing:
        room_id_a0: 0x0067
        link_y_20: 0x0C68
        link_x_22: 0x0E80
        scroll_x_e2: 0x0E00
        scroll_y_e8: 0x0C00
        camera_y_618: 0x0078
        camera_x_61c: 0x007F
        layer_0476: 0x00
        bg_setting_ee: 0x00
        hv_scroll_a6: 0x00
        hv_scroll_a7: 0x02
        scroll_quad_a9: 0x00
        scroll_quad_aa: 0x00
        floor_a4: 0xFF
        blockset_aa1: 0x09
        scroll_bounds: [0x0C, 0x0C, 0x0C, 0x0D, 0x0E, 0x0E, 0x0E, 0x0F]

  - name: Skull Pinball Terminal
    region: Skull Pinball
    sources:
      - Skull Pinball Drop Portal Fall
    rom:
      entrance: 0x78
      landing:
        room_id_a0: 0x0068
        link_y_20: 0x0C96
        link_x_22: 0x1100
        scroll_x_e2: 0x1088
        scroll_y_e8: 0x0C29
        camera_y_618: 0x00A1
        camera_x_61c: 0x0107
        layer_0476: 0x00
        bg_setting_ee: 0x00
        hv_scroll_a6: 0x02
        hv_scroll_a7: 0x02
        scroll_quad_a9: 0x01
        scroll_quad_aa: 0x00
        floor_a4: 0xFF
        blockset_aa1: 0x09
        scroll_bounds: [0x0C, 0x0C, 0x0C, 0x0D, 0x11, 0x10, 0x11, 0x11]

  - name: Skull Back Drop Terminal
    region: Skull Back Drop
    sources:
      - Skull Back Drop Drop Portal Fall
    rom:
      entrance: 0x79
      landing:
        room_id_a0: 0x0056
        link_y_20: 0x0A68
        link_x_22: 0x0D40
        scroll_x_e2: 0x0D00
        scroll_y_e8: 0x0A00
        camera_y_618: 0x0077
        camera_x_61c: 0x017F
        layer_0476: 0x00
        bg_setting_ee: 0x00
        hv_scroll_a6: 0x00
        hv_scroll_a7: 0x02
        scroll_quad_a9: 0x01
        scroll_quad_aa: 0x00
        floor_a4: 0xFF
        blockset_aa1: 0x09
        scroll_bounds: [0x0A, 0x0A, 0x0A, 0x0B, 0x0D, 0x0C, 0x0D, 0x0D]

  - name: Sewers Rat Path Terminal
    region: Sewers Rat Path
    sources:
      - Sewers Drop Portal Fall
    rom:
      entrance: 0x81
      landing:
        room_id_a0: 0x0011
        link_y_20: 0x031A
        link_x_22: 0x0393
        scroll_x_e2: 0x0300
        scroll_y_e8: 0x02AD
        camera_y_618: 0x0125
        camera_x_61c: 0x017F
        layer_0476: 0x00
        bg_setting_ee: 0x00
        hv_scroll_a6: 0x00
        hv_scroll_a7: 0x02
        scroll_quad_a9: 0x01
        scroll_quad_aa: 0x02
        floor_a4: 0xFF
        blockset_aa1: 0x01
        scroll_bounds: [0x03, 0x02, 0x03, 0x03, 0x03, 0x02, 0x03, 0x03]
```

  Add `floor_a4` and `blockset_aa1` to every existing landing block from its capture with this one-off script (run from
  the repo root; it keeps comments by editing lines):

```python
import json, re
caps = {t['label']: t for t in json.load(open('pit_warp_data_manual.json'))['transitions']}
out, cap = [], None
for line in open('data/terminals.yaml'):
    m = re.match(r"\s+capture: '([^']*)'", line)
    if m:
        cap = caps[m.group(1)]
    out.append(line)
    m = re.match(r'(\s+)scroll_quad_aa: ', line)
    if m and cap is not None:
        out.append(f"{m.group(1)}floor_a4: {cap['floor_a4']:#04X}\n".replace('0X', '0x'))
        out.append(f"{m.group(1)}blockset_aa1: {cap['blockset_aa1']:#04X}\n".replace('0X', '0x'))
        cap = None
open('data/terminals.yaml', 'w').writelines(out)
```

  Update the yaml header comment: `rom` holds `rows` (LandingZoneData rows) for pit/warp sources or `entrance` (the
  EntranceData row) for a hole's Drop Portal fall. In `test/dungeon/TestPitWarpRom.py`, the rows tests now skip entries
  that have `entrance` instead of `rows`, and the capture test skips entries without `capture`.

- [ ] **Step 8: Entrance shuffle.** In `source/overworld/EntranceShuffle2.py`:
  - `drop_map` (1990-1993, 2001) and `default_connections` (2479): hole → Drop Portal region (the `VANILLA_HOLES` map in
    the test).
  - `mandatory_connections` (2411): delete `('Sewer Drop', 'Sewers Rat Path')`; the fall is a door connected in Step 6.
  - `exit_ids` (2814-2818): key the five entries by Drop Portal region name, same IDs (`0x76`-`0x79`, `0x81`). Do the
    same in `ItemList.connect_entrance` (602) if it holds its own table, and in the dev table `Utils.py:185-189`.
  - `dungeon_restriction_checks` (2282-2286): Drop Portal region names in place of `'Sewer Drop'` and the four landings.
  - `determine_dungeon_restrictions` (690-697): the drop regions are now the Drop Portals, whose entrances come from the
    overworld directly, so its `parent_region.type in [LightWorld, DarkWorld]` test keeps working; confirm by test.

- [ ] **Step 9: Run the new tests**

Run: `PYTHONPATH=.:source PYTHONHASHSEED=0 $PY -m unittest test.dungeon.TestDropPortals -v`
Expected: PASS except the skipped ROM test. Failures here at this point are call sites from Task 2 (the landings are no
longer entered from the overworld); if generation fails, note which site and fix it in Task 2 before committing.

(No commit: Task 1 and Task 2 are one unit, "Section 1", committed and shown together.)

---

### Task 2: Generalize every "entered from outside" and portal-name check

**Files (each site from the catalog; replace the condition, keep the surrounding logic):**
- `BaseClasses.py:2180, 2202, 2211` (`Sector.branching_factor`, `is_entrance_sector`, `get_start_regions`)
- `DoorShuffle.py:1322, 1353` (`determine_entrance_list_vanilla`, `determine_entrance_list`), `:2387-2406`
  (`filter_start_regions`), `:368` (`_find_portal_for_region`: use `is_lobby_portal` + `removesuffix`, unless the
  generator session's fix has already landed), `:1421, 3481, 3564` (`endswith(' Portal')` BFS checks: Drop Portals must
  be traversed like portals, so these stay suffix-based; add a comment saying so), `:1764` (`convert_to_sectors`: only
  `'Enter '` exits register portals; unchanged), `:1650` (`palette_assignment` Rat Path BFS; unchanged)
- `DungeonGenerator.py:2566-2575` (`find_independent_entrances`), `source/dungeon/DungeonStitcher.py:55-66`
- `source/dungeon/SmallKeyDoorShuffle.py:325-344` (`filter_start_regions`)
- `source/dungeon/DungeonGenLocalSearch.py:903-911` (`drop_parent_region`: delete; callers use
  `DropPortals.drop_parent_region` on the Drop Portal region)
- `source/dungeon/DungeonStitcherV2.py:112-123` (`determine_entrance_regions`; full rework in Task 5, here only switch
  it to iterate `drop_portals` of the builder and use `DropPortals.drop_parent_region`)
- `source/dungeon/NewKeyLogic.py:604-610` (`_find_gateway_region`: stop at a region entered from outside, including a
  Drop Portal)
- `source/dungeon/EnemyList.py:2257` (`find_entrance_ids`: walk back through a Drop Portal to the hole)
- `KeyDoorShuffle.py:1719-1726` (`find_outside_connection`: `is_lobby_portal` instead of the `' Portal' in` substring)
- `Rules.py:104` (`mirrorless_path_to_castle_courtyard`: `'Sewers Drop Portal'`), `:2223-2229`
  (`drop_dungeon_entrances`: the five hole entrance names, which is what `get_rule_to_add` compares), `:2146`
  (`endswith('Portal')` → `is_lobby_portal`), `:2258-2259` (`bunny_revivable_entrances`: Drop Portal names)
- `test/dungeon/transitivity_witness.py:97-101, 114, 134` (`_overworld_drops`, `start_regions`: Drop Portals are drops)
- `District.py:136`, `Rom.py:1944`: the Rat Path Drop Portal now has a dungeon (Hyrule Castle); hint text for the
  Sanctuary Grave hole names Hyrule Castle, as the Skull holes already name Skull Woods. No code change; covered by
  the sweep.

**Interfaces:**
- Consumes: everything `DropPortals` produces (Task 1).

- [ ] **Step 1: One-off locked-mode check (not a committed test).** Before Task 1, record each seed's door
  connections (crossed i3 and i4 with `pit_warps: none`, seeds 1-6) with a scratch script; after Task 2, rerun and
  compare, reading a hole's connection into a Drop Portal as one into its landing. A committed layout snapshot would
  break on any unrelated change to the random draws.

- [ ] **Step 2: Run the comparison; expect differences until the sites are converted**

Run: `PYTHONPATH=.:source PYTHONHASHSEED=0 $PY -m unittest test.dungeon.TestDropPortals -v`

- [ ] **Step 3: Convert each site.** Replace, at each site above, the pattern

```python
(parent.type in [RegionType.LightWorld, RegionType.DarkWorld] and parent.name != 'Menu') or parent.name == 'Sewer Drop'
```

  (and its `!= RegionType.Dungeon` / walk-back variants) with `entered_from_outside(entrance)` or
  `is_outside(parent) or is_drop_portal(parent)`. Where code walks one step back from `'Sewer Drop'` to the overworld,
  use `drop_parent_region(drop_portal_region)`.

- [ ] **Step 4: Run all suites**

Run: `test/dungeon` and `test/overworld` with the Global Constraints command; then
`$PY source/tools/gen_check.py sweep --seeds 1-30 --workers 4 -- --door_shuffle crossed --intensity 3 --dungeon_shuffle_algorithm experimental --key_logic_algorithm experimental`
and the same with `--shuffle crossed`, with `--mode standard`, and with `--mode inverted`, on the commit before Task 1
and after Task 2. Expected: all tests PASS; the locked layouts match; sweep rates within noise of the baseline.

- [ ] **Step 5: Show the Section 1 diff to the user** (color-coded, line numbers, inline notes; side-by-side HTML at
  `analysis/phase3_section1_diff.html`), then on approval commit:

```bash
git add source/dungeon/DropPortals.py Regions.py Doors.py Dungeons.py data/terminals.yaml DoorShuffle.py \
  source/overworld/EntranceShuffle2.py ItemList.py Utils.py BaseClasses.py DungeonGenerator.py KeyDoorShuffle.py \
  Rules.py source/dungeon/*.py test/dungeon/TestDropPortals.py test/dungeon/TestPitWarpRom.py \
  test/dungeon/transitivity_witness.py
git commit -m "feat: route overworld holes through drop portals"
```

---

### Task 3: Unlock drops; pin Drop Portal sectors; describe them

**Files:**
- Modify: `source/dungeon/DungeonGenLocalSearch.py:914-917` (`drop_lobbies_locked`), `:160-161` (lock-down), `:1385-1391`
  (`default_lobby_drops` stays for the locked path)
- Modify: `source/dungeon/DungeonGenSectorDesc.py` (`analyze_sector`, `classify`)
- Test: `test/dungeon/TestDoorFlags.py`, `test/dungeon/TestDropPortals.py`

**Interfaces:**
- Produces: `drop_lobbies_locked(flags) -> bool` (real rule); `drop_portal_builders(name, dungeon_map, world, player)
  -> list[str]`; a Drop Portal sector's descriptor has `reachability[fall] == [(fall, Orange, Null)]` and is never a
  dead end.

- [ ] **Step 1: Failing tests**

```python
# test/dungeon/TestDoorFlags.py (replace the always-locked expectation)
    def test_drop_lobbies_unlock_with_lobbies_and_pits(self):
        for intensity, locked in [(1, True), (2, True), (3, True), (4, False)]:
            with self.subTest(intensity=intensity):
                self.assertEqual(locked, drop_lobbies_locked(DoorFlags.for_player(stub_world(intensity), 1)))
```

```python
# test/dungeon/TestDropPortals.py (add)
class TestDropPortalSectors(unittest.TestCase):

    def test_unlocked_drop_portals_stay_with_their_owner(self):
        world = generate_one_i4()
        for p in drop_portals:
            with self.subTest(drop=p.region):
                region = world.get_region(p.region, 1)
                owner = region.dungeon.name
                self.assertIn(owner, ['Skull Woods'] if p.owner == 'Skull Woods' else ['Hyrule Castle'])
```

  (`generate_one_i4` = `generate_one` at intensity 4, first seed of 1-8 that completes.)

- [ ] **Step 2: Run; expect FAIL** (`drop_lobbies_locked` returns True at intensity 4).

- [ ] **Step 3: Implement**

```python
def drop_lobbies_locked(flags):
    """Overworld drops keep their vanilla landing unless lobbies and pits both shuffle (pitwarps Phase 3)."""
    return not (flags.lobbies and flags.pit_warps in ('pits', 'both'))
```

  In `create_dungeon_builders` (near line 160), after the boss lock-down:

```python
    if drop_lobbies_locked(info.flags):
        lock_down_default_sectors(default_lobby_drops)
    else:
        for p in drop_portals:
            sector = find_sector(p.region, info.sector_pool)
            if sector:
                builders = drop_portal_builders(p, dungeon_map, world, player)
                propose_sector(dungeon_map[random.choice(builders)], sector, info, False, restrict_list=builders)
```

```python
def drop_portal_builders(p, dungeon_map, world, player):
    """Skull Drop Portals go with the front half when Skull Woods splits (it holds the destination portal that opens
    Skull Back's forest); the Rat Path Drop Portal may sit in either Hyrule Castle builder."""
    if p.owner == 'Skull Woods':
        return ['Skull Woods Front'] if 'Skull Woods Front' in dungeon_map else ['Skull Woods']
    return [b for b in ['Hyrule Castle', 'Hyrule Castle Sewers', 'Hyrule Castle Dungeon'] if b in dungeon_map]
```

  In `SectorDescriptor.analyze_sector`, before the outstanding-door loop:

```python
        for region in sector_drop_portals(self.sector):
            fall = next(ext.door for ext in region.exits if ext.door is not None)
            if fall in self.sector.outstanding_doors:  # entered from the overworld, crystals reset: like a portal
                self.reachability[fall].append((fall, CrystalBarrier.Orange, CrystalBarrier.Null))
                skip_doors.add(fall)
```

  In `classify`, skip `self.dead_end = True` when `sector_drop_portals(self.sector)` is non-empty.

- [ ] **Step 4: Run** `TestDoorFlags`, `TestDropPortals`; expect PASS.

(No commit yet: Tasks 3-5 are the generation unit, committed after Task 5.)

---

### Task 4: Transitivity starts, gating and free hooks; witness checker

**Files:**
- Modify: `source/dungeon/DungeonGenTransitivity.py` (`ConstraintInfo.__init__` near 136-200, `append_sector_free`
  426, `find_connectable_doors` 450, `connect_door` 624 and its enabled-portals block near 713)
- Modify: `test/dungeon/transitivity_witness.py`
- Test: `test/dungeon/TestDropPortalTransitivity.py`

**Interfaces:**
- Produces on `ConstraintInfo`: `drop_starts: list[Door]` (ungated falls), `dependent_lookup: dict[Door, list[Door]]`
  (was `Door -> Door`), `free_hooks: set[Door]` (falls that are never a route).

- [ ] **Step 1: Failing tests** (built on the `transitivity_harness` helpers used by `TestTransitivityVanilla`)

```python
# test/dungeon/TestDropPortalTransitivity.py
import unittest

from test.dungeon.transitivity_harness import build_world, sectors_for, check
from source.dungeon.DropPortals import drop_portal_by_region


class TestDropPortalTransitivity(unittest.TestCase):

    def test_ungated_drop_is_a_start(self):
        # Skull Woods front sectors with Pinball's Drop Portal unlocked: solvable with the drop as the only start
        world = build_world(intensity=4)
        self.assertTrue(check(world, 'Skull Woods', sectors_for(world, 'Skull Woods')))

    def test_gated_drop_needs_its_destination_portal(self):
        world = build_world(intensity=4)
        sectors = sectors_for(world, 'Skull Woods', without_portals=['Skull 2 West', 'Skull 3'])
        info = check(world, 'Skull Woods', sectors, return_info=True)
        fall = world.get_door(drop_portal_by_region['Skull Back Drop Drop Portal'].fall, 1)
        self.assertIn(fall, info.free_hooks)

    def test_free_hook_never_lands_on_a_lone_terminal(self):
        world = build_world(intensity=4, standard=True)
        info, solution = check(world, 'Hyrule Castle Sewers', sectors_for(world, 'Hyrule Castle Sewers'),
                               return_info=True, return_solution=True)
        fall = world.get_door(drop_portal_by_region['Sewers Drop Portal'].fall, 1)
        terminal = solution.connection_map[fall]
        sector = info.door_sector_map[terminal]
        self.assertGreater(len(sector.outstanding_doors), 1)
```

  If `transitivity_harness` lacks `build_world`/`sectors_for`/`check` with these keywords, add them there in this step
  (thin wrappers over the existing harness functions).

- [ ] **Step 2: Run; expect FAIL.**

- [ ] **Step 3: Implement.** In `ConstraintInfo.__init__`, classify each Drop Portal sector's fall:

```python
        self.drop_starts, self.free_hooks = [], set()
        outside_of = {}  # overworld region -> portal doors in this sector list that lead out onto it
        for s in sector_list:
            for p in s.portals:
                side = portal_overworld_side(p)
                if side is not None:
                    outside_of.setdefault(side, []).append(p.door)
        for s in sector_list:
            for region in sector_drop_portals(s):
                fall = next(ext.door for ext in region.exits if ext.door is not None)
                if fall not in s.outstanding_doors:
                    continue
                parent = drop_parent_region(region)
                escape_builder = flags.std_flag and builder.name in ['Hyrule Castle Sewers', 'Hyrule Castle Dungeon']
                if escape_builder or parent is None:
                    self.free_hooks.add(fall)
                elif parent.name not in parent.world.inaccessible_regions[parent.player]:
                    self.drop_starts.append(fall)
                elif parent in outside_of:
                    for enabler in outside_of[parent]:
                        self.dependent_lookup.setdefault(enabler, []).append(fall)
                else:
                    self.free_hooks.add(fall)
```

  where `portal_overworld_side(portal)` returns the non-dungeon region the portal region exits onto (the witness
  checker's `_overworld_side`, moved into `DropPortals.py` so both use one rule). Convert the existing
  `dependent_lookup[enabling_portal.door] = d` to `.setdefault(..., []).append(d)` and the enabled-portals block in
  `connect_door` to loop over the list.

  Seed starts in `do_transitivity_check_main` after the init portals:

```python
    for fall in c_info.drop_starts + sorted(c_info.free_hooks, key=lambda d: d.name):
        if fall in t.remaining_doors:
            t.remaining_doors.remove(fall)
            t.unconnected_doors[fall] = CrystalBarrier.Orange
```

  In `find_connectable_doors`, for a free hook as `available`, only allow a Terminal hanger whose sector has another
  outstanding door:

```python
                if available in c_info.free_hooks:
                    if is_terminal(d) and len(c_info.door_sector_map[d].outstanding_doors) > 1:
                        connectable_doors.append((d, available))
                    continue
```

  In `connect_door`, a free hook records the connection, removes the hanger from `remaining_doors`/`unconnected_doors`,
  satisfies the hanger's constraints, and propagates nothing:

```python
        if hook in c_info.free_hooks:
            t.unconnected_doors.pop(hook)
            if hanger in t.remaining_doors:
                t.remaining_doors.remove(hanger)
            t.unconnected_doors.pop(hanger, None)
            t.satisfy_constraints(hanger, hook, c_info)
            return t
```

  (Extract the existing "deal with newly satisfied constraints" block into `satisfy_constraints(hanger, hook, c_info)`
  so both paths share it.) `some_door_never_reachable` treats free hooks as reached hooks that reach nothing: an
  over-approximation, so pruning stays sound.

  Witness checker: a drop is a start under the same three-way rule (import the shared helpers); a free hook's
  connection is not explored.

- [ ] **Step 4: Run** `TestDropPortalTransitivity`, `TestTransitivityVanilla`, `TestTransitivityWitness`,
  `TestTransitivityOracle`; expect PASS.

---

### Task 5: Stitcher and key/trap stages

**Files:**
- Modify: `source/dungeon/DungeonStitcherV2.py:112-123` (`determine_entrance_regions`)
- Modify: `DoorShuffle.py:3497-3545` (`find_accessible_entrances`, `find_possible_entrances`)
- Test: `test/dungeon/TestDropPortals.py`

- [ ] **Step 1: Failing test**

```python
class TestDropEntrances(unittest.TestCase):

    def test_stages_credit_drops_to_their_dungeon(self):
        from DoorShuffle import find_possible_entrances
        world = generate_one_i4()
        for name, builder in world.dungeon_layouts[1].items():
            drops = [r.name for s in builder.sectors for r in sector_drop_portals(s)]
            with self.subTest(builder=name):
                self.assertTrue(set(drops) <= set(find_possible_entrances(world, 1, builder)))
```

- [ ] **Step 2: Run; expect FAIL.**

- [ ] **Step 3: Implement.** `determine_entrance_regions`: replace the `default_lobby_drops` loop with

```python
    for s in builder.sectors:
        for region in sector_drop_portals(s):
            parent = drop_parent_region(region)
            if std_flag and builder.name in ['Hyrule Castle Sewers', 'Hyrule Castle Dungeon']:
                continue
            if parent is not None and (parent.name not in world.inaccessible_regions[player] or single_entrance_flag):
                entrance_regions.append(region)
```

  plus, for gated drops, append the Drop Portal region once the traversal reaches a portal whose overworld side is
  `parent` (mirror Task 4's rule in the stitcher's exploration). `find_possible_entrances` / `find_accessible_entrances`:
  replace `drop_entrances[builder.name]` with the Drop Portal region names in `builder.sectors`.

- [ ] **Step 4: Run** `test/dungeon`; then a 40-seed `gen_check` sweep at crossed i4. Compare against the Task 2 baseline.

- [ ] **Step 5: Show the generation diff (Tasks 3-5) to the user**, then on approval commit:

```bash
git commit -m "feat: shuffle overworld drop landings"
```

---

### Task 6: ROM entrance rows for shuffled drops

**Files:**
- Modify: `Rom.py` (new `entrance_row_fields`, `write_drop_entrances`; call next to `write_pitwarps`)
- Test: `test/dungeon/TestPitWarpRom.py`, `test/dungeon/TestDropPortals.py` (remove the skip from Task 1)

**Interfaces:**
- Produces: `entrance_row_fields(entrance_id, landing) -> list[tuple[int, list[int]]]` (pc address, bytes);
  `write_drop_entrances(world, rom, player)`.

- [ ] **Step 1: Failing test**

```python
class TestWriteDropEntrances(unittest.TestCase):

    def test_shuffled_drop_writes_its_landing_and_nothing_else(self):
        world, entries = stub_drop_world({'Skull Pinball Terminal': 'Ice Boss Terminal'})
        rom = RecordingRom()
        write_drop_entrances(world, rom, 1)
        expected = dict(entrance_row_fields(0x78, entries['Ice Boss Terminal']['rom']['landing']))
        self.assertEqual(expected, rom.writes)

    def test_unshuffled_drops_write_nothing(self):
        world, entries = stub_drop_world({})
        rom = RecordingRom()
        write_drop_entrances(world, rom, 1)
        self.assertEqual({}, rom.writes)
```

  (`stub_drop_world` mirrors `stub_world` in the same file: a fall source whose `group` is its vanilla Terminal and
  whose `pit_terminal` is the assigned one.)

- [ ] **Step 2: Run; expect FAIL** (`ImportError`).

- [ ] **Step 3: Implement**

```python
ENTRANCE_WORDS = {'room_id_a0': 0x14577, 'scroll_x_e2': 0x14AA9, 'scroll_y_e8': 0x14BB3, 'link_y_20': 0x14CBD,
                  'link_x_22': 0x14DC7, 'camera_y_618': 0x14ED1, 'camera_x_61c': 0x14FDB}
ENTRANCE_BOUNDS = 0x14681
ENTRANCE_BYTES = {'blockset_aa1': 0x150E5, 'floor_a4': 0x1516A}
ENTRANCE_LAYER, ENTRANCE_SCROLL_CONTROL, ENTRANCE_QUADRANT = 0x152F9, 0x1537E, 0x15403


def entrance_row_fields(entrance_id, landing):
    """(pc address, bytes) of a drop entrance's EntranceData row from a landing block; dungeon, in-door, overworld door
    tilemap and song are the owning dungeon's and stay vanilla."""
    fields = [(base + entrance_id * 2, int16_as_bytes(landing[key])) for key, base in ENTRANCE_WORDS.items()]
    fields.append((ENTRANCE_BOUNDS + entrance_id * 8, list(landing['scroll_bounds'])))
    fields += [(base + entrance_id, [landing[key]]) for key, base in ENTRANCE_BYTES.items()]
    fields.append((ENTRANCE_LAYER + entrance_id, [landing['bg_setting_ee'] << 4 | landing['layer_0476']]))
    fields.append((ENTRANCE_SCROLL_CONTROL + entrance_id, [landing['hv_scroll_a6'] << 4 | landing['hv_scroll_a7']]))
    fields.append((ENTRANCE_QUADRANT + entrance_id, [landing['scroll_quad_a9'] << 4 | landing['scroll_quad_aa']]))
    return fields


def write_drop_entrances(world, rom, player):
    """Writes the entrance row of every shuffled drop, even one landing on its own vanilla landing (as write_pitwarps)."""
    for p in drop_portals:
        fall = world.get_door(p.fall, player)
        if fall.pit_terminal is None:
            continue
        for address, data in entrance_row_fields(p.entrance_id, fall.pit_terminal.pitwarp_rom['landing']):
            rom.write_bytes(address, data)
```

  `write_pitwarps` must skip falls (their vanilla Terminal has `entrance`, not `rows`): guard with
  `if 'rows' not in vanilla.pitwarp_rom: continue`. Call `write_drop_entrances(world, rom, player)` right after
  `write_pitwarps`.

- [ ] **Step 4: Run** `TestPitWarpRom`, `TestDropPortals` (ROM round-trip now active); expect PASS.

- [ ] **Step 5: Show the diff; on approval commit** (stage `Rom.py` without the user's hash hunk):
  `git commit -m "feat: write shuffled drop landings to the entrance rows"`

---

### Task 7: Verification and docs

- [ ] **Step 1:** Transitivity verification bar at intensity 4 with drops (13 vanilla dungeons, 78 pairs, real
  LocalSearch calls seeds 1-12 with every True checked by the witness checker). Record results in
  `docs/plans/transitivity_pitwarp_verification.md` (current-truth, replacing the drop-lobby items under "Open work").
- [ ] **Step 2:** `gen_check` sweeps: crossed i4 seeds 1-40 (before = Task 2 commit, after = Task 6), standard i4, and
  `--shuffle crossed` i4, seeds 1-20 each. Then one TestSuite run when the other session has none running.
- [ ] **Step 3:** One emulator test seed in `test_games/` with drops landing away from vanilla, plus a notes file
  listing hole → landing; the user checks landing position, falling animation, graphics, floor and music.
- [ ] **Step 4:** Update `docs/plans/pitwarps_feature.md` Phase 3 to done-state and the project memory; show the diff;
  commit `docs: record pitwarps phase 3 verification`.
