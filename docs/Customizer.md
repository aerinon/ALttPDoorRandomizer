## Customizer Files

A customizer file is [yaml file](https://yaml.org/) with different settings. This documentation is intended to be read with an [example customizer file](customizer_example.yaml).

This can also be used to roll a mystery or mutli-mystery seed via the GUI. [Example](multi_mystery_example.yaml)

The cli includes a couple arguments to help:

`--print_template_yaml` will create a yaml file based on the settings used. This does not contain any seed specific information.

Present on the GUI as `Export Yaml` on the bottom.

`--print_custom_yaml` will create a yaml file based on the seed rolled. Treat it like a spoiler.

`--customizer` takes a file as an argument. 

Present on the GUI as `Print Customizer File` and `Customizer File` on the Generation Setup tab.

### meta

Supported values:

* `players`: number of players
* `seed`: you can set the seed number for a set experience on things that are randomized instead of specified
* `algorithm`: fill algorithm
* `names`: for naming mutliworld players

###### Not Yet Implemented

* `mystery`: indicates the seed should be treated as a mystery (hides total collection_rate) (This may end up player specific)

### settings

This must be defined by player. Each player number should be listed with the appropriate settings.

in each player section you can set up default settings for that player or you can specify a mystery yaml file.

```
1: player1.yaml 
2:
  shuffle: crossed
  door_shuffle: basic   
```

Player 1's settings will be determined by rolling the mystery weights and player 2's setting will be default except for those two specified in his section. Each setting should be consistent with the CLI arguments. Simple weighted settings are supported here. If you need sub-weights though, use a separate yaml file.

Start inventory is not supported here. It has a separate section.

#### Extra Settings

Some settings are intended to only be accessed using the customizer:

* `aga_randomness` setting this to false, turns off blue balls and ganon warp randomness
* `money_balance` this is a percent (0-100). For numbers less than 100, both price balancing and money balancing will only attempt to ensure the player has access to only a percentage of the required funds. When 0, this should effectively disable money balancing. Grinding for rupees may be necessary whenever this is less than 100.
* `free_lamp_cone` setting this to true will make all dark rooms have a light cone without lamp. The lamp will be placed without regard to dark room logic.
* `force_enemy` setting this to a specific enemy (like 'StalfosKnight' or 'Lynel', complete list in EnemyList.py) will attempt to make all enemies that type. Some enemies cannot be changed (like bosses). Known issues with gfx glitches occurring in the overworld, as they do not limit the enemy types as appropriate for the sprite sheet.

###### Not Yet Implemented

Rom/Adjust flags like sprite, quickswap are not outputing with the print_template_yaml or print_custom_yaml settings 

### item_pool

This must be defined by player. Each player number should be listed with the appropriate pool.

Then each player can have the entire item pool defined. The name of item should be followed by the number of that item in the pool. Many key items will be added to the pool if not detected.

`Bottle (Random)` is supported to randomize bottle contents according to those allowed by difficulty. Pendants and crystals are supported here.


##### Caveat 
 
Dungeon items amount can be increased (but not decreased as the minimum of each dungeon item is either pre-determined or calculated by door rando) if the type of dungeon item is not shuffled then it is attempted to be placed in the dungeon. Extra item beyond dungeon capacity not be confined to the dungeon.

### goals

This must be defined by player. Each player number should be listed with the appropriate custom goals. This section has four primary subsections for each of the current supported events:

* `gtentry` (Ganon's Tower entrance)
* `ganongoal` (Ganon vulnerability)
* `pedgoal` (Master Sword Pedestal activation)
* `murahgoal` (Murahdahla requirement, if given requirements, Murahdahla appears always and acts as an alternative way to beat the game)

These four custom goals use the following identical structure to define them. These goals have four primary subsections: `cutscene_gfx`, `goaltext`, `requirements`, and `logic`

#### cutscene_gfx

This is where you can define custom GFX to be used for an event that has an animation (currently only the GT entry cutscene is supported). For convenience, there are a number of pre-defined names that can be used to indicate already known GFX values built into the ROM. There are too many to list, but a full list can be found in `item_gfx_table` in `Tables.py`. You can also use `Random` and it will take a random one from the aforementioned table.

```yaml
goals:
  1:
    gtentry:
      cutscene_gfx: Mirror Shield
```

Alternatively, you may also supply a custom address and palette ID, respectively, if you are injecting your own personal custom GFX into the ROM.

```yaml
goals:
  1:
    gtentry:
      cutscene_gfx:
        - 0x8140
        - 0x04
```

#### goaltext

This is where you define the dialogue that will show in-game that informs the player what the goal is. This section is required if a goal event has any `requirements` defined. This value can contain `%d` as a numeric placeholder, where this value will be provided by the goal information provided in the `requirements` section (prioritizes the first goal defined).

A new dialogue has been added for Master Sword Pedestal, if you attempt to receive the pedestal item but do not satisfy the condition for it, a dialogue will appear.

#### requirements

For the various events, you may define many conditions for the player to meet. All of the conditions you specify must pass to activate the event. There are several built-in conditions that can be used and the logic will be automatically added for consideration. However, when `CustomGoal` goals are used, there is no automatic logic that gets applied for this; for this, you must supply additional logic information to be used during generation. For more information on this, see the `logic` subsection. Keep in mind, through this level of customization, it is possible to create unbeatable games, and it will be possible to require things that the game doesn't provide a way to see the current progress for, and none of the options here change any HUD or UI elements to expose that information. It will be important to be careful when making these definitions and to use all provided tools and information to minimize these risks. These are the current supported conditions:

* `Pendants` (Default: 3)
* `Crystals` (Default: 7)
* `PendantBosses` (Default: 3)
* `CrystalBosses` (Default: 7)
* `PrizeBosses` (Default: 10)
* `Agahnim1Defeated`
* `Agahnim2Defeated`
* `TriforcePieces` (Default: set elsewhere)
* `CollectionRate` (Default: Max)
* `CustomGoal` (Needs additional `logic` defined when applicable)

These condition sections use a default target value unless a `target` is specified to override the default.

In addition, we have provided a `CustomGoal` to allow for very advanced control over custom requirements; this however requires some knowledge of either the rando assembly code, the LTTP disassembly source, or autotracker memory addresses. `CustomGoal` uses a few additional required and optional subsections:

* `address`: An address from memory that the game should read to compare (Only addresses from banks 0x7E and 0x7F are valid)
* `target`: A value to use to compare to the value found at the address (Hexadecimal values can be used)
* `size`: Optional, default is 1 byte will be read from memory (`16bit` or `2 bytes` are valid keywords to specify 2 bytes should be read and compared)
* `comparison`: This is to specify the method of comparison that should take place

##### comparison

* `minimum` or `at least`: Checks if a value is met or exceeded. This will likely be the most common comparison method.
* `equals`: Checks if a value exactly matches
* `any flag`: Checks against a bitfield value to see if any flag bits are set. (ie. a target of 0x40 only checks the one flag)
* `flags match`: Checks against a bitfield value to see if all flag bits are set. (ie. a target of 0x70 checks if all 3 bits are set)
* `count bits`: Counts the number of bits are set and compares that to the target

#### logic

Logic is automatically calculated for all of the basic out-of-the-box conditions, so nothing additional is required for specification for these. But for `CustomGoal`, this `logic` subsection is here to allow mode sculptors to provide this custom logic. This section is handled by three subsections: `item`, `access`, and `ability`

##### item

This is simply a list of items that are to be logically required to unlock the event. If multiple of the an item are needed, use an `=` followed by the amount required (ie. `- Triforce Piece=30`). For better support of Door Rando, dungeon items can be specified with a region name instead of a dungeon name; this way if you want to require a specific Big Key that opens a specific big chest in some room, this is possible to achieve (ie. `- Big Key (PoD Big Chest Balcony)`)

##### access

This is a list of regions that are logically required to be able to access before unlocking an event. Region names are internally named and not exposed on spoiler logs, but can be found by browsing `Regions.py`

##### ability

This is a list of abilities that the player logically requires. These are built-in logical patterns to make it easy to bundle larger nuanced requirements into one single definition. Some abilities take in an optional or required parameter, specified within `(` and `)` following the ability keyword. Here are the allowed keywords:

* `FarmBombs`: Link has access to repeatedly acquire bombs
* `CanUseBombs`: Link has the ability to use bombs
* `FarmRupees`: Link has access to repeatedly acquire rupees
* `NoBunny(<region name>)`: Link is required to not be a bunny in the specified region
* `MagicExtension(<number>)`: Link has a magic meter with a higher capacity (parameter is optional, a value of 8 represents one normal full magic bar, default value if left blank is 16, which is equivalent to half magic or one bottle with access to a green potion)
* `CanStun`: Link has the ability to stun enemies
* `CanKill(<number of enemies>)`: Link has the ability to kill most enemy types (parameter is optional, higher number tends to favor weapons that don't consume ammo, default value is 6 enemies)
* `CanShootArrows`: Link has ability to fire arrows at enemies
* `CanBonkDrop`: Link is able to retrieve Bonk Drops from trees and rocks
* `CanLift`: Link is able to lift basic rocks
* `CanFlute`: Link has ability to use flute (includes access to flute activation)
* `HasFire`: Link has a fire source
* `CanMelt`: Link can melt ice with Firerod or Bombos
* `HasMMMedallion`: Link has the medallion required for unlocking Misery Mire entrance
* `HasTRMedallion`: Link has the medallion required for unlocking Turtle Rock entrance

#### (example)

This entire section is very advanced and can be used to make very powerful customizations to the game. To make the overall definition more clear, we provide an example that makes use of a lot of the controls in place: Ganon requiring both 5 crystals AND requiring opening the GT Big Chest

```yaml
goals:
  1:
    ganongoal:
      goaltext: You’ll need %d crystals and to open the Big Chest in Ganon’s Tower
      requirements:
        - Crystals:
          target: 5
        - Custom:
          address: 0x7ef118
          target: 0x80
          comparison: flags match
      logic:
        item:
          - Big Key (GT Big Chest)
        access:
          - GT Big Chest
        ability:
          - NoBunny(GT Big Chest)
```

### placements

This must be defined by player. Each player number should be listed with the appropriate placement list.

You may list each location for a player and the item you wish to place there. A location name requires to be enclosed by single quotes if the location name contains a `#` (Most pot locations have the `#`). (Currently no location names have both a `'` and a `#` so you don't need to worry about escaping the `'`)
 
 For multiworld you can specify which player the item is for using this syntax:

`<item name>#<player number>`
 
 Example:
 `Pegasus Boots#3` means the boots for player 3.


### advanced_placements

This must be defined by player. Each player number should be listed with the appropriate section. Each section is a list of placement rules. Each placement rule has a specific type.

Supported Types: LocationGroup, NotLocationGroup, PreferredLocationGroup

#### LocationGroup

You may define an item, and a list of locations. The locations may be weighted if desired. The item will be placed at one of the listed locations - this currently ignores logic. The item will be placed there. The special location 'Random' indicates that the item should be placed randomly, without any other consideration. This may be repeated for placement of multiple items like multiple bows or swords.

#### NotLocationGroup

You may define an item and a list of locations that an item should not be placed at. This will apply to all items of that type. The logic is considered for this. If it is otherwise impossible, the item will be considered for the listed locations. This is important for small key layouts mostly, but it will try other locations first.

#### PreferredLocationGroup

You may define a list of items and a list of locations. Those items will be considered first for placements and the logic will attempt to place those items in those locations first. If there are more item than locations or vice versa, the leftover items or location will be treated normally. (Although, the leftover items will be placed earlier by the algorithm than those not listed)

### ow-edges

This must be defined by player. Each player number should be listed with the appropriate sections and each of these players MUST have either `ow_layout` or `ow_crossed` enabled in the `settings` section in order for any values here to take effect. This section has two primary subsections: `two-way` and `groups`.

#### two-way

`two-way` should be used for defining overworld edge transition connections. An asterisk `*` at the end of an edge name can be used on any parallel edge (an edge that exists in the same place in the opposite world), this will swap the defined edge with its parallel edge if the tile is flipped by Tile Flip.

`Links House ES*: Stone Bridge WS*` The edge east of Links House will be vanilla, but if Links House screen gets flipped by Tile Flip, then Big Bomb Shop ES will connect to Stone Bridge.

#### groups

`groups` should be used for defining new pool divisions of overworld edge transitions. Each group must have some unique name with all the edges listed that are desired to exist in the pool. The name of a group can be anything as long as it is valid yaml syntax. These defined groups cannot break up edges that conflict with mode settings, like `Keep Similar Edges Together`. The asterisk `*` notation, described in the `ow-edges/two-way` section, can be used here.

This example puts these 2 edges in their own pool, while the rest of the edges remain in their existing pools:
```
someDescription:
  - Links House ES*
  - Stone Bridge WS*
```

### ow-grid

`grid` contains additional options that only have an effect when `ow_layout` is set to `grid`.

#### wrap_horizontal / wrap_vertical

Set these to `true` to allow for overworld edge transitions to wrap from one side of a world to the opposite side. With `wrap_horizontal`, there can be east transitions on the eastern edge of the world map that send the player to the western edge of the world. With `wrap_vertical`, there can be south transitions on the southern edge of the world map that send the player to the northern edge of the world.

### ow-crossed

This must be defined by player. Each player number should be listed with the appropriate sections and each of these players MUST have `ow_crossed` enabled in the `settings` section in order for any values here to take effect. This section has four primary subsections: `force_crossed`, `force_noncrossed`, `limit_crossed`, and `undefined_chance`. There are also 

#### force_crossed / force_noncrossed

`force_crossed` and `force_noncrossed` should be used to define specific overworld edge transitions you wish to be cross-world connected without needing to specify an exact destination. These sections are optional but must contain a list of edge names. The asterisk `*` notation, described in the `ow-edges/two-way` section, can be used here.

#### limit_crossed

`limit_crossed` should be used to limit how many overworld edge transitions end up connecting cross-world. This value can be set to any non-negative integer. A value of 0 means no edges will be cross-world, except for edges that are forced cross-world (either by the previous step or a result of some combination of OWR settings). This option only takes effect in `Unrestricted` Crossed setting.

#### undefined_chance

`undefined_chance` should be used to determine how to handle all the remaining overworld edge transitions that aren't explicitly defined in the earlier steps. This represents the percent chance an edge will be cross-world. This value can be set from 0 to 100 (default is 50). A value of 0 means there is a 0% chance it will be cross-world. This option only takes effect under two mode combinations:
- 1: `Unrestricted` Crossed with a `Vanilla` OW Layout
- 2: `Grouped` Crossed

#### (Grouped specific options)

All four options available in the `ow-tileflips` section below are also available for `Grouped`, but must be defined under the `ow-crossed` section. In addition to the previous `undefined_chance`, the three other subsections are: `force_flip`, `force_no_flip`, and `force_together`. For more information about these sections, see the `ow-tileflips` section below.

### ow-whirlpools

This must be defined by player. Each player number should be listed with the appropriate sections and each of these players MUST have `ow_whirlpool: true` in the `settings` section in order for any values here to take effect. This section has one primary subsection: `two-way`.

#### two-way

`two-way` should be used for defining whirlpool connections.

`River Bend Whirlpool: Lake Hylia Whirlpool` The whirlpool west of Potion Shop will be connected to the whirlpool at Lake Hylia.

### ow-tileflips

This must be defined by player. Each player number should be listed with the appropriate sections and each of these players MUST have `ow_mixed: true` in the `settings` section in order for any values here to take effect. This section has four primary subsections: `force_flip`, `force_no_flip`, `force_together`, and `undefined_chance`.

#### force_flip / force_no_flip

`force_flip` and `force_no_flip` should be used for tiles you want to flip or not flip. These sections are optional but must contain a list of OW Screen IDs. It is common to reference OW Screen IDs in hexadecimal (altho decimal is okay to use, if preferred), which range from:
  0x00 to 0x3f - Light World
  0x40 to 0x7f - Dark World
  0x80 - Pedestal/Hobo
  0x81 - Zoras Domain

Here is an example which forces Links House and Sanctuary screens to stay in their original worlds. Note: It is unnecessary to supply both worlds' IDs. Links House is 0x2c and Big Bomb Shop is 0x6c.
```
force_no_flip:
  - 0x2c
  - 0x13
```

#### force_together

`force_together` should be used for defining tiles you want to force to flip as a group. Each group must have some unique name with all the OW Screen IDs listed that are desired to be grouped together. The name of a group can be anything as long as it is valid yaml syntax.

Here is an example which forces Links House and Sanctuary screens to flip together:
```
someGroup:
  - 0x2c
  - 0x13
```

#### undefined_chance

`undefined_chance` should be used to determine how to handle all the remaining tiles that aren't explicitly defined in the earlier step. This represents the percent chance a tile will flip. This value can be set from 0 to 100 (default is 50). A value of 0 means there is a 0% chance it will be flipped.

### ow-flutespots

This must be defined by player. Each player number should be listed with the appropriate sections and each of these players MUST have some form of Flute Shuffle in order for any values here to take effect. This section has two subsections: `force` and `forbid`. Both are lists of OW Screen IDs, please refer to ow-tileflips above for more information.

Everything listed in `force` means that this screen must contain a flute spot.

Everything listed in `forbid` means that this screen must not contain a flute spot.

### entrances

This must be defined by player. Each player number should be listed with the appropriate sections. This section has three primary subsections: `entrances`, `exits`, and `two-way`.

#### two-way

`two-way` should be used for connectors, dungeons that you wish to couple. (as opposite to decoupled in the insanity shuffle). Links house should be placed using this method as is can be decoupled logically. (Haven't tested to see if it works in game). The overworld entrance is listed first, followed by the interior exit that it leads to. (The exit will then be linked to exit at that entrance).

`50 Rupee Cave: Desert Palace Exit (North)` The 50 Rupee entrance leads to Desert North entrance, and leaving there will spit you out at the same place.

#### exits

`exits` is used for the Chris Houlihan Room Exit and connectors and dungeons that you wish to be decoupled from their entrances. Perhaps counter-intuitively, the exit is listed after the entrance from which it emerges.

`Light Hype Fairy: Chris Houlihan Room Exit` leaving Chris Houlihan Room will spit you out at the Light Hype Fairy.

(I can easily switch this syntax around if people would like me too) 

#### entrances

`entrances` is used for single entrances caves, houses, shops, etc. and drops. Single entrance caves always exit to where you enter, they cannot be decoupled. Dungeons and connectors which are decoupled can also be listed here.

`Chicken House: Kakariko Shop` if you walk into Chicken House door, you will in the Kakariko Shop.

### doors

This must be defined by player. Each player number should be listed with the appropriate sections. This section has three primary subsections: `lobbies` and `doors`.

`lobbies` lists the doors by which each dungeon is entered

`<lobby name>: <door name>` Ex. `Turtle Rock Chest: TR Lava Escape SE`

`doors` lists pairs of doors. The first door name is listed is the key. The value of this object may be the paired door name or optionally it can have two properties: `dest` and `type`. If you want a type, you must use the second option. 

The destination door is listed under `dest`
Supported `type`s are `Key Door`, `Bomb Door`, and `Dash Door`

Here are the two examples of the syntax:

```Hyrule Dungeon Guardroom Abyss Edge: Hyrule Castle Lobby W```
```
Sewers Rat Path WS:
        dest: Sewers Secret Room ES
        two-way: true
        type: Key Door
```

You'll note that sub-tile door do not need to be listed, but if you want them to be key doors you will have to list them.
 
 ###### Not Yet Implemented
 
 `one-way` to indicate decoupled doors
 
 ##### Known Issue
 
 If you specify a door type and those doors cannot be a stateful door due to the nature of the supertile (or you've placed too many on the supertile) an exception is thrown. 

### medallions

This must be defined by player. Each player number should be listed with the appropriate info.

Example:
```
Misery Mire: Ether
Turtle Rock: Quake
```

Leave blank or omit if you wish it to be random. Alternatively, a weighted dictionary is supported and a 'Random' option

### bosses

This must be defined by player. Each player number should be listed with the appropriate boss list.

This is done as `<dungeon>: <boss>`

E.g. `Skull Woods: Helmasaur King` for helmacopter. Be sure to turn on at least one enemizer setting for the bosses to actually be randomized.

### start_inventory

This must be defined by player. Each player number should be listed with a list of items to start with.

This is a yaml list (note the hyphens):

```
start_inventory:
    1:
      - Pegasus Boots
      - Progressive Sword
```

To start with multiple copies of progressive items, list them more than once.

There are some additional non-standard keywords available that can be added as starting inventory:

* `RandomWeapon` - This grants the player with the same random weapon options that Uncle gives in standard starts, including ammo for that weapon.
* `Beat Agahnim 1` - This enables post-Agahnim world state by default and flags Agahnim 1 as defeated.
* `Return Old Man` - This enables the Mountain Cave starting location by default. This also removes one item location from the game.
* Followers - These are the companions that can follow Link until you complete their quest. These can only be added if you have `Follower Shuffle` enabled. If standard start is enabled, a follower will only start following after the escape has been completed, unless it is set to start with Zelda.
  * `Zelda Herself`
  * `Escort Old Man`
  * `Maiden Rescued`
  * `Get Frog`
  * `Sign Vandalized` (Locksmith)
  * `Pick Up Kiki`
  * `Pick Up Purple Chest`
  * `Pick Up Big Bomb`
  * `RandomFollower` - This will pick any of the above as a random follower to start

##### Known Issue

This conflicts with the mystery yaml, if specified. These start inventory items will be added after those are added.

### drops

This must be defined by player. You may have prize packs, tree pulls, crab drops, stun prizes, and the fish prize defined using the following keys:
```
drops:
   1: 
     Pack 1
     - Small Heart
     - Bombs (4)
     - Random
     - etc
    Pack 2: (list)
    ...
    Pack 7: (list)
    Tree Pull Tier 1: Single Bomb
    Tree Pull Tier 2: Arrows (10)
    Tree Pull Tier 3: Fairy
    Crab Normal: Rupees (20)
    Crab Special: Small Magic
    Stun Prize: Bombs (8)
    Fish: Big Magic
```

Prize packs expect a list of eight items each (anything not specified will be whatever randomization would have normally occurred). The special drops expect a single item. Packs 1 through 7 are supported. Prize pack 0 is not customizable.

### prices

This must be defined by player. You may have the prices of items in shops defined using the following

```
prices:
  1:
    Capacity Upgrade - Left: 100
    Capacity Upgrade - Right: 200
    Dark Death Mountain Shop - Left: 100
    Dark Death Mountain Shop - Middle: 150
    Dark Death Mountain Shop - Right: 300
    Dark Lake Hylia Shop - Left: 200
```
