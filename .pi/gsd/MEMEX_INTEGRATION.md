# GSD + Memex Integration Guide

**Purpose:** Combine GSD's structured handoff files with Memex's persistent knowledge graph for superior session management.

---

## Why Both?

| System | Captures | Use Case |
|--------|----------|----------|
| **GSD Handoff Files** | Session state (what we're doing right now) | Immediate resume context |
| **Memex Cards** | Knowledge (what we've learned, patterns, decisions) | Long-term memory, pattern reuse |

**Together:** Resume work immediately AND understand why decisions were made.

---

## Enhanced Pause Workflow

### Step 1: Traditional GSD Handoff
Create files as usual:
```bash
# Machine-readable state
.planning/HANDOFF.json

# Human-readable context
.planning/phases/02-core-entities/.continue-here.md
```

### Step 2: Memex Session Capture
Save session state to knowledge graph:
```python
memex_write(
    slug="gsd-session-{project}-{phase}",
    content="""
**Phase:** 02-core-entities (COMPLETE)
**Key Work:** [what was built]
**Next:** [what's next]
**Links:** [[pattern-used]], [[domain-knowledge]]
"""
)
```

### Step 3: Knowledge Cards
Capture reusable knowledge:
```python
# Domain model
memex_write(
    slug="{project}-domain",
    content="...domain knowledge..."
)

# Decisions with rationale
memex_write(
    slug="{project}-decisions",
    content="...decisions and why..."
)

# Solutions to problems
memex_write(
    slug="{project}-solutions",
    content="...blockers and workarounds..."
)
```

---

## Enhanced Resume Workflow

### Step 1: GSD State (Immediate)
```bash
# Load session state
cat .planning/HANDOFF.json
cat .planning/phases/XX/.continue-here.md
```

### Step 2: Memex Context (Deeper)
```python
# Load memory index
memex_recall()

# Find session notes
memex_search("ontario energy phase 2")

# Read related knowledge
memex_read("ontario-energy-pricing-domain")
memex_read("hacs-component-test-patterns")
```

### Step 3: Navigate Knowledge Graph
```python
# Follow links
memex_links("gsd-session-ontario-energy-phase2-complete")

# See all project cards
memex_search("ontario energy")
```

---

## Integration Pattern

### In HANDOFF.json:
```json
{
  "memex": {
    "session_card": "gsd-session-{project}-{phase}",
    "domain_card": "{project}-domain",
    "pattern_card": "{project}-patterns",
    "related_cards": [
      "gsd-init-complete",
      "phase-validation-process"
    ]
  }
}
```

### In .continue-here.md:
```markdown
## Memex Links
**Session State:** [[gsd-session-{project}-{phase}]]  
**Domain Knowledge:** [[{project}-domain]]  
**Patterns Used:** [[{project}-patterns]]
```

---

## Example: Ontario Energy Integration

### Pause (Complete Phase 2):
1. Create `.planning/HANDOFF.json` with phase status
2. Create `.planning/phases/02-core-entities/.continue-here.md`
3. Write `gsd-session-ontario-energy-phase2-complete` card
4. Update `ontario-energy-pricing-domain` card if needed
5. Create `gsd-pause-resume-memex-pattern` card for future use

### Resume Session:
```python
# Immediate context from GSD
read(".planning/HANDOFF.json")
read(".planning/phases/02-core-entities/.continue-here.md")

# Deep context from Memex
memex_recall()
memex_read("gsd-session-ontario-energy-phase2-complete")
memex_read("ontario-energy-pricing-domain")
memex_read("hacs-component-test-patterns")  # Reuse test patterns

# Navigate links
memex_links("gsd-session-ontario-energy-phase2-complete")
```

---

## Card Types to Create

| Type | Slug Pattern | Purpose |
|------|--------------|---------|
| **Session State** | `gsd-session-{project}-{phase}` | Point-in-time snapshot |
| **Domain Model** | `{project}-domain` | Business/domain knowledge |
| **Technical Decisions** | `{project}-decisions` | Why choices were made |
| **Solved Problems** | `{project}-solutions` | Blockers and workarounds |
| **Reusable Patterns** | `{pattern-name}` | Cross-project patterns |

---

## Convention: Wikilink References

Use `[[card-slug]]` to link cards:

```markdown
This uses [[hacs-component-test-patterns]] for testing approach.
See [[ontario-energy-pricing-domain]] for pricing formulas.
```

Pi automatically resolves these to card content.

---

## Benefits

1. **Immediate Resume:** GSD files load instantly  
2. **Deep Context:** Memex provides full background  
3. **Pattern Reuse:** Solutions documented once, used many times  
4. **Decision Preservation:** "Why" survives alongside "what"  
5. **Cross-Project:** Learnings from one project inform others

---

## Current Project Cards

| Card | Purpose | Links |
|------|---------|-------|
| `gsd-session-ontario-energy-phase2-complete` | Phase 2 snapshot | → patterns, domain |
| `ontario-energy-pricing-domain` | IESO/LMP knowledge | ← session |
| `gsd-pause-resume-memex-pattern` | Integration pattern | → all sessions |
| `gsd-task-tool-workaround` | Environment fix | ← this session |
| `phase-validation-process` | Validation methodology | ← all phases |
| `hacs-component-test-patterns` | Testing patterns | ← all HACS work |

---

## To View All Cards

```python
memex_recall()  # Load index
memex_search()  # List all
memex_organize()  # Check network health
```

---

## Files

- `MEMEX_INTEGRATION.md` - This guide
- `FAQ.md` - GSD compatibility issues
- `COMPATIBILITY.md` - Task() workaround
- `pi-gsd-compat.py` - Script for missing tools

---

*Pattern established: 2026-04-12*
*Project: Ontario Energy Pricing HACS Integration*
