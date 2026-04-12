#!/usr/bin/env python3
"""Demo: GSD + Memex Integration for Session Resume

Shows the combined workflow for pausing and resuming work
using both GSD handoff files and Memex knowledge graph.
"""

from __future__ import annotations

import json
from pathlib import Path


def pause_work():
    """Enhanced pause workflow with memex integration."""
    print("=" * 60)
    print("GSD + Memex Pause Workflow")
    print("=" * 60)
    print()

    # 1. Traditional GSD handoff
    print("Step 1: Create GSD Handoff Files")
    print("-" * 40)
    print("Creating .planning/HANDOFF.json...")
    print("Creating .planning/phases/XX/.continue-here.md...")
    print()

    # 2. Memex session capture
    print("Step 2: Save Session to Memex")
    print("-" * 40)
    print("Creating memex card: gsd-session-{project}-{phase}")
    print("  - Phase status")
    print("  - Key decisions")
    print("  - Links to patterns and domain knowledge")
    print()

    # 3. Capture reusable knowledge
    print("Step 3: Capture Reusable Knowledge")
    print("-" * 40)
    print("If new domain knowledge: {project}-domain")
    print("If new pattern: {pattern-name}")
    print("If blocker solved: {project}-solutions")
    print()

    print("=" * 60)
    print("Work paused successfully!")
    print("=" * 60)


def resume_work():
    """Enhanced resume workflow with memex integration."""
    print("=" * 60)
    print("GSD + Memex Resume Workflow")
    print("=" * 60)
    print()

    # 1. Load GSD state
    print("Step 1: Load GSD State (Immediate)")
    print("-" * 40)
    handoff_path = Path(".planning/HANDOFF.json")
    continue_path = Path(".planning/phases/02-core-entities/.continue-here.md")

    if handoff_path.exists():
        with open(handoff_path) as f:
            handoff = json.load(f)
        print(f"Phase: {handoff.get('phase')} - {handoff.get('phase_name')}")
        print(f"Status: {handoff.get('status')}")
        print(f"Task: {handoff.get('task')} of {handoff.get('total_tasks')}")

        # Check for memex links
        memex_links = handoff.get("memex", {}).get("related_cards", [])
        if memex_links:
            print(f"\nMemex links found: {len(memex_links)} cards")
    print()

    # 2. Load memex context
    print("Step 2: Load Memex Context (Deep)")
    print("-" * 40)
    print("Commands to run:")
    print("  memex_recall()           # Load index")
    print("  memex_read('session')    # Read session card")
    print("  memex_read('domain')     # Read domain knowledge")
    print("  memex_links('session')   # Navigate linked cards")
    print()

    # 3. Combine for full context
    print("Step 3: Combine for Full Context")
    print("-" * 40)
    print("GSD provides: Where we are")
    print("Memex provides: Why we're here, what we've learned")
    print()

    print("=" * 60)
    print("Ready to resume work!")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage: python3 demo_memex_integration.py [pause|resume]")
        sys.exit(1)

    if sys.argv[1] == "pause":
        pause_work()
    elif sys.argv[1] == "resume":
        resume_work()
    else:
        print(f"Unknown command: {sys.argv[1]}")
        print("Use 'pause' or 'resume'")
        sys.exit(1)
