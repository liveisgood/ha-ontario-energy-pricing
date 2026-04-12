---
name: full-stop
description: Enhanced pause that saves to GSD handoff AND memex. Use when user says "/full-stop" or "pause and remember" or "save state" or "checkpoint". Combines GSD handoff files with memex knowledge capture for complete session preservation.
---

# Full Stop: GSD + Memex Handoff

## Trigger
- User sends: `/full-stop`
- User sends: `/full-pause`
- User sends: `pause and remember`
- User sends: `save state`
- User sends: `checkpoint`

## Process

### Step 1: Gather Current State

```yaml
git_project: $(basename `git rev-parse --show-toplevel`)
git_branch: $(git rev-parse --abbrev-ref HEAD)
git_commit: $(git rev-parse --short HEAD)

# Current phase from STATE.md
phase: $(grep "current_phase:" .planning/STATE.md | cut -d: -f2)
status: $(grep "status:" .planning/STATE.md | head -1 | cut -d: -f2)

# Check for incomplete work
handoff_exists: $(test -f .planning/HANDOFF.json && echo "true" || echo "false")
continue_exists: $(find .planning/phases -name ".continue-here.md" 2>/dev/null | head -1)
```

### Step 2: Create GSD Handoff (Traditional)

```json
{
  "version": "1.0",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "phase": {phase_number},
  "phase_name": "{phase_name}",
  "phase_dir": ".planning/phases/{padded_phase}-{name}",
  "plan": {current_plan},
  "task": {current_task},
  "total_tasks": {total_tasks},
  "status": "paused|blocked|needs_decision",
  "completed_tasks": [...],
  "remaining_tasks": [...],
  "blockers": [
    {
      "description": "{what is stuck}",
      "type": "technical|human_action|external",
      "workaround": "{if any}"
    }
  ],
  "human_actions_pending": [
    {
      "action": "{what needs to be done}",
      "context": "{why}",
      "blocking": true|false
    }
  ],
  "decisions": [
    {
      "decision": "{what}",
      "rationale": "{why}",
      "phase": "{phase}"
    }
  ],
  "uncommitted_files": "{git_status}",
  "next_action": "{specific first action}",
  "context_notes": "{mental state, approach}"
}
```

Write to: `.planning/HANDOFF.json`

### Step 3: Create Memex Session Card

```yaml
memex_write:
  slug: "gsd-session-{git_project}-{phase}-{status}"
  content: ""
---
title: GSD Session - {project} {phase}
created: {timestamp}
source: pi
category: gsd-session
modified: {timestamp}
---

**Session Checkpoint:** {phase} ({status})

**Project:** {project_name}
**Phase:** {phase} - {phase_name}
**Commit:** {git_commit}
**Branch:** {git_branch}
**Timestamp:** {timestamp}

**Completed Work:**
| Task | File | Status |
|------|------|--------|
| {N} | {file} | done |
...

**Next Phase:** {next_phase}
**Next Action:** {next_action}

**Links:**
- [[gsd-init-{project}]]
- [[{project}-domain]] (if exists)
- Other session: [[gsd-session-{project}-*]]
"""
```

### Step 4: Capture/Update Domain Knowledge

**Prompt user:** "Any domain knowledge to capture? (LMP rates, IESO endpoints, pricing formulas, etc.)"

If yes:
```yaml
memex_write:
  slug: "{project}-domain"
  content: "{domain knowledge with yaml frontmatter}"
```

### Step 5: Capture Decisions

**Prompt user:** "Any key decisions made this session? (approach chosen, technical choices, etc.)"

If yes:
```yaml
memex_write:
  slug: "{project}-decisions"
  content: "{decision and rationale with yaml frontmatter}"
```

### Step 6: Create .continue-here.md

```markdown
---
phase: {phase_dir}
task: {current_task}
total_tasks: {total_tasks}
status: paused
last_updated: {timestamp}
---

## Current State

**Phase {phase}: {phase_name} - PAUSED**

## Completed Work
- {completed tasks}

## Remaining Work
- {remaining tasks}

## Decisions Made
- {decisions}

## Memex Links
**Session:** [[gsd-session-{project}-{phase}]]
**Domain:** [[{project}-domain]]
**Decisions:** [[{project}-decisions]]

## Next Action
{next_action}
```

### Step 7: Update HANDOFF.json with Memex References

```json
{
  "memex": {
    "session_card": "gsd-session-{project}-{phase}",
    "domain_card": "{project}-domain",
    "pattern_card": "gsd-pause-resume-memex-pattern",
    "related_cards": [
      "gsd-init-{project}",
      "{project}-domain",
      "{project}-decisions"
    ]
  }
}
```

### Step 8: Commit

```bash
# Commit with standardized message
git add -A
git commit -m "wip({phase}-{task}): {phase_name} paused at task {task}/{total_tasks}

Session checkpoint:
- Completed: {completed_count} tasks
- Status: {status}
- Next: {next_action}"
```

### Step 9: Confirm

```markdown
✓ Paused and Saved

**Files:**
- .planning/HANDOFF.json (state)
- .planning/phases/{phase_dir}/.continue-here.md (context)

**Memex:**
- [[gsd-session-{project}-{phase}]] (session)
- [[{project}-domain]] (domain, if updated)
- [[{project}-decisions]] (decisions, if updated)

**Commit:** {git_hash}
**To Resume:** `/full-resume`
```

## Expected Response Format

```markdown
## Checkpoint Created: {timestamp}

**Phase:** {phase} - {phase_name}
**Task:** {task}/{total_tasks}
**Status:** {status}

**Saved to:**
- GSD: `.planning/HANDOFF.json`
- Memex: `gsd-session-{project}-{phase}`

**Commit:** `{git_hash}`

**Next:** {next_action}

**To Resume:** Use `/full-resume`
```

## Knowledge Captured

| Type | Card | When Captured |
|------|------|---------------|
| Session State | `gsd-session-{project}-{phase}` | Every pause |
| Domain Knowledge | `{project}-domain` | When prompted |
| Decisions | `{project}-decisions` | When prompted |
| Patterns | `{project}-patterns` | When prompted |
