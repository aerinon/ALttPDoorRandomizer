# Documentation Guide for LLMs

## 1. Purpose and Scope

This guide provides a framework for documenting this project in a way that enables Large Language Models (LLMs) to quickly understand, reason about, and extend the codebase. It outlines what topics to cover, how to structure information, and best practices for clarity and context.

## 2. Project Overview

- Summarize the project's main goals and high-level architecture.
- List primary components and their responsibilities.
- State the intended audience for the documentation.

## 3. Directory and File Structure

- Describe the purpose of each major directory and file.
- Use relative paths and clickable links where possible.
- Example:

  ```
  - source/: Core source code
  - docs/: Documentation and guides
  - data/: Game data and assets
  ```

## 4. Codebase Conventions

- Document naming conventions, formatting, and docstring standards.
- Specify how to document functions, classes, and modules.

## 5. Core Concepts and Workflows

- Explain important algorithms, data flows, and logic.
- Use diagrams (e.g., Mermaid) for complex workflows.
- Highlight how different modules interact.

  Example Mermaid diagram:
  ```
  graph TD
    A[Input] --> B[Processing]
    B --> C[Output]
  ```

## 6. Best Practices for LLM Documentation

- Write concise, context-rich explanations.
- Use clear headings and semantic structure.
- Link related files, functions, and concepts.
- Highlight dependencies and integration points.
- Use diagrams for non-trivial flows.

## 7. Documentation Process and Maintenance Standards

- **Topic Coverage Mapping:** Regularly cross-reference all Python modules with documentation topics to identify gaps and overlaps.
- **Reference-Only Linking:** All documentation links to code must use file and symbol references only (e.g., [`source/dungeon/NewKeyLogic.py`](source/dungeon/NewKeyLogic.py)), never line numbers, to ensure maintainability.
- **No Code Snippets:** Do not include code blocks or inline code snippets in documentation topics. Instead, reference files, classes, or functions directly.
- **LLM-Friendly Practices:** Write for clarity, context, and modularity. Use semantic headings, bullet points, and diagrams where helpful.
- **Update Workflow:** When code changes, review documentation for affected references and update as needed. Use batch search/replace to maintain link consistency.
- **Documentation Review:** Periodically audit documentation for completeness and adherence to these standards.

### Checklist for Future Edits

- [ ] Cross-reference new or changed Python files with documentation topics.
- [ ] Ensure all links to code are file/symbol only (no line numbers).
- [ ] Remove or avoid code snippets in documentation topics.
- [ ] Use diagrams or lists for complex flows.
- [ ] Review documentation for clarity and LLM accessibility.
- [ ] Update this guide if the process changes.

## 8. Maintaining and Updating Topics

- When adding new features or modules, create or update a corresponding topic file in `docs/ai_context/topics/` and add an entry in `topics.md`.
- When removing or refactoring code, update or remove related documentation topics and references.
- Use a consistent naming scheme for topic files and headings to ensure clarity and discoverability.
- Periodically review all topic files for outdated information, broken references, or missing coverage.
- After major codebase changes, perform a full cross-reference audit between `.py` files and topics.
- Encourage contributors to document rationale, design decisions, and known limitations in topic files.
- Keep the `topics.md` index up to date as the canonical list of documentation topics.

### Deprecation and Legacy Code

- Minimize or eliminate documentation effort for deprecated code.
- Clearly mark deprecated modules, classes, or functions in both code and documentation.
- Maintain a dedicated section or file (e.g., `docs/ai_context/topics/deprecated.md`) listing deprecated features, their status, and planned removal timelines.
- Remove documentation for deprecated code once it is deleted from the codebase.
- Avoid referencing deprecated code in new or updated topic files unless necessary for historical context.

## 9. Example Section

### Example: Documenting a Module

```
## source/dungeon/NewKeyLogic.py

**Purpose:** Implements logic for new key distribution in dungeons.

**Key Functions:**
- [`calculate_new_keys`](source/dungeon/NewKeyLogic.py): Determines key placement based on dungeon layout.
- [`validate_key_logic`](source/dungeon/NewKeyLogic.py): Ensures all key placements are solvable.

**Related Files:**
- [`source/dungeon/SmallKeyDoorShuffle.py`](source/dungeon/SmallKeyDoorShuffle.py)
- [`source/dungeon/RoomList.py`](source/dungeon/RoomList.py)
```

## 10. Documenting the Randomizer Flow

- Create a dedicated topic for the overall flow of the randomizer, referencing [`Main.py`](../../Main.py).
- Summarize the orchestration steps: settings/seed initialization, world and module setup, item pool generation, logic/rule setup, ROM patching, and playthrough/spoiler generation.
- Use diagrams or bullet lists to clarify the sequence and dependencies.
- Link to relevant modules and files for each major step.

---

Follow this guide to ensure documentation is accessible, comprehensive, and optimized for LLMs and future contributors.