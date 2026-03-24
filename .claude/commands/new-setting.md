# Add a New Setting

Use this checklist when adding a new per-player setting to the Door Randomizer.
The example setting name used throughout is `my_setting` with choices `vanilla | pooled | crossed` and default `pooled`.

---

## 1. CLI argument — `resources/app/cli/args.json`

Add an entry before a nearby related argument:

```json
"my_setting": {
  "choices": ["vanilla", "pooled", "crossed"]
},
```

---

## 2. CLI passthrough and defaults — `CLI.py`

Two places:

**Passthrough list** (search for a nearby setting, add after it):
```python
'my_setting',
```

**`parse_settings()` defaults dict** (same pattern):
```python
'my_setting': 'pooled',
```

---

## 3. World attribute — `Main.py`

Two places:

**`main()` after world setup** (near other `world.<setting> = args.<setting>.copy()`):
```python
world.my_setting = args.my_setting.copy()
```

**`copy_world()`** (near other `ret.<setting> = world.<setting>.copy()`):
```python
ret.my_setting = world.my_setting.copy()
```

---

## 4. BaseClasses.py — three places

**Per-player default** in `set_player_attr` block:
```python
set_player_attr('my_setting', 'pooled')
```

**Spoiler header** in `to_json()` / spoiler dict:
```python
'my_setting': self.world.my_setting,
```

**Settings hash encoding** — find byte 13 (or whichever byte has free bits) in `make_code` and `adjust_args_from_code`:

```python
# Near top of make_code, add a mode dict:
my_setting_mode = {'vanilla': 0, 'pooled': 1, 'crossed': 2}

# In make_code byte packing:
| my_setting_mode[w.my_setting[p]] << N   # N = bit offset

# Update the byte comment:
# byte 13: SSDD MDDT  (update the legend)

# In adjust_args_from_code decode:
args.my_setting[p] = r(my_setting_mode)[(settings[13] & MASK) >> N]
```

Notes:
- `r(d)` is a reverse-dict helper already in the file
- Each new 2-bit field needs 2 contiguous free bits; track which bits are used in the byte comment
- Guards like `if len(settings) > 13:` protect against old codes — add one if using a new byte

---

## 5. CustomSettings.py — `source/classes/CustomSettings.py`

Two places (search for a nearby setting):

**Reading from customizer file:**
```python
args.my_setting[p] = get_setting(settings['my_setting'], args.my_setting[p])
```

**Exporting to settings dict:**
```python
settings_dict[p]['my_setting'] = world.my_setting[p]
```

---

## 6. Core logic

Implement the actual behavior wherever the setting is consumed (e.g. `DoorShuffle.py`).
Pattern used for `door_type_distribution` in `main_dungeon_pool()`:

```python
dist = world.my_setting[player]
if dist == 'vanilla':
    # restructure pools for vanilla behavior
elif dist == 'crossed':
    # restructure pools for crossed behavior
# 'pooled' (default) requires no change — it is the existing behavior
```

---

## 7. `source/classes/constants.py` — `SETTINGSTOPROCESS`

Add the GUI widget name → setting name mapping in the appropriate page section
(`randomizer.dungeon`, `randomizer.entrance`, etc.):

```python
"my_setting": "my_setting",
```

---

## 8. GUI widget — `resources/app/gui/randomize/dungeon/widgets.json`

Add after the nearest related widget:

```json
"my_setting": {
  "type": "selectbox",
  "default": "pooled",
  "options": ["vanilla", "pooled", "crossed"],
  "config": {
    "width": 45,
    "padx": [20, 0]
  }
},
```

For checkboxes the pattern is simpler:
```json
"my_setting": {
  "type": "checkbox",
  "config": { "padx": [20, 0] }
},
```

---

## 9. CLI help text — `resources/app/cli/lang/en.json`

Add to the `"help"` section near related settings:

```json
"my_setting": [
  "My Setting description (default: %(default)s)",
  "vanilla: Each dungeon keeps its own counts",
  "pooled:  Redistribute within each pool",
  "crossed: Redistribute across all dungeons"
],
```

---

## 10. GUI labels — `resources/app/gui/lang/en.json`

Add near related settings in the `"gui"` section:

```json
"randomizer.dungeon.my_setting": "My Setting Label",
"randomizer.dungeon.my_setting.vanilla": "Vanilla (Per-Dungeon)",
"randomizer.dungeon.my_setting.pooled": "Pooled (Within Pool)",
"randomizer.dungeon.my_setting.crossed": "Crossed (All Dungeons)",
```

For a checkbox, only the base key is needed (no option sub-keys).

---

## Checklist

- [ ] `resources/app/cli/args.json` — choices
- [ ] `CLI.py` — passthrough list + defaults
- [ ] `Main.py` — world attr assignment + copy_world
- [ ] `BaseClasses.py` — per-player default + spoiler + settings hash (make_code + adjust_args_from_code)
- [ ] `source/classes/CustomSettings.py` — read + export
- [ ] Core logic implementation
- [ ] `source/classes/constants.py` — `SETTINGSTOPROCESS` mapping
- [ ] `resources/app/gui/randomize/dungeon/widgets.json` — widget
- [ ] `resources/app/cli/lang/en.json` — help text
- [ ] `resources/app/gui/lang/en.json` — GUI labels
- [ ] Docs update (e.g. `docs/NewGeneration.md`) if user-facing
