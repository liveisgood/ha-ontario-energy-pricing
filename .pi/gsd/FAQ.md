# GSD Compatibility FAQ

**Environment:** pi-coding-agent without Task tool support  
**Version:** GSD 1.30.0-compat

---

## Quick Start

When GSD commands reference `/gsd-validate-phase` or other agent-spawning operations:

```bash
# Generate compatible workflow before reading
python3 .pi/gsd/pi-gsd-compat.py validate-phase > /tmp/workflow.md
cat /tmp/workflow.md  # Read this instead
```

Or just remember: **When you see `Task(...)`, execute the agent inline manually.**

---

## Common Issues & Solutions

### Issue: "Tool not found" when executing GSD commands

**Cause:** GSD workflows expect a `Task` tool to spawn subagents (gsd-nyquist-auditor, gsd-executor, etc.). This tool doesn't exist in pi-coding-agent.

**Solution:** Execute agent logic inline using standard pi tools.

**Steps:**
1. Read the agent definition: `cat .pi/gsd/agents/<agent-name>.md`
2. Follow the `<execution_flow>` using Read/Write/Edit/Bash/Make/CodingTask tools
3. Return the expected output format (GAPS FILLED, PARTIAL, or ESCALATE)

---

### Issue: `/gsd-validate-phase N` command

**What happens:** Workflow tries to spawn `gsd-nyquist-auditor` via `Task(...)`

**Workaround:**

1. Generate compatible workflow:
   ```bash
   python3 .pi/gsd/pi-gsd-compat.py validate-phase > /tmp/validate-compat.md
   ```

2. Read the compatible version instead of the original

3. When you reach Step 5 ("Spawn gsd-nyquist-auditor"):
   - Read `.pi/gsd/agents/gsd-nyquist-auditor.md`
   - Execute the logic inline:
     - For each gap: create/improve tests
     - Run tests to verify
     - Document in VALIDATION.md
   - Return result:
     - `## GAPS FILLED` - All tests pass
     - `## PARTIAL` - Some gaps remain (add to Manual-Only)
     - `## ESCALATE` - Implementation bug found

---

### Issue: `/gsd-execute-phase N` command

**What happens:** Workflow tries to spawn `gsd-executor` agent

**Workaround:**

1. Read the execution plan from `.planning/phases/N-*/N-PLAN.md`
2. Execute each task using standard tools
3. Write SUMMARY.md when complete

**Agent execution checklist:**
- [ ] Read PLAN.md for the phase
- [ ] Read any referenced CONTEXT.md
- [ ] Execute tasks one by one
- [ ] Run verification after each task
- [ ] Write SUMMARY.md documenting what was done
- [ ] Update STATE.md progress

---

### Issue: `/gsd-plan-phase N` command

**What happens:** Workflow tries to spawn `gsd-planner` agent

**Workaround:**

1. Read requirements and context:
   - `.planning/REQUIREMENTS.md`
   - `.planning/phases/N-*/N-CONTEXT.md` (if exists)
   - `.planning/ROADMAP.md`

2. Create PLAN.md manually:
   - List requirements to address
   - Break into tasks with clear actions
   - Define acceptance criteria per task
   - Reference files to create/modify

3. Use planning structure from templates:
   ```
   .pi/gsd/templates/PLAN.md
   ```

---

## Available Agents

When GSD asks to spawn an agent, here are the key ones:

| Agent | Purpose | Workaround |
|-------|---------|------------|
| `gsd-nyquist-auditor` | Create validation tests | Create tests inline using testing framework |
| `gsd-executor` | Execute plan tasks | Execute tasks using Read/Write/Edit/Bash |
| `gsd-planner` | Create phase plans | Write PLAN.md following template |
| `gsd-debugger` | Debug issues | Investigate using logs, reproduction steps |
| `gsd-verifier` | Verify implementation | Check against requirements manually |

All agent definitions: `.pi/gsd/agents/*.md`

---

## Output Formats

When executing agents inline, use these structured outputs:

### For Validation (nyquist-auditor)

**All gaps resolved:**
```markdown
## GAPS FILLED
All requirements have automated verification.
- Tests created: N
- Files: test_*.py
```

**Partial success:**
```markdown
## PARTIAL  
Resolved: N
Escalated: M
Manual-only: [list requirements that need manual verification]
```

**Critical issue:**
```markdown
## ESCALATE
Reason: [description of implementation bug or blocker]
File: [path to implementation with issue]
```

### For Execution (executor)

**Complete:**
```markdown
## EXECUTION COMPLETE
Phase: N
Tasks completed: M of M
Files changed: [list]
```

**Partial:**
```markdown
## EXECUTION PARTIAL
Tasks completed: N of M
Blocked: [task description]
Reason: [why blocked]
```

---

## Testing in This Environment

Since we can't spawn test runners via Task:

**Python projects:**
```bash
# Write tests manually
pytest tests/ -v  # If pytest is installed
python3 -m py_compile tests/*.py  # Syntax check
```

**Other languages:**
- Use language-specific test commands directly
- May need to install test dependencies first

---

## Phase Status Meanings

| Status | Meaning |
|--------|---------|
| `not_started` | Plan exists, no implementation yet |
| `in_progress` | Partially implemented |
| `complete` | Implemented, awaiting validation |
| `validated` | Implementation + tests complete |

---

## Quick Reference: GSD Commands

| Command | Original Action | Compatibility Mode |
|---------|-----------------|-------------------|
| `/gsd-validate-phase N` | Spawn nyquist-auditor | Generate compat workflow, execute inline |
| `/gsd-execute-phase N` | Spawn executor | Read PLAN.md, execute tasks manually |
| `/gsd-plan-phase N` | Spawn planner | Write PLAN.md from template |
| `/gsd-debug [issue]` | Spawn debugger | Investigate with standard tools |

---

## Files & Directories

| Path | Purpose |
|------|---------|
| `.pi/gsd/agents/` | Agent definitions (Markdown) |
| `.pi/gsd/workflows/` | Workflow definitions (XML-like in MD) |
| `.pi/gsd/templates/` | Templates for PLAN.md, VALIDATION.md |
| `.pi/gsd/pi-gsd-compat.py` | This compatibility script |
| `.planning/REQUIREMENTS.md` | Project requirements |
| `.planning/STATE.md` | Current project state |
| `.planning/phases/N-*/` | Phase-specific documents |

---

## Contributing

To add support for a new GSD command:

1. Find the workflow in `.pi/gsd/workflows/`
2. Identify `Task(...)` calls that need replacement
3. Add pattern to `pi-gsd-compat.py:replace_task_with_inline()`
4. Document in this FAQ

---

## Debugging

If something doesn't work:

1. Check if it's trying to spawn an agent
2. Read the agent definition from `.pi/gsd/agents/`
3. Execute steps manually
4. Return expected output format

---

*Last updated: 2026-04-12*
