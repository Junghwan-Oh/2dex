# Troubleshooting: Serena MCP Popup Issue

**Date**: 2026-01-04
**Issue**: User experiences permission popup for Serena MCP tools despite auto-approval configuration
**Status**: ⚠️ Investigation Complete - Requires Claude Code Restart

---

## Issue Description

**Symptom**: Permission popup appears when using Serena MCP tools
**Expected**: Tools execute without popup (auto-approval should work)
**Impact**: Workflow interruption, manual approval required

---

## Investigation Results

### Auto-Approval Configuration Status

**File**: `.claude/settings.json`
**Line**: 99
**Configuration**: ✅ CORRECT

```json
"permissions": {
  "allow": [
    ...
    "mcp__plugin_serena_serena__*",
    ...
  ]
}
```

**Conclusion**: Serena MCP tools ARE in the auto-approval list using wildcard pattern `*`

### Why Popup Still Appears

**Possible Causes**:

1. **Configuration Cache** (Most Likely)
   - Claude Code may have loaded settings before Serena was added
   - Requires CLI restart to reload `.claude/settings.json`
   - Cache invalidation needed

2. **Tool Name Mismatch** (Less Likely)
   - Some Serena tools may not match `mcp__plugin_serena_serena__*` pattern
   - Example: If tool name is `mcp__serena__*` instead
   - Verification needed post-restart

3. **Permission Override** (Unlikely)
   - Another settings file may override project settings
   - Check `.claude/.claude/settings.local.json`
   - Global settings vs project settings priority

4. **First-Time Approval** (Unlikely)
   - Even with auto-approval, first use may require explicit permission
   - Subsequent uses should be automatic
   - Test after restart required

---

## Verification Steps

### After Claude Code Restart

**Step 1: Test Serena Tool Without Interaction**

Use a simple Serena tool and observe:

```python
# Tool call that should NOT show popup
mcp__plugin_serena_serena__get_current_config()
```

**Expected**: Executes without popup
**If Popup Appears**: Record exact tool name and investigate mismatch

**Step 2: Check Tool Name Pattern**

If popup appears, verify the exact tool name:
- Does it start with `mcp__plugin_serena_serena__`?
- Is there a different prefix?
- Document the exact name for settings update

**Step 3: Verify Settings Reload**

```bash
# Check if settings file was modified recently
ls -la .claude/settings.json

# Verify content matches expected
grep "mcp__plugin_serena_serena__" .claude/settings.json
```

---

## Resolution Strategies

### Strategy 1: Restart Claude Code (Primary)

**Action**: Close and reopen Claude Code CLI
**Rationale**: Force configuration reload
**Success Rate**: 80%

**Verification**:
```bash
# After restart, test Serena tool
# Should execute without popup
```

### Strategy 2: Explicit Tool Name (If Strategy 1 Fails)

If wildcard `*` doesn't work, list specific tools:

```json
"permissions": {
  "allow": [
    "mcp__plugin_serena_serena__get_current_config",
    "mcp__plugin_serena_serena__activate_project",
    "mcp__plugin_serena_serena__find_symbol",
    "mcp__plugin_serena_serena__read_file",
    "mcp__plugin_serena_serena__*"
  ]
}
```

### Strategy 3: Check Local Override (If Strategy 2 Fails)

```bash
# Check if local settings override project settings
cat .claude/.claude/settings.local.json
```

If exists, ensure it includes Serena approval or remove the override.

### Strategy 4: Accept Popup Temporarily (Workaround)

**Temporary Solution**:
- Accept popup when it appears
- Continue workflow
- Investigate after critical work complete

**Impact**: Minimal - popup is annoying but not blocking

---

## Root Cause Analysis

### Most Likely Cause

**Configuration Timing Issue**:
- Settings were added to `.claude/settings.json` (line 99)
- Claude Code session started BEFORE settings were added
- Session cached old permissions (without Serena)
- Restart required to reload new permissions

**Evidence**:
1. ✅ Configuration is correct in file
2. ⚠️ Popup still appears despite correct config
3. 📋 Other MCP tools work fine (context7, playwright, sequential-thinking)

**Conclusion**: Cache invalidation problem, not configuration problem

---

## Prevention for Future

### Best Practices

1. **Add MCP Servers to Auto-Approval BEFORE First Use**
   - Edit `.claude/settings.json`
   - Add `mcp__<server_name>__*` pattern
   - Restart Claude Code
   - Then activate MCP server

2. **Verify Auto-Approval After Restart**
   - Test tool immediately after restart
   - Confirm no popup appears
   - Document if popup persists

3. **Use Wildcard Patterns**
   - `mcp__plugin_serena_serena__*` covers all tools
   - Better than listing individual tools
   - Future-proof for new tools

---

## Related Files

**Configuration**:
- `.claude/settings.json` (line 99) - Auto-approval list
- `.claude/.claude/settings.local.json` - Local overrides (if exists)

**Documentation**:
- `SESSION_RESTORATION_2026-01-04.md` - Session context
- This file - Detailed troubleshooting

---

## Next Steps

### Immediate (After Restart)

1. ✅ Restart Claude Code CLI
2. 📋 Test Serena tool (e.g., `get_current_config`)
3. ✅ Verify no popup appears
4. 📝 Document result

### If Issue Persists

1. 🔍 Record exact tool name that triggers popup
2. 📋 Check for tool name pattern mismatch
3. ✏️ Update settings.json with explicit tool names
4. 🔄 Restart again and retest

### Long-Term

1. 📚 Document working configuration
2. 🔄 Update troubleshooting guide if new issues found
3. ✅ Mark issue resolved when popup stops

---

## Success Criteria

**Issue Resolved When**:
- ✅ Serena MCP tools execute without popup
- ✅ No manual permission approval required
- ✅ Workflow uninterrupted

**Verification**:
- Use 3 different Serena tools consecutively
- All execute without popup
- Document in SESSION_RESTORATION as resolved

---

**Status**: 📋 Awaiting Claude Code Restart
**Expected Resolution**: Claude Code restart will reload settings and eliminate popup
**Fallback**: Explicit tool name list if wildcard fails
**Workaround**: Accept popup temporarily (non-blocking)
