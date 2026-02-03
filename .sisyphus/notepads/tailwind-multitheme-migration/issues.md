# Issues & Gotchas

## Important Notes
- SSE disconnect/reconnect should refetch current session theme to avoid stale state
- Must NOT store light/dark mode in API - it's local UI state only
- Must NOT build a full theme-builder UI - store only `theme_id`
- Must NOT have dynamic Tailwind class name generation
- Add explicit fallback behavior for unknown `themeId`

---

## Task 9 Issues & Gotchas

1. **No Optimistic UI Updates**: ThemePicker does not update theme immediately when user clicks
   - Current behavior: API call completes, SSE stream updates session, ThemeProvider applies theme
   - Result: Noticeable delay between click and theme change
   - Decision: Intentionally no optimistic updates to prevent UI inconsistencies with server state
   - Acceptable tradeoff: Consistency > perceived performance for this simple action

2. **CSS Variables for ThemePicker**: Component currently uses CSS classes but doesn't have associated CSS
   - ThemePicker uses classes like `theme-picker`, `theme-picker__option`, `theme-picker__swatch`, etc.
   - No CSS file created yet (will be migrated in Task 10)
   - Current state: Component renders but styling relies on Tailwind utilities or default browser styles
   - Note: Task 10 (component CSS migration) will add proper styling

3. **Gradient Definition in Component**: Theme swatch gradients defined as inline styles in component
   - Current: `gradient: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)'` for Aurora
   - Should ideally come from theme CSS variables for consistency
   - Task 5 theme presets already define these colors in CSS
   - Future improvement: Use CSS variables from themes.css for gradient swatches

4. **Test Mock Complexity**: Initial test implementation tried to use `vi.hoisted()` and `vi.doMock()`
   - This approach was overly complex and didn't work well with Vitest
   - Solution: Used simple `vi.mock()` at top level with straightforward mocks
   - Learning: Follow existing test patterns rather than over-engineering

---
