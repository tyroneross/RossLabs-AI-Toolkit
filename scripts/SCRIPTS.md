# scripts/

## marketplace-sync.py

Reconciles every distribution surface of toolkit plugin versions and detects
host-install drift across Claude Code and Codex.

### What it does

Four surfaces must agree on the same plugin version:

| Surface | File |
|---------|------|
| Claude marketplace | `.claude-plugin/marketplace.json` |
| Codex marketplace | `.agents/plugins/marketplace.json` |
| README table | `README.md` |
| Host installs | `~/.claude/plugins/installed_plugins.json`, `codex plugin list` |

The source of truth is the external GitHub repo's `.claude-plugin/plugin.json`
(what `claude plugin install` actually clones). The tool fetches this via
`gh api` and falls back to the local mirror under `plugins/<name>/` when the
network or `gh` is unavailable.

### Usage

```bash
# Dry-run: show what would change across catalog + README
python3 scripts/marketplace-sync.py --all

# Apply catalog + README changes
python3 scripts/marketplace-sync.py --all --write

# Check host installs (Claude + Codex) vs catalog truth; print fix commands
python3 scripts/marketplace-sync.py --check-hosts

# Combined: catalog sync + host check in one pass
python3 scripts/marketplace-sync.py --all --check-hosts

# CI/cron read-only check — exits 3 if ANY surface drifts
python3 scripts/marketplace-sync.py --check --source local

# Single plugin (uses local mirror, no gh call)
python3 scripts/marketplace-sync.py plugins/build-loop

# Force local-mirror sourcing (skip gh API)
python3 scripts/marketplace-sync.py --all --source local
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Changes proposed (or applied with `--write`) |
| 1 | Shape error (bad JSON, missing file, missing plugin) |
| 2 | All surfaces already in sync |
| 3 | `--check` mode: at least one surface drifted |

### Host-install drift detection (`--check-hosts`)

Compares each installed plugin's version against the catalog truth and prints
the exact remediation command.

**Claude Code:** reads `~/.claude/plugins/installed_plugins.json`. For each
stale scope emits:

```
claude plugin update <name>@rosslabs-ai-toolkit --scope <scope>
```

Restart Claude Code after updating.

**Codex:** runs `codex plugin list` and parses `ross-labs-local` marketplace
rows. Codex has no `plugin update` command; for each stale install emits:

```
codex plugin remove <name>@ross-labs-local
codex plugin add <name>@ross-labs-local
```

Both checks degrade gracefully: if the file/CLI is absent, a note is printed
and the check is skipped — the tool never crashes.

### package.json ↔ plugin.json drift (`--check`)

For each `plugins/<name>/` mirror that has both `package.json` and
`.claude-plugin/plugin.json`, reports a version mismatch. Report-only — no
cross-repo edits.

Currently all 13 mirrors are in sync. A drift here means someone bumped one
file but not the other during a local update.

### Daily automation (macOS launchd)

The root cause of catalog drift is the tool never running. A launchd plist
runs `--all --check` daily at 09:00 and logs results. Activation is explicit:

```bash
# Install and activate the daily job
python3 scripts/marketplace-sync.py --install-cron

# Remove it
python3 scripts/marketplace-sync.py --uninstall-cron
```

The plist is written to `~/Library/LaunchAgents/ai.rosslabs.marketplace-sync.plist`
and loaded via `launchctl load`. Logs go to:

```
~/Library/Logs/marketplace-sync.log
~/Library/Logs/marketplace-sync.err
```

The job exits 2 (clean) or 3 (drift found — check the log and run
`--check-hosts` for fix commands). It does NOT apply any changes automatically.

### Tests

```bash
# Run all unit tests (no live machine state, fixture-based)
python3 tests/test_marketplace_sync.py

# With pytest if available
python3 -m pytest tests/test_marketplace_sync.py -v
```

Tests cover: semver comparison, Claude installed_plugins.json parsing, Codex
plugin list parsing, drift detection, remediation command generation, and
package.json ↔ plugin.json drift detection. All tests use fixture files under
`tests/fixtures/` — zero dependency on live host state.
