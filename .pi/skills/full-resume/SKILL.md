---
name: full-resume
description: Enhanced resume that loads GSD state AND memex context. Use when user says "/full-resume" or "resume with context" or "continue with memory". Combines GSD handoff files with memex knowledge graph for complete session restoration.
---

# Full Resume: GSD + Memex Integration

## Trigger
- User sends: `/full-resume`
- User sends: `resume with context`
- User sends: `continue with memory`

## Process

### Step 1: Check for GSD Handoff
```bash
# Check if handoff exists
ls .planning/HANDOFF.json 2>/dev/null && echo "Handoff found" || echo "No handoff"
```

**If not found:** Skip to Step 4

### Step 2: Load GSD State (Immediate Context)
```yaml
Read: .planning/HANDOFF.json
Parse:
  - phase: Current phase number
  - status: Phase status
  - task: Current task position
  - total_tasks: Total tasks
  - next_action: What to do next
  - memex: Memex card references
```

### Step 3: Load Phase Context
```yaml
Read: .planning/phases/{phase_dir}/.continue-here.md
Extract:
  - Completed work summary
  - Decisions made
  - Blockers (if any)
  - Context notes
```

### Step 4: Load Memex Knowledge (Deep Context)

**If HANDOFF.json has memex field:**
```yaml
memex_recall()  # Load index

memex_read(handoff.memex.session_card)
memex_read(handoff.memex.domain_card)  # if exists
memex_read(handoff.memex.pattern_card)  # if exists

# Load all related cards
for card in handoff.memex.related_cards:
    memex_read(card)

# Navigate knowledge graph
memex_links(handoff.memex.session_card)
```

**If no memex in handoff but standard cards exist:**
```yaml
# Try to find session card from git project name
git_project=$(basename `git rev-parse --show-toplevel`)

memex_search("{git_project}")
memex_list_recent(5)  # Last 5 cards

# Look for domain card
memex_search("{git_project} domain")
```

### Step 5: Present Complete Context

```markdown
╔════════════════════════════════════════════════════════════
║ RESUME: {project_name} - Phase {phase}
╠════════════════════════════════════════════════════════════
║ From GSD (Where we are):
║   Phase: {phase} - {phase_name}
║   Task: {task}/{total_tasks}
║   Status: {status}
║   Next: {next_action}
╠════════════════════════════════════════════════════════════
║ From Memex (What we know):
║   Session: {session_card}
║   Domain: {domain_card}
║   Patterns: {pattern_card}
║   Decisions: {decisions_count} recorded
║   Links: {(memex_links(session_card))}
╚════════════════════════════════════════════════════════════
```

### Step 6: Delete Handoff One-Shot Artifact

After successful resume (gaps filled), delete HANDOFF.json:

```bash
rm .planning/HANDOFF.json
```

### Step 7: Ready to Work

Present:
- Current phase status
- Immediate next action
- Any blockers or warnings
- Suggested next step

## Expected Output Format

```markdown
## Resumed: {date}

**Phase:** {phase} - {phase_name}
**Status:** {status}
**Task:** {task}/{total_tasks}

**GSD State:**
- {key point 1}
- {key point 2}

**Memex Knowledge:**
- [[session_card]]
- [[domain_card]]
- [[pattern_card]]

**Next:** {next_action}
```

## Fallback
If no HANDOFF.json exists:
- Fall back to `/gsd-resume-work` behavior
- Search memex for "{project}" cards
- Present recovery options
