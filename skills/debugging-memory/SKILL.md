---
name: debugging-memory
description: This skill should be used when the user asks to "debug this", "fix this bug", "why is this failing", "investigate error", "getting an error", "exception thrown", "crash", "not working", "what's causing this", "root cause", "diagnose this issue", or describes any software bug or error. Also activates when spawning subagents for debugging tasks, using Task tool for bug investigation, or coordinating multiple agents on a debugging problem. Provides memory-first debugging workflow that checks past incidents before investigating.
version: 1.5.0
user-invocable: false
canonical: true
source-plugin: claude-code-debugger
source-repo: https://github.com/tyroneross/claude-code-debugger
---

# Debugging Memory Workflow

This skill integrates the claude-code-debugger memory system into debugging workflows. The core principle: **never solve the same bug twice**.

## Memory-First Approach

Before investigating any bug, always check the debugging memory using the debugger `search` MCP tool:

```
Use the debugger search tool with the symptom description.
```

The search returns a **verdict** with matching incidents and patterns.

**Verdict-based decision tree:**

1. **KNOWN_FIX**: Apply the documented fix directly, adapting for current context
2. **LIKELY_MATCH**: Review the past incident, use it as a starting point
3. **WEAK_SIGNAL**: Consider loosely related incidents, but investigate fresh
4. **NO_MATCH**: Proceed with standard debugging, document the solution afterward

## Progressive Depth Retrieval

Results are returned as compact summaries. Drill into matches on demand:

1. **Initial search**: Use the debugger `search` MCP tool — returns verdict + compact matches
2. **Drill down**: Use the debugger `detail` MCP tool with the ID to load full incident/pattern data
3. **Outcome tracking**: Use the debugger `outcome` MCP tool to record whether the fix worked, failed, or was modified

## Visibility

When this skill activates, always announce it to the user:

1. **Before searching**: Output "Checking debugging memory for similar issues..."
2. **After search**: Report result briefly:
   - Found match: "Found X matching incident(s) from past debugging sessions"
   - No match: "No matching incidents in debugging memory - starting fresh investigation"

## Structured Debugging Process

When no past solution applies, follow this systematic approach:

### 1. Reproduce
Establish a reliable reproduction path:
- Identify exact steps to trigger the bug
- Note any environmental factors (OS, dependencies, state)
- Create a minimal reproduction if possible

### 2. Isolate
Narrow down the problem space:
- Binary search through recent changes
- Disable components to find the culprit
- Check logs and error messages for clues

### 3. Diagnose
Find the root cause:
- Trace the execution path
- Examine state at failure point
- Identify the specific code causing the issue

### 4. Fix
Implement the solution:
- Make minimal, targeted changes
- Avoid side effects
- Consider edge cases

### 5. Verify
Confirm the fix works:
- Test the original reproduction steps
- Run related tests
- Check for regressions

## Incident Documentation

After fixing a bug, use the debugger `store` MCP tool to document it for future retrieval.

The store tool accepts:
- **symptom** (required): User-facing description of the bug
- **root_cause** (required): Technical explanation of why the bug occurred
- **fix** (required): What was done to fix it
- **category**: Root cause category (logic, config, dependency, performance, react-hooks)
- **tags**: Search keywords for future retrieval
- **files_changed**: List of files that were modified
- **file**: Primary file where the bug was located

### Quality Indicators

The memory system scores incidents on:
- Root cause analysis depth (30%)
- Fix documentation completeness (30%)
- Verification status (20%)
- Tags and metadata (20%)

Target 75%+ quality score for effective future retrieval.

## Pattern Recognition

The memory system automatically extracts patterns when 3+ similar incidents exist. Patterns represent reusable solutions with higher reliability than individual incidents.

When a pattern matches:
- Trust the solution template (90%+ confidence)
- Apply the recommended approach
- Note any caveats mentioned

## Parallel Domain Assessment

For complex issues that may span multiple areas, use parallel assessment to diagnose all domains simultaneously.

### Domain Assessors

| Assessor | Expertise |
|----------|-----------|
| `database-assessor` | Prisma, PostgreSQL, queries, migrations, connection issues |
| `frontend-assessor` | React, hooks, rendering, state, hydration, SSR |
| `api-assessor` | Endpoints, REST/GraphQL, auth, middleware, CORS |
| `performance-assessor` | Latency, memory, CPU, bottlenecks, optimization |

Launch assessors in parallel. Each returns confidence scores and recommended actions. Aggregate by ranking confidence and evidence count.

## Token-Efficient Retrieval

| Tier | Token Usage | Content |
|------|-------------|---------|
| Summary | ~100 tokens | ID, symptom preview, category |
| Compact | ~200 tokens | Short keys, essential fields |
| Full | ~550 tokens | Complete incident details |

Default budget: 2500 tokens. The system automatically selects the appropriate tier.

## MCP Tools Quick Reference

| Tool | Purpose |
|------|---------|
| `search` | Search memory for similar bugs (returns verdict) |
| `store` | Store a new debugging incident |
| `detail` | Get full details of an incident or pattern |
| `status` | Show memory statistics |
| `list` | List recent incidents |
| `patterns` | List known fix patterns |
| `outcome` | Record whether a fix worked |

*claude-code-debugger — debugging memory*
