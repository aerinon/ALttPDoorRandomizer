# New Features

## Shopsanity

--shopsanity added. This adds 32 shop locations (9 more in retro) to the general location pool.

Multi-world supported. Thanks go to Pepper and CaitSith2 for figuring out several items related to this major feature.

Shop locations:
* Lake Hylia Cave Shop (3 items)
* Kakariko Village Shop (3 items)
* Potion Shop (3 new items)
* Paradox Cave Shop (3 items)
* Capacity Upgrade Fairy (2 items)
* Dark Lake Hylia Shop (3 items)
* Curiosity/Red Shield Shop (3 items)
* Dark Lumberjack Shop (3 items)
* Dark Potion Shop (3 items)
* Village of Outcast Hammer Peg Shop (3 items)
* Dark Death Mountain Shop (3 items)

Item Pool changes: To accommodate the new locations, new items are added to the pool, as follows:

* 10 - Red Potion Refills
* 9 - Ten Bombs
* 4 - Small Hearts
* 4 - Blue Shields
* 1 - Red Shield
* 1 - Bee
* 1 - Ten Arrows
* 1 - Green Potion Refill
* 1 - Blue Potion Refill
* 1 - +5 Bomb Capacity
* 1 - +5 Arrow Capacity

1. Initially, 1 of each type of potion refill is shuffled to the shops. (the Capacity Fairy is excluded from this, see step 4). This ensures that potions can be bought somewhere.
2. The rest of the shop pool is shuffled with the rest of the item pool. 
3. At this time, only Ten Bombs, Ten Arrows, Capacity upgrades, Small Hearts, and the non-progressive shields can appear outside of shops. Any other shop items are replaced with rupees of various amounts. This is because of one reason: potion refills and the Bee are indistinguishable from Bottles with that item in them. Receiving those items without a bottle or empty bottle is essentially a nothing item but looks like a bottle. Note, the non-progressive Shields interact fine with Progressive Shields (you never get downgraded) but are usually also a nothing item most of the time.
4. The Capacity Fairy cannot sell Potion Refills because the graphics are incompatible. 300 Rupees will replace any potion refill that ends up there.
5. For capacity upgrades, if any shop sells capacity upgrades, then it will sell all seven of that type. Otherwise, if plain bombs or arrows are sold somewhere, then the other six capacity upgrades will be purchasable first at those locations and then replaced by the underlying ammo. If no suitable spot is found, then no more capacity upgrades will be available for that seed. (There is always one somewhere in the pool.)
6. Any shop item that is originally sold by shops can be bought indefinitely, but only the first purchase counts toward total checks on the credits screen & item counter. All other items can be bought only once.

All items in the general item pool may appear in shops. This includes normal progression items and dungeon items in the appropriate keysanity settings.

#### Pricing Guide

All prices range approx. from half the base price to the base price in increments of 5, the exact price is chosen randomly within the range.

| Category          | Items   | Base Price | Typical Range |
| ----------------- | ------- |:----------:|:-------------:|
| Major Progression | Hammer, Hookshot, Mirror, Ocarina, Boots, Somaria, Fire Rod, Ice Rod | 250 | 125-250
|                   | Moon Pearl | 200 | 100-200
|                   | Lamp, Progressive Bows, Gloves, & Swords | 150 | 75-150
|                   | Triforce Piece | 100 | 50-100
| Medallions        | Bombos, Ether, Quake | 100 | 50-100
| Safety/Fetch      | Cape, Mushroom, Shovel, Powder, Bug Net, Byrna, Progressive Armor & Shields, Half Magic | 50 | 25-50
| Bottles			| Empty Bottle or Bee Bottle | 50 | 25-50
|       			| Green Goo or Good Bee | 60 | 30-60
|       			| Red Goo or Fairy | 70 | 35-70
|        			| Blue Goo | 80 | 40-80
| Health            | Heart Container | 40 | 20-40
|                   | Sanctuary Heart | 50 | 25-50 
|                   | Piece of Heart | 10 | 5-10
| Dungeon           | Big Keys | 60 | 30-60
|                   | Small Keys | 40 | 20-40
|                   | Info Maps | 20 | 10-20
|                   | Other Maps & Compasses | 10 | 5-10
| Rupees			| Green | Free | Free
|       			| Blue  | 2 | 2
|       			| Red  | 10 | 5-10
|       			| Fifty  | 25 | 15-25
|       			| One Hundred  | 50 | 25-50
|       			| Three Hundred  | 150 | 75-150
| Ammo	            | Three Bombs | 15 | 10-15
|       			| Single Arrow | 3 | 3
| Original Shop Items | Other Ammo, Refills, Non-Progressive Shields, Capacity Upgrades, Small Hearts, Retro Quiver, Universal Key | Original | Could be Discounted as Above  				

~~In addition, 4-7 items are steeply discounted at random.~~ Sales are over.

#### Rupee Balancing Algorithm

To prevent needed to grind for rupees to buy things in Sphere 1 and later, a money balancing algorithm has been developed to counteract the need for rupees. Basic logic: it assumes you buy nothing until you are blocked by a shop, a check that requires money, or blocked by Kiki. Then you must have enough to make all purchases. If not, any free rupees encountered may be swapped with higher denominations that have not been encountered. Ammo may also be swapped, if necessary.

(Checks that require money: Bottle Merchant, King Zora, Digging Game, Chest Game, Blacksmith, anything blocked by Kiki e.g. all of Palace of Darkness when ER is vanilla)

The Houlihan room is not in logic but the five dungeon rooms that provide rupees are. Pots with rupees, the arrow game, and all other gambling games are not counted for determining income.

Currently this is applied to seeds without shopsanity on so early money is slightly more likely if progression is on a check that requires money even if Shopsanity is not turned on. 

#### Retro and Shopsanity

9 new locations are added.

The four "Take Any" caves are converted into "Take Both" caves. Those and the old man cave are included in the shuffle. The sword is returned to the pool, and the 4 heart containers and 4 blue potion refills are also added to the general item pool. All items found in the retro caves are free to take once. Potion refills will disappear after use.

Arrow Capacity upgrades are now replaced by Rupees wherever it might end up.
 
The Ten Arrows and 5 randomly selected Small Hearts or Blue Shields are replaced by the quiver item (represented by the Single Arrow in game.) 5 Red Potion refills are replaced by the Universal small key. It is assured that at least one shop sells Universal Small Keys. The quiver may thus not be found in shops. The quiver and small keys retain their original base price, but may be discounted.

##### Misc Notes

The location counter both experimental and the credits now reflects the total and current checks made. Original retro for example is 221 while shopsanity by itself is 248. Keydropshuffle+sanity+retro can reach up to 290.

## In-Room Staircases/Ladders

In intensity level 2 and higher the in-floor staircases/ladders that take you between tiles can now be shuffled with
any N/S connections. (those that appear to go up one floor are North connection and those that go down are South ones)

Big thanks to Catobat for doing all the hard work.

## Enemizer change

The attic/maiden sequence is now active and required when Blind is the boss of Theives' Town even when bosses are shuffled.

## Settings code

File names have changed with a settings code instead of listing major settings chosen. Mystery games omit this for obvious reasons. Also found in the spoiler.

Added to CLI only now. With more testing, this will be added to the GUI to be able to save use settings codes for generation. 

## Mystery fixes

The Mystery.py file has been updated for those who like to use that for generating games. Supports keydropshuffle, 
shopsanity, and other settings that have been added.

## Triforce Hunt Options

Thanks to deathFouton!

--triforce_pool and --triforce_goal added to the CLI. 

Also, to the Mystery.py he added the following options:
* triforce_goal_min
* triforce_goal_max
* triforce_pool_min
* triforce_pool_max
* triforce_min_difference

See the example yaml file for demonstrated usage.

## Experimental Item Counter

New item counter modified to show total

# Bug Fixes and Notes.

* 0.3.1.6-u
	* Fix for inverted. AT or GT vanilla lobby in intensity 3 should not softlock on exit in non-ER modes.
	* Backward compatibility for "chaos" enemizer flags. (Thanks krebel)
	* Fix for potshuffle and swamp trench generation errors (Thanks StructuralMike)
	* Fix for TFH playthrough (Thanks StructuralMike)
	* Fix for Standard+Retro (Thanks StructuralMike)
	* New options for TFH in CLI and Mystery (Thanks deathFouton)
	* A few price adjustments for Shopsanity
	* Fixed a subtle problem with Progressive Shields introduced by Shopsanity
* 0.3.1.5-u
	* Ganon hints fixed for shops
	* Added support for a settings file so SahasrahBot and the main website can use it easier. (Thanks Synack)
	* Fix for Skull Pinball during re-generation attempts (thank compiling)
	* Fix for multiworld progression balancing and shopsanity
* 0.3.1.4-u
	* Fix for Blind when shuffled to TT and another dungeon
	* Remove use of RaceRandom
	* Minor update to GameType field
* 0.3.1.3-u
	* Fix for the Rom field on the GUI
* 0.3.1.2-u
	* Include base ER updates
		* Goal sign should now indicate whether Aga 2 is required or not
		* Inverted logic fixes
	* Potion shop (powder) item now properly replaced with rupees
	* Removed Arrow Capacity upgrades in retro (non-shopsanity)
	* Intensity level 3 fixes courtesy of Catobat
	* Scrolling issue in Desert Cannonball
* 0.3.1.1-u
	* Potion shop crash in non-shopsanity
* 0.3.1.0-u
	* Shopsanity introduced
	* Blind sequence restored when Blind is in Theives Town in boss shuffle
	* Settings code added to file name
	* Minor fix to Standard generation
* 0.3.0.4-u
	* QoL fixes from Mike
	* Allow PoD Mimics 2 as a lobby in non-keysanity seeds (Thanks @Catobat)
	* Fix for double-counting Hera key in keydropshuffle
* 0.3.0.3-u
	* Disallowed Swamp Lobby in Hyrule Castle in Standard mode
	* Prevent defeating Aga 1 before Zelda is delivered to the Sanctuary. (He can't take damage)
	* Fix for Ice Jelly room when going backward and enemizer is on
	* Fix for inverted - don't start as a bunny in Dark Sanctuary
	* Fix for non-ER Inverted with Lobby shuffle. Aga Tower's exit works properly now.
	* Fix for In-Room Stairs with Trap Doors
	* Key logic fix
	* Fix for door gen re-start
	* More lenient keys in DR+Retro
	* Fix for shufflepots option
* 0.3.0.2-u
	* Introduced in-room staircases/ladders
* 0.3.0.1-u
	* Problem with lobbies on re-rolls corrected
	* Potential playthrough problem addressed
* 0.3.0.0-u
	* Generation improvements. Basic >95% success. Crossed >80% success. 
	* Possible increased generation times as certain generation problem tries a partial re-roll 

# Known Issues

* Potential keylocks in multi-entrance dungeons
* Incorrect vanilla key logic for Mire