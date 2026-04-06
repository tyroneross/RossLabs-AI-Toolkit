---
name: design-validation
description: This skill should be used when the user asks to "build this UI", "implement this design", "make it look like", "check my progress", "does this match what I described", "build this component", "make this work", "implement the layout", "set up this page", or when frontend files (.tsx, .jsx, .vue, .svelte, .css, .scss, .swift) are being actively edited and implementation needs to stay aligned with user intent.
version: 0.5.0
user-invocable: false
canonical: true
source-plugin: ibr
source-repo: https://github.com/tyroneross/interface-built-right
---

# Design Implementation with IBR

Use IBR as a planning partner during the build — scan live pages to confirm implementation matches user intent, catch mismatches early, and track changes incrementally. Ground truth is what is actually rendered, not what the code is supposed to do.

## Validating Against User Intent

Every description the user provides is a testable assertion. Extract the claim and find the corresponding scan field:

| User said | Check this scan field |
|-----------|----------------------|
| "blue buttons" | `computedStyles.backgroundColor` on button elements |
| "16px font" | `computedStyles.fontSize` |
| "working search" | `interactive.hasOnClick: true` on the search trigger |
| "accessible" | `a11y.ariaLabel` present on interactive elements |
| "disabled submit until form is valid" | `interactive.isDisabled: true` on submit before input |

If a user assertion does not match the scan output, fix the mismatch before continuing.

## Scan While Building

Scan at each meaningful checkpoint:

1. After scaffolding the component structure
2. After applying layout and spacing
3. After wiring interactions and handlers
4. After adding accessibility attributes
5. After the user says "check my progress"

Each scan should produce fewer issues than the previous.

## Primary Tool: `ibr scan`

Call the `ibr scan` MCP tool to read the live page state.

**Returns:**
- Verdict: `PASS`, `ISSUES`, or `FAIL`
- Per-element data: selector, tagName, bounds, computedStyles, interactive status, a11y attributes
- Interactivity audit: buttons with/without handlers, links with real/placeholder hrefs
- Console errors and warnings
- Issue list with severity, category, description, and selector

## Change Tracking Workflow

1. **Capture baseline**: Call `ibr snapshot` before changes
2. **Make code changes**: Focused edits, avoid changing unrelated things
3. **Compare**: Call `ibr compare` after changes

| Verdict | Meaning | Action |
|---------|---------|--------|
| `MATCH` | No changes detected | Confirm expected |
| `EXPECTED_CHANGE` | Changes look intentional | Review and continue |
| `UNEXPECTED_CHANGE` | Something changed that shouldn't have | Investigate |
| `LAYOUT_BROKEN` | Major structural displacement | Fix immediately |

## Native iOS/watchOS/macOS Validation

For Swift/SwiftUI projects, use native IBR tools against the running simulator:
- `ibr native_scan` — extract accessibility elements and check layout
- `ibr native_snapshot` / `ibr native_compare` — track simulator-level changes
- `ibr native_devices` — list available simulators
- `ibr scan_macos` — scan macOS app via accessibility tree

## Decision Tree

| User intent | Tool | Notes |
|-------------|------|-------|
| "Check my UI" | `ibr scan` | Primary validation |
| "I'm about to change the nav" | `ibr snapshot` | Capture before changes |
| "Did my refactor break anything" | `ibr compare` | After changes |
| "Scan the simulator" | `ibr native_scan` | iOS/watchOS |
| "Scan the macOS app" | `ibr scan_macos` | macOS accessibility |

*ibr — design implementation*
