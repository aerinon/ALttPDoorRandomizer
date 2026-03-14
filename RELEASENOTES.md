# New Features

FastROM changes have been included now.

## Enemizer Features

Please see this document for extensive details. [Enemizer in DR](https://docs.google.com/document/d/1iwY7Gy50DR3SsdXVaLFIbx4xRBqo9a-e1_jAl5LMCX8/edit?usp=sharing)

Key points:
* Enemizer no longer uses a third party program. It is now built-in.
* New option under Enemy Drops: Underworld. Any underworld enemy can drop items.
* New option under Enemizer tab: Enemy Logic

Please read the entire document above for extensive details about enemizer and enemy drop shuffle systems.

Enemizer main changes:
* Several sprites added to the pool. Most notable is how enemies behave on shallow water. They work now.
* Clearing rooms, spawnable chests, and enemy keys drops can now have enemies with specific logic in the room. This logic is controlled by the new Enemy Logic option
* New system for banning enemies that cause issue is place. If you see an enemy in a place that would cause issue, please report it and it can be banned to never happen again. Initial bans can be found [in the code](source/enemizer/enemy_deny.yaml) for the curious
* Thieves are always unkillable, but banned from the entire underworld. We can selectively ban them from problematic places in the overworld, and if someone wants to figure out where they could be safe in the underworld, I'll allow them there once the major problems have been banned.
* THe old "random" and "legacy" options have been discarded for enemy shuffle. Tile room patterns are currently shuffled with enemies.

Underworld drops:
 
* A flashing blue square added to help locate enemies that have remaining drops on the supertile. (Dungeons and caves without a compass get this for free.)
* Flying enemies, spawned enemies, and enemies with special death routines will not drop items.
* Pikits do not drop their item if they have eaten a shield.
* Hovers in swamp waterway do no drop items due to a layer issue that's not been solved.
* Enemies that are over pits require boomerang or hookshot to collect the item
* Enemies behind rails require the boomerang (hookshot can sequence break in certain cases)
* Enemies that spawn on walls do not drop items. (Keese normally don't, but in enemizer these can be valid drops otherwise. The document has a visual guide.)

(Older notes below)

One major change with this update is that big key doors and certain trap doors are no longer guaranteed to be vanilla in Dungeon Door Shuffle modes even if you choose not to shuffle those types. A newer algorithm for putting dungeons together has been written and it will remove big key doors and trap doors when necessary to ensure progress can be made.

Please note that retro features are now independently customizable as referenced below. Selecting Retro mode or World State: Retro will change Bow Mode to Retro (Progressive). Take Anys to Random, and Small Keys to Universal.

## Flute Mode

Normal mode for flute means you need to activate it at the village statue after finding it like usual.
Activated flute mode mean you can use it immediately upon finding it. the flute SFX plays to let you know this is the case.

## Bow Mode

Four options here:

* Progressive. Standard progressive bows.
* Silvers separate. One bow in the pool and silvers are a separate item.
* Retro (progressive). Arrows cost rupees. You need to purchase the single arrow item at a shop and there are two progressive bows places.
* Retro + Silvers. Arrows cost rupees. You need to purchase the single arrow item or find the silvers, there is only one bow, and silvers are a separate item (but count for the quiver if found).

## Dungeon Shuffle Features

### Small Keys

There are three options now available:

* In Dungeon: The small key will be in their own dungeon
* Randomized: Small keys can be shuffled outside their own dungeon 
* Universal: Retro keys without the other options

### Dungeon Door Shuffle

New mode: Partitioned. Partly between basic and crossed, dungeons are shuffled in 3 pools:

* Light World dungeons, Hyrule Castle and Aga Tower are mixed together
* Palace of Darkness, Swamp Palace, Skull Woods, and Thieves Town are mixed together 
* The other dark world dungeons including Ganons Tower are mixed together

### Door Types to Shuffle

Four options here, and all of them only take effect if Dungeon Door Shuffle is not Vanilla:

* Small Key Doors, Bomb Doors, Dash Doors: This is what was normally shuffled previously
* Adds Big Keys Doors: Big key doors are now shuffled in addition to those above, and Big Key doors are enabled to be on in both vertical directions thanks to a graphic that ended up on the cutting room floor. This does change
* Adds Trap Doors: All trap doors that are permanently shut in vanilla are shuffled.
* Increases all Door Types: This is a chaos mode where each door type per dungeon is randomized between 1 less and 4 more.

Note: Boss Trap doors are removed currently and not added into the trap door pool as extra trap doors. This may not be a permanent change

### Decouple Doors

This is similar to insanity mode in ER where door entrances and exits are not paired anymore. Tends to remove more logic from dungeons as many rooms will not be required to traverse to explore. Hope you like transitions.

## Customizer

Please see [Customizer documentation](docs/Customizer.md) on how to create custom seeds.

## New Goals

### Ganonhunt
Collect the requisite triforce pieces, then defeat Ganon. (Aga2 not required). Use `ganonhunt` on CLI

### Completionist
All dungeons not enough for you? You have to obtain every item in the game too. This option turns on the collection rate counter and forces accessibility to be 100% locations. Finish by defeating Ganon.


## Standard Generation Change

Hyrule Castle in standard mode is generated a little differently now. The throne room is guaranteed to be in Hyrule Castle and the Sanctuary is guaranteed to be beyond that. Additionally, the Mirror Scroll will bring you back to Zelda's Cell or the Throne Room depending on what save point you last obtained, this is to make it consistent with where you end up if you die. If you are lucky enough to find the Mirror, it behaves differently and brings you the last entrance used - giving you more options for exploration in Hyrule Castle.

## ER Features

### New Experimental Algorithm

To accommodate future flexibility the ER algorithm was rewritten for easy of use. This allows future modes to be added more easily. This new algorithm is only used when the experimental flag is turned on.

### Lite/Lean ER (Experimental required)

Designed by Codemann, these are available now (only with experimental turned on - they otherwise fail)

#### Lite
- Dungeon and multi-entrance caves can only lead to dungeon and multi-entrance caves
- Dropdowns can only lead to dropdowns, with them staying coupled to their appropriate exits
- Cave entrances that normally lead to items can only lead to caves that have items (this includes Potion Shop and Big Bomb Shop)
- All remaining entrances remain vanilla
- Multi-entrance caves are connected same-world only
- LW is guaranteed to have HC/EP/DP/ToH/AT and DW: IP/MM/TR/GT
- Shop locations are included in the Item Cave pool if Shopsanity is enabled
- Houses with pots are included in the Item Cave pool if Pottery is enabled

#### Lean
- Same grouping/pooling mechanism as in Lite ER
- Both dungeons and connectors can be cross-world connections
- No dungeon guarantees like in Lite ER

### Back of Tavern Shuffle (Experimental required)

Thanks goes to Catobat which now allows the back of tavern to be shuffled anywhere and any valid cave can be at the back of tavern with this option checked. Available in experimental only for now as it requires the new algorithm to be shuffled properly.

#### Take Any Caves

These are now independent of retro mode and have three options: None, Random, and Fixed. None disables the caves. Random works as take-any caves did before. Fixed means that the take any caves replace specific fairy caves in the pool and will be at those entrances unless ER is turned on (then they can be shuffled wherever). The fixed entrances are:

* Desert Healer Fairy
* Swamp Healer Fairy (aka Light Hype Cave)
* Dark Death Mountain Healer Fairy
* Dark Lake Hylia Ledge Healer Fairy (aka Shopping Mall Bomb)
* Bonk Fairy (Dark)

# Patch Notes

* 1.5.6
  * Enemy Drops: Pikit are no longer eligible for dropped items due to a vanilla bug where a failed steal can overwrite the assigned drop.
  * Standard Mode: Reworked spawn refills to be more generous for enemy drop modes.
  * Customizer: Added `item_pool_adjust` section to apply additive/subtractive deltas to the base item pool rather than replacing it entirely.
  * Multiworld: Fixed a generation crash when beemizer is active and pottery is enabled. Pot locations are now properly filled with same-player items when the MW limit is hit even when beemizer has replaced native pot items.
  

