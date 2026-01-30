---
layout: default
title: Roadmap
nav_order: 5
---

# Development Roadmap
{: .no_toc }

Future plans and upcoming features for ALttP Door Randomizer.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Project Vision

Door Randomizer aims to provide the most comprehensive and flexible dungeon randomization experience for A Link to the Past while maintaining playability and logical consistency. Our focus is on:

1. **Robust Generation** - Ensuring seeds are always completable and logical
2. **Feature Richness** - Providing extensive customization options
3. **Community Engagement** - Responding to player feedback and needs
4. **Performance** - Improving generation speed and reliability

---

## Bug Fixes

Critical and important bugs that need to be addressed:

### Critical Bugs
- Dungeon Key HUD indicator issue (total is incorrect)
- Links House on DM pathing issues (See OWR solution)

### Minor Bugs
- Resolve Swamp Trench 2 draining issue (pot obtained but still drains)
- Fix OHKO logic issues - Crystal Path backwards in GT
- Fix MapCompass forbidden boss items mode (currently bugged)
- Killing Certain Red Guards Kills Music

---

## Logic & Generation Improvements

Improving dungeon generation algorithms and logic:

- Enhanced key logic algorithms (experimental mode in New Generation)
- Rework Uncle weapon/Escape small key
- Make Sanctuary heart the logical one (simplify sanctuary heart logic)
- Investigate rupee balancing issues causing failed generations

---

## New Features

New functionality and game modes, mostly planned for the NewGeneration branch:

- Portal placement flexibility (customizability and mixed dungeon pools)
- Smarter trap door placement (reduce forced mirroring)
- DR Keysanity menu improvements
- PitWarp feature
- Door Type pooling customizations
- OWR ER standardization (District ER, Links on Death Mountain issue)
- NewSwappedAlgorithm integration
- Bonk Item Pool from Overworld Randomizer (downstream integration)
- A better hint system
- Prize Shuffle from Overworld Randomizer (downstream integration)
- Map Screen from GK Randomizer (need to investigate)
- Other downstream integrations? (custom goals, follower shuffle, flute shuffle?)

---

## Quality of Life Enhancements

Improving user experience and usability:

- Preferred location groups (control item placement with warnings/failures/retries)
- Preset support
- Control output ROM name (customize generated ROM filename)
- Progress indicators for generations
- Better entrance tracking for trackers (investigate race legality)
- Super-tile split palettes (reduce hinting from palette colors)
- Turn off Bob by default for enemizer (fewer graphical glitches)

---

## Performance Improvements

Making generation faster and more efficient:

- Reduce memory footprint

---

## Customization & Content Creation

Tools and features for creating custom content:

- Re-design customizer file format (improved YAML structure)
- Presets for customizer (start from predefined base)
- Easier enemy customization (simpler interface for customizing specific enemies - better integration with customization system)

---

## Multiworld

Enhancements for multiplayer seeds:

- Multiworld documentation
- Ability to have similar randomizations across multiworlds (makes parts of it co-op)

---

## External Tools & Integration

Integration with external tools and platforms:

- Tracker integration features
- Web-based API

---

## Technical Debt & Refactoring

Behind-the-scenes code improvements:

- Modernize Rules.py (improve readability and maintainability)
- Python upgrade (3.10 deprecated in 2026)

---

## Research & Exploration

Experimental ideas that may or may not be implemented:

### Dungeon Randomization Ideas

- **Subroom randomization** - Randomize smaller rooms within a larger room (subtile vs. supertile doors)
- **Euclidean dungeon layouts** - Dungeon randomization that makes spatial sense (rooms connected geographically)
- **Swapped dungeon generation** - Create dungeons by swapping door destinations (requires new algorithms)

---

## Branch Strategy

### Current Branches

- **NewGeneration** - Active development branch for new generation system
- **NewSwappedAlgorithm** - Experimental branch for swapped item algorithm
- **DoorDevUnstable** - Main branch, maintenance mode - only bug fixes and patches (ready to be moved to official stable)
- **DoorDev** - Stale development branch (needs update)
- **Dev/Master** - Do NOT use for PRs. Used by upstream only.

### Planned Branch Changes

- Transition from DoorDevUnstable to DoorDev as main maintenance branch
- Transition NewGeneration to main development branch

---

## Completed Features

Recent accomplishments:

- ✅ Dynamic colored pots
- ✅ Free lamp cone
- ✅ Experimental key logic improvements

---

## How to Contribute

Want to help shape the future of Door Randomizer?

### For Players
- **Test seeds** - Play with different settings and report issues
- **Provide feedback** - Share what you like and what could be better
- **Suggest features** - Tell us what you want to see

### For Developers
- **Submit PRs to DoorDevUnstable**
- **Join Discord** - Discuss development in `#door-rando`
- **Write tests** - Improve test coverage
- **Improve documentation** - Help others understand the code

### For Creators
- **Custom rooms** - Design interesting custom rooms
- **Presets** - Create balanced preset configurations
- **Tutorials** - Teach others how to use Door Rando
- **Tools** - Build complementary tools (trackers, analyzers)

---

## Release Schedule

### Regular Releases
- **Unstable builds** - Automated on every push to DoorDevUnstable
- **Hotfixes** - As needed for critical bugs

### Upcoming Releases (Tentative)
- **v1.5.x** (Q2 2026) - DoorDevUnstable becomes DoorDev
- **v1.6** (Q3 2026) - Python upgrade
- **v2.0** (Q4 2026) - New Generation branch release

---

## Success Metrics

How we measure progress:

### Technical Metrics
- Generation success rate (target: >95%)
- Average generation time (target: <10s for crossed seeds)
- Memory usage (start measuring)
- Test coverage (start measuring)

---

## Feedback & Discussion

Have thoughts on the roadmap?

- **Discord**: Join `#door-rando` to discuss

---

*This roadmap is a living document and will be updated regularly as priorities shift and progress is made.*

Last updated: 2026-01-30
