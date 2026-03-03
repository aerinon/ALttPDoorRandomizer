---
layout: default
title: Known Issues
nav_order: 4
---

# Known Issues & Bug Tracking
{: .no_toc }

Current known issues, bugs, and limitations in ALttP Door Randomizer.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Reporting Bugs

Before reporting a bug, please:

1. Check this page to see if the issue is already known
2. Search [existing GitHub issues](https://github.com/aerinon/ALttPDoorRandomizer/issues)
3. Verify you're using the latest version

### How to Report

Report bugs in this location:

- **Discord**: [ALTTP Randomizer Discord](https://discordapp.com/invite/alttprandomizer) in `#bug-reports` or `#door-rando` channels

### What to Include

When reporting a bug, please provide:

- **Spoiler log** if you have one
- If you don't have a spoiler log, include:
  - **Seed number** and **settings used** 
  - **Version** of Door Randomizer (from GUI or `--version`)
- **Website or Platform** (Windows, macOS, Linux) if generator error, or which website was used
- **Description** of the issue
- **Steps to reproduce** the problem
- **Screenshots or videos** (if applicable)
- Optionally, **Save state** (if gameplay issue) (and which emulator/version)

---

## Known Issues

### Critical Issues

#### Links House on Death Mountain - no logical way off the mountain

**Status**: Under investigation

Some ER generations can have Link's House be on Death Mountain and no good way off the mountain.


---

### Major Issues

#### Crossed Dungeon Generation Can Be Slow

**Status**: Performance optimization needed

Generating crossed dungeon seeds, especially with high intensity and complex settings, can take a significant amount of time (30 seconds to several minutes).

**Why**: The dungeon generation algorithm uses constraint satisfaction and local search, which can require many attempts to find valid layouts.

**Workaround**: Be patient, or reduce intensity/complexity of settings.

#### Rare Impossible Seeds (Generation Failures)

**Status**: Occasional, investigating

In rare cases, the generator may fail to place all items or create a valid dungeon layout. This usually happens with very restrictive settings combinations.

**Workaround**: Try a different seed number, or slightly adjust settings.

---

### Moderate Issues

#### Some Enemy Placements Can Be Problematic

**Status**: Ongoing ban list maintenance

Despite the enemy ban list, some enemy placements can occasionally cause issues:
- Blocking required paths
- Causing unavoidable damage
- Creating glitchy behavior
- Bush enemies not working correctly
- Wallmasters can cause issues in certain locations

**Workaround**: Report specific problematic enemy locations so they can be added to the ban list.

**Note**: Thieves are always unkillable and banned from the entire underworld.


---

### Minor Issues

#### Forbidden Boss Items "MapCompass" Mode Bugged

**Status**: Under investigation

The `mapcompass` option for `--restrict_boss_items` is currently bugged and not recommended for use.

**Workaround**: Use `dungeon` option instead, or use `none`.

#### Swamp Trench 2 Keeps Draining

**Status**: Known issue

In some configurations, Swamp Trench 2 continues to drain even after the pot is obtained.

**Workaround**: None currently. This is a known behavior issue.

#### Killing Certain Red Guards Kills Music

**Status**: Known issue

Killing certain red guards in specific locations causes the music to stop playing.

**Workaround**: None currently. This is a cosmetic issue that doesn't affect gameplay.

#### Some Lobbies Exitable During Escape (Standard Mode)

**Status**: Known issue

In standard mode, some dungeon lobbies can be exited during the escape sequence when they shouldn't be.

**Workaround**: Avoid leaving during escape if you want to maintain intended flow.

---

### Logic Issues

These are cases where the logic may not perfectly match what's actually possible in-game:

#### GT Crystal Paths Room Logic

**Status**: Under investigation

Crystal switch logic for GT Crystal Paths room may not properly account for OHKO scenarios when traversing backwards.

#### OHKO (One-Hit KO) Logic Issues

**Status**: Under investigation

In some configurations, unavoidable damage logic or OHKO scenarios may not be properly accounted for.

#### Hammerjump Logic and Mixed Travel

**Status**: Configurable behavior

Hammerjump and similar tricks (PoD Arena hovering, Mire Big Key bomb jump) can unintentionally put you in another dungeon with the wrong dungeon ID.

**Setting**: Use `--mixed_travel` to control this behavior:
- `prevent`: Adds rails to prevent tricks (default, recommended for learning)
- `allow`: Up to player discretion
- `force`: Sections forced to same dungeon

---

## Mode-Specific Issues

### Glitched Logic Modes

Several issues specific to glitched logic modes (OWG, HMG):

#### Cave State Issues

**Status**: Under investigation

Cave state in GT hearts area may not work correctly in glitched modes.

#### Rain State Issues

**Status**: Under investigation

Rain state handling may have issues in glitched logic modes.

#### Key/Pot SRAM System

**Status**: Needs restoration

Old key/pot SRAM system needs to be restored for glitched modes to work properly.

### Inverted Mode Issues

#### Dark Sanctuary Inverted Insanity

**Status**: Under investigation

Dark Sanctuary with inverted mode and insanity entrance shuffle may have double entrance issues.

#### Dark Sanctuary at Tavern Error

**Status**: In progress

When Dark Sanctuary is at Tavern location, Link's body position may be incorrect.

### Entrance Randomization Issues

#### Dungeon Boss Exits in Non-ER

**Status**: Under investigation

Dungeon boss exits may not work correctly when entrance randomization is disabled.

### Decoupled Doors Issues

#### Sanctuary Palette Detection

**Status**: Known issue

In decoupled doors mode, sanctuary palette doesn't correctly identify adjacent rooms. Uses exits instead of entrances for determination.

**Workaround**: Use coupled doors or original palette mode.

### Shopsanity Issues

#### Output YAML: Shopsanity Potions Missing

**Status**: Under investigation

When outputting to YAML format, shopsanity potions may not be correctly included in the item pool representation.

**Workaround**: Check spoiler log for actual item locations.

---

## Known Limitations & Design Decisions

These items are **not planned to be fixed** as they are either fundamental limitations, intentional design choices, or affect all ALttP randomizers.

### Game Engine Limitations

#### Compass Count Stops Working After Triforce

After obtaining the Triforce, compass counts no longer function correctly. This is true in all ALttP randomizers and is a base game limitation.

**Workaround**: Complete dungeon exploration before finishing the game if you need counts.

#### GT Bosses Don't Respawn

GT bosses don't respawn after killing them. This is intentional base game behavior.

### Door Randomizer Design Decisions

#### Hybrid Major Glitches Not Compatible with Door Shuffle

Hybrid major glitches logic is not compatible with door shuffle modes. This is a fundamental limitation due to how glitch logic interacts with shuffled dungeon interiors.

**Workaround**: Use Overworld Glitches logic instead, or disable door shuffle.

#### Fire Rod Not in Logic for Dark Rooms

Fire Rod is not in logic for dark rooms in door shuffle mode, as it's too difficult to determine which dark room you're in after doors are shuffled.

**Note**: This is different from Advanced mode in the vanilla randomizer.

#### Hammerjump Requiring Mixed Travel Settings

Hammerjump and similar tricks (PoD Arena hovering, Mire Big Key bomb jump) require `--mixed_travel` settings in crossed mode to allow unintended dungeon transitions.

#### Blind Maiden/Attic Sequence Always Required

Blind maiden/attic sequence is required even when boss is shuffled. This maintains story consistency.

#### Southeast Skull Woods Chest Not Guaranteed Key

In Entrance Randomizer, the southeast Skull Woods chest is guaranteed to be a small key. In Door Randomizer, this is not guaranteed. This is an intentional change from ER.

### Technical Limitations

#### Pottery Lottery Mode: Multiworld Item Limit

In pottery lottery mode, only 256 items for other players can be placed under pots in your world due to technical constraints in how the game tracks items.

---

## Feature Limitations

See the [Roadmap](/roadmap) for planned features.

---

## Recently Fixed Issues

See RELEASENOTES.md for the latest fixes.

And PastReleaseNotes.md for older fixes.

---

## Performance Issues

### Memory Usage

**Issue**: Generator can use significant memory for complex seeds.

**Most affected by**:
- Multiworld with many players
- Pottery lottery mode

**Workaround**: Close other applications, or increase available RAM.

---

## Emulator Compatibility

### Known Issues with Emulators

#### Older SNES9x versions

Some older versions (< 1.55) may have graphical glitches with certain custom graphics.

#### ZSNES

**Not recommended**: ZSNES is outdated and has known accuracy issues.

---

## Workarounds & Tips

### If Generation Keeps Failing

1. Switch to a different door shuffle mode
4. Disable some restrictive settings (strict key logic, dungeon item restrictions)
5. Use balanced fill algorithm instead of district restriction

### If Seed Seems Impossible

1. Check spoiler log to verify it's beatable
2. Remember new logic differences (see Features guide)
3. Check for required techniques (boots bonking, crystal switch bombs, etc.)
4. Ask for help in Discord with spoiler log

### If Performance Is Poor

1. Use pre-built executable instead of running from source
2. Close other applications
3. Update to latest version
4. Use simpler settings combinations


---

## Issue Status Tracking

For real-time status of known issues, check:

- Discord `#bug-reports` and `#door-rando` channels

---

Last updated: 2026-01-30

This page is maintained as issues are discovered and fixed. If you notice an issue not listed here, please report it!
