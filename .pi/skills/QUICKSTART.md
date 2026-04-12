# Full Resume / Full Stop Quickstart

**New slash commands:** `/full-resume` and `/full-stop`

These enhanced commands combine GSD handoff files with Memex knowledge graph.

---

## `/full-resume` - Enhanced Resume

**What it does:**
1. Loads `.planning/HANDOFF.json` (GSD state)
2. Loads `.planning/phases/XX/.continue-here.md` (context)
3. Calls `memex_recall()` (load memory index)
4. Reads memex cards linked in handoff (deep context)
5. Navigates knowledge graph via links
6. Presents combined GSD + Memex view

**When to use:**
- Starting a new session on existing project
- "continue", "resume", "where were we"

**Example:**
```
You: /full-resume

I: ╔════════════════════════════════════════════╗
║ RESUME: Ontario Energy - Phase 2 ║
╠════════════════════════════════════════════╣
║ From GSD (Where we are): ║
║ Phase: 2 - core-entities ║
║ Status: completed ║
║ Task: 6/6 ║
╠════════════════════════════════════════════╣
║ From Memex (What we know): ║
║ Session: [[gsd-session-ontario-phase2]] ║
║ Domain: [[ontario-energy-pricing-domain]] ║
║ Pattern: [[gsd-pause-resume-memex-pattern]] ║
╚════════════════════════════════════════════╝
```

---

## `/full-stop` - Enhanced Pause

**What it does:**
1. Creates/updates `.planning/HANDOFF.json` (GSD state)
2. Creates/updates `.planning/phases/XX/.continue-here.md` (context)
3. Calls `memex_write()` (save session to knowledge graph)
4. Captures domain knowledge (if prompted)
5. Captures decisions (if prompted)
6. Updates HANDOFF.json with memex links
7. Commits with `wip` message

**When to use:**
- Ending a session
- "pause", "save state", "checkpoint"

**Example:**
```
You: /full-stop

I: ✓ Paused and Saved

Files:
- .planning/HANDOFF.json (state)
- .planning/phases/02-core-entities/.continue-here.md (context)

Memex:
- [[gsd-session-ontario-energy-phase2-complete]]
- [[ontario-energy-pricing-domain]]

Commit: 7db78dc
To Resume: /full-resume
```

---

## Comparison

| Feature | `/gsd-resume-work` | `/full-resume` |
|---------|-------------------|-----------------|
| GSD state | ✅ | ✅ |
| Phase context | ✅ | ✅ |
| Memex knowledge | ❌ | ✅ |
| Domain model | ❌ | ✅ |
| Decision history | ❌ | ✅ |
| Pattern reuse | ❌ | ✅ |

| Feature | `/gsd-pause-work` | `/full-stop` |
|---------|------------------|----------------|
| GSD handoff | ✅ | ✅ |
| Git commit | ✅ | ✅ |
| Memex session | ❌ | ✅ |
| Domain capture | ❌ | ✅ (prompted) |
| Decision capture | ❌ | ✅ (prompted) |
| Knowledge graph | ❌ | ✅ |

---

## Skill Files

| Skill | Location |
|-------|----------|
| `/full-resume` | `.pi/skills/full-resume/SKILL.md` |
| `/full-stop` | `.pi/skills/full-stop/SKILL.md` |

---

## Tips

1. **Always commit first** - Both skills commit automatically with `wip` prefix
2. **Memex persistence** - Cards survive across sessions and projects
3. **Wikilink navigation** - Use `[[card-name]]` to link related knowledge
4. **Knowledge compounds** - Each `/full-stop` adds to your knowledge graph

---

## Project Cards Created

Current session: [[gsd-session-ontario-energy-phase2-complete]]  
Domain knowledge: [[ontario-energy-pricing-domain]]  
Integration pattern: [[gsd-pause-resume-memex-pattern]]

View all: `memex_recall()` → `memex_search("ontario energy")`
