---
layout: default
title: Features
nav_order: 2
---

# Features Guide
{: .no_toc }

Comprehensive documentation of all Door Randomizer features and settings.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Important Differences from Other Randomizers

Most of these apply only when door shuffle is not vanilla.

### Starting Item

You start with a **Mirror Scroll** (looks like a map), a simplified mirror that only works in dungeons, not the overworld, and can't erase blocks like the Mirror.

### Navigation Changes

- Holes in Mire Torches Top and Mire Torches Bottom fall through to rooms below (you only need fire to get the chest)
- You can Hookshot from the left Mire wooden Bridge to the right one
- In the PoD Arena, you can bonk with Boots between the two blue crystal barriers against the ladder to reach the Arena Bridge chest and door (Bomb Jump also possible but not in logic - Boots are required)
- Flooded Rooms in Swamp can be traversed backward and may be required. Flippers are needed to get out of the water

### Logic Differences

- The chest in southeast Skull Woods that is traditionally a guaranteed Small Key in ER is not guaranteed here
- Fire Rod is not in logic for dark rooms (hard enough to figure out which dark room you are in)
- The hammerjump (and some other skips) are not in logic by default (see the mixed_travel setting for details). Doing so in a crossed dungeon seed can put you into another dungeon with the wrong dungeon id

### Boss Differences

- You have to find the attic floor and bomb it open and bring the maiden to the light to fight Blind. In cross dungeon door shuffle, the attic can be in any dungeon. If you bring the maiden to the boss arena, she will hint where the cracked floor can be found
- GT Bosses do not respawn after killing them in this mode
- Enemizer change: The attic/maiden sequence is now active and required when Blind is the boss of Thieves' Town even when bosses are shuffled

### Crystal Switches

- You can hit the PoD crystal switch in the Sexy Statue room with a bomb from the balcony above without jumping down
- GT Crystal Conveyor room (it has gibdos) - You can hit the crystal switch with a bomb when the blue barrier is up from the far side so you can leave the room to the left with blue barriers down
- PoD Arena Bridge - If entering from the bridge, you can circle round and hit the switch, then fall into the hole to respawn at the bridge again with the crystal barriers different

---

## Dungeon Settings

### Door Shuffle

Controls how dungeon doors are shuffled:

- **Vanilla** - Doors are not shuffled
- **Basic** - Doors are shuffled only within a single dungeon
- **Partitioned** - Dungeons are shuffled in 3 pools: Light World, Early Dark World, Late Dark World (Late Dark are the four dungeons that require Mitts in vanilla, including Ganon's Tower)
- **Crossed** - Doors are shuffled between dungeons as well

CLI: `--doorShuffle [vanilla|basic|partitioned|crossed]`

### Intensity

Controls which types of connections are shuffled:

- **Level 1** - Normal doors and spiral staircases are shuffled
- **Level 2** - Same as Level 1 plus open edges and both types of straight staircases are shuffled
- **Level 3** - Same as Level 2 plus Dungeon Lobbies are shuffled

CLI: `--intensity [1|2|3]`

### Door Type Shuffle

Controls which types of doors can be shuffled (only active if door shuffle is not vanilla):

- **Small Key Doors, Bomb Doors, Dash Doors** - Standard shuffled doors
- **Adds Big Key Doors** - Big key doors are now shuffled in addition to those above
- **Adds Trap Doors** - All trap doors that are permanently shut in vanilla are shuffled, excluding boss trap doors
- **Increases all Door Types** - Chaos mode where each door type per dungeon is randomized between 1 less and 4 more

CLI: `--door_type_mode [original|big|all|chaos]`

### Trap Door Removal

Options for making dungeon traversal more convenient:

- **No Removal** - Does not remove any trap doors
- **Removed If Blocking Path** - Dungeon generation removes annoying trap doors if necessary (boss trap doors never shuffled)
- **Remove Boss Traps** - Boss traps are removed, including the one near Mothula
- **Remove All Annoying Traps** - Removes all trap doors that are annoying, including boss traps

CLI: `--trap_door_mode [vanilla|optional|boss|oneway]`

### Dungeon Items

#### Small Keys

- **In Dungeon** - Small keys are restricted to their own dungeon
- **Randomized** - Small keys can be found anywhere
- **Universal** - Small keys work in any dungeon, can be found anywhere, and at least one shop will sell keys (like original Legend of Zelda)

CLI: `--keyshuffle [none|wild|universal]`

All other dungeon items (maps, compasses, Big Keys) can be restricted to their own dungeon or shuffled in the general pool.

### Key Logic Algorithm

Determines how small key door logic works:

- **Partial Protection** - Assumes you always have full inventory and worst case usage. Accounts for dark room and bunny revival glitches
- **Strict** - Small key doors require all small keys to be available to be in logic
- **Dangerous** - Assumes you never use keys out of logic (not recommended)

CLI: `--key_logic [partial|strict|dangerous]`

### Decouple Doors

Similar to insanity mode in ER where door entrances and exits are not paired anymore. Tends to remove more logic from dungeons as many rooms will not be required to traverse.

CLI: `--decoupledoors`

### Allow Self-Looping Spiral Stairs

If enabled, spiral stairs are allowed to lead to themselves.

CLI: `--door_self_loops`

### Experimental Features

You will start as a bunny if your spawn point is in the dark world.

CLI: `--experimental`

### Crossed Dungeon Specific Settings

#### Dungeon Chest Counters

- **Auto** - Picks an appropriate setting based on other settings
- **On** - Dungeon counters on HUD always displayed
- **Off** - Dungeon counters on HUD never displayed
- **On Compass Pickup** - Dungeons with a compass item will display the counter once the compass is found

CLI: `--dungeon_counters [auto|on|off|pickup]`

#### Mixed Travel

Controls Hammerjump, PoD Arena hovering, and Mire Big Key Chest bomb jump:

- **Prevent (default)** - Rails are added to prevent these tricks. Recommended for those learning crossed dungeon mode
- **Allow** - Rooms are left alone and it is up to player discretion whether to use these tricks
- **Force** - The two disjointed sections are forced to be in the same dungeon but the glitches are never logically required

CLI: `--mixed_travel [prevent|allow|force]`

#### Standardize Palettes

- **Standardize (default)** - Rooms in the same dungeon have their palettes changed to match
- **Original** - Rooms/supertiles keep their original palettes

CLI: `--standardize_palettes`

---

## Pool Expansions

### Pottery

Controls which pots (and large blocks) are in the locations pool:

- **None** - No pots are in the pool, like normal randomizer
- **Key Pots** - The pots that have keys are in the pool
- **Cave Pots** - The pots that are not found in dungeons are in the pool (includes Spike Cave large block)
- **Cave + Keys Pots** - Both non-dungeon pots and pots that used to have keys
- **Reduced Dungeon Pots** - Cave+Keys plus roughly 25% of dungeon pots (dynamic mode with colored pots)
- **Clustered Dungeon Pots** - Like reduced but pots grouped by logical sets, roughly 50% chosen (dynamic mode)
- **Excludes Empty Pots** - All pots that had some sort of objects under them
- **Dungeon Pots** - The pots that are in dungeons
- **Lottery** - All pots and large blocks are in the pool

CLI: `--pottery [none|keys|cave|cavekeys|reduced|clustered|nonempty|dungeon|lottery]`

#### Colorize Pots

Colors the pots that have been chosen to be part of the location pool. Forced on for dynamic modes (clustered and reduced).

CLI: `--colorizepots`

### Shuffle Enemy Drops

Controls whether enemies that drop items are randomized:

- **None** - Special enemies drop keys normally
- **Keys** - Enemies that drop keys are added to the randomization pool (includes Hyrule Castle Big Key)
- **Underworld** - Enemies in the underworld are added to the randomization pool. Blue square indicates if there are any enemies on the supertile that still have an available drop

CLI: `--dropshuffle [none|keys|underworld]`

### Shopsanity

Adds 32 shop locations (9 more in retro) to the general location pool. Multi-world supported.

Shop locations include:
- Lake Hylia Cave Shop (3 items)
- Kakariko Village Shop (3 items)
- Potion Shop (3 new items)
- Paradox Cave Shop (3 items)
- Capacity Upgrade Fairy (2 items)
- Dark Lake Hylia Shop (3 items)
- Curiosity/Red Shield Shop (3 items)
- Dark Lumberjack Shop (3 items)
- Dark Potion Shop (3 items)
- Village of Outcast Hammer Peg Shop (3 items)
- Dark Death Mountain Shop (3 items)

[See README for complete pricing guide and mechanics](/README#shopsanity)

### Take Any Caves

Three options: None, Random, and Fixed. Fixed means take any caves replace specific fairy caves:

- Desert Healer Fairy
- Swamp Healer Fairy (aka Light Hype Cave)
- Dark Death Mountain Healer Fairy
- Dark Lake Hylia Ledge Healer Fairy (aka Shopping Mall Bomb)
- Bonk Fairy (Dark)

---

## Item Randomization

### New "Items"

#### Bomb Bag

Two bomb bags are added to the item pool (look like +10 Capacity upgrades). Bombs are unable to be used until one is found.

CLI: `--bombbag`

#### Pseudo Boots

Dashing is allowed without the boots item however doors and certain rocks remain unopenable until boots are found. Specific sequence breaks like hovering and water-walking are not allowed until boots are found.

CLI: `--pseudoboots`

#### Mirror Scroll

Mirror is usable inside dungeons. Locations that require the mirror are still unattainable.

CLI: `--mirrorscroll`

#### Flute Mode

- **Normal** - Need to activate it at the village statue after finding it
- **Activated** - Can use it immediately upon finding it

CLI: `--flute_mode`

#### Bow Mode

- **Progressive** - Standard progressive bows
- **Silvers separate** - One bow in the pool and silvers are a separate item
- **Retro (progressive)** - Arrows cost rupees, need to purchase single arrow item at shop
- **Retro + Silvers** - Arrows cost rupees, one bow, silvers are separate item

CLI: `--bow_mode [progressive|silvers|retro|retro_silvers]`



### Goal Options

- **Trinity** - Find one of 3 triforces to win (pedestal, Ganon, or Murahdahla with 8 of 10 pieces)
- **Ganonhunt** - Collect the requisite triforce pieces, then defeat Ganon (Aga2 not required)
- **Completionist** - Obtain every item in the game and defeat Ganon (forces 100% accessibility)

### Item Sorting (Fill Algorithms)

Controls how items are placed in the world:

#### Balanced

Most random distribution of items (recommended).

#### Vanilla Fill

Attempts to place all items in their vanilla locations when possible. If not possible, prefers "major" locations, then heart piece locations, then the rest.

#### Major Location Restriction

Attempts to place major items in major locations. Major locations are where major items are found in the vanilla game.

#### Dungeon Restriction

Attempts to place all major items in dungeons. Overflows to overworld if necessary.

#### District Restriction

The world is divided into different regions/districts. Districts are chosen at random and filled with major items. Single green rupees indicate chosen districts.

CLI: `--algorithm [balanced|vanilla_fill|major_only|dungeon_only|district]`

### Forbidden Boss Items

Restrict items that can appear on bosses:

- **None** - Boss may have any item
- **MapCompass** - Map and compass are logically required to defeat a boss (currently bugged)
- **Dungeon** - Small keys and big keys of the dungeon are not allowed on a boss

CLI: `--restrict_boss_items [none|mapcompass|dungeon]`

---

## Entrance Randomization

### New Modes

- **Lite** - Non item entrances are vanilla, dungeons/caves grouped with restrictions
- **Lean** - Same grouping as Lite but cross-world connections allowed
- **Swapped** - Entrances are swapped with each other

### Shuffle Links House

In certain ER shuffles (not dungeonssimple or dungeonsfulls), control whether Links House is shuffled or remains vanilla.

### Skull Woods Shuffle

Options to reduce annoying Skull Woods layouts:

- **Original** - Skull woods shuffles classically amongst itself unless insanity mode
- **Restricted** - Skull woods drops are vanilla, entrances stay in skull woods and are shuffled
- **Loose** - Skull woods drops are vanilla, main ER mode's pool determines handling
- **Followlinked** - Follows Linked Drops setting

### Linked Drops Override

Controls whether drops should be linked to nearby entrances:

- **Unset** - Uses the mode's default (linked for all modes except insanity)
- **Linked** - Forces drops to be linked to their entrances
- **Independent** - Decouples drops from entrances

### Overworld Map

Option to move indicators on overworld map to reference dungeon location:

- **Default** - Showing only the prize markers on vanilla dungeon locations
- **Compass** - Compass item controls whether marker is moved to dungeon locations
- **Map** - Map item shows both prize and location of the dungeon

CLI: `--overworld_map [default|compass|map]`

---

## Enemizer

Enemizer has been incorporated into the generator. See [Enemizer in DR documentation](https://docs.google.com/document/d/1iwY7Gy50DR3SsdXVaLFIbx4xRBqo9a-e1_jAl5LMCX8/edit?usp=sharing) for extensive details.

### Enemy Shuffle

Enemies are shuffled with an enemy ban list that prevents problematic placements (blocking paths, unavoidable damage, glitches).

### Enemy Damage

The shuffled setting actually shuffles the damage table unlike the original enemizer.

### Boss Shuffle: Unique

Bosses are shuffled with some exceptions:
- Trinexx is not allowed on GT basement when DR is enabled
- Harder bosses in GT basement have logic concessions for low percentage requirements

New variant: At least one boss of each type for prize bosses will be present guarding prizes.

### Enemy Health

Health is taken into account for challenge rooms if magic or ammo is required.

### Enemy Logic

Can account for logical access to challenge rooms and item/key drops when enemies are shuffled:

- **Forbid special enemies** - Special enemies disallowed from drops and challenge rooms
- **Item drops may have special enemies** - Challenge rooms won't have special enemies, but drops may
- **Allow special enemies anywhere** - Both challenge rooms and enemy drops can have special requirements

---

## Glitched Logic

CLI: `--logic [noglitches|owglitches|hybridglitches|nologic]`

### Overworld Glitches

Includes overworld teleports, clips, superbunny, mirror to access Desert Palace East Entrance, bunny pocket access, etc.

### Hybrid Major Glitches

**Not compatible with Door Shuffle**

Includes all Overworld Glitches logic plus:
- Kikiskip to access PoD without MP or DW access
- IP Lobby clip to skip fire requirement
- Various traversals between dungeons (TT ↔ Desert, Spec rock, Paradox, Mire ↔ Hera ↔ Swamp)
- Stealing SK from Mire to open SP
- Using Mire big key to open Hera doors

---

## Game Options

### MSU Resume

Turns on MSU resume support.

CLI: `--msu_resume`

### Collection Rate

Display the collection rate unless the triforce piece counter is needed.

CLI: `--collection_rate`

### Reduce Flashing

Accessibility option to reduce some flashing animations in the game.

CLI: `--reduce_flashing`

### Shuffle Sound Effects

Shuffles a large portion of the sound effects. Can be used with the adjuster.

CLI: `--shuffle_sfx`

---

## Customizer

Create custom seeds with custom dungeons and rooms.

See [Customizer documentation](Customizer.md) for details.

---

## Generation Setup & Miscellaneous

### Create BPS Patches

Create BPS patch(es) instead of generating ROM(s) for distribution.

CLI: `--bps`

### Triforce Hunt Settings

Controls for triforce piece pool:
- `--triforce_goal_min` / `--triforce_goal_max` - Pieces to collect to win
- `--triforce_pool_min` / `--triforce_pool_max` - Pieces in item pool
- `--triforce_min_difference` / `--triforce_max_difference` - Difference between pool and goal

### Seed

Set a seed number to generate. Same seed with same settings on same version will always yield identical output.

### Count

Batch generate multiple seeds with same settings. If seed number provided, it will be used to derive subsequent seeds.
