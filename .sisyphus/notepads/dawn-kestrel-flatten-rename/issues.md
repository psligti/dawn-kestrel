# Issues Encountered

## Task: Establish root project layout and move packaging to repo root

### Issues Found

None significant. The restructuring went smoothly.

### Potential Issues to Monitor

1. **Pydantic Settings Config Conflict Warning**
   - Warning: `Legacy filename conflict for config '.env': using 'opencode-python' over 'opencode_python'`
   - This is expected and not a blocker for this task
   - Should be addressed in a future task if config loading needs to be standardized

2. **Deprecation Warnings from Compatibility Shim**
   - When importing `opencode_python`, users see: `opencode_python is deprecated; import dawn_kestrel instead.`
   - This is intentional and expected behavior
   - Users should update their imports to `dawn_kestrel`

### No Blockers

All expected outcomes achieved without encountering blocking issues.
