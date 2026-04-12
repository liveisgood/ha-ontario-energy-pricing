# GSD Compatibility for pi-coding-agent

**Status:** ✅ Active - Workarounds in place  
**Environment:** pi@wsl (without Task tool)  
**GSD Version:** 1.30.0  

---

## The Problem

This GSD installation expects a `Task` tool for spawning subagents (gsd-nyquist-auditor, gsd-executor, etc.). The `Task` tool is **not available** in this environment.

### How it manifests:
- `{}` - Empty JSON response
- `Tool not found` errors during GSD workflows
- Validation/execution workflow steps mentioning "Spawn gsd-*-auditor" cannot complete

---

## The Solution

Use **`pi-gsd-compat.py`** to generate compatible workflows and execute agents inline.

### Quick Commands

```bash
# Generate compatible workflow for validation
python3 .pi/gsd/pi-gsd-compat.py validate-phase > /tmp/workflow-compat.md

# Generate compatible workflow for execution  
python3 .pi/gsd/pi-gsd-compat.py execute-phase > /tmp/exec-compat.md

# Execute agent inline (shows you what the agent would do)
python3 .pi/gsd/pi-gsd-compat.py exec-agent gsd-nyquist-auditor

# List available workflows
python3 .pi/gsd/pi-gsd-compat.py --help
```

---

## Usage Pattern

### When you see this in a GSD command:
```
Step 5: Spawn gsd-nyquist-auditor
Task(
  prompt="...",
  subagent_type="gsd-nyquist-auditor",
  ...
)
```

### Do this instead:

1. **Generate compatible workflow:**
   ```bash
   python3 .pi/gsd/pi-gsd-compat.py validate-phase > /tmp/compat.md
   ```

2. **Read the agent definition:**
   ```bash
   cat .pi/gsd/agents/gsd-nyquist-auditor.md
   ```
   (Or use `Read` tool to view)

3. **Execute the agent logic inline:**
   - The agent's execution flow is now YOUR instructions
   - Use standard pi tools: Read, Write, Edit, Bash, Make, etc.
   - Perform each step the agent would have done

4. **Return expected output format:**
   ```markdown
   ## GAPS FILLED
   [description of what was accomplished]
   ```

---

## What pi-gsd-compat.py Does

1. **Reads workflow files** from `.pi/gsd/workflows/`
2. **Identifies `Task(...)` calls** that would spawn agents
3. **Replaces them** with inline execution instructions
4. **Outputs compatible workflow** that's executable with standard tools

---

## Files Added

| File | Purpose |
|------|---------|
| `pi-gsd-compat.py` | Main compatibility script |
| `FAQ.md` | Frequently asked questions |
| `COMPATIBILITY.md` | This file - system documentation |

---

## Workflow Modifications

### validate-phase ➜ Step 5

**Original:** Spawn gsd-nyquist-auditor via Task()  
**Replacement:** Execute validation logic inline

1. Read agent definition
2. Analyze gaps from PLAN/SUMMARY
3. Create tests for each gap
4. Run verification
5. Write VALIDATION.md

### execute-phase ➜ Agent Execution

**Original:** Spawn gsd-executor via Task()  
**Replacement:** Execute tasks inline

1. Read PLAN.md
2. Execute each task's `<action>` block
3. Verify with `<acceptance_criteria>`
4. Update SUMMARY.md
5. Update STATE.md progress

---

## Agent Mapping

| GSD Command | Original Agent | Inline Action |
|-------------|----------------|---------------|
| `/gsd-validate-phase` | gsd-nyquist-auditor | Create validation tests |
| `/gsd-execute-phase` | gsd-executor | Execute plan tasks |
| `/gsd-plan-phase` | gsd-planner | Write PLAN.md |
| `/gsd-debug` | gsd-debugger | Investigate with logs |

---

## Example: Phase Validation

**Before (would fail):**
```
/gsd-validate-phase 2
→ Load workflow
→ Step 5: Task() ← FAILS HERE
```

**After (works):**
```
/gsd-validate-phase 2
→ python3 .pi/gsd/pi-gsd-compat.py validate-phase → /tmp/compat.md
→ Read /tmp/compat.md
→ Follow Step 5 (now has inline instructions)
→ Execute validation manually
→ Return ## GAPS FILLED
→ Continue workflow
```

---

## Success Criteria

- [x] `/gsd-validate-phase` works (tested with Phase 2)  
- [x] Agent definitions readable  
- [x] Compatible workflow generation works  
- [x] FAQ documents common issues  
- [ ] `/gsd-execute-phase` (needs testing)  
- [ ] `/gsd-plan-phase` (needs testing)  

---

## Contributing

To add support for more workflows:

1. Add pattern regex in `replace_task_with_inline()`
2. Test with `python3 pi-gsd-compat.py <workflow-name>`
3. Update FAQ.md with new instructions
4. Update this COMPATIBILITY.md

---

## References

- GSD Agents: `.pi/gsd/agents/`
- GSD Workflows: `.pi/gsd/workflows/`
- FAQ: `.pi/gsd/FAQ.md`
- Original GSD docs: `/usr/lib/node_modules/@mariozechner/pi-coding-agent/docs/`

---

## Contact

If you find new GSD commands that fail due to Task() tool missing:

1. Read the workflow from `.pi/gsd/workflows/`
2. Identify the Task() call location
3. Add support to `pi-gsd-compat.py`
4. Or execute manually following FAQ.md guidelines

---

*Maintained alongside pi-coding-agent GSD installation*
*Last verified: 2026-04-12*
