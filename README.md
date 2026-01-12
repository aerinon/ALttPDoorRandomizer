# Overworld Randomizer

This is a overworld randomizer for _The Legend of Zelda: A Link to the Past_ for the SNES
based on the Door Randomizer found at [Aerinon's Github Project.](https://github.com/Aerinon/ALttPDoorRandomizer)
See https://alttpr.com/ for more details on the normal randomizer.

### Trackers & Guides

This is a very new mode of LTTPR so the tools and info is very limited.
- There is an [OW Rando Cheat Sheet](https://zelda.codemann8.com/images/shared/ow-rando-reference-sheet.png) that shows all the transitions that exist and are candidates for shuffle.
- There is OW tracking capability within the following trackers:
    - [Community Tracker](https://alttptracker.dunka.net/)
    - CodeTracker, an [EmoTracker](https://emotracker.net) package for LTTPR
- There is an [OW OWG Reference Sheet](https://zelda.codemann8.com/images/shared/ow-owg-reference-sheet.png) that shows all the in-logic places where boots/mirror clips and fake flippers are expected from the player.

### If you want to playtest this, know these things:
- If you fake flipper, beware of transitioning south. You could end up at the top of the waterfall in the southeast of either world. If you mistakenly drop down, it is important to know that altho the game may appear as frozen for a bit of time, the game is simply scrolling Link back to the original point of water entry. Upon "landing", you'll be able to S+Q properly. Falling from the waterfall is avoidable but it is super easy to do as it is super close to the transition.

# Feedback and Bug Reports

All feedback and dev conversation happens in the #ow-rando channel on the [ALTTP Randomizer discord](https://discordapp.com/invite/alttprandomizer).

# Installation from Source

1. Download the source code from the repository directly and put it in a folder of your choosing. Any method of grabbing the source code is fine, but due to some changes on GitHub's site, some of the other alternatives might be better options for some people.
    - Use [GitHub Desktop](https://desktop.github.com) to clone this repository to a folder on your computer. Once a repository is established, you can click `Fetch origin` or `Pull` to re-download whenever you want to grab the latest version. This is the best option for a simple one-click solution.
    - Download the [source code](https://github.com/codemann8/ALttPDoorRandomizer/archive/refs/heads/OverworldShuffle.zip) from GitHub manually.

2. You must have [Python](https://www.python.org/downloads) installed (version 3.7 - 3.10 supported), and ensure PATH is included during the installation.
    - A common issue with users is that there are multiple instances of Python installed on the same computer. This causes the computer to be confused with which Python instance it uses. Ensure that any older Python installations have been removed.

3. This program requires all python dependencies that are necessary to run OW Randomizer. There are multiple ways to install them:
    - Try running ```pip install missingdependency``` or ```python -m pip install missingdependency``` on the command line (replace ```missingdependency``` with the specific package that is missing) to install the dependency.
    - The simpler method, run (double-click) ```resources/ci/common/local_install.py``` to install all the missing dependencies as well.

4. Once installed, you should be able to run (double-click) ```Gui.py``` and the OWR program will appear, where you can select your desired settings.

See the following link if you have additional trouble: https://github.com/codemann8/ALttPDoorRandomizer/blob/OverworldShuffle/docs/BUILDING.md

# Running the Program

- Run (or double-click) ```Gui.py``` for a simple graphical user interface.
- Alternatively, you can generate thru the CLI, run ```DungeonRandomizer.py```.

# Getting Started
## "I heard about OWR and want to give it a try, what do I do?"
This is a common sentiment among those who are unfamiliar with OWR's offerings. One might be tempted to simply turn on a bunch of the options and give it a go. I cannot express this enough:

**^ DO NOT do this! ^**

OWR definitely has a lot of options, and all of them by themselves are pretty simple to grasp, but combining multiple OWR options together increases the complexity and confusion in exponential fashion. Now, of course, some OWR options like Flute Shuffle can safely be combined at any level and isn't gonna make anything more complicated. But specifically, avoid combining these 3 options, at least when going for your first seed:
- OW Layout Shuffle
- OW Tile Flip (Mixed)
- Crossed OW

## "Any recommendations for a first-timer?"
For a first (and second) seed... *and I say "second" because I feel like both of these recommendations I'm about to make have VERY different vibes, have different levels of challenge, but are both, of their own right, worthy of being tried at least once.* Your first OWR experience can be combined with any mode combination that you are already familiar with and have a lot of experience in playing. If you like Crosskeys and feel very comfortable running that, feel free to turn on all those settings in addition to ONE of these two options:
1. `OW Tile Flip (Mixed)` - Overly, a pretty easy-breezy mode, it doesn't require too much big brain, and is pretty managable even without proper logic tracking, as long as you at least have a standard map tracker. This is actually my favorite way to run OWR today
    - DO NOT turn on Layout or Whirlpool Shuffle, leave this on `Vanilla`
    - DO NOT turn on Crossed OWR
    - `Flute Shuffle` or `Bonk Drops` could be enabled if desired, altho I'd recommend against it, at least for a fresh viewpoint of Mixed OWR
2. `OW Layout Shuffle` - Set to `Parallel`. This is the original spirit and vision of OWR from the time of its own founding. It's definitely much more complicated to run than OW Tile Flip, so keep that in mind.
    - `Starting Boots` - Either actual boots or pseudoboots, you will be spending a lot of time navigating the OW, so it's best to do it with the ability to run fast.
    - DO NOT turn on OW Tile Flip (Mixed)
    - DO NOT turn on Crossed OWR
    - Enable `Whirlpool Shuffle` - Recommended to always be enabled with Layout Shuffle
    - Enable `Keep Similar Edges Together` - This just helps keep some of your sanity for a first experience
    - Enable `Flute Shuffle` - I recommend setting this to `Balanced`, this helps space out the flute spots across the world. Being that the world itself is shuffled, the vanilla flute spots are likely NOT as conveniently located as they normally are.
    - `Free Terrain` - Recommend to NOT turn this on for a first run, but definitely on a second run.
    - `Bonk Drops` - Recommend to NOT turn this on, especially if you don't have starting boots, but you could enable this in future seeds if you've become more familiar with OWR, as you'll be visiting these screens anyways, you might as well grab the items on the way :)

## "What tracker should I use?"
I personally use 2 trackers together, at least if Layout Shuffle is enabled. Currently, DunkaTracker is the ONLY tracker that is useful for tracking Layout Shuffle, highly recommended. However, I personally don't like the main portion of the tracker and ignore the main window completely. For tracking everything else, I use `CodeTracker`, a tracker pack that is installable within `EmoTracker`, this handles ALL OWR modes EXCEPT Layout Shuffle (and generally Crossed OW, but missing that doesn't make much of a difference). I am unaware of ANY trackers outside of these 2 that handle OWR modes, so my advice would be to familiarize yourself with both trackers and pick and choose the parts you find most useful for yourself.

# Terminology

### OW / OWR
OW is shorthand for Overworld, referring to anywhere that is "outside" in the game: ie. not caves or dungeons, which are considered Underworld.

OWR is shorthand for Overworld Rando/Shuffle, the concept of randomizing certain elements present in the Overworld.

### LW / DW (**IMPORTANT TO READ**)
Light World and Dark World. Some of the references to LW and DW can be a bit ambiguous. Sometimes, if a LW tile is being referenced, it's usually referring to the normal LW tile that you already know of. Other times, I might be referring to a DW tile that has now become part of the LW, due to a certain way that the game can be shuffled. This can be particularly confusing when trying to understand these modes, and what they do, based on the text description of them, but it's important to keep in mind the context of which is being described.

Things get extra confusing when adding Crossed OWR into the mix, due to the fluidity of navigating between LW and DW freely. It's often best to think of Crossed OWR like this: You've been used to a two-part Light and Dark World, but Crossed works more close to a Starting Plane and Other Plane, ie. You can walk around and never be able to reach the "other" plane until you have the items to enter portals, including using mirror. Both of these planes consist of Light and Dark World tiles.

During gameplay and in the OW, there is an L or D in the upper left corner, indicating which *world* you are in. As complicated as all the rules can be, this L or D is the simplest way to digest it all. Whenever it says you are in DW, this means you are subject to being transformed to a bunny, cannot use the flute, and you will be able to use the mirror to gain access to the LW. When in LW, you are transformed to Link (if not already), and you're able to use the flute.

### Tile
This refers to one OW screen, containing one or more transitions (or edges) that lead to another tile. Most tiles have a "other world" version of it, linked by either a portal or mirror; some do not like Zora's Domain or Master Sword Pedestal.

### Edge / Transition
This refers to the sides/edges of the screen, where you walk into them and causes another tile to load, the camera pans over, and Link continues movement that destination tile.

### Parallel (as a concept)
Various things in this readme are referred to as parallel or non-parallel. Parallel refers to elements that exist in similar orientation in the opposite world. For instance, Kakariko Village and Village of Outcasts each have 5 transitions, all in the same geographical area and all leading in the same direction, that makes all those transitions parallel. In another instance, The Purple Chest screen (where you turn it in) has transitions on the West side of the screen, but in the DW, those transitions do not exist, therefore, these West transitions are non-parallel, and the tile itself is not parallel. Determining whether something is parallel or not dictates whether something can be shuffled or not, or whether it requires something else to be grouped with it and shuffled together.

### Tile Groups
These are groups of tiles that must be shuffled (or not shuffled) as a group. For instance, if Standard World State is enabled, Link's House, Hyrule Castle, and Sanctuary must be kept together, to ensure that the opening sequence can commence. There are a number of scenarios that can cause various tiles to be grouped, this is largely determined by the specific combination of OWR settings and is necessary to ensure correct logic.

### Similar Edge
These refer to groups of edges that are near each other. For instance, at Link's House, there are 3 different edges on the West side of the screen, separated by the cliffside terrain. All 3 of these can potentially lead to 3 different places. But conversely, these 3 edges are also considered similar edges and can be made to all lead to the same area.

Similar edges on the larger OW tiles are a bit harder to intuitively determine. For instance, in Kakariko Village, there are 3 North edges, but all 3 are NOT part of the same Similar Edge group. Instead, the 2 on the West End are deemed Similar, while the one to the far East is its own edge. The most definitive way to figure out which edges are actually grouped, look at a world map image with gridlines (one is linked above in `Trackers & Guides` labeled OW Rando Cheat Sheet), if you draw imaginary lines, splitting up large tiles into 2x2 parts (continuing the small tiles' patterns), all edges within these bounds are considered Similar Edges.

Similar edges are used when `Keep Similar Edges Together` is enabled and have meaning when used with `Layout Shuffle` (with and without `Free Terrain`) and `Crossed` settings.

# Overworld Map Changes

The overworld map check screen has been completely overhauled in this OWR fork. In other LTTP forks, there are numbered icons to indicate the crystal number of the crystal and those are shown alongside crystal prizes. OWR has changed this so the numbers instead correspond to dungeon numbers. In the LW, you have the 3 pendant dungeons, these are indicated by a blue 1, 2, and 3. In the DW, you have the 7 crystal dungeon, these are indicated by red numbers (1-7). In addition, there may be some mode combinations where HC, AT, and GT may be visible via icon, indicated by a white H, a white A, and a skull. An example of what you can expect to see on a map check can be found [here](https://zelda.codemann8.com/images/shared/newmapcheck.gif).

# Inverted Changes

The version of Inverted included in OWR varies quite a bit compared to the Door Rando and VT (main rando) forks. This is often referred to as Inverted 2.0, as this is a plan to shift it to a newer/updated concept, intended to either enhance/improve the Inverted experience or to restore some behaviors more closer to vanilla. Some of these changes are likely going to be added to all rando forks/branches and subject to change, but this will be based on user feedback.

- Links House start now spawns inside the Big Bomb Shop, where there is now a bed
- Old Man Cave/Bumper Cave entrances are restored to their original state
- Mountain Cave S+Q now spawns in his usual Cave
- Removed the ladder that leads from West Dark Death Mountain up to the top near the GT entrance
- Flute Spot 1 is moved to the very Top of Dark Death Mountain, next to the GT entrance
- When finding Flute, it comes pre-activated (will hear SFX on collecting)
- Spiral and Mimic Cave are now bridged together
- TR Peg Puzzle is restored but instead reveals a ladder
- Houlihan now exits same place as the Link's House start does
- Ganon Hole Exit now exits out a new door on top of HC
- Ice Palace has been re-sealed to vanilla, portal moved to outer edge of moat (makes IP mirror locked)
- Glitched modes will now use vanilla terrain except where necessary

Note: These changes do impact the logic. If you use `CodeTracker`, these Inverted 2.0 logic rules are automatically detected if using autotracker, indicated by a 2 in the corner of the World State mode icon. This can also be manually applied if you right-click the World State mode icon.

# Settings

Only settings specifically added by this Overworld Shuffle fork are found here. All door and entrance randomizer settings are supported. See their [readme](https://github.com/Aerinon/ALttPDoorRandomizer/blob/master/README.md)

## Overworld Layout Shuffle (--ow_layout)
OW Edge Transitions are shuffled to create new world layouts. A brief visual representation of this can be viewed [here](https://zelda.codemann8.com/images/shared/ow-modes.gif). (This graphic also includes combinations of Crossed and Tile Flip)

### Vanilla

OW Transitions are not shuffled.

### Grid

OW Screens are shuffled in such a way that they are still arranged on an 8x8 grid for each world like vanilla, and the OW Transitions are based on that arrangement.

### Wild

OW Transitions are shuffled with no respect to geometric coherence.

## Parallel (--ow_unparallel to disable)

With OW Layout Shuffle, this forces both worlds to have a matching layout.

## Free Terrain (--ow_terrain)

With OW Layout Shuffle, this allows land and water edges to be connected.

## Crossed Options (--ow_crossed)

This allows OW connections to be shuffled cross-world. There are 2 main methodologies of Crossed OWR: 

- `Grouped` and `Polar` both are guaranteed to result in two separated planes of tiles, similar to that of vanilla. This means you cannot simply walk around and be able to visit all the tiles. To navigate to the other plane, you have the following methods: 1) Normal portals 2) Mirroring on DW tiles 3) Fluting to a tile that was previously unreachable

- `Unrestricted` is not bound to follow a two-plane framework. This means that it could be possible to travel on foot to every tile without entering a normal portal.

See each option to get more details on the differences.

### None

Transitions will remain same-world.

### Grouped

This option shuffles connections cross-world in the same manner as Tile Flip (Mixed), the connections coming in and going out of a Tile Group (see `Terminology` section above) are crossed (ie. meaning it is impossible to take a different path to a tile and end up in the opposite world, unlike `Unrestricted`). This is considered the simplest way to play Crossed OWR.

### Polar

Only effective if Tile Flip (Mixed) is enabled. Polar follows the same principle as Grouped, except that it preserves the original/vanilla connections even when tiles are flipped/mixed. This results in a completely vanilla overworld, except that some tiles will transform Link to a Bunny. Even though these tiles give the appearance of your normal LW tile, due to how Tile Flip works, those LW tiles give DW properties (such as bunnying, ability to mirror, and prevents flute usage). This offers an interesting twist on Mixed where you have a pre-conditioned knowledge of the terrain you will encounter, but not necessarily be able to do what you need to do there, due to bunny state. (see `Tile Flip / Mixed` section for more details)

### Unrestricted

Every transition is independently a candidate to be chosen as a cross-world connection. This option abides by the `Keep Similar Edges Together` option and will guarantee same effect on all edges in a Similar Edge group if enabled. If a Similar Edge group is chosen from the pool of candidates, it only counts as one portal, not multiple. Each transition has an equal 50/50 chance of being a crossed connection.

Note: If Whirlpool Shuffle is enabled, those connections can be cross-world.

## Keep Similar Edges Together (--ow_keepsimilar)

This keeps similar edge transitions together. ie. The 2 west land edges of Potion Shop will be paired to another set of two similar edges, unless Free Terrain is also enabled, in which case these 2 edges together with the west water edge form a group of 3 similar edges. See `Terminology` section above for a more detailed explanation of Similar Edges.

Note: This affects OW Layout Shuffle mostly, but also affects `Unrestricted` mode in Crossed OW.

## Tile Flip / Mixed Overworld (--ow_mixed)

Tile Flip (often referred to as Mixed OWR) can be thought of as a hybrid of Open and Inverted, where OW tiles are randomly chosen to be flipped to become a part of the opposite world. When this occurs, that tile will use the Inverted version of that tile. For instance, if the Cave 45 tile becomes flipped, that means while walking around in the LW, you will find the screen that's south of Stumpy instead, and Cave 45 will instead be found in the DW; but like Inverted, the Cave 45 tile is modified to not have a ledge, this ensures that it will be possible to access it.

Being that this uses concepts from Inverted, it will be important to review the OWR-exclusive changes that have been made to Inverted (often referred to as Inverted 2.0). See `Inverted Changes` for more details.

During gameplay:
    - When on the OW, there will be an L or D in the upper left corner, indicating which world you are currently in. Mirroring still works the same, you must be in the DW to mirror to the LW.
    - When doing a map check (pressing X while on the OW), the tiles shown will reflect the flipped tiles. This means that dungeon prizes will show the prizes for the dungeons that are now part of that world. Here is an image showing the difference of appearance when tiles are flipped on the [map check](https://zelda.codemann8.com/images/shared/lttp-lw-mapcheck.gif) screen.

Note: Tiles are put into Tile Groups (see `Terminology`) that must be shuffled together when certain settings are enabled. For instance, if ER is disabled, then any tiles that have a connector cave that leads to a different tile, then those tiles must flip together.

## Tile Flip vs Crossed Explained
The above OWR options are very difficult to describe. The above descriptions are written in a way that is most correct even when these options are combined with more complicated modes. But, this section aims to simplify the explanation by assuming the user chooses a normal 'Open 7/7 Defeat Ganon' seed but with just one OWR setting enabled.

Both of these options are very similar and often confused from each other.
    - Tile Flip is a mode where some DW tiles are moved and BECOME part of the LW (and the LW counterparts become part of the DW). What does it mean to "become" part of a world? It means that it will inherit (NOT bring over) the properties of that world it is moving to (such as being able to flute, ability to use the mirror, or being susceptible to bunnying).
    - Crossed on the other hand doesn't change the properties of tiles, instead it transports Link *physically?* across worlds upon transitioning. This also means that Link can be transformed into a bunny moving from tile to tile.
tldr: Tile Flip moves the tiles, Crossed moves Link

So, let's run an example of 2 tiles, Link's House and the screen to the right of it. Transitioning right from Link's House: In vanilla, you get the Stone Bridge screen and Link stays his normal self and is just normal LW behavior. Now, let's assume Links House screen stays vanilla, but the tile to the right is getting Flipped or Crossed.
    - In Tile Flip, you'd get the Hammer Bridge screen and Link would stay as Link and you'd be able to flute away from this screen if you had a flute.
    - In Crossed, you'd get the same Hammer Bridge Screen, but this time Link would be transformed into a bunny, just like he'd normally be when on that tile.
    - In Polar Crossed (when both Tile Flip and Crossed effects are applied together), you get the normal Stone Bridge screen, but Link is transformed to a bunny (because the Stone Bridge screen has moved to the DW AND Link is also moving across worlds).

As you can see, things get pretty complicated when mixing modes together. Doing this can definitely create a very unique and interesting experience, but one that is very hard to grasp. And then beyond that there is OW Layout Shuffle, which is where transition destinations are shuffled, so Link will get transported to a different tile entirely, but the same rules apply when you eventually find the Stone/Hammer Bridge screen, you just likely won't find that screen thru a transition on Link's House screen.

## Whirlpool Shuffle (--ow_whirlpool)

When enabled, the whirlpool connections are shuffled. If Crossed OW is enabled, the whirlpools can also be cross-world as well. When the number of crossed edges are limited thru Customizer, this doesn't count towards the limited number of crossed edge transitions.

## Flute Shuffle (--ow_fluteshuffle)

When enabled, new flute spots are generated and gives the player the option to cancel out of the flute menu by pressing X.

Note: Desert Teleporter Ledge is always guaranteed to be chosen. One of the three Mountain tiles are guaranteed if OW Layout Shuffle is set to Vanilla.

### Vanilla

Flute spots remain unchanged.

### Balanced

New flute spots are chosen at random, with restrictions that limit the promixity between other chosen flute spots.

### Random

New flute spots are chosen at random with minimum bias.

## Follower Shuffle (--shuffle_followers)

This shuffles the follower companions throughout the world. Here is a full list of followers in the game:

- Princess Zelda
- Old Man
- Blind Maiden
- Frog/Blacksmith
- Locksmith (Guy who unlocks Purple Chest)
- Kiki the Monkey
- Purple Chest
- Super Bomb

When followers are shuffled, you must still fulfill the original requirements of the follower location. For example, if the Super Bomb Shop now contains the Frog, you must have crystals 5 and 6 and 100 rupees to unlock the Frog. It is also important to note that Purple Chest still needs to be delivered to the usual spot. Also, since it isn't useful normally, many people might not know that the Locksmith (the Purple Chest unlocking guy) can follow you, you must remove his sign to get him to follow.

Most of the limitations of followers in the vanilla game have been lifted for this shuffle to work. For instance, you are able to mirror, flute, die, collect a crystal, and save/quit in most situations and still retain the follower. You are also able to enter caves/dungeons and complete dig game while you have a follower.

In the scenario where you are forced down a narrow path and a follower is in your way and you already have a different follower. Running into that follower will switch the followers rather than overwriting, this gives you the opportunity to proceed with either one of the followers. Note that if you leave the screen, you lose this option to switch and you will need to go back to the original place you found the first follower.

Optionally, thru the customizer, you can add a follower to your starting inventory, and you will be given that follower and it will stay with you until you complete their quest.

## Bonk Drop Shuffle (--bonk_drops)

This adds 42 new item locations to the game. These bonk locations are limited to the ones that drop a static item in the vanilla game.

- Bonk Locations consist of some trees, rocks, and statues
    - 33 Trees
        - 8 of the tree locations require Agahnim to be defeated to access the item
    - 6 Rocks
        - 1 of the rocks drops 2 items
    - 2 Statues
        - 1 of them is the Cold Fairy Statue next to Ice Rod Cave
- Bonk locations can be collected by bonking into them with the Pegasus Boots or using the Quake Medallion
- One of the bonk locations are guaranteed to have a full magic decanter
- Some of the drops can be farmed repeatedly, but only increments the collection rate once
- All of the bonk trees have been given an alternate color (and all non-bonk trees are reverted to normal tree color)
    - Some screens are coded to change the "alternate tree color", some of them are strange (just how the vanilla game does it)
    - Rocks and statues are unable to be made to have a different color

Here is a map that shows all the [Bonk Locations](https://zelda.codemann8.com/images/shared/bonkdrops.png). FYI, the numbers indicate how many bonk items there. The stars with a green square are all Bonk Locations that are unlocked after you kill Aga 1.

As far as map trackers, Bonk Locations are supported on `CodeTracker` when the Bonk Drops option is enabled.

#### Items Added To Pool:
- 15 Fairies
- 8 Apples
- 6 Bee Traps
- 3 Red Rupees
- 3 Blue Rupees
- 2 Single Bombs
- 2 Small Hearts
- 1 Large Magic Decanter
- 1 8x Bomb Pack
- 1 Good Bee

## Nearby Dungeon Items

This is a new option in addition to the traditional wild vs non-wild (keysanity/non-keysanity) options for all the dungeon item types (maps, compasses, small keys, big keys, prizes). This new option shuffles dungeon items into locations somewhere either within the dungeon that it is assigned to or within the surrounding district of that dungeon.

## Prize Shuffle (--prizeshuffle)

A new option has been added to shuffle the 10 dungeon prizes in ways that they haven't been shuffled before. This means that dungeon prizes can be found in other item locations, such as chests or free-standing item locations. This also means that bosses are able to drop a 2nd item in place of the shuffled prize.

### On Boss

This is the normal prize behavior that has been a part of rando up until now. The dungeon prizes are shuffled amongst themselves in their own pool and aren't considered part of the main collection total.

### In Dungeon

This option shuffles the prize into a location somewhere within the dungeon that it is assigned to.

### Nearby

This option shuffles the prize into a location somewhere either within the dungeon that it is assigned to or within the surrounding district of that dungeon.

### Randomized

This option freely shuffles the prizes throughout the world. While the dungeon prizes can end up anywhere, they still are assigned to a specific dungeon. When you defeat the boss of a certain dungeon, checking the map on the overworld will reveal the location WHERE you can find the prize, an example shown [here](https://zelda.codemann8.com/images/shared/prizemap-all.gif). Finding the map will still reveal WHAT the prize is. If you defeated a boss but haven't collected the map for that dungeon, the prize will be indicated by a red X, example shown [here](https://zelda.codemann8.com/images/shared/prizemap-boss.gif). If you collected a map but haven't defeated the boss yet, the icon indicator on the map will be shown on the top edge (for LW dungeons) or the bottom edge (for DW dungeons), but it will show you WHAT the prize is for that dungeon, an example of that is shown [here](https://zelda.codemann8.com/images/shared/prizemap-map.gif).

- It is important to note that the overworld map check has changed: the numbered icons that are displayed are NO LONGER indicating the crystal number like they have in the past. They are now indicating the dungeon that it belongs to; a blue E/D/T indicates the 3 LW dungeons (EP, DP, and ToH) and a red 1-7 indicate the 7 DW dungeons

## New Goal Options (--goal)

### Trinity

This goal gives you the choice between 3 goals, only one of which the player needs to complete: Fast Ganon (no Aga2), pulling Pedestal, or turn in TF pieces to Murahdahla. By default, you need to find 8 of 10 total TF pieces but this can be changed with a Custom Item Pool. It is recommended to set GT Entry to 7 crystals and Ganon to 4 or 5 crystals or Random crystals, although the player can flexibly change these settings as they see fit.

## New Entrance Shuffle Options (--shuffle)

### Lite

This mode is intended to be a beginner-friendly introduction to playing ER, unlike that of Simple ER. It focuses on reducing Low% world traversal in late-game dungeons while reducing the number of entrances needing to be checked.

This mode groups entrances into types and shuffles them freely within those groups.
- Dungeons and Connectors (Multi-Entrance Caves)
- Item Locations (Single-Entrance Caves with an item, includes Potion Shop and Red Bomb Shop)
    - Includes Shops only if Shopsanity is enabled
    - Includes caves with pots only if Pottery settings have them shuffled)
- Dropdowns and their associated exits (Skull Woods dropdowns are handled the same as in Crossed)
- Non-item locations (junk locations) all remain vanilla

Lite ER shuffles all connectors same-world, to limit bunny traversal. And to prevent Low% enemy and boss combat, some dungeons are confined to specific worlds.

The following dungeons are guaranteed to be in the Light World:
- Hyrule Castle
- Eastern Palace
- Desert Palace
- Tower of Hera
- Agahnim's Tower

The following are guaranteed to be in the Dark World:
- Ice Palace
- Misery Mire
- Turtle Rock
- Ganon's Tower

Both Lite and Lean ER modes are supported in `CodeTracker`, showing only the entrances that are shuffled.

### Lean

This mode is intended to be a more refined and more competitive format to Crossed ER. It focuses on reducing the number of entrances needing to be checked, while giving the player unique routing options based on the entrance pools defined below, as opposed to mindlessly checking all the remaining entrances. The Dungeons/Connectors can connect cross-world.

This mode groups entrances into types and shuffles them freely within those groups.
- Dungeons and Connectors (Multi-Entrance Caves)
- Item Locations (Single-Entrance Caves with an item, includes Potion Shop and Red Bomb Shop)
    - Includes Shops only if Shopsanity is enabled
    - Includes caves with pots only if Pottery settings have them shuffled)
- Dropdowns and their associated exits (Skull Woods dropdowns are handled the same as in Crossed)
- Non-item locations (junk locations) all remain vanilla

Both Lite and Lean ER modes are supported in `CodeTracker`, showing only the entrances that are shuffled.

### Swapped

This mostly follows the rules of Crossed ER, but instead of entrances being randomly placed individually, random pairs of two entrances are chosen to swap with each other. This creates a unique experience where checking one entrance gives you information about another entrance, which can influence your future routing.

If there is an odd amount of entrances being shuffled in the pool, the last remaining entrance will be vanilla. All other entrances are guaranteed to be non-vanilla.

Here is a [Swapped ER Reference Sheet](http://zelda.codemann8.com/images/shared/swapped-reference-sheet.png) that shows some of the caves/houses that are less familiar to most people.

### District

This is an entrance shuffle that only shuffles entrances within their respective `Districts` (See Below). Also, dropdowns and the entrance that a dropdown normally exits are NOT kept together; this also means that the Skull Woods entrances are no longer guaranteed to lead to Skull Woods. Also, since there is no district that can span multiple worlds, this is NOT a cross-world entrance mode.

Districts are a concept originally conceived by Aerinon in the Door Randomizer, where parts of the OW are split into areas and given a name. Here is a [District Map](https://zelda.codemann8.com/images/shared/ow-districts-reference-sheet.png) showing how they are split up.

# Command Line Options

```
-h, --help
```

Show the help message and exit.

```
--ow_layout <mode>
```

For specifying the overworld layout shuffle you want as above. (default: vanilla)

```
--ow_unparallel
```

With OW Layout Shuffle, this no longer forces both worlds to have a matching layout.

```
--ow_terrain
```

With OW Layout Shuffle, this allows land and water edges to be connected.

```
--ow_crossed <mode>
```

For specifying the type of cross-world connections you want on the overworld

```
--ow_keepsimilar
```

This keeps similar edge transitions paired together with other pairs of transitions

```
--ow_mixed
```

This gives each OW tile a random chance to be flipped to the opposite world

```
--ow_fluteshuffle <mode>
```

For randomizing the flute spots around the overworld

```
--ow_no_fog
```

With OW Grid Layout Shuffle or Mixed, this disables the fog that prevents you from seeing unvisited screens on the overworld map.

```
--shuffle_followers
```

This shuffles the follower companion locations, ie. Purple Chest, Old Man, etc.

```
--bonk_drops
```

This extends the item pool to bonk locations and makes them additional item locations

```
--prizeshuffle <mode>
```

This allows prizes (crystals/pendants) to shuffle outside their usual boss location.
